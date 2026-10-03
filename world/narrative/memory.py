"""Owner-scoped memory models and business logic.

Preserves character knowledge and beliefs with immutable provenance,
permission boundaries, and recoverable effective-state revision history.
"""

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from django.db import transaction
from django.db.models import F

from world.narrative.models import (
    MemoryRecord,
    MemoryRevision,
    NarrativeEvent,
    OwnerMemoryGeneration,
    ProjectionProgress,
)
from world.observability import log_error, log_info

VALID_SCOPES = frozenset({"witnessed", "told", "inferred", "public"})
VALID_AVAILABILITY = frozenset({"active", "superseded", "inactive"})
VALID_TIERS = frozenset({"core", "working", "archive"})

# Forbidden categories / tags for private authoring
PRIVATE_AUTHORING_CATEGORIES = frozenset({"dream_authoring", "private_authoring", "authoring_draft"})


class NarrativeMemoryError(Exception):
    """Base exception for narrative memory errors."""


class NarrativeMemoryPermissionError(NarrativeMemoryError):
    """Raised when access violates memory ownership or privacy boundaries."""


class NarrativeMemoryImmutabilityError(NarrativeMemoryError):
    """Raised when an attempt is made to mutate immutable record fields."""


@dataclass(frozen=True)
class MemoryRecordView:
    """Detached, immutable plain-value representation of an owner memory."""

    id: int
    owner_id: str
    tick: int
    category: str
    content: dict[str, Any]
    salience: int
    knowledge_scope: str
    confidence: float
    subjects: list[Any]
    source_id: str
    projector_version: Optional[int]
    derived_generation: Optional[int]
    tier: str
    availability: str
    revision_number: int
    decay_metadata: dict[str, Any]
    relations: dict[str, Any]


def _increment_owner_generation(owner_id: str) -> int:
    """Atomically increment and return the memory generation counter for an owner."""
    clean_owner = str(owner_id).strip()
    gen_obj, created = OwnerMemoryGeneration.objects.get_or_create(
        owner_id=clean_owner,
        defaults={"generation": 1},
    )
    if not created:
        OwnerMemoryGeneration.objects.filter(owner_id=clean_owner).update(
            generation=F("generation") + 1
        )
        gen_obj.refresh_from_db(fields=["generation"])
    return int(gen_obj.generation)


def get_owner_generation(owner_id: str) -> int:
    """Get the current memory generation for an owner."""
    clean_owner = str(owner_id).strip()
    gen_obj = OwnerMemoryGeneration.objects.filter(owner_id=clean_owner).first()
    return int(gen_obj.generation) if gen_obj else 0


def record_memory(
    *,
    owner_id: str,
    content: dict[str, Any],
    tick: int = 0,
    category: str = "observation",
    tier: str = "working",
    salience: int = 1,
    knowledge_scope: str = "witnessed",
    confidence: float = 1.0,
    subjects: Optional[Iterable[Any]] = None,
    source_id: str = "",
    projector_version: Optional[int] = None,
    derived_generation: Optional[int] = None,
    decay_metadata: Optional[dict[str, Any]] = None,
    relations: Optional[dict[str, Any]] = None,
) -> tuple[MemoryRecord, MemoryRevision, bool]:
    """Atomically record an owner memory with immutable provenance and initial revision.

    If projector_version and source_id are set, uses unique constraint to ensure idempotency.
    Returns (record, revision, created).
    """
    clean_owner = str(owner_id).strip()
    clean_scope = str(knowledge_scope).strip()
    if clean_scope not in VALID_SCOPES:
        raise ValueError(f"Invalid knowledge_scope '{clean_scope}'. Must be one of {sorted(VALID_SCOPES)}")

    clean_tier = str(tier).strip()
    if clean_tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier '{clean_tier}'. Must be one of {sorted(VALID_TIERS)}")

    clean_content = dict(content)
    clean_subjects = list(subjects) if subjects else []
    clean_source = str(source_id).strip()
    clean_decay = dict(decay_metadata) if decay_metadata else {}
    clean_relations = dict(relations) if relations else {}

    # Check for existing record if projection-keyed
    if projector_version is not None and clean_source:
        existing = MemoryRecord.objects.filter(
            owner_id=clean_owner,
            source_id=clean_source,
            projector_version=projector_version,
        ).first()
        if existing:
            latest_rev = existing.revisions.order_by("-revision_number").first()
            return existing, latest_rev, False

    with transaction.atomic():
        record = MemoryRecord.objects.create(
            owner_id=clean_owner,
            tick=int(tick),
            category=str(category).strip(),
            content=clean_content,
            salience=int(salience),
            knowledge_scope=clean_scope,
            confidence=float(confidence),
            subjects=clean_subjects,
            source_id=clean_source,
            projector_version=projector_version,
            derived_generation=derived_generation,
            effective_tier=clean_tier,
            effective_availability="active",
            latest_revision_number=1,
        )

        revision = MemoryRevision.objects.create(
            record=record,
            revision_number=1,
            availability="active",
            tier=clean_tier,
            decay_metadata=clean_decay,
            supersedes_record_id="",
            relations=clean_relations,
        )

        gen = _increment_owner_generation(clean_owner)

        boundary = {
            "record_id": record.id,
            "owner_id": clean_owner,
            "category": record.category,
            "tick": record.tick,
            "scope": record.knowledge_scope,
            "generation": gen,
        }
        transaction.on_commit(
            lambda b=boundary: log_info("narrative_memory_recorded", context=b)
        )

        return record, revision, True


