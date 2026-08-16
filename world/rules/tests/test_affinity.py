"""Sole-writer affinity API tests (affinity-system 3.x)."""

from tools.spec_traceability import covers_requirement

import ast
import re
from pathlib import Path
from unittest.mock import patch
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.quests.catalog import register_catalog
from world.rules.affinity import (
    AFFINITY_DAILY_CAP_HINT,
    AffinityRecord,
    AffinitySource,
    apply_affinity_change,
    raise_affinity_cap,
)
from world.rules.affinity_config import load_config
from world.rules.clock import CLOCK_YAML, get_world_clock

_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]

REPO_ROOT = Path(__file__).resolve().parents[3]

_CAP_WRITER_EXCLUSIONS = ("world/rules/affinity.py",)


def _production_sources(root: Path, package: str):
    """Yield (package-relative_path, text) for non-test Python files."""
    for path in sorted(root.rglob("*.py")):
        parts = path.relative_to(root).parts
        if "tests" in parts or "__pycache__" in parts:
            continue
        yield f"{package}/{path.relative_to(root).as_posix()}", path.read_text(encoding="utf-8")


class CapOwnershipContractTests(unittest.TestCase):
    """No module outside ``world/rules/affinity.py`` mutates a record's cap.

    ``raise_affinity_cap`` is the sole cap writer (affinity-cap-break D1); the
    record's ``cap`` must only change through it, so any ``cap`` assignment or
    ``cap=`` keyword elsewhere is a regression of the monotonic/idempotent
    guarantee.
    """

    @covers_requirement("affinity-cap-break::raise-affinity-cap-is-the-sole-cap-writer-and-is-monotonic-and-idempotent")
    def test_only_the_cap_writer_mutates_a_records_cap(self):
        offenders = []
        for package in ("world", "typeclasses", "commands", "web", "server"):
            for relative, source in _production_sources(REPO_ROOT / package, package):
                if relative in _CAP_WRITER_EXCLUSIONS:
                    continue
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            text = ast.unparse(target)
                            if re.search(r"\.cap\b", text) or re.search(
                                r"\[['\"]cap['\"]\]", text
                            ):
                                offenders.append(f"{relative}: assigns {text}")
                    if isinstance(node, ast.Call):
                        keyword_names = {
                            kw.arg for kw in node.keywords if kw.arg is not None
                        }
                        if "cap" in keyword_names and ast.unparse(node.func) == "replace":
                            offenders.append(f"{relative}: replace(..., cap=...)")
        self.assertEqual(offenders, [])


class AffinityWriterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog()
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

    @covers_requirement("affinity-system::apply-affinity-change-is-the-sole-affinity-writer-with-a-source-capped-daily-budget")
    def test_friendly_fire_source_applies_without_budget_interaction(self):
        self._day_clock(0)
        for _ in range(5):
            apply_affinity_change(self.npc, self.player, AffinitySource.TALK, 1)
        with patch(
            "world.rules.affinity.run_auto_leave_recheck"
        ) as recheck:
            outcome = apply_affinity_change(
                self.npc,
                self.player,
                AffinitySource.FRIENDLY_FIRE,
                -1,
            )
        self.assertEqual(outcome.delta_used, -1)
        self.assertTrue(outcome.applied)
        self.assertFalse(outcome.budget_capped)
        self.assertFalse(outcome.source_rejected)
        recheck.assert_called_once_with(self.npc, self.player)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 4)
        record = self.npc.relations._load(self.player)
        self.assertEqual(record.daily_gain, 5)

    @covers_requirement("affinity-system::apply-affinity-change-is-the-sole-affinity-writer-with-a-source-capped-daily-budget")
    def test_sexual_forced_source_applies_without_budget_interaction(self):
        self._day_clock(0)
        for _ in range(5):
            apply_affinity_change(self.npc, self.player, AffinitySource.TALK, 1)
        with patch(
            "world.rules.affinity.run_auto_leave_recheck"
        ) as recheck:
            outcome = apply_affinity_change(
                self.npc,
                self.player,
                AffinitySource.SEXUAL_FORCED,
                -3,
            )
        self.assertEqual(outcome.delta_used, -3)
        self.assertTrue(outcome.applied)
        self.assertFalse(outcome.budget_capped)
        self.assertFalse(outcome.source_rejected)
        recheck.assert_called_once_with(self.npc, self.player)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 2)
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


