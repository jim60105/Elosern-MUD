"""NPC schedule runtime tests: settlement, movement, events, gates, registration.

Covers the ``npc-schedule-runtime`` change: the ``npc_schedules`` clock
source, due state/move settlement with boundary arithmetic and deterministic
ordering, JSON-safe events, per-entry failure isolation, the non-player
movement no-ops, mid-day assignment, and the interaction gate's core contract
(tasks 1.x, 2.1, 3.1-3.5, 3.7). Surface-level gate tests live beside their
surfaces (command tests, webclient action tests, typeclass seam tests).
"""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, Room
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.clock import AdvanceSource, ScheduledEvent, get_world_clock
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.rules.npc_schedules import (
    SCHEDULE_BLOCKED_REASON,
    ScheduleError,
    _INTERACTION_KINDS,
    interaction_reason,
    set_npc_schedule,
    settle_npc_schedules,
    sync_npc_schedules,
)

DAY_SECONDS = 86400


class InteractionReasonTests(unittest.TestCase):
    def _npc(self, state):
        return SimpleNamespace(db=SimpleNamespace(schedule_state=state), key="npc")

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_kind_vocabulary_declares_talk_engage_shop_and_guild(self):
        self.assertEqual(
            _INTERACTION_KINDS, frozenset({"talk", "engage", "service_shop", "service_guild"})
        )

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_unknown_kind_fails_loudly(self):
        with self.assertRaises(ScheduleError):
            interaction_reason(self._npc("busy"), "teleport")

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_none_state_never_blocks_any_kind(self):
        for kind in _INTERACTION_KINDS:
            with self.subTest(kind=kind):
                self.assertIsNone(interaction_reason(self._npc(None), kind))

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_duty_state_never_blocks(self):
        for kind in _INTERACTION_KINDS:
            with self.subTest(kind=kind):
                self.assertIsNone(interaction_reason(self._npc("duty"), kind))

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_and_resting_block_every_kind_with_the_stable_reason(self):
        for state in ("busy", "resting"):
            for kind in _INTERACTION_KINDS:
                with self.subTest(state=state, kind=kind):
                    self.assertEqual(
                        interaction_reason(self._npc(state), kind),
                        SCHEDULE_BLOCKED_REASON,
                    )

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_engage_is_declared_and_requires_no_engagement_surface_gate(self):
        # The engagement surface rejects non-hostile targets before any
        # schedule check, so ``engage`` needs no gate call there; the kind is
        # carried for a future NPC-combat change. The engagement surface's
        # NOT_HOSTILE rejection is asserted by its own combat tests.
        self.assertIn("engage", _INTERACTION_KINDS)
        from world.rules.combat_session import SessionReason

        self.assertIsNotNone(SessionReason.NOT_HOSTILE)


class SettlementStateEntryTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object(NPC, key="巡邏守衛", location=self.room1)

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_due_state_entry_updates_state_and_emits_event_with_payload(self):
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 50400, "kind": "state", "state": "resting"}
                ],
            },
        )
        events = settle_npc_schedules(0, DAY_SECONDS)
        self.assertEqual(self.npc.db.schedule_state, "resting")
        self.assertEqual(
            events,
            [
                ScheduledEvent(
                    "npc_state_changed",
                    50400,
                    {
                        "npc_id": int(self.npc.pk),
                        "npc": "巡邏守衛",
                        "state": "resting",
                    },
                )
            ],
        )

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_npc_without_a_schedule_settles_to_nothing(self):
        before_location = self.npc.location
        events = settle_npc_schedules(0, DAY_SECONDS)
        self.assertEqual(events, [])
        self.assertIs(self.npc.location, before_location)
        self.assertIsNone(self.npc.db.schedule_state)


class SettlementMoveEntryTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.north_gate = AnchorRoom.create(key="北門", xyz=(9, 9, "test_map"))[0]
        self.north_gate.db.anchor_key = "north_gate"
        self.barracks = AnchorRoom.create(key="營房", xyz=(9, 10, "test_map"))[0]
        self.barracks.db.anchor_key = "barracks"
        self.door = create_object(
            Exit, key="門", location=self.north_gate, destination=self.barracks
        )
        self.npc = create_object(NPC, key="巡邏守衛", location=self.north_gate)

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_due_move_entry_relocates_along_a_real_exit_and_emits_events(self):
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "move", "target": "barracks"}
                ],
            },
        )
        events = settle_npc_schedules(0, DAY_SECONDS)
        self.assertIs(self.npc.location, self.barracks)
        self.assertEqual(
            events,
            [
                ScheduledEvent(
                    "npc_departed",
                    21600,
                    {
                        "npc_id": int(self.npc.pk),
                        "npc": "巡邏守衛",
                        "from": "北門",
                    },
                ),
                ScheduledEvent(
                    "npc_arrived",
                    21600,
                    {
                        "npc_id": int(self.npc.pk),
                        "npc": "巡邏守衛",
                        "to": "營房",
                    },
                ),
            ],
        )

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_move_success_writes_the_templates_default_state(self):
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "guard"})
        # The guard template's first move (21600, north_gate) is skipped: the
        # NPC is already at north_gate. The 50400 state entry and the 64800
        # move to barracks are due later the same day; the move must succeed
        # and rewrite the template's default_state (duty).
        events = settle_npc_schedules(0, DAY_SECONDS)
        self.assertIs(self.npc.location, self.barracks)
        self.assertEqual(self.npc.db.schedule_state, "duty")
        self.assertEqual(
            [event.kind for event in events],
            ["npc_state_changed", "npc_departed", "npc_arrived"],
        )
        self.assertEqual(
            [event.due_tick for event in events], [50400, 64800, 64800]
        )

    @covers_requirement("npc-schedule-runtime::npc-movement-through-settlement-never-charges-the-clock-records-map-knowledge")
    def test_settled_move_does_not_advance_the_clock(self):
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "move", "target": "barracks"}
                ],
            },
        )
        before = get_world_clock().tick
        settle_npc_schedules(0, DAY_SECONDS)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("npc-schedule-runtime::npc-movement-through-settlement-never-charges-the-clock-records-map-knowledge")
    def test_settled_move_records_no_map_knowledge(self):
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "move", "target": "barracks"}
                ],
            },
        )
        from world.rules.map_knowledge import KNOWLEDGE_ATTR

        settle_npc_schedules(0, DAY_SECONDS)
        self.assertIsNone(self.char1.attributes.get(KNOWLEDGE_ATTR))
        self.assertIs(self.npc.location, self.barracks)

    @covers_requirement("npc-schedule-runtime::npc-movement-through-settlement-never-charges-the-clock-records-map-knowledge")
    def test_settled_move_triggers_no_companion_follow(self):
        from world.rules.party import join_party

        companion = create_object(NPC, key="隨從", location=self.north_gate)
        self.char1.location = self.north_gate
        join_party(companion, self.char1)
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "move", "target": "barracks"}
                ],
            },
        )
        settle_npc_schedules(0, DAY_SECONDS)
        self.assertIs(self.npc.location, self.barracks)
        self.assertIs(companion.location, self.north_gate)

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_dbref_target_override_resolves_directly(self):
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {
                        "tick_offset": 21600,
                        "kind": "move",
                        "target": f"#{int(self.barracks.id)}",
                    }
                ],
            },
        )
        settle_npc_schedules(0, DAY_SECONDS)
        self.assertIs(self.npc.location, self.barracks)


class SettlementFailureIsolationTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.north_gate = AnchorRoom.create(key="北門", xyz=(9, 9, "test_map"))[0]
        self.north_gate.db.anchor_key = "north_gate"
        self.locked_post = AnchorRoom.create(key="鎖守點", xyz=(9, 11, "test_map"))[0]
        self.locked_post.db.anchor_key = "locked_post"
        self.barracks = AnchorRoom.create(key="營房", xyz=(9, 10, "test_map"))[0]
        self.barracks.db.anchor_key = "barracks"
        self.locked_npc = create_object(NPC, key="受阻守衛", location=self.locked_post)
        self.free_npc = create_object(NPC, key="自由守衛", location=self.north_gate)

    @covers_requirement("npc-schedule-runtime::a-failed-entry-settles-as-a-per-entry-skip-without-blocking-settlement")
    def test_locked_exit_skips_only_that_entry_and_others_settle(self):
        locked_door = create_object(
            Exit, key="鎖門", location=self.locked_post, destination=self.barracks
        )
        locked_door.locks.add("traverse:false()")
        create_object(
            Exit, key="敞門", location=self.north_gate, destination=self.barracks
        )
        for npc, target in (
            (self.locked_npc, "barracks"),
            (self.free_npc, "barracks"),
        ):
            set_npc_schedule(
                npc,
                {
                    "schema_version": 1,
                    "entries": [
                        {"tick_offset": 21600, "kind": "move", "target": target}
                    ],
                },
            )
        with patch("world.rules.npc_schedules.log_warn") as warn:
            events = settle_npc_schedules(0, DAY_SECONDS)
        warn.assert_called()
        self.assertIs(self.locked_npc.location, self.locked_post)
        self.assertIs(self.free_npc.location, self.barracks)
        # Only the successful move emits events (departed + arrived).
        self.assertEqual(len(events), 2)
        self.assertTrue(all(event.kind in ("npc_departed", "npc_arrived") for event in events))

    @covers_requirement("npc-schedule-runtime::a-failed-entry-settles-as-a-per-entry-skip-without-blocking-settlement")
    def test_unresolvable_target_skips_the_entry_without_an_event(self):
        set_npc_schedule(
            self.locked_npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "move", "target": "vanished_tower"}
                ],
            },
        )
        with patch("world.rules.npc_schedules.log_warn") as warn:
            events = settle_npc_schedules(0, DAY_SECONDS)
        warn.assert_called()
        self.assertEqual(events, [])
        self.assertIs(self.locked_npc.location, self.locked_post)

    @covers_requirement("npc-schedule-runtime::a-failed-entry-settles-as-a-per-entry-skip-without-blocking-settlement")
    def test_no_exit_to_the_destination_skips_the_move(self):
        set_npc_schedule(
            self.locked_npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "move", "target": "barracks"}
                ],
            },
        )
        events = settle_npc_schedules(0, DAY_SECONDS)
        self.assertEqual(events, [])
        self.assertIs(self.locked_npc.location, self.locked_post)

    @covers_requirement("npc-schedule-runtime::a-failed-entry-settles-as-a-per-entry-skip-without-blocking-settlement")
    def test_redirecting_exit_never_moves_the_npc_off_the_scheduled_route(self):
        from typeclasses.exits import Exit

        class RedirectingExit(Exit):
            """An exit whose at_traverse ignores the destination (wilderness-like)."""

            def at_traverse(self, traversing_object, target_location, **kwargs):
                return traversing_object.move_to(self._detour, quiet=True)

        detour = create_object(Room, key="岔路", location=None)
        gate = create_object(
            RedirectingExit, key="鬼打牆", location=self.locked_post, destination=self.barracks
        )
        gate._detour = detour
        set_npc_schedule(
            self.locked_npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "move", "target": "barracks"}
                ],
            },
        )
        with patch("world.rules.npc_schedules.log_warn") as warn:
            events = settle_npc_schedules(0, DAY_SECONDS)
        warn.assert_called()
        self.assertEqual(events, [])
        self.assertIs(self.locked_npc.location, self.locked_post)
        self.assertIsNone(self.locked_npc.db.schedule_state)

    @covers_requirement("npc-schedule-runtime::a-failed-entry-settles-as-a-per-entry-skip-without-blocking-settlement")
    def test_a_damaged_npc_cannot_raise_out_of_the_clock_source(self):
        # A schedule-bearing NPC whose stored unit fails to parse with an
        # unexpected exception is skipped with a bounded diagnostic; the
        # healthy NPC still settles and the source never raises.
        from world.rules import npc_schedules as npc_schedules_module

        set_npc_schedule(
            self.free_npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "state", "state": "resting"}
                ],
            },
        )
        set_npc_schedule(
            self.locked_npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "state", "state": "busy"}
                ],
            },
        )
        real_parse = npc_schedules_module.parse_stored_schedule

        def fake_parse(npc):
            if npc is self.locked_npc:
                raise RuntimeError("corrupt attribute")
            return real_parse(npc)

        with patch(
            "world.rules.npc_schedules.parse_stored_schedule", side_effect=fake_parse
        ):
            events = settle_npc_schedules(0, DAY_SECONDS)
        self.assertEqual(
            [event.payload["npc_id"] for event in events], [int(self.free_npc.pk)]
        )
        self.assertEqual(self.free_npc.db.schedule_state, "resting")
        self.assertIsNone(self.locked_npc.db.schedule_state)


class MultiDaySettlementTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.north_gate = AnchorRoom.create(key="北門", xyz=(9, 9, "test_map"))[0]
        self.north_gate.db.anchor_key = "north_gate"
        self.barracks = AnchorRoom.create(key="營房", xyz=(9, 10, "test_map"))[0]
        self.barracks.db.anchor_key = "barracks"
        create_object(Exit, key="門", location=self.north_gate, destination=self.barracks)
        create_object(Exit, key="回門", location=self.barracks, destination=self.north_gate)
        self.npc = create_object(NPC, key="巡邏守衛", location=self.barracks)
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "move", "target": "north_gate"},
                    {"tick_offset": 64800, "kind": "move", "target": "barracks"},
                ],
            },
        )

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_multi_day_skip_matches_repeated_day_by_day_advances(self):
        multi_events = settle_npc_schedules(0, 2 * DAY_SECONDS)
        # Every due occurrence settles exactly once, in (due_tick, stable id,
        # entry_index) order: each move emits departed then arrived, so each
        # due tick appears exactly twice.
        self.assertEqual(len(multi_events), 8)
        self.assertEqual(
            [event.due_tick for event in multi_events],
            [
                21600,
                21600,
                64800,
                64800,
                DAY_SECONDS + 21600,
                DAY_SECONDS + 21600,
                DAY_SECONDS + 64800,
                DAY_SECONDS + 64800,
            ],
        )
        self.assertIs(self.npc.location, self.barracks)
        # The A→B→A route requires exits both ways; the day-by-day equivalent
        # must land identically.
        self.npc.location = self.barracks
        settle_npc_schedules(0, DAY_SECONDS)
        settle_npc_schedules(DAY_SECONDS, 2 * DAY_SECONDS)
        self.assertIs(self.npc.location, self.barracks)

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_occurrences_carry_the_day_start_plus_offset_due_tick(self):
        events = settle_npc_schedules(DAY_SECONDS, 2 * DAY_SECONDS)
        self.assertEqual(
            sorted(event.due_tick for event in events),
            [DAY_SECONDS + 21600, DAY_SECONDS + 21600, DAY_SECONDS + 64800, DAY_SECONDS + 64800],
        )


class MidDayAssignmentTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object(NPC, key="店鋪老闆", location=self.room1)

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_passed_occurrences_never_settle_after_mid_day_assignment(self):
        get_world_clock().advance(30000, AdvanceSource.SKIP, [])
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "state", "state": "resting"},
                    {"tick_offset": 50400, "kind": "state", "state": "busy"},
                ],
            },
        )
        events = settle_npc_schedules(0, DAY_SECONDS)
        self.assertEqual(
            events,
            [
                ScheduledEvent(
                    "npc_state_changed",
                    50400,
                    {
                        "npc_id": int(self.npc.pk),
                        "npc": "店鋪老闆",
                        "state": "busy",
                    },
                )
            ],
        )
        self.assertEqual(self.npc.db.schedule_state, "busy")

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_assignment_exactly_at_a_due_tick_settles_that_occurrence(self):
        # Advance the clock to exactly the entry's due tick, assign there, and
        # settle the next window: the occurrence due at the assignment tick
        # was never offered to an earlier window, so it must settle.
        get_world_clock().advance(50400, AdvanceSource.SKIP, [])
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 50400, "kind": "state", "state": "resting"}
                ],
            },
        )
        events = settle_npc_schedules(50400, DAY_SECONDS)
        self.assertEqual(self.npc.db.schedule_state, "resting")
        self.assertEqual(
            events,
            [
                ScheduledEvent(
                    "npc_state_changed",
                    50400,
                    {
                        "npc_id": int(self.npc.pk),
                        "npc": "店鋪老闆",
                        "state": "resting",
                    },
                )
            ],
        )

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_start_boundary_occurrences_already_settled_do_not_replay(self):
        # Two NPCs: one scheduled from day 0 whose boundary occurrence the
        # day-0 window already settled; one assigned exactly at the next
        # window's start. The next window must not re-settle the first NPC's
        # boundary occurrence, but must settle the newly assigned one.
        first = create_object(NPC, key="第一店員", location=self.room1)
        set_npc_schedule(
            first,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 50400, "kind": "state", "state": "resting"}
                ],
            },
        )
        settle_npc_schedules(0, 50400)
        self.assertEqual(first.db.schedule_state, "resting")
        get_world_clock().advance(50400, AdvanceSource.SKIP, [])
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 51400, "kind": "state", "state": "busy"}
                ],
            },
        )
        events = settle_npc_schedules(50400, DAY_SECONDS)
        self.assertEqual(
            [event.payload["npc_id"] for event in events], [int(self.npc.pk)]
        )
        self.assertEqual(first.db.schedule_state, "resting")
        self.assertEqual(self.npc.db.schedule_state, "busy")


