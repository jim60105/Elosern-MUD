"""Durable narrative event and projection progress operations."""

from dataclasses import dataclass
from typing import Any, Iterable
import uuid

from django.db import transaction
from django.db.models import QuerySet

from world.narrative.models import NarrativeEvent, ProjectionProgress
from world.rules.titles.awards import AutomaticTitleAward
from world.observability import log_info


#: Maximum code points of a persisted readable location label.
LOCATION_LABEL_MAX_CHARS = 120


@dataclass(frozen=True)
class LocationSnapshot:
    """One settlement-time location reference persisted with a committed fact.

    ``identity`` is the durable identity of the source's actual location owner
    and ``label`` its detached, readable name at settlement. ``known`` states
    whether an identity was recorded at all: an occurrence whose producer held
    no authoritative location carries neither, and its consumers render that
    state explicitly instead of inferring a location later.
    """

    identity: str = ""
    label: str = ""

    @property
    def known(self) -> bool:
        return bool(self.identity)

    def to_content(self) -> dict[str, str]:
        """Return the detached content snapshot a producer persists."""
        return {"id": self.identity, "label": self.label}

    def to_json(self) -> dict[str, Any]:
        """Return the rendered reference; unknown never carries an identity."""
        if not self.identity:
            return {"known": False}
        return {"known": True, "id": self.identity, "label": self.label}


def snapshot_location(location: Any) -> LocationSnapshot:
    """Return the settlement-time reference for one fact's location owner.

    A live location owner yields its durable identity plus its own readable key
    (bounded). A plain identity value (an integer or a non-empty string) yields
    an identity-only reference, because a bare value can never state the owner's
    readable label. ``None`` or an empty value states unknown explicitly and is
    never replaced by a later lookup.
    """
    if isinstance(location, LocationSnapshot):
        return location
    identity = getattr(location, "pk", None)
    if identity is not None:
        label = getattr(location, "key", None)
        if not isinstance(label, str) or not label.strip():
            label = getattr(location, "name", "")
        return LocationSnapshot(
            identity=str(identity),
            label=str(label or "")[:LOCATION_LABEL_MAX_CHARS],
        )
    if isinstance(location, bool):
        return LocationSnapshot()
    if isinstance(location, int):
        return LocationSnapshot(identity=str(location))
    if isinstance(location, str):
        return LocationSnapshot(identity=location.strip())
    return LocationSnapshot()


@dataclass(frozen=True)
class NarrativeEventRecord:
    source_id: str
    event_type: str
    content: dict[str, Any]
    participants: list[str]
    location: str
    tick: int
    visibility: str
    salience: int


def build_encounter_source_id(session_id: str, kind: str = "round", ordinal: int = 1) -> str:
    """Format a stable, unique source identity for an encounter occurrence."""
    clean_session = str(session_id).strip()
    return f"encounter:{clean_session}:{kind}:{int(ordinal)}"


def get_committed_award_results(source_id: str) -> tuple[AutomaticTitleAward, ...] | None:
    """Look up committed automatic title awards for an existing occurrence.

    Returns a tuple of ``AutomaticTitleAward`` records if ``source_id`` exists
    in durable storage (which may be empty ``()`` if no titles were granted),
    or ``None`` if the occurrence has not yet been committed.
    """
    clean_source = str(source_id).strip()
    existing = NarrativeEvent.objects.filter(source_id=clean_source).first()
    if existing is None:
        return None
    raw_awards = existing.content.get("award_results")
    if not isinstance(raw_awards, list):
        return ()
    return tuple(AutomaticTitleAward.from_dict(item) for item in raw_awards if isinstance(item, dict))


def serialize_award_results(awards: Iterable[AutomaticTitleAward | dict[str, Any]]) -> list[dict[str, Any]]:
    """Serialize an iterable of award results into plain JSON dicts."""
    out = []
    for award in awards:
        item = award.to_dict() if isinstance(award, AutomaticTitleAward) else dict(award)
        out.append(item)
    return out


def record_narrative_event(
    *,
    source_id: str,
    event_type: str,
    content: dict[str, Any],
    participants: Iterable[str | int],
    location: str = "",
    tick: int = 0,
    visibility: str = "public",
    salience: int = 1,
    award_results: Iterable[AutomaticTitleAward | dict[str, Any]] = (),
    projector_version: int = 1,
) -> tuple[NarrativeEvent, ProjectionProgress, bool]:
    """Durably record a narrative event and pending projection in the current transaction.

    Idempotent: if `source_id` already exists, returns the existing event and progress
    without mutating the immutable event record or resetting completed progress.
    Returns `(event, progress, created)`.
    """
    clean_source = str(source_id).strip()
    clean_participants = [str(p) for p in participants]
    clean_content = dict(content)
    if award_results:
        clean_content["award_results"] = serialize_award_results(award_results)
    elif "award_results" not in clean_content:
        clean_content["award_results"] = []

    existing_event = NarrativeEvent.objects.filter(source_id=clean_source).first()
    if existing_event is not None:
        progress, _ = ProjectionProgress.objects.get_or_create(
            source_id=clean_source,
            projector_version=projector_version,
            defaults={"status": "pending"},
        )
        return existing_event, progress, False

    with transaction.atomic():
        event = NarrativeEvent.objects.create(
            source_id=clean_source,
            event_type=event_type,
            content=clean_content,
            participants=clean_participants,
            location=str(location or ""),
            tick=int(tick),
            visibility=str(visibility),
            salience=int(salience),
        )
        progress = ProjectionProgress.objects.create(
            source_id=clean_source,
            projector_version=projector_version,
            status="pending",
        )
        # Log boundary event via on_commit of the outermost transaction
        boundary = {
            "source_id": clean_source,
            "event_type": event_type,
            "tick": int(tick),
            "participants": len(clean_participants),
        }
        # Both boundary side effects are recoverable and must never abort the
        # remaining commit callbacks: the projection leaving its row pending
        # IS the documented failure mode, and a raising callback would both
        # skip every later callback and propagate a post-commit error into the
        # caller's rollback compensation as if the transaction had failed.
        transaction.on_commit(
            lambda b=boundary: log_info("narrative_event_recorded", context=b),
            robust=True,
        )
        # Settle memory projection via on_commit of the outermost transaction
        from world.narrative.memory import project_narrative_event_to_memories
        transaction.on_commit(
            lambda e=event, pv=projector_version: project_narrative_event_to_memories(e, projector_version=pv),
            robust=True,
        )
        return event, progress, True


def get_pending_projections(projector_version: int = 1) -> QuerySet[ProjectionProgress]:
    """Retrieve all pending projection progress entries for the given projector version."""
    return ProjectionProgress.objects.filter(
        projector_version=projector_version,
        status="pending",
    ).order_by("id")


def mark_projection_completed(source_id: str, projector_version: int = 1) -> bool:
    """Mark a projection progress entry as completed."""
    rows = ProjectionProgress.objects.filter(
        source_id=str(source_id).strip(),
        projector_version=projector_version,
    ).update(status="completed")
    return rows > 0


def scan_pending_narrative_projections(projector_version: int = 1) -> int:
    """Startup recovery scanner for pending projection rows across restarts."""
    pending_qs = get_pending_projections(projector_version=projector_version)
    count = pending_qs.count()
    log_info(
        "narrative_projection_pending_scanned",
        context={"projector_version": projector_version, "count": count},
    )
    return count
