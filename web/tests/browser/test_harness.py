"""Harness unit tests (section 6.3) plus one real end-to-end server boot.

The fast tests drive ``ManagedServer`` with fake subprocess runners so startup
failure, readiness timeout, process ownership, and cleanup are verified
without booting a server. One test actually starts the real Evennia portal and
server against an isolated runtime, proves the WebClient answers, and confirms
its processes are stopped and temporary state removed.
"""

from __future__ import annotations

import subprocess
import fcntl
import os
import tempfile
import time
from pathlib import Path
from unittest import mock
import unittest

from . import fixtures
from .harness import (
    HarnessError,
    ManagedServer,
    PORTAL_PIDFILE,
    SERVER_PIDFILE,
)


class FakeRunner:
    """Stand-in for ``fixtures.run_launcher`` recording every invocation."""

    def __init__(self, start_rc: int = 0, stop_rc: int = 0):
        self.calls: list[tuple[tuple, dict]] = []
        self.start_rc = start_rc
        self.stop_rc = stop_rc

    def __call__(self, runtime, *args, **kwargs):
        self.calls.append((args, kwargs))
        if args[0] == "start":
            result = subprocess.CompletedProcess(
                ["start"], self.start_rc, "started", ""
            )
        elif args[0] == "stop":
            result = subprocess.CompletedProcess(
                ["stop"], self.stop_rc, "stopped", ""
            )
        else:
            result = subprocess.CompletedProcess(list(args), 0, "", "")
        return result


