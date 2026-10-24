"""Deterministic skip commands routing through the shared skip operation."""

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
)
from tools.spec_traceability import covers_requirement
from world.rules.clock import AdvanceSource, ScheduledEvent
from world.rules.progression import proficiency_cap
from world.rules.skip_safety import SkipRejectReason
from world.rules.time_skip import (
    MAX_SKIP_SECONDS,
    SkipResult,
    SleepEntry,
    SleepOutcome,
    SleepRefused,
    advance_wait,
    seconds_to_full_regen,
)
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries

# Kit rows: an ACTIVE martial skill is practicable; a PASSIVE row must be
# refused as "unknown" by the booking preflight.
_PRACTICE_SKILL = SYNTH_SKILLS["t_cinder_cleave"].key
_PASSIVE_SKILL = SYNTH_SKILLS["t_steady_stride"].key


def _result(seconds: int) -> SkipResult:
    return SkipResult(
        operation_id="synthetic-operation",
        requested_seconds=seconds,
        elapsed_seconds=seconds,
        events=(),
    )


class SkipCommandHelperTests(unittest.TestCase):
    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    def test_rest_routes_the_exact_duration_through_the_shared_operation(self):
        caller = SimpleNamespace(msg=Mock(), db=SimpleNamespace())
        command = CmdRest()
        command.caller = caller
        command.args = "1h"

        with (
            patch("commands.skip.evaluate_skip_safety", return_value=None) as safety,
            patch("commands.skip.advance_wait", return_value=_result(3600)) as op,
        ):
            command.func()

        safety.assert_called_once_with(caller)
        op.assert_called_once_with(caller, 3600, practice_skill=None)
        caller.msg.assert_called_once_with("時間經過了 3600 秒。")

    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    def test_rest_longer_than_the_maximum_is_capped(self):
        caller = SimpleNamespace(msg=Mock(), db=SimpleNamespace())
        command = CmdRest()
        command.caller = caller
        command.args = "1000000000d"

        with (
            patch("commands.skip.evaluate_skip_safety", return_value=None),
            patch(
                "commands.skip.advance_wait",
                return_value=_result(MAX_SKIP_SECONDS),
            ) as op,
        ):
            command.func()

        op.assert_called_once_with(
            caller, MAX_SKIP_SECONDS, practice_skill=None
        )
        caller.msg.assert_called_once_with(
            f"時間經過了 {MAX_SKIP_SECONDS} 秒。"
        )

    def test_duration_parser_accepts_explicit_units_only(self):
        self.assertEqual(_parse_duration("1h"), 3600)
        self.assertEqual(_parse_duration("30m"), 1800)
        with self.assertRaises(DurationParseError):
            _parse_duration("tomorrow")

    @covers_requirement(
        "time-skip-commands::every-time-skip-command-reports-the-events-that-"
        "came-due",
        "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-"
        "capped-at-a-configured-maximum",
    )
    def test_sleep_target_and_summary_report_the_committed_elapsed_time(self):
        entity = SimpleNamespace(
            traits=SimpleNamespace(
                hp=SimpleNamespace(value=0, max=100, rate=1),
                mp=SimpleNamespace(value=0, max=100, rate=2),
                sp=SimpleNamespace(value=100, max=100, rate=1),
            )
        )
        self.assertEqual(seconds_to_full_regen(entity), 100)
        self.assertIn(
            "新的一天",
            _render_skip_summary(1, [ScheduledEvent("daily_reset", 1, {})]),
        )

    @covers_requirement(
        "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-"
        "capped-at-a-configured-maximum"
    )
    def test_sleep_reports_the_committed_elapsed_interval(self):
        caller = SimpleNamespace(msg=Mock(), db=SimpleNamespace())
        entry = SleepEntry("synthetic-entry", caller, 3600, False)
        command = CmdSleep()
        command.caller = caller
        command.args = ""
        with (
            patch("commands.skip.evaluate_skip_safety", return_value=None),
            patch(
                "commands.skip.begin_sleep",
                return_value=SleepOutcome(entry, _result(7)),
            ),
        ):
            command.func()
        caller.msg.assert_called_once_with("時間經過了 7 秒。")


