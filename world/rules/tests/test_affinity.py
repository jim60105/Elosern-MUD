"""Sole-writer affinity API tests (affinity-system 3.x)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.rules.affinity import (
    AFFINITY_DAILY_CAP_HINT,
    AffinityRecord,
    AffinitySource,
    apply_affinity_change,
)
from world.rules.affinity_config import load_config
from world.rules.clock import CLOCK_YAML, get_world_clock

_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]


class AffinityWriterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object(NPC, key="host")
        self.player = create_object(PlayerCharacter, key="player")

    def _day_clock(self, day: int):
        get_world_clock()._persist(day * _DAY_SECONDS)
        return get_world_clock()

    @covers_requirement("affinity-system::apply-affinity-change-is-the-sole-affinity-writer-with-a-source-capped-daily-budget")
    def test_capped_sources_exhaust_the_daily_budget(self):
        for _ in range(5):
            outcome = apply_affinity_change(
                self.npc, self.player, AffinitySource.TALK, 1
            )
            self.assertTrue(outcome.applied)
        blocked = apply_affinity_change(
            self.npc, self.player, AffinitySource.TALK, 1
        )
        self.assertFalse(blocked.applied)
        self.assertTrue(blocked.budget_capped)
        self.assertEqual(blocked.delta_used, 0)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 5)
        record = self.npc.relations._load(self.player)
        self.assertEqual(record.daily_gain, 5)

    def test_partial_delta_applies_only_the_remaining_budget(self):
        for _ in range(3):
            apply_affinity_change(self.npc, self.player, AffinitySource.TALK, 1)
        outcome = apply_affinity_change(
            self.npc, self.player, AffinitySource.TRADE, 4
        )
        self.assertEqual(outcome.delta_used, 2)
        self.assertTrue(outcome.applied)
        self.assertTrue(outcome.budget_capped)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 5)
        record = self.npc.relations._load(self.player)
        self.assertEqual(record.daily_gain, 5)

    def test_zero_applied_at_cap_consumes_no_budget(self):
        apply_affinity_change(
            self.npc, self.player, AffinitySource.QUEST_COMPLETION, 99
        )
        self.assertEqual(self.npc.relations.affinity_for(self.player), 99)
        outcome = apply_affinity_change(
            self.npc, self.player, AffinitySource.TALK, 1
        )
        self.assertEqual(outcome.delta_used, 0)
        self.assertFalse(outcome.applied)
        self.assertFalse(outcome.budget_capped)
        record = self.npc.relations._load(self.player)
        self.assertEqual(record.daily_gain, 0)

    def test_budget_resets_on_a_new_world_day(self):
        self._day_clock(0)
        for _ in range(5):
            apply_affinity_change(self.npc, self.player, AffinitySource.TALK, 1)
        blocked = apply_affinity_change(
            self.npc, self.player, AffinitySource.TALK, 1
        )
        self.assertTrue(blocked.budget_capped)
        self._day_clock(1)
        outcome = apply_affinity_change(
            self.npc, self.player, AffinitySource.TALK, 1
        )
        self.assertTrue(outcome.applied)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 6)

    def test_quest_completion_bypasses_the_daily_cap(self):
        self._day_clock(0)
        for _ in range(5):
            apply_affinity_change(self.npc, self.player, AffinitySource.TALK, 1)
        outcome = apply_affinity_change(
            self.npc, self.player, AffinitySource.QUEST_COMPLETION, 2
        )
        self.assertTrue(outcome.applied)
        self.assertFalse(outcome.budget_capped)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 7)

    @covers_requirement("affinity-system::apply-affinity-change-is-the-sole-affinity-writer-with-a-source-capped-daily-budget", "affinity-system::the-party-auto-leave-recheck-hook-runs-after-negative-affinity-deltas")
    def test_negative_delta_never_resets_or_restores_budget(self):
        self._day_clock(0)
        for _ in range(5):
            apply_affinity_change(self.npc, self.player, AffinitySource.TALK, 1)
        with patch(
            "world.rules.affinity.run_auto_leave_recheck"
        ) as recheck:
            outcome = apply_affinity_change(
                self.npc, self.player, AffinitySource.TALK, -2
            )
        self.assertEqual(outcome.delta_used, -2)
        recheck.assert_called_once_with(self.npc, self.player)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 3)
        record = self.npc.relations._load(self.player)
        self.assertEqual(record.daily_gain, 5)

    def test_negative_delta_floors_at_zero(self):
        apply_affinity_change(
            self.npc, self.player, AffinitySource.QUEST_COMPLETION, 1
        )
        with patch("world.rules.affinity.run_auto_leave_recheck"):
            outcome = apply_affinity_change(
                self.npc, self.player, AffinitySource.TALK, -5
            )
        self.assertEqual(outcome.delta_used, -1)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 0)

    def test_unknown_source_is_rejected_without_writing(self):
        outcome = apply_affinity_change(self.npc, self.player, "mystery", 1)
        self.assertTrue(outcome.source_rejected)
        self.assertFalse(outcome.applied)
        self.assertFalse(self.npc.relations.has_record(self.player))

    def test_non_npc_owner_is_rejected_without_writing(self):
        monster = create_object(Monster, key="monster")
        outcome = apply_affinity_change(monster, self.player, AffinitySource.TALK, 1)
        self.assertTrue(outcome.source_rejected)
        self.assertFalse(monster.relations.has_record(self.player))
        player_owned = apply_affinity_change(
            self.player, self.player, AffinitySource.TALK, 1
        )
        self.assertTrue(player_owned.source_rejected)

    @covers_requirement("affinity-system::every-npc-holds-a-hidden-numeric-affinity-toward-each-player")
    def test_corrupted_record_recovers_to_defaults(self):
        self.npc.db.relations_data = {
            str(self.player.pk): {"value": "oops", "cap": 99, "daily_gain": 0, "daily_tick": 0}
        }
        with patch("world.rules.affinity.log_warn") as log:
            record = self.npc.relations._load(self.player)
        self.assertEqual(record, AffinityRecord())
        log.assert_called_once()
        self.assertEqual(self.npc.relations.affinity_for(self.player), 0)

    @covers_requirement("affinity-system::every-npc-holds-a-hidden-numeric-affinity-toward-each-player")
    def test_reads_never_materialize_a_record(self):
        self.assertEqual(self.npc.relations.affinity_for(self.player), 0)
        self.assertEqual(self.npc.relations.stage_for(self.player).id, "acquaintance")
        self.assertFalse(self.npc.relations.has_record(self.player))
        self.assertIsNone(self.npc.db.relations_data)

    def test_records_are_keyed_per_player(self):
        other = create_object(PlayerCharacter, key="other")
        apply_affinity_change(self.npc, self.player, AffinitySource.TALK, 1)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 1)
        self.assertEqual(self.npc.relations.affinity_for(other), 0)
        self.assertFalse(self.npc.relations.has_record(other))

    def test_capped_hint_is_fixed_and_non_numeric(self):
        for digit in "0123456789":
            self.assertNotIn(digit, AFFINITY_DAILY_CAP_HINT)

    def test_daily_cap_constant_matches_yaml(self):
        self.assertEqual(
            load_config().daily_interaction_cap, 5
        )
