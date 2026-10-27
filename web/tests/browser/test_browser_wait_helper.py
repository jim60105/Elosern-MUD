"""Focused unit tests for the shared deterministic-state wait helper.

These tests exercise ``wait_for_store_state``'s required failure modes — a
``None`` store read (mid-reload), the dual store+DOM gate, and the timeout
diagnostic fields — without booting a managed Evennia server or a real
browser, by driving a fake Playwright page whose ``evaluate`` returns a
scripted sequence of store views and DOM-readiness results.
"""

from __future__ import annotations

import json
import time
import unittest

from playwright.sync_api import Error
from tools.spec_traceability import covers_requirement

from .browser_helpers import submit_until_admitted, wait_for_store_state

_REQUIREMENT_ID = "webclient-browser-verification::browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline"


class _FakeLocator:
    """Minimal stand-in for ``page.locator(sel)``."""

    def __init__(self, page: "_FakePage", selector: str) -> None:
        self._page = page
        self.selector = selector

    def focus(self, timeout: int | None = None) -> None:
        self._page.focused = True

    def wait_for(self, state: str | None = None, timeout: int | None = None) -> None:
        return None

    def click(self, timeout: int | None = None) -> None:
        self._page.clicked = True

    def inner_text(self) -> str:
        return self._page.inner_text

    def get_attribute(self, name: str) -> str | None:
        return self._page.attrs.get(name)


class _FakePage:
    """Scripted fake of a Playwright ``Page`` for the store-state gate.

    ``store_queue`` is consumed in order (each entry is the next store view,
    possibly ``None`` to model a mid-reload). ``dom_queue`` (or the scalar
    ``dom_result``) supplies the DOM-readiness predicate results. ``active_element``
    is what the ``document.activeElement`` diagnostic returns.

    The bridge read is served as a JSON string (``json.dumps``), mirroring the
    real page contract: the helper's store read evaluates
    ``JSON.stringify(store.view)`` in-page and parses it in Python.
    """

    def __init__(self) -> None:
        self.store_queue: list[dict | None] = []
        self._store_index = 0
        self.dom_queue: list[bool] = []
        self.dom_result = False
        self.dom_eval_error: Error | None = None
        self.active_element = "body"
        self.focused = False
        self.clicked = False
        self.inner_text = ""
        self.attrs: dict[str, str] = {}
        self.predicate_calls = 0

    def _next_store_view(self) -> dict | None:
        if self._store_index < len(self.store_queue):
            value = self.store_queue[self._store_index]
            self._store_index += 1
            return value
        return self.store_queue[-1] if self.store_queue else None

    def _next_dom_result(self, arg) -> bool | dict | None:
        if arg is None:
            # In-loop DOM-readiness predicate (no argument).
            if self.dom_eval_error is not None:
                raise self.dom_eval_error
            if self.dom_queue:
                return self.dom_queue.pop(0)
            return self.dom_result
        # Post-loop DOM diagnostic (the selector is passed as the argument).
        return {"connected": True, "visible": True, "enabled": None}

    def evaluate(self, expression: str, arg=None):
        if "__elosernBridge" in expression:
            value = self._next_store_view()
            return json.dumps(value) if value is not None else None
        if "activeElement" in expression:
            return self.active_element
        return self._next_dom_result(arg)

    def wait_for_timeout(self, ms: int) -> None:
        time.sleep(min(ms, 50) / 1000)

    def locator(self, selector: str) -> _FakeLocator:
        return _FakeLocator(self, selector)


def _active_shell(state: dict) -> bool:
    return (
        bool(state.get("connected"))
        and state.get("phase") == "active"
        and bool(state.get("epoch"))
        and state.get("mutationsLocked") is not True
        and bool(state.get("mode"))
    )


class WaitForStoreStateTest(unittest.TestCase):
    """Unit tests for the shared ``wait_for_store_state`` gate."""

    def _shell_ready_state(self) -> dict:
        return {
            "connected": True,
            "phase": "active",
            "epoch": 7,
            "mutationsLocked": False,
            "mode": "exploration",
        }

    @covers_requirement("webclient-browser-verification::browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline")
    def test_store_gate_returns_when_predicate_true(self) -> None:
        page = _FakePage()
        page.store_queue = [self._shell_ready_state()]
        wait_for_store_state(page, _active_shell, timeout=300)

    @covers_requirement("webclient-browser-verification::browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline")
    def test_none_read_tolerated_and_predicate_not_invoked_on_none(self) -> None:
        page = _FakePage()
        calls = {"n": 0}

        def counting_predicate(state: dict) -> bool:
            calls["n"] += 1
            return _active_shell(state)

        page.store_queue = [None, self._shell_ready_state()]
        wait_for_store_state(page, counting_predicate, timeout=300)
        self.assertEqual(calls["n"], 1)

    def test_both_gates_must_hold(self) -> None:
        page = _FakePage()
        page.store_queue = [self._shell_ready_state()]
        page.dom_queue = [False, False, True]
        dom = {
            "selector": '[data-testid="command-line"]',
            "predicate": "() => !!(document.querySelector('[data-testid=\"command-line\"]') && true)",
            "description": "command line mounted",
        }
        wait_for_store_state(page, _active_shell, dom_readiness=dom, timeout=300)

    @covers_requirement("webclient-browser-verification::browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline")
    def test_timeout_diagnostic_carries_required_fields(self) -> None:
        page = _FakePage()
        page.store_queue = [{"connected": True, "phase": "detached"}]
        dom = {
            "selector": '[data-testid="command-line"]',
            "predicate": "() => false",
            "description": "command line mounted",
        }
        with self.assertRaises(AssertionError) as ctx:
            wait_for_store_state(page, lambda s: s.get("phase") == "active", dom_readiness=dom, timeout=300)
        message = str(ctx.exception)
        self.assertIn("last_state=", message)
        self.assertIn("none_observed=", message)
        self.assertIn("dom_readiness=", message)
        self.assertIn("activeElement=", message)

    @covers_requirement("webclient-browser-verification::browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline")
    def test_none_read_flagged_in_timeout(self) -> None:
        page = _FakePage()
        page.store_queue = [None, {"connected": True, "phase": "detached"}]
        with self.assertRaises(AssertionError) as ctx:
            wait_for_store_state(page, lambda s: s.get("phase") == "active", timeout=300)
        self.assertIn("none_observed=True", str(ctx.exception))

    @covers_requirement("webclient-browser-verification::browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline")
    def test_non_navigation_dom_error_surfaced_in_diagnostic(self) -> None:
        page = _FakePage()
        page.store_queue = [{"connected": True, "phase": "active"}]
        page.dom_eval_error = Error("querySelector returned null (selector error)")
        dom = {
            "selector": '#missing-el',
            "predicate": "() => document.querySelector('#missing-el').focus()",
            "description": "missing element",
        }
        with self.assertRaises(AssertionError) as ctx:
            wait_for_store_state(page, lambda s: True, dom_readiness=dom, timeout=300)
        message = str(ctx.exception)
        self.assertIn("DOM predicate evaluate error", message)


class _ScriptedSubmitPage:
    """Scripted page for ``submit_until_admitted``'s three reads.

    ``evaluate`` serves the outbound envelope list, the recorded results and the
    committed store view (as JSON, like the real bridge read). Activation itself
    is the test's own callable, so each case decides how many envelopes one
    activation sends and what the server answers.
    """

    def __init__(self) -> None:
        self.sent: list[list] = []
        self.results: list[dict] = []
        self.state: dict = {
            "connected": True,
            "phase": "active",
            "mutationsLocked": False,
            "revision": 9,
            "recovery": {"status": "idle"},
            "dispatch": {"inFlight": None, "uncertain": False},
            "lastActionResult": {"requestId": "session:0", "presentationRevision": 9},
        }

    def evaluate(self, expression: str, arg=None):
        if "window.__elosernSent" in expression:
            return self.sent
        if "window.__elosernResults" in expression:
            return list(self.results)
        if "__elosernBridge" in expression:
            return json.dumps(self.state)
        return None

    def wait_for_timeout(self, ms: int) -> None:
        time.sleep(min(ms, 5) / 1000)


