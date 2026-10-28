from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import synthetic_workspace  # noqa: E402

from elosern_map_editor.config import EditorConfig  # noqa: E402

PORT = 8765
ORIGIN = f"http://127.0.0.1:{PORT}"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return synthetic_workspace.write_workspace(tmp_path / "workspace")


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html><title>editor</title>", encoding="utf-8")
    (root / "assets" / "app.js").write_text("export {};", encoding="utf-8")
    return root


def make_config(workspace: Path, dist: Path | None = None, port: int = PORT, **kwargs) -> EditorConfig:
    return EditorConfig(
        workspace_root=workspace,
        port=port,
        frontend_dist=dist if dist is not None else workspace / "no-dist",
        **kwargs,
    )


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class LiveServer:
    """A real uvicorn server on a loopback port in a background thread."""

    def __init__(self, config: EditorConfig) -> None:
        import uvicorn

        from elosern_map_editor.app import create_app, service_of

        self.app = create_app(config)
        self.service = service_of(self.app)
        self.port = config.port
        self.server = uvicorn.Server(
            uvicorn.Config(
                self.app,
                host="127.0.0.1",
                port=config.port,
                log_level="warning",
                access_log=False,
                lifespan="on",
                timeout_graceful_shutdown=1,
                ws="none",
            )
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self) -> "LiveServer":
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("server did not start")
            time.sleep(0.02)
        return self

    def __exit__(self, *exc) -> None:
        self.server.should_exit = True
        self.thread.join(10)
