"""NPC schedule model tests: rulebook, validation, assignment, sync, guards.

The shipped rulebook, every named validation error, the two storage shapes,
the assignment API, the consumer-side parser, the startup sync, and the
declared ``schedule_state`` no-writer contract (tasks 1.2, 2.x, 3.1, 4.x).
"""

from tools.spec_traceability import covers_requirement

import copy
import inspect
import tempfile
import unittest
from pathlib import Path

import yaml
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.npc_schedules import (
    MAX_ENTRIES,
    ParsedSchedule,
    SCHEDULE_TAG,
    ScheduleEntryError,
    ScheduleError,
    ScheduleRulebookError,
    ScheduleShapeError,
    ScheduleTemplateError,
    get_rulebook,
    load_rulebook,
    parse_stored_schedule,
    resolve_schedule,
    set_npc_schedule,
    sync_npc_schedules,
)

DAY_SECONDS = 86400

_VALID_RULEBOOK = {
    "schema_version": 1,
    "states": ["duty", "resting", "busy"],
    "templates": {
        "guard": {
            "default_state": "duty",
            "entries": [
                {"tick_offset": 21600, "kind": "move", "target": "north_gate"},
                {"tick_offset": 50400, "kind": "state", "state": "resting"},
                {"tick_offset": 64800, "kind": "move", "target": "barracks"},
            ],
        },
    },
}


def _write_deviant(mutate) -> Path:
    """Serialize a deviant rulebook derived from the valid one to a temp file."""
    data = copy.deepcopy(_VALID_RULEBOOK)
    mutate(data)
    directory = tempfile.mkdtemp()
    path = Path(directory) / "npc_schedules.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


class ShippedRulebookTests(unittest.TestCase):
    @covers_requirement("npc-schedule-model::role-templates-are-immutable-rulebook-data-with-a-fixed-entry-shape")
    def test_shipped_rulebook_loads_and_validates(self):
        rulebook = load_rulebook()
        self.assertEqual(rulebook.schema_version, 1)
        self.assertEqual(rulebook.states, ("duty", "resting", "busy"))
        keys = {template.key for template in rulebook.templates}
        self.assertGreaterEqual(keys, {"guard", "storekeeper", "resident"})
        guard = rulebook.template_by_key("guard")
        self.assertEqual(guard.default_state, "duty")
        self.assertEqual([entry.kind for entry in guard.entries], ["move", "state", "move"])

    def test_get_rulebook_returns_the_validated_singleton(self):
        self.assertIs(get_rulebook(), get_rulebook())


