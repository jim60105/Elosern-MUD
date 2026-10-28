"""The Starlette application: read model, invalidation stream and reread.

Routes in this slice (later slices add their named domain commands only):

``GET  /``               the built frontend (``index.html``)
``GET  /assets/...``     its local assets
``GET  /api/session``    same-origin token bootstrap
``GET  /api/workspace``  one complete replacement of the authoritative state
``GET  /api/events``     SSE ``status``/``invalidate`` notifications
``GET  /api/settlements/<id>/route?source=&destination=``
                         read-only route preview of the published snapshot
                         (the core's planner: steps, authored directions and
                         physical lengths), stamped with its snapshot revision
``POST /api/reload``     authenticated reread of the current disk files
``POST /api/commands/<name>`` one named single-document command, undo or redo
                         (see :mod:`elosern_map_editor.commands`)
``POST /api/partition/generate`` admit one explicit partition job
``POST /api/partition/cancel``   cancel the generating partition job
``GET  /api/partition/outlines`` the current artifact's district outlines
                         (see :mod:`elosern_map_editor.partition_job`)

There is no generic patch, file write, path mutation, shell, Python or remote
account route, and no handoff/resume/return route.

Continuous file following (:mod:`elosern_map_editor.watching`) rereads the
workspace after coalesced directory notifications and reconciles every read
against the committed fingerprint ledger; there is no turn, ownership or
handoff state.
"""

from __future__ import annotations

import asyncio
import hashlib
import threading
import time
import json
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from elosern_map_core import decode_partition, partition_source_signature, schema, settlement_route
from elosern_map_core.partition_codec import PartitionDocumentError
from elosern_map_core.schema import IDENTIFIER_PATTERN
from elosern_map_core.sources import is_world_source
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .commands import (
    COMMANDS,
    HANDLERS,
    CommandError,
    Current,
    Envelope,
    parse_envelope,
    validate_candidate,
)
from .config import EditorConfig
from .confinement import PARTITION_ARTIFACT, ConfinedWorkspace, ConfinementError
from .events import Broadcaster, format_event
from .history import Entry, History, Presence
from .partition_job import (
    CANCELLED,
    FAILED,
    GENERATING,
    SUCCEEDED,
    JobRejected,
    PartitionJobs,
    request_payload,
)
from .security import AdmissionMiddleware, error_body
from .snapshot import WorkspaceRead, read_sources, read_workspace
from .writer import ABSENT, DocumentWriter, Effect, SaveUncertain, StaleDocument, WriteError

_IDENTIFIER = re.compile(IDENTIFIER_PATTERN)

