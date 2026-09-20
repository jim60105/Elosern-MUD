"""Slice of ``test_defeat_aftermath_core``: RollbackTests, ZeroUncausedWriteTests."""
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
    _attack,
    _isolate_synthetic_catalog,
)


class ZeroUncausedWriteTests(WildernessDefeatMixin, RegistryIsolationMixin, DefeatAftermathBase):
    """The declared-write manifest battery (D-C7, tasks 6.1)."""

    # Record families the defeat settlement must leave byte-identical. Code,
    # not prose: each downstream change extends this manifest with its declared
    # writes and re-runs the battery.
    CLOCK_CAUSED_FAMILIES = (
        # Legitimate in-window mutations the world clock causally produces:
        # quest deadline failure, gauge daily decay/reset, merchant restock,
        # buff decay. The battery's settlement window crosses none of them.
        "quest_deadline",
        "gauge_daily",
        "restock",
        "buff_decay",
    )

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()
        self.companion = create_object(NPC, key="aftermath companion")
        self.companion.race = "human"
        self.companion.apply_race_baseline()
        self.companion.location = self.room
        self.guard_npc = create_object(NPC, key="aftermath staff")
        self.guard_npc.race = "human"
        self.guard_npc.apply_race_baseline()
        self.guard_npc.location = self.room
        from world.rules.party import join_party

        join_party(self.companion, self.player)
        apply_affinity_change(self.guard_npc, self.player, "quest_completion", 5)
        self.player.guild_rank = "E"
        write_counter_trait(self.player, "guild_merit", 10)
        self.player.wallet = 500
        # Seeded raw inventory (shape mirrors list_items: a list of keys).
        self.player.db.inventory = [_T_POTION]
        definition = register(quest("battery_defeat", stages=(QuestStage(0, defeat(bound=True)),)))
        record = accept(self.player, definition.key)
        self.bound_room = create_object(InstanceRoom, key="battery binding room")
        self.bound_monster = _monster("battery bound goblin")
        self.bound_monster.location = self.room
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=self.bound_room,
            objective_targets=(self.bound_monster,),
            protected_entities=(self.guard_npc,),
        )
        self._mark_population_monster(self.monster)

    def _manifest(self):
        """The declared-write manifest: family -> extractor (D-C7)."""
        player, companion, guard = self.player, self.companion, self.guard_npc
        return {
            "affinity": lambda: (
                guard.relations.affinity_for(player),
                companion.relations.affinity_for(player),
            ),
            "wallet": lambda: player.wallet,
            "inventory": lambda: list(player.db.inventory or []),
            "quest_progress": lambda: [dict(e) for e in (player.db.quest_log or [])],
            "guild_rank": lambda: player.guild_rank,
            "guild_merit": lambda: read_counter_trait(player, "guild_merit"),
            "protected_bindings": lambda: list(self.bound_room.db.pin_reasons or []),
            "party_binding": lambda: (list(player.db.party or []), companion.db.party_member),
        }

    @covers_requirement(
        "defeat-aftermath-core::defeat-settlement-s-only-uncaused-record-writes-are-the-declared-ones"
    )
    def test_manifest_section_ownership(self):
        manifest = self._manifest()
        for family in (
            "affinity",
            "wallet",
            "inventory",
            "quest_progress",
            "guild_rank",
            "guild_merit",
            "protected_bindings",
        ):
            self.assertIn(family, manifest)
        self.assertTrue(self.CLOCK_CAUSED_FAMILIES)

    @covers_requirement(
        "defeat-aftermath-core::defeat-settlement-s-only-uncaused-record-writes-are-the-declared-ones",
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained",
    )
    def test_defeat_settlement_writes_only_the_declared_records(self):
        before = {family: extract() for family, extract in self._manifest().items()}
        saved_marker_pk = self.monster.pk
        saved_bound_pk = self.bound_monster.pk
        # Defeat one: the population-marker monster despawns. Defeat two: the
        # quest-bound monster is retained by precedence.
        with self.captureOnCommitCallbacks(execute=True):
            self._defeat_by_forfeit(self.monster)
            self.player.traits.hp.current = 100
            self._defeat_by_forfeit(self.bound_monster)
        after = {family: extract() for family, extract in self._manifest().items()}
        self.assertEqual(after, before)
        self.assertFalse(ObjectDB.objects.filter(id=saved_marker_pk).exists())
        self.assertTrue(ObjectDB.objects.filter(id=saved_bound_pk).exists())
        self.assertEqual(self.bound_monster.location, self.room)
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.HOSTILE_PRESENT
        )