def revise_memory(
    *,
    record: MemoryRecord,
    availability: Optional[str] = None,
    tier: Optional[str] = None,
    decay_metadata: Optional[dict[str, Any]] = None,
    supersedes_record_id: Optional[str] = None,
    relations: Optional[dict[str, Any]] = None,
) -> MemoryRevision:
    """Create an append-only revision for effective metadata, decay, or supersession.

    Atomically updates materialized effective state and advances owner generation.
    Never overwrites original content or provenance.
    """
    with transaction.atomic():
        # Lock record row for update
        locked_record = MemoryRecord.objects.select_for_update().get(id=record.id)
        latest_rev = locked_record.revisions.order_by("-revision_number").first()

        new_rev_num = (latest_rev.revision_number + 1) if latest_rev else 1

        new_avail = str(availability).strip() if availability is not None else (latest_rev.availability if latest_rev else "active")
        if new_avail not in VALID_AVAILABILITY:
            raise ValueError(f"Invalid availability '{new_avail}'. Must be one of {sorted(VALID_AVAILABILITY)}")

        new_tier = str(tier).strip() if tier is not None else (latest_rev.tier if latest_rev else "working")
        if new_tier not in VALID_TIERS:
            raise ValueError(f"Invalid tier '{new_tier}'. Must be one of {sorted(VALID_TIERS)}")

        new_decay = dict(decay_metadata) if decay_metadata is not None else (dict(latest_rev.decay_metadata) if latest_rev else {})
        new_supersedes = str(supersedes_record_id).strip() if supersedes_record_id is not None else (latest_rev.supersedes_record_id if latest_rev else "")
        new_relations = dict(relations) if relations is not None else (dict(latest_rev.relations) if latest_rev else {})

        revision = MemoryRevision.objects.create(
            record=locked_record,
            revision_number=new_rev_num,
            availability=new_avail,
            tier=new_tier,
            decay_metadata=new_decay,
            supersedes_record_id=new_supersedes,
            relations=new_relations,
        )

        # Update materialized effective state
        locked_record.effective_availability = new_avail
        locked_record.effective_tier = new_tier
        locked_record.latest_revision_number = new_rev_num
        locked_record.save(update_fields=["effective_availability", "effective_tier", "latest_revision_number", "updated_at"])

        gen = _increment_owner_generation(locked_record.owner_id)

        boundary = {
            "record_id": locked_record.id,
            "revision_number": new_rev_num,
            "owner_id": locked_record.owner_id,
            "availability": new_avail,
            "tier": new_tier,
            "generation": gen,
        }
        transaction.on_commit(
            lambda b=boundary: log_info("narrative_memory_revised", context=b)
        )

        return revision


