"""The Starlette application: read model, invalidation stream and reread.

Routes in this slice (later slices add their named domain commands only):

``GET  /``               the built frontend (``index.html``)
``GET  /assets/...``     its local assets
``GET  /api/session``    same-origin token bootstrap
``GET  /api/workspace``  one complete replacement of the authoritative state
``GET  /api/events``     SSE ``status``/``invalidate`` notifications
``POST /api/reload``     authenticated reread of the current disk files
``POST /api/commands/<name>`` one named single-document command, undo or redo
                         (see :mod:`elosern_map_editor.commands`)

There is no generic patch, file write, path mutation, shell, Python or remote
account route, and no handoff/resume/return route.
"""

from __future__ import annotations

import asyncio
import threading
import json
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from elosern_map_core import schema
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
from .confinement import ConfinedWorkspace
from .events import Broadcaster, format_event
from .history import Entry, History, Presence
from .security import AdmissionMiddleware, error_body
from .snapshot import WorkspaceRead, read_workspace
from .writer import ABSENT, DocumentWriter, Effect, SaveUncertain, StaleDocument, WriteError

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


class EditorService:
    """Session, published snapshot, the serialized writer and its history.

    Every reread and every command runs under one lock, so source/layout
    writes are strictly serial and each sees the state the previous one left.
    """

    def __init__(self, config: EditorConfig, *, fault=None) -> None:
        self.config = config
        self.workspace = ConfinedWorkspace(config.workspace_root)
        self.session = Session.create()
        self.broadcaster = Broadcaster()
        self._lock = asyncio.Lock()
        #: Guards the observable state (read, history, pause, revision) so a
        #: concurrent GET never sees a half-applied command.
        self._state = threading.RLock()
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
        # Startup is a fresh disk read with this new session identity.
        self._adopt(read_workspace(self.workspace, config.limits))

    # -- state -----------------------------------------------------------
    def _adopt(
        self, read: WorkspaceRead, expected: dict[str, str] | None = None, *, bump: bool = False
    ) -> bool:
        """Record one read; return whether the observable state changed.

        ``expected`` is the source/layout fingerprint map an own write should
        have produced. History survives only a loaded read whose map equals
        it (or, for a reread, equals the previous map); any other adopted map,
        or a failed read, is an external change and clears the history.
        ``bump`` forces one revision change (an own write moved the history).
        """

        previous = self.latest.fingerprint_map if self.latest is not None else None
        if read.loaded:
            baseline = expected if expected is not None else previous
            if read.fingerprint_map != baseline:
                self.history.clear()
        else:
            self.history.clear()
        now = _now()
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

    @property
    def preview_state(self) -> str:
        if self.latest is not None and self.latest.loaded:
            return PREVIEW_CURRENT
        return PREVIEW_STALE if self.published is not None else PREVIEW_UNAVAILABLE

    @property
    def write_pause(self) -> dict[str, Any]:
        if self.uncertain is not None:
            return {"paused": True, "reason": "uncertain_durability"}
        state = self.preview_state
        if state == PREVIEW_CURRENT:
            return {"paused": False, "reason": None}
        return {"paused": True, "reason": f"{state}_preview"}

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
            "partition_status": latest.partition_status,
            "history": self.history.describe(),
            "pending_intent": self.uncertain,
            "uncertain_outcome": self.uncertain_outcome,
        }

    async def reload(self) -> bool:
        async with self._lock:
            # Shielded: a cancelled request cannot release the lock while its
            # worker thread is still reading, so rereads stay strictly serial.
            read = await asyncio.shield(
                run_in_threadpool(read_workspace, self.workspace, self.config.limits)
            )
            with self._state:
                changed = self._resolve(read)
        if changed:
            self.broadcaster.publish("invalidate", self.status())
        return changed

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
                return await asyncio.shield(run_in_threadpool(self._execute, name, raw))
            finally:
                if self._notify:
                    self._notify = False
                    self.broadcaster.publish("invalidate", self.status())

    _notify = False

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

        validate_candidate(self.workspace, self.config.limits, effect)
        result = self._publish(command, effect, before.fingerprint)
        assert self.latest is not None
        expected_map = dict(self.latest.fingerprint_map)
        if result == ABSENT:
            expected_map.pop(effect.relative_path, None)
        else:
            expected_map[effect.relative_path] = result
        try:
            read = read_workspace(self.workspace, self.config.limits)
        except Exception as error:
            # Published, but the service cannot see what it now holds: stop
            # writing and require a reread instead of trusting stale state.
            self._pause(command, effect, before.fingerprint, f"the reread after publication failed: {error}")
            raise CommandError(
                500, "reread_failed", "the document was written but could not be reread; reread before writing",
                document_id=effect.relative_path,
            ) from error
        # History, the new read and the revision change together, once.
        with self._state:
            if direction is None:
                self.history.record(segment, Entry(command, effect.relative_path, before, Presence(result, effect.text)))
            else:
                self.history.confirm(direction)
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


def _error(status: int, code: str, message: str) -> Response:
    return Response(error_body(code, message), status_code=status, media_type="application/json")


def create_app(config: EditorConfig, *, fault=None) -> Starlette:
    """The service app; ``fault`` is the writer's test-only fault hook."""

    service = EditorService(config, fault=fault)
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

    routes = [
        Route("/", index, methods=["GET", "HEAD"]),
        Route("/api/session", session, methods=["GET"]),
        Route("/api/workspace", workspace, methods=["GET"]),
        Route("/api/events", events, methods=["GET"]),
        Route("/api/reload", reload, methods=["POST"]),
        Route("/api/commands/{name}", command, methods=["POST"]),
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
        yield
        service.broadcaster.close()

    return lifespan


def service_of(app) -> EditorService:
    """The service behind an app returned by :func:`create_app`."""

    return app.app.state.service


__all__ = ["EditorService", "Session", "create_app", "service_of"]
