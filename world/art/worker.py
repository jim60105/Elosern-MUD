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

from world.art.formats import encode
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
from world.observability import log_error, log_info, log_warn
from world.observability.sanitize import safe_endpoint
from world.prompts.loader import PromptLibraryError

_LEASE_MARGIN_SECONDS = 5

# Per-item wall-clock allowance for the LOCAL conversion step (decode +
# encode is pure CPU and unbounded by the network timeout), folded into the
# lease bound so a slow encode never gets a legitimate batch reclaimed.
_CONVERSION_ALLOWANCE_SECONDS = 60


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
    extension = str(settings.ART_SD_OUTPUT_EXTENSION)
    if subject.kind is ArtSubjectKind.SCENE:
        return f"scene/{subject.key}{extension}"
    if subject.kind is ArtSubjectKind.MONSTER:
        return f"portrait/monster/{subject.key}{extension}"
    return f"portrait/character/{subject.key}{extension}"


def _store_root() -> Path:
    return Path(settings.ART_STORE_ROOT)


def _resolved_under_root(path: Path) -> Path | None:
    """Return the symlink-resolved path if it stays inside the store root."""
    try:
        resolved = path.resolve()
    except OSError:  # observability: ignore R2: confinement probe; None result is the caller's bounded-failure signal
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
        except OSError:  # observability: ignore R2: best-effort temp cleanup; the original error propagates below
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
    """Generate, convert, and publish one claimed record; return the settle outcome.

    Every failure mode maps to a bounded settle: named ``SDError`` codes,
    local-conversion failures (``sd_format_error``), prompt-library failures
    (``sd_prompt_error``), and any unexpected internal error
    (``sd_internal_error``); the record's prior valid output is retained on
    every failure path. The embedded-metadata provenance comes from the
    ``GeneratedImage`` the client returned — never from a second render of
    the mutable prompt library. A success publishes the encoded bytes
    atomically through ``settle_generated`` (carrying the returned seed),
    which settles the record ``done`` under the queue lock (the returned flag
    marks that); only after that commit does an extension change delete the
    validated prior file (a deletion error is a bounded log, never a revert).
    Returns ``None`` when the claim was requeued or reclaimed mid-flight and
    must not be settled by this worker.
    """
    subject = subject_for(record)
    description = str(record.db.source_description or "")
    # The claim-time token snapshot is captured BEFORE any blocking work:
    # settle authority is the token this worker actually claimed, never
    # whatever the record field happens to hold after the generation.
    generation_token = str(record.db.generation_token or "")
    try:
        image = client.generate(subject, description)
        encoded, _extension = encode(
            image.data,
            prompt=image.prompt,
            negative_prompt=image.negative_prompt,
            steps=image.steps,
            cfg_scale=image.cfg_scale,
            sampler=image.sampler,
            scheduler=image.scheduler,
            width=image.width,
            height=image.height,
            seed=image.seed,
            checkpoint=image.checkpoint,
            output_format=str(settings.ART_SD_OUTPUT_FORMAT),
            quality=int(settings.ART_SD_OUTPUT_QUALITY),
            preserve_metadata=bool(settings.ART_SD_PRESERVE_GENERATION_METADATA),
        )
        identity = expected_output_identity(subject)
        tmp_path = _write_temp(identity, encoded)
    except SDError as error:
        log_warn("sd_generation_error", context={"endpoint": _sd_endpoint(), "code": error.code}, exc=error)
        return ArtAssetStatus.FAILED, None, error.code, False
    except PromptLibraryError as error:
        log_warn("sd_generation_error", context={"endpoint": _sd_endpoint(), "code": "sd_prompt_error"}, exc=error)
        return ArtAssetStatus.FAILED, None, "sd_prompt_error", False
    except WorkerStoreError as error:
        log_warn("sd_generation_error", context={"endpoint": _sd_endpoint(), "code": "worker_output_out_of_root"}, exc=error)
        return ArtAssetStatus.FAILED, None, "worker_output_out_of_root", False
    except Exception as error:
        log_warn("sd_generation_error", context={"endpoint": _sd_endpoint(), "code": "sd_internal_error"}, exc=error)
        return ArtAssetStatus.FAILED, None, "sd_internal_error", False
    try:
        committed = settle_generated(
            subject,
            generation_token=generation_token,
            output_identity=identity,
            tmp_path=tmp_path,
            seed=image.seed,
        )
    except Exception as error:  # noqa: BLE001 - a publication failure is a terminal per-record failure, never a batch abort
        # A non-stale claim whose atomic publication failed must still reach
        # a terminal settle (the batch settles FAILED with the prior output
        # retained); letting this escape would strand the record
        # ``in_progress`` and skip every later record in the batch.
        log_warn(
            "sd_generation_error",
            context={
                "endpoint": _sd_endpoint(),
                "code": "sd_internal_error",
                "stage": "publication",
            },
            exc=error,
        )
        return ArtAssetStatus.FAILED, None, "sd_internal_error", False
    if committed is None:
        return None
    _record, prior_identity = committed
    if prior_identity:
        _cleanup_prior_output(prior_identity)
    return ArtAssetStatus.DONE, identity, None, True


