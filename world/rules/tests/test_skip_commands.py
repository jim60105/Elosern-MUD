"""Pure helpers used by deterministic skip commands."""

import unittest
from types import SimpleNamespace

from commands.skip import (
    DurationParseError,
    _parse_duration,
    _render_skip_summary,
    _seconds_to_full_regen,
)
from world.rules.clock import ScheduledEvent


class SkipCommandHelperTests(unittest.TestCase):
    def test_duration_parser_accepts_explicit_units_only(self):
        self.assertEqual(_parse_duration("1h"), 3600)
        self.assertEqual(_parse_duration("30m"), 1800)
        with self.assertRaises(DurationParseError):
            _parse_duration("tomorrow")

    def test_sleep_uses_slowest_regen_and_summary_mentions_daily_reset(self):
        entity = SimpleNamespace(
            traits=SimpleNamespace(
                hp=SimpleNamespace(value=0, max=100, rate=1),
                mp=SimpleNamespace(value=0, max=100, rate=2),
                sp=SimpleNamespace(value=100, max=100, rate=1),
            )
        )
        self.assertEqual(_seconds_to_full_regen(entity), 100)
        self.assertIn(
            "新的一天",
            _render_skip_summary(1, [ScheduledEvent("daily_reset", 1, {})]),
        )