PREVIEW_CURRENT = "current"
PREVIEW_STALE = "stale"
PREVIEW_UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Session:
    """One service start: a fresh identity and launch token."""

    generation: str
    token: str

    @classmethod
    def create(cls) -> "Session":
        return cls(generation=uuid.uuid4().hex, token=secrets.token_urlsafe(32))


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class _PartitionMethods:
    """Partition-job admission, cancellation, publication and outlines.

    Part of :class:`EditorService` (kept separate only for readability).
    """

    # -- admission -------------------------------------------------------
    async def start_partition(self, raw: bytes) -> dict[str, Any]:
        self._loop = asyncio.get_running_loop()
        async with self._lock:
            result = await _finish(run_in_threadpool(self._start_partition_io, raw))
        self.broadcaster.publish("invalidate", self.status())
        return result

    def _start_partition_io(self, raw: bytes) -> dict[str, Any]:
        with self._io:
            return self._start_partition(raw)

    def _start_partition(self, raw: bytes) -> dict[str, Any]:
        body = _json_body(raw, {"session_generation", "snapshot_revision"})
        if body["session_generation"] != self.session.generation:
            raise JobRejected(409, "stale_session", "the session changed; reread before generating")
        if body["snapshot_revision"] != self.snapshot_revision:
            raise JobRejected(
                409, "stale_snapshot", "the snapshot changed; reread before generating",
                snapshot_revision=self.snapshot_revision,
            )
        pause = self.write_pause
        if pause["paused"]:
            raise JobRejected(423, "write_paused", "writes are paused", reason=pause["reason"])
        if self.preview_state != PREVIEW_CURRENT:
            raise JobRejected(
                423, "write_paused", "generation waits for a current preview",
                reason=f"{self.preview_state}_preview",
            )
        if self.partitions.running:
            raise JobRejected(409, "job_running", "a partition job is already running",
                              job=self.partitions.describe())
        assert self.published is not None and self.published.authoring is not None
        signature = self.published.authoring.partition_signature
        limits = self.config.limits
        sources, refused, _ = read_sources(self.workspace, limits, self.workspace.discover_world())
        if refused or partition_source_signature(sources) != signature:
            raise JobRejected(409, "stale_snapshot", "the partition sources changed on disk; reread before generating")
        artifact = self.writer.read_partition_artifact(limits.max_artifact_bytes)
        if artifact.startswith("unreadable:"):
            raise JobRejected(409, "artifact_unreadable", f"the partition artifact cannot be guarded ({artifact})")
        with self._state:
            job_id = self.partitions.begin(signature)
            self._invalidate()
        try:
            self.partitions.launch(
                job_id,
                request_payload(sources, signature),
                lambda job, text: self._publish_partition(job, text, signature, artifact),
                self._partition_failed,
            )
        except Exception as error:  # noqa: BLE001 - recorded on the job
            self._partition_failed(job_id, "internal_error", [f"the partition job did not start: {error!r}"])
        return {**self.status(), "job": self.partitions.describe()}

    # -- cancellation ----------------------------------------------------
    async def cancel_partition(self, raw: bytes) -> dict[str, Any]:
        self._loop = asyncio.get_running_loop()
        body = _json_body(raw, {"session_generation"})
        if body["session_generation"] != self.session.generation:
            raise JobRejected(409, "stale_session", "the session changed; reread before cancelling")
        result = await run_in_threadpool(self._cancel_partition)
        self.broadcaster.publish("invalidate", self.status())
        return result

    def _cancel_partition(self) -> dict[str, Any]:
        with self._state:
            job = self.partitions.cancel()
            if job is not None:
                self._invalidate()
        if job is None:
            # Already published, publishing, failed or idle: report the job's
            # own state; a replaced artifact is never rolled back.
            raise JobRejected(409, "job_not_running", "no partition job is generating",
                              job=self.partitions.describe())
        return {**self.status(), "job": job}

    # -- job thread callbacks --------------------------------------------
    def _notify_threadsafe(self) -> None:
        loop = self._loop
        if loop is None:
            return
        status = self.status()
        try:
            loop.call_soon_threadsafe(self.broadcaster.publish, "invalidate", status)
        except RuntimeError:
            # observability: ignore R2: the editor service has no game logging
            # facade; the loop has stopped, so no stream is left to notify
            # (the job state above is already recorded).
            pass

    def _partition_failed(self, job_id: str, reason: str, problems: list[str]) -> None:
        # Generating or publishing: an unexpected error in either phase must
        # end the job (a cancel cannot end a publishing one).
        with self._state:
            if self.partitions.finish(job_id, FAILED, reason=reason, problems=problems):
                self._invalidate()
        self._notify_threadsafe()

    def _publication_refusal(self, signature: str, artifact: str) -> tuple[str, str] | None:
        """Why the job's output may not be published now (caller holds I/O)."""

        if self.write_pause["paused"]:
            return "write_paused", "writes are paused; the result was not published"
        if self.preview_state != PREVIEW_CURRENT:
            return "stale_preview", "the preview is not current; the result was not published"
        limits = self.config.limits
        sources, refused, _ = read_sources(self.workspace, limits, self.workspace.discover_world())
        if refused or partition_source_signature(sources) != signature:
            return "inputs_changed", "a partition source changed during generation; the result was discarded"
        if self.writer.read_partition_artifact(limits.max_artifact_bytes) != artifact:
            return "artifact_changed", "the partition artifact changed during generation; it was not overwritten"
        return None

    def _publish_partition(self, job_id: str, text: str, signature: str, artifact: str) -> None:
        with self._io:
            if not self.partitions.to_publishing(job_id):
                return
            try:
                self._publish_claimed(job_id, text, signature, artifact)
            except Exception as error:  # noqa: BLE001 - recorded on the job
                with self._state:
                    if self.partitions.finish(job_id, FAILED, reason="internal_error",
                                              problems=[f"the publication failed unexpectedly: {error!r}"]):
                        self._invalidate()
        self._notify_threadsafe()

    def _publish_claimed(self, job_id: str, text: str, signature: str, artifact: str) -> None:
        """Recheck and publish one claimed job (caller holds the I/O lock)."""

        refusal = self._publication_refusal(signature, artifact)
        fingerprint = None
        if refusal is None:
            try:
                fingerprint = self.writer.publish_partition_artifact(
                    text, artifact, self.config.limits.max_artifact_bytes
                )
            except StaleDocument as error:
                refusal = ("artifact_changed", str(error))
            except SaveUncertain as error:
                refusal = ("publish_uncertain", str(error))
            except WriteError as error:
                refusal = ("publish_failed", str(error))
        try:
            read = read_workspace(self.workspace, self.config.limits)
        except Exception as error:  # noqa: BLE001 - reported on the job
            read = None
            refusal = refusal or ("reread_failed", f"the artifact was written but could not be reread: {error}")
        with self._state:
            if read is not None:
                self._adopt(read)
            if refusal is None:
                self.partitions.finish(job_id, SUCCEEDED, fingerprint=fingerprint)
            else:
                self.partitions.finish(job_id, FAILED, reason=refusal[0], problems=[refusal[1]],
                                       fingerprint=fingerprint)
            self._invalidate()

    # -- outlines --------------------------------------------------------
    def partition_outlines(self) -> dict[str, Any] | None:
        """The current artifact's district outlines (metres), or None."""

        try:
            raw = self.workspace.read_document(PARTITION_ARTIFACT, self.config.limits.max_artifact_bytes)
            document = json.loads(raw.decode("utf-8"))
            # Outlines need no land rule; the decode still shape-checks them.
            partition = decode_partition(document, is_land=lambda cell: False)
        except (ConfinementError, PartitionDocumentError, UnicodeDecodeError, ValueError):
            # observability: ignore R2: the editor service has no game logging
            # facade; partition_status already reports the unusable artifact.
            return None
        return {
            "artifact_fingerprint": hashlib.sha256(raw).hexdigest(),
            "input_signature": document["source_signature"],
            "outlines": {key: [list(ring) for ring in rings] for key, rings in partition.outlines.items()},
        }


