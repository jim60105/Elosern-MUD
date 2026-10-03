"""Durable narrative event and projection progress operations."""

from dataclasses import dataclass
from typing import Any, Iterable
import uuid

from django.db import transaction
from django.db.models import QuerySet

from world.narrative.models import NarrativeEvent, ProjectionProgress
from world.observability import log_info


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
        transaction.on_commit(
            lambda b=boundary: log_info("narrative_event_recorded", context=b)
        )
        # Settle memory projection via on_commit of the outermost transaction
        from world.narrative.memory import project_narrative_event_to_memories
        transaction.on_commit(
            lambda e=event, pv=projector_version: project_narrative_event_to_memories(e, projector_version=pv)
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