class RollbackTests(
    EventSourceIsolation, WildernessDefeatMixin, RegistryIsolationMixin, DefeatAftermathBase
):
    """Rollback injection after the writer's last write (tasks 6.2, D-C5)."""

    def setUp(self):
        open_synthetic_scope(self, "items", "prices", "shops")
        super().setUp()
        self.setUp_wilderness()
        self._mark_population_monster(self.monster)

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-aftermath-joins-the-round-s-atomic-persistence-unit"
    )
    @covers_requirement(
        "defeat-aftermath-recovery::the-recovery-phase-commits-with-the-settlement"
    )
    def test_persist_failure_rolls_back_the_whole_aftermath_and_retry_settles_once(self):
        engage(self.player, self.monster)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=1), patch("world.rules.combat.damage.roll_d100", return_value=1), patch("world.rules.combat.rounds.roll_d100", return_value=1):
            _attack(self.player, self.monster)
        saved_pk = self.monster.pk
        hp_after_round = self.player.traits.hp.current
        quest_log_before = [dict(e) for e in (self.player.db.quest_log or [])]
        with (
            patch("world.rules.combat_session.settlement._persist", side_effect=RuntimeError("injected")),
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        # Every aftermath write is absent: monster, bookkeeping, HP, buff.
        self.assertTrue(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.location, self.room)
        self.assertEqual(self.player.traits.hp.current, hp_after_round)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual([dict(e) for e in (self.player.db.quest_log or [])], quest_log_before)
        self.assertIsNotNone(self.player.db.active_combat)
        self.assertEqual(self.clock.tick, 6)
        # Retry settles fully, exactly once.
        with self.captureOnCommitCallbacks(execute=True):
            result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        self.assertFalse(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertFalse(self._registered(self.monster))
        self.assertIsNone(self.player.db.active_combat)
        # Combat 6s + recovery 8s (scale 0.5 over the 1.0/s stored rate).
        self.assertEqual(self.clock.tick, 20)

    @covers_requirement(
        "defeat-aftermath-recovery::the-recovery-phase-commits-with-the-settlement"
    )
    def test_outer_commit_failure_restores_the_recovery_advance(self):
        """The outer-owner seam covers the recovery advance's registry (duck 6)."""

        class OuterExplodingAtomic:
            def __init__(self):
                self.depth = 0
                self.exploded = False

            def __enter__(self):
                self.depth += 1
                return self

            def __exit__(self, exc_type, exc, tb):
                self.depth -= 1
                if exc_type is None and self.depth == 0 and not self.exploded:
                    self.exploded = True
                    raise RuntimeError("injected outer commit failure")
                return False

        self.isolate_event_sources(register_caravan_arrivals, sync_quest_runtime)
        _isolate_synthetic_catalog(self)
        store = create_object(Room, key="rollback store")
        merchant_npc = create_object(NPC, key="rollback merchant", location=store)
        merchant = Merchant.create(
            merchant_npc,
            service_id="t_synthetic_merchant",
            shop_key=_T_SHOP,
        )
        merchant_npc.components.add(merchant)
        merchant.merchant_stock = {_T_POTION: _T_POTION_STOCK_BEFORE, _T_BLADE: 1}
        merchant.last_restock_day = 0

        engage(self.player, self.monster)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=1), patch("world.rules.combat.damage.roll_d100", return_value=1), patch("world.rules.combat.rounds.roll_d100", return_value=1):
            _attack(self.player, self.monster)
        hp_after_round = self.player.traits.hp.current
        saved_marker = self.monster.db.population_key
        collected: list = []
        fake_tx = MagicMock()
        fake_tx.atomic.return_value = OuterExplodingAtomic()
        fake_tx.on_commit.side_effect = collected.append
        # The restock boundary (day 1, 06:00 = 108000) sits inside the first
        # attempt's recovery window (107996, 108004].
        self.clock.tick = 107990
        with (
            patch("django.db.transaction.atomic", fake_tx.atomic),
            patch("django.db.transaction.on_commit", fake_tx.on_commit),
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        # The successful recovery advance is fully restored: the player's
        # traits, and the contract-discovered merchant surface the advance
        # had already restocked.
        self.assertEqual(self.player.traits.hp.current, hp_after_round)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(merchant.merchant_stock[_T_POTION], _T_POTION_STOCK_BEFORE)
        self.assertEqual(merchant.last_restock_day, 0)
        self.assertEqual(self.monster.db.population_key, saved_marker)
        # Retry: the wake state and the advance are reproduced. The restock
        # boundary is day-granular: the reverted last_restock_day=0 with the
        # retry window still ending on day 1 after 06:00 legitimately catches
        # the day-1 restock up once.
        with self.captureOnCommitCallbacks(execute=True):
            result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertEqual(self.clock.tick, 108010)
        self.assertEqual(merchant.last_restock_day, 1)
        self.assertEqual(merchant.merchant_stock[_T_POTION], _T_POTION_RESTOCKED)

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-aftermath-joins-the-round-s-atomic-persistence-unit"
    )
    def test_commit_exit_failure_restores_aftermath_surfaces(self):
        class ExplodingAtomic:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                if exc_type is None:
                    raise RuntimeError("injected commit failure")
                return False

        collected: list = []
        engage(self.player, self.monster)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=1), patch("world.rules.combat.damage.roll_d100", return_value=1), patch("world.rules.combat.rounds.roll_d100", return_value=1):
            _attack(self.player, self.monster)
        saved_pk = self.monster.pk
        saved_marker = self.monster.db.population_key
        hp_after_round = self.player.traits.hp.current
        fake_tx = MagicMock()
        fake_tx.atomic.return_value = ExplodingAtomic()
        fake_tx.on_commit.side_effect = collected.append
        with (
            patch("django.db.transaction.atomic", fake_tx.atomic),
            patch("django.db.transaction.on_commit", fake_tx.on_commit),
            self.assertRaises(RuntimeError),
        ):
            forfeit(self.player)
        # The commit-exit failure bypasses any in-body handler: the outer
        # handler restored every idmapper-cached aftermath surface.
        self.assertEqual(self.player.traits.hp.current, hp_after_round)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(self.monster.db.population_key, saved_marker)
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.pk, saved_pk)  # callbacks never executed

    @covers_requirement(
        "defeat-aftermath-core::the-defeat-aftermath-joins-the-round-s-atomic-persistence-unit",
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained",
    )
    def test_outer_round_rollback_restores_aftermath_surfaces(self):
        # The submit path settles inside _submit_request's round transaction:
        # a failure AFTER the settlement returned must roll the aftermath
        # back together with the round (duck review issue 1).
        self.player.traits.hp.current = 1
        self.monster.traits.atk_phys.base = 100
        engage(self.player, self.monster)
        saved_pk = self.monster.pk
        saved_marker = self.monster.db.population_key
        real_continue = combat_session_module._continue_or_settle

        def exploding_continue(actor, record, battlefield, logs, **kwargs):
            real_continue(actor, record, battlefield, logs, **kwargs)
            raise RuntimeError("injected outer failure after settlement")

        with (
            patch(
                "world.rules.combat_session.rounds._continue_or_settle",
                exploding_continue,
            ),
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
            self.assertRaises(RuntimeError),
        ):
            _attack(self.player, self.monster)
        # The armed undo ran inside _submit_request's except: the winner and
        # its marker/bookkeeping survived the outer rollback.
        self.assertEqual(self.monster.pk, saved_pk)
        self.assertEqual(self.monster.db.population_key, saved_marker)
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.location, self.room)
        self.assertNotIn("defeat_weak", entity_active_buffs(self.player))
        self.assertEqual(self.player.traits.hp.current, 1)
        self.assertIsNotNone(self.player.db.active_combat)