class CapBreakWriterTests(EvenniaTest):
    """The sole cap writer ``raise_affinity_cap`` (affinity-cap-break 2.x)."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.npc = create_object(NPC, key="cap host")
        self.player = create_object(PlayerCharacter, key="cap player")

    @covers_requirement("affinity-cap-break::raise-affinity-cap-is-the-sole-cap-writer-and-is-monotonic-and-idempotent")
    def test_raise_sets_the_cap_and_preserves_value_and_daily_fields(self):
        apply_affinity_change(
            self.npc, self.player, AffinitySource.QUEST_COMPLETION, 30
        )
        record_before = self.npc.relations._load(self.player)
        changed = raise_affinity_cap(self.npc, self.player, 150)
        self.assertTrue(changed)
        record = self.npc.relations._load(self.player)
        self.assertEqual(record.cap, 150)
        self.assertEqual(record.value, 30)
        self.assertEqual(record.daily_gain, record_before.daily_gain)
        self.assertEqual(record.daily_tick, record_before.daily_tick)

    def test_raise_is_idempotent(self):
        raise_affinity_cap(self.npc, self.player, 150)
        changed = raise_affinity_cap(self.npc, self.player, 150)
        self.assertFalse(changed)
        self.assertEqual(self.npc.relations._load(self.player).cap, 150)

    def test_cap_only_grows(self):
        raise_affinity_cap(self.npc, self.player, 150)
        changed = raise_affinity_cap(self.npc, self.player, 99)
        self.assertFalse(changed)
        changed = raise_affinity_cap(self.npc, self.player, 100)
        self.assertFalse(changed)
        changed = raise_affinity_cap(self.npc, self.player, 151)
        self.assertTrue(changed)
        self.assertEqual(self.npc.relations._load(self.player).cap, 151)

    @covers_requirement("affinity-cap-break::raise-affinity-cap-is-the-sole-cap-writer-and-is-monotonic-and-idempotent")
    def test_recordless_player_gets_a_fresh_raised_record(self):
        self.assertFalse(self.npc.relations.has_record(self.player))
        changed = raise_affinity_cap(self.npc, self.player, 150)
        self.assertTrue(changed)
        record = self.npc.relations._load(self.player)
        self.assertEqual(record.cap, 150)
        self.assertEqual(record.value, 0)

    def test_raise_runs_no_auto_leave_hook(self):
        with patch("world.rules.affinity.run_auto_leave_recheck") as recheck:
            raise_affinity_cap(self.npc, self.player, 150)
        recheck.assert_not_called()

    def test_raise_rejects_non_npc_and_bad_new_cap(self):
        monster = create_object(Monster, key="cap monster")
        self.assertFalse(raise_affinity_cap(monster, self.player, 150))
        raise_affinity_cap(self.npc, self.player, 150)
        self.assertFalse(raise_affinity_cap(self.npc, self.player, "150"))
        self.assertFalse(raise_affinity_cap(self.npc, self.player, True))
        self.assertEqual(self.npc.relations._load(self.player).cap, 150)

    @covers_requirement("affinity-system::every-npc-holds-a-hidden-numeric-affinity-toward-each-player")
    def test_raised_cap_round_trips_through_storage(self):
        raise_affinity_cap(self.npc, self.player, 150)
        apply_affinity_change(
            self.npc, self.player, AffinitySource.QUEST_COMPLETION, 10
        )
        stored = self.npc.db.relations_data[str(self.player.pk)]
        self.assertEqual(stored["cap"], 150)
        self.assertEqual(stored["value"], 10)
        reloaded = self.npc.relations._load(self.player)
        self.assertEqual(reloaded.cap, 150)
        self.assertEqual(reloaded.value, 10)

    @covers_requirement("affinity-cap-break::raise-affinity-cap-is-the-sole-cap-writer-and-is-monotonic-and-idempotent")
    def test_fresh_record_created_by_raise_round_trips(self):
        raise_affinity_cap(self.npc, self.player, 150)
        stored = self.npc.db.relations_data[str(self.player.pk)]
        self.assertEqual(stored["cap"], 150)
        self.assertEqual(stored["value"], 0)
        self.assertEqual(stored["daily_gain"], 0)
        self.assertEqual(stored["daily_tick"], 0)

    @covers_requirement("affinity-cap-break::raise-affinity-cap-is-the-sole-cap-writer-and-is-monotonic-and-idempotent")
    def test_values_above_old_natural_cap_render_topmost_stage(self):
        raise_affinity_cap(self.npc, self.player, 150)
        apply_affinity_change(
            self.npc, self.player, AffinitySource.QUEST_COMPLETION, 130
        )
        self.assertEqual(self.npc.relations.affinity_for(self.player), 130)
        stage = self.npc.relations.stage_for(self.player)
        self.assertEqual(stage.id, "absolute_bond")
        self.assertEqual(stage.name, "絕對羈絆")
