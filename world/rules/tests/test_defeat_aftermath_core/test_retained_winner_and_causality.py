"""Slice of ``test_defeat_aftermath_core``: RecoveryWindowClockCausalityTests, RetainedWinnerConsequenceTests."""
import math
import unittest
from unittest.mock import MagicMock, patch
from django.test import override_settings
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
import world.rules.defeat_aftermath as defeat_aftermath_module
import world.rules.defeat_aftermath.violation as defeat_aftermath_violation_module
from world.rules import combat_session as combat_session_module
from world.rules import clock as clock_module
from world.rules import guild_config as guild_config_module
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.components import Merchant
from typeclasses.rooms import InstanceRoom, Room
from world.quests.bootstrap import sync_quest_runtime
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)
from world.rules.caravan_arrivals import register_caravan_arrivals
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
    synth_offer_rule,
    synth_shop_config,
)
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.tests._fixtures import (
    RegistryIsolationMixin,
    accept,
    defeat,
    quest,
    register,
)
from world.rules.affinity import apply_affinity_change
from world.rules.buffs import entity_active_buffs, tick_buffs
from world.rules.clock import MAX_ADVANCE_SECONDS, AdvanceSource, WorldClock
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage,
    forfeit,
    restore_active_session,
    submit_player_action,
)
from world.rules.defeat_aftermath import (
    DEFEAT_AFTERMATH_RULEBOOK,
    solve_recovery_seconds,
    load_defeat_aftermath_sections,
    register_violation_hook,
)
from world.rules.event_log import render_plain_text
from world.rules.movement import charge_movement
from world.rules.player_messages import terminal_outcome_message
from world.rules.skip_safety import SkipRejectReason, evaluate_skip_safety
from world.rules.time_skip import advance_skip, seconds_to_full_regen
from world.rules.surfaces import read_counter_trait, write_counter_trait
from tools.spec_traceability import covers_requirement
from world.rules.tests._combat_session_helpers import (
    BattlefieldIsolation,
    _monster,
    _player,
    open_synthetic_scope,
)
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS

from ._support import (
    DefeatAftermathBase,
    EventSourceIsolation,
    WildernessDefeatMixin,
    _T_BLADE,
    _T_POTION,
    _T_POTION_RESTOCKED,
    _T_POTION_STOCK_BEFORE,
    _T_SHOP,
    _T_SHOP_RESTOCK_HOUR,
    _isolate_synthetic_catalog,
)


class RetainedWinnerConsequenceTests(WildernessDefeatMixin, DefeatAftermathBase):
    """Task 3.3: the retained winner blocks rest; movement stays HP-free."""

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()
        definition = register(quest("retained_defeat", stages=(QuestStage(0, defeat(bound=True)),)))
        record = accept(self.player, definition.key)
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=create_object(InstanceRoom, key="retained guard room"),
            objective_targets=(self.monster,),
        )

    @covers_requirement(
        "defeat-aftermath-core::hostile-defeat-floors-player-hp-at-1-and-marks-the-player-knocked-out",
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained",
    )
    def test_retained_winner_blocks_rest_but_not_movement(self):
        self._defeat_by_forfeit()
        self.assertEqual(self.player.traits.hp.current, 5)
        # skip_safety still refuses a time-skip rest with the live winner.
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.HOSTILE_PRESENT
        )
        # Movement has no HP gate (pinned behavior, no edit): the shared cost
        # charge succeeds at the post-settlement wake state.
        before = self.clock.tick
        charge_movement(self.player, "move")
        self.assertGreater(self.clock.tick, before)

    @covers_requirement(
        "defeat-aftermath-recovery::a-retained-quest-bound-winner-forces-the-move-and-rest-route"
    )
    def test_defeat_then_move_then_rest_to_full(self):
        """Task 3.3 smoke: retained winner -> wake at target -> move -> rest."""
        self._defeat_by_forfeit()
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.HOSTILE_PRESENT
        )
        # Movement has no HP gate: traverse an ordinary wilderness exit out
        # of the winner's room into an adjacent, monster-free, non-gateway
        # cell (the wilderness exits self-loop; routing is coordinate-based).
        from world.maps.wilderness_destination import (
            DIRECTION_DELTAS,
            find_gateway,
            normalize_wilderness_direction,
        )

        current = self.script.db.itemcoordinates[self.player]
        exits_by_direction = {
            normalize_wilderness_direction(exit_obj.key): exit_obj
            for exit_obj in self.room.exits
        }
        direction = next(
            _d for _d in sorted(DIRECTION_DELTAS) if not find_gateway(current, _d)
        )
        exit_obj = exits_by_direction[direction]
        delta_x, delta_y = DIRECTION_DELTAS[direction]
        neighbor = (current[0] + delta_x, current[1] + delta_y)
        exit_obj.at_traverse(self.player, exit_obj.destination)
        self.assertEqual(self.script.db.itemcoordinates[self.player], neighbor)
        # The Elosern map spawns a living monster on every wilderness cell at
        # room-activation time; the smoke arranges the destination's own
        # spawn away so the rest proves the movement route, not monster
        # density. The winner itself lives on, evicted back at (60, 103).
        for occupant in list(self.player.location.contents):
            if isinstance(occupant, Monster):
                occupant.delete()
        self.assertIsNone(evaluate_skip_safety(self.player))
        advance_skip(self.player, seconds_to_full_regen(self.player))
        self.assertEqual(self.player.traits.hp.current, self.player.traits.hp.max)


