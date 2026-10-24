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
    continue_owner_sleep,
    continue_sleep,
    owner_sleep_view_state,
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
    if offer is not None:
        message = f"{message}\n{offer}"
    from server.dream_service import pending_sleep_question

    question = pending_sleep_question(caller)
    return message if question is None else f"{message}\n{question}"


# ``rest <duration> [practice <skill>]``: a duration token plus an optional
# declared-practice clause naming a skill key (whitespace-free by contract).
_REST_ARGS_RE = re.compile(
    r"^(?P<duration>\S+)(?:\s+practice\s+(?P<skill>\S+))?$"
)

_REST_USAGE = "用法：rest <數字><s|m|h|d> [practice <技能>]"
_SLEEP_ACCEPTED_MESSAGE = "你進入睡眠。"
_SLEEP_USAGE = (
    "用法：sleep [<時長>|until-recovered]、"
    "sleep all [<時長>|until-recovered]、sleep continue"
)

# ``修煉 <技能> [= <成員>]``: one whitespace-free skill key plus an optional
# member token naming a present party member (default: the caller).
_PRACTICE_ARGS_RE = re.compile(
    r"^(?P<skill>\S+)(?:\s*=\s*(?P<member>\S.*))?$"
)

_PRACTICE_USAGE = "用法：修煉 <技能> [= <成員>]"





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
        

class CmdSleep(Command):
    key = "sleep"
    aliases = ("睡眠",)

    def _request(
        self, tokens: list[str]
    ) -> tuple[str, int | None, bool] | None:
        """Parse the accepted sleep argument forms into ``(mode, seconds, explicit)``."""
        from world.rules.sleep_receipt import MODE_DURATION, MODE_RECOVERY

        if not tokens:
            return MODE_RECOVERY, None, False
        if len(tokens) != 1:
            return None
        token = tokens[0]
        if token in ("until-recovered", "until_recovered"):
            return MODE_RECOVERY, None, True
        try:
            seconds = parse_duration(token)
        except DurationParseError:
            return None
        if seconds < 1:
            return None
        return MODE_DURATION, seconds, True

    def func(self) -> None:
        choice = self.args.strip()
        tokens = choice.split()
        scope = "self"
        if tokens and tokens[0] == "all":
            scope = "party"
            tokens = tokens[1:]
        if tokens == ["continue"]:
            if scope == "party":
                self.caller.msg(_SLEEP_USAGE)
                return
            try:
                owner_state = owner_sleep_view_state(self.caller)
                if owner_state is not None:
                    if owner_state["pending"]:
                        from server.dream_service import answer_sleep_dream

                        answer = answer_sleep_dream(
                            self.caller,
                            decision="decline",
                            sleep_id=owner_state["sleep_id"],
                            revision=owner_state["revision"],
                            generation=owner_state["generation"],
                        )
                        if answer["outcome"] != "success":
                            self.caller.msg(answer["message"])
                            return
                        current = owner_sleep_view_state(self.caller)
                        if current is None:
                            self.caller.msg(answer["message"])
                            return
                    result = continue_owner_sleep(
                        self.caller,
                        sleep_id=owner_state["sleep_id"],
                        expected_generation=owner_state["generation"],
                    )
                else:
                    result = continue_sleep(self.caller)
            except SkipRefused as error:
                self.caller.msg(rejection_message(error.reason))
                return
            except SleepRefused as error:
                self.caller.msg(error.message)
                return
            self.caller.msg(
                _with_handoff_offer(
                    self.caller,
                    result.summary
                    or _render_skip_summary(
                        result.elapsed_seconds, list(result.events)
                    ),
                )
            )
            deliver_unlocks(
                self.caller, notices_from_events(result.events), announce=False
            )
            return
        request = self._request(tokens)
        if request is None:
            self.caller.msg(_SLEEP_USAGE)
            return
        if not _safe_to_skip(self.caller):
            return
        mode, seconds, explicit = request
        try:
            if scope == "party":
                from world.rules.sleep_control import begin_all_party_sleep

                outcome = begin_all_party_sleep(
                    self.caller,
                    mode=mode,
                    seconds=seconds,
                    session=getattr(self, "session", None),
                )
                self.caller.msg(
                    _with_handoff_offer(
                        self.caller,
                        getattr(outcome, "message", None)
                        or _SLEEP_ACCEPTED_MESSAGE,
                    )
                )
                return
            outcome = begin_sleep(
                self.caller,
                mode=mode,
                seconds=seconds,
                scope=scope,
                allow_continue=not explicit,
            )
        except SkipRefused as error:
            self.caller.msg(rejection_message(error.reason))
            return
        except SleepRefused as error:
            self.caller.msg(error.message)
            return
        if outcome.message is not None:
            self.caller.msg(_with_handoff_offer(self.caller, outcome.message))
            return
        result = outcome.result
        if result is None:
            self.caller.msg(
                _with_handoff_offer(self.caller, _SLEEP_ACCEPTED_MESSAGE)
            )
            return
        self.caller.msg(
            _with_handoff_offer(
                self.caller,
                result.summary
                or _render_skip_summary(
                    result.elapsed_seconds, list(result.events)
                ),
            )
        )
        deliver_unlocks(
            self.caller, notices_from_events(result.events), announce=False
        )

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
