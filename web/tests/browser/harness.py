"""Repeatable managed Evennia server harness for browser acceptance.

``ManagedServer`` owns one Evennia portal+server pair started against an
isolated browser-test runtime: it initializes the temporary SQLite database,
seeds the deterministic account/character, boots Evennia through the
``evennia --settings browser_settings start`` launcher, polls the allocated
WebClient URL until ready, and always stops only its own processes (via the
launcher's AMP shutdown with a direct kill fallback) before removing temporary
state -- on success, failure, or timeout.

Each harness instance uses fresh dynamic loopback ports and temporary roots,
so ``web/tests/browser/`` can be collected repeatedly by the full Evennia
suite and the explicit browser entry point without shared process state, port
collision, or a stale server.
"""

from __future__ import annotations

import atexit
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Callable

from . import fixtures

SERVER_PIDFILE = fixtures.PROJECT_ROOT / "server" / "server.pid"
PORTAL_PIDFILE = fixtures.PROJECT_ROOT / "server" / "portal.pid"

DEFAULT_BOOT_TIMEOUT = 600
DEFAULT_READY_TIMEOUT = 240
DEFAULT_STOP_TIMEOUT = 60

# Ephemeral-port races between concurrent harness processes on one runner.
# ``allocate_ports`` releases its sockets before Evennia binds those exact
# ports, so a sibling process may grab a released port; the portal then fails
# with one of these markers. Retrying with a fresh runtime is the resolution.
_PORT_CONFLICT_MARKERS = ("CannotListenError", "Address already in use")
MAX_PORT_CONFLICT_RETRIES = 2


class HarnessError(RuntimeError):
    """Raised when the managed server cannot be started or verified."""


def _tail(text: str, lines: int = 40) -> str:
    return "\n".join((text or "").strip().splitlines()[-lines:])


