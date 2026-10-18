"""Player-facing deterministic rest, sleep, and wait commands.

The duration parsing, full-regen computation, safety gate, and summary
rendering all delegate to the shared ``world.rules.time_skip`` helper (design
D7) so the WebClient ``explore.wait`` adapter and the typed commands can never
diverge. The clock advance uses the module-level ``get_world_clock`` name so
the deterministic command tests can keep patching it.
"""

import re

from commands.command import Command

from world.rules.clock import (
    AdvanceSource,
    DaypartError,
    get_world_clock,
    seconds_until_daypart,
)
from world.rules.party_scope import (
    PartyScopeError,
    present_party_scope,
    resolve_member_token,
)
from world.rules.skip_safety import evaluate_skip_safety
from world.rules.time_skip import (
    DurationParseError,
    book_member_practice,
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
        # the present members' standing bookings. The clock's
        # practice_settlement stage remains the sole consumer/writer.
        entities = present_party_scope(self.caller)
        previous_booking = None
        if skill_key is not None:
            previous_booking = self.caller.db.practice_booking
            self.caller.db.practice_booking = skill_key
        try:
            events = get_world_clock().advance(
                seconds, AdvanceSource.SKIP, entities
            )
        except Exception:
            # The clock's rollback restores its entry snapshot, which already
            # contains this declaration; restoring the caller's previous
            # booking keeps a failed clause from replacing a standing one.
            if skill_key is not None:
                self.caller.db.practice_booking = previous_booking
            raise
        self.caller.msg(_render_skip_summary(seconds, events))
        _maybe_nominate_after_rest(self.caller, events)


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
        seconds = _seconds_to_full_regen(self.caller)
        entities = present_party_scope(self.caller)
        # An unlabeled skip records no booking and leaves the present
        # members' standing bookings for the clock's practice stage.
        clock = get_world_clock()
        tick_from = int(clock.tick) if choice else None
        events = clock.advance(seconds, AdvanceSource.SKIP, entities)
        settled_seconds = int(clock.tick) - tick_from if choice else seconds
        self.caller.msg(_render_skip_summary(settled_seconds, events))
        _maybe_nominate_after_rest(self.caller, events)
        if choice:
            from server.dream_service import enter_after_sleep
            from commands.dream import render_state
            state = enter_after_sleep(
                self.caller, tick_from=tick_from, tick_to=int(clock.tick),
                requested_seconds=seconds, events=events,
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
        entities = present_party_scope(self.caller)
        # An unlabeled skip records no booking and leaves the present
        # members' standing bookings for the clock's practice stage.
        events = clock.advance(seconds, AdvanceSource.SKIP, entities)
        self.caller.msg(_render_skip_summary(seconds, events))
        _maybe_nominate_after_rest(self.caller, events)


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