def _cleanup_prior_output(identity: str) -> None:
    """Delete the validated prior file after the record transition committed.

    Runs strictly after the commit, so the record can never point at the
    deleted file. The under-root confinement is re-checked before unlinking;
    any deletion error is a bounded ``cleanup_failed`` log that leaves an
    unreferenced orphan (cleaned by the next regeneration) and NEVER reverts
    the committed transition.
    """
    path = _store_root() / identity
    if _resolved_under_root(path) is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError as error:
        log_warn("art_cleanup_failed", context={"identity": identity}, exc=error)


def _sd_endpoint() -> str:
    """The configured sd-webui endpoint identity, credential-free.

    Log-only: configured URLs may embed ``user:password@`` or query
    secrets, so the identity is sanitized at the source before any
    event context can carry it.
    """
    return safe_endpoint(settings.ART_SD_BASE_URL)


def _log_claim(record: ArtAssetRecord) -> None:
    """One boundary event per actually-claimed record."""
    subject = subject_for(record)
    log_info("sd_job_claim", context={"job": record.db_key, "subject": subject.full()})


def _log_settled(
    record: ArtAssetRecord, subject: ArtSubject, status: str, reason: str
) -> None:
    """One boundary event per record whose terminal settle was applied."""
    log_info(
        "sd_job_settled",
        context={
            "job": record.db_key,
            "subject": subject.full(),
            "status": status,
            "reason": reason,
        },
    )


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
    pairs = [(record, subject_for(record)) for record in records]
    try:
        client = resolve_sd_client()
    except Exception as error:
        log_error(
            "sd_client_config_failed",
            context={"endpoint": _sd_endpoint(), "code": "sd_client_config_error"},
            exc=error,
        )
        _fail_batch(pairs, "sd_client_config_error")
        return []
    settled: list[ArtSubject] = []
    for record, subject in pairs:
        outcome = _settle_one(client, record)
        if outcome is None:
            continue
        status, identity, error, already_settled = outcome
        if already_settled:
            settled.append(subject)
            _log_settled(record, subject, status, "generated")
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
            _log_settled(record, subject, status, str(error))
    return settled


def _fail_batch(pairs: list[tuple[ArtAssetRecord, ArtSubject]], error: str) -> None:
    """Settle every claimed record ``failed``; event only when applied.

    A stale record (requeued or reclaimed mid-flight) settles to a no-op
    (``settle`` returns ``None``) and must not fabricate a settle event.
    """
    for record, subject in pairs:
        if (
            settle(
                subject,
                status=ArtAssetStatus.FAILED,
                output_identity=None,
                error=error,
            )
            is not None
        ):
            _log_settled(record, subject, ArtAssetStatus.FAILED, error)


def _lease_timeout() -> float:
    """Lease-reclaim bound sized by the worst-case claimed batch.

    A batch of up to ``ART_SCHEDULER_LIMIT`` claimed records can run for
    ``N x (ART_SD_TIMEOUT_SECONDS + per-item local-conversion allowance)`` on
    the single slot, so the lease bound is
    ``N x (timeout + conversion allowance) + margin`` -- never a flat per-item
    timeout -- so neither a slow generation nor a slow local encode reclaims a
    legitimately slow batch while its worker thread is still running. The
    hard per-request deadline plus the per-subject terminal-settle guarantee
    mean a batch always finishes within a bounded wall-clock budget.
    """
    per_item = float(settings.ART_SD_TIMEOUT_SECONDS) + _CONVERSION_ALLOWANCE_SECONDS
    return int(settings.ART_SCHEDULER_LIMIT) * per_item + _LEASE_MARGIN_SECONDS


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
    except Exception:
        _release_worker_slot()
        raise
    try:
        records = claim(limit)
    except Exception as error:
        _release_worker_slot()
        log_error("sd_job_claim_failed", context={"endpoint": _sd_endpoint()}, exc=error)
        raise
    if not records:
        _release_worker_slot()
        return 0
    for record in records:
        _log_claim(record)
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
    except Exception:
        _release_worker_slot()
        raise
    try:
        records = claim(limit)
    except Exception as error:
        _release_worker_slot()
        log_error("sd_job_claim_failed", context={"endpoint": _sd_endpoint()}, exc=error)
        raise
    if not records:
        _release_worker_slot()
        return 0
    try:
        for record in records:
            _log_claim(record)
        settled = _run_and_settle_batch(records)
        _notify_completed_batch(settled)
        return len(records)
    finally:
        _release_worker_slot()


def _log_drain_failure(failure) -> None:
    log_error("art_drain_failed", context={"exc_type": type(failure.value).__name__}, exc=failure.value)
    return None
