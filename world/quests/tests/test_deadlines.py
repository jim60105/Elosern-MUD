"""Tests for deadline settlement and startup registration (tasks 8.1-8.5)."""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import InstanceRoom, Room
from world.maps.bootstrap import sync_grid
from world.quests.binding import bind_stage_runtime
from world.quests.bootstrap import sync_quest_runtime
from world.quests.deadlines import settle_quest_deadlines
from world.quests.runtime import (
    QuestState,
    accept_quest,
    read_records,
    to_storage,
)
from world.rules.clock import AdvanceSource, get_world_clock, register_event_source
from server.conf.at_server_startstop import at_server_start

from ._fixtures import (
    QuestRegistryIsolation,
    bound_instance_locator,
    defeat,
    quest,
    reach,
    register,
)


class DeadlineSettlementTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="deadline-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.due = register(quest("deadline_due", deadline_hours=2))
        self.open = register(quest("deadline_open", deadline_hours=None))
        self.hours = 3600

    def _accept(self, key: str):
        with patch("world.quests.runtime._current_tick", return_value=0):
            return accept_quest(self.player, key)

    def _settle(self, end: int, start: int = 0):
        return settle_quest_deadlines(start, end)

    def _records(self):
        return [to_storage(record) for record in read_records(self.player)]

    def test_due_quest_fails_once_and_emits_json_safe_event(self):
        record = self._accept(self.due.key)
        self.assertEqual(record.deadline_tick, 2 * self.hours)
        events = self._settle(2 * self.hours)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "failed")
        self.assertEqual(stored["failure_reason"], "deadline_expired")
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.kind, "quest_deadline_expired")
        self.assertEqual(event.due_tick, 2 * self.hours)
        self.assertEqual(
            event.payload,
            {
                "character_id": self.player.pk,
                "quest_id": "deadline_due:1",
                "definition_key": "deadline_due",
            },
        )

    def test_not_due_quest_is_unchanged(self):
        self._accept(self.due.key)
        events = self._settle(2 * self.hours - 1)
        self.assertEqual(self._records()[0]["state"], "in_progress")
        self.assertEqual(events, [])

    @covers_requirement("quest-failure-conditions::due-active-quests-fail-and-release-their-current-instance-pin")
    def test_no_deadline_quest_never_expires(self):
        self._accept(self.open.key)
        self.assertEqual(self._records()[0]["deadline_tick"], None)
        events = self._settle(1_000_000)
        self.assertEqual(self._records()[0]["state"], "in_progress")
        self.assertEqual(events, [])

    def test_terminal_records_are_ignored(self):
        self._accept(self.due.key)
        from world.quests.runtime import abandon_quest

        abandon_quest(self.player, "deadline_due:1")
        events = self._settle(1_000_000)
        self.assertEqual(self._records()[0]["state"], "failed")
        self.assertEqual(self._records()[0]["failure_reason"], "abandoned")
        self.assertEqual(events, [])

    def test_deadline_releases_bound_instance_and_clears_binding(self):
        from world.quests.definitions import QuestStage

        bound_room_def = register(
            quest(
                "deadline_bound_room",
                deadline_hours=1,
                stages=(QuestStage(0, reach(bound_instance_locator())),),
            )
        )
        with patch("world.quests.runtime._current_tick", return_value=0):
            record = accept_quest(self.player, bound_room_def.key)
        room = create_object(InstanceRoom, key="deadline-room")
        bind_stage_runtime(self.player, record.quest_id, room=room)
        self.assertEqual(room.db.pin_reasons, [f"quest:{self.player.pk}:{record.quest_id}:stage:0"])
        events = self._settle(self.hours)
        stored = self._records()[0]
        self.assertEqual(stored["state"], "failed")
        self.assertEqual(stored["stage_room_id"], None)
        self.assertEqual(stored["protected_entity_ids"], [])
        self.assertEqual(room.db.pin_reasons, [])
        self.assertEqual(len(events), 1)

    def test_malformed_character_is_isolated(self):
        bad = create_object(PlayerCharacter, key="bad-deadline")
        good = create_object(PlayerCharacter, key="good-deadline")
        bad.db.quest_log = [{"quest_id": "broken", "definition_key": "??"}]
        with patch("world.quests.runtime._current_tick", return_value=0):
            accept_quest(good, self.due.key)
        before_bad = list(bad.db.quest_log)
        with patch("world.quests.deadlines.log_warn") as logger:
            events = self._settle(2 * self.hours)
        self.assertEqual(logger.call_count, 1)
        self.assertEqual(bad.db.quest_log, before_bad)
        good_log = [to_storage(r) for r in read_records(good)]
        self.assertEqual(good_log[0]["state"], "failed")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload["character_id"], good.pk)

    @covers_requirement("quest-failure-conditions::quest-deadline-settlement-is-registered-from-the-server-startup-composition-root")
    def test_repeated_startup_registration_is_idempotent(self):
        self._accept(self.due.key)
        sync_quest_runtime()
        sync_quest_runtime()
        events = self._settle(2 * self.hours)
        self.assertEqual(len(events), 1)

    def test_stage_order_keeps_deadlines_before_reclamation(self):
        from world.rules.clock import _STAGE_ORDER

        self.assertIn("quest_deadlines", _STAGE_ORDER)
        self.assertIn("instance_reclamation", _STAGE_ORDER)
        self.assertLess(
            _STAGE_ORDER.index("quest_deadlines"),
            _STAGE_ORDER.index("instance_reclamation"),
        )

    def test_server_start_calls_quest_sync_after_map_sync(self):
        source = inspect.getsource(at_server_start)
        self.assertIn("sync_quest_runtime()", source)
        self.assertLess(source.index("sync_wilderness()"), source.index("sync_quest_runtime()"))


class DeadlinePrecedesReclamationTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        create_object(Room, key="Limbo", location=None)
        sync_grid()
        sync_quest_runtime()
        self.player = create_object(PlayerCharacter, key="reclaim-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.hours = 3600

    @covers_requirement("quest-failure-conditions::deadline-failure-precedes-instance-reclamation-in-one-clock-advance")
    def test_due_room_is_unpinned_and_reclaimed_in_one_advance(self):
        from world.quests.definitions import QuestStage

        bound_def = register(
            quest(
                "reclaim_bound",
                deadline_hours=1,
                stages=(QuestStage(0, reach(bound_instance_locator())),),
            )
        )
        with patch("world.quests.runtime._current_tick", return_value=0):
            record = accept_quest(self.player, bound_def.key)
        room = create_object(InstanceRoom, key="reclaim-room")
        bind_stage_runtime(self.player, record.quest_id, room=room)
        room.db.expire_tick = self.hours + 100
        clock = get_world_clock()
        self.assertEqual(clock.tick, 0)
        events = clock.advance(self.hours * 2, AdvanceSource.COMMAND, [self.player])
        kinds = [event.kind for event in events]
        self.assertIn("quest_deadline_expired", kinds)
        self.assertIn("instance_reclaimed", kinds)
        self.assertLess(
            kinds.index("quest_deadline_expired"),
            kinds.index("instance_reclaimed"),
        )
        stored = [to_storage(r) for r in read_records(self.player)][0]
        self.assertEqual(stored["state"], "failed")
        self.assertEqual(stored["failure_reason"], "deadline_expired")
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())


if __name__ == "__main__":
    unittest.main()
