"""Serializable records emitted by deterministic action resolution.

``actor`` and ``target`` are the readable display labels a narration template
fills; they are never identity. A participant-bearing record additionally
carries the stable individual identity of each side
(:func:`world.rules.combat.decision_scope.stable_actor_id`), so a consumer that
attributes, credits or targets never has to parse a label and two same-label
individuals can never be confused. A record that legitimately has no
participant (a team summary, a source-less casualty) leaves its identity
fields ``None``.
"""

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
    # Stable individual identities behind the prose labels, or ``None`` for a
    # record that names no participant on that side.
    actor_id: str | None = None
    target_id: str | None = None


@dataclass(frozen=True)
class EventLog:
    """The complete deterministic record of one successful action."""

    actor: str
    skill_key: str
    targets: tuple[str, ...]
    entries: tuple[EventEntry, ...]
    time_cost_seconds: int
    # The acting participant's stable identity (``None`` for a system/summary
    # log) and the resolved recipients' identities in resolution order.
    actor_id: str | None = None
    target_ids: tuple[str, ...] = ()


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
