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
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from twisted.internet import threads

from world.art.cutout import (
    REMBG_MODEL_NAME,
    CutoutError,
    applies_to,
    remove_background,
)
from world.art.formats import encode
from world.art.paths import resolved_under_store_root
from world.art.queue import (
    claim,
    expected_gallery_identity,
    queue_lock,
    reclaim_expired_leases,
    settle_gallery_failed,
    settle_gallery_generated,
)
from world.art import publication
from world.art.sd_worker import SDError, resolve_sd_client
from world.art.store import GalleryJobRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, parse_subject
from world.art.translate import TranslateError, translate_description
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


@dataclass(frozen=True)
class ArtCompletion:
    """One applied gallery-job settlement: exactly its subject and image.

    Captured from the claim-time snapshot BEFORE the settle deletes the job,
    so a completion always names the exact requested image. It carries no
    output path, prompt or worker internal.
    """

    subject_key: str
    image_id: str


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


def output_identity_for(record: GalleryJobRecord) -> str:
    """The job's exact per-image gallery identity, or a bounded rejection.

    Derived from the job's own validated subject/image metadata:
    ``gallery/<kind-directory>/<subject-key>/<image-id><extension>``. Invalid
    metadata rejects; it never falls back to a fixed subject path.
    """
    identity = expected_gallery_identity(record)
    if identity is None:
        raise WorkerStoreError(
            f"job {record.db_key!r} carries no valid per-image gallery identity"
        )
    return identity


def _store_root() -> Path:
    return Path(settings.ART_STORE_ROOT)


def _write_temp(identity: str, png_bytes: bytes) -> str:
    """Write the PNG to a unique temporary file inside the store directory.

    The final atomic replace onto ``identity`` happens later in
    ``settle_gallery_generated`` (under the queue lock, only while the claim is
    still current), so a stale or failed generation never touches any existing
    card or byte. The identity must resolve strictly under the store root
    (``world.art.paths.resolved_under_store_root``, which also refuses any
    symlinked component) or the write is rejected before any file is created.
    """
    if resolved_under_store_root(identity) is None:
        raise WorkerStoreError(
            f"output identity {identity!r} resolves outside the store root"
        )
    target = _store_root() / identity
    # Held so a world snapshot never sees a half-written temporary file.
    with publication.publishing():
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


def subject_for(record: GalleryJobRecord) -> ArtSubject:
    """Rebuild the typed subject from a claimed record's persisted fields."""
    return parse_subject(f"{record.db.kind}:{record.db.subject_key}")


