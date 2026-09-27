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


def render_entry_text(entry: EventEntry) -> str:
    """Render one entry into its own line of plain text.

    The single ``text_template.format`` call of the text channel: the combat
    beats panel (design §10.1 of
    ``docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md``,
    change ``combat-beats-panel``) reuses it so a beat's ``text`` is
    one-to-one with the line the ordinary text output already delivered.
    """
    return entry.text_template.format(
        actor=entry.actor,
        target=entry.target,
        data=entry.data,
    )


def render_plain_text(event_log: EventLog) -> str:
    """Render an event log without an LLM or other external service."""
    return "\n".join(render_entry_text(entry) for entry in event_log.entries)
