"""The internal sd-webui worker boundary and store-path confinement.

The engine owns an in-process sd-webui client (design D11 amendment): for every
claimed record it resolves the configured client (``ART_SD_CLIENT`` dotted
path), calls ``generate(subject, description)`` with a bounded timeout, and
writes the returned PNG bytes atomically to the pre-computed expected relative
identity under ``ART_STORE_ROOT`` (symlink-resolved). A job settles ``done``
only when the client returned valid PNG bytes and the engine wrote them to
exactly the expected identity.

Every claimed subject reaches a terminal settle. Named client errors
(``SDError`` codes), prompt-library failures (``sd_prompt_error``),
client-resolution failures (``sd_client_config_error``), and unexpected
internal errors (``sd_internal_error``) all settle the subject ``failed``, so a
bad admin prompt or a settings typo can never leave a batch half
``in_progress``.

Drains are claim-based and non-blocking: the claim and settle are fast DB
transactions under the queue lock, and the client call runs on a background
Twisted thread with the lock released and a bounded timeout.
"""

import os
import tempfile
from pathlib import Path
from typing import Any

from django.conf import settings
from twisted.internet import threads

from world.art.queue import (
    claim,
    queue_lock,
    reclaim_expired_leases,
    settle,
    settle_generated,
)
from world.art.sd_worker import SDError, resolve_sd_client
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind, parse_subject
from world.prompts.loader import PromptLibraryError

_LEASE_MARGIN_SECONDS = 5


class WorkerStoreError(ValueError):
    """Raised when a validated output identity would escape the store root."""


# Exactly one sd-webui generation may be in flight at a time (one worker
# concurrency slot, design D4). The flag is guarded by the shared queue lock so
# a second drain can never double-claim or start a second generation.
_worker_in_flight = False


def _try_acquire_worker_slot() -> bool:
    global _worker_in_flight
    with queue_lock:
        if _worker_in_flight:
            return False
        _worker_in_flight = True
        return True


def _release_worker_slot() -> None:
    global _worker_in_flight
    with queue_lock:
        _worker_in_flight = False


def expected_output_identity(subject: ArtSubject) -> str:
    """The exact same-store relative identity the engine expects for a subject."""
    if subject.kind is ArtSubjectKind.SCENE:
        return f"scene/{subject.key}.png"
    if subject.kind is ArtSubjectKind.MONSTER:
        return f"portrait/monster/{subject.key}.png"
    return f"portrait/character/{subject.key}.png"


def _store_root() -> Path:
    return Path(settings.ART_STORE_ROOT)


def _resolved_under_root(path: Path) -> Path | None:
    """Return the symlink-resolved path if it stays inside the store root."""
    try:
        resolved = path.resolve()
    except OSError:
        return None
    root = _store_root().resolve()
    if resolved == root or root not in resolved.parents:
        return None
    return resolved