class RecoveryWindowClockCausalityTests(
    EventSourceIsolation, WildernessDefeatMixin, RegistryIsolationMixin, DefeatAftermathBase
):
    """The recovery window's clock causality (task 3.1, delta requirement 4)."""

    # altoria_general_store restocks at day-1 06:00 = 108000. The defeat at
    # tick 107990 spends 6s of combat and 8s of recovery, so exactly that one
    # boundary falls inside the recovery window (107996, 108004].
    RESTOCK_TICK = 86400 + _T_SHOP_RESTOCK_HOUR * 3600

    def setUp(self):
        open_synthetic_scope(self, "items", "prices", "shops")
        super().setUp()
        self.setUp_wilderness()
        clock_patcher = patch(
            "world.quests.runtime.get_world_clock", return_value=self.clock
        )
        clock_patcher.start()
        self.addCleanup(clock_patcher.stop)
        self.isolate_event_sources(register_caravan_arrivals, sync_quest_runtime)
        _isolate_synthetic_catalog(self)
        store = create_object(Room, key="window store")
        merchant_npc = create_object(NPC, key="window merchant", location=store)
        self.merchant = Merchant.create(
            merchant_npc,
            service_id="t_synthetic_merchant",
            shop_key=_T_SHOP,
        )
        merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {_T_POTION: _T_POTION_STOCK_BEFORE, _T_BLADE: 1}
        self.merchant.last_restock_day = 0

    def _manifest(self):
        player = self.player
        return {
            "wallet": lambda: player.wallet,
            "inventory": lambda: list(player.db.inventory or []),
            "guild_rank": lambda: player.guild_rank,
            "guild_merit": lambda: read_counter_trait(player, "guild_merit"),
        }

    @covers_requirement(
        "defeat-aftermath-recovery::clock-side-effects-during-the-recovery-window-are-the-only-quest-world-mutations"
    )
    def test_window_fails_exactly_one_deadline_and_restocks_once(self):
        self.clock.tick = self.RESTOCK_TICK - 3600  # accepted tick 104400
        definition = register(quest("window_deadline", deadline_hours=1))
        record = accept(self.player, definition.key)
        self.assertEqual(record.deadline_tick, self.RESTOCK_TICK)
        before = {family: extract() for family, extract in self._manifest().items()}
        self.clock.tick = self.RESTOCK_TICK - 10
        with self.captureOnCommitCallbacks(execute=True):
            self._defeat_by_forfeit()
        # Combat window (107990, 107996] crossed nothing; the recovery window
        # (107996, 108004] crossed the deadline and the restock together.
        self.assertEqual(self.clock.tick, self.RESTOCK_TICK + 4)
        self.assertEqual(self.player.traits.hp.current, 5)
        stored = [dict(entry) for entry in (self.player.db.quest_log or [])]
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["state"], "failed")
        self.assertEqual(stored[0]["failure_reason"], "deadline_expired")
        self.assertEqual(self.merchant.merchant_stock[_T_POTION], _T_POTION_RESTOCKED)
        self.assertEqual(self.merchant.last_restock_day, 1)
        self.assertEqual(self.merchant.merchant_stock[_T_BLADE], 1)
        after = {family: extract() for family, extract in self._manifest().items()}
        self.assertEqual(after, before)
