"""The external worker boundary and store-path confinement (design D5).

The engine's only job is to hand validated jobs to an external command and
validate the results. A job is ``{"kind", "key", "description", "out_path",
"aspect_ratio"}``; the engine pre-computes the exact expected relative output
identity per subject and writes it as ``out_path``. A result is accepted only
when its key matches an input job, its status is ``success``/``failed``, and
its ``output_identity`` exactly equals the expected identity with an existing
regular file under ``ART_STORE_ROOT`` (symlink-resolved).

Drains are claim-based and non-blocking: the claim and settle are fast DB
transactions under the queue lock, and the worker subprocess runs on a
background Twisted thread with the lock released and a bounded timeout.
"""

import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any

from django.conf import settings
from twisted.internet import threads

from world.art.queue import claim, queue_lock, reclaim_expired_leases, settle
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind, parse_subject


class WorkerProtocolError(ValueError):
    """Raised when a worker result violates the one-to-one batch protocol."""


_LEASE_MARGIN_SECONDS = 5

# Exactly one external worker subprocess may be in flight at a time (one
# worker concurrency slot, design D4). The flag is guarded by the shared queue
# lock so a second drain can never double-claim or start a second worker.
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


def _worker_env() -> dict[str, str]:
    """Subprocess environment: expose the store root and the game directory.

    The default worker (``tools.art_worker``) must be importable as a module
    even though the subprocess runs with ``cwd=ART_STORE_ROOT``, so the game
    directory is added to ``PYTHONPATH``. Custom workers may ignore it.
    """
    env = dict(os.environ)
    env["ART_DEFAULT_STORE_ROOT"] = str(_store_root())
    env["ART_GAME_DIR"] = str(Path(settings.GAME_DIR))
    game_dir = str(Path(settings.GAME_DIR))
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = game_dir if not existing else f"{game_dir}:{existing}"
    return env


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


def _build_job(subject: ArtSubject, description: str) -> dict[str, Any]:
    return {
        "kind": subject.kind.value,
        "key": subject.full(),
        "description": description,
        "out_path": expected_output_identity(subject),
        "aspect_ratio": "16:9" if subject.kind is ArtSubjectKind.SCENE else "3:4",
    }


