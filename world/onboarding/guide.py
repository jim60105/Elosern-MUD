"""Pure onboarding beat coordinator and guide-progress schema (D2).

This module decides what to present and which state transition to request from
a plain snapshot of the character's onboarding attributes. It never reads or
writes game state itself: ``world.rules.onboarding`` is the sole writer. It
imports only the onboarding data modules and the Python standard library, so
the dependency direction stays ``rules -> onboarding`` with no cycle.
"""

from dataclasses import dataclass

from .guide_dialogue import DIALOGUE_TABLE, NO_UNDERSTANDING_LINE
from .scenes import (
    BEAT_REGISTRY,
    GUILD_EXTERIOR_ROOM_KEY,
    GUIDED_CORRIDOR,
    LOOK_BEAT_ID,
    SOUTH_GATE_ROOM_KEY,
    Beat,
)


@dataclass(frozen=True)
class GuideProgress:
    """Persisted guide-progress schema owned by the rules service.

    ``state`` is one of ``active``, ``completed``, or ``skipped``.
    ``seen_keywords`` records which guard keywords the player has heard so the
    rules service can persist them through this schema only.
    """

    state: str
    seen_keywords: tuple[str, ...] = ()

    @classmethod
    def active(cls) -> "GuideProgress":
        return cls(state="active")

    def to_storage(self) -> dict[str, object]:
        return {"state": self.state, "seen_keywords": list(self.seen_keywords)}

    @classmethod
    def from_storage(cls, raw: dict[str, object] | None) -> "GuideProgress | None":
        if raw is None:
            return None
        state = raw.get("state")
        if state not in {"active", "completed", "skipped"}:
            raise ValueError(f"invalid guide_progress state {state!r}")
        seen = tuple(raw.get("seen_keywords") or ())
        if not all(isinstance(keyword, str) for keyword in seen):
            raise ValueError("guide_progress seen_keywords must be strings")
        return cls(state=state, seen_keywords=seen)

    def with_keyword(self, keyword: str) -> "GuideProgress":
        if keyword in self.seen_keywords:
            return self
        return GuideProgress(
            state=self.state, seen_keywords=(*self.seen_keywords, keyword)
        )


@dataclass(frozen=True)
class OnboardingSnapshot:
    """Read-only view of the character's onboarding attributes."""

    onboarded: bool
    onboarding_beat: str | None
    guide_progress: GuideProgress | None
    first_arrival_seen: bool
    location_key: str | None


@dataclass(frozen=True)
class BeatOutput:
    """The next beat to present plus the requested state transition."""

    beat: Beat
    next_beat_id: str | None


def current_beat(beat_id: str | None) -> Beat | None:
    """Resolve a persisted beat id against the immutable registry."""
    if beat_id is None:
        return None
    return BEAT_REGISTRY.get(beat_id)


def arrival_scene(snapshot: OnboardingSnapshot) -> tuple[Beat, ...] | None:
    """Return the arrival-scene beats to present, or ``None`` when it must not play.

    The scene plays only for an onboarding character at the South Gate whose
    arrival beat has not been completed yet. A returning, onboarded player at
    the gate never sees it, and neither does a player whose guide has already
    ended (completed or skipped) — reaching the guild exterior ends guidance
    even when the player never completed the ``look`` beat.
    """
    if snapshot.onboarded:
        return None
    if snapshot.location_key != SOUTH_GATE_ROOM_KEY:
        return None
    if snapshot.first_arrival_seen:
        return None
    if snapshot.guide_progress is not None and snapshot.guide_progress.state != "active":
        return None
    return (BEAT_REGISTRY["arrival"], BEAT_REGISTRY[LOOK_BEAT_ID])


def next_beat_output(
    snapshot: OnboardingSnapshot,
) -> BeatOutput | None:
    """Return the continuation of the current beat, if any."""
    current = current_beat(snapshot.onboarding_beat)
    if current is None or current.next_beat_id is None:
        return None
    next_beat = BEAT_REGISTRY[current.next_beat_id]
    return BeatOutput(next_beat, next_beat.next_beat_id)


def guide_should_prompt(snapshot: OnboardingSnapshot) -> bool:
    """Whether the guard should still prompt this character at all."""
    if snapshot.onboarded:
        return False
    progress = snapshot.guide_progress
    if progress is not None and progress.state != "active":
        return False
    return True


def room_entry_decision(snapshot: OnboardingSnapshot, room_key: str) -> str | None:
    """Decide what a room entry means for the guide.

    Returns ``None`` (no change), ``"completed"`` when the player reaches the
    guild exterior, or ``"skipped"`` when the player deviates outside the guided
    corridor without finishing the guide.
    """
    if snapshot.onboarded:
        return None
    if room_key == GUILD_EXTERIOR_ROOM_KEY:
        return "completed"
    if room_key not in GUIDED_CORRIDOR:
        return "skipped"
    return None


def dialogue_response(dialogue_key: str, keyword: str) -> str:
    """Return the authored response for one keyword, or the no-understanding line."""
    definition = DIALOGUE_TABLE.get(dialogue_key)
    if definition is None:
        return NO_UNDERSTANDING_LINE
    for entry in definition.responses:
        if entry.keyword == keyword:
            return entry.response
    return NO_UNDERSTANDING_LINE


def dialogue_has_keyword(dialogue_key: str, keyword: str) -> bool:
    """Whether ``keyword`` has an authored response in the named table."""
    definition = DIALOGUE_TABLE.get(dialogue_key)
    if definition is None:
        return False
    return any(
        entry.keyword == keyword
        for entry in definition.responses
    )
