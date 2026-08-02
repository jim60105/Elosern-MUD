"""Fixture helpers for the isolated browser acceptance harness.

Provides per-instance runtime allocation (dynamic loopback ports, temporary
SQLite/log/media/static roots), the deterministic seed command, and the
``evennia`` launcher command runner. All subprocesses run through the locked
uv-managed environment and never read or write the developer database.

Chromium is installed out of band (never committed): the quality workflow runs
``uv run --locked playwright install --with-deps chromium`` before any runner
that can discover these tests.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# The settings module importable by the launcher shim.
SETTINGS_NAME = "browser_settings"
# Settings module used by the one-off seed process.
SEED_SETTINGS_DOTPATH = "web.tests.browser.browser_settings"

# Distinct per-instance services that must never collide with 4000/4001/4002
# or with each other.
PORT_COUNT = 5
TELNET_PORT, HTTP_PORT, INTERNAL_PORT, WS_PORT, AMP_PORT = range(PORT_COUNT)

_READY_TIMEOUT_SECONDS = 180
_READY_POLL_SECONDS = 1.0


@dataclass
class BrowserRuntime:
    """One isolated runtime: temporary roots, dynamic ports, and its env."""

    root_dir: Path
    database_path: Path
    log_dir: Path
    media_dir: Path
    static_dir: Path
    cache_dir: Path
    ports: list[int]
    env: dict[str, str] = field(default_factory=dict)

    @property
    def telnet_port(self) -> int:
        return self.ports[TELNET_PORT]

    @property
    def http_port(self) -> int:
        return self.ports[HTTP_PORT]

    @property
    def websocket_port(self) -> int:
        return self.ports[WS_PORT]

    @property
    def webclient_url(self) -> str:
        return f"http://127.0.0.1:{self.http_port}/webclient/"

    def cleanup(self) -> None:
        """Remove every temporary root created for this instance."""
        shutil.rmtree(self.root_dir, ignore_errors=True)


def allocate_ports(count: int = PORT_COUNT) -> list[int]:
    """Bind ``count`` loopback sockets to port 0 and return their ports.

    All sockets are bound before any is released, so the returned ports are
    distinct within one call. There is still a tiny release-then-bind race,
    which is acceptable for ephemeral ports; distinctness per call is
    guaranteed by the simultaneous bind.
    """
    sockets = []
    try:
        for _ in range(count):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            sockets.append(sock)
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


def create_runtime(prefix: str = "elosern-browser-") -> BrowserRuntime:
    """Create one isolated runtime and its complete environment."""
    root_dir = Path(tempfile.mkdtemp(prefix=prefix))
    log_dir = root_dir / "logs"
    media_dir = root_dir / "media"
    static_dir = root_dir / "static"
    cache_dir = root_dir / "cache"
    database_path = root_dir / "evennia.db3"
    for directory in (log_dir, media_dir, static_dir, cache_dir):
        directory.mkdir(parents=True, exist_ok=True)

    ports = allocate_ports()
    env = {
        "ELOSERN_BROWSER_DB": str(database_path),
        "ELOSERN_BROWSER_LOG_DIR": str(log_dir),
        "ELOSERN_BROWSER_MEDIA_ROOT": str(media_dir),
        "ELOSERN_BROWSER_STATIC_ROOT": str(static_dir),
        "ELOSERN_BROWSER_CACHE_DIR": str(cache_dir),
        "ELOSERN_BROWSER_TELNET_PORT": str(ports[TELNET_PORT]),
        "ELOSERN_BROWSER_HTTP_PORT": str(ports[HTTP_PORT]),
        "ELOSERN_BROWSER_INTERNAL_PORT": str(ports[INTERNAL_PORT]),
        "ELOSERN_BROWSER_WS_PORT": str(ports[WS_PORT]),
        "ELOSERN_BROWSER_AMP_PORT": str(ports[AMP_PORT]),
        # WebSocket port encoded into the webclient page matches the listener.
        "WEBSOCKET_CLIENT_PROXY_PORT": str(ports[WS_PORT]),
    }
    return BrowserRuntime(
        root_dir=root_dir,
        database_path=database_path,
        log_dir=log_dir,
        media_dir=media_dir,
        static_dir=static_dir,
        cache_dir=cache_dir,
        ports=ports,
        env=env,
    )


def _base_env(runtime: BrowserRuntime, extra: dict[str, str] | None = None) -> dict[str, str]:
    """The project's environment plus runtime overrides and the venv on PATH."""
    env = os.environ.copy()
    env.update(runtime.env)
    venv_bin = os.path.dirname(sys.executable)
    env["PATH"] = os.pathsep.join([venv_bin, env.get("PATH", "")])
    if extra:
        env.update(extra)
    return env


def evennia_command(*args: str) -> list[str]:
    """The ``evennia`` launcher command with the browser-test settings."""
    return [sys.executable, "-m", "evennia", "--settings", SETTINGS_NAME, *args]


def run_launcher(
    runtime: BrowserRuntime,
    *args: str,
    timeout: int = 300,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one ``evennia --settings browser_settings <args>`` command."""
    env = _base_env(runtime, env_extra)
    return subprocess.run(
        evennia_command(*args),
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def run_migrate(runtime: BrowserRuntime) -> subprocess.CompletedProcess[str]:
    """Initialize the temporary SQLite database schema."""
    return run_launcher(runtime, "migrate")


def run_seed(runtime: BrowserRuntime) -> subprocess.CompletedProcess[str]:
    """Seed the deterministic account and activated adult character."""
    env = _base_env(
        runtime,
        {"DJANGO_SETTINGS_MODULE": SEED_SETTINGS_DOTPATH},
    )
    return subprocess.run(
        [sys.executable, "-m", "web.tests.browser.seed"],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )


_READY_BODY_MARKER = "id=\"main-sub\""


def webclient_ready(runtime: BrowserRuntime, timeout: float = _READY_TIMEOUT_SECONDS) -> bool:
    """Poll the allocated WebClient URL until it returns the real shell page.

    The project webclient template always contains ``id="main-sub"``; a 200
    without that marker (for example while the server is mid-restart during
    its first boot) is not considered ready.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(runtime.webclient_url, timeout=5) as response:
                if response.status == 200:
                    body = response.read(65536).decode("utf-8", "replace")
                    if _READY_BODY_MARKER in body:
                        return True
        except (urllib.error.URLError, OSError, ConnectionError):
            pass
        time.sleep(_READY_POLL_SECONDS)
    return False


def web_server_settled(
    runtime: BrowserRuntime, timeout: float = 120.0, poll: float = 1.0
) -> bool:
    """Wait until the Django website renders, proving server-side web is up.

    The Evennia server finishes its world bootstrap a few seconds after the
    portal proxy first answers the webclient URL; during that window Django
    pages can return an empty 200. The browser login journey waits for the
    real login form instead of guessing.
    """
    login_url = f"http://127.0.0.1:{runtime.http_port}/auth/login/"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(login_url, timeout=5) as response:
                body = response.read(65536).decode("utf-8", "replace")
                if response.status == 200 and "id_username" in body:
                    return True
        except (urllib.error.URLError, OSError, ConnectionError):
            pass
        time.sleep(poll)
    return False


def process_is_alive(pid: int) -> bool:
    """Return True when ``pid`` refers to a live process we may own."""
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
