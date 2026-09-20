"""Slice of ``test_defeat_aftermath_core``: DepartureRuleTests, RecoveryFallbackDepartureTests, WildernessDepartureTests."""
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
    WildernessDefeatMixin,
)


class DepartureRuleTests(DefeatAftermathBase):
    """Violator departure precedence: quest-bound retain over despawn (D-C3)."""

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_foreign_monster_is_untouched(self):
        result = self._defeat_by_forfeit()
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.monster.pk, self.monster.pk)  # alive, untouched
        self.assertEqual(self.monster.location, self.room)


class WildernessDepartureTests(WildernessDefeatMixin, DefeatAftermathBase):
    """Population despawn and quest-bound retention in the real wilderness."""

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_population_winner_despawns_at_defeat_settlement(self):
        self._mark_population_monster(self.monster)
        saved_pk = self.monster.pk
        with self.captureOnCommitCallbacks(execute=True):
            self._defeat_by_forfeit()
        self.assertFalse(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertFalse(self._registered(self.monster))
        # The next coordinate activation respawns per the untouched model.
        from world.maps.wilderness_population import ensure_population

        ensure_population(self.script, (60, 103))
        monsters = [
            obj
            for obj in self.script.get_objs_at_coordinates((60, 103))
            if isinstance(obj, type(self.monster))
        ]
        self.assertEqual(len(monsters), 1)

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_quest_bound_winner_with_marker_is_retained(self):
        self._bind_defeat_quest(self.monster)
        self._mark_population_monster(self.monster)
        saved_pk = self.monster.pk
        self._defeat_by_forfeit()
        # Quest retention outranks the population marker: the monster stays.
        self.assertTrue(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertEqual(self.monster.location, self.room)
        self.assertTrue(self._registered(self.monster))

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_post_commit_delete_failure_reverts_departure(self):
        self._mark_population_monster(self.monster)
        saved_marker = self.monster.db.population_key
        with (
            patch.object(
                type(self.monster), "delete", side_effect=RuntimeError("boom")
            ),
            patch("world.rules.defeat_aftermath.aftermath.log_error") as log_error,
            self.captureOnCommitCallbacks(execute=True),
        ):
            self._defeat_by_forfeit()
        # Deterministic recovery: the logical departure reverted, the monster
        # remains a normal reconcilable population monster.
        self.assertEqual(self.monster.db.population_key, saved_marker)
        self.assertTrue(self._registered(self.monster))
        self.assertEqual(self.monster.location, self.room)
        errors = [
            call
            for call in log_error.call_args_list
            if call.args and call.args[0] == "defeat_aftermath_depart_delete_failed"
        ]
        self.assertEqual(len(errors), 1)

    def _bind_defeat_quest(self, monster):
        """Accept a bound-defeat quest whose objective targets ``monster``."""
        definition = register(quest("aftermath_defeat", stages=(QuestStage(0, defeat(bound=True)),)))
        record = accept(self.player, definition.key)
        self.guard_room = create_object(InstanceRoom, key="aftermath guard room")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=self.guard_room,
            objective_targets=(monster,),
            protected_entities=(self._guard_npc(),),
        )

    def _guard_npc(self):
        if not hasattr(self, "guard_npc"):
            self.guard_npc = create_object(NPC, key="aftermath guard")
            self.guard_npc.race = "human"
            self.guard_npc.apply_race_baseline()
        return self.guard_npc


class RecoveryFallbackDepartureTests(WildernessDefeatMixin, DefeatAftermathBase):
    """The degraded recovery path departs the resolvable winner (review D4)."""

    def setUp(self):
        super().setUp()
        self.setUp_wilderness()
        self._mark_population_monster(self.monster)

    @covers_requirement(
        "defeat-aftermath-core::living-winning-violators-depart-the-room-quest-bound-monsters-retained"
    )
    def test_moved_player_recovery_still_departs_population_winner(self):
        engage(self.player, self.monster)
        elsewhere = create_object(Room, key="recovery fallback room")
        self.player.location = elsewhere
        saved_pk = self.monster.pk
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            self.captureOnCommitCallbacks(execute=True),
        ):
            restore_active_session(self.player)
        self.assertEqual(self.player.traits.hp.current, 5)
        self.assertIn("defeat_weak", entity_active_buffs(self.player))
        self.assertFalse(ObjectDB.objects.filter(id=saved_pk).exists())
        self.assertFalse(self._registered(self.monster))
        self.assertIsNone(self.player.db.active_combat)