def _scripted_activation(page: _ScriptedSubmitPage, outcomes: list[str], *, per_activation: int = 1):
    """Return an ``activate`` callable answering ``outcomes`` in order."""
    calls = {"n": 0}

    def activate() -> None:
        calls["n"] += 1
        outcome = outcomes[calls["n"] - 1]
        for index in range(per_activation):
            request_id = "session:%d:%d" % (calls["n"], index)
            page.sent.append(
                [
                    "ui_action",
                    [{"action_id": "explore.dialogue_leave", "request_id": request_id}],
                    {},
                ]
            )
            page.results.append(
                {
                    "protocolVersion": 1,
                    "requestId": request_id,
                    "outcome": outcome,
                    "code": outcome,
                    "presentationRevision": 9,
                }
            )

    return activate


class SubmitUntilAdmittedTest(unittest.TestCase):
    """Unit tests for the bounded stale re-activation submit helper."""

    def test_stale_activation_is_repeated_once_and_admitted(self) -> None:
        page = _ScriptedSubmitPage()
        activate = _scripted_activation(page, ["stale", "success"])
        result = submit_until_admitted(
            page, activate, action_id="explore.dialogue_leave", timeout=1000
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(len(page.sent), 2, "the stale activation was repeated once")

    def test_three_consecutive_stale_answers_fail_the_journey(self) -> None:
        page = _ScriptedSubmitPage()
        activate = _scripted_activation(page, ["stale", "stale", "stale"])
        with self.assertRaises(AssertionError) as ctx:
            submit_until_admitted(
                page, activate, action_id="explore.dialogue_leave", timeout=1000
            )
        self.assertIn("all answered stale", str(ctx.exception))
        self.assertEqual(len(page.sent), 3, "the retry is bounded to three activations")

    def test_an_unrelated_result_never_stands_in_for_the_activation(self) -> None:
        page = _ScriptedSubmitPage()
        # A reading acknowledgement commits its own result while the leave is in
        # flight; the newest committed result is then not the leave's answer.
        page.results.append(
            {"requestId": "reading:1", "outcome": "stale", "presentationRevision": 9}
        )

        def activate() -> None:
            page.sent.append(
                [
                    "ui_action",
                    [
                        {
                            "action_id": "explore.dialogue_leave",
                            "request_id": "session:1",
                        }
                    ],
                    {},
                ]
            )
            page.results.append(
                {
                    "requestId": "session:1",
                    "outcome": "success",
                    "presentationRevision": 9,
                }
            )

        result = submit_until_admitted(
            page, activate, action_id="explore.dialogue_leave", timeout=1000
        )
        self.assertEqual(result["requestId"], "session:1")
        self.assertEqual(len(page.sent), 1)

    def test_one_activation_that_dispatches_twice_fails(self) -> None:
        page = _ScriptedSubmitPage()
        activate = _scripted_activation(page, ["success", "success"], per_activation=2)
        with self.assertRaises(AssertionError) as ctx:
            submit_until_admitted(
                page, activate, action_id="explore.dialogue_leave", timeout=1000
            )
        self.assertIn("exactly once", str(ctx.exception))

    def test_a_domain_rejection_returns_without_reactivation(self) -> None:
        page = _ScriptedSubmitPage()
        activate = _scripted_activation(page, ["refused"])
        result = submit_until_admitted(
            page, activate, action_id="explore.dialogue_leave", timeout=1000
        )
        self.assertEqual(result["outcome"], "refused")
        self.assertEqual(len(page.sent), 1, "only stale answers are retried")


if __name__ == "__main__":
    unittest.main()
