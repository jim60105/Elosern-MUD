"""Player-facing deterministic rest, sleep, and wait commands."""

import math
import re

from evennia import Command

from world.rules.clock import (
    AdvanceSource,
    CLOCK_YAML,
    DaypartError,
    ScheduledEvent,
    get_world_clock,
    seconds_until_daypart,
)
from world.rules.skip_safety import SkipRejectReason, evaluate_skip_safety
from world.rules.traits import GAUGE_KEYS


class DurationParseError(ValueError):
    """Raised for an explicit rest duration with unsupported syntax."""


_DURATION_RE = re.compile(r"^(?P<amount>\d+)\s*(?P<unit>[smhd])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_REJECTIONS = {
    SkipRejectReason.IN_COMBAT: "你仍在戰鬥中，無法跳過時間。",
    SkipRejectReason.HOSTILE_PRESENT: "附近有活著的怪物，這裡不安全。",
}


def _parse_duration(text: str) -> int:
    match = _DURATION_RE.fullmatch(text.strip())
    if match is None:
        raise DurationParseError("duration must use <number><s|m|h|d>")
    return int(match["amount"]) * _UNIT_SECONDS[match["unit"]]


def _seconds_to_full_regen(entity) -> int:
    seconds = 0
    for key in GAUGE_KEYS:
        gauge = getattr(entity.traits, key)
        rate = float(getattr(gauge, "rate", 0))
        if rate > 0 and gauge.value < gauge.max:
            seconds = max(seconds, math.ceil((gauge.max - gauge.value) / rate))
    return min(seconds, CLOCK_YAML["max_sleep_seconds"])


def _render_skip_summary(seconds: int, events: list[ScheduledEvent]) -> str:
    message = f"時間經過了 {seconds} 秒。"
    if any(event.kind == "daily_reset" for event in events):
        message += " 新的一天開始了。"
    return message


def _safe_to_skip(caller) -> bool:
    reason = evaluate_skip_safety(caller)
    if reason is None:
        return True
    caller.msg(_REJECTIONS[reason])
    return False


class CmdRest(Command):
    key = "rest"
    aliases = ("休息",)

    def func(self) -> None:
        try:
            seconds = _parse_duration(self.args)
        except DurationParseError:
            self.caller.msg("用法：rest <數字><s|m|h|d>")
            return
        if not _safe_to_skip(self.caller):
            return
        events = get_world_clock().advance(seconds, AdvanceSource.SKIP, [self.caller])
        self.caller.msg(_render_skip_summary(seconds, events))


class CmdSleep(Command):
    key = "sleep"
    aliases = ("睡眠",)

    def func(self) -> None:
        if not _safe_to_skip(self.caller):
            return
        seconds = _seconds_to_full_regen(self.caller)
        events = get_world_clock().advance(seconds, AdvanceSource.SKIP, [self.caller])
        self.caller.msg(_render_skip_summary(seconds, events))


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
        events = clock.advance(seconds, AdvanceSource.SKIP, [self.caller])
        self.caller.msg(_render_skip_summary(seconds, events))
