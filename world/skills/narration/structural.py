"""Structural combat prose owned by the narration catalog.

The round marker, terminal announcements, engagement opening, overwhelm
summary, and party-retreat lines stay single stable authored lines (design
D10): the client's beat playback anchors on them, and the per-entry prose
above them carries the story.
"""

from __future__ import annotations

from .pools import (
    CONTINUE_MESSAGE,
    ENGAGEMENT_OPENING_TEMPLATE,
    OVERWHELM_SUMMARY_LINE,
    PARTY_RETREAT_LINES,
    TERMINAL_OUTCOME_MESSAGES,
)


def terminal_outcome_message(outcome: str) -> str:
    """Return the stable announcement for one terminal session outcome."""
    return TERMINAL_OUTCOME_MESSAGES.get(outcome, CONTINUE_MESSAGE)


def engagement_opening_line(name: str) -> str:
    """Return the authored engagement opening naming the engaged foe."""
    return ENGAGEMENT_OPENING_TEMPLATE.format(name=name)


def overwhelm_summary_line() -> str:
    """Return the numberless overwhelm resolution summary template."""
    return OVERWHELM_SUMMARY_LINE


def party_retreat_line(escaped: bool) -> str:
    """Return the stable party-retreat line for one verdict."""
    return PARTY_RETREAT_LINES["escaped" if escaped else "failed"]


__all__ = [
    "engagement_opening_line",
    "overwhelm_summary_line",
    "party_retreat_line",
    "terminal_outcome_message",
]
