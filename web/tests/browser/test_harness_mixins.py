"""Focused unit tests for the shared browser-harness teardown and wait helpers.

These tests exercise ``ManagedServerTearDownMixin.tearDown`` (with a ``Mock``
server) and ``wait_command_field_released`` — without booting a managed
Evennia server or a real browser — by driving the mixin from a minimal host
class and driving the wait gate against a fake Playwright page whose
``evaluate`` returns a scripted store view and DOM-readiness result (the same
fake-page pattern ``test_browser_wait_helper`` uses for ``wait_for_store_state``).
"""

from __future__ import annotations

import json
import time
import unittest
from unittest.mock import Mock

from .harness import ManagedServerTearDownMixin, wait_command_field_released


class _RecordingBase:
    """Plain-object base host recording that its teardown ran, in call order."""

    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def tearDown(self) -> None:
        self._calls.append("base")


class _MixinHost(ManagedServerTearDownMixin, _RecordingBase):
    """Minimal class under test: the mixin layered over the recording base."""


class _FakePage:
    """Scripted fake of a Playwright ``Page`` for the command-field gate.

    ``store_queue`` is consumed in order (each entry is the next store view);
    ``dom_result`` supplies the in-loop DOM-readiness predicate result. The
    bridge read is served as a JSON string, mirroring the real page contract.
    """

    def __init__(self) -> None:
        self.store_queue: list[dict | None] = []
        self._store_index = 0
        self.dom_result = False
        self.active_element = "action-dock"

    def _next_store_view(self) -> dict | None:
        if self._store_index < len(self.store_queue):
            value = self.store_queue[self._store_index]
            self._store_index += 1
            return value
        return self.store_queue[-1] if self.store_queue else None

    def evaluate(self, expression: str, arg=None):
        if "__elosernBridge" in expression:
            value = self._next_store_view()
            return json.dumps(value) if value is not None else None
        return self.dom_result

    def wait_for_timeout(self, ms: int) -> None:
        time.sleep(min(ms, 50) / 1000)


class ManagedServerTearDownMixinTest(unittest.TestCase):
    """Unit tests for the shared managed-server teardown mixin."""

    def test_tear_down_runs_base_then_stops_server(self) -> None:
        calls: list[str] = []
        host = _MixinHost(calls)
        server = Mock()
        # Record the stop into the same sequence as the base teardown.
        server.stop.side_effect = lambda: calls.append("stop")
        host.server = server
        host.tearDown()
        self.assertEqual(calls, ["base", "stop"])
        server.stop.assert_called_once_with()
        self.assertIsNone(host.server, "the server reference must be dropped")

    def test_tear_down_without_server_is_clean(self) -> None:
        calls: list[str] = []
        host = _MixinHost(calls)
        host.tearDown()
        self.assertEqual(calls, ["base"])

    def test_stop_helper_reports_stop_failures_without_hiding_them(self) -> None:
        host = _MixinHost([])
        server = Mock()
        server.stop.side_effect = RuntimeError("server failed to stop")
        host.server = server
        with self.assertRaises(RuntimeError):
            host.tearDown()
        self.assertIsNone(host.server, "the reference is dropped even on stop failure")

    def test_stop_snapshot_helper_drops_attribute(self) -> None:
        host = _MixinHost([])
        server = Mock()
        host.server = Mock()
        host._stop_managed_server(server)
        server.stop.assert_called_once_with()
        self.assertIsNone(host.server)


class WaitCommandFieldReleasedTest(unittest.TestCase):
    """Unit tests for the shared command-field-release gate."""

    def test_gate_passes_when_store_connected_and_dock_focused(self) -> None:
        page = _FakePage()
        page.store_queue = [{"connected": True}]
        page.dom_result = True
        wait_command_field_released(page, timeout=300)

    def test_gate_timeouts_when_store_never_connected(self) -> None:
        page = _FakePage()
        page.store_queue = [{"connected": False}]
        page.dom_result = True
        with self.assertRaises(AssertionError) as ctx:
            wait_command_field_released(page, timeout=300)
        self.assertIn("store-state gate not satisfied", str(ctx.exception))

    def test_gate_timeouts_when_dock_never_focused(self) -> None:
        page = _FakePage()
        page.store_queue = [{"connected": True}]
        page.dom_result = False
        with self.assertRaises(AssertionError) as ctx:
            wait_command_field_released(page, timeout=300)
        self.assertIn("command field released", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()