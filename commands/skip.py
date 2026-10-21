"""Player-facing deterministic rest, sleep, and wait commands.

Duration parsing, the safety gate, sleep entry/continuation, interruptible
boundary composition, and summary rendering all delegate to the shared
``world.rules.time_skip`` operations so the WebClient ``explore.wait`` adapter
and the typed commands can never diverge. Read-only daypart arithmetic uses
the module-level ``get_world_clock`` name.
"""

import re

from commands.command import Command

from world.rules.clock import (
    DaypartError,
    get_world_clock,
    seconds_until_daypart,
)
from world.rules.party_scope import (
    PartyScopeError,
    resolve_member_token,
)
from world.rules.skip_safety import evaluate_skip_safety
from world.rules.time_skip import (
    DurationParseError,
    SkipRefused,
    SleepRefused,
    accepted_wait_handoff_offer,
    advance_wait,
    begin_sleep,
    book_member_practice,
    parse_duration,
    preflight_practice_booking,
    rejection_message,
    render_skip_summary,
)
from world.rules.unlock_notices import deliver_unlocks, notices_from_events

# Thin names retained for the deterministic command tests.
_parse_duration = parse_duration
_render_skip_summary = render_skip_summary


def _safe_to_skip(caller) -> bool:
    reason = evaluate_skip_safety(caller)
    if reason is None:
        return True
    caller.msg(rejection_message(reason))
    return False


def _with_handoff_offer(caller, message: str) -> str:
    """Append the post-commit sleep handoff offer, when one now exists."""
    offer = accepted_wait_handoff_offer(caller)
    return message if offer is None else f"{message}\n{offer}"


# ``rest <duration> [practice <skill>]``: a duration token plus an optional
# declared-practice clause naming a skill key (whitespace-free by contract).
_REST_ARGS_RE = re.compile(
    r"^(?P<duration>\S+)(?:\s+practice\s+(?P<skill>\S+))?$"
)

_REST_USAGE = "用法：rest <數字><s|m|h|d> [practice <技能>]"
_NO_DREAM_MESSAGE = "身體已完全恢復，沒有進入夢境。"

# ``修煉 <技能> [= <成員>]``: one whitespace-free skill key plus an optional
# member token naming a present party member (default: the caller).
_PRACTICE_ARGS_RE = re.compile(
    r"^(?P<skill>\S+)(?:\s*=\s*(?P<member>\S.*))?$"
)

_PRACTICE_USAGE = "用法：修煉 <技能> [= <成員>]"


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
                # A rejected clause leaves the caller's standing booking
                # exactly as it was; nothing is half-applied.
                self.caller.msg(reject.message)
                return
        # An accepted clause records the caller's standing booking (replacing
        # a previous one); a clause-less rest records nothing and settles only
        # the present members' standing bookings. The shared operation
        # truncates the request at the earliest relevant boundary, and the
        # clock's practice_settlement stage remains the sole consumer/writer.
        try:
            result = advance_wait(
                self.caller, seconds, practice_skill=skill_key
            )
        except SkipRefused as error:
            self.caller.msg(rejection_message(error.reason))
            return
        self.caller.msg(
            _with_handoff_offer(
                self.caller,
                _render_skip_summary(result.elapsed_seconds, result.events),
            )
        )
        # The summary already carries each committed unlock line; record the
        # session unread marks from the same committed events.
        deliver_unlocks(
            self.caller, notices_from_events(result.events), announce=False
        )
        _maybe_nominate_after_rest(self.caller, result.events)


class CmdSleep(Command):
    key = "sleep"
    aliases = ("睡眠",)

    def func(self) -> None:
        choice = self.args.strip()
        if choice not in ("", "dream"):
            self.caller.msg("用法：sleep [dream]")
            return
        if not _safe_to_skip(self.caller):
            return
        try:
            outcome = begin_sleep(self.caller)
        except SkipRefused as error:
            self.caller.msg(rejection_message(error.reason))
            return
        except SleepRefused as error:
            self.caller.msg(error.message)
            return
        if outcome.message is not None:
            self.caller.msg(outcome.message)
            return
        result = outcome.result
        assert result is not None
        self.caller.msg(
            _with_handoff_offer(
                self.caller,
                _render_skip_summary(result.elapsed_seconds, result.events),
            )
        )
        deliver_unlocks(
            self.caller, notices_from_events(result.events), announce=False
        )
        _maybe_nominate_after_rest(self.caller, result.events)
        if choice:
            from commands.dream import render_state
            from server.dream_service import enter_after_sleep

            if not result.voluntary or result.elapsed_seconds <= 0:
                self.caller.msg(_NO_DREAM_MESSAGE)
                return
            state = enter_after_sleep(
                self.caller,
                tick_from=int(get_world_clock().tick) - result.elapsed_seconds,
                tick_to=int(get_world_clock().tick),
                requested_seconds=result.requested_seconds,
                elapsed_seconds=result.elapsed_seconds,
                voluntary=result.voluntary,
                events=result.events,
            )
            self.caller.msg(render_state(state))

class CmdWaitUntil(Command):
    key = "wait"
    aliases = ("等待", "w")

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
        try:
            result = advance_wait(self.caller, seconds)
        except SkipRefused as error:
            self.caller.msg(rejection_message(error.reason))
            return
        self.caller.msg(
            _with_handoff_offer(
                self.caller,
                _render_skip_summary(result.elapsed_seconds, result.events),
            )
        )
        deliver_unlocks(
            self.caller, notices_from_events(result.events), announce=False
        )
        _maybe_nominate_after_rest(self.caller, result.events)


class CmdPractice(Command):
    """Book one present party member's practice for the next time skip."""

    key = "修煉"
    aliases = ("practice",)
    help_category = "General"

    def func(self) -> None:
        match = _PRACTICE_ARGS_RE.fullmatch(self.args.strip())
        if match is None:
            self.caller.msg(_PRACTICE_USAGE)
            return
        member = self.caller
        member_token = match["member"]
        if member_token is not None:
            try:
                member = resolve_member_token(self.caller, member_token)
            except PartyScopeError as error:
                self.caller.msg(error.message)
                return
        try:
            booking = book_member_practice(
                self.caller, member.pk, match["skill"]
            )
        except PartyScopeError as error:
            self.caller.msg(error.message)
            return
        # Both outcomes carry the player-facing line: the booking
        # confirmation, or the stable rejection message.
        self.caller.msg(booking.message)