def supersede_memory(
    *,
    old_record: MemoryRecord,
    new_record: MemoryRecord,
) -> tuple[MemoryRevision, MemoryRevision]:
    """Supersede old_record with new_record.

    Marks old_record as 'superseded' with supersedes_record_id pointing to new_record.
    Links new_record relations to old_record.
    Advances owner generation.
    """
    if str(old_record.owner_id) != str(new_record.owner_id):
        raise NarrativeMemoryPermissionError("Cannot supersede memory across different owners.")

    with transaction.atomic():
        old_rev = revise_memory(
            record=old_record,
            availability="superseded",
            supersedes_record_id=str(new_record.id),
        )
        new_relations = dict(new_record.revisions.order_by("-revision_number").first().relations if new_record.revisions.exists() else {})
        new_relations["supersedes_prior_id"] = str(old_record.id)
        new_rev = revise_memory(
            record=new_record,
            relations=new_relations,
        )
        return old_rev, new_rev


def get_owner_memories(
    *,
    owner_id: str,
    requester_id: Optional[str] = None,
    include_superseded: bool = False,
    include_inactive: bool = False,
    tier: Optional[str] = None,
    scope: Optional[str] = None,
    category: Optional[str] = None,
) -> list[MemoryRecordView]:
    """Retrieve permission-filtered detached memory record views for an owner.

    Enforces knowledge and privacy boundaries:
    - Normal access excludes inactive and superseded records.
    - Historical access (include_superseded=True) includes superseded records while preserving provenance and permissions.
    - An arbitrary requester cannot access another owner's private cognition unless explicitly public knowledge.
    - Private authoring records are excluded from normal cognition views.
    - Returns detached immutable MemoryRecordView objects, never ORM models.
    """
    clean_owner = str(owner_id).strip()
    if requester_id is not None:
        clean_requester = str(requester_id).strip()
        if clean_requester != clean_owner:
            # Different requester: only genuinely public cognition can be viewed
            if scope != "public":
                return []

    qs = MemoryRecord.objects.filter(owner_id=clean_owner)

    # Exclude private authoring from in-world cognition views
    qs = qs.exclude(category__in=PRIVATE_AUTHORING_CATEGORIES)

    if not include_superseded and not include_inactive:
        qs = qs.filter(effective_availability="active")
    elif not include_inactive:
        qs = qs.filter(effective_availability__in=["active", "superseded"])

    if tier:
        qs = qs.filter(effective_tier=str(tier).strip())
    if scope:
        qs = qs.filter(knowledge_scope=str(scope).strip())
    if category:
        qs = qs.filter(category=str(category).strip())

    qs = qs.select_related().prefetch_related("revisions").order_by("tick", "id")

    views: list[MemoryRecordView] = []
    for rec in qs:
        # Get latest revision
        latest_rev = rec.revisions.order_by("-revision_number").first()
        decay = dict(latest_rev.decay_metadata) if latest_rev else {}
        relations = dict(latest_rev.relations) if latest_rev else {}
        rev_num = latest_rev.revision_number if latest_rev else rec.latest_revision_number
        avail = latest_rev.availability if latest_rev else rec.effective_availability
        current_tier = latest_rev.tier if latest_rev else rec.effective_tier

        views.append(
            MemoryRecordView(
                id=rec.id,
                owner_id=rec.owner_id,
                tick=rec.tick,
                category=rec.category,
                content=dict(rec.content),
                salience=rec.salience,
                knowledge_scope=rec.knowledge_scope,
                confidence=rec.confidence,
                subjects=list(rec.subjects),
                source_id=rec.source_id,
                projector_version=rec.projector_version,
                derived_generation=rec.derived_generation,
                tier=current_tier,
                availability=avail,
                revision_number=rev_num,
                decay_metadata=decay,
                relations=relations,
            )
        )
    return views


