"""Run the real editor service as a separate process in its own environment.

Standard library only, so repository-level wrappers and browser tests (which
run in the game's environment) can load this file by path and drive the
editor without importing it. The child process gets a scrubbed environment:
no inherited ``PYTHONPATH``/``VIRTUAL_ENV``/``DJANGO_*`` can leak the game's
packages or settings into the editor, so the editor's own interpreter proves
the framework is absent.
"""

from __future__ import annotations

import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT.parent.parent
FRONTEND_DIST = PROJECT / "frontend" / "dist"
_SCRUBBED_PREFIXES = ("DJANGO_", "EVENNIA", "MUD_", "COVERAGE", "OPENSPEC_")
_SCRUBBED = {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONSTARTUP"}


class EditorUnavailable(RuntimeError):
    """uv is missing or the editor environment cannot be synchronised.

    Callers may skip on it locally, but never in CI: see :func:`skip_allowed`.
    """


def skip_allowed() -> bool:
    """A missing editor environment is a skip locally and a failure in CI."""

    return not os.environ.get("CI")


def scrubbed_env(path: str | None = None) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in _SCRUBBED and not key.startswith(_SCRUBBED_PREFIXES)
    }
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if path is not None:
        env["PATH"] = path
    return env


_SYNCED: Path | None = None


def editor_python() -> Path:
    """Sync the editor's locked environment once and return its interpreter."""

    global _SYNCED
    if _SYNCED is not None:
        return _SYNCED
    uv = shutil.which("uv")
    if uv is None:
        raise EditorUnavailable("uv is not installed; the editor runs in its own uv environment")
    result = subprocess.run(
        [uv, "sync", "--locked", "--project", str(PROJECT)],
        cwd=PROJECT,
        env=scrubbed_env(),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise EditorUnavailable(f"uv sync failed:\n{result.stderr[-2000:]}")
    python = PROJECT / ".venv" / "bin" / "python"
    if not python.exists():
        raise EditorUnavailable(f"{python} is missing after uv sync")
    _SYNCED = python
    return python


def run_editor_python(code: str, *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(editor_python()), "-I", "-c", code],
        cwd=cwd or PROJECT,
        env=scrubbed_env(),
        capture_output=True,
        text=True,
        timeout=120,
    )


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class EditorProcess:
    """``python -m elosern_map_editor`` on a loopback port, as a child process.

    ``node_free_path`` runs the service with a ``PATH`` holding nothing, so no
    Node (or any other tool) is resolvable by the service.
    """

    def __init__(
        self,
        workspace: Path,
        *,
        port: int | None = None,
        frontend_dist: Path | None = None,
        node_free_path: bool = True,
    ) -> None:
        self.workspace = Path(workspace)
        self.port = port or free_port()
        self.frontend_dist = frontend_dist if frontend_dist is not None else self.workspace / "no-frontend-build"
        self.node_free_path = node_free_path
        self.process: subprocess.Popen | None = None
        self._empty_path: str | None = None

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> "EditorProcess":
        path = None
        if self.node_free_path:
            self._empty_path = tempfile.mkdtemp(prefix="editor-empty-path-")
            path = self._empty_path
        self.process = subprocess.Popen(
            [
                str(editor_python()),
                "-I",
                "-m",
                "elosern_map_editor",
                "--workspace",
                str(self.workspace),
                "--port",
                str(self.port),
                "--frontend-dist",
                str(self.frontend_dist),
            ],
            cwd=PROJECT,
            env=scrubbed_env(path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                output = self.process.stdout.read() if self.process.stdout else ""
                raise RuntimeError(f"editor exited with {self.process.returncode}:\n{output}")
            try:
                status, _ = self.request("GET", "/api/session")
                if status == 200:
                    return self
            except OSError:
                pass
            time.sleep(0.1)
        self.__exit__(None, None, None)
        raise RuntimeError("editor service did not start")

    def __exit__(self, *exc) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(10)
        if self.process is not None and self.process.stdout:
            self.process.stdout.close()
        if self._empty_path:
            shutil.rmtree(self._empty_path, ignore_errors=True)

    def request(self, method: str, path: str, *, headers: dict | None = None, body: bytes | str | None = None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            all_headers = {"Host": f"127.0.0.1:{self.port}"}
            all_headers.update(headers or {})
            connection.request(method, path, body=body, headers={k: v for k, v in all_headers.items() if v is not None})
            response = connection.getresponse()
            payload = response.read()
        finally:
            connection.close()
        try:
            data = json.loads(payload) if payload else None
        except ValueError:
            data = payload.decode("utf-8", "replace")
        return response.status, data

    def session(self) -> dict:
        return self.request("GET", "/api/session")[1]

    def workspace_state(self) -> dict:
        return self.request("GET", "/api/workspace")[1]

    def reload(self, token: str | None, generation: str, **header_overrides):
        headers = {
            "Origin": self.origin,
            "X-Map-Editor-Token": token,
            "Content-Type": "application/json",
        }
        headers.update(header_overrides)
        return self.request(
            "POST",
            "/api/reload",
            headers=headers,
            body=json.dumps({"session_generation": generation}),
        )


def command(editor: "EditorProcess", name: str, *, document_id: str, expected: str, arguments: dict,
            segment: str = "wrapper-segment", **overrides):
    """POST one named command with a complete, current envelope."""

    session = editor.session()
    state = editor.workspace_state()
    body = {
        "session_generation": session["session_generation"],
        "snapshot_revision": state["snapshot_revision"],
        "segment": segment,
        "document_id": document_id,
        "expected_document_fingerprint": expected,
        "arguments": arguments,
    }
    body.update(overrides)
    return editor.request(
        "POST",
        f"/api/commands/{name}",
        headers={
            "Origin": editor.origin,
            "X-Map-Editor-Token": session["token"],
            "Content-Type": "application/json",
        },
        body=json.dumps(body),
    )


def load_by_path(name: str, path: Path):
    """Import a stand-alone helper module (e.g. the synthetic workspace) by path."""

    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


__all__ = [
    "EditorProcess",
    "command",
    "EditorUnavailable",
    "FRONTEND_DIST",
    "PROJECT",
    "REPO_ROOT",
    "editor_python",
    "free_port",
    "load_by_path",
    "run_editor_python",
    "scrubbed_env",
]