def _run_worker(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run the configured worker command on the current thread.

    JSON-lines jobs in, JSON-lines results out, bounded by
    ``ART_WORKER_TIMEOUT_SECONDS``. This is the only place a worker subprocess
    is ever spawned; the caller decides on which thread it runs.
    """
    payload = "\n".join(json.dumps(job, ensure_ascii=False) for job in jobs) + "\n"
    completed = subprocess.run(
        settings.ART_WORKER_CMD,
        input=payload,
        capture_output=True,
        text=True,
        timeout=settings.ART_WORKER_TIMEOUT_SECONDS,
        cwd=str(_store_root()),
        env=_worker_env(),
    )
    results: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as error:
            raise WorkerProtocolError(
                f"worker emitted non-JSON output: {error}"
            ) from error
        if not isinstance(parsed, dict):
            raise WorkerProtocolError(
                "worker emitted a non-object result line"
            )
        results.append(parsed)
    return results


def _valid_result(
    job: dict[str, Any], result: dict[str, Any]
) -> tuple[str, str | None, str | None]:
    """Validate one result against its input job.

    Returns ``(settle_status, output_identity, error)``. A result is accepted
    only when its key matches the input job, its status is ``success``/``failed``,
    and -- for a success -- its ``output_identity`` exactly equals the expected
    identity resolving to an existing regular file under the root. Anything
    else is rejected with a bounded protocol error.
    """
    if result.get("key") != job["key"]:
        return ArtAssetStatus.FAILED, None, "worker_result_key_mismatch"
    status = result.get("status")
    if status == "success":
        identity = result.get("output_identity")
        if not isinstance(identity, str) or identity != job["out_path"]:
            return ArtAssetStatus.FAILED, None, "worker_output_identity_mismatch"
        target = _store_root() / identity
        resolved = _resolved_under_root(target)
        if resolved is None:
            return ArtAssetStatus.FAILED, None, "worker_output_out_of_root"
        if not resolved.is_file():
            return ArtAssetStatus.FAILED, None, "worker_output_missing"
        return ArtAssetStatus.DONE, identity, None
    if status == "failed":
        return ArtAssetStatus.FAILED, None, result.get("error") or "worker_failed"
    return ArtAssetStatus.FAILED, None, "worker_result_invalid_status"


def subject_for(record: ArtAssetRecord) -> ArtSubject:
    """Rebuild the typed subject from a claimed record's persisted fields."""
    return parse_subject(f"{record.db.kind}:{record.db.subject_key}")


def _run_and_settle_batch(records: list[ArtAssetRecord]) -> list[ArtSubject]:
    """Run the worker for one claimed batch and settle every result.

    Runs on a background Twisted thread with the queue lock released. The
    batch protocol is one-to-one: missing, duplicated, or unparseable results
    mark the unfinished claimed jobs ``failed`` with a bounded protocol error,
    so no job can be stuck ``in_progress`` or silently double-completed.

    Returns the subjects whose ``settle()`` actually applied a terminal
    ``done``/``failed`` status. A stale settle that returned ``None`` (the
    record was requeued or reclaimed by a newer worker) is excluded, so the
    completion notification is emitted only for a result that is truly the
    current record.
    """
    subjects = [subject_for(record) for record in records]
    descriptions = [str(record.db.source_description or "") for record in records]
    jobs = [_build_job(subject, description) for subject, description in zip(subjects, descriptions)]
    try:
        raw_results = _run_worker(jobs)
    except (WorkerProtocolError, subprocess.TimeoutExpired, OSError) as error:
        _fail_batch(subjects, _bounded_error(error))
        return []

    if len(raw_results) != len(jobs):
        # One-to-one batch protocol: a missing or duplicated result marks every
        # unfinished claimed job failed so none stays stuck in_progress.
        _fail_batch(subjects, "worker_batch_protocol_error")
        return []

    settled: list[ArtSubject] = []
    try:
        for subject, job, result in zip(subjects, jobs, raw_results):
            status, identity, error = _valid_result(job, result)
            if settle(
                subject,
                status=status,
                output_identity=identity,
                error=error,
            ) is not None:
                settled.append(subject)
    except Exception:
        # Defensive: an unexpected settle error must never leave a claimed job
        # stuck in_progress; fail every unfinished subject as a bounded failure.
        _fail_batch(subjects, "worker_settle_error")
        return []
    return settled


def _fail_batch(subjects: list[ArtSubject], error: str) -> None:
    for subject in subjects:
        settle(
            subject,
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error=error,
        )


def _bounded_error(error: Exception) -> str:
    if isinstance(error, subprocess.TimeoutExpired):
        return "worker_timeout"
    if isinstance(error, OSError):
        return "worker_start_failed"
    return "worker_protocol_error"


def _notify_completed_batch(subjects: list[ArtSubject]) -> None:
    """Emit ``asset_completed`` for the subjects that really settled.

    Runs on the reactor thread (the ``deferToThread`` success callback) or on
    the calling thread in deterministic ``drain_synchronous`` tests. Never runs
    on the worker subprocess thread, so no subscriber touches the DB from a
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
    queue lock), then runs the worker subprocess and settles the results on a
    background Twisted thread with the lock released. At most one worker runs
    at a time; a drain attempted while another worker is in flight claims
    nothing and returns 0. Returns the number of jobs dispatched; the caller
    (a command or the scheduler Script) never blocks on the worker wait.
    """
    if not _try_acquire_worker_slot():
        return 0
    try:
        reclaim_expired_leases(
            settings.ART_WORKER_TIMEOUT_SECONDS + _LEASE_MARGIN_SECONDS
        )
        records = claim(limit)
    except Exception:
        _release_worker_slot()
        raise
    if not records:
        _release_worker_slot()
        return 0
    deferred = threads.deferToThread(_run_and_release_slot, records)
    # The success callback runs on the reactor thread, so the completion
    # notification is never emitted from the worker subprocess thread.
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
        reclaim_expired_leases(
            settings.ART_WORKER_TIMEOUT_SECONDS + _LEASE_MARGIN_SECONDS
        )
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