class RulebookValidationTests(unittest.TestCase):
    def _assert_rulebook_rejected(self, mutate, error):
        with self.assertRaises(error) as raised:
            load_rulebook(path=_write_deviant(mutate))
        self.assertTrue(str(raised.exception).strip())

    @covers_requirement("npc-schedule-model::role-templates-are-immutable-rulebook-data-with-a-fixed-entry-shape")
    def test_move_entry_with_state_field_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"][0]["state"] = "resting"

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    @covers_requirement("npc-schedule-model::role-templates-are-immutable-rulebook-data-with-a-fixed-entry-shape")
    def test_move_entry_without_target_is_rejected(self):
        def mutate(data):
            del data["templates"]["guard"]["entries"][0]["target"]

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    @covers_requirement("npc-schedule-model::role-templates-are-immutable-rulebook-data-with-a-fixed-entry-shape")
    def test_state_entry_with_target_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"][1]["target"] = "north_gate"

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_state_entry_without_state_is_rejected(self):
        def mutate(data):
            del data["templates"]["guard"]["entries"][1]["state"]

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_unknown_kind_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"][1]["kind"] = "teleport"

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_unknown_entry_field_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"][0]["price"] = 5

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    @covers_requirement("npc-schedule-model::role-templates-are-immutable-rulebook-data-with-a-fixed-entry-shape")
    def test_tick_offset_at_day_seconds_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"][1]["tick_offset"] = DAY_SECONDS

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_negative_tick_offset_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"][1]["tick_offset"] = -1

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_non_integer_tick_offset_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"][1]["tick_offset"] = "noon"

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_boolean_tick_offset_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"][1]["tick_offset"] = True

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    @covers_requirement("npc-schedule-model::role-templates-are-immutable-rulebook-data-with-a-fixed-entry-shape")
    def test_valid_default_state_is_accepted(self):
        rulebook = load_rulebook()
        self.assertEqual(rulebook.template_by_key("guard").default_state, "duty")

    @covers_requirement("npc-schedule-model::role-templates-are-immutable-rulebook-data-with-a-fixed-entry-shape")
    def test_out_of_vocabulary_default_state_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["default_state"] = "meditating"

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_out_of_vocabulary_state_value_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"][1]["state"] = "meditating"

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_template_not_mapping_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"] = [
                {"tick_offset": 21600, "kind": "move", "target": "north_gate"}
            ]

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_template_without_entries_is_rejected(self):
        def mutate(data):
            del data["templates"]["guard"]["entries"]

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_empty_template_entries_are_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"] = []

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_oversized_template_is_rejected(self):
        def mutate(data):
            data["templates"]["guard"]["entries"] = [
                {"tick_offset": 60 * index, "kind": "state", "state": "duty"}
                for index in range(MAX_ENTRIES + 1)
            ]

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_unknown_top_level_field_is_rejected(self):
        def mutate(data):
            data["season_names"] = ["spring"]

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_wrong_schema_version_is_rejected(self):
        def mutate(data):
            data["schema_version"] = 2

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_missing_states_vocabulary_is_rejected(self):
        def mutate(data):
            del data["states"]

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_empty_states_vocabulary_is_rejected(self):
        def mutate(data):
            data["states"] = []

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_duplicate_states_are_rejected(self):
        def mutate(data):
            data["states"] = ["duty", "duty"]

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_empty_templates_are_rejected(self):
        def mutate(data):
            data["templates"] = {}

        self._assert_rulebook_rejected(mutate, ScheduleRulebookError)

    def test_unreadable_rulebook_file_is_rejected(self):
        with self.assertRaises(ScheduleRulebookError):
            load_rulebook(path=Path("/nonexistent/npc_schedules.yaml"))

    def test_invalid_yaml_rulebook_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "npc_schedules.yaml"
            path.write_text("schema_version: [unclosed", encoding="utf-8")
            with self.assertRaises(ScheduleRulebookError):
                load_rulebook(path=path)


