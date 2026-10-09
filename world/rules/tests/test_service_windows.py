"""Synthetic Evennia tests for planned-npc-service-windows."""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.exits import Exit
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from tools.spec_traceability import covers_requirement
from world.rules.clock import get_world_clock
from world.rules.exam_schedule_holds import (
    begin_exam_schedule_hold,
    read_exam_schedule_hold,
    release_exam_schedule_hold,
)
from world.rules.npc_schedules import (
    ScheduleEntry,
    ScheduleRulebook,
    ScheduleTemplate,
    set_npc_schedule,
    settle_npc_schedules,
)
from world.rules.service_windows import (
    REASON_ACTIVE_EXAM_HOLD,
    REASON_INVALID_HOST,
    REASON_MISSING_SCHEDULE,
    REASON_MISSING_WORLD_CLOCK,
    REASON_SCHEDULE_SILENCED,
    REASON_UNCONFIRMABLE,
    REASON_UNRESOLVED_DESTINATION,
    PlannedServiceInterval,
    read_next_planned_service_interval,
)

DAY = 86400


class PlannedServiceWindowsTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.home = create_object(Room, key="home_room")
        self.guild = create_object(Room, key="guild_hall")
        self.door_out = create_object(Exit, key="out", location=self.home, destination=self.guild)
        self.door_in = create_object(Exit, key="in", location=self.guild, destination=self.home)

        self.npc = create_object(NPC, key="host_npc", location=self.home)
        self.clock = get_world_clock()
        self.clock.tick = 0
        self.clock._persist(0)

        book = ScheduleRulebook(
            1,
            ("duty", "busy", "resting"),
            (
                ScheduleTemplate(
                    "daily_host",
                    (
                        ScheduleEntry(100, "move", target="guild_hall"),
                        ScheduleEntry(200, "move", target="home_room"),
                    ),
                    default_state="duty",
                    cycle_days=1,
                ),
                ScheduleTemplate(
                    "busy_arrival_host",
                    (
                        ScheduleEntry(100, "move", target="guild_hall"),
                        ScheduleEntry(100, "state", state="busy"),
                        ScheduleEntry(150, "state", state="duty"),
                        ScheduleEntry(250, "move", target="home_room"),
                    ),
                    default_state="duty",
                    cycle_days=1,
                ),
                ScheduleTemplate(
                    "weekly_host",
                    (
                        ScheduleEntry(DAY + 100, "move", target="guild_hall"),
                        ScheduleEntry(DAY + 500, "move", target="home_room"),
                    ),
                    default_state="duty",
                    cycle_days=7,
                ),
            ),
        )

        for target, kwargs in (
            ("world.rules.npc_schedules.get_rulebook", {"return_value": book}),
            (
                "world.rules.npc_schedules._resolve_destination",
                {"side_effect": {"guild_hall": self.guild, "home_room": self.home}.get},
            ),
        ):
            mock = patch(target, **kwargs)
            mock.start()
            self.addCleanup(mock.stop)

    @covers_requirement(
        "npc-service-availability::planned-service-intervals-use-authoritative-schedule-occurrences-without-mutation"
    )
    def test_busy_arrival_scenario(self):
        """Scenario: Busy arrival - interval starts at available transition, not at arrival."""
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "busy_arrival_host"})
        self.npc.location = self.home
        self.npc.db.schedule_state = "duty"

        result = read_next_planned_service_interval(self.npc, self.guild, current_tick=50)
        self.assertTrue(result.available)
        self.assertIsNone(result.reason)
        # Arrival at 100 is busy, duty transition at 150, leaves at 250 -> [150, 250)
        self.assertEqual(result.interval, PlannedServiceInterval(150, 250))

    @covers_requirement(
        "npc-service-availability::planned-service-intervals-use-authoritative-schedule-occurrences-without-mutation"
    )
    def test_read_only_snapshot_scenario(self):
        """Scenario: Read-only snapshot - no mutations occur when reading valid absent host."""
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "daily_host"})
        self.npc.location = self.home
        self.npc.db.schedule_state = "duty"

        loc_before = self.npc.location
        state_before = self.npc.db.schedule_state
        clock_before = self.clock.tick
        tags_before = list(self.npc.tags.all())
        attrs_before = {
            key: self.npc.attributes.get(key)
            for key in ("schedule", "schedule_state", "exam_schedule_hold")
        }

        result = read_next_planned_service_interval(self.npc, self.guild, current_tick=50)
        self.assertTrue(result.available)
        self.assertEqual(result.interval, PlannedServiceInterval(100, 200))

        self.assertIs(self.npc.location, loc_before)
        self.assertEqual(self.npc.db.schedule_state, state_before)
        self.assertEqual(self.clock.tick, clock_before)
        self.assertEqual(list(self.npc.tags.all()), tags_before)
        attrs_after = {
            key: self.npc.attributes.get(key)
            for key in ("schedule", "schedule_state", "exam_schedule_hold")
        }
        self.assertEqual(attrs_after, attrs_before)

    @covers_requirement(
        "npc-service-availability::planned-service-intervals-use-authoritative-schedule-occurrences-without-mutation"
    )
    def test_missed_arrival_scenario(self):
        """Scenario: Missed arrival - absent host at an earlier planned window finds future interval."""
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "daily_host"})
        # Arrival was scheduled at tick 100 to guild, departure at 200.
        # At tick 150, NPC is still at home (skipped arrival).
        self.npc.location = self.home
        self.npc.db.schedule_state = "duty"

        result = read_next_planned_service_interval(self.npc, self.guild, current_tick=150)
        self.assertTrue(result.available)
        # It must NOT return [150, 200) or [100, 200). It must project the NEXT cycle: [DAY + 100, DAY + 200)
        self.assertEqual(result.interval, PlannedServiceInterval(DAY + 100, DAY + 200))

    @covers_requirement(
        "npc-service-availability::indeterminate-attendance-never-fabricates-a-timetable-or-reveals-private-routes"
    )
    @covers_requirement(
        "npc-service-availability::planned-service-intervals-use-authoritative-schedule-occurrences-without-mutation"
    )
    def test_arrival_due_now_remains_planned_until_location_confirms(self):
        """Arrival due at current_tick: if location is not confirmed, remains planned."""
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "daily_host"})
        # Arrival is scheduled at 100 to guild_hall.
        # At tick 100, if location is still home, arrival due now is treated as missed / not confirmed yet
        self.npc.location = self.home
        self.npc.db.schedule_state = "duty"

        result = read_next_planned_service_interval(self.npc, self.guild, current_tick=100)
        self.assertTrue(result.available)
        # Because arrival at 100 was not confirmed, the current interval [100, 200) cannot provide presence.
        self.assertEqual(result.interval, PlannedServiceInterval(DAY + 100, DAY + 200))

        # But if actual location confirms it:
        self.npc.location = self.guild
        confirmed = read_next_planned_service_interval(self.npc, self.guild, current_tick=100)
        self.assertTrue(confirmed.available)
        self.assertEqual(confirmed.interval, PlannedServiceInterval(100, 200))

    @covers_requirement(
        "npc-service-availability::planned-service-intervals-use-authoritative-schedule-occurrences-without-mutation"
    )
    def test_currently_present_host_returns_current_tick_to_departure(self):
        """When host is actually at destination and duty, interval is [current_tick, end)."""
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "daily_host"})
        self.npc.location = self.guild
        self.npc.db.schedule_state = "duty"

        result = read_next_planned_service_interval(self.npc, self.guild, current_tick=150)
        self.assertTrue(result.available)
        self.assertEqual(result.interval, PlannedServiceInterval(150, 200))

    @covers_requirement(
        "npc-service-availability::indeterminate-attendance-never-fabricates-a-timetable-or-reveals-private-routes"
    )
    def test_missing_clock_scenario(self):
        """Scenario: Missing clock returns named unavailable without clock creation."""
        with patch("world.rules.service_windows.read_world_clock", return_value=None):
            result = read_next_planned_service_interval(self.npc, self.guild, current_tick=None)
            self.assertFalse(result.available)
            self.assertEqual(result.reason, REASON_MISSING_WORLD_CLOCK)

    @covers_requirement(
        "npc-service-availability::indeterminate-attendance-never-fabricates-a-timetable-or-reveals-private-routes"
    )
    def test_held_or_silenced_host_scenario(self):
        """Scenario: Held or silenced host never fabricates an interval."""
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "daily_host"})

        # Active hold
        self.clock.tick = 0
        self.clock._persist(0)
        begin_exam_schedule_hold(self.npc, "exam_1", 0)
        result = read_next_planned_service_interval(self.npc, self.guild, current_tick=50)
        self.assertFalse(result.available)
        self.assertEqual(result.reason, REASON_ACTIVE_EXAM_HOLD)

        # Release hold
        self.clock.tick = 50
        self.clock._persist(50)
        release_exam_schedule_hold(self.npc, "exam_1", 50)
        result_after_release = read_next_planned_service_interval(
            self.npc, self.guild, current_tick=50
        )
        self.assertTrue(result_after_release.available)

        # Silenced host
        with patch("world.rules.service_windows.schedule_silenced", return_value=True):
            silenced_result = read_next_planned_service_interval(
                self.npc, self.guild, current_tick=50
            )
            self.assertFalse(silenced_result.available)
            self.assertEqual(silenced_result.reason, REASON_SCHEDULE_SILENCED)

    @covers_requirement(
        "npc-service-availability::indeterminate-attendance-never-fabricates-a-timetable-or-reveals-private-routes"
    )
    def test_boundary_scenario(self):
        """Scenario: Boundary - tick equals service interval end is no longer usable."""
        set_npc_schedule(self.npc, {"schema_version": 1, "template": "daily_host"})
        self.npc.location = self.guild
        self.npc.db.schedule_state = "duty"

        # At tick 200, interval [100, 200) has ended; departure occurs at 200.
        result = read_next_planned_service_interval(self.npc, self.guild, current_tick=200)
        self.assertTrue(result.available)
        # Returns the next cycle arrival!
        self.assertEqual(result.interval, PlannedServiceInterval(DAY + 100, DAY + 200))

    @covers_requirement(
        "npc-service-availability::indeterminate-attendance-never-fabricates-a-timetable-or-reveals-private-routes"
    )
    def test_indeterminate_inputs_named_reasons(self):
        """Invalid inputs return explicit named reasons."""
        # Non-persistent NPC
        temp_npc = NPC()
        self.assertEqual(
            read_next_planned_service_interval(temp_npc, self.guild, 0).reason,
            REASON_INVALID_HOST,
        )

        # Unresolved destination
        self.assertEqual(
            read_next_planned_service_interval(self.npc, "non_existent_anchor", 0).reason,
            REASON_UNRESOLVED_DESTINATION,
        )

        # Missing schedule
        self.npc.db.schedule = None
        self.assertEqual(
            read_next_planned_service_interval(self.npc, self.guild, 0).reason,
            REASON_MISSING_SCHEDULE,
        )

        # Bounded unconfirmable (schedule with no arrivals)
        set_npc_schedule(
            self.npc,
            {
                "schema_version": 1,
                "entries": [{"tick_offset": 50, "kind": "state", "state": "duty"}],
            },
        )
        self.assertEqual(
            read_next_planned_service_interval(self.npc, self.guild, 0).reason,
            REASON_UNCONFIRMABLE,
        )