def _json_body(raw: bytes, keys: set[str]) -> dict[str, Any]:
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise JobRejected(400, "invalid_body", "the body is not JSON") from None
    if not isinstance(body, dict) or set(body) != keys:
        raise JobRejected(400, "invalid_body", f"the body carries exactly {', '.join(sorted(keys))}")
    if "snapshot_revision" in keys and (
        isinstance(body["snapshot_revision"], bool) or not isinstance(body["snapshot_revision"], int)
    ):
        raise JobRejected(400, "invalid_body", "snapshot_revision is an integer")
    return body



class EditorService(_PartitionMethods):
    """Session, published snapshot, the serialized writer and its history.

    Every reread and every command runs under one lock, so source/layout
    writes are strictly serial and each sees the state the previous one left.
    The workspace I/O of commands, rereads, partition-job admission and
    partition publication additionally runs under one thread lock, because a
    partition job publishes from its own thread (lock order: I/O, then
    state, then the job's leaf lock).
    """

    def __init__(self, config: EditorConfig, *, fault=None, partition_hook=None) -> None:
        self.config = config
        self.workspace = ConfinedWorkspace(config.workspace_root)
        self.session = Session.create()
        self.broadcaster = Broadcaster()
        self._lock = asyncio.Lock()
        #: Guards the observable state (read, history, pause, revision) so a
        #: concurrent GET never sees a half-applied command.
        self._state = threading.RLock()
        #: Serializes workspace I/O across request threads and the job thread.
        self._io = threading.Lock()
        #: The event loop that delivers notifications from the job thread.
        self._loop: asyncio.AbstractEventLoop | None = None
        self.partitions = PartitionJobs(
            timeout_seconds=config.partition_timeout_seconds,
            # The answer carries the artifact text JSON-escaped once.
            max_output_bytes=2 * config.limits.max_artifact_bytes,
            hook=partition_hook,
        )
        self.writer = DocumentWriter(self.workspace, config.limits.max_document_bytes, fault=fault)
        self.history = History()
        #: The pending intent of a publication whose durability is unknown;
        #: while set, every mutation is paused until a reread loads.
        self.uncertain: dict[str, Any] | None = None
        #: What the reread that cleared the last uncertainty found on disk.
        self.uncertain_outcome: dict[str, Any] | None = None
        self.snapshot_revision = 0
        self.published: WorkspaceRead | None = None
        self.published_at: str | None = None
        self.latest: WorkspaceRead | None = None
        self.latest_at: str | None = None
        #: The committed fingerprint ledger: the source/layout presence map
        #: the service last committed to (its last adopted loaded read, or
        #: that map plus its own write's result). A fresh read equal to it is
        #: the service's own output; any other loaded map is an external
        #: change. Failed reads never move it.
        self.committed: dict[str, str] | None = None
        #: The last adopted external change (``sequence`` 0: none yet).
        self.external_change: dict[str, Any] = {"sequence": 0, "at": None, "documents": []}
        #: Watch coordinator status (see :mod:`elosern_map_editor.watching`).
        self.following: dict[str, Any] = {"active": False, "batches": 0, "error": None}
        # Startup is a fresh disk read with this new session identity.
        self._adopt(read_workspace(self.workspace, config.limits))

    # -- state -----------------------------------------------------------
    def _adopt(
        self, read: WorkspaceRead, expected: dict[str, str] | None = None, *, bump: bool = False
    ) -> bool:
        """Record one read; return whether the observable state changed.

        ``expected`` is the fingerprint map an own write should have produced;
        otherwise the read is reconciled against the committed ledger. A
        loaded read whose map differs is an adopted external change: the
        history is cleared and the change is recorded. A failed read clears
        the history and keeps the last preview (stale) and the ledger.
        ``bump`` forces one revision change (an own write moved the history).
        """

        baseline = expected if expected is not None else self._ledger(read)
        now = _now()
        if read.loaded:
            current = read.fingerprint_map
            if baseline is not None and current != baseline:
                self.history.clear()
                self._record_external(baseline, current, now)
            self.committed = current
            # A loaded read with other partition inputs ends a generating job.
            if read.authoring is not None:
                self.partitions.invalidate(read.authoring.partition_signature)
        else:
            self.history.clear()
        if self.latest is not None and read.digest == self.latest.digest:
            # Same observable state: record the check, publish nothing.
            self.latest_at = now
            if bump:
                self.snapshot_revision += 1
            return bump
        self.latest, self.latest_at = read, now
        if read.loaded:
            self.published, self.published_at = read, now
        self.snapshot_revision += 1
        return True

    def _ledger(self, read: WorkspaceRead) -> dict[str, str] | None:
        """The committed ledger, accepting either outcome of an uncertain write.

        While a publication is uncertain, its document may hold the intended
        or the baseline presence; both are the service's own output.
        """

        intent = self.uncertain
        if intent is None or self.committed is None or not read.loaded:
            return self.committed
        document = intent["document_id"]
        found = read.fingerprint_map.get(document, ABSENT)
        if found not in (intent["intended_fingerprint"], intent["baseline_fingerprint"]):
            return self.committed
        ledger = dict(self.committed)
        if found == ABSENT:
            ledger.pop(document, None)
        else:
            ledger[document] = found
        return ledger

    def _record_external(self, baseline: dict[str, str], current: dict[str, str], now: str) -> None:
        changed = sorted(
            path for path in set(baseline) | set(current) if baseline.get(path) != current.get(path)
        )
        self.external_change = {
            "sequence": self.external_change["sequence"] + 1,
            "at": now,
            "documents": changed,
        }

    @property
    def preview_state(self) -> str:
        if self.latest is not None and self.latest.loaded:
            return PREVIEW_CURRENT
        return PREVIEW_STALE if self.published is not None else PREVIEW_UNAVAILABLE

    @property
    def write_pause(self) -> dict[str, Any]:
        """The explicit write pause, orthogonal to the preview state.

        Only an uncertain publication (``save_uncertain`` or a failed reread
        after publication) pauses writes until an explicit reread loads. A
        stale or unavailable preview is the separate ``preview_state``
        condition; both are checked at admission.
        """

        if self.uncertain is not None:
            return {"paused": True, "reason": "uncertain_durability"}
        return {"paused": False, "reason": None}

    def _invalidate(self) -> None:
        """An observable change that is not a new read (pause, history)."""

        self.snapshot_revision += 1

    def status(self) -> dict[str, Any]:
        with self._state:
            return {
                "session_generation": self.session.generation,
                "snapshot_revision": self.snapshot_revision,
                "preview_state": self.preview_state,
            }

    def workspace_state(self) -> dict[str, Any]:
        with self._state:
            return self._workspace_state()

    def _workspace_state(self) -> dict[str, Any]:
        latest = self.latest
        published = self.published
        assert latest is not None
        failed = not latest.loaded
        return {
            "session_generation": self.session.generation,
            "snapshot_revision": self.snapshot_revision,
            "write_pause": self.write_pause,
            "preview_state": self.preview_state,
            "snapshot_read_at": self.published_at if published else None,
            "checked_at": self.latest_at,
            "schema": schema(),
            "documents": list(published.documents) if published else [],
            "world": published.world if published else None,
            "diagnostics": list(published.diagnostics) if published else [],
            "candidate_diagnostics": list(latest.diagnostics) if failed else [],
            "external_context_status": latest.external_context_status,
            "external_incoming_references": {
                ref: list(rows) for ref, rows in (published.external_incoming_references if published else ())
            },
            "external_identifiers": {
                family: list(values) for family, values in (published.external_identifiers if published else ())
            },
            "partition_status": self._partition_status(latest),
            "partition_job": self.partitions.describe(),
            "history": self.history.describe(),
            "pending_intent": self.uncertain,
            "uncertain_outcome": self.uncertain_outcome,
            "external_change": dict(self.external_change, documents=list(self.external_change["documents"])),
            "following": dict(self.following),
        }

    def _partition_status(self, latest: WorkspaceRead) -> dict[str, Any]:
        """The artifact freshness plus explicit game readiness.

        ``game_ready`` is true only for an artifact that describes the current
        inputs and whose last publication was not of uncertain durability.
        """

        job = self.partitions.describe()
        status = dict(latest.partition_status)
        status["game_ready"] = bool(status.get("current")) and job["reason"] != "publish_uncertain"
        return status

    def route(self, settlement_id: str, source: str, destination: str) -> dict[str, Any] | None:
        """The core's route preview over the published snapshot, or None.

        One consistent (read, revision) pair is taken under the state lock;
        the immutable world is then read outside it. Nothing is written.
        """

        with self._state:
            published, revision = self.published, self.snapshot_revision
        world = published.authoring if published is not None else None
        settlement = world.settlements.get(settlement_id) if world is not None else None
        if settlement is None:
            return None
        preview = settlement_route(settlement_id, settlement, source, destination)
        return {"snapshot_revision": revision, "settlement_id": settlement_id, **preview.as_dict()}

    async def reload(self) -> bool:
        async with self._lock:
            # Shielded: a cancelled request cannot release the lock while its
            # worker thread is still reading, so rereads stay strictly serial.
            changed = await _finish(run_in_threadpool(self._reload_io))
        if changed:
            self.broadcaster.publish("invalidate", self.status())
        return changed

    def _reload_io(self) -> bool:
        with self._io:
            read = read_workspace(self.workspace, self.config.limits)
            with self._state:
                return self._resolve(read)

    async def follow(self) -> bool:
        """Reconcile the workspace after coalesced directory notifications.

        Serialized with commands and rereads under the service lock. It never
        resolves an uncertain publication (only the explicit reread does).
        """

        async with self._lock:
            changed = await _finish(run_in_threadpool(self.reconcile))
        if changed:
            self.broadcaster.publish("invalidate", self.status())
        return changed

    def reconcile(self) -> bool:
        """One watcher reread and its reconciliation (caller holds the lock).

        A candidate that does not load is read once more after the settle
        interval before it is published as stale, so a write caught half-way
        (truncate-then-write) does not cost the history.
        """

        with self._io:
            read = read_workspace(self.workspace, self.config.limits)
            if not read.loaded and self.config.settle_seconds > 0:
                time.sleep(self.config.settle_seconds)
                read = read_workspace(self.workspace, self.config.limits)
            with self._state:
                return self._adopt(read)

    def _resolve(self, read: WorkspaceRead) -> bool:
        changed = self._adopt(read)
        if self.uncertain is not None and read.loaded:
            # Only a loadable reread resolves an uncertain publication. It
            # reports what is on disk; it never claims a save, and the
            # history of the interrupted segment is not kept.
            intent = self.uncertain
            found = read.fingerprint_map.get(intent["document_id"], ABSENT)
            if found == intent["intended_fingerprint"]:
                landed = "intended"
            elif found == intent["baseline_fingerprint"]:
                landed = "baseline"
            else:
                landed = "other"
            self.uncertain = None
            self.uncertain_outcome = {**intent, "found_fingerprint": found, "landed": landed}
            self.history.clear()
            self._invalidate()
            changed = True
        return changed

    # -- commands --------------------------------------------------------
    async def command(self, name: str, raw: bytes) -> dict[str, Any]:
        async with self._lock:
            try:
                # Shielded like the reread: a cancelled request cannot release
                # the lock while its worker thread may still be publishing.
                return await _finish(run_in_threadpool(self._execute_io, name, raw))
            finally:
                if self._notify:
                    self._notify = False
                    self.broadcaster.publish("invalidate", self.status())

    _notify = False

    def _execute_io(self, name: str, raw: bytes) -> dict[str, Any]:
        with self._io:
            return self._execute(name, raw)

    def _refuse_during_generation(self, relative_path: str) -> None:
        """World-data writes wait for the partition job; layouts do not.

        An editor layout cannot change a generation input, so layout commands
        (and their undo/redo) stay admitted while a job runs.
        """

        if self.partitions.running and is_world_source(relative_path):
            raise CommandError(
                423,
                "write_paused",
                "world-data writes are rejected while the partition is generating",
                reason="partition_generating",
                document_id=relative_path,
            )

    def _admit(self, name: str, raw: bytes) -> Envelope:
        if name not in COMMANDS:
            raise CommandError(404, "unknown_command", f"there is no command named {name!r}")
        envelope = parse_envelope(raw)
        if envelope.session_generation != self.session.generation:
            raise CommandError(409, "stale_session", "the session changed; reread before writing")
        if envelope.snapshot_revision != self.snapshot_revision:
            raise CommandError(
                409,
                "stale_snapshot",
                "the snapshot changed; reread before writing",
                snapshot_revision=self.snapshot_revision,
            )
        pause = self.write_pause
        if pause["paused"]:
            raise CommandError(423, "write_paused", "writes are paused", reason=pause["reason"])
        preview = self.preview_state
        if preview != PREVIEW_CURRENT:
            # World-data and layout writes wait for a loadable candidate;
            # recovery is automatic on the next loadable change.
            raise CommandError(
                423, "write_paused", "writes are rejected while the preview is not current",
                reason=f"{preview}_preview",
            )
        self._refuse_during_generation(envelope.document_id)
        return envelope

    def _current(self, document_id: str, expected: str) -> Current:
        """The guard-checked current state of the target document."""

        assert self.latest is not None
        known = self.latest.fingerprint_map.get(document_id, ABSENT)
        if expected != known:
            raise CommandError(
                409, "stale_document", "the document changed; reread before writing", fingerprint=known
            )
        fingerprint, data = self.writer.read(document_id)
        if fingerprint != expected:
            raise CommandError(
                409, "stale_document", "the document changed on disk; reread before writing",
                fingerprint=fingerprint,
            )
        if data is None:
            return Current(ABSENT, None)
        try:
            return Current(fingerprint, data.decode("utf-8"))
        except UnicodeDecodeError:
            raise CommandError(422, "validation_failed", "the document is not valid UTF-8") from None

    def _execute(self, name: str, raw: bytes) -> dict[str, Any]:
        envelope = self._admit(name, raw)
        if name in ("undo", "redo"):
            if envelope.arguments:
                raise CommandError(400, "invalid_command", "undo and redo take no arguments")
            entry = self.history.top(name, envelope.segment)
            if entry is None:
                raise CommandError(409, "history_empty", f"there is nothing to {name} in this segment")
            effect, expected = entry.undo_effect() if name == "undo" else entry.redo_effect()
            if (envelope.document_id, envelope.expected) != (entry.document_id, expected):
                raise CommandError(409, "stale_history", "the history changed; reread before writing")
            current = self._current(envelope.document_id, expected)
            before = Presence(current.fingerprint, current.text)
            command = entry.command
        else:
            assert self.published is not None and self.published.world is not None
            handler = HANDLERS[name]
            handler.target(self.published.world, envelope)
            current = self._current(envelope.document_id, envelope.expected)
            effect = handler.effect(envelope, current)
            if effect is None:
                return {**self.status(), "changed": False, "document_id": envelope.document_id,
                        "fingerprint": current.fingerprint}
            before = Presence(current.fingerprint, current.text)
            entry = None
            command = name
        return self.apply_effect(effect, before, command=command, segment=envelope.segment,
                                 direction=name if entry is not None else None)

    def apply_effect(
        self,
        effect: Effect,
        before: Presence,
        *,
        command: str,
        segment: str,
        direction: str | None = None,
    ) -> dict[str, Any]:
        """Validate, publish and record one effect (no HTTP route reaches this).

        Named handlers and history inverses are its only production callers;
        ``direction`` is ``undo``/``redo`` for a history move, else ``None``.
        """

        # The authoritative exclusion check, keyed on the effect's own path.
        self._refuse_during_generation(effect.relative_path)
        validate_candidate(self.workspace, self.config.limits, effect)
        result = self._publish(command, effect, before.fingerprint)
        assert self.committed is not None
        expected_map = dict(self.committed)
        if result == ABSENT:
            expected_map.pop(effect.relative_path, None)
        else:
            expected_map[effect.relative_path] = result
        try:
            read = read_workspace(self.workspace, self.config.limits)
        except Exception as error:
            # Published, but the service cannot see what it now holds: stop
            # writing and require a reread instead of trusting stale state.
            # The write itself published: the ledger includes it.
            with self._state:
                self.committed = expected_map
            self._pause(command, effect, before.fingerprint, f"the reread after publication failed: {error}")
            raise CommandError(
                500, "reread_failed", "the document was written but could not be reread; reread before writing",
                document_id=effect.relative_path,
            ) from error
        # History, the new read and the revision change together, once.
        with self._state:
            actual = read.fingerprint_map
            if read.loaded and actual.get(effect.relative_path, ABSENT) == result:
                if actual != expected_map:
                    # Another document changed externally meanwhile: the
                    # segment ends there, and this guarded operation starts
                    # the next one (a history move has nothing left to move).
                    self.history.clear()
                    self._record_external(expected_map, actual, _now())
                    if direction is None:
                        self.history.record(
                            segment, Entry(command, effect.relative_path, before, Presence(result, effect.text))
                        )
                elif direction is None:
                    self.history.record(segment, Entry(command, effect.relative_path, before, Presence(result, effect.text)))
                else:
                    self.history.confirm(direction)
                self.committed = actual
                self._adopt(read, actual, bump=True)
            else:
                # Our own document is not what we wrote (or the read failed).
                # The write did publish, so the ledger includes it: only the
                # differences from it are external.
                self.committed = expected_map
                # nothing is recorded; the reconciliation clears the history.
                self._adopt(read, expected_map, bump=True)
        self._notify = True
        return {**self.status(), "changed": True, "document_id": effect.relative_path, "fingerprint": result}

    def _pause(self, command: str, effect: Effect, baseline: str, reason: str) -> None:
        with self._state:
            self.uncertain = {
                "command": command,
                "document_id": effect.relative_path,
                "action": effect.action,
                "baseline_fingerprint": baseline,
                "intended_fingerprint": effect.result,
                "reason": reason,
            }
            self.uncertain_outcome = None
            # The stacks stay as they were; the resolving reread clears them.
            self._invalidate()
        self._notify = True

    def _publish(self, command: str, effect: Effect, expected: str) -> str:
        try:
            return self.writer.publish(effect, expected)
        except SaveUncertain as error:
            self._pause(command, effect, expected, str(error))
            raise CommandError(500, "save_uncertain", str(error), document_id=effect.relative_path) from error
        except StaleDocument as error:
            raise CommandError(409, "stale_document", str(error), document_id=effect.relative_path) from error
        except WriteError as error:
            raise CommandError(500, error.code, str(error), document_id=effect.relative_path) from error


