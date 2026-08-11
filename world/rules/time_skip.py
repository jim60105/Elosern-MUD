"""Shared deterministic time-skip helper (webclient-exploration-menu D7).

The ``rest``/``sleep``/``wait`` commands and the WebClient ``explore.wait``
adapter share one helper so duration parsing, the bounded full-regen
computation, the safety gate, and clock advancement can never diverge. This
module owns the ``clock.yaml`` bounds, the ``evaluate_skip_safety`` gate, and
the ``AdvanceSource.SKIP`` execution; callers never advance time themselves.

``rest`` caps its parsed duration at ``MAX_SKIP_SECONDS``
(``CLOCK_YAML["max_sleep_seconds"]``), the same bound ``sleep`` uses for its
computed full-regen duration. The WebClient ``explore.wait`` ``seconds``
payload is bounded by the documented protocol-level ``MAX_WEB_SKIP_SECONDS``,
which equals ``MAX_SKIP_SECONDS``; none of the bounds change command behavior
beyond the configured maximum.
"""

import math
import re
from typing import Any

from world.rules.clock import (
    AdvanceSource,
    CLOCK_YAML,
    ScheduledEvent,
    get_world_clock,
)
from world.rules.skip_safety import SkipRejectReason, evaluate_skip_safety
from world.rules.traits import GAUGE_KEYS


class DurationParseError(ValueError):
    """Raised for an explicit rest duration with unsupported syntax."""


# The four named dayparts accepted by ``wait`` and ``explore.wait``.
DAYPARTS = ("midnight", "dawn", "noon", "dusk")

# Cap for explicit ``rest`` durations and the full-regen ``sleep`` duration.
MAX_SKIP_SECONDS = CLOCK_YAML["max_sleep_seconds"]

# Protocol-level bound for the WebClient ``explore.wait`` ``seconds`` value.
MAX_WEB_SKIP_SECONDS = MAX_SKIP_SECONDS

_DURATION_RE = re.compile(r"^(?P<amount>\d+)\s*(?P<unit>[smhd])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_REJECTION_MESSAGES = {
    SkipRejectReason.IN_COMBAT: "你仍在戰鬥中，無法跳過時間。",
    SkipRejectReason.HOSTILE_PRESENT: "附近有活著的怪物，這裡不安全。",
}


def parse_duration(text: str) -> int:
    """Parse an explicit ``<number><s|m|h|d>`` rest duration into seconds.

    The result is clamped to ``MAX_SKIP_SECONDS`` so ``rest`` can never drive
    an unbounded clock advance; durations at or under the cap parse exactly.
    """
    match = _DURATION_RE.fullmatch(text.strip())
    if match is None:
        raise DurationParseError("duration must use <number><s|m|h|d>")
    try:
        seconds = int(match["amount"]) * _UNIT_SECONDS[match["unit"]]
    except ValueError:
        # Absurdly long digit strings exceed Python's int-string limit; any
        # such duration is astronomically over the cap, so clamp directly.
        return MAX_SKIP_SECONDS
    return min(seconds, MAX_SKIP_SECONDS)


def seconds_to_full_regen(entity: Any) -> int:
    """Return the bounded seconds to fully regenerate every gauge."""
    seconds = 0
    for key in GAUGE_KEYS:
        gauge = getattr(entity.traits, key)
        rate = float(getattr(gauge, "rate", 0))
        if rate > 0 and gauge.value < gauge.max:
            seconds = max(seconds, math.ceil((gauge.max - gauge.value) / rate))
    return min(seconds, CLOCK_YAML["max_sleep_seconds"])


def render_skip_summary(seconds: int, events: list[ScheduledEvent]) -> str:
    """Render the stable skip summary from the settled events."""
    message = f"時間經過了 {seconds} 秒。"
    if any(event.kind == "daily_reset" for event in events):
        message += " 新的一天開始了。"
    return message


def rejection_message(reason: SkipRejectReason) -> str | None:
    """Return the safe rejection message for one skip-safety reason."""
    return _REJECTION_MESSAGES.get(reason)


def unsafe_rejection(actor: Any) -> str | None:
    """Return the skip-safety rejection message when skipping is unsafe.

    Returns ``None`` when the actor may skip; otherwise the exact safe
    Traditional Chinese rejection for the current reason (active combat or a
    co-located living monster).
    """
    reason = evaluate_skip_safety(actor)
    if reason is None:
        return None
    return _REJECTION_MESSAGES[reason]


def advance_skip(actor: Any, seconds: int) -> list[ScheduledEvent]:
    """Advance the world clock exactly like ``rest``/``sleep``/``wait``.

    ``seconds`` must already be safe and validated; this call performs the
    single ``AdvanceSource.SKIP`` advance and returns the settled events.
    """
    return get_world_clock().advance(seconds, AdvanceSource.SKIP, [actor])


__all__ = [
    "DAYPARTS",
    "DurationParseError",
    "MAX_SKIP_SECONDS",
    "MAX_WEB_SKIP_SECONDS",
    "advance_skip",
    "parse_duration",
    "rejection_message",
    "render_skip_summary",
    "seconds_to_full_regen",
    "unsafe_rejection",
]
