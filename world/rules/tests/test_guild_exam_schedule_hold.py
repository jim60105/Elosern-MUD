"""Synthetic examination hold/replay behavior with real Exit traversal."""

from types import SimpleNamespace
from unittest.mock import patch

from django.db import transaction
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.exits import Exit
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules import clock as clock_module
from world.rules.clock import get_world_clock, settle_combat_result
from world.rules.exam_schedule_holds import (
    HOLD_ATTRIBUTE, ExamScheduleHoldError, begin_exam_schedule_hold,
    read_exam_schedule_hold, release_exam_schedule_hold,
    restore_exam_schedule_hold_surfaces, snapshot_exam_schedule_hold_surfaces,
)
from world.rules.npc_schedules import (
    ScheduleEntry, ScheduleRulebook, ScheduleTemplate, register_npc_schedules,
    set_npc_schedule, settle_npc_schedules,
)
from world.tests.raw_attributes import raw_attribute_value

DAY = 86400


class ExamScheduleHoldTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.home = create_object(Room, key="hold_home")
        self.work = create_object(Room, key="hold_work")
        self.exit = create_object(Exit, key="leave", location=self.home, destination=self.work)
        create_object(Exit, key="return", location=self.work, destination=self.home)
        self.host = create_object(NPC, key="exam_host", location=self.home)
        self.other = create_object(NPC, key="other_worker", location=self.home)
        self.clock = get_world_clock()
        self.clock.tick = DAY - 5
        self.clock._persist(self.clock.tick)
        book = ScheduleRulebook(1, ("duty", "busy", "resting"), (
            ScheduleTemplate("hold_role", (
                ScheduleEntry(DAY, "move", target="hold_work"),
                ScheduleEntry(DAY, "state", state="busy"),
                ScheduleEntry(2 * DAY, "move", target="hold_home"),
            ), default_state="duty", cycle_days=7),
        ))
        for target, kwargs in (
            ("world.rules.npc_schedules.get_rulebook", {"return_value": book}),
            ("world.rules.npc_schedules._resolve_destination", {
                "side_effect": {"hold_work": self.work, "hold_home": self.home}.get,
            }),
        ):
            mock = patch(target, **kwargs)
            mock.start()
            self.addCleanup(mock.stop)
        source_patch = patch.dict(clock_module._EVENT_SOURCES, {}, clear=True)
        source_patch.start()
        self.addCleanup(source_patch.stop)
        register_npc_schedules()
        for npc in (self.host, self.other):
            set_npc_schedule(npc, {"schema_version": 1, "template": "hold_role"})
        self.host.db.schedule_state = "duty"

    def _begin(self, exam_id="synthetic_exam"):
        return begin_exam_schedule_hold(self.host, exam_id, get_world_clock().tick)

    def _settle(self, seconds=6):
        return settle_combat_result(SimpleNamespace(total_seconds=seconds), ())

    def _schedule_events(self, events):
        return [event for event in events if event.kind in {
            "npc_departed", "npc_arrived", "npc_state_changed",
        }]

    def _snapshot(self):
        return (
            self.host.location.pk, self.host.db.schedule_state,
            raw_attribute_value(self.host, HOLD_ATTRIBUTE),
            tuple(obj.pk for obj in self.home.contents),
            tuple(obj.pk for obj in self.work.contents),
            get_world_clock().tick,
        )

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_weekly_departure_after_synthetic_terminal_sequences(self):
        # Each sequence models the predecessor API contract; production terminal
        # wiring belongs to persistent-guild-exam-lifecycle.
        for terminal in ("pass", "fail", "flee", "invalid_recovery"):
            with self.subTest(terminal=terminal):
                tick = get_world_clock().tick
                if tick != DAY - 5:
                    self.clock._persist(DAY - 5)
                for npc in (self.host, self.other):
                    npc.location = self.home
                    npc.db.schedule_state = "duty"
                self.host.attributes.remove(HOLD_ATTRIBUTE)
                self._begin(terminal)
                self.host.db.schedule_state = "resting"  # synthetic active exam state
                with patch.object(self.exit, "at_traverse", wraps=self.exit.at_traverse) as traversal:
                    events = self._schedule_events(self._settle())
                    self.assertEqual(traversal.call_count, 1)  # unrelated worker
                    self.assertEqual(self.host.location, self.home)
                    self.assertEqual(self.host.db.schedule_state, "resting")
                    self.assertEqual([event.payload["npc_id"] for event in events], [self.other.pk] * 3)
                    self.assertEqual([event.kind for event in events],
                                     ["npc_departed", "npc_arrived", "npc_state_changed"])
                    self.assertEqual(self.other.location, self.work)
                    self.host.db.schedule_state = "duty"  # lifecycle restores before release
                    released = release_exam_schedule_hold(self.host, terminal, DAY + 1)
                    self.assertEqual(traversal.call_count, 2)
                    self.assertEqual([event.kind for event in released],
                                     ["npc_departed", "npc_arrived", "npc_state_changed"])
                    self.assertEqual([event.due_tick for event in released], [DAY] * 3)
                    self.assertEqual(self.host.location, self.work)
                    self.assertEqual(self.host.db.schedule_state, "busy")
                    hold = read_exam_schedule_hold(self.host).hold
                    self.assertTrue(hold.released)
                    self.assertEqual(hold.consumed_through, (DAY, 1))
                    self.assertEqual(get_world_clock().tick, DAY + 1)
                    self.assertEqual(release_exam_schedule_hold(self.host, terminal, DAY + 1), [])
                    self.assertEqual(traversal.call_count, 2)
                    self.assertEqual(get_world_clock().tick, DAY + 1)

    def test_pending_and_completed_release_survive_cold_cache(self):
        self._begin()
        self._settle()
        before = self._snapshot()
        self.host.attributes.reset_cache()
        self.assertEqual(self._snapshot(), before)
        self.assertFalse(read_exam_schedule_hold(self.host).hold.released)
        self.assertEqual(len(release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1)), 3)
        self.host.attributes.reset_cache()
        completed = self._snapshot()
        self.assertEqual(release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1), [])
        self.assertEqual(self._snapshot(), completed)
        self.assertTrue(read_exam_schedule_hold(self.host).hold.released)

    def test_marker_persistence_failure_restores_storage_location_and_caches(self):
        self._begin()
        self._settle()
        before = self._snapshot()
        original = self.host.attributes.add

        def fail_marker(key, value, *args, **kwargs):
            original(key, value, *args, **kwargs)
            if key == HOLD_ATTRIBUTE and value["released"]:
                raise RuntimeError("release marker persistence fault")

        with patch.object(self.host.attributes, "add", side_effect=fail_marker):
            with self.assertRaisesRegex(RuntimeError, "persistence fault"):
                release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1)
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(ObjectDB.objects.get(pk=self.host.pk).db_location_id, self.home.pk)
        self.assertEqual(len(release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1)), 3)

    def test_outer_lifecycle_rollback_uses_explicit_snapshot(self):
        self._begin()
        self._settle()
        before = self._snapshot()
        snapshot = snapshot_exam_schedule_hold_surfaces(self.host)
        try:
            with transaction.atomic():
                release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1)
                raise RuntimeError("outer lifecycle failure")
        except RuntimeError:
            restore_exam_schedule_hold_surfaces(self.host, snapshot)
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(len(release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1)), 3)

    def test_clock_persistence_failure_restores_held_interval_and_other_npc(self):
        self._begin()
        before = self._snapshot()
        clock = get_world_clock()

        def fail_tick(tick):
            clock._script.db.tick = tick
            raise RuntimeError("clock persist fault")

        with patch.object(clock, "_persist", side_effect=fail_tick):
            with self.assertRaisesRegex(RuntimeError, "clock persist fault"):
                clock.advance(6, clock_module.AdvanceSource.COMBAT, ())
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(self.other.location, self.home)
        self.assertEqual(read_exam_schedule_hold(self.host).hold.held_through_tick, DAY - 5)

    def test_hold_extension_failure_aborts_clock_settlement(self):
        self._begin()
        before = self._snapshot()
        original = self.host.attributes.add

        def fail_extension(key, value, *args, **kwargs):
            original(key, value, *args, **kwargs)
            if key == HOLD_ATTRIBUTE and value["held_through_tick"] > DAY - 5:
                raise RuntimeError("extension fault")

        with patch.object(self.host.attributes, "add", side_effect=fail_extension):
            with self.assertRaisesRegex(RuntimeError, "extension fault"):
                self._settle()
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(self.other.location, self.home)

    def test_ownership_timing_and_read_rejection_are_nonmutating(self):
        self._begin()
        before = self._snapshot()
        self.assertEqual(self._begin(), read_exam_schedule_hold(self.host).hold)
        for operation in (
            lambda: begin_exam_schedule_hold(self.host, "foreign", DAY - 5),
            lambda: release_exam_schedule_hold(self.host, "foreign", DAY - 5),
            lambda: release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1),
            lambda: release_exam_schedule_hold(self.host, "synthetic_exam", True),
        ):
            with self.assertRaises(ExamScheduleHoldError):
                operation()
            self.assertEqual(self._snapshot(), before)
        self.host.attributes.remove(HOLD_ATTRIBUTE)
        for tick in (DAY - 6, DAY - 4, True, -1):
            with self.assertRaises(ExamScheduleHoldError):
                begin_exam_schedule_hold(self.host, "new", tick)
        self.assertTrue(read_exam_schedule_hold(self.host).known)
        self.assertIsNone(read_exam_schedule_hold(self.host).hold)

    def test_corrupt_hold_defers_host_and_exposes_named_indeterminate_read(self):
        self._begin()
        raw = dict(self.host.db.exam_schedule_hold)
        for replacement in (None, {}, {**raw, "host_id": self.other.pk},
                            {**raw, "consumed_through": (DAY + 5, 1)},
                            {**raw, "consumed_through": (DAY - 5, 47)},
                            {**raw, "held_through_tick": True}):
            self.host.attributes.add(HOLD_ATTRIBUTE, replacement)
            before = self._snapshot()
            result = read_exam_schedule_hold(self.host)
            self.assertFalse(result.known)
            self.assertIsNotNone(result.reason)
            self.assertEqual(self._snapshot(), before)
            events = settle_npc_schedules(DAY - 5, DAY + 1)
            self.assertNotIn(self.host.pk, [event.payload["npc_id"] for event in events])
            self.assertEqual(self.host.location, self.home)
            with self.assertRaises(ExamScheduleHoldError):
                release_exam_schedule_hold(self.host, "synthetic_exam", DAY - 5)

    def test_locked_exit_is_consumed_and_same_tick_state_still_settles(self):
        self._begin()
        self._settle()
        self.exit.locks.add("traverse:false()")
        events = release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1)
        self.assertEqual([event.kind for event in events], ["npc_state_changed"])
        self.assertEqual(self.host.location, self.home)
        self.assertEqual(self.host.db.schedule_state, "busy")
        self.exit.locks.add("traverse:true()")
        self.assertEqual(release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1), [])

    def test_silencing_precedes_hold_extension_and_release_skips_occurrences(self):
        self._begin()
        with patch("world.rules.service_gate.schedule_silenced",
                   side_effect=lambda npc: npc is self.host):
            events = self._schedule_events(self._settle())
            self.assertNotIn(self.host.pk, [event.payload["npc_id"] for event in events])
            self.assertEqual(read_exam_schedule_hold(self.host).hold.held_through_tick, DAY - 5)
            self.assertEqual(release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1), [])
        self.assertEqual(self.host.location, self.home)
        self.assertEqual(self.host.db.schedule_state, "duty")
        self.assertTrue(read_exam_schedule_hold(self.host).hold.released)

    def test_indeterminate_schedule_keeps_pending_hold_for_repair(self):
        self._begin()
        self._settle()
        self.host.db.schedule = {"schema_version": 999}
        before = self._snapshot()
        with self.assertRaisesRegex(ExamScheduleHoldError, "schedule is indeterminate"):
            release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1)
        self.assertEqual(self._snapshot(), before)

    def test_effective_from_excludes_past_occurrences_and_orders_multiple_cycles(self):
        self._begin()
        self.clock._persist(8 * DAY + 1)
        events = release_exam_schedule_hold(self.host, "synthetic_exam", 8 * DAY + 1)
        self.assertEqual([(event.due_tick, event.kind) for event in events], [
            (DAY, "npc_departed"), (DAY, "npc_arrived"), (DAY, "npc_state_changed"),
            (2 * DAY, "npc_departed"), (2 * DAY, "npc_arrived"),
            (8 * DAY, "npc_departed"), (8 * DAY, "npc_arrived"), (8 * DAY, "npc_state_changed"),
        ])
        self.assertEqual(read_exam_schedule_hold(self.host).hold.consumed_through, (8 * DAY, 1))
        self.assertEqual(get_world_clock().tick, 8 * DAY + 1)

    def test_same_tick_assignment_release_is_not_replayed_by_next_advance(self):
        self.clock._persist(DAY)
        set_npc_schedule(self.host, {"schema_version": 1, "template": "hold_role"})
        self._begin()
        released = release_exam_schedule_hold(self.host, "synthetic_exam", DAY)
        self.assertEqual(len(released), 3)
        self.assertEqual(get_world_clock().tick, DAY)
        events = self._settle(1)
        self.assertNotIn(self.host.pk, [event.payload["npc_id"] for event in events])
        self.assertEqual(get_world_clock().tick, DAY + 1)

    def test_reassignment_effective_from_does_not_replay_pre_assignment_entries(self):
        self.clock._persist(DAY + 1)
        set_npc_schedule(self.host, {"schema_version": 1, "template": "hold_role"})
        self._begin()
        self.clock._persist(2 * DAY)
        events = release_exam_schedule_hold(self.host, "synthetic_exam", 2 * DAY)
        # The prior departure was before effective-from, so the return finds
        # the host already home and is an ordinary skipped traversal.
        self.assertEqual(events, [])
        self.assertEqual(self.host.location, self.home)
        self.assertEqual(self.host.db.schedule_state, "duty")
        self.assertEqual(read_exam_schedule_hold(self.host).hold.consumed_through, (2 * DAY, 2))

    def test_vetoed_traversal_is_consumed_without_blocking_state(self):
        self._begin()
        self._settle()
        with patch.object(self.host, "at_pre_move", return_value=False):
            events = release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1)
        self.assertEqual([event.kind for event in events], ["npc_state_changed"])
        self.assertEqual(self.host.location, self.home)
        self.assertEqual(self.host.db.schedule_state, "busy")
        self.assertEqual(release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1), [])

    def test_boundary_events_wait_for_outer_commit_and_disappear_on_rollback(self):
        with patch("world.rules.exam_schedule_holds.log_info") as log:
            with self.captureOnCommitCallbacks(execute=True):
                self._begin()
                self._settle()
                release_exam_schedule_hold(self.host, "synthetic_exam", DAY + 1)
                self.assertFalse(log.called)
            self.assertEqual([call.args[0] for call in log.call_args_list], [
                "exam_schedule_hold_started", "exam_schedule_hold_extended",
                "exam_schedule_hold_released",
            ])
            self.assertTrue(all(call.kwargs["context"]["host_id"] == self.host.pk
                                for call in log.call_args_list))
            log.reset_mock()
            snapshot = snapshot_exam_schedule_hold_surfaces(self.host)
            with self.captureOnCommitCallbacks(execute=True):
                try:
                    with transaction.atomic():
                        begin_exam_schedule_hold(self.host, "later_exam", DAY + 1)
                        raise RuntimeError("rollback")
                except RuntimeError:
                    restore_exam_schedule_hold_surfaces(self.host, snapshot)
            self.assertFalse(log.called)
