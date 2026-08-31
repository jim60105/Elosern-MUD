"""Idempotent subject-keyed art queue and the shared serialization lock.

Scenes and portraits share exactly one process-wide ``queue_lock`` and one
worker concurrency slot (design D4). Every record write happens under that
lock: enqueue (ensure), forced requeue, claim, lease reclaim, and settle. The
external worker subprocess never runs under the lock -- it executes on a
background Twisted thread -- so concurrent drains, ``@art`` commands, and
``on_commit`` enqueues serialize on fast DB transactions only.
"""

import hashlib
import os
import threading
import time
import uuid
from pathlib import Path

from django.conf import settings
from evennia.utils.create import create_script

from world.art.sd_worker import prompt_digest
from world.art.store import ArtAssetRecord, ArtAssetStatus, status_rank
from world.art.subjects import ArtSubject
from world.prompts.loader import PromptLibraryError

# The single shared serialization lock for every scene and portrait operation.
queue_lock = threading.Lock()


def record_key(subject: ArtSubject) -> str:
    """The script key for a subject's asset record."""
    return f"art:{subject.full()}"


def source_hash(description: str) -> str:
    """Deterministic sha256 of the canonical subject description."""
    return hashlib.sha256(description.encode("utf-8")).hexdigest()


def _prompt_digest_or_empty(subject: ArtSubject, description: str) -> str:
    """The rendered-prompt digest, or an empty sentinel when the library is broken.

    The digest is sha256 of the rendered positive+negative prompt pair. A
    broken prompt library (an admin mid-edit, an unreadable file) must never
    block an enqueue, so the failure degrades to an empty digest; a later
    successful render then differs from the stored value and surfaces through
    the ``hash_changed`` review flag exactly like a prompt edit.
    """
    try:
        return prompt_digest(subject, description)
    except PromptLibraryError:
        return ""


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
    changed source hash or a changed rendered-prompt digest for a ``done``
    record is surfaced for staff review and never silently replaces the
    completed image (design D4, D-3b).
    """
    digest = source_hash(description)
    with queue_lock:
        record = _find_or_create(subject)
        prior = record.db.status
        if prior in ArtAssetStatus.ACTIVE or prior == ArtAssetStatus.DONE:
            if prior == ArtAssetStatus.DONE:
                if record.db.source_hash != digest:
                    record.db.hash_changed = True
                if record.db.prompt_digest != _prompt_digest_or_empty(subject, description):
                    record.db.hash_changed = True
            return record
        record.db.source_hash = digest
        record.db.source_description = description
        record.db.prompt_digest = _prompt_digest_or_empty(subject, description)
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
    across a later failed regeneration (design D4). The rendered-prompt digest
    is recomputed so it tracks the prompt text the pending job will actually
    render, and the generation token is cleared so an in-flight worker from the
    previous claim can never publish its output. This keeps the review flag
    free of spurious changes after a successful regeneration.
    """
    with queue_lock:
        record = _find_or_create(subject)
        if record.db.status == ArtAssetStatus.DONE and record.db.output_identity:
            record.db.prior_output_identity = record.db.output_identity
        record.db.prompt_digest = _prompt_digest_or_empty(
            subject, str(record.db.source_description or "")
        )
        record.db.generation_token = ""
        record.db.status = ArtAssetStatus.PENDING
        if record.db.enqueued_at is None:
            record.db.enqueued_at = time.time()
        return record


def claim(limit: int) -> list[ArtAssetRecord]:
    """Claim up to ``limit`` ``pending`` records under the lock.

    Each claimed record becomes ``in_progress`` with a ``claimed_at`` lease,
    a fresh generation token, and an incremented attempt count. The lock is
    released before any worker work.
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
            record.db.generation_token = uuid.uuid4().hex
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


def settle_generated(
    subject: ArtSubject,
    *,
    generation_token: str,
    output_identity: str,
    tmp_path: str,
    seed: int | None = None,
) -> tuple[ArtAssetRecord, str | None] | None:
    """Atomically publish one generated output for the current claim under the lock.

    The claim's ``generation_token`` must still match the record and the record
    must still be ``in_progress``: a worker whose job was requeued (reset to
    ``pending``) or reclaimed can never publish, so a stale generation can
    never replace the record's prior valid output. When the claim is current,
    the settlement validates BOTH the new target AND the record's committed
    ``output_identity`` (the authoritative prior — never the transient
    ``prior_output_identity`` recovery field) under the store root, atomically
    replaces the temporary file onto the new identity, and settles the record
    ``done`` in the same critical section, with ``seed`` assigned
    unconditionally (``None`` clears the previous output's seed — a seedless
    regeneration must never advertise the old image's seed).

    Returns ``(record, prior_identity)`` where ``prior_identity`` is the
    committed prior validated under the root when its extension differs from
    the new one (the same-extension case replaces in place and yields
    ``None``), so the caller deletes exactly that file AFTER this transaction
    commits. A deletion failure can therefore never strand the record on a
    deleted file: at worst the prior stays as an unreferenced orphan. On any
    failure at or before the record transition the temporary file is removed,
    the existing output is never touched, and the error propagates. Returns
    ``None`` (stale claim) after removing the temporary file.
    """
    with queue_lock:
        records = _records_for(subject)
        if not records:
            _remove_tmp(tmp_path)
            return None
        record = records[0]
        if (
            record.db.status != ArtAssetStatus.IN_PROGRESS
            or record.db.generation_token != generation_token
        ):
            _remove_tmp(tmp_path)
            return None
        root = Path(settings.ART_STORE_ROOT).resolve()
        target = Path(settings.ART_STORE_ROOT) / output_identity
        try:
            resolved = target.resolve()
        except OSError:
            resolved = None
        if resolved is None or resolved == root or root not in resolved.parents:
            _remove_tmp(tmp_path)
            raise ValueError(f"output identity {output_identity!r} escapes the store root")
        prior_cleanup = _validated_prior_cleanup(record, root, output_identity)
        try:
            os.replace(tmp_path, target)
        except BaseException:
            _remove_tmp(tmp_path)
            raise
        record.db.status = ArtAssetStatus.DONE
        record.db.output_identity = output_identity
        record.db.prior_output_identity = None
        record.db.completed_at = time.time()
        record.db.last_error_code = None
        record.db.claimed_at = None
        record.db.generation_token = ""
        record.db.seed = seed
        return record, prior_cleanup


def _validated_prior_cleanup(
    record: ArtAssetRecord, root: Path, output_identity: str
) -> str | None:
    """Return the committed prior identity when it is a deletable stale-format file.

    Only an extension CHANGE leaves the prior file at a different path (a
    same-extension replace overwrote it in place). The committed prior is
    re-validated under the root before it is ever named as a cleanup
    candidate; an unvalidatable prior yields ``None`` (left untouched, never
    deleted outside the root).
    """
    prior = str(record.db.output_identity or "")
    if not prior or prior == output_identity:
        return None
    if os.path.splitext(prior)[1].lower() == os.path.splitext(output_identity)[1].lower():
        # Same extension: the replace above already overwrote the same path.
        return None
    prior_path = Path(settings.ART_STORE_ROOT) / prior
    try:
        resolved = prior_path.resolve()
    except OSError:
        return None
    if resolved == root or root not in resolved.parents:
        return None
    return prior


def _remove_tmp(tmp_path: str) -> None:
    """Best-effort removal of a stale or failed temporary output file."""
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


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
