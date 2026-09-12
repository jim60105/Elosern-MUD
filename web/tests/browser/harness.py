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
collision, or a stale server. The release-then-bind window between dynamic
port allocation and the launcher binding them is closed two ways: every
runtime's ports are allocated, and then booted to the point the portal holds
them, under a runner-local ``flock`` startup lock, so concurrent harness
processes (the packed browser shards run two per machine) can never
interleave allocation-to-bind; and a boot that answers ``already running`` --
impossible for a freshly cleared runtime unless the launcher joined a foreign
portal on a released AMP port -- is failed fast and retried with a fresh
runtime.
"""

from __future__ import annotations

import atexit
import fcntl
import os
import signal
import subprocess
import tempfile
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

# The launcher prints this pair when its status probe reaches a live portal on
# the runtime's AMP port. A freshly cleared runtime can never legitimately be
# "already running": the probe hit ANOTHER harness's portal after that AMP
# port was released by allocation and rebound by the sibling (a variant of the
# port race the launcher reports with no error marker, exit code 0). Failing
# fast here beats waiting out the readiness timeout against a port that will
# never bind; the retry then allocates a fresh runtime.
_FOREIGN_PORTAL_MARKER = "Portal is already running as process"

# Runner-local serialization of the port-critical startup section. Two
# harness processes share one runner on the packed browser shards, and
# dynamic-port allocation cannot coordinate across processes: one process may
# allocate a port another has released but not yet bound. Allocating a
# runtime's ports and booting until the portal holds them is therefore done
# under an advisory ``flock`` on one file in the system temp directory (the
# filesystem both processes share; matrix jobs run on separate machines, so
# the lock never contends across jobs).
STARTUP_LOCK_PATH = Path(tempfile.gettempdir()) / "elosern-browser-startup.lock"

# The lock is advisory ``flock``, which the kernel releases automatically when
# the owning process dies -- a crashed shard cannot wedge the runner, so there
# is no stale-owner breaking (and none of its live-owner revocation risk).
# The wait ceiling only has to sit safely above the bounded critical section
# (migrate <=300s + seed <=300s + boot <=600s + slack); exceeding it means a
# genuinely wedged holder, which must fail loudly, not be cut in line.
STARTUP_LOCK_WAIT_TIMEOUT = 1800.0
STARTUP_LOCK_POLL = 1.0


class _StartupLock:
    """``flock``-based cross-process serialization of server startup.

    ``fcntl.flock(fd, LOCK_EX)`` is held on an open file description the
    process keeps for the duration; the kernel drops it on process exit, so
    owners never need to be identified or evicted. Acquisition is non-blocking
    with a poll loop so a wedged (live but stuck) holder surfaces as a named
    harness failure once the bounded critical section's own ceiling passes.
    """

    def __init__(
        self,
        path: Path = STARTUP_LOCK_PATH,
        wait_timeout: float = STARTUP_LOCK_WAIT_TIMEOUT,
        poll: float = STARTUP_LOCK_POLL,
    ) -> None:
        self.path = path
        self.wait_timeout = wait_timeout
        self.poll = poll
        self._fd: int | None = None

    def acquire(self) -> None:
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.monotonic() + self.wait_timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                if time.monotonic() >= deadline:
                    raise HarnessError(
                        "browser startup lock held beyond its bounded "
                        f"critical section: {self.path}"
                    )
                time.sleep(self.poll)
                fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o644)
                continue
            # Record the owner for diagnostics only; never used to evict.
            os.ftruncate(fd, 0)
            os.write(fd, str(os.getpid()).encode("ascii"))
            self._fd = fd
            return

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> "_StartupLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def _startup_lock() -> _StartupLock:
    """Indirection so tests can neutralize cross-process serialization."""
    return _StartupLock(STARTUP_LOCK_PATH)


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
        # ``create_runtime`` deliberately allocates NO ports: the port set is
        # the only runner-shared resource, and ``_start_once`` takes it under
        # the startup lock for every runtime, caller-provided included.
        # A runtime whose ports are already allocated bypasses that lock (the
        # release-then-bind window is already open before we see it), so it is
        # rejected here rather than silently treated as protected.
        if runtime is not None and runtime.ports is not None:
            raise HarnessError(
                "ManagedServer requires a runtime with unallocated ports; "
                "allocate_ports() before start() reintroduces the sibling "
                "release-then-bind race the startup lock exists to close"
            )
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

        Port allocation through successful boot runs under a runner-local
        startup lock so the two harness processes sharing a CI runner never
        interleave the release-then-bind window. A boot whose diagnostics show
        a loopback port conflict, or an ``already running`` answer from a
        freshly cleared runtime (the launcher joined a foreign portal on a
        released AMP port), is retried with a fresh runtime up to
        ``MAX_PORT_CONFLICT_RETRIES`` times; other failures propagate
        immediately.
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
                joined_foreign_portal = _FOREIGN_PORTAL_MARKER in diagnostics
                self.stop()
                if (
                    not (is_port_conflict or joined_foreign_portal)
                    or attempt >= MAX_PORT_CONFLICT_RETRIES
                ):
                    raise
                attempt += 1
                # Runtime creation allocates no ports, so replacing it here is
                # race-free; the next attempt takes fresh ports under the lock
                # exactly like any other attempt.
                self.runtime = fixtures.recreate_runtime(self.runtime)
                self.migrate_result = None
                self.seed_result = None
                self.boot_result = None

    def _start_once(self) -> None:
        """One migrate/seed/boot/readiness attempt against the current runtime.

        Migrate and seed touch no ports and may overlap sibling processes.
        Everything from the port allocation to the portal holding the ports
        (allocate, clear pidfiles, boot, record pids) runs in ONE acquisition
        of the runner-local startup lock: a sibling cannot allocate ports
        while our released ports await binding, and cannot bind while we are
        between allocate and bind. Once boot returns with the processes up,
        the kernel itself protects the bound ports, so the readiness poll runs
        outside the lock.
        """
        self._run_migrate()
        self._run_seed()
        with _startup_lock():
            self.runtime.allocate_ports()
            self._clear_pidfiles()
            self._run_boot()
            self._raise_if_joined_foreign_portal()
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

    def _raise_if_joined_foreign_portal(self) -> None:
        """Fail a boot where ``evennia start`` joined another harness's portal.

        The launcher prints the already-running pair only when its status
        probe reached a live portal on the runtime's AMP port. Our runtime was
        freshly cleared seconds earlier, so the portal that answered is never
        ours — a sibling grabbed this runtime's AMP port across the release
        window that predates the startup lock. Nothing binds our allocated
        HTTP port, so readiness can never arrive; failing here yields a named
        cause and a fresh-port retry instead of a 240s timeout with a
        misleading message.
        """
        boot_stdout = self.boot_result.stdout if self.boot_result else ""
        if _FOREIGN_PORTAL_MARKER in (boot_stdout or ""):
            raise HarnessError(
                "evennia start joined a foreign portal instead of booting "
                "this runtime\n" + self._diagnostics()
            )

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