def project_narrative_event_to_memories(
    event: NarrativeEvent,
    projector_version: int = 1,
) -> list[MemoryRecord]:
    """Project a durable NarrativeEvent into eligible owner memories atomically and settle progress.

    Projection rules:
    - Encounter protection:
      - Eligible observers: participants in the event who witnessed it.
      - Each eligible observer gains a 'witnessed' MemoryRecord.
      - Non-observers gain no memory.
    - Claim event (e.g. event_type == 'claim_receipt'):
      - Eligible recipients gain a 'told' MemoryRecord containing the claim.
      - Never instantiates or mutates world truth (no rules/maps/quests writes).
    - Idempotency & atomicity:
      - Uses transaction.atomic() to create memories and mark ProjectionProgress 'completed'.
      - If already completed or records exist, does not duplicate records.
    """
    source_id = str(event.source_id).strip()

    with transaction.atomic():
        # Lock progress row
        progress, created = ProjectionProgress.objects.select_for_update().get_or_create(
            source_id=source_id,
            projector_version=projector_version,
            defaults={"status": "pending"},
        )
        if progress.status == "completed":
            # Already completed; return existing records
            return list(MemoryRecord.objects.filter(
                source_id=source_id,
                projector_version=projector_version,
            ).order_by("id"))

        records: list[MemoryRecord] = []

        if event.event_type == "encounter_protection":
            # Participants are [actor_pk, *protected_companion_pks]
            # All committed participants are eligible observers who witnessed the protection
            participants = [str(p) for p in event.participants]
            for p_id in participants:
                # Content for protection memory
                mem_content = {
                    "summary": "Witnessed successful protection during encounter",
                    "encounter_outcome": event.content.get("encounter_outcome", "victory"),
                    "protected_keys": event.content.get("protected_keys", []),
                    "mode": event.content.get("mode", ""),
                    "rounds_elapsed": event.content.get("rounds_elapsed", 0),
                }
                rec, _, _ = record_memory(
                    owner_id=p_id,
                    content=mem_content,
                    tick=event.tick,
                    category="encounter",
                    tier="working",
                    salience=event.salience,
                    knowledge_scope="witnessed",
                    confidence=1.0,
                    subjects=participants,
                    source_id=source_id,
                    projector_version=projector_version,
                )
                records.append(rec)

        elif event.event_type == "claim_receipt":
            # Content contains: claimant, statement, recipients
            recipients = [str(r) for r in event.content.get("recipients", event.participants)]
            statement = event.content.get("statement", "")
            claimant = str(event.content.get("claimant", "unknown"))

            for r_id in recipients:
                mem_content = {
                    "summary": f"Told by {claimant}: {statement}",
                    "claimant": claimant,
                    "statement": statement,
                }
                rec, _, _ = record_memory(
                    owner_id=r_id,
                    content=mem_content,
                    tick=event.tick,
                    category="claim",
                    tier="working",
                    salience=event.salience,
                    knowledge_scope="told",
                    confidence=0.5,  # Claim has lower default confidence than direct observation
                    subjects=[claimant],
                    source_id=source_id,
                    projector_version=projector_version,
                )
                records.append(rec)

        else:
            # Generic event projection for public or participant awareness
            for p_id in [str(p) for p in event.participants]:
                rec, _, _ = record_memory(
                    owner_id=p_id,
                    content=dict(event.content),
                    tick=event.tick,
                    category="observation",
                    tier="working",
                    salience=event.salience,
                    knowledge_scope="witnessed",
                    confidence=1.0,
                    subjects=[str(p) for p in event.participants],
                    source_id=source_id,
                    projector_version=projector_version,
                )
                records.append(rec)

        # Mark progress as completed inside the same transaction
        progress.status = "completed"
        progress.save(update_fields=["status", "updated_at"])

        boundary = {
            "source_id": source_id,
            "projector_version": projector_version,
            "records_count": len(records),
        }
        transaction.on_commit(
            lambda b=boundary: log_info("narrative_memory_projected", context=b)
        )

        return records


def process_pending_narrative_memory_projections(projector_version: int = 1) -> int:
    """Consume all pending projections for the given version and settle memories.

    Safe for restart recovery.
    Returns the count of successfully processed sources.
    """
    pending_items = list(
        ProjectionProgress.objects.filter(
            projector_version=projector_version,
            status="pending",
        ).values_list("source_id", flat=True)
    )

    processed_count = 0
    for source_id in pending_items:
        event = NarrativeEvent.objects.filter(source_id=source_id).first()
        if not event:
            continue
        try:
            project_narrative_event_to_memories(event, projector_version=projector_version)
            processed_count += 1
        except Exception as exc:
            log_error(
                "narrative_memory_projection_failed",
                context={"source_id": source_id, "projector_version": projector_version},
                exc=exc,
            )

    return processed_count
