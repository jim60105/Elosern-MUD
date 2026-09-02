"""Tests for deadline settlement and startup registration (tasks 8.1-8.5)."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

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

from ._fixtures import (
    QuestRegistryIsolation,
    bound_instance_locator,
    defeat,
    quest,
    reach,
    register,
)


class DeadlineSettlementTests(QuestRegistryIsolation, EvenniaTestCase):
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
        # The quest runtime sync must run after the lore/map syncs but before
        # session restoration and wilderness reconciliation, so a recovery
        # advance settles with ``quest_deadlines`` registered
        # (fix-startup-clock-source-order D1).
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        self.assertIn("sync_quest_runtime", STARTUP_STEP_ORDER)
        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_all"),
            STARTUP_STEP_ORDER.index("sync_quest_runtime"),
        )
        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_grid"),
            STARTUP_STEP_ORDER.index("sync_quest_runtime"),
        )
        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_quest_runtime"),
            STARTUP_STEP_ORDER.index("sync_wilderness"),
        )


class StartupRecoveryDeadlineTests(QuestRegistryIsolation, EvenniaTest):
    """A startup recovery advance fails quests due inside its window (F8)."""

    def setUp(self):
        super().setUp()
        from typeclasses.monsters import Monster

        self.player = create_object(PlayerCharacter, key="deadline-recovery-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.monster = create_object(Monster, key="荒原野豬", location=self.room1)
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier("floor")
        self.due = register(quest("recovery_due", deadline_hours=1))
        self.hours = 3600

    @covers_requirement("player-combat-session::startup-combat-restoration-advances-time-only-after-every-deterministic-clock-source-is-registered")
    def test_recovery_advance_fails_a_quest_deadline_inside_its_window(self):
        from dataclasses import replace

        from world.rules.clock import get_world_clock
        from world.rules.combat_session import _persist, engage, read_session
        from world.rules.guild_economy import restore_persisted_sessions

        with patch("world.quests.runtime._current_tick", return_value=0):
            record = accept_quest(self.player, self.due.key)
        self.assertEqual(record.deadline_tick, self.hours)
        # A well-formed hostile session whose accumulated rounds cross the
        # deadline tick (600 rounds x 6 s = 3600 s), with its recorded enemy
        # gone: restoration terminates it as invalid and settles the window.
        engage(self.player, self.monster)
        session = read_session(self.player)
        _persist(self.player, replace(session, rounds_elapsed=600))
        self.monster.delete()

        # The deterministic startup sequence registers the quest deadline
        # source before session restoration (fix-startup-clock-source-order
        # D1), so the deadline due inside the recovery window fails.
        sync_quest_runtime()
        restore_persisted_sessions()

        stored = [to_storage(r) for r in read_records(self.player)][0]
        self.assertEqual(stored["state"], "failed")
        self.assertEqual(stored["failure_reason"], "deadline_expired")
        self.assertEqual(get_world_clock().tick, self.hours)


class DeadlinePrecedesReclamationTests(QuestRegistryIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
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


class DeadlineRollbackCacheTests(QuestRegistryIsolation, EvenniaTestCase):
    """A rolled-back advance restores quest logs and room pins (F5).

    ``WorldClock.advance`` snapshots every durable surface the
    ``quest_deadlines`` contract declares -- the player's ``quest_log`` and
    each bound room's ``pin_reasons`` -- and restores them after a later
    stage or the final persist fails, so the in-process cache never serves
    state the rolled-back transaction did not commit.
    """

    def setUp(self):
        super().setUp()
        import world.rules.clock as clock_module

        self.player = create_object(PlayerCharacter, key="deadline-rollback-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.hours = 3600
        self.due = register(quest("deadline_rollback_due", deadline_hours=2))
        self._sources = dict(clock_module._EVENT_SOURCES)

    def tearDown(self):
        import world.rules.clock as clock_module

        clock_module._EVENT_SOURCES.clear()
        clock_module._EVENT_SOURCES.update(self._sources)
        super().tearDown()

    def _accept_bound(self):
        from world.quests.definitions import QuestStage

        bound_def = register(
            quest(
                "deadline_rollback_bound",
                deadline_hours=2,
                stages=(QuestStage(0, reach(bound_instance_locator())),),
            )
        )
        with patch("world.quests.runtime._current_tick", return_value=0):
            record = accept_quest(self.player, bound_def.key)
        room = create_object(InstanceRoom, key="deadline-rollback-room")
        bind_stage_runtime(self.player, record.quest_id, room=room)
        return room

    def _raw_attribute(self, obj, key):
        row = (
            obj.db_attributes.through.objects.filter(
                objectdb_id=obj.pk, attribute__db_key=key
            )
            .values_list("attribute__db_value", flat=True)
            .first()
        )
        return None if row is None else row

    @covers_requirement("world-clock::a-rolled-back-advance-restores-every-callback-owned-surface-not-just-caller-entities")
    def test_later_stage_failure_restores_quest_log_and_pins(self):
        from world.maps.instance import snapshot_instance_reclamation_surfaces
        from world.quests.bootstrap import sync_quest_runtime
        from world.rules.clock import get_world_clock, register_event_source

        room = self._accept_bound()
        before_log = list(self.player.db.quest_log)
        before_pins = list(room.db.pin_reasons)
        sync_quest_runtime()

        def raising_settle(start_tick, end_tick):
            raise RuntimeError("simulated later-stage failure")

        register_event_source(
            "instance_reclamation",
            raising_settle,
            snapshot_instance_reclamation_surfaces,
        )
        clock = get_world_clock()
        before_tick = clock.tick
        with self.assertRaises(RuntimeError):
            clock.advance(2 * self.hours, AdvanceSource.SKIP, [self.player])

        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertEqual(self.player.db.quest_log, before_log)
        self.assertEqual(self._raw_attribute(self.player, "quest_log"), before_log)
        self.assertEqual(room.db.pin_reasons, before_pins)
        self.assertEqual(self._raw_attribute(room, "pin_reasons"), before_pins)

    @covers_requirement("world-clock::a-rolled-back-advance-restores-every-callback-owned-surface-not-just-caller-entities")
    def test_failing_final_persist_restores_quest_log_and_pins(self):
        from evennia.utils.search import search_script
        from world.quests.bootstrap import sync_quest_runtime
        from world.rules.clock import get_world_clock

        room = self._accept_bound()
        before_log = list(self.player.db.quest_log)
        before_pins = list(room.db.pin_reasons)
        sync_quest_runtime()
        clock = get_world_clock()
        before_tick = clock.tick
        script = search_script("world_clock")[0]

        def failing_persist(tick):
            script.db.tick = tick
            raise RuntimeError("simulated persist failure")

        clock._persist = failing_persist
        with self.assertRaises(RuntimeError):
            clock.advance(2 * self.hours, AdvanceSource.SKIP, [self.player])

        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(script.db.tick, before_tick)
        self.assertEqual(self.player.db.quest_log, before_log)
        self.assertEqual(self._raw_attribute(self.player, "quest_log"), before_log)
        self.assertEqual(room.db.pin_reasons, before_pins)
        self.assertEqual(self._raw_attribute(room, "pin_reasons"), before_pins)

    @covers_requirement("world-clock::advance-persists-the-tick-and-entity-state-atomically")
    def test_successful_advance_with_a_due_deadline_still_commits(self):
        from world.quests.bootstrap import sync_quest_runtime
        from world.rules.clock import get_world_clock

        room = self._accept_bound()
        sync_quest_runtime()
        clock = get_world_clock()
        before_tick = clock.tick
        events = clock.advance(2 * self.hours, AdvanceSource.SKIP, [self.player])
        self.assertTrue(
            any(event.kind == "quest_deadline_expired" for event in events)
        )
        stored = [to_storage(record) for record in read_records(self.player)][0]
        self.assertEqual(stored["state"], "failed")
        self.assertEqual(stored["failure_reason"], "deadline_expired")
        self.assertEqual(stored["stage_room_id"], None)
        self.assertEqual(room.db.pin_reasons, [])
        self.assertEqual(clock.tick, before_tick + 2 * self.hours)
        self.assertEqual(get_world_clock().tick, before_tick + 2 * self.hours)
        self.assertEqual(self._raw_attribute(self.player, "quest_log"), self.player.db.quest_log)


if __name__ == "__main__":
    unittest.main()
