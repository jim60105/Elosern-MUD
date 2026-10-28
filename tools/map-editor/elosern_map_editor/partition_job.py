"""Explicit partition jobs: one background generation with guarded publication.

A job is admitted only by the explicit ``POST /api/partition/generate`` route
(never by a pointer move, a drag or an ordinary command). At most one job runs
at a time. While it runs, the service refuses every world-data mutation
(``write_paused`` with reason ``partition_generating``) and keeps browsing,
inspection, rereads, file following, layout edits, status and cancellation
useful.

Execution (:class:`PartitionJobs`):

1. admission, under the service's workspace I/O lock: current session and
   snapshot revision, no write pause, a current preview, no running job;
   a fresh confined read of the world sources must carry the published
   world's partition source signature (the captured input signature); the
   partition artifact's presence is captured for the publication guard;
2. a dedicated thread runs :mod:`elosern_map_editor.partition_worker` as a
   child process on exactly the captured sources. The heavy raster work never
   shares the service's interpreter or event loop, and cancelling, timing
   out or invalidating a job ends that process;
3. an adopted loaded read whose partition signature differs from the
   captured one (an external change seen by file following or a reread)
   invalidates the job at once (``failed``/``inputs_changed``);
4. publication, under the I/O lock: the job must still be the running one;
   then no write pause, a current preview, a fresh disk read with the
   captured partition signature and an unchanged artifact presence; then the
   writer's guarded atomic artifact replacement and one reread.

Job states: ``idle``, ``generating``, ``publishing``, ``succeeded``,
``cancelled``, ``failed`` (with a ``reason``). A cancel or failure never
touches the last artifact. A cancel that arrives while or after publication
is answered with the job's own state; there is no rollback of a replaced
artifact.

Lock order (no other order is used): the service's I/O lock, then its state
lock, then this module's leaf lock. The leaf lock only guards the job fields
and is never held while acquiring another lock or doing I/O.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

IDLE = "idle"
GENERATING = "generating"
PUBLISHING = "publishing"
SUCCEEDED = "succeeded"
CANCELLED = "cancelled"
FAILED = "failed"
#: States in which world-data mutations are refused.
RUNNING = frozenset({GENERATING, PUBLISHING})

#: Problem lines kept from a failed job (each is also length-bounded).
MAX_PROBLEMS = 20
MAX_PROBLEM_CHARS = 400

#: Test-only hook stages, in job order.
HOOK_STAGES = ("spawned", "generated")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _bounded(problems) -> list[str]:
    return [str(problem)[:MAX_PROBLEM_CHARS] for problem in list(problems)[:MAX_PROBLEMS]]


class JobRejected(Exception):
    """An inadmissible job request; ``status``/``code`` form the HTTP error."""

    def __init__(self, status: int, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.details = details


class PartitionJobs:
    """The single partition job of one service session.

    ``hook`` is a test-only callable invoked in the job thread with a
    :data:`HOOK_STAGES` stage name (production passes none).
    """

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_output_bytes: int,
        hook: Callable[[str], None] | None = None,
    ) -> None:
        self._leaf = threading.Lock()
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.hook = hook
        self._process: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._fields: dict[str, Any] = {
            "state": IDLE,
            "job_id": None,
            "input_signature": None,
            "started_at": None,
            "finished_at": None,
            "reason": None,
            "problems": [],
            "published_fingerprint": None,
        }

    # -- observation (leaf lock only) -------------------------------------
    def describe(self) -> dict[str, Any]:
        with self._leaf:
            return {**self._fields, "problems": list(self._fields["problems"])}

    @property
    def running(self) -> bool:
        with self._leaf:
            return self._fields["state"] in RUNNING

    def is_current(self, job_id: str, state: str) -> bool:
        with self._leaf:
            return self._fields["job_id"] == job_id and self._fields["state"] == state

    # -- transitions (caller holds the service state lock) ----------------
    def begin(self, signature: str) -> str:
        """Record a new generating job; the caller has admitted it."""

        job_id = uuid.uuid4().hex
        with self._leaf:
            self._fields = {
                "state": GENERATING,
                "job_id": job_id,
                "input_signature": signature,
                "started_at": _now(),
                "finished_at": None,
                "reason": None,
                "problems": [],
                "published_fingerprint": None,
            }
        return job_id

    def to_publishing(self, job_id: str) -> bool:
        """Claim publication; False when the job was cancelled or invalidated."""

        with self._leaf:
            if self._fields["job_id"] != job_id or self._fields["state"] != GENERATING:
                return False
            self._fields["state"] = PUBLISHING
            return True

    def finish(
        self,
        job_id: str,
        state: str,
        *,
        reason: str | None = None,
        problems=(),
        fingerprint: str | None = None,
        expect: frozenset[str] = RUNNING,
    ) -> bool:
        """Move the named job to a terminal state if it is still in ``expect``."""

        with self._leaf:
            if self._fields["job_id"] != job_id or self._fields["state"] not in expect:
                return False
            self._fields.update(
                state=state,
                finished_at=_now(),
                reason=reason,
                problems=_bounded(problems),
                published_fingerprint=fingerprint,
            )
            process = self._process if state in (CANCELLED, FAILED) else None
        if process is not None:
            _kill(process)
        return True

    def cancel(self) -> dict[str, Any] | None:
        """Cancel a generating job; ``None`` when no job is generating."""

        with self._leaf:
            job_id = self._fields["job_id"] if self._fields["state"] == GENERATING else None
        if job_id is None or not self.finish(job_id, CANCELLED, expect=frozenset({GENERATING})):
            return None
        return self.describe()

    def invalidate(self, signature: str | None) -> bool:
        """An adopted read with another partition signature ends a generating job."""

        with self._leaf:
            fields = self._fields
            if fields["state"] != GENERATING or signature == fields["input_signature"]:
                return False
            job_id = fields["job_id"]
        return self.finish(
            job_id,
            FAILED,
            reason="inputs_changed",
            problems=["a partition source changed during generation; the result was discarded"],
            expect=frozenset({GENERATING}),
        )

    # -- execution ----------------------------------------------------------
    def launch(self, job_id: str, payload: bytes, on_output: Callable[[str, str], None],
               on_failure: Callable[[str, str, list[str]], None]) -> None:
        """Start the job thread (the caller has called :meth:`begin`)."""

        thread = threading.Thread(
            target=self._run,
            args=(job_id, payload, on_output, on_failure),
            name=f"partition-job-{job_id[:8]}",
            daemon=True,
        )
        self._thread = thread
        thread.start()

    def _hook(self, stage: str) -> None:
        if self.hook is not None:
            self.hook(stage)

    def _run(self, job_id, payload, on_output, on_failure) -> None:
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "elosern_map_editor.partition_worker"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
            )
        except OSError as error:
            on_failure(job_id, "worker_failed", [f"the generation process did not start: {error}"])
            return
        with self._leaf:
            self._process = process
            ended = self._fields["job_id"] != job_id or self._fields["state"] != GENERATING
        if ended:
            # Cancelled or invalidated before the process was recorded.
            _kill(process)
        self._hook("spawned")
        try:
            out, err = process.communicate(payload, timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            _kill(process)
            on_failure(job_id, "timeout", [f"generation exceeded {self.timeout_seconds:g} s"])
            return
        finally:
            with self._leaf:
                if self._process is process:
                    self._process = None
        if not self.is_current(job_id, GENERATING):
            return
        if process.returncode != 0:
            tail = err.decode("utf-8", "replace").strip().splitlines()[-5:]
            on_failure(job_id, "worker_failed", [f"the generation process exited with {process.returncode}", *tail])
            return
        if len(out) > self.max_output_bytes:
            on_failure(job_id, "output_too_large", [f"the generated artifact exceeds {self.max_output_bytes} bytes"])
            return
        try:
            result = json.loads(out.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            on_failure(job_id, "worker_failed", [f"the generation process answered malformed output: {error}"])
            return
        if not result.get("ok"):
            on_failure(job_id, str(result.get("code") or "generation_failed"), list(result.get("problems") or []))
            return
        self._hook("generated")
        on_output(job_id, result["text"])

    def shutdown(self) -> None:
        """Service shutdown: end a running child process and its job."""

        with self._leaf:
            job_id = self._fields["job_id"] if self._fields["state"] == GENERATING else None
            process = self._process
        if job_id is not None:
            self.finish(job_id, CANCELLED, reason="service_stopped", expect=frozenset({GENERATING}))
        if process is not None:
            _kill(process)


def _kill(process: subprocess.Popen) -> None:
    """End a child process; the job thread's ``communicate`` reaps it."""

    try:
        process.kill()
    except OSError:
        # observability: ignore R2: the editor service has no game logging
        # facade; the process already exited (nothing left to end).
        pass


def request_payload(sources, signature: str) -> bytes:
    """The worker's stdin document for captured source documents."""

    return json.dumps(
        {
            "signature": signature,
            "sources": [
                {"relative_path": source.relative_path, "text": source.text} for source in sources
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")


__all__ = [
    "CANCELLED",
    "FAILED",
    "GENERATING",
    "HOOK_STAGES",
    "IDLE",
    "JobRejected",
    "PUBLISHING",
    "PartitionJobs",
    "RUNNING",
    "SUCCEEDED",
    "request_payload",
]
