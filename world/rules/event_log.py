"""Serializable records emitted by deterministic action resolution."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EventEntry:
    """One ordered, renderable state-change record."""

    kind: str
    actor: str
    target: str | None
    data: dict[str, Any]
    text_template: str


@dataclass(frozen=True)
class EventLog:
    """The complete deterministic record of one successful action."""

    actor: str
    skill_key: str
    targets: tuple[str, ...]
    entries: tuple[EventEntry, ...]
    time_cost_seconds: int


def render_plain_text(event_log: EventLog) -> str:
    """Render an event log without an LLM or other external service."""
    return "\n".join(
        entry.text_template.format(
            actor=entry.actor,
            target=entry.target,
            data=entry.data,
        )
        for entry in event_log.entries
    )