def _settle_one(
    client: Any,
    record: GalleryJobRecord,
    subject: ArtSubject,
    generation_token: str,
) -> tuple[str, str | None, str | None, bool] | None:
    """Generate, convert, and publish one claimed record; return the settle outcome.

    ``subject`` and ``generation_token`` are the CLAIM-TIME values captured by
    the batch runner before any blocking work: settle authority is the token
    this worker actually claimed, never whatever the record field happens to
    hold after a reclaim (design D6a) — the record attribute is live storage
    and is deliberately never re-read here.

    Every failure mode maps to a bounded settle: named ``SDError`` codes,
    background-removal failures (``art_cutout_unavailable`` /
    ``art_cutout_error``), local-conversion failures (``sd_format_error``),
    prompt-library failures (``sd_prompt_error``), and any unexpected internal
    error (``sd_internal_error``); every existing card and byte is retained
    on every failure path. The embedded-metadata provenance comes from the
    ``GeneratedImage`` the client returned — never from a second render of
    the mutable prompt library. A success publishes the encoded bytes
    atomically through ``settle_gallery_generated`` (file write, then exactly
    one card append, then spent-record deletion, carrying the returned seed);
    a failure goes through ``settle_gallery_failed`` (no card, bounded code on
    the subject's gallery record, spent-record deletion). No prior file is
    deleted here: a capped gallery's own append handles its displaced
    unreferenced file after commit.
    Returns ``None`` when the claim was requeued or reclaimed mid-flight and
    must not be settled by this worker.
    """
    # The job key and image id are likewise captured BEFORE the settle: a
    # gallery settle deletes the job record, and the post-settle boundary
    # event must still name the finished job.
    job_key = str(record.db_key)
    image_id = str(record.db.gallery_image_id or "")
    description = str(record.db.source_description or "")
    if bool(settings.ART_TRANSLATE_ENABLED):
        description = _translate_prompt(
            description,
            job_key=job_key,
            subject=subject,
            image_id=image_id,
        )

    def _gallery_failure(code: str):
        """Terminal gallery failure settle; ``None`` when the claim is stale."""
        applied = settle_gallery_failed(
            job_key, generation_token=generation_token, error=code
        )
        if applied is None:
            return None
        _log_gallery_settle(subject, image_id, ArtAssetStatus.FAILED, code)
        return ArtAssetStatus.FAILED, None, code, True

    def _cutout_transport(png_bytes: bytes) -> bytes:
        """Apply the background-removal stage and emit its boundary event.

        Exactly one stage event per outcome (design D12): ``art_cutout_done``
        on success, ``art_cutout_failed`` (with ``exc=``) on failure. Neither
        is emitted for a subject the stage skipped.
        """
        started = time.monotonic()
        try:
            result = remove_background(png_bytes)
        except CutoutError as error:
            log_warn(
                "art_cutout_failed",
                context={
                    "job": job_key,
                    "subject": subject.full(),
                    "image_id": image_id,
                    "model": REMBG_MODEL_NAME,
                    "code": error.code,
                },
                exc=error,
            )
            raise
        log_info(
            "art_cutout_done",
            context={
                "job": job_key,
                "subject": subject.full(),
                "image_id": image_id,
                "model": REMBG_MODEL_NAME,
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
        return result

    try:
        image = client.generate(subject, description)
        # The stage runs on the transport PNG bytes, before encode (design
        # D1). The GeneratedImage provenance is untouched: the metadata still
        # describes the request sd-webui actually served (design D11).
        if bool(settings.ART_REMBG_ENABLED) and applies_to(subject.kind):
            image_bytes = _cutout_transport(image.data)
        else:
            image_bytes = image.data
        encoded, _extension = encode(
            image_bytes,
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
            infotext=image.infotext,
            output_format=str(settings.ART_SD_OUTPUT_FORMAT),
            quality=int(settings.ART_SD_OUTPUT_QUALITY),
            preserve_metadata=bool(settings.ART_SD_PRESERVE_GENERATION_METADATA),
        )
        identity = output_identity_for(record)
        tmp_path = _write_temp(identity, encoded)
    except SDError as error:
        log_warn("sd_generation_error", context={"endpoint": _sd_endpoint(), "code": error.code}, exc=error)
        return _gallery_failure(error.code)
    except CutoutError as error:
        log_warn("sd_generation_error", context={"endpoint": _sd_endpoint(), "code": error.code}, exc=error)
        return _gallery_failure(error.code)
    except PromptLibraryError as error:
        log_warn("sd_generation_error", context={"endpoint": _sd_endpoint(), "code": "sd_prompt_error"}, exc=error)
        return _gallery_failure("sd_prompt_error")
    except WorkerStoreError as error:
        log_warn("sd_generation_error", context={"endpoint": _sd_endpoint(), "code": "worker_output_out_of_root"}, exc=error)
        return _gallery_failure("worker_output_out_of_root")
    except Exception as error:
        log_warn("sd_generation_error", context={"endpoint": _sd_endpoint(), "code": "sd_internal_error"}, exc=error)
        return _gallery_failure("sd_internal_error")

    def _publish() -> tuple[str, str | None, str | None, bool] | None:
        """The publication step a world snapshot never splits."""
        try:
            stored = settle_gallery_generated(
                job_key,
                generation_token=generation_token,
                output_identity=identity,
                tmp_path=tmp_path,
                prompt={"positive": image.prompt, "negative": image.negative_prompt},
                seed=image.seed,
                checkpoint=image.checkpoint,
                image_size={"width": image.decoded_width, "height": image.decoded_height},
            )
        except Exception as error:  # noqa: BLE001 - a publication failure is a terminal per-record failure, never a batch abort
            log_warn(
                "sd_generation_error",
                context={
                    "endpoint": _sd_endpoint(),
                    "code": "sd_internal_error",
                    "stage": "publication",
                },
                exc=error,
            )
            # A card-append failure leaves at worst an orphan FILE (written
            # before the append) for the startup prune; the job settles failed.
            return _gallery_failure("sd_internal_error")
        if stored is None:
            return None
        _log_gallery_settle(subject, image_id, ArtAssetStatus.DONE, "generated")
        return ArtAssetStatus.DONE, identity, None, True

    # The card publication and spent-job deletion run under the publication
    # gate (``world.art.publication``), taken before ``queue_lock``, so a
    # snapshot sees either none or all of it.
    with publication.publishing():
        return _publish()


def _translate_prompt(
    description: str, *, job_key: str, subject: ArtSubject, image_id: str
) -> str:
    """Translate a prompt locally, degrading safely to its authored text."""
    started = time.monotonic()
    try:
        translated, counts = translate_description(description)
    except TranslateError as error:
        log_warn(
            "art_translate_failed",
            context={
                "job": job_key,
                "subject": subject.full(),
                "image_id": image_id,
                "code": error.code,
            },
            exc=error,
        )
        return description
    except Exception as error:  # belt-and-braces for the stage's bounded contract
        log_warn(
            "art_translate_failed",
            context={
                "job": job_key,
                "subject": subject.full(),
                "image_id": image_id,
                "code": "art_translate_error",
            },
            exc=error,
        )
        return description
    if counts.lines_offered:
        log_info(
            "art_translate_done",
            context={
                "job": job_key,
                "subject": subject.full(),
                "image_id": image_id,
                "lines_total": counts.lines_total,
                "lines_offered": counts.lines_offered,
                "lines_untranslated": counts.lines_untranslated,
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
    return translated


def _sd_endpoint() -> str:
    """The configured sd-webui endpoint identity, credential-free.

    Log-only: configured URLs may embed ``user:password@`` or query
    secrets, so the identity is sanitized at the source before any
    event context can carry it.
    """
    return safe_endpoint(settings.ART_SD_BASE_URL)


def _log_claim(record: GalleryJobRecord) -> None:
    """One boundary event per actually-claimed record."""
    subject = subject_for(record)
    log_info("sd_job_claim", context={"job": record.db_key, "subject": subject.full()})


def _log_settled(
    job_key: str, subject: ArtSubject, status: str, reason: str
) -> None:
    """One boundary event per job whose terminal settle was applied.

    ``job_key`` is the CLAIM-TIME snapshot: the gallery settle deletes the
    job record, so the event never re-reads a deleted row.
    """
    log_info(
        "sd_job_settled",
        context={
            "job": job_key,
            "subject": subject.full(),
            "status": status,
            "reason": reason,
        },
    )


def _log_gallery_settle(
    subject: ArtSubject, image_id: str, status: str, reason: str
) -> None:
    """One boundary event per gallery job that reached an applied terminal settle."""
    log_info(
        "gallery_settle",
        context={
            "subject": subject.full(),
            "image_id": image_id,
            "kind": subject.kind.value,
            "status": status,
            "reason": reason,
        },
    )


def _claim_pairs(
    records: list[GalleryJobRecord],
) -> list[tuple[GalleryJobRecord, ArtSubject, str, str]]:
    """Capture the CLAIM-TIME (record, subject, generation token, job key) tuples.

    Runs synchronously on the calling thread immediately after ``claim()``
    returned, before any blocking work (design D6a): settle authority is the
    token this worker actually claimed. The record attribute is live storage —
    a record reclaimed and re-claimed later would hand a stale worker the NEW
    claim's token — so the token and the job key are snapshotted exactly once
    here and threaded through every settle/log call; the attribute is never
    re-read afterwards (the terminal gallery settle deletes the row).
    """
    return [
        (
            record,
            subject_for(record),
            str(record.db.generation_token or ""),
            str(record.db_key),
        )
        for record in records
    ]


def _completion(subject: ArtSubject, image_id: str) -> ArtCompletion:
    return ArtCompletion(subject_key=subject.full(), image_id=image_id)


def _append_completion(completions: list[ArtCompletion], completion: ArtCompletion) -> None:
    """Keep one entry per exact ``(subject_key, image_id)`` pair.

    Distinct images of one subject are distinct completions and are never
    merged by subject.
    """
    if completion not in completions:
        completions.append(completion)


def _run_and_settle_batch(
    pairs: list[tuple[GalleryJobRecord, ArtSubject, str, str]],
) -> list[ArtCompletion]:
    """Generate and settle one claimed batch on the background thread.

    The client is resolved once per batch: a bad ``ART_SD_CLIENT`` dotted path
    settles every claimed subject ``failed`` with ``sd_client_config_error``.
    Each subject is then generated and published independently, so one bad
    subject never fails its batch-mates and no claimed job is left
    ``in_progress``.

    Returns one :class:`ArtCompletion` per job whose status was actually
    applied (a card published or a bounded gallery error recorded), including
    every failure ``_fail_batch`` applied when the client cannot be resolved.
    A stale result whose claim was requeued or reclaimed is excluded, so the
    completion notification is emitted only for a result that is truly the
    current job.
    """
    try:
        client = resolve_sd_client()
    except Exception as error:
        log_error(
            "sd_client_config_failed",
            context={"endpoint": _sd_endpoint(), "code": "sd_client_config_error"},
            exc=error,
        )
        return _fail_batch(pairs, "sd_client_config_error")
    settled: list[ArtCompletion] = []
    for record, subject, token, job_key in pairs:
        # Captured BEFORE the settle: a terminal gallery settle deletes the
        # job record, so the completion's image id is never re-read after it.
        image_id = str(record.db.gallery_image_id or "")
        outcome = _settle_one(client, record, subject, token)
        if outcome is None:
            continue
        status, _identity, error, applied = outcome
        if applied:
            _append_completion(settled, _completion(subject, image_id))
            _log_settled(
                job_key,
                subject,
                status,
                str(error) if status == ArtAssetStatus.FAILED else "generated",
            )
    return settled


def _fail_batch(
    pairs: list[tuple[GalleryJobRecord, ArtSubject, str, str]], error: str
) -> list[ArtCompletion]:
    """Settle every claimed job ``failed``; event only when applied.

    Returns the completions of the failures actually applied, so a batch
    that could not even construct its client still notifies its watchers.

    A stale job (requeued or reclaimed mid-flight) settles to a no-op and must
    not fabricate a settle event. The job's card is never appended, the
    bounded code lands on the subject's gallery record, and the spent job
    record is deleted.
    """
    applied_failures: list[ArtCompletion] = []
    for record, subject, token, job_key in pairs:
        # The event fields are captured BEFORE the settle: the terminal
        # gallery-failed settle deletes the job record.
        image_id = str(record.db.gallery_image_id or "")
        applied = settle_gallery_failed(
            job_key,
            generation_token=token,
            error=error,
        )
        if applied is not None:
            _log_gallery_settle(
                subject, image_id,
                ArtAssetStatus.FAILED, error,
            )
            _log_settled(job_key, subject, ArtAssetStatus.FAILED, error)
            _append_completion(applied_failures, _completion(subject, image_id))
    return applied_failures


def _lease_timeout() -> float:
    """Lease-reclaim bound sized by the worst-case claimed batch.

    A batch of up to ``ART_SCHEDULER_LIMIT`` claimed records can run for
    ``N x (ART_SD_TIMEOUT_SECONDS + per-item local-conversion allowance +
    per-item background-removal allowance)`` on the single slot, so the lease
    bound is
    ``N x (timeout + conversion allowance) + margin`` -- never a flat per-item
    timeout -- so neither a slow generation, a slow local encode, nor a slow
    background-removal pass reclaims a legitimately slow batch while its
    worker thread is still running. The background-removal term
    (``ART_REMBG_ALLOWANCE_SECONDS``) is charged ONLY when
    ``ART_REMBG_ENABLED`` is true, so a deployment that does not run the stage
    keeps today's bound exactly. The one-time model download sits deliberately
    OUTSIDE this bound (a 1 GB fetch can exceed any sane lease and cannot be
    preempted from another thread); the claim-token rule makes such an overrun
    safe instead of corrupting (design D6a). The hard per-request deadline
    plus the per-subject terminal-settle guarantee mean a batch always
    finishes within a bounded wall-clock budget.
    """
    per_item = float(settings.ART_SD_TIMEOUT_SECONDS) + _CONVERSION_ALLOWANCE_SECONDS
    if bool(settings.ART_REMBG_ENABLED):
        per_item += int(settings.ART_REMBG_ALLOWANCE_SECONDS)
    return int(settings.ART_SCHEDULER_LIMIT) * per_item + _LEASE_MARGIN_SECONDS


def _notify_completed_batch(completions: list[ArtCompletion]) -> None:
    """Emit ``asset_completed`` once per applied settlement.

    Runs on the reactor thread (the ``deferToThread`` success callback) or on
    the calling thread in deterministic ``drain_synchronous`` tests. Never runs
    on the worker generation thread, so no subscriber touches the DB from a
    worker thread. The payload carries exactly the completed full subject key
    and the canonical image id of the settled job.
    """
    if not completions:
        return
    from world.art.signals import asset_completed

    for completion in completions:
        asset_completed.send(
            sender=ArtCompletion,
            subject_key=completion.subject_key,
            image_id=completion.image_id,
        )


def drain(limit: int) -> int:
    """Claim up to ``limit`` pending jobs and dispatch them non-blocking.

    Reclaims expired leases, claims the batch synchronously (fast, under the
    queue lock), then generates and settles the results on a background Twisted
    thread with the lock released. At most one generation runs at a time; a
    drain attempted while another is in flight claims nothing and returns 0.
    Returns the number of jobs dispatched; the caller (a command or the
    scheduler Script) never blocks on the generation wait.
    """
    if publication.is_paused():
        # A world snapshot holds the art store still (world.art.publication).
        return 0
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
    # Snapshot the claim-time tokens BEFORE any other step: a reactor-thread
    # requeue could interleave even between the claim logs, so the snapshot
    # must be the very next statement after claim() (design D6a).
    pairs = _claim_pairs(records)
    for record, _subject, _token, _job_key in pairs:
        _log_claim(record)
    deferred = threads.deferToThread(_run_and_release_slot, pairs)
    # The success callback runs on the reactor thread, so the completion
    # notification is never emitted from the worker generation thread.
    deferred.addCallback(_notify_completed_batch)
    deferred.addErrback(_log_drain_failure)
    return len(records)


def _run_and_release_slot(
    pairs: list[tuple[GalleryJobRecord, ArtSubject, str, str]],
) -> list[ArtCompletion]:
    """Run a claimed batch on the worker thread and always release the slot.

    Returns the completions whose terminal status was actually applied so the
    reactor-thread callback can emit the completion notification.
    """
    try:
        return _run_and_settle_batch(pairs)
    finally:
        _release_worker_slot()


def drain_synchronous(limit: int) -> int:
    """Drain on the calling thread for deterministic tests and recovery paths."""
    if publication.is_paused():
        # A world snapshot holds the art store still (world.art.publication).
        return 0
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
        pairs = _claim_pairs(records)
        for record, _subject, _token, _job_key in pairs:
            _log_claim(record)
        settled = _run_and_settle_batch(pairs)
        _notify_completed_batch(settled)
        return len(records)
    finally:
        _release_worker_slot()


def _log_drain_failure(failure) -> None:
    log_error("art_drain_failed", context={"exc_type": type(failure.value).__name__}, exc=failure.value)
    return None