class SourceRegistrationTests(EvenniaTest):
    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_sync_registers_settle_npc_schedules_as_the_only_source(self):
        from world.rules.clock import _EVENT_SOURCES

        sync_npc_schedules()
        # A dict key holds exactly one source, so one key means one source.
        registration = _EVENT_SOURCES["npc_schedules"]
        self.assertIs(registration.settle, settle_npc_schedules)
        self.assertIsNotNone(registration.surfaces)

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_duplicate_key_npcs_tie_break_by_stable_primary_key(self):
        # Two NPCs sharing one display key with identical due entries settle
        # in stable (due_tick, npc_id, entry_index) order regardless of the
        # tag-query order.
        first = create_object(NPC, key="同名守衛", location=self.room1)
        second = create_object(NPC, key="同名守衛", location=self.room1)
        for npc in (first, second):
            set_npc_schedule(
                npc,
                {
                    "schema_version": 1,
                    "entries": [
                        {"tick_offset": 21600, "kind": "state", "state": "resting"}
                    ],
                },
            )
        events = settle_npc_schedules(0, DAY_SECONDS)
        self.assertEqual(
            [event.payload["npc_id"] for event in events],
            sorted([int(first.pk), int(second.pk)]),
        )
        for event in events:
            self.assertEqual(event.payload["npc"], "同名守衛")

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_registration_is_idempotent(self):
        from world.rules.clock import _EVENT_SOURCES

        sync_npc_schedules()
        sync_npc_schedules()
        self.assertIs(_EVENT_SOURCES["npc_schedules"].settle, settle_npc_schedules)

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-settles-due-schedule-entries")
    def test_advance_includes_npc_schedule_events_at_the_stage_position(self):
        from world.rules.clock import _STAGE_ORDER, register_event_source

        npc = create_object(NPC, key="店鋪老闆", location=self.room1)
        set_npc_schedule(
            npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 0, "kind": "state", "state": "busy"}
                ],
            },
        )
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        clock = get_world_clock()
        register_event_source("npc_schedules", settle_npc_schedules)
        events = clock.advance(DAY_SECONDS, AdvanceSource.SKIP, [self.char1])
        kinds = [event.kind for event in events]
        self.assertIn("npc_state_changed", kinds)
        stage_positions = {
            kind: _STAGE_ORDER.index(kind)
            for kind in ("daily_resets", "npc_schedules", "instance_reclamation")
        }
        self.assertLess(stage_positions["daily_resets"], stage_positions["npc_schedules"])
        self.assertLess(stage_positions["npc_schedules"], stage_positions["instance_reclamation"])


class ScheduleRollbackCacheTests(EvenniaTestCase):
    """A rolled-back advance restores schedule state and location (F5)."""

    def setUp(self):
        super().setUp()
        import world.rules.clock as clock_module

        self.north_gate = AnchorRoom.create(key="北門", xyz=(9, 9, "test_map"))[0]
        self.north_gate.db.anchor_key = "north_gate"
        self.barracks = AnchorRoom.create(key="營房", xyz=(9, 10, "test_map"))[0]
        self.barracks.db.anchor_key = "barracks"
        create_object(Exit, key="門", location=self.north_gate, destination=self.barracks)
        self.npc = create_object(NPC, key="巡邏守衛", location=self.north_gate)
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 21600, "kind": "state", "state": "resting"},
                    {"tick_offset": 64800, "kind": "move", "target": "barracks"},
                ],
            },
        )
        self._sources = dict(clock_module._EVENT_SOURCES)

    def tearDown(self):
        import world.rules.clock as clock_module

        clock_module._EVENT_SOURCES.clear()
        clock_module._EVENT_SOURCES.update(self._sources)
        super().tearDown()

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
    def test_failing_persist_restores_schedule_state_and_location(self):
        from evennia.utils.search import search_script
        from world.rules.clock import get_world_clock
        from world.rules.npc_schedules import register_npc_schedules

        before_state = self.npc.db.schedule_state
        before_location = self.npc.location
        register_npc_schedules()
        clock = get_world_clock()
        before_tick = clock.tick
        script = search_script("world_clock")[0]

        def failing_persist(tick):
            script.db.tick = tick
            raise RuntimeError("simulated persist failure")

        clock._persist = failing_persist
        with self.assertRaises(RuntimeError):
            clock.advance(DAY_SECONDS, AdvanceSource.SKIP, [])

        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(script.db.tick, before_tick)
        self.assertEqual(self.npc.db.schedule_state, before_state)
        self.assertEqual(self._raw_attribute(self.npc, "schedule_state"), before_state)
        self.assertIs(self.npc.location, before_location)
        self.assertIn(self.npc, self.north_gate.contents)
        self.assertNotIn(self.npc, self.barracks.contents)
        self.assertIn(self.npc, [o for o in self.north_gate.contents])

    @covers_requirement("world-clock::a-rolled-back-advance-restores-every-callback-owned-surface-not-just-caller-entities")
    def test_successful_advance_settles_state_and_move_committed(self):
        from world.rules.clock import get_world_clock
        from world.rules.npc_schedules import register_npc_schedules

        register_npc_schedules()
        clock = get_world_clock()
        before_tick = clock.tick
        clock.advance(DAY_SECONDS, AdvanceSource.SKIP, [])
        self.assertEqual(clock.tick, before_tick + DAY_SECONDS)
        self.assertEqual(self.npc.db.schedule_state, None)
        self.assertIs(self.npc.location, self.barracks)


class StartupClockSourceOrderTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    """Cold-start probes: a startup recovery advance settles with sources registered.

    ``restore_persisted_sessions`` may advance the world clock while settling
    an invalid persisted session; every world-event clock source must already
    be registered so an occurrence due inside the recovery window settles
    exactly as in an ordinary advance (audit finding run-3 F8,
    fix-startup-clock-source-order D1). The startup syncs register process-
    global catalog content, so the registries are snapshotted around each
    test (registry-isolation contract).
    """

    def setUp(self):
        super().setUp()
        self.player = create_object(
            PlayerCharacter, key="recovery-player", location=self.room1
        )
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.npc = create_object(NPC, key="巡邏守衛", location=self.room1)
        self.enemy = create_object(Monster, key="荒原野豬", location=self.room1)
        self.enemy.threat_tier = "low"
        self.enemy.apply_monster_tier("floor")

    @covers_requirement("npc-schedule-runtime::the-npc-schedules-clock-source-is-registered-before-startup-combat-recovery-advances-time")
    def test_recovery_advance_settles_an_occurrence_due_inside_its_window(self):
        from dataclasses import replace
        from unittest.mock import patch

        from world.maps.bootstrap import sync_grid, sync_service_interiors
        from world.quests.bootstrap import sync_quest_runtime
        from world.rules.clock import settle_combat_result
        from world.rules.combat_session import _persist, engage, read_session
        from world.rules.guild_economy import (
            restore_persisted_sessions,
            sync_guild_economy,
        )
        from world.rules.npc_schedules import sync_npc_schedules
        from world.rules.onboarding import sync_guard_npc

        clock = get_world_clock()
        self.assertEqual(clock.tick, 0)
        # A schedule effective from tick 0 with a state entry due at tick 3,
        # inside the (0, 6] window of a one-round recovery advance.
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [
                    {"tick_offset": 3, "kind": "state", "state": "resting"}
                ],
            },
        )
        # A well-formed one-round session whose recorded enemy is gone, as
        # after a crash before settlement: restoration terminates it as
        # invalid and settles the accumulated round time.
        engage(self.player, self.enemy)
        record = read_session(self.player)
        _persist(self.player, replace(record, rounds_elapsed=record.rounds_elapsed + 1))
        self.enemy.delete()

        captured: dict[str, Any] = {}

        def spy(result, entities):
            events = settle_combat_result(result, entities)
            captured["total_seconds"] = result.total_seconds
            captured["events"] = events
            return events

        # The deterministic startup sequence registers every clock source
        # before session restoration (fix-startup-clock-source-order D1).
        with patch("world.rules.combat_session.settle_combat_result", side_effect=spy):
            sync_grid()
            sync_service_interiors()
            sync_quest_runtime()
            sync_guild_economy()
            sync_guard_npc()
            sync_npc_schedules()
            restore_persisted_sessions()

        self.assertEqual(captured["total_seconds"], 6)
        self.assertEqual(get_world_clock().tick, 6)
        self.assertEqual(self.npc.db.schedule_state, "resting")
        self.assertTrue(
            any(
                event.kind == "npc_state_changed" and event.due_tick == 3
                for event in captured["events"]
            )
        )


class SettlementGuardTests(unittest.TestCase):
    def test_settlement_is_a_registered_source_never_written_by_ai(self):
        from world.rules import npc_schedules

        source = inspect.getsource(npc_schedules)
        self.assertIn("register_event_source", source)
        self.assertIn('"npc_schedules"', source)
        self.assertIn("settle_npc_schedules", source)
        self.assertIn("snapshot_npc_schedule_surfaces", source)
        self.assertNotIn("world.ai", source)


if __name__ == "__main__":
    unittest.main()