def _ok_result(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([name], 0, f"{name} ok", "")


class ManagedServerFastTests(unittest.TestCase):
    """Fast harness behavior tests using fake subprocesses."""

    def setUp(self):
        self.runtime = fixtures.create_runtime(prefix="elosern-fast-")
        self.addCleanup(self.runtime.cleanup)
        self.fake = FakeRunner()
        self.server = ManagedServer(runtime=self.runtime, runner=self.fake)

    def _patch_steps(self, ready: bool = True):
        migrate = mock.patch(
            "web.tests.browser.harness.fixtures.run_migrate",
            return_value=_ok_result("migrate"),
        )
        seed = mock.patch(
            "web.tests.browser.harness.fixtures.run_seed",
            return_value=_ok_result("seed"),
        )
        poll = mock.patch(
            "web.tests.browser.harness.fixtures.webclient_ready",
            return_value=ready,
        )
        for patcher in (migrate, seed, poll):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_startup_failure_is_detected(self):
        """A failing migrate raises and records diagnostics without booting."""
        migrate = mock.patch(
            "web.tests.browser.harness.fixtures.run_migrate",
            return_value=subprocess.CompletedProcess(
                ["migrate"], 1, "boom", "traceback"
            ),
        )
        migrate.start()
        self.addCleanup(migrate.stop)
        with self.assertRaises(HarnessError) as caught:
            self.server.start()
        self.assertIn("migrate failed", str(caught.exception))
        self.assertIn("traceback", str(caught.exception))
        self.assertFalse(self.server.started)
        # The fake boot step must never have run.
        self.assertEqual(
            [call[0] for call in self.fake.calls], []
        )

    def test_readiness_timeout_is_reported(self):
        """A ready-poll timeout raises with diagnostics and still stops."""
        self._patch_steps(ready=False)
        self.fake.start_rc = 0
        with self.assertRaises(HarnessError) as caught:
            self.server.start()
        self.assertIn("did not become ready", str(caught.exception))
        self.assertIn("migrate", str(caught.exception))
        self.assertFalse(self.server.ready)
        self.server.stop()
        self.assertFalse(self.runtime.root_dir.exists())

    def test_port_conflict_boot_is_retried_with_fresh_runtime(self):
        """A portal killed by an occupied port is retried with fresh ports.

        Two harness processes may run concurrently on one runner (the packed
        browser shards); the ephemeral-port release-then-bind race can make
        the portal fail with ``Address already in use``. The harness must
        retry with a fresh runtime instead of failing the whole shard.
        """
        ready_calls = {"count": 0}

        def flaky_ready(runtime, timeout=0):
            ready_calls["count"] += 1
            if ready_calls["count"] == 1:
                # The real portal writes the bind failure into its log before
                # the readiness poll gives up.
                runtime.log_dir.mkdir(parents=True, exist_ok=True)
                (runtime.log_dir / "portal.log").write_text(
                    "twisted.internet.error.CannotListenError: Couldn't listen "
                    "on 127.0.0.1:44951: [Errno 98] Address already in use.\n",
                    encoding="utf-8",
                )
                return False
            return True

        migrate = mock.patch(
            "web.tests.browser.harness.fixtures.run_migrate",
            return_value=_ok_result("migrate"),
        )
        seed = mock.patch(
            "web.tests.browser.harness.fixtures.run_seed",
            return_value=_ok_result("seed"),
        )
        poll = mock.patch(
            "web.tests.browser.harness.fixtures.webclient_ready",
            side_effect=flaky_ready,
        )
        for patcher in (migrate, seed, poll):
            patcher.start()
            self.addCleanup(patcher.stop)

        first_runtime = self.server.runtime
        first_runtime.env["ELOSERN_BROWSER_CREATION"] = "1"
        self.server.start()
        self.assertTrue(self.server.started)
        self.assertEqual(ready_calls["count"], 2)
        self.assertIsNot(self.server.runtime, first_runtime)
        self.assertFalse(first_runtime.root_dir.exists())
        self.assertEqual(
            self.server.runtime.env["ELOSERN_BROWSER_CREATION"], "1"
        )
        self.server.stop()
        self.assertFalse(self.server.runtime.root_dir.exists())

    def test_port_conflict_retries_exhausted_raises(self):
        """A persistent port conflict gives up after the retry budget."""
        ready_calls = {"count": 0}

        def always_conflicting(runtime, timeout=0):
            ready_calls["count"] += 1
            runtime.log_dir.mkdir(parents=True, exist_ok=True)
            (runtime.log_dir / "portal.log").write_text(
                "twisted.internet.error.CannotListenError: Couldn't listen on "
                "127.0.0.1:44951: [Errno 98] Address already in use.\n",
                encoding="utf-8",
            )
            return False

        migrate = mock.patch(
            "web.tests.browser.harness.fixtures.run_migrate",
            return_value=_ok_result("migrate"),
        )
        seed = mock.patch(
            "web.tests.browser.harness.fixtures.run_seed",
            return_value=_ok_result("seed"),
        )
        poll = mock.patch(
            "web.tests.browser.harness.fixtures.webclient_ready",
            side_effect=always_conflicting,
        )
        for patcher in (migrate, seed, poll):
            patcher.start()
            self.addCleanup(patcher.stop)

        with self.assertRaises(HarnessError) as caught:
            self.server.start()
        self.assertIn("did not become ready", str(caught.exception))
        self.assertIn("Address already in use", str(caught.exception))
        self.assertFalse(self.server.started)
        self.assertEqual(ready_calls["count"], 3)

    def test_readiness_timeout_cleans_up_automatically(self):
        """A failed start must stop owned processes and remove temp state.

        ``start()`` raises, and the failure path itself runs ``stop()`` so a
        failing browser run cannot leak a live server or temporary roots.
        """
        self._patch_steps(ready=False)
        self.fake.start_rc = 0
        # Simulate recorded PIDs from the (fake) boot step.
        self.server.pids = {"server": 999999, "portal": 999998}
        with self.assertRaises(HarnessError):
            self.server.start()
        self.assertFalse(self.server.started)
        self.assertFalse(self.runtime.root_dir.exists())
        # ``stop()`` is idempotent after the automatic cleanup.
        self.server.stop()
        self.assertFalse(self.runtime.root_dir.exists())

    def test_boot_failure_raised(self):
        """A failing ``evennia start`` raises instead of silently continuing."""
        self._patch_steps(ready=True)
        self.fake.start_rc = 2
        with self.assertRaises(HarnessError) as caught:
            self.server.start()
        self.assertIn("evennia start failed", str(caught.exception))

    def test_clear_and_restore_pidfiles(self):
        """Stale pidfiles are backed up, cleared, and restored on stop."""
        original = "15\n"
        SERVER_PIDFILE.write_text(original, encoding="utf-8")
        self.addCleanup(lambda: SERVER_PIDFILE.unlink(missing_ok=True))
        self.server._clear_pidfiles()
        self.assertFalse(SERVER_PIDFILE.exists())
        self.server._restore_pidfiles()
        self.assertEqual(SERVER_PIDFILE.read_text(encoding="utf-8"), original)

    def test_recorded_pids_kill_only_owned_processes(self):
        """``_kill_recorded`` terminates recorded PIDs and leaves others alone."""
        owned = subprocess.Popen(["sleep", "30"])
        other = subprocess.Popen(["sleep", "30"])
        self.addCleanup(lambda: other.kill())
        # Only ``owned`` is recorded as ours; ``other`` must be untouched.
        self.server.pids = {"server": owned.pid}
        self.server._kill_recorded()
        deadline = time.monotonic() + 5
        while owned.poll() is None and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertIsNotNone(owned.poll(), "recorded process must be killed")
        self.assertIsNone(other.poll(), "unrelated process must survive")
        other.kill()
        other.wait()

    def test_remove_pidfiles_only_for_recorded_pids(self):
        """A pidfile naming a PID we recorded is removed; others are kept."""
        SERVER_PIDFILE.write_text("1", encoding="utf-8")
        PORTAL_PIDFILE.write_text("2", encoding="utf-8")
        self.addCleanup(lambda: SERVER_PIDFILE.unlink(missing_ok=True))
        self.addCleanup(lambda: PORTAL_PIDFILE.unlink(missing_ok=True))
        self.server.pids = {"server": 1}
        self.server._remove_pidfiles()
        self.assertFalse(SERVER_PIDFILE.exists())
        self.assertTrue(PORTAL_PIDFILE.exists())

    def test_stop_cleans_runtime_and_restores_pidfiles(self):
        """A full start+stop with fakes removes temp state and pidfiles."""
        SERVER_PIDFILE.write_text("15\n", encoding="utf-8")
        self.addCleanup(lambda: SERVER_PIDFILE.unlink(missing_ok=True))
        self._patch_steps(ready=True)
        self.server.start()
        self.assertTrue(self.server.ready)
        self.server.stop()
        self.assertFalse(self.runtime.root_dir.exists())
        self.assertEqual(SERVER_PIDFILE.read_text(encoding="utf-8"), "15\n")


class PortAllocationTests(unittest.TestCase):
    """Repeated dynamic-port discovery must never collide."""

    def test_allocate_ports_are_distinct_per_call(self):
        a = fixtures.allocate_ports(5)
        b = fixtures.allocate_ports(5)
        self.assertEqual(len(a), 5)
        self.assertEqual(len(set(a)), 5)
        self.assertEqual(len(set(b)), 5)
        self.assertFalse(set(a) & set(b), "two allocations share a port")

    def test_repeated_runtimes_are_fully_isolated(self):
        first = fixtures.create_runtime(prefix="elosern-iso1-")
        second = fixtures.create_runtime(prefix="elosern-iso2-")
        self.addCleanup(first.cleanup)
        self.addCleanup(second.cleanup)
        # Ports are allocated lazily (only under the harness startup lock),
        # so materialize them before comparing.
        first.allocate_ports()
        second.allocate_ports()
        self.assertFalse(set(first.ports) & set(second.ports))
        self.assertNotEqual(first.database_path, second.database_path)
        self.assertNotEqual(first.log_dir, second.log_dir)

    def test_create_runtime_defers_port_allocation(self):
        """A fresh runtime holds NO ports until ``allocate_ports`` runs.

        Port allocation is the only runner-shared startup step and must be
        able to happen under the harness startup lock; eager allocation at
        construction reintroduced the release-then-bind race for every
        caller that creates a runtime before starting the server.
        """
        runtime = fixtures.create_runtime(prefix="elosern-defer-")
        self.addCleanup(runtime.cleanup)
        self.assertIsNone(runtime.ports)
        for key in (
            "ELOSERN_BROWSER_TELNET_PORT",
            "ELOSERN_BROWSER_HTTP_PORT",
            "ELOSERN_BROWSER_WS_PORT",
            "ELOSERN_BROWSER_AMP_PORT",
        ):
            self.assertNotIn(key, runtime.env)
        runtime.allocate_ports()
        self.assertEqual(len(runtime.ports), fixtures.PORT_COUNT)
        self.assertEqual(
            runtime.env["ELOSERN_BROWSER_HTTP_PORT"],
            str(runtime.ports[fixtures.HTTP_PORT]),
        )
        # Idempotent: a second call keeps the same ports.
        before = list(runtime.ports)
        runtime.allocate_ports()
        self.assertEqual(runtime.ports, before)


class StartupLockTests(unittest.TestCase):
    """The runner-local startup lock's exclusion and wedge behavior."""

    def setUp(self):
        from . import harness

        self.harness = harness
        holder = tempfile.TemporaryDirectory(prefix="elosern-lock-")
        self.addCleanup(holder.cleanup)
        self.lock_path = Path(holder.name) / "startup.lock"

    def test_lock_serializes_holders(self):
        """A second acquirer cannot hold the lock while the first does."""
        from .harness import _StartupLock

        first = _StartupLock(self.lock_path)
        first.acquire()
        self.addCleanup(first.release)
        second = _StartupLock(self.lock_path, poll=0.01)
        # Non-blocking attempt: the kernel must refuse while held.
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        self.addCleanup(lambda: os.close(fd))
        with self.assertRaises(BlockingIOError):
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        first.release()
        # After release the SAME description acquires immediately.
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        second.acquire()
        second.release()

    def test_dead_owner_lock_is_reacquirable(self):
        """flock semantics: a killed holder cannot wedge the runner."""
        from .harness import _StartupLock

        child = subprocess.Popen(
            [
                "python3",
                "-c",
                "import fcntl, os, sys, time;"
                "fd = os.open(sys.argv[1], os.O_CREAT | os.O_RDWR, 0o644);"
                "fcntl.flock(fd, fcntl.LOCK_EX);"
                "print('held', flush=True); time.sleep(60)",
                str(self.lock_path),
            ],
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual("held", child.stdout.readline().strip())
            child.kill()
            child.wait(timeout=10)
        finally:
            if child.poll() is None:
                child.kill()
        # The kernel dropped the dead owner's flock; reacquiring must not
        # need any stale-break logic and must not wait.
        lock = _StartupLock(self.lock_path)
        lock.acquire()
        lock.release()

    def test_wedged_holder_times_out_with_named_cause(self):
        """Waiting past the bounded critical section fails, never cuts in."""
        from .harness import _StartupLock

        first = _StartupLock(self.lock_path)
        first.acquire()
        self.addCleanup(first.release)
        second = _StartupLock(self.lock_path, wait_timeout=0.2, poll=0.01)
        with self.assertRaises(HarnessError) as caught:
            second.acquire()
        self.assertIn("bounded critical section", str(caught.exception))


class _RecordingLock:
    """Stand-in for ``_StartupLock`` recording whether it is held."""

    def __init__(self) -> None:
        self.held = False
        self.acquisitions = 0

    def __enter__(self) -> "_RecordingLock":
        self.held = True
        self.acquisitions += 1
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.held = False


class StartupSerializationTests(unittest.TestCase):
    """The port-critical startup section must run under the startup lock."""

    def _patch_offline_steps(self):
        for target, result in (
            ("run_migrate", _ok_result("migrate")),
            ("run_seed", _ok_result("seed")),
        ):
            patcher = mock.patch(
                f"web.tests.browser.harness.fixtures.{target}",
                return_value=result,
            )
            patcher.start()
            self.addCleanup(patcher.stop)
        poll = mock.patch(
            "web.tests.browser.harness.fixtures.webclient_ready",
            return_value=True,
        )
        poll.start()
        self.addCleanup(poll.stop)

    def test_boot_and_allocation_run_under_the_startup_lock(self):
        """Ports are allocated and the launcher boots inside the lock span.

        The release-then-bind race is only closed when BOTH ends happen while
        the runner-local lock is held; a boot observed outside the span (or a
        runtime with ports already allocated before the span) means the race
        is back.
        """
        lock = _RecordingLock()
        with mock.patch(
            "web.tests.browser.harness._startup_lock", return_value=lock
        ):
            runtime = fixtures.create_runtime(prefix="elosern-serial-")
            observed: dict[str, object] = {}

            class LockAwareRunner(FakeRunner):
                def __call__(self, runtime, *args, **kwargs):
                    if args and args[0] == "start":
                        observed["held"] = lock.held
                        observed["ports"] = runtime.ports
                    return super().__call__(runtime, *args, **kwargs)

            server = ManagedServer(runtime=runtime, runner=LockAwareRunner())
            self._patch_offline_steps()
            self.addCleanup(server.stop)
            server.start()
        self.assertTrue(observed.get("held"), "boot ran outside the lock")
        self.assertIsNotNone(observed.get("ports"), "ports unallocated at boot")
        self.assertEqual(lock.acquisitions, 1)

    def test_foreign_portal_boot_fails_fast_and_retries(self):
        """``already running`` from a cleared runtime retries with fresh ports.

        The launcher exits 0 after joining a foreign portal on a released AMP
        port; without the marker check the harness waits out the whole
        readiness timeout and reports a misleading cause.
        """
        ready_calls = {"count": 0}

        def counting_ready(runtime, timeout=0):
            ready_calls["count"] += 1
            return True

        foreign_runner = FakeRunner()
        original = foreign_runner.__call__
        calls = {"count": 0}

        def flaky_foreign(runtime, *args, **kwargs):
            calls["count"] += 1
            if args and args[0] == "start" and calls["count"] == 1:
                return subprocess.CompletedProcess(
                    ["start"],
                    0,
                    "Portal is already running as process 4214. Not restarted.\n"
                    "Server is already running as process 4222.\n",
                    "",
                )
            return original(runtime, *args, **kwargs)

        poll = mock.patch(
            "web.tests.browser.harness.fixtures.webclient_ready",
            side_effect=counting_ready,
        )
        migrate = mock.patch(
            "web.tests.browser.harness.fixtures.run_migrate",
            return_value=_ok_result("migrate"),
        )
        seed = mock.patch(
            "web.tests.browser.harness.fixtures.run_seed",
            return_value=_ok_result("seed"),
        )
        lock = mock.patch(
            "web.tests.browser.harness._startup_lock",
            side_effect=lambda: _RecordingLock(),
        )
        for patcher in (migrate, seed, poll, lock):
            patcher.start()
            self.addCleanup(patcher.stop)

        first_runtime = fixtures.create_runtime(prefix="elosern-foreign-")
        first_runtime.env["ELOSERN_BROWSER_CREATION"] = "1"
        server = ManagedServer(runtime=first_runtime, runner=flaky_foreign)
        self.addCleanup(server.stop)
        try:
            server.start()
        except HarnessError:
            self.fail("foreign-portal boot must be retried, not raised")
        self.assertTrue(server.started)
        # The foreign boot never polled readiness; only the retry did.
        self.assertEqual(ready_calls["count"], 1)
        self.assertIsNot(server.runtime, first_runtime)
        self.assertFalse(first_runtime.root_dir.exists())
        self.assertEqual(
            server.runtime.env["ELOSERN_BROWSER_CREATION"], "1"
        )


class RealServerBootTest(unittest.TestCase):
    """One genuine end-to-end boot of the managed Evennia server."""

    def test_real_server_boots_and_cleans_up(self):
        server = ManagedServer()
        try:
            server.start()
            self.assertTrue(server.ready)
            self.assertTrue(server.pids.get("portal"), "portal pid recorded")
            self.assertTrue(server.pids.get("server"), "server pid recorded")
            self.assertTrue(fixtures.webclient_ready(server.runtime, timeout=30))
        finally:
            server.stop()
        self.assertFalse(server.runtime.root_dir.exists())
        for pid in server.pids.values():
            self.assertFalse(
                fixtures.process_is_alive(pid), "owned process left behind"
            )


if __name__ == "__main__":
    unittest.main()