class ManagedServer:
    """Owns one isolated Evennia portal+server process pair."""

    def __init__(
        self,
        runtime: fixtures.BrowserRuntime | None = None,
        boot_timeout: float = DEFAULT_BOOT_TIMEOUT,
        ready_timeout: float = DEFAULT_READY_TIMEOUT,
        stop_timeout: float = DEFAULT_STOP_TIMEOUT,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.runtime = runtime or fixtures.create_runtime()
        self.boot_timeout = boot_timeout
        self.ready_timeout = ready_timeout
        self.stop_timeout = stop_timeout
        # ``runner`` is the subprocess entry point; tests inject a fake.
        self.runner = runner or fixtures.run_launcher
        self.started = False
        self.ready = False
        self.pids: dict[str, int] = {}
        self._pidfile_originals: dict[Path, str | None] = {}
        self.migrate_result: subprocess.CompletedProcess[str] | None = None
        self.seed_result: subprocess.CompletedProcess[str] | None = None
        self.boot_result: subprocess.CompletedProcess[str] | None = None

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Migrate, seed, boot, and wait until the WebClient URL answers 200.

        On any failure (migrate, seed, boot, or readiness timeout), owned
        processes are stopped and temporary state is removed so a failing run
        cannot leak live servers, occupied ports, or databases.

        A boot whose diagnostics show a loopback port conflict (the documented
        release-then-bind race between concurrent harness processes) is retried
        with a fresh runtime up to ``MAX_PORT_CONFLICT_RETRIES`` times; other
        failures propagate immediately.
        """
        if self.started:
            return
        attempt = 0
        while True:
            try:
                self._start_once()
                return
            except BaseException:
                diagnostics = self._diagnostics()
                is_port_conflict = any(
                    marker in diagnostics for marker in _PORT_CONFLICT_MARKERS
                )
                self.stop()
                if not is_port_conflict or attempt >= MAX_PORT_CONFLICT_RETRIES:
                    raise
                attempt += 1
                self.runtime = fixtures.recreate_runtime(self.runtime)
                self.migrate_result = None
                self.seed_result = None
                self.boot_result = None

    def _start_once(self) -> None:
        """One migrate/seed/boot/readiness attempt against the current runtime."""
        self._run_migrate()
        self._run_seed()
        self._clear_pidfiles()
        self._run_boot()
        self._record_pids()
        self.ready = fixtures.webclient_ready(
            self.runtime, timeout=self.ready_timeout
        )
        if not self.ready:
            raise HarnessError(
                "managed server did not become ready in time\n"
                + self._diagnostics()
            )
        self.started = True

    def stop(self) -> None:
        """Shut down owned processes and remove temporary state.

        Safe to call when ``start()`` failed partway: only recorded PIDs are
        killed, only recorded pidfiles are removed, and temporary state is
        always cleaned up.
        """
        try:
            if self.pids:
                self._run_stop()
                if not self._pids_gone():
                    self._kill_recorded()
        finally:
            self._remove_pidfiles()
            self._restore_pidfiles()
            self.runtime.cleanup()
            self.pids = {}
            self.started = False

    # -- subprocess steps (patchable for fast unit tests) -------------------

    def _run_migrate(self) -> None:
        result = fixtures.run_migrate(self.runtime)
        self.migrate_result = result
        if result.returncode != 0:
            raise HarnessError(
                "evennia migrate failed\n"
                + _tail(result.stdout)
                + "\n"
                + _tail(result.stderr)
            )

    def _run_seed(self) -> None:
        result = fixtures.run_seed(self.runtime)
        self.seed_result = result
        if result.returncode != 0:
            raise HarnessError(
                "deterministic seed failed\n"
                + _tail(result.stdout)
                + "\n"
                + _tail(result.stderr)
            )

    def _run_boot(self) -> None:
        """Run ``evennia start`` and wait for the launcher to finish."""
        try:
            result = self.runner(
                self.runtime, "start", timeout=self.boot_timeout
            )
        except subprocess.TimeoutExpired as error:
            raise HarnessError(
                "evennia start timed out after "
                + f"{self.boot_timeout}s\n{self._diagnostics()}"
            ) from error
        self.boot_result = result
        if result.returncode != 0:
            raise HarnessError(
                "evennia start failed\n"
                + _tail(result.stdout)
                + "\n"
                + _tail(result.stderr)
            )

    def _run_stop(self) -> None:
        try:
            self.runner(self.runtime, "stop", timeout=self.stop_timeout)
        except subprocess.TimeoutExpired:
            return

    # -- process ownership --------------------------------------------------

    def _read_pidfile(self, path: Path) -> int | None:
        try:
            raw = path.read_text(encoding="utf-8").strip()
            return int(raw)
        except (OSError, ValueError):
            return None

    def _clear_pidfiles(self) -> None:
        """Back up and remove pidfiles left by a previous instance.

        Twisted's server startup refuses to run when the pidfile names any
        live PID, so a stale file (for example from an earlier container or a
        killed harness) must be cleared before boot. The original content is
        restored on stop so the working tree is left exactly as found.
        """
        for path in (PORTAL_PIDFILE, SERVER_PIDFILE):
            if path.exists():
                try:
                    self._pidfile_originals[path] = path.read_text(
                        encoding="utf-8"
                    )
                except OSError:
                    self._pidfile_originals[path] = None
                try:
                    path.unlink()
                except OSError:
                    pass

    def _restore_pidfiles(self) -> None:
        for path, original in self._pidfile_originals.items():
            try:
                if original is None:
                    if path.exists():
                        path.unlink()
                else:
                    path.write_text(original, encoding="utf-8")
            except OSError:
                pass
        self._pidfile_originals = {}

    def _record_pids(self) -> None:
        for name, path in (("portal", PORTAL_PIDFILE), ("server", SERVER_PIDFILE)):
            pid = self._read_pidfile(path)
            if pid:
                self.pids[name] = pid

    def _pids_gone(self) -> bool:
        for pid in self.pids.values():
            if fixtures.process_is_alive(pid):
                return False
        return True

    def _kill_recorded(self) -> None:
        """Kill only the recorded portal/server PIDs (never an unrelated one)."""
        for name, pid in sorted(self.pids.items()):
            if not fixtures.process_is_alive(pid):
                continue
            try:
                os.kill(pid, signal.SIGTERM)
            except (OSError, PermissionError):
                pass
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self._pids_gone():
                break
            time.sleep(0.5)
        for name, pid in sorted(self.pids.items()):
            if not fixtures.process_is_alive(pid):
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except (OSError, PermissionError):
                pass

    def _remove_pidfiles(self) -> None:
        """Delete pidfiles only when they still name a PID we recorded."""
        for name, path in (("portal", PORTAL_PIDFILE), ("server", SERVER_PIDFILE)):
            current = self._read_pidfile(path)
            if current is not None and current == self.pids.get(name):
                try:
                    path.unlink()
                except OSError:
                    pass

    # -- diagnostics ---------------------------------------------------------

    def _diagnostics(self) -> str:
        lines: list[str] = []
        for label, result in (
            ("migrate", self.migrate_result),
            ("seed", self.seed_result),
            ("boot", self.boot_result),
        ):
            if result is not None:
                lines.append(f"--- {label} exit={result.returncode} ---")
                lines.append(_tail(result.stdout))
                lines.append(_tail(result.stderr))
        for label, path in (
            ("portal log", self.runtime.log_dir / "portal.log"),
            ("server log", self.runtime.log_dir / "server.log"),
        ):
            if path.exists():
                lines.append(f"--- {label} ---")
                lines.append(_tail(path.read_text(encoding="utf-8", errors="replace")))
        return "\n".join(lines) if lines else "(no diagnostics captured)"

    # -- context manager ------------------------------------------------------

    def __enter__(self) -> "ManagedServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()


# ---------------------------------------------------------------------------
# Shared per-process server for the browser acceptance tests.
#
# ``unittest`` collects each test module separately, but a single Python
# process is one collection; starting one server per process (and reusing it
# across every browser test) keeps the suite fast while each collection still
# owns a fresh runtime, ports, and database. ``atexit`` guarantees shutdown
# even when a test fails hard.
# ---------------------------------------------------------------------------

_shared_server: ManagedServer | None = None


def get_shared_server() -> ManagedServer:
    """Return the one managed server for this process, starting it on first use."""
    global _shared_server
    if _shared_server is None:
        _shared_server = ManagedServer()
        atexit.register(_shutdown_shared_server)
        _shared_server.start()
    return _shared_server


def _shutdown_shared_server() -> None:
    global _shared_server
    if _shared_server is not None:
        try:
            _shared_server.stop()
        finally:
            _shared_server = None
