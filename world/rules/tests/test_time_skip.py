"""Shared deterministic time-skip helper tests (webclient-exploration-menu D7).

The ``world/rules/time_skip.py`` helper owns duration parsing, the bounded
full-regen computation, the safety gate, and the ``AdvanceSource.SKIP``
execution shared by the typed commands and the ``explore.wait`` adapter.
"""

from tools.spec_traceability import covers_requirement

import math
import unittest
from types import SimpleNamespace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC
from typeclasses.monsters import Monster
from world.rules.clock import (
    AdvanceSource,
    CLOCK_YAML,
    ScheduledEvent,
    _EVENT_SOURCES,
    get_world_clock,
    register_event_source,
)
from world.rules.fatigue import (
    SleepPosture,
    read_fatigue_state,
    write_fatigue_state,
)
from world.rules.mental_time import next_mental_offset, sample_activity
from world.rules.party import join_party
from world.rules.time_skip import (
    MAX_SKIP_SECONDS,
    MAX_WEB_SKIP_SECONDS,
    DurationParseError,
    SkipRefused,
    SleepRefused,
    advance_wait,
    begin_sleep,
    continue_sleep,
    enter_sleep,
    parse_duration,
    render_skip_summary,
    seconds_to_full_regen,
    seconds_to_natural_wake,
    unsafe_rejection,
)


class _Attrs:
    """Minimal read-only attribute store for pure physiology probes."""

    def __init__(self, **values):
        self.values = values

    def has(self, key, category=None):
        return key in self.values

    def get(self, key, default=None, category=None):
        return self.values.get(key, default)


class _Gauge:
    def __init__(self, value, maximum, rate=0):
        self.current = value
        self.value = value
        self.max = maximum
        self.rate = rate


def _fatigue_probe(reserve, posture, *, full_gauges=False):
    gauges = (
        _Gauge(100, 100, 0) if full_gauges else _Gauge(10, 100, 1)
    )
    return SimpleNamespace(
        traits=SimpleNamespace(hp=gauges, mp=gauges, sp=gauges),
        attributes=_Attrs(
            mental_reserve_units=reserve, sleep_posture=posture.value
        ),
    )


class SkipHelperPureTests(unittest.TestCase):
    def test_parse_duration(self):
        self.assertEqual(parse_duration("90s"), 90)
        self.assertEqual(parse_duration("2m"), 120)
        self.assertEqual(parse_duration("1h"), 3600)
        self.assertEqual(parse_duration("11h"), 11 * 3600)
        for bad in ("", "soon", "1", "1x", "-5m"):
            with self.assertRaises(DurationParseError):
                parse_duration(bad)

    def test_parse_duration_clamps_at_max_skip_seconds(self):
        self.assertEqual(parse_duration("12h"), MAX_SKIP_SECONDS)
        self.assertEqual(parse_duration("1d"), MAX_SKIP_SECONDS)
        self.assertEqual(parse_duration("1000000000d"), MAX_SKIP_SECONDS)
        self.assertEqual(parse_duration("11h"), 11 * 3600)
        # A five-digit amount below the cap still parses exactly.
        self.assertEqual(parse_duration("10000s"), 10000)

    def test_parse_duration_clamps_absurd_digit_strings(self):
        self.assertEqual(parse_duration("9" * 5000 + "d"), MAX_SKIP_SECONDS)
        self.assertEqual(parse_duration("9" * 5000 + "s"), MAX_SKIP_SECONDS)

    def test_full_regen_is_bounded_by_max_sleep_seconds(self):
        class Gauge:
            def __init__(self, value, maximum, rate):
                self.value = value
                self.current = value
                self.max = maximum
                self.rate = rate

        entity = SimpleNamespace(
            traits=SimpleNamespace(
                hp=Gauge(10, 100, 1),
                mp=Gauge(50, 100, 100),
                sp=Gauge(100, 100, 0),
            )
        )
        seconds = seconds_to_full_regen(entity)
        self.assertEqual(seconds, 90)  # hp regen is the slowest
        # A pathological gap is still capped at the clock.yaml bound.
        entity.traits.hp = Gauge(1, 10 ** 9, 1)
        self.assertEqual(seconds_to_full_regen(entity), CLOCK_YAML["max_sleep_seconds"])

    def test_web_bound_never_exceeds_the_sleep_cap(self):
        self.assertEqual(MAX_WEB_SKIP_SECONDS, CLOCK_YAML["max_sleep_seconds"])

    def test_full_gauges_with_half_reserve_need_15000_seconds(self):
        entity = _fatigue_probe(180000, SleepPosture.AWAKE, full_gauges=True)
        # 180,000 reserve units at the authored 12 units/second sleep rate.
        self.assertEqual(seconds_to_full_regen(entity), 15000)

    def test_forced_sleeper_needs_6000_seconds_from_zero(self):
        entity = _fatigue_probe(0, SleepPosture.FORCED, full_gauges=True)
        self.assertEqual(seconds_to_natural_wake(entity), 6000)
        self.assertEqual(next_mental_offset(entity), 6000)

    def test_awake_depletion_boundary_uses_the_authored_rate(self):
        entity = _fatigue_probe(2400, SleepPosture.AWAKE, full_gauges=True)
        self.assertEqual(next_mental_offset(entity), 600)

    def test_activity_sampling_follows_the_stored_posture(self):
        self.assertIs(
            sample_activity(_fatigue_probe(1000, SleepPosture.FORCED)),
            sample_activity(_fatigue_probe(1000, SleepPosture.VOLUNTARY)),
        )
        self.assertIsNot(
            sample_activity(_fatigue_probe(1000, SleepPosture.AWAKE)),
            sample_activity(_fatigue_probe(1000, SleepPosture.FORCED)),
        )

    def test_render_skip_summary(self):
        self.assertEqual(
            render_skip_summary(90, []), "時間經過了 90 秒。"
        )
        self.assertEqual(
            render_skip_summary(90, [SimpleNamespace(kind="daily_reset", due_tick=0, payload={})]),
            "時間經過了 90 秒。 新的一天開始了。",
        )
        # A committed booked-study unlock rides the summary as its own line.
        self.assertEqual(
            render_skip_summary(
                90,
                [
                    SimpleNamespace(
                        kind="practice_unlock",
                        due_tick=0,
                        payload={"line": "同伴 學會了 合成分枝術"},
                    )
                ],
            ),
            "時間經過了 90 秒。 同伴 學會了 合成分枝術",
        )


class SkipHelperAdvanceTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.save()
        write_fatigue_state(self.player, 360000, SleepPosture.AWAKE)

    def _companion(self, reserve=360000, posture=SleepPosture.AWAKE):
        npc = create_object(NPC, key=f"companion-{reserve}", location=self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        write_fatigue_state(npc, reserve, posture)
        return npc

    def test_advance_wait_uses_skip_source_and_returns_an_accepted_result(self):
        before = get_world_clock().tick
        result = advance_wait(self.player, 60)
        self.assertEqual(get_world_clock().tick - before, 60)
        self.assertEqual(result.requested_seconds, 60)
        self.assertEqual(result.elapsed_seconds, 60)
        self.assertFalse(result.voluntary)

    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    def test_mixed_wait_differs_per_member_activity(self):
        sleeper = self._companion(0, SleepPosture.FORCED)
        result = advance_wait(self.player, 600)
        self.assertEqual(result.elapsed_seconds, 600)
        self.assertEqual(read_fatigue_state(sleeper).reserve_units, 7200)
        self.assertIs(read_fatigue_state(sleeper).posture, SleepPosture.FORCED)
        # The awake commander waits at -4 units/second; nobody is selected
        # for sleep by the shared advance.
        self.assertEqual(read_fatigue_state(self.player).reserve_units, 357600)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)

    def test_first_wake_truncates_and_discards_the_remainder(self):
        sleeper = self._companion(0, SleepPosture.FORCED)
        before = get_world_clock().tick
        result = advance_wait(self.player, 10000)
        self.assertEqual(result.requested_seconds, 10000)
        self.assertEqual(result.elapsed_seconds, 6000)
        self.assertEqual(get_world_clock().tick - before, 6000)
        self.assertEqual(read_fatigue_state(sleeper).reserve_units, 72000)
        self.assertIs(read_fatigue_state(sleeper).posture, SleepPosture.AWAKE)

    def test_first_collapse_truncates_and_latches_forced_sleep(self):
        companion = self._companion(2400)
        result = advance_wait(self.player, 1200)
        self.assertEqual(result.elapsed_seconds, 600)
        state = read_fatigue_state(companion)
        self.assertEqual(state.reserve_units, 0)
        self.assertIs(state.posture, SleepPosture.FORCED)

    def test_registered_interactive_boundary_stops_the_skip(self):
        previous = _EVENT_SOURCES.get("shop_hours")

        def settle(start, end):
            return [ScheduledEvent("synthetic_interactive", end, {})]

        register_event_source(
            "shop_hours",
            settle,
            next_boundary=lambda start, end: start + 37,
        )
        try:
            result = advance_wait(self.player, 100)
        finally:
            if previous is None:
                _EVENT_SOURCES.pop("shop_hours", None)
            else:
                _EVENT_SOURCES["shop_hours"] = previous
        self.assertEqual(result.elapsed_seconds, 37)
        self.assertIn(
            "synthetic_interactive", [event.kind for event in result.events]
        )

    def test_tied_member_boundaries_commit_one_shared_interval(self):
        first = self._companion(0, SleepPosture.FORCED)
        second = self._companion(0, SleepPosture.FORCED)
        before = get_world_clock().tick
        result = advance_wait(self.player, 10000)
        self.assertEqual(result.elapsed_seconds, 6000)
        self.assertEqual(get_world_clock().tick - before, 6000)
        for sleeper in (first, second):
            self.assertEqual(read_fatigue_state(sleeper).reserve_units, 72000)
            self.assertIs(
                read_fatigue_state(sleeper).posture, SleepPosture.AWAKE
            )

    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    def test_tied_registered_event_and_wake_publish_both_facts(self):
        previous = _EVENT_SOURCES.get("shop_hours")
        sleeper = self._companion(0, SleepPosture.FORCED)
        register_event_source(
            "shop_hours",
            lambda start, end: [
                ScheduledEvent("synthetic_interactive", end, {})
            ],
            next_boundary=lambda start, end: start + 6000,
        )
        try:
            result = advance_wait(self.player, 10000)
        finally:
            if previous is None:
                _EVENT_SOURCES.pop("shop_hours", None)
            else:
                _EVENT_SOURCES["shop_hours"] = previous
        self.assertEqual(result.elapsed_seconds, 6000)
        self.assertIn(
            "synthetic_interactive", [event.kind for event in result.events]
        )
        self.assertIs(
            read_fatigue_state(sleeper).posture, SleepPosture.AWAKE
        )

    def test_duplicate_operation_identity_never_replays_time(self):
        before = get_world_clock().tick
        first = advance_wait(self.player, 60, operation_id="synthetic-op-once")
        after_first = get_world_clock().tick
        second = advance_wait(self.player, 60, operation_id="synthetic-op-once")
        self.assertEqual(get_world_clock().tick, after_first)
        self.assertEqual(after_first - before, 60)
        self.assertEqual(first, second)

    def test_unsafe_wait_refuses_before_any_time(self):
        monster = self._monster()
        before = get_world_clock().tick
        with self.assertRaises(SkipRefused):
            advance_wait(self.player, 60)
        self.assertEqual(get_world_clock().tick, before)
        self.assertIsNotNone(monster.pk)

    def test_entry_commits_posture_at_zero_elapsed(self):
        before = get_world_clock().tick
        entry = enter_sleep(self.player)
        self.assertEqual(get_world_clock().tick, before)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.VOLUNTARY)
        self.assertEqual(entry.requested_seconds, 0)

    @covers_requirement(
        "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-"
        "capped-at-a-configured-maximum"
    )
    def test_full_gauges_with_half_reserve_continue_for_15000_seconds(self):
        for key in ("hp", "mp", "sp"):
            gauge = getattr(self.player.traits, key)
            gauge.current = gauge.max
            gauge.rate = 0.0
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        before = get_world_clock().tick
        outcome = begin_sleep(self.player)
        self.assertIsNotNone(outcome.result)
        self.assertEqual(outcome.result.elapsed_seconds, 15000)
        self.assertEqual(get_world_clock().tick - before, 15000)
        self.assertEqual(read_fatigue_state(self.player).reserve_units, 360000)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        self.assertTrue(outcome.result.woke)

    def test_forced_sleeper_cannot_volunteer_but_recovers_by_waiting(self):
        write_fatigue_state(self.player, 0, SleepPosture.FORCED)
        with self.assertRaises(SleepRefused):
            begin_sleep(self.player)
        result = advance_wait(self.player, 10000)
        self.assertEqual(result.elapsed_seconds, 6000)
        self.assertEqual(read_fatigue_state(self.player).reserve_units, 72000)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)

    def test_duplicate_continuation_identity_never_replays_time(self):
        entry = enter_sleep(self.player)
        first = continue_sleep(
            self.player, entry, operation_id="synthetic-sleep-once"
        )
        before = get_world_clock().tick
        second = continue_sleep(
            self.player, entry, operation_id="synthetic-sleep-once"
        )
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(first, second)

    def test_unsafe_rejection_reports_hostile_present(self):
        monster = self._monster()
        rejection = unsafe_rejection(self.player)
        self.assertIn("怪物", rejection)
        self.assertIsNotNone(monster.pk)

    def test_safe_skip_returns_none_rejection(self):
        self.assertIsNone(unsafe_rejection(self.player))

    def _monster(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        return monster


if __name__ == "__main__":
    unittest.main()
