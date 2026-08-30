"""Player-facing deterministic rest, sleep, and wait commands.

The duration parsing, full-regen computation, safety gate, and summary
rendering all delegate to the shared ``world.rules.time_skip`` helper (design
D7) so the WebClient ``explore.wait`` adapter and the typed commands can never
diverge. The clock advance uses the module-level ``get_world_clock`` name so
the deterministic command tests can keep patching it.
"""

import re

from evennia import Command

from world.rules.clock import (
    AdvanceSource,
    DaypartError,
    get_world_clock,
    seconds_until_daypart,
)
from world.rules.skip_safety import evaluate_skip_safety
from world.rules.time_skip import (
    DurationParseError,
    parse_duration,
    preflight_practice_booking,
    rejection_message,
    render_skip_summary,
    seconds_to_full_regen,
)

# Thin names retained for the deterministic command tests.
_parse_duration = parse_duration
_seconds_to_full_regen = seconds_to_full_regen
_render_skip_summary = render_skip_summary


def _safe_to_skip(caller) -> bool:
    reason = evaluate_skip_safety(caller)
    if reason is None:
        return True
    caller.msg(rejection_message(reason))
    return False


# ``rest <duration> [practice <skill>]``: a duration token plus an optional
# declared-practice clause naming a skill key (whitespace-free by contract).
_REST_ARGS_RE = re.compile(
    r"^(?P<duration>\S+)(?:\s+practice\s+(?P<skill>\S+))?$"
)

_REST_USAGE = "用法：rest <數字><s|m|h|d> [practice <技能>]"
def _maybe_nominate_after_rest(caller, events) -> None:
    """Rest-point nomination trigger (title-system D4 §7.1, change G).

    Fires only when the SKIP-source advance crossed a world-clock day
    boundary. The composition-root import is function-local (the
    ``commands/scene.py`` precedent) and every failure is swallowed: resting
    can never be broken by nomination, and the stage is a silent no-op
    offline.
    """
    try:
        from server.title_nomination_service import (
            schedule_rest_boundary_nomination,
        )

        schedule_rest_boundary_nomination(caller, events)
    except Exception:
        pass


class CmdRest(Command):
    key = "rest"
    aliases = ("休息",)

    def func(self) -> None:
        # Fixed order: parse -> safety gate -> booking preflight -> advance.
        # Every rejection performs ZERO clock advance; a skip never
        # half-applies (declared-practice-skip D7).
        match = _REST_ARGS_RE.fullmatch(self.args.strip())
        if match is None:
            self.caller.msg(_REST_USAGE)
            return
        try:
            seconds = _parse_duration(match["duration"])
        except DurationParseError:
            self.caller.msg(_REST_USAGE)
            return
        if not _safe_to_skip(self.caller):
            return
        skill_key = match["skill"]
        if skill_key is not None:
            reject = preflight_practice_booking(self.caller, skill_key)
            if reject is not None:
                # Rejected bookings leave no practice state at all: not even
                # a stale earlier booking may settle later.
                self.caller.db.practice_booking = None
                self.caller.msg(reject.message)
                return
        # The booking always reflects THIS command's declared intention: an
        # accepted clause records it, a clause-less explicit rest clears any
        # stale booking (plain rest grows nothing), and the clock's
        # practice_settlement stage is the sole consumer/writer.
        self.caller.db.practice_booking = skill_key
        events = get_world_clock().advance(seconds, AdvanceSource.SKIP, [self.caller])
        self.caller.msg(_render_skip_summary(seconds, events))
        _maybe_nominate_after_rest(self.caller, events)


class CmdSleep(Command):
    key = "sleep"
    aliases = ("睡眠",)

    def func(self) -> None:
        if not _safe_to_skip(self.caller):
            return
        seconds = _seconds_to_full_regen(self.caller)
        self.caller.db.practice_booking = None  # unlabeled skips grow nothing
        events = get_world_clock().advance(seconds, AdvanceSource.SKIP, [self.caller])
        self.caller.msg(_render_skip_summary(seconds, events))
        _maybe_nominate_after_rest(self.caller, events)


class CmdWaitUntil(Command):
    key = "wait"
    aliases = ("等待",)

    def func(self) -> None:
        prefix = "until "
        if not self.args.strip().startswith(prefix):
            self.caller.msg("用法：wait until <midnight|dawn|noon|dusk>")
            return
        daypart = self.args.strip()[len(prefix):].strip()
        try:
            clock = get_world_clock()
            seconds = seconds_until_daypart(clock.calendar, daypart)
        except DaypartError:
            self.caller.msg("未知的時段。")
            return
        if not _safe_to_skip(self.caller):
            return
        self.caller.db.practice_booking = None  # unlabeled skips grow nothing
        events = clock.advance(seconds, AdvanceSource.SKIP, [self.caller])
        self.caller.msg(_render_skip_summary(seconds, events))
        _maybe_nominate_after_rest(self.caller, events)
