"""Pure helpers used by deterministic skip commands."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from commands.skip import (
    CmdRest,
    CmdSleep,
    CmdWaitUntil,
    DurationParseError,
    _parse_duration,
    _render_skip_summary,
    _seconds_to_full_regen,
)
from tools.spec_traceability import covers_requirement
from world.rules.clock import AdvanceSource, ScheduledEvent
from world.rules.progression import proficiency_cap
from world.rules.skip_safety import SkipRejectReason
from world.rules.time_skip import MAX_SKIP_SECONDS, advance_skip


class SkipCommandHelperTests(unittest.TestCase):
    @covers_requirement("time-skip-commands::rest-duration-parses-an-explicit-duration-and-advances-the-clock-by-that-much-capped-at-the-configured-maximum")
    def test_rest_advances_by_the_exact_explicit_duration(self):
        caller = SimpleNamespace(msg=Mock(), db=SimpleNamespace())
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
        caller = SimpleNamespace(msg=Mock(), db=SimpleNamespace())
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


def _booking_caller(
    owned: tuple[str, ...] = (),
    proficiency: dict[str, float] | None = None,
    booking: str | None = None,
):
    """Caller stub the real booking preflight accepts or rejects."""
    return SimpleNamespace(
        msg=Mock(),
        pk=1,
        key="tester",
        race=None,
        skills=SimpleNamespace(owned_keys=lambda: set(owned)),
        db=SimpleNamespace(
            skill_proficiency=dict(proficiency or {}),
            affinity_elements=[],
            practice_booking=booking,
        ),
    )


class RestPracticeBookingTests(unittest.TestCase):
    """Declared-practice clause: preflight order, zero-advance, booking state."""

    def _run(self, args: str, caller):
        clock = Mock()
        clock.advance.return_value = []
        observed: list = []
        clock.advance.side_effect = lambda *a, **k: (
            observed.append(caller.db.practice_booking),
            [],
        )[1]
        command = CmdRest()
        command.caller = caller
        command.args = args
        with (
            patch("commands.skip.evaluate_skip_safety", return_value=None),
            patch("commands.skip.get_world_clock", return_value=clock),
        ):
            command.func()
        return clock, observed

    @covers_requirement("time-skip-commands::rest-duration-parses-an-explicit-duration-and-advances-the-clock-by-that-much-capped-at-the-configured-maximum")
    def test_valid_booking_is_recorded_before_the_advance(self):
        caller = _booking_caller(owned=("fire_arrow",))
        clock, observed = self._run("8h practice fire_arrow", caller)
        clock.advance.assert_called_once_with(28800, AdvanceSource.SKIP, [caller])
        # Recorded on the caller BEFORE advance; the clock stage is the writer.
        self.assertEqual(observed, ["fire_arrow"])

    @covers_requirement("time-skip-commands::rest-duration-parses-an-explicit-duration-and-advances-the-clock-by-that-much-capped-at-the-configured-maximum")
    def test_unknown_skill_rejects_with_zero_advance(self):
        caller = _booking_caller(owned=("fire_arrow",))
        clock, _ = self._run("1h practice not_a_skill", caller)
        clock.advance.assert_not_called()
        self.assertIn(
            "PRACTICE_SKILL_UNKNOWN", caller.msg.call_args_list[0].args[0]
        )
        self.assertIsNone(caller.db.practice_booking)

    @covers_requirement("time-skip-commands::rest-duration-parses-an-explicit-duration-and-advances-the-clock-by-that-much-capped-at-the-configured-maximum")
    def test_unowned_and_passive_skills_reject_as_unknown(self):
        unowned = _booking_caller(owned=())
        clock, _ = self._run("1h practice fire_arrow", unowned)
        clock.advance.assert_not_called()
        self.assertIn(
            "PRACTICE_SKILL_UNKNOWN", unowned.msg.call_args_list[0].args[0]
        )
        passive = _booking_caller(owned=("fire_mastery",))
        clock, _ = self._run("1h practice fire_mastery", passive)
        clock.advance.assert_not_called()
        self.assertIn(
            "PRACTICE_SKILL_UNKNOWN", passive.msg.call_args_list[0].args[0]
        )

    @covers_requirement("time-skip-commands::rest-duration-parses-an-explicit-duration-and-advances-the-clock-by-that-much-capped-at-the-configured-maximum")
    def test_capped_skill_rejects_and_clears_stale_booking(self):
        cap = proficiency_cap("fire_arrow")
        caller = _booking_caller(
            owned=("fire_arrow",),
            proficiency={"fire_arrow": cap * 50.0},
            booking="fire_arrow",
        )
        clock, _ = self._run("8h practice fire_arrow", caller)
        clock.advance.assert_not_called()
        self.assertIn("PRACTICE_SKILL_CAPPED", caller.msg.call_args_list[0].args[0])
        # A rejected clause leaves no booking — new or stale — to settle later.
        self.assertIsNone(caller.db.practice_booking)

    @covers_requirement("time-skip-commands::rest-duration-parses-an-explicit-duration-and-advances-the-clock-by-that-much-capped-at-the-configured-maximum")
    def test_plain_rest_clears_a_stale_rolled_back_booking(self):
        caller = _booking_caller(owned=("fire_arrow",), booking="fire_arrow")
        clock, observed = self._run("8h", caller)
        clock.advance.assert_called_once_with(28800, AdvanceSource.SKIP, [caller])
        self.assertEqual(observed, [None])
        self.assertIsNone(caller.db.practice_booking)

    @covers_requirement("skip-safety-gate::the-safety-gate-rejects-outright-it-does-not-compute-a-partial-safety-shortened")
    def test_safety_gate_rejection_precedes_booking_preflight(self):
        caller = _booking_caller(booking="fire_arrow")
        clock = Mock()
        command = CmdRest()
        command.caller = caller
        command.args = "1h practice not_a_skill"
        with (
            patch(
                "commands.skip.evaluate_skip_safety",
                return_value=SkipRejectReason.HOSTILE_PRESENT,
            ),
            patch("commands.skip.preflight_practice_booking") as preflight,
            patch("commands.skip.get_world_clock", return_value=clock),
        ):
            command.func()
        preflight.assert_not_called()
        clock.advance.assert_not_called()
        caller.msg.assert_called_once_with("附近有活著的怪物，這裡不安全。")
        # The whole command was blocked before booking handling: nothing
        # booking-related was written on any rejection path before the gate.
        self.assertEqual(caller.db.practice_booking, "fire_arrow")

    def test_malformed_clause_rejects_before_any_safety_check(self):
        caller = _booking_caller()
        command = CmdRest()
        command.caller = caller
        command.args = "2h practice"
        with patch("commands.skip.evaluate_skip_safety") as safety:
            command.func()
        safety.assert_not_called()
        caller.msg.assert_called_once_with(
            "用法：rest <數字><s|m|h|d> [practice <技能>]"
        )


class UnlabeledSkipClearingTests(unittest.TestCase):
    """Accepted unlabeled skips clear stale bookings before advancing."""

    @staticmethod
    def _caller():
        return SimpleNamespace(
            msg=Mock(),
            db=SimpleNamespace(practice_booking="fire_arrow"),
            traits=SimpleNamespace(
                hp=SimpleNamespace(value=100, max=100, rate=1),
                mp=SimpleNamespace(value=100, max=100, rate=1),
                sp=SimpleNamespace(value=100, max=100, rate=1),
            ),
        )

    @staticmethod
    def _clock(seen: list, caller):
        clock = Mock()
        clock.advance.return_value = []
        clock.advance.side_effect = lambda *a, **k: (
            seen.append(caller.db.practice_booking),
            [],
        )[1]
        return clock

    @covers_requirement("time-skip-commands::rest-duration-parses-an-explicit-duration-and-advances-the-clock-by-that-much-capped-at-the-configured-maximum")
    def test_sleep_clears_stale_booking_before_advance(self):
        caller = self._caller()
        seen: list = []
        clock = self._clock(seen, caller)
        command = CmdSleep()
        command.caller = caller
        with (
            patch("commands.skip._safe_to_skip", return_value=True),
            patch("commands.skip.get_world_clock", return_value=clock),
        ):
            command.func()
        clock.advance.assert_called_once()
        self.assertEqual(seen, [None])

    @covers_requirement("time-skip-commands::rest-duration-parses-an-explicit-duration-and-advances-the-clock-by-that-much-capped-at-the-configured-maximum")
    def test_wait_until_clears_stale_booking_before_advance(self):
        caller = self._caller()
        seen: list = []
        clock = self._clock(seen, caller)
        command = CmdWaitUntil()
        command.caller = caller
        command.args = "until dawn"
        with (
            patch("commands.skip._safe_to_skip", return_value=True),
            patch("commands.skip.seconds_until_daypart", return_value=60),
            patch("commands.skip.get_world_clock", return_value=clock),
        ):
            command.func()
        clock.advance.assert_called_once_with(60, AdvanceSource.SKIP, [caller])
        self.assertEqual(seen, [None])

    @covers_requirement("time-skip-commands::rest-duration-parses-an-explicit-duration-and-advances-the-clock-by-that-much-capped-at-the-configured-maximum")
    def test_advance_skip_clears_before_the_webclient_adapter_advance(self):
        caller = self._caller()
        seen: list = []
        clock = self._clock(seen, caller)
        with patch("world.rules.time_skip.get_world_clock", return_value=clock):
            advance_skip(caller, 3600)
        self.assertEqual(seen, [None])
        self.assertIsNone(caller.db.practice_booking)
        clock.advance.assert_called_once_with(3600, AdvanceSource.SKIP, [caller])