def _write_temp(identity: str, png_bytes: bytes) -> str:
    """Write the PNG to a unique temporary file inside the store directory.

    The final atomic replace onto ``identity`` happens later in
    ``settle_generated`` (under the queue lock, only while the claim is still
    current), so a stale or failed generation never touches the record's prior
    valid output. The identity must resolve inside the store root (the
    symlink-resolved under-root check) or the write is rejected before any file
    is created.
    """
    target = _store_root() / identity
    if _resolved_under_root(target) is None:
        raise WorkerStoreError(
            f"output identity {identity!r} resolves outside the store root"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(png_bytes)
            handle.flush()
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return tmp_path


def subject_for(record: ArtAssetRecord) -> ArtSubject:
    """Rebuild the typed subject from a claimed record's persisted fields."""
    return parse_subject(f"{record.db.kind}:{record.db.subject_key}")


def _settle_one(
    client: Any,
    record: ArtAssetRecord,
) -> tuple[str, str | None, str | None, bool] | None:
    """Generate and publish one claimed record; return the settle outcome.

    Every failure mode maps to a bounded settle: named ``SDError`` codes,
    prompt-library failures (``sd_prompt_error``), and any unexpected internal
    error (``sd_internal_error``); the record's prior valid output is retained
    on every failure path. A success publishes the PNG atomically through
    ``settle_generated`` (carrying the returned seed), which already settles
    the record ``done`` under the queue lock (the returned flag marks that).
    Returns ``None`` when the claim was requeued or reclaimed mid-flight and
    must not be settled by this worker.
    """
    subject = subject_for(record)
    description = str(record.db.source_description or "")
    try:
        image = client.generate(subject, description)
        identity = expected_output_identity(subject)
        tmp_path = _write_temp(identity, image.data)
    except SDError as error:
        return ArtAssetStatus.FAILED, None, error.code, False
    except PromptLibraryError:
        return ArtAssetStatus.FAILED, None, "sd_prompt_error", False
    except WorkerStoreError:
        return ArtAssetStatus.FAILED, None, "worker_output_out_of_root", False
    except Exception:
        return ArtAssetStatus.FAILED, None, "sd_internal_error", False
    committed = settle_generated(
        subject,
        generation_token=str(record.db.generation_token or ""),
        output_identity=identity,
        tmp_path=tmp_path,
        seed=image.seed,
    )
    if committed is None:
        return None
    return ArtAssetStatus.DONE, identity, None, True


def _run_and_settle_batch(records: list[ArtAssetRecord]) -> list[ArtSubject]:
    """Generate and settle one claimed batch on the background thread.

    The client is resolved once per batch: a bad ``ART_SD_CLIENT`` dotted path
    settles every claimed subject ``failed`` with ``sd_client_config_error``.
    Each subject is then generated and published independently, so one bad
    subject never fails its batch-mates and no claimed job is left
    ``in_progress``.

    Returns the subjects whose status was actually applied (``done`` via
    ``settle_generated``, or a terminal ``failed`` via ``settle``). A stale
    result whose claim was requeued or reclaimed is excluded, so the completion
    notification is emitted only for a result that is truly the current record.
    """
    subjects = [subject_for(record) for record in records]
    try:
        client = resolve_sd_client()
    except Exception:
        _fail_batch(subjects, "sd_client_config_error")
        return []
    settled: list[ArtSubject] = []
    for subject, record in zip(subjects, records):
        outcome = _settle_one(client, record)
        if outcome is None:
            continue
        status, identity, error, already_settled = outcome
        if already_settled:
            settled.append(subject)
            continue
        if (
            settle(
                subject,
                status=status,
                output_identity=identity,
                error=error,
            )
            is not None
        ):
            settled.append(subject)
    return settled


def _fail_batch(subjects: list[ArtSubject], error: str) -> None:
    for subject in subjects:
        settle(
            subject,
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error=error,
        )


def _lease_timeout() -> float:
    """Lease-reclaim bound sized by the worst-case claimed batch.

    A batch of up to ``ART_SCHEDULER_LIMIT`` claimed records can run for
    ``N x ART_SD_TIMEOUT_SECONDS`` on the single slot, so the lease bound is
    ``N x timeout + margin`` -- never a flat per-item timeout -- so a
    legitimately slow batch is not reclaimed while its worker thread is still
    running. The hard per-request deadline plus the per-subject terminal-settle
    guarantee mean a batch always finishes within a bounded wall-clock budget.
    """
    return (int(settings.ART_SCHEDULER_LIMIT) * float(settings.ART_SD_TIMEOUT_SECONDS)) + _LEASE_MARGIN_SECONDS


def _notify_completed_batch(subjects: list[ArtSubject]) -> None:
    """Emit ``asset_completed`` for the subjects that really settled.

    Runs on the reactor thread (the ``deferToThread`` success callback) or on
    the calling thread in deterministic ``drain_synchronous`` tests. Never runs
    on the worker generation thread, so no subscriber touches the DB from a
    worker thread. The payload carries only the completed full subject key.
    """
    if not subjects:
        return
    from world.art.signals import asset_completed

    for subject in subjects:
        asset_completed.send(sender=subject.__class__, subject_key=subject.full())


def drain(limit: int) -> int:
    """Claim up to ``limit`` pending jobs and dispatch them non-blocking.

    Reclaims expired leases, claims the batch synchronously (fast, under the
    queue lock), then generates and settles the results on a background Twisted
    thread with the lock released. At most one generation runs at a time; a
    drain attempted while another is in flight claims nothing and returns 0.
    Returns the number of jobs dispatched; the caller (a command or the
    scheduler Script) never blocks on the generation wait.
    """
    if not _try_acquire_worker_slot():
        return 0
    try:
        reclaim_expired_leases(_lease_timeout())
        records = claim(limit)
    except Exception:
        _release_worker_slot()
        raise
    if not records:
        _release_worker_slot()
        return 0
    deferred = threads.deferToThread(_run_and_release_slot, records)
    # The success callback runs on the reactor thread, so the completion
    # notification is never emitted from the worker generation thread.
    deferred.addCallback(_notify_completed_batch)
    deferred.addErrback(_log_drain_failure)
    return len(records)


def _run_and_release_slot(records: list[ArtAssetRecord]) -> list[ArtSubject]:
    """Run a claimed batch on the worker thread and always release the slot.

    Returns the subjects whose terminal status was actually applied so the
    reactor-thread callback can emit the completion notification.
    """
    try:
        return _run_and_settle_batch(records)
    finally:
        _release_worker_slot()


def drain_synchronous(limit: int) -> int:
    """Drain on the calling thread for deterministic tests and recovery paths."""
    if not _try_acquire_worker_slot():
        return 0
    try:
        reclaim_expired_leases(_lease_timeout())
        records = claim(limit)
        if not records:
            return 0
        settled = _run_and_settle_batch(records)
        _notify_completed_batch(settled)
        return len(records)
    finally:
        _release_worker_slot()


def _log_drain_failure(failure) -> None:
    from evennia import logger

    logger.log_err(f"art drain failed: {failure.getTraceback()}")
    return None