class TemplateResolutionTests(unittest.TestCase):
    def test_template_reference_resolves_to_template_entries(self):
        parsed = resolve_schedule({"schema_version": 1, "template": "guard"})
        self.assertEqual(
            [entry.kind for entry in parsed.entries], ["move", "state", "move"]
        )
        self.assertEqual(parsed.default_state, "duty")
        self.assertIsNone(parsed.effective_from_tick)

    @covers_requirement("npc-schedule-model::per-npc-schedules-are-assigned-through-one-validated-api-and-stored-in-exactly")
    def test_override_merges_shallowly_into_one_entry(self):
        parsed = resolve_schedule(
            {
                "schema_version": 1,
                "template": "guard",
                "overrides": {"0": {"target": "east_wall"}},
            }
        )
        self.assertEqual(parsed.entries[0].target, "east_wall")
        self.assertEqual(parsed.entries[0].tick_offset, 21600)
        self.assertEqual(parsed.entries[1].state, "resting")
        self.assertEqual(parsed.default_state, "duty")

    def test_override_changing_kind_is_rejected(self):
        # Fields not mentioned in an override keep template values, so the
        # merged entry still carries the base kind's forbidden field; a kind
        # change is not expressible through overrides.
        with self.assertRaises(ScheduleEntryError):
            resolve_schedule(
                {
                    "schema_version": 1,
                    "template": "guard",
                    "overrides": {"1": {"kind": "move", "target": "east_wall"}},
                }
            )

    @covers_requirement("npc-schedule-model::per-npc-schedules-are-assigned-through-one-validated-api-and-stored-in-exactly")
    def test_override_missing_entry_index_is_rejected(self):
        with self.assertRaises(ScheduleTemplateError):
            resolve_schedule(
                {
                    "schema_version": 1,
                    "template": "guard",
                    "overrides": {"9": {"target": "east_wall"}},
                }
            )

    def test_override_non_string_key_is_rejected(self):
        with self.assertRaises(ScheduleTemplateError):
            resolve_schedule(
                {
                    "schema_version": 1,
                    "template": "guard",
                    "overrides": {0: {"target": "east_wall"}},
                }
            )

    def test_override_value_not_mapping_is_rejected(self):
        with self.assertRaises(ScheduleTemplateError):
            resolve_schedule(
                {"schema_version": 1, "template": "guard", "overrides": {"0": None}}
            )

    def test_override_introducing_out_of_vocabulary_state_is_rejected(self):
        with self.assertRaises(ScheduleEntryError):
            resolve_schedule(
                {
                    "schema_version": 1,
                    "template": "guard",
                    "overrides": {"1": {"state": "meditating"}},
                }
            )

    @covers_requirement("npc-schedule-model::role-templates-are-immutable-rulebook-data-with-a-fixed-entry-shape")
    def test_unknown_template_key_is_rejected(self):
        with self.assertRaises(ScheduleTemplateError):
            resolve_schedule({"schema_version": 1, "template": "druid"})

    @covers_requirement("npc-schedule-model::per-npc-schedules-are-assigned-through-one-validated-api-and-stored-in-exactly")
    def test_full_custom_list_resolves_exactly(self):
        entries = [
            {"tick_offset": 21600, "kind": "move", "target": "north_gate"},
            {"tick_offset": 50400, "kind": "state", "state": "busy"},
        ]
        parsed = resolve_schedule({"schema_version": 1, "entries": entries})
        self.assertEqual(len(parsed.entries), 2)
        self.assertEqual(parsed.entries[0].target, "north_gate")
        self.assertEqual(parsed.entries[1].state, "busy")
        self.assertIsNone(parsed.default_state)

    def test_both_template_and_entries_are_rejected(self):
        with self.assertRaises(ScheduleShapeError):
            resolve_schedule(
                {
                    "schema_version": 1,
                    "template": "guard",
                    "entries": [
                        {"tick_offset": 21600, "kind": "move", "target": "north_gate"}
                    ],
                }
            )

    def test_overrides_without_template_are_rejected(self):
        with self.assertRaises(ScheduleShapeError):
            resolve_schedule(
                {
                    "schema_version": 1,
                    "entries": [
                        {"tick_offset": 21600, "kind": "move", "target": "north_gate"}
                    ],
                    "overrides": {"0": {"target": "east_wall"}},
                }
            )

    def test_missing_schema_version_is_rejected(self):
        with self.assertRaises(ScheduleShapeError):
            resolve_schedule({"template": "guard"})

    def test_wrong_schema_version_is_rejected(self):
        with self.assertRaises(ScheduleShapeError):
            resolve_schedule({"schema_version": 2, "template": "guard"})

    def test_non_dict_schedule_is_rejected(self):
        with self.assertRaises(ScheduleShapeError):
            resolve_schedule(["guard"])

    def test_unknown_schedule_field_is_rejected(self):
        with self.assertRaises(ScheduleShapeError):
            resolve_schedule({"schema_version": 1, "template": "guard", "extra": 1})

    def test_empty_custom_entries_are_rejected(self):
        with self.assertRaises(ScheduleShapeError):
            resolve_schedule({"schema_version": 1, "entries": []})

    def test_custom_entries_not_list_are_rejected(self):
        with self.assertRaises(ScheduleShapeError):
            resolve_schedule(
                {
                    "schema_version": 1,
                    "entries": {"tick_offset": 21600, "kind": "move", "target": "north_gate"},
                }
            )

    def test_custom_entries_as_tuple_are_rejected(self):
        entries = tuple(
            [{"tick_offset": 21600, "kind": "move", "target": "north_gate"}]
        )
        with self.assertRaises(ScheduleShapeError):
            resolve_schedule({"schema_version": 1, "entries": entries})

    def test_oversized_custom_entries_are_rejected(self):
        entries = [
            {"tick_offset": 60 * index, "kind": "state", "state": "duty"}
            for index in range(MAX_ENTRIES + 1)
        ]
        with self.assertRaises(ScheduleShapeError):
            resolve_schedule({"schema_version": 1, "entries": entries})

    def test_effective_from_tick_is_carried_through(self):
        parsed = resolve_schedule(
            {"schema_version": 1, "template": "guard"}, effective_from_tick=1234
        )
        self.assertEqual(parsed.effective_from_tick, 1234)


class AssignmentApiTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object(NPC, key="test_npc", location=self.room1)

    @covers_requirement("npc-schedule-model::per-npc-schedules-are-assigned-through-one-validated-api-and-stored-in-exactly")
    def test_template_reference_parses_and_sets_tag_and_freshness(self):
        schedule = {
            "schema_version": 1,
            "template": "guard",
            "overrides": {"0": {"target": "east_wall"}},
        }
        set_npc_schedule(self.npc, schedule)
        self.assertEqual(self.npc.db.schedule, schedule)
        self.assertEqual(self.npc.db.schedule_effective_from_tick, get_world_clock().tick)
        self.assertTrue(self.npc.tags.has(SCHEDULE_TAG))
        parsed = parse_stored_schedule(self.npc)
        self.assertEqual(parsed.entries[0].target, "east_wall")
        self.assertEqual(parsed.default_state, "duty")

    @covers_requirement("npc-schedule-model::per-npc-schedules-are-assigned-through-one-validated-api-and-stored-in-exactly")
    def test_full_custom_list_parses_and_sets_tag(self):
        schedule = {
            "schema_version": 1,
            "entries": [
                {"tick_offset": 21600, "kind": "move", "target": "north_gate"}
            ],
        }
        set_npc_schedule(self.npc, schedule)
        self.assertEqual(self.npc.db.schedule, schedule)
        self.assertTrue(self.npc.tags.has(SCHEDULE_TAG))
        parsed = parse_stored_schedule(self.npc)
        self.assertEqual(parsed.entries[0].target, "north_gate")
        self.assertIsNone(parsed.default_state)

    def test_effective_from_tick_records_the_assignment_tick(self):
        get_world_clock().advance(1000, AdvanceSource.SKIP, [])
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "guard"})
        self.assertEqual(self.npc.db.schedule_effective_from_tick, 1000)

    def test_malformed_shapes_reject_and_write_nothing(self):
        for malformed in (
            {"schema_version": 2, "template": "guard"},
            {"schema_version": 1, "template": "guard", "entries": []},
            ["guard"],
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ScheduleError):
                    set_npc_schedule(self.npc, malformed)
                self.assertIsNone(self.npc.db.schedule)
                self.assertIsNone(self.npc.db.schedule_effective_from_tick)
                self.assertFalse(self.npc.tags.has(SCHEDULE_TAG))

    @covers_requirement("npc-schedule-model::per-npc-schedules-are-assigned-through-one-validated-api-and-stored-in-exactly")
    def test_clearing_a_schedule_removes_the_tag(self):
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "guard"})
        set_npc_schedule(self.npc, None)
        self.assertIsNone(self.npc.db.schedule)
        self.assertIsNone(self.npc.db.schedule_effective_from_tick)
        self.assertFalse(self.npc.tags.has(SCHEDULE_TAG))


class StoredScheduleParsingTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object(NPC, key="test_npc", location=self.room1)

    def test_none_stored_schedule_parses_to_no_schedule(self):
        self.assertIsNone(parse_stored_schedule(self.npc))

    def test_valid_stored_schedule_parses(self):
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "guard"})
        parsed = parse_stored_schedule(self.npc)
        self.assertIsInstance(parsed, ParsedSchedule)
        self.assertEqual(len(parsed.entries), 3)

    @covers_requirement("npc-schedule-model::per-npc-schedules-are-assigned-through-one-validated-api-and-stored-in-exactly")
    def test_malformed_stored_value_resolves_to_no_schedule(self):
        self.npc.db.schedule = {"schema_version": 2, "template": "guard"}
        self.assertIsNone(parse_stored_schedule(self.npc))

    def test_missing_effective_tick_resolves_to_no_schedule(self):
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "guard"})
        self.npc.db.schedule_effective_from_tick = None
        self.assertIsNone(parse_stored_schedule(self.npc))

    def test_non_integer_effective_tick_resolves_to_no_schedule(self):
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "guard"})
        self.npc.db.schedule_effective_from_tick = "yesterday"
        self.assertIsNone(parse_stored_schedule(self.npc))


class StartupSyncTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object(NPC, key="test_npc", location=self.room1)
        self.other = create_object(NPC, key="other_npc", location=self.room1)

    @covers_requirement("npc-schedule-model::startup-synchronization-is-idempotent-and-degrades-safely")
    def test_sync_confirms_schedules_and_tags(self):
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "guard"})
        set_npc_schedule(
            self.other,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "move", "target": "north_gate"}
                ],
            },
        )
        sync_npc_schedules()
        self.assertTrue(self.npc.tags.has(SCHEDULE_TAG))
        self.assertTrue(self.other.tags.has(SCHEDULE_TAG))
        self.assertEqual(len(parse_stored_schedule(self.npc).entries), 3)
        self.assertEqual(len(parse_stored_schedule(self.other).entries), 1)

    @covers_requirement("npc-schedule-model::startup-synchronization-is-idempotent-and-degrades-safely")
    def test_broken_schedule_degrades_without_blocking_others(self):
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "guard"})
        self.other.db.schedule = {"schema_version": 2, "template": "guard"}
        sync_npc_schedules()
        self.assertIsNone(self.other.db.schedule)
        self.assertFalse(self.other.tags.has(SCHEDULE_TAG))
        self.assertTrue(self.npc.tags.has(SCHEDULE_TAG))
        self.assertIsNotNone(parse_stored_schedule(self.npc))

    @covers_requirement("npc-schedule-model::startup-synchronization-is-idempotent-and-degrades-safely")
    def test_rerunning_sync_is_a_noop_for_valid_schedules(self):
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "guard"})
        sync_npc_schedules()
        stored = self.npc.db.schedule
        tick = self.npc.db.schedule_effective_from_tick
        sync_npc_schedules()
        self.assertEqual(self.npc.db.schedule, stored)
        self.assertEqual(self.npc.db.schedule_effective_from_tick, tick)
        self.assertEqual(len(parse_stored_schedule(self.npc).entries), 3)

    def test_sync_adds_the_tag_to_a_valid_stored_unit_without_one(self):
        self.npc.db.schedule = {"schema_version": 1, "template": "guard"}
        self.npc.db.schedule_effective_from_tick = 0
        sync_npc_schedules()
        self.assertTrue(self.npc.tags.has(SCHEDULE_TAG))

    def test_sync_removes_a_stale_tag_without_a_schedule(self):
        self.npc.tags.add(SCHEDULE_TAG)
        sync_npc_schedules()
        self.assertFalse(self.npc.tags.has(SCHEDULE_TAG))

    def test_sync_degrades_a_schedule_missing_its_effective_tick(self):
        self.npc.db.schedule = {"schema_version": 1, "template": "guard"}
        self.npc.tags.add(SCHEDULE_TAG)
        sync_npc_schedules()
        self.assertIsNone(self.npc.db.schedule)
        self.assertFalse(self.npc.tags.has(SCHEDULE_TAG))

    def test_sync_deactivates_every_schedule_when_the_rulebook_is_broken(self):
        from unittest.mock import patch

        set_npc_schedule(self.npc, {"schema_version": 1, "template": "guard"})
        with patch("world.rules.npc_schedules.get_rulebook", side_effect=ScheduleRulebookError("boom")):
            sync_npc_schedules()
        self.assertFalse(self.npc.tags.has(SCHEDULE_TAG))
        self.assertEqual(self.npc.db.schedule["template"], "guard")


class ScheduleStateWriterGuardTests(unittest.TestCase):
    def _module_source(self):
        from world.rules import npc_schedules

        return inspect.getsource(npc_schedules)

    @covers_requirement("npc-schedule-model::schedule-state-is-a-declared-attribute-contract")
    def test_schedule_state_contract_is_declared_without_a_writer(self):
        source = self._module_source()
        self.assertIn("npc.db.schedule_state", source)
        self.assertNotIn("db.schedule_state =", source)

    def test_npc_typeclass_never_assigns_schedule_state(self):
        from typeclasses import npcs

        self.assertNotIn("db.schedule_state =", inspect.getsource(npcs))


if __name__ == "__main__":
    unittest.main()