async def _finish(awaitable):
    """Await work that holds the service lock to its end, even if cancelled.

    A cancelled request or a stopping coordinator must not release the lock
    while its worker thread still reads or publishes, so rereads and commands
    stay strictly serial; the cancellation is re-raised afterwards.
    """

    task = asyncio.ensure_future(awaitable)
    cancelled = False
    while True:
        try:
            result = await asyncio.shield(task)
            break
        except asyncio.CancelledError:
            if task.done():
                raise
            cancelled = True
    if cancelled:
        raise asyncio.CancelledError
    return result


def _error(status: int, code: str, message: str) -> Response:
    return Response(error_body(code, message), status_code=status, media_type="application/json")


def create_app(config: EditorConfig, *, fault=None, partition_hook=None) -> Starlette:
    """The service app; ``fault``/``partition_hook`` are test-only hooks."""

    service = EditorService(config, fault=fault, partition_hook=partition_hook)
    dist = Path(config.frontend_dist)

    async def index(request: Request) -> Response:
        page = dist / "index.html"
        if not page.is_file():
            return PlainTextResponse(
                "The editor frontend is not built. Run: "
                "pnpm --dir tools/map-editor/frontend install --frozen-lockfile && "
                "pnpm --dir tools/map-editor/frontend run build",
                status_code=503,
            )
        return FileResponse(page, media_type="text/html")

    async def session(request: Request) -> Response:
        return JSONResponse(
            {"session_generation": service.session.generation, "token": service.session.token}
        )

    async def workspace(request: Request) -> Response:
        return JSONResponse(service.workspace_state())

    async def events(request: Request) -> Response:
        return StreamingResponse(
            service.broadcaster.stream(
                lambda: format_event("status", service.status()), config.heartbeat_seconds
            ),
            media_type="text/event-stream",
            headers={"x-accel-buffering": "no"},
        )

    async def route(request: Request) -> Response:
        settlement_id = request.path_params["settlement_id"]
        source = request.query_params.get("source", "")
        destination = request.query_params.get("destination", "")
        if not all(_IDENTIFIER.fullmatch(value) and len(value) <= 128 for value in (settlement_id, source, destination)):
            return _error(400, "invalid_query", "settlement, source and destination are authored identifiers")
        # The planner runs off the event loop over the immutable snapshot.
        result = await run_in_threadpool(service.route, settlement_id, source, destination)
        if result is None:
            return _error(404, "unknown_settlement", f"there is no settlement {settlement_id!r} in the snapshot")
        return JSONResponse(result)

    async def reload(request: Request) -> Response:
        try:
            body = json.loads(await request.body())
        except (ValueError, UnicodeDecodeError):
            return _error(400, "invalid_body", "the body is not JSON")
        if not isinstance(body, dict) or set(body) != {"session_generation"}:
            return _error(400, "invalid_body", "the body carries exactly session_generation")
        if body["session_generation"] != service.session.generation:
            return _error(409, "stale_session", "the session changed; reread before writing")
        changed = await service.reload()
        return JSONResponse({**service.status(), "changed": changed})

    async def command(request: Request) -> Response:
        try:
            result = await service.command(request.path_params["name"], await request.body())
        except CommandError as error:
            return Response(error.body(), status_code=error.status, media_type="application/json")
        return JSONResponse(result)

    def _rejected(error: JobRejected) -> Response:
        return JSONResponse(
            {"error": {"code": error.code, "message": str(error), **error.details}}, status_code=error.status
        )

    async def generate(request: Request) -> Response:
        try:
            return JSONResponse(await service.start_partition(await request.body()))
        except JobRejected as error:
            return _rejected(error)

    async def cancel(request: Request) -> Response:
        try:
            return JSONResponse(await service.cancel_partition(await request.body()))
        except JobRejected as error:
            return _rejected(error)

    async def outlines(request: Request) -> Response:
        result = await run_in_threadpool(service.partition_outlines)
        if result is None:
            return _error(404, "partition_unavailable", "the partition artifact is missing or malformed")
        return JSONResponse(result)

    routes = [
        Route("/", index, methods=["GET", "HEAD"]),
        Route("/api/session", session, methods=["GET"]),
        Route("/api/workspace", workspace, methods=["GET"]),
        Route("/api/events", events, methods=["GET"]),
        Route("/api/settlements/{settlement_id}/route", route, methods=["GET"]),
        Route("/api/reload", reload, methods=["POST"]),
        Route("/api/commands/{name}", command, methods=["POST"]),
        Route("/api/partition/generate", generate, methods=["POST"]),
        Route("/api/partition/cancel", cancel, methods=["POST"]),
        Route("/api/partition/outlines", outlines, methods=["GET"]),
    ]
    assets = dist / "assets"
    if assets.is_dir():
        routes.append(Mount("/assets", app=StaticFiles(directory=assets, follow_symlink=False)))

    app = Starlette(routes=routes, lifespan=_lifespan(service))
    app.state.service = service
    return AdmissionMiddleware(
        app,
        allowed_hosts=config.allowed_hosts,
        allowed_origins=config.allowed_origins,
        token=lambda: service.session.token,
        max_body_bytes=config.limits.max_body_bytes,
    )


def _lifespan(service: EditorService):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        service._loop = asyncio.get_running_loop()
        coordinator = None
        if service.config.watch:
            from .watching import WatchCoordinator

            coordinator = WatchCoordinator(service)
            coordinator.start()
        try:
            yield
        finally:
            if coordinator is not None:
                await coordinator.stop()
            service.partitions.shutdown()
            service.broadcaster.close()

    return lifespan


def service_of(app) -> EditorService:
    """The service behind an app returned by :func:`create_app`."""

    return app.app.state.service


__all__ = ["EditorService", "Session", "create_app", "service_of"]
