"""Tests for persisted quest records and lifecycle operations (tasks 3.1-3.5)."""

import json
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.quests.catalog import register_catalog
from world.quests.runtime import (
    QuestAlreadyActive,
    QuestDataError,
    QuestNotFound,
    QuestState,
    abandon_quest,
    accept_quest,
    definition_for,
    fail_record,
    from_storage,
    read_records,
    to_storage,
)
from world.quests.transitions import apply_quest_log_replacement

from ._fixtures import QuestRegistryIsolation, quest, register


class RuntimeLifecycleTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="quest-player")
        register_catalog()

    @staticmethod
    def _tick(value: int):
        return patch("world.quests.runtime._current_tick", return_value=value)

    def _accept_deadlined(self, hours: int = 72, tick: int = 1000):
        registered = register(quest(f"deadline_{hours}_{tick}", deadline_hours=hours))
        with self._tick(tick):
            return accept_quest(self.player, registered.key)

    def test_record_round_trips_through_json(self):
        original = from_storage(
            {
                "quest_id": "q:2",
                "definition_key": "introductory_hunt",
                "state": "in_progress",
                "stage_index": 0,
                "stage_progress": 1,
                "deadline_tick": 5000,
                "accepted_tick": 1000,
                "stage_room_id": 42,
                "objective_target_ids": [5, 6],
                "protected_entity_ids": [],
                "failure_reason": None,
            }
        )
        storage = to_storage(original)
        payload = json.dumps(storage)
        rebuilt = from_storage(json.loads(payload))
        self.assertEqual(rebuilt, original)
        for value in storage.values():
            if isinstance(value, list):
                self.assertTrue(all(isinstance(item, int) for item in value))

    def test_from_storage_rejects_malformed_entries(self):
        base = {
            "quest_id": "q",
            "definition_key": "introductory_hunt",
            "state": "in_progress",
            "stage_index": 0,
            "stage_progress": 0,
            "deadline_tick": None,
            "accepted_tick": 0,
            "stage_room_id": None,
            "objective_target_ids": [],
            "protected_entity_ids": [],
            "failure_reason": None,
        }
        malformed = [
            ("missing", lambda d: {k: v for k, v in d.items() if k != "state"}),
            ("unknown", lambda d: {**d, "extra": 1}),
            ("not-dict", lambda d: "oops"),
            ("bad-state", lambda d: {**d, "state": "warped"}),
            ("negative-index", lambda d: {**d, "stage_index": -1}),
            ("bad-room-id", lambda d: {**d, "stage_room_id": "4"}),
            ("non-int-ids", lambda d: {**d, "objective_target_ids": ["5"]}),
            ("overlap", lambda d: {**d, "objective_target_ids": [5], "protected_entity_ids": [5]}),
            ("bad-reason", lambda d: {**d, "failure_reason": 3}),
        ]
        for name, mutate in malformed:
            with self.subTest(name=name):
                with self.assertRaises(QuestDataError):
                    from_storage(mutate(dict(base)))

    def test_unaccepted_definition_has_no_record(self):
        self.assertEqual(self.player.db.quest_log, [])

    def test_missing_definition_is_reported_not_reinterpreted(self):
        record = from_storage(
            {
                "quest_id": "ghost:1",
                "definition_key": "no_such_definition",
                "state": "in_progress",
                "stage_index": 0,
                "stage_progress": 0,
                "deadline_tick": None,
                "accepted_tick": 0,
                "stage_room_id": None,
                "objective_target_ids": [],
                "protected_entity_ids": [],
                "failure_reason": None,
            }
        )
        with self.assertRaises(QuestDataError) as caught:
            definition_for(record)
        self.assertIn("no_such_definition", str(caught.exception))

    def test_malformed_log_fails_any_operation_without_partial_write(self):
        registered = register(quest("malformed_neighbor"))
        accept_quest(self.player, registered.key)
        before = list(self.player.db.quest_log)
        self.player.db.quest_log = [
            {"quest_id": "broken", "state": "in_progress", "definition_key": "??"},
            *before,
        ]
        with self.assertRaises(QuestDataError):
            accept_quest(self.player, registered.key)
        with self.assertRaises(QuestDataError):
            abandon_quest(self.player, f"{registered.key}:1")
        self.assertEqual(self.player.db.quest_log[1:], before)

    def test_first_acceptance_creates_stage_zero_active_record(self):
        registered = register(quest("first_accept"))
        with self._tick(300):
            record = accept_quest(self.player, registered.key)
        self.assertEqual(record.quest_id, "first_accept:1")
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.stage_index, 0)
        self.assertEqual(record.stage_progress, 0)
        self.assertEqual(record.accepted_tick, 300)
        self.assertEqual(
            [entry["quest_id"] for entry in self.player.db.quest_log],
            ["first_accept:1"],
        )

    def test_duplicate_active_acceptance_is_rejected(self):
        registered = register(quest("duplicate_active"))
        accept_quest(self.player, registered.key)
        before = list(self.player.db.quest_log)
        with self.assertRaises(QuestAlreadyActive):
            accept_quest(self.player, registered.key)
        self.assertEqual(self.player.db.quest_log, before)

    def test_terminal_quest_may_be_retried_deterministically(self):
        registered = register(quest("retryable"))
        record = accept_quest(self.player, registered.key)
        abandoned = abandon_quest(self.player, record.quest_id)
        self.assertEqual(abandoned.state, QuestState.FAILED)
        retried = accept_quest(self.player, registered.key)
        self.assertEqual(retried.quest_id, "retryable:2")
        self.assertEqual(retried.state, QuestState.IN_PROGRESS)
        states = {entry["quest_id"]: entry for entry in self.player.db.quest_log}
        self.assertEqual(states["retryable:1"]["state"], "failed")
        self.assertEqual(states["retryable:2"]["state"], "in_progress")

    def test_explicit_deadline_is_converted_to_ticks(self):
        record = self._accept_deadlined(hours=72, tick=1000)
        self.assertEqual(
            record.deadline_tick,
            1000 + 72 * 3600,
        )

    def test_no_deadline_definition_remains_without_a_deadline(self):
        registered = register(quest("no_deadline", deadline_hours=None))
        record = accept_quest(self.player, registered.key)
        self.assertIsNone(record.deadline_tick)

    def test_unknown_quest_id_raises_not_found_without_mutation(self):
        before = list(self.player.db.quest_log)
        with self.assertRaises(QuestNotFound):
            abandon_quest(self.player, "nope:1")
        self.assertEqual(self.player.db.quest_log, before)

    def test_abandonment_records_failure_and_clears_bindings(self):
        registered = register(quest("abandonable"))
        record = accept_quest(self.player, registered.key)
        bound = from_storage(
            {
                **to_storage(record),
                "stage_room_id": 77,
                "objective_target_ids": [5, 6],
                "protected_entity_ids": [9],
            }
        )
        apply_quest_log_replacement(self.player, [bound])
        failed = abandon_quest(self.player, "abandonable:1")
        self.assertEqual(failed.state, QuestState.FAILED)
        self.assertEqual(failed.failure_reason, "abandoned")
        self.assertIsNone(failed.stage_room_id)
        self.assertEqual(failed.objective_target_ids, ())
        self.assertEqual(failed.protected_entity_ids, ())
        stored = self.player.db.quest_log[0]
        self.assertEqual(stored["failure_reason"], "abandoned")

    def test_repeated_abandonment_is_harmless(self):
        registered = register(quest("abandon_twice"))
        record = accept_quest(self.player, registered.key)
        first = abandon_quest(self.player, record.quest_id)
        before = list(self.player.db.quest_log)
        second = abandon_quest(self.player, record.quest_id)
        self.assertIs(first.state, QuestState.FAILED)
        self.assertEqual(second, first)
        self.assertEqual(self.player.db.quest_log, before)

    def test_fail_record_and_storage_match(self):
        from_world = from_storage(
            {
                "quest_id": "sample:1",
                "definition_key": "introductory_hunt",
                "state": "in_progress",
                "stage_index": 0,
                "stage_progress": 0,
                "deadline_tick": None,
                "accepted_tick": 0,
                "stage_room_id": None,
                "objective_target_ids": [],
                "protected_entity_ids": [],
                "failure_reason": None,
            }
        )
        failed = fail_record(from_world, "deadline_expired")
        self.assertEqual(failed.state, QuestState.FAILED)
        self.assertEqual(failed.failure_reason, "deadline_expired")
        self.assertEqual(to_storage(failed)["state"], "failed")
        self.assertEqual(read_records(self.player), [])

    def test_read_records_returns_empty_for_empty_log(self):
        self.assertEqual(read_records(self.player), [])

    def test_duplicate_quest_ids_are_rejected(self):
        registered = register(quest("duplicate_ids"))
        accept_quest(self.player, registered.key)
        log = list(self.player.db.quest_log)
        self.player.db.quest_log = [log[0], dict(log[0])]
        with self.assertRaises(QuestDataError):
            read_records(self.player)
        with self.assertRaises(QuestDataError):
            abandon_quest(self.player, f"{registered.key}:1")

    def test_active_record_with_out_of_range_stage_is_rejected(self):
        registered = register(quest("stale_stage"))
        record = accept_quest(self.player, registered.key)
        stale = {
            **to_storage(record),
            "stage_index": 5,
        }
        apply_quest_log_replacement(self.player, [from_storage(stale)])
        with self.assertRaises(QuestDataError):
            read_records(self.player)
        with self.assertRaises(QuestDataError):
            abandon_quest(self.player, f"{registered.key}:1")

    def test_terminal_record_with_residual_bindings_is_rejected(self):
        registered = register(quest("terminal_bindings"))
        record = accept_quest(self.player, registered.key)
        residual = {
            **to_storage(record),
            "state": "completed",
            "stage_room_id": 9,
            "objective_target_ids": [5],
        }
        apply_quest_log_replacement(self.player, [from_storage(residual)])
        with self.assertRaises(QuestDataError):
            read_records(self.player)

    def test_failed_record_without_reason_is_rejected(self):
        registered = register(quest("reasonless"))
        record = accept_quest(self.player, registered.key)
        reasonless = {**to_storage(record), "state": "failed", "failure_reason": None}
        apply_quest_log_replacement(self.player, [from_storage(reasonless)])
        with self.assertRaises(QuestDataError):
            read_records(self.player)

    def test_non_dict_log_entry_is_a_named_error(self):
        self.player.db.quest_log = ["oops-not-a-dict"]
        with self.assertRaises(QuestDataError):
            read_records(self.player)


if __name__ == "__main__":
    unittest.main()