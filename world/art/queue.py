"""Idempotent subject-keyed art queue and the shared serialization lock.

Scenes and portraits share exactly one process-wide ``queue_lock`` and one
worker concurrency slot (design D4). Every record write happens under that
lock: enqueue (ensure), forced requeue, claim, lease reclaim, and settle. The
external worker subprocess never runs under the lock -- it executes on a
background Twisted thread -- so concurrent drains, ``@art`` commands, and
``on_commit`` enqueues serialize on fast DB transactions only.
"""

import hashlib
import threading
import time

from evennia.utils.create import create_script

from world.art.store import ArtAssetRecord, ArtAssetStatus, status_rank
from world.art.subjects import ArtSubject

# The single shared serialization lock for every scene and portrait operation.
queue_lock = threading.Lock()


def record_key(subject: ArtSubject) -> str:
    """The script key for a subject's asset record."""
    return f"art:{subject.full()}"


def source_hash(description: str) -> str:
    """Deterministic sha256 of the canonical subject description."""
    return hashlib.sha256(description.encode("utf-8")).hexdigest()


def _all_records() -> list[ArtAssetRecord]:
    return list(ArtAssetRecord.objects.all())


def _records_for(subject: ArtSubject) -> list[ArtAssetRecord]:
    return list(ArtAssetRecord.objects.filter(db_key=record_key(subject)))


def _consolidate(subject: ArtSubject) -> ArtAssetRecord | None:
    """Keep the most-advanced record for a subject, delete the rest.

    Enforces per-subject uniqueness even outside the single-process assumption
    (a hypothetical overlapping hot-reload could leave duplicates behind).
    """
    records = _records_for(subject)
    if not records:
        return None
    records.sort(key=lambda record: status_rank(record.db.status), reverse=True)
    for duplicate in records[1:]:
        duplicate.delete()
    return records[0]


def _create_record(subject: ArtSubject) -> ArtAssetRecord:
    record = create_script(
        ArtAssetRecord, key=record_key(subject), persistent=True, interval=0
    )
    record.db.kind = subject.kind.value
    record.db.subject_key = subject.key
    return record


def _find_or_create(subject: ArtSubject) -> ArtAssetRecord:
    """Atomic find-or-create for one subject under the queue lock."""
    record = _consolidate(subject)
    if record is None:
        record = _create_record(subject)
    return record


def ensure(subject: ArtSubject, description: str) -> ArtAssetRecord:
    """Idempotently enqueue one subject under the queue lock.

    An existing ``pending``/``in_progress``/``done`` record is left alone; a
    ``missing`` or ``failed`` record becomes ``pending`` (the retry path). A
    changed source hash for a ``done`` record is surfaced for staff review and
    never silently replaces the completed image (design D4).
    """
    digest = source_hash(description)
    with queue_lock:
        record = _find_or_create(subject)
        prior = record.db.status
        if prior in ArtAssetStatus.ACTIVE or prior == ArtAssetStatus.DONE:
            if prior == ArtAssetStatus.DONE and record.db.source_hash != digest:
                record.db.hash_changed = True
            return record
        record.db.source_hash = digest
        record.db.source_description = description
        record.db.aspect_ratio = _aspect_ratio_for(subject)
        record.db.status = ArtAssetStatus.PENDING
        if record.db.enqueued_at is None:
            record.db.enqueued_at = time.time()
        if prior == ArtAssetStatus.FAILED:
            record.db.attempt_count = int(record.db.attempt_count or 0) + 1
        return record


def requeue(subject: ArtSubject) -> ArtAssetRecord:
    """Force a staff regeneration: reset to ``pending`` under the lock.

    The prior valid output (if any) is preserved for rollback and retained
    across a later failed regeneration (design D4).
    """
    with queue_lock:
        record = _find_or_create(subject)
        if record.db.status == ArtAssetStatus.DONE and record.db.output_identity:
            record.db.prior_output_identity = record.db.output_identity
        record.db.status = ArtAssetStatus.PENDING
        if record.db.enqueued_at is None:
            record.db.enqueued_at = time.time()
        return record


def claim(limit: int) -> list[ArtAssetRecord]:
    """Claim up to ``limit`` ``pending`` records under the lock.

    Each claimed record becomes ``in_progress`` with a ``claimed_at`` lease and
    an incremented attempt count. The lock is released before any worker work.
    """
    with queue_lock:
        pending = [
            record
            for record in _all_records()
            if record.db.status == ArtAssetStatus.PENDING
        ]
        pending.sort(key=lambda record: record.db.enqueued_at or 0.0)
        claimed = pending[: max(limit, 0)]
        now = time.time()
        for record in claimed:
            record.db.status = ArtAssetStatus.IN_PROGRESS
            record.db.claimed_at = now
            record.db.attempt_count = int(record.db.attempt_count or 0) + 1
            record.db.last_error_code = None
        return claimed


def reclaim_expired_leases(timeout: float) -> int:
    """Reclaim ``in_progress`` records whose lease has expired to ``pending``.

    A crashed or timed-out worker never leaves a job stuck (design D4).
    """
    now = time.time()
    reclaimed = 0
    with queue_lock:
        for record in _all_records():
            if record.db.status != ArtAssetStatus.IN_PROGRESS:
                continue
            claimed_at = record.db.claimed_at
            if claimed_at is None or now - float(claimed_at) >= timeout:
                record.db.status = ArtAssetStatus.PENDING
                record.db.claimed_at = None
                reclaimed += 1
    return reclaimed


def settle(subject: ArtSubject, *, status: str, output_identity: str | None,
           error: str | None) -> ArtAssetRecord | None:
    """Apply one validated terminal result for a claimed record under the lock.

    A failure retains the record's prior valid output. ``status`` must be
    ``done`` or ``failed``; anything else is recorded as a bounded failure.
    Only a record that is still ``in_progress`` is settled: a stale settle from
    a worker whose job was later requeued (reset to ``pending``) or reclaimed
    is a no-op, so an older worker result can never overwrite a newer forced
    regeneration (design D4).
    """
    with queue_lock:
        records = _records_for(subject)
        if not records:
            return None
        record = records[0]
        if record.db.status != ArtAssetStatus.IN_PROGRESS:
            return None
        if status == ArtAssetStatus.DONE and output_identity:
            record.db.status = ArtAssetStatus.DONE
            record.db.output_identity = output_identity
            record.db.prior_output_identity = None
            record.db.completed_at = time.time()
            record.db.last_error_code = None
            record.db.claimed_at = None
        else:
            record.db.status = ArtAssetStatus.FAILED
            record.db.last_error_code = error or "settle_error"
            record.db.claimed_at = None
        return record


def failed_keys() -> list[str]:
    """Full subject keys of every ``failed`` record (for ``@art retry``)."""
    with queue_lock:
        return [
            record.db_key.removeprefix("art:")
            for record in _all_records()
            if record.db.status == ArtAssetStatus.FAILED
        ]


def _aspect_ratio_for(subject: ArtSubject) -> str:
    return "16:9" if subject.kind.value == "scene" else "3:4"
