"""The process-wide time of the last player input.

Written at the two ingress points of ``server/conf/inputfuncs.py``. Read by a
background caller that must not run while a player is acting. The value is a
monotonic clock reading, held in memory only: a reload starts with no input
recorded, which reads as idle.
"""

from __future__ import annotations

import time

#: The monotonic reading of the last player input, or ``None`` before any.
_LAST_INPUT: float | None = None


def _now() -> float:
    """The monotonic clock; the one seam a test replaces."""
    return time.monotonic()


def note_player_input() -> None:
    """Record that a player sent input now."""
    global _LAST_INPUT
    _LAST_INPUT = _now()


def seconds_since_player_input() -> float | None:
    """Real seconds since the last player input; ``None`` when none was recorded."""
    if _LAST_INPUT is None:
        return None
    return _now() - _LAST_INPUT


def reset_player_input() -> None:
    """Forget the recorded input (process start state; used by tests)."""
    global _LAST_INPUT
    _LAST_INPUT = None


__all__ = ["note_player_input", "reset_player_input", "seconds_since_player_input"]
