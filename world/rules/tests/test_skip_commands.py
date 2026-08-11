"""Pure helpers used by deterministic skip commands."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from commands.skip import (
    CmdRest,
    DurationParseError,
    _parse_duration,
    _render_skip_summary,
    _seconds_to_full_regen,
)
from tools.spec_traceability import covers_requirement
from world.rules.clock import AdvanceSource, ScheduledEvent
from world.rules.time_skip import MAX_SKIP_SECONDS


class SkipCommandHelperTests(unittest.TestCase):
    @covers_requirement("time-skip-commands::rest-duration-parses-an-explicit-duration-and-advances-the-clock-by-that-much-capped-at-the-configured-maximum")
    def test_rest_advances_by_the_exact_explicit_duration(self):
        caller = SimpleNamespace(msg=Mock())
        clock = Mock()
        clock.advance.return_value = []
        command = CmdRest()
        command.caller = caller
        command.args = "1h"

        with (
            patch("commands.skip.evaluate_skip_safety", return_value=None) as safety,
            patch("commands.skip.get_world_clock", return_value=clock),
        ):
            command.func()

        safety.assert_called_once_with(caller)
        clock.advance.assert_called_once_with(3600, AdvanceSource.SKIP, [caller])
        caller.msg.assert_called_once_with("時間經過了 3600 秒。")

    def test_rest_longer_than_the_maximum_is_capped(self):
        caller = SimpleNamespace(msg=Mock())
        clock = Mock()
        clock.advance.return_value = []
        command = CmdRest()
        command.caller = caller
        command.args = "1000000000d"

        with (
            patch("commands.skip.evaluate_skip_safety", return_value=None),
            patch("commands.skip.get_world_clock", return_value=clock),
        ):
            command.func()

        clock.advance.assert_called_once_with(
            MAX_SKIP_SECONDS, AdvanceSource.SKIP, [caller]
        )
        caller.msg.assert_called_once_with(
            f"時間經過了 {MAX_SKIP_SECONDS} 秒。"
        )

    def test_duration_parser_accepts_explicit_units_only(self):
        self.assertEqual(_parse_duration("1h"), 3600)
        self.assertEqual(_parse_duration("30m"), 1800)
        with self.assertRaises(DurationParseError):
            _parse_duration("tomorrow")

    @covers_requirement("time-skip-commands::every-time-skip-command-reports-the-events-that-came-due", "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-capped-at-a-configured-maximum")
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