class SleepCommandGrammarTests(unittest.TestCase):
    """Accepted sleep forms route to the shared rules operation."""

    def _command(self, args):
        caller = SimpleNamespace(msg=Mock(), db=SimpleNamespace())
        command = CmdSleep()
        command.caller = caller
        command.args = args
        return command, caller

    def _run(self, args, outcome):
        command, caller = self._command(args)
        with patch("commands.skip._safe_to_skip", return_value=True), patch(
            "commands.skip.begin_sleep", return_value=outcome
        ) as op:
            command.func()
        return caller, op

    def test_explicit_duration_routes_the_declared_mode(self):
        caller = SimpleNamespace(msg=Mock(), db=SimpleNamespace())
        entry = SleepEntry("synthetic-entry", caller, 7200, False)
        caller_, op = self._run(
            "2h", SleepOutcome(entry, _result(7200))
        )
        op.assert_called_once_with(
            caller_,
            mode="duration",
            seconds=7200,
            scope="self",
            allow_continue=False,
        )
        caller_.msg.assert_called_once_with("時間經過了 7200 秒。")

    def test_all_party_recovery_routes_the_party_scope(self):
        caller, op = self._run(
            "all until-recovered",
            SleepOutcome(None, None, "在場成員已進入睡眠。"),
        )
        op.assert_called_once_with(
            caller,
            mode="recovery",
            seconds=None,
            scope="party",
            allow_continue=False,
        )
        caller.msg.assert_called_once_with("在場成員已進入睡眠。")

    def test_continue_routes_the_shared_continuation(self):
        command, caller = self._command("continue")
        with patch(
            "commands.skip.continue_sleep", return_value=_result(60)
        ) as op:
            command.func()
        op.assert_called_once_with(caller)
        caller.msg.assert_called_once_with("時間經過了 60 秒。")

    def test_malformed_or_contradictory_forms_reject_before_any_write(self):
        for args in ("soon", "2h all", "all continue", "until-recovered 2h"):
            command, caller = self._command(args)
            with patch("commands.skip.begin_sleep") as op:
                command.func()
            op.assert_not_called()
            caller.msg.assert_called_once()
            self.assertIn("用法", caller.msg.call_args.args[0])

    def test_active_plan_refuses_replacement_and_offers_continue(self):
        command, caller = self._command("1h")
        with patch("commands.skip._safe_to_skip", return_value=True), patch(
            "commands.skip.begin_sleep",
            side_effect=SleepRefused(
                "already_asleep",
                "你仍在自願睡眠中；若要繼續，請使用 sleep continue。",
            ),
        ):
            command.func()
        caller.msg.assert_called_once_with(
            "你仍在自願睡眠中；若要繼續，請使用 sleep continue。"
        )

    def test_legacy_dream_form_still_routes_ordinary_sleep(self):
        command, caller = self._command("dream")
        with patch("commands.skip._safe_to_skip", return_value=True), patch(
            "commands.skip.begin_sleep",
            return_value=SleepOutcome(None, None, "已接受睡眠。"),
        ) as op:
            command.func()
        op.assert_called_once_with(
            caller,
            mode="recovery",
            seconds=None,
            scope="self",
            allow_continue=True,
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


@synthetic_registries("skills")
class RestPracticeBookingTests(unittest.TestCase):
    """Declared-practice clause: preflight order, zero-advance, booking state."""

    def _run(self, args: str, caller):
        command = CmdRest()
        command.caller = caller
        command.args = args
        with (
            patch("commands.skip.evaluate_skip_safety", return_value=None),
            patch(
                "commands.skip.advance_wait",
                return_value=_result(28800),
            ) as operation,
        ):
            command.func()
        return operation

    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    def test_valid_booking_is_passed_to_the_single_advance(self):
        caller = _booking_caller(owned=(_PRACTICE_SKILL,))
        operation = self._run(f"8h practice {_PRACTICE_SKILL}", caller)
        operation.assert_called_once_with(
            caller, 28800, practice_skill=_PRACTICE_SKILL
        )

    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    def test_unknown_skill_rejects_with_zero_advance(self):
        caller = _booking_caller(owned=(_PRACTICE_SKILL,))
        operation = self._run("1h practice not_a_skill", caller)
        operation.assert_not_called()
        self.assertIn(
            "PRACTICE_SKILL_UNKNOWN", caller.msg.call_args_list[0].args[0]
        )
        self.assertIsNone(caller.db.practice_booking)

    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    def test_unowned_and_passive_skills_reject_as_unknown(self):
        unowned = _booking_caller(owned=())
        operation = self._run(f"1h practice {_PRACTICE_SKILL}", unowned)
        operation.assert_not_called()
        self.assertIn(
            "PRACTICE_SKILL_UNKNOWN", unowned.msg.call_args_list[0].args[0]
        )
        passive = _booking_caller(owned=(_PASSIVE_SKILL,))
        operation = self._run(f"1h practice {_PASSIVE_SKILL}", passive)
        operation.assert_not_called()
        self.assertIn(
            "PRACTICE_SKILL_UNKNOWN", passive.msg.call_args_list[0].args[0]
        )

    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    def test_capped_skill_rejects_and_leaves_the_standing_booking(self):
        cap = proficiency_cap(_PRACTICE_SKILL)
        caller = _booking_caller(
            owned=(_PRACTICE_SKILL,),
            proficiency={_PRACTICE_SKILL: cap * 50.0},
            booking=_PRACTICE_SKILL,
        )
        operation = self._run(f"8h practice {_PRACTICE_SKILL}", caller)
        operation.assert_not_called()
        self.assertIn("PRACTICE_SKILL_CAPPED", caller.msg.call_args_list[0].args[0])
        self.assertEqual(caller.db.practice_booking, _PRACTICE_SKILL)

    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    def test_plain_rest_passes_no_booking_clause(self):
        caller = _booking_caller(owned=(_PRACTICE_SKILL,), booking=_PRACTICE_SKILL)
        operation = self._run("8h", caller)
        operation.assert_called_once_with(caller, 28800, practice_skill=None)
        self.assertEqual(caller.db.practice_booking, _PRACTICE_SKILL)

    @covers_requirement(
        "skip-safety-gate::the-safety-gate-rejects-outright-it-does-not-"
        "compute-a-partial-safety-shortened"
    )
    def test_safety_gate_rejection_precedes_booking_preflight(self):
        caller = _booking_caller(booking=_PRACTICE_SKILL)
        command = CmdRest()
        command.caller = caller
        command.args = "1h practice not_a_skill"
        with (
            patch(
                "commands.skip.evaluate_skip_safety",
                return_value=SkipRejectReason.HOSTILE_PRESENT,
            ),
            patch("commands.skip.preflight_practice_booking") as preflight,
            patch("commands.skip.advance_wait") as operation,
        ):
            command.func()
        preflight.assert_not_called()
        operation.assert_not_called()
        caller.msg.assert_called_once_with("附近有活著的怪物，這裡不安全。")
        self.assertEqual(caller.db.practice_booking, _PRACTICE_SKILL)

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


@synthetic_registries("skills")
class UnlabeledSkipStandingBookingTests(unittest.TestCase):
    """Accepted unlabeled skips leave standing bookings for the clock stage."""

    @staticmethod
    def _caller():
        return SimpleNamespace(
            msg=Mock(),
            db=SimpleNamespace(practice_booking=_PRACTICE_SKILL),
            traits=SimpleNamespace(
                hp=SimpleNamespace(value=100, max=100, rate=1),
                mp=SimpleNamespace(value=100, max=100, rate=1),
                sp=SimpleNamespace(value=100, max=100, rate=1),
            ),
        )

    @staticmethod
    def _clock(seen: list, caller):
        clock = Mock()
        clock.tick = 0
        clock.advance.return_value = []
        clock.advance.side_effect = lambda *a, **k: (
            seen.append(caller.db.practice_booking),
            [],
        )[1]
        return clock

    @staticmethod
    def _patches(clock, caller):
        return (
            patch("world.rules.time_skip.get_world_clock", return_value=clock),
            patch(
                "world.rules.time_skip.present_party_scope",
                return_value=(caller,),
            ),
            patch("world.rules.time_skip.evaluate_skip_safety", return_value=None),
        )

    @covers_requirement(
        "time-skip-commands::rest-duration-parses-an-explicit-duration-and-"
        "advances-the-clock-by-that-much-capped-at-the-configured-maximum"
    )
    def test_unlabeled_wait_leaves_the_standing_booking_for_the_clock_stage(self):
        caller = self._caller()
        seen: list = []
        clock = self._clock(seen, caller)
        world, scope, safety = self._patches(clock, caller)
        with world, scope, safety:
            result = advance_wait(caller, 3600)
        self.assertEqual(seen, [_PRACTICE_SKILL])
        self.assertEqual(caller.db.practice_booking, _PRACTICE_SKILL)
        self.assertEqual(result.elapsed_seconds, 3600)
        clock.advance.assert_called_once()
        args, kwargs = clock.advance.call_args
        self.assertEqual(args[:3], (3600, AdvanceSource.SKIP, (caller,)))
        self.assertIsNotNone(kwargs["mental"])

    @covers_requirement(
        "skip-safety-gate::the-safety-gate-rejects-outright-it-does-not-"
        "compute-a-partial-safety-shortened"
    )
    def test_unsafe_wait_refuses_without_advancing(self):
        caller = self._caller()
        clock = self._clock([], caller)
        with (
            patch("world.rules.time_skip.get_world_clock", return_value=clock),
            patch(
                "world.rules.time_skip.present_party_scope",
                return_value=(caller,),
            ),
            patch(
                "world.rules.time_skip.evaluate_skip_safety",
                return_value=SkipRejectReason.HOSTILE_PRESENT,
            ),
            self.assertRaises(Exception),
        ):
            advance_wait(caller, 60)
        clock.advance.assert_not_called()


class WaitUntilRoutingTests(unittest.TestCase):
    @covers_requirement(
        "time-skip-commands::wait-until-daypart-computes-seconds-to-the-next-"
        "occurrence-of-a-named-daypart"
    )
    def test_wait_until_routes_the_computed_seconds_once(self):
        caller = SimpleNamespace(msg=Mock(), db=SimpleNamespace())
        clock = SimpleNamespace(tick=0, calendar=object())
        command = CmdWaitUntil()
        command.caller = caller
        command.args = "until dawn"
        with (
            patch("commands.skip.evaluate_skip_safety", return_value=None),
            patch("commands.skip.get_world_clock", return_value=clock),
            patch("commands.skip.seconds_until_daypart", return_value=60),
            patch("commands.skip.advance_wait", return_value=_result(60)) as op,
        ):
            command.func()
        op.assert_called_once_with(caller, 60)
        caller.msg.assert_called_once_with("時間經過了 60 秒。")
