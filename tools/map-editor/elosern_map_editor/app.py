"""The Starlette application: read model, invalidation stream and reread.

Routes in this slice (later slices add their named domain commands only):

``GET  /``               the built frontend (``index.html``)
``GET  /assets/...``     its local assets
``GET  /api/session``    same-origin token bootstrap
``GET  /api/workspace``  one complete replacement of the authoritative state
``GET  /api/events``     SSE ``status``/``invalidate`` notifications
``POST /api/reload``     authenticated reread of the current disk files

There is no generic patch, file write, path mutation, shell, Python or remote
account route, and no handoff/resume/return route.
"""

from __future__ import annotations

import asyncio
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

from .config import EditorConfig
from .confinement import ConfinedWorkspace
from .events import Broadcaster, format_event
from .security import AdmissionMiddleware, error_body
from .snapshot import WorkspaceRead, read_workspace

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
    """Session, published snapshot and the serialized reread."""

    def __init__(self, config: EditorConfig) -> None:
        self.config = config
        self.workspace = ConfinedWorkspace(config.workspace_root)
        self.session = Session.create()
        self.broadcaster = Broadcaster()
        self._lock = asyncio.Lock()
        self.snapshot_revision = 0
        self.published: WorkspaceRead | None = None
        self.published_at: str | None = None
        self.latest: WorkspaceRead | None = None
        self.latest_at: str | None = None
        # Startup is a fresh disk read with this new session identity.
        self._adopt(read_workspace(self.workspace, config.limits))

    # -- state -----------------------------------------------------------
    def _adopt(self, read: WorkspaceRead) -> bool:
        """Record one read; return whether the observable state changed."""

        now = _now()
        if self.latest is not None and read.digest == self.latest.digest:
            # Same observable state: record the check, publish nothing.
            self.latest_at = now
            return False
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
        state = self.preview_state
        if state == PREVIEW_CURRENT:
            return {"paused": False, "reason": None}
        return {"paused": True, "reason": f"{state}_preview"}

    def status(self) -> dict[str, Any]:
        return {
            "session_generation": self.session.generation,
            "snapshot_revision": self.snapshot_revision,
            "preview_state": self.preview_state,
        }

    def workspace_state(self) -> dict[str, Any]:
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
        }

    async def reload(self) -> bool:
        async with self._lock:
            # Shielded: a cancelled request cannot release the lock while its
            # worker thread is still reading, so rereads stay strictly serial.
            read = await asyncio.shield(
                run_in_threadpool(read_workspace, self.workspace, self.config.limits)
            )
            changed = self._adopt(read)
        if changed:
            self.broadcaster.publish("invalidate", self.status())
        return changed


def _error(status: int, code: str, message: str) -> Response:
    return Response(error_body(code, message), status_code=status, media_type="application/json")


def create_app(config: EditorConfig) -> Starlette:
    service = EditorService(config)
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

    routes = [
        Route("/", index, methods=["GET", "HEAD"]),
        Route("/api/session", session, methods=["GET"]),
        Route("/api/workspace", workspace, methods=["GET"]),
        Route("/api/events", events, methods=["GET"]),
        Route("/api/reload", reload, methods=["POST"]),
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
