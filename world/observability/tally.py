"""Counting scope for per-entity world-maintenance events.

A population lifecycle settlement pass emits one event per body or group it
moves. Those lines are unobserved maintenance, so the pass opens this scope:
inside it the five maintenance events are logged at debug level and counted,
and the pass emits a single info summary on durable commit.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

MAINTENANCE_EVENTS: frozenset[str] = frozenset(
    {
        "fatigue_transition",
        "monster_activity_decided",
        "monster_departed",
        "monster_arrived",
        "monster_arrival_deferred",
    }
)

_ACTIVE: dict[str, int] | None = None


@contextmanager
def maintenance_tally() -> Iterator[dict[str, int]]:
    """Open the counting scope; a nested call reuses the open scope."""
    global _ACTIVE
    if _ACTIVE is not None:
        yield _ACTIVE
        return
    counts: dict[str, int] = {}
    _ACTIVE = counts
    try:
        yield counts
    finally:
        _ACTIVE = None


@contextmanager
def suspended_maintenance_tally() -> Iterator[None]:
    """Run the enclosed work with no scope, then resume the same scope."""
    global _ACTIVE
    previous = _ACTIVE
    _ACTIVE = None
    try:
        yield
    finally:
        _ACTIVE = previous


def note_maintenance(event: str) -> bool:
    """Count ``event`` in the open scope and return True; False with no scope."""
    if event not in MAINTENANCE_EVENTS:
        raise ValueError(f"not a maintenance event: {event!r}")
    if _ACTIVE is None:
        return False
    _ACTIVE[event] = _ACTIVE.get(event, 0) + 1
    return True


__all__ = [
    "MAINTENANCE_EVENTS",
    "maintenance_tally",
    "note_maintenance",
    "suspended_maintenance_tally",
]
