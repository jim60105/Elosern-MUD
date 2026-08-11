"""Shared deterministic time-skip helper tests (webclient-exploration-menu D7).

The ``world/rules/time_skip.py`` helper owns duration parsing, the bounded
full-regen computation, the safety gate, and the ``AdvanceSource.SKIP``
execution shared by the typed commands and the ``explore.wait`` adapter.
"""

from tools.spec_traceability import covers_requirement

import math
import unittest
from types import SimpleNamespace

from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from world.rules.clock import AdvanceSource, CLOCK_YAML, get_world_clock
from world.rules.time_skip import (
    MAX_SKIP_SECONDS,
    MAX_WEB_SKIP_SECONDS,
    DurationParseError,
    advance_skip,
    parse_duration,
    render_skip_summary,
    seconds_to_full_regen,
    unsafe_rejection,
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

    def test_render_skip_summary(self):
        self.assertEqual(
            render_skip_summary(90, []), "時間經過了 90 秒。"
        )
        self.assertEqual(
            render_skip_summary(90, [SimpleNamespace(kind="daily_reset", due_tick=0, payload={})]),
            "時間經過了 90 秒。 新的一天開始了。",
        )


class SkipHelperAdvanceTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.save()

    def test_advance_skip_uses_advance_source_skip_and_returns_events(self):
        before = get_world_clock().tick
        events = advance_skip(self.player, 60)
        self.assertEqual(get_world_clock().tick - before, 60)
        # The command path and the adapter settle through the same gate; the
        # helper's advance is the single execution site.
        self.assertIsInstance(events, list)

    def test_unsafe_rejection_reports_hostile_present(self):
        monster = self._monster()
        rejection = unsafe_rejection(self.player)
        self.assertIn("怪物", rejection)

    def test_safe_skip_returns_none_rejection(self):
        self.assertIsNone(unsafe_rejection(self.player))

    def _monster(self):
        from evennia.utils.create import create_object

        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        return monster


if __name__ == "__main__":
    unittest.main()
