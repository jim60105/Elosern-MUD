"""Project delivered and first-read letters into told owner cognition.

A letter's receipt is the authoritative occurrence; its claims never become
world truth. The delivery occurrence leaves its version-2 projection pending
under the archived delivery contract, so this consumer drains that durable
source wherever cognition is needed (server startup, reply capture, the
face-to-face recall boundary), while a player's first read projects inside the
read transaction because that occurrence is the player's knowledge boundary.
Every source is addressed by durable identity, so replay and restart settle one
memory per owner and never duplicate cognition.
"""

from django.db import transaction

from world.narrative.correspondence import (
    CORRESPONDENCE_PROJECTOR_VERSION,
    correspondence_event_source_id,
)
from world.narrative.memory import record_memory
from world.narrative.models import (
    LetterSend,
    MemoryRecord,
    NarrativeEvent,
    ProjectionProgress,
)
from world.observability import log_error, log_info, log_warn

LETTER_MEMORY_CATEGORY = "correspondence"
# A letter communicates a statement; it is told speech, never a witnessed fact.
LETTER_MEMORY_SCOPE = "told"
# Working tier keeps a letter inside bounded fixed selection, so face-to-face
# continuity reads the same cognition instead of re-copying the letter archive.
LETTER_MEMORY_TIER = "working"
# Reported information carries the told-claim confidence of the existing
# claim projection, below a direct observation.
LETTER_MEMORY_CONFIDENCE = 0.5
# The rendered cognition line stays bounded; the full statement lives in content.
SUMMARY_EXCERPT_CHARACTERS = 200


def _letter_content(letter, *, settled_tick):
    """Immutable letter provenance plus the bounded prompt-facing claim line."""
    statement = " ".join(letter.body.split())
    excerpt = statement[:SUMMARY_EXCERPT_CHARACTERS]
    if len(statement) > SUMMARY_EXCERPT_CHARACTERS:
        excerpt += "…"
    return {
        "summary": f"Letter from correspondent {letter.sender_id}: {excerpt}",
        "channel": "correspondence",
        "letter_source_id": letter.source_id,
        "sender_id": letter.sender_id,
        "recipient_id": letter.recipient_id,
        "sent_tick": int(letter.sent_tick),
        "settled_tick": int(settled_tick),
        "reply_to": letter.reply_to,
        "statement": letter.body,
    }


def _approved_owner(event, letter):
    """The one owner the approved boundary admits, or None for no content.

    An NPC gains a delivered letter; an available player letter stays unknown
    until its first read, and only the recorded reader can own a read memory.
    """
    if event.event_type == "correspondence_delivery":
        if event.content.get("status") != "delivered":
            return None
        return letter.recipient_id
    if event.event_type == "correspondence_read":
        reader = str(letter.recipient_id)
        if reader in {str(participant) for participant in event.participants}:
            return reader
        return None
    return None


def _source_letter(event):
    """Read the immutable accepted letter a durable occurrence references."""
    source_id = event.content.get("letter_source_id")
    if not isinstance(source_id, str) or not source_id:
        return None
    return LetterSend.objects.filter(source_id=source_id).first()


def project_correspondence_event(event, projector_version=CORRESPONDENCE_PROJECTOR_VERSION):
    """Project one durable delivery/read occurrence into told owner memories.

    Idempotent: the ``(source_id, projector_version)`` progress row settles once,
    and a replay returns the original records instead of duplicating cognition.
    Occurrences the boundary admits nobody for still settle their own row.
    """
    source_id = str(event.source_id).strip()
    with transaction.atomic():
        progress, _created = ProjectionProgress.objects.select_for_update().get_or_create(
            source_id=source_id,
            projector_version=projector_version,
            defaults={"status": "pending"},
        )
        if progress.status == "completed":
            return list(MemoryRecord.objects.filter(
                source_id=source_id, projector_version=projector_version,
            ).order_by("id"))

        records = []
        letter = _source_letter(event)
        owner_id = _approved_owner(event, letter) if letter is not None else None
        if owner_id:
            record, _revision, _recorded = record_memory(
                owner_id=owner_id,
                content=_letter_content(letter, settled_tick=event.tick),
                tick=int(event.tick),
                category=LETTER_MEMORY_CATEGORY,
                tier=LETTER_MEMORY_TIER,
                salience=int(event.salience),
                knowledge_scope=LETTER_MEMORY_SCOPE,
                confidence=LETTER_MEMORY_CONFIDENCE,
                subjects=[letter.sender_id],
                source_id=source_id,
                projector_version=projector_version,
            )
            records.append(record)

        progress.status = "completed"
        progress.save(update_fields=["status", "updated_at"])
        boundary = {
            "source_id": source_id,
            "owner_id": owner_id or "",
            "projector_version": projector_version,
            "records_count": len(records),
        }
        transaction.on_commit(
            lambda b=boundary: log_info("correspondence_memory_projected", context=b)
        )
        return records


def settle_delivery_cognition(letter_source_id):
    """Drain this letter's durable delivery source before gated generation.

    Returns False when the delivery occurrence or its progress row is missing,
    so a gated caller waits instead of generating from absent cognition.
    """
    source_id = correspondence_event_source_id(str(letter_source_id), "delivered")
    progress = ProjectionProgress.objects.filter(
        source_id=source_id,
        projector_version=CORRESPONDENCE_PROJECTOR_VERSION,
    ).first()
    if progress is None:
        return False
    if progress.status == "completed":
        return True
    event = NarrativeEvent.objects.filter(source_id=source_id).first()
    if event is None:
        return False
    project_correspondence_event(event)
    return True


def recover_pending_correspondence_projections():
    """Startup recovery entry: drain the durable queue and announce the scan."""
    return process_pending_correspondence_projections(announce=True)


def process_pending_correspondence_projections(*, announce=False):
    """Drain every pending version-2 source; safe to repeat after interruption.

    Returns the number of sources settled in this pass. The cataloged startup
    scan event is announced only by the recovery entry: the lazy reply and
    recall drains run on hot paths and stay quiet, while each settled source
    still emits its own ``correspondence_memory_projected`` boundary event.
    """
    if announce:
        from world.narrative.events import scan_pending_narrative_projections

        scan_pending_narrative_projections(projector_version=CORRESPONDENCE_PROJECTOR_VERSION)
    pending = list(ProjectionProgress.objects.filter(
        projector_version=CORRESPONDENCE_PROJECTOR_VERSION, status="pending",
    ).values_list("source_id", flat=True))

    processed = 0
    for source_id in pending:
        event = NarrativeEvent.objects.filter(source_id=source_id).first()
        if event is None:
            log_warn(
                "correspondence_memory_projection_skipped",
                context={
                    "source_id": source_id,
                    "projector_version": CORRESPONDENCE_PROJECTOR_VERSION,
                },
            )
            continue
        try:
            project_correspondence_event(event)
            processed += 1
        except Exception as exc:
            log_error(
                "correspondence_memory_projection_failed",
                context={
                    "source_id": source_id,
                    "projector_version": CORRESPONDENCE_PROJECTOR_VERSION,
                },
                exc=exc,
            )
    return processed
