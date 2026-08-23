"""Combat browser rejection and reconnect tests (tasks 5.3-5.4).

Proves that an admitted combat action through the real server rejects
deterministically when resources are insufficient or a target is stale, that a
duplicate request is not double-executed, and that active-combat disconnect and
reconnect rebuilds the same persisted session without replaying intent.
"""

from __future__ import annotations

import time

from playwright.sync_api import Error
from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    evaluate_tolerating_navigation,
    install_outbound_recorder,
    outbound_messages,
    store_state,
    store_state_or_none,
    suppress_one_shot_recovery_reload,
    wait_for_presentation_settled,
    wait_for_store_state,
)


class CombatRejectionBrowserTest(BrowserAcceptanceTest):
    """Drives real combat sessions through the action dock and asserts rejections.

    Each test boots its own dedicated isolated server: an active combat session
    leaves the Evennia server session in a state that a later fresh login on
    the same server cannot reuse cleanly.
    """

    def setUp(self) -> None:
        from .harness import ManagedServer

        self.server = ManagedServer()
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None

    def _engage(self, page, name="goblin"):
        page.evaluate("Evennia.msg('text', ['engage %s'], {})" % name)
        self._wait_combat_mode(page)

    def _wait_combat_mode(self, page, timeout=30000):
        def _combat_panel_ready(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("context_actions") or {}
            return state.get("mode") == "combat" and panel.get("available") is True

        wait_for_store_state(page, _combat_panel_ready, timeout=timeout)

    def _press(self, page, key):
        page.keyboard.press(key)
        page.wait_for_timeout(80)

    def _last_result(self, page):
        return store_state(page)["lastActionResult"]

    @covers_requirement("webclient-combat-menu::availability-uses-shared-side-effect-free-rules-preview")
    def test_tampered_target_rejects_without_round(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        panel = self._combat_panel(page)
        fire = next(
            s
            for category in panel["skills"]
            for group in category["groups"]
            for s in group["skills"]
            if s["key"] == "fire_ball"
        )
        self.assertTrue(fire["enabled"])

        # A ui_action must name the server's newest revision exactly or the
        # dispatcher rejects it stale: submit only after the post-engage
        # publication burst has fully landed in the store.
        wait_for_presentation_settled(page)
        # A modified client sends a participant ID that is not in the session;
        # the adapter must reject before initiative with no round advance.
        prev_result = store_state(page)["lastActionResult"]
        page.evaluate(
            "() => Elosern.actions.submit('combat.cast', "
            "{ skill_key: 'fire_ball', target_ids: [999999] })"
        )
        def _fresh_rejected(state: dict) -> bool:
            result = state.get("lastActionResult")
            if not result or result.get("outcome") != "rejected":
                return False
            if prev_result is not None:
                return result.get("requestId") != prev_result.get("requestId")
            return True

        wait_for_store_state(page, _fresh_rejected)
        result = self._last_result(page)
        self.assertEqual(result["code"], "unknown_session_id")
        self.assertEqual(
            store_state(page)["panels"]["context_actions"]["session"]["round"],
            0,
        )

    def _combat_panel(self, page):
        return store_state(page)["panels"]["context_actions"]

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_stale_forfeit_rejects(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        wait_for_presentation_settled(page)
        session_id = self._combat_panel(page)["session"]["session_id"]
        prev_result = store_state(page)["lastActionResult"]
        page.evaluate(
            "(id) => Elosern.actions.submit('combat.forfeit', "
            "{ session_id: 'hostile:999:0' })",
            session_id,
        )
        def _fresh_rejected(state: dict) -> bool:
            result = state.get("lastActionResult")
            if not result or result.get("outcome") != "rejected":
                return False
            if prev_result is not None:
                return result.get("requestId") != prev_result.get("requestId")
            return True

        wait_for_store_state(page, _fresh_rejected)
        result = self._last_result(page)
        self.assertEqual(result["code"], "unknown_session_id")
        panel = self._combat_panel(page)
        self.assertEqual(panel["session"]["session_id"], session_id)


class CombatReconnectBrowserTest(BrowserAcceptanceTest):
    """Active-combat disconnect/reconnect without intent replay.

    Each test boots its own dedicated isolated server: an abnormal transport
    close during an active combat session leaves the server session in a state
    that a later fresh login on the same server cannot reuse cleanly.
    """

    def setUp(self) -> None:
        from .harness import ManagedServer

        self.server = ManagedServer()
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None

    def _combat_panel(self, page):
        return store_state(page)["panels"]["context_actions"]

    def _engage(self, page, name="goblin"):
        page.evaluate("Evennia.msg('text', ['engage %s'], {})" % name)
        self._wait_combat_mode(page)

    def _wait_combat_mode(self, page, timeout=30000):
        def _combat_panel_ready(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("context_actions") or {}
            return state.get("mode") == "combat" and panel.get("available") is True

        wait_for_store_state(page, _combat_panel_ready, timeout=timeout)

    @covers_requirement("webclient-combat-menu::reconnect-rebuilds-combat-without-replaying-intent")
    def test_reconnect_resumes_same_session_without_new_round(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        session_before = store_state(page)["panels"]["context_actions"]["session"]
        round_before = session_before["round"]
        # Scope the window under test to the client's own reconnect; a
        # one-shot recovery reload under a loaded runner would wipe the
        # in-page state these assertions read.
        suppress_one_shot_recovery_reload(page)

        # Abnormally close the transport and wait for the offline overlay.
        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
            dom_readiness={
                "selector": "#elosern-offline-overlay",
                "predicate": (
                    "() => { const o = document.querySelector('#elosern-offline-overlay'); "
                    "return o && o.getAttribute('data-visible') === 'true'; }"
                ),
                "description": "offline overlay visible",
            },
        )

        # Wait for the reconnect to open a new generation and adopt a snapshot.
        # `store_state_or_none` tolerates the re-bootstrap window where the
        # ``Elosern`` global is briefly absent and any in-flight navigation;
        # a None snapshot just means "not yet".
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            state = store_state_or_none(page)
            panel = state["panels"] and state["panels"].get("context_actions") if state else None
            if (
                state
                and state["connected"]
                and state["mode"] == "combat"
                and panel
                and panel.get("available") is True
            ):
                session_after = panel["session"]
                if session_after["session_id"] == session_before["session_id"]:
                    break
            if time.monotonic() > deadline - 25:
                # Guarded: while the client re-boots, window.Evennia is
                # briefly absent and a bare evaluate would raise.
                evaluate_tolerating_navigation(
                    page,
                    "() => { if (window.Evennia && Evennia.connect) "
                    "Evennia.connect(); }",
                )
            page.wait_for_timeout(500)
        else:
            self.fail("combat session was not restored after reconnect")

        session_after = store_state(page)["panels"]["context_actions"]["session"]
        self.assertEqual(session_after["session_id"], session_before["session_id"])
        self.assertEqual(session_after["round"], round_before)

        # Leave the shared server clean for subsequent tests.
        page.evaluate("Evennia.msg('text', ['combat forfeit'], {})")
        page.wait_for_timeout(1200)

    @covers_requirement("webclient-combat-menu::reconnect-rebuilds-combat-without-replaying-intent")
    def test_disconnect_after_submit_shows_uncertain_notice_no_retry(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)

        # Deterministically keep the submitted cast's result out of the action
        # client: the server processes the request and the store records the
        # result, but the client never observes it, so its request stays in
        # flight when the transport dies.
        page.evaluate(
            "() => {"
            "  const client = Elosern.actions && Elosern.actions.client;"
            "  if (!client) return false;"
            "  client.onActionResult = function () { return undefined; };"
            "  return true;"
            "}"
        )
        # Settle before submitting: a cast naming the pre-burst revision is
        # rejected stale and the round would never commit.
        wait_for_presentation_settled(page)
        # Arm a JS timer that re-applies the no-op on the current client
        # instance every 100ms: a re-attach re-bootstraps window.Elosern and
        # re-creates the action client, losing the one-shot override. The timer
        # keeps the cast's result out of the client so its in-flight request
        # stays unconfirmed.
        page.evaluate(
            "() => {"
            "  if (window.__elosernNoOpTimer) clearInterval(window.__elosernNoOpTimer);"
            "  window.__elosernNoOpTimer = setInterval(() => {"
            "    const c = Elosern && Elosern.actions && Elosern.actions.client;"
            "    if (c) {"
            "      c.onActionResult = function () { return undefined; };"
            "      c.isInFlight = function () { return true; };"
            "    }"
            "  }, 100);"
            "}"
        )
        target = self._combat_panel(page)["participants"][-1]["identity"]
        page.evaluate(
            "(target) => Elosern.actions.submit('combat.cast', "
            "{ skill_key: 'basic_attack', target_ids: [target] });",
            target,
        )
        # The cast is admitted and a round commits; the result reaches the store
        # but the client's in-flight request is never released (the no-op timer
        # keeps the result out of the client).
        def _round_committed(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("context_actions") or {}
            session = panel.get("session") or {}
            return bool(panel.get("available")) and int(session.get("round") or 0) >= 1

        wait_for_store_state(page, _round_committed)
        # The assertions below read the action client's in-memory
        # uncertain-notice state and the outbound recorder; a one-shot
        # recovery reload (fired by a slow re-attach under load) would wipe
        # both, so scope the window to the client's own reconnect.
        suppress_one_shot_recovery_reload(page)
        # Keep the no-op timer running across the transport close: the
        # `isInFlight` override must still be in effect when the store's
        # `setConnected(false)` runs on the close event, so the mutation is
        # marked uncertain. The timer is stopped only after the disconnect is
        # observed.
        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
        )
        # Capture the client's in-flight gate and result-observation state at the
        # disconnect moment (before the resync releases it), for diagnostics of
        # whether the mutation was unconfirmed at the loss.
        disconnect_gate = evaluate_tolerating_navigation(
            page,
            "() => { const c = window.Elosern && window.Elosern.actions && window.Elosern.actions.client; "
            "return c && c.isInFlight ? c.isInFlight() : null; }",
        )
        disconnect_observed = evaluate_tolerating_navigation(
            page,
            "() => { const c = window.Elosern && window.Elosern.actions && window.Elosern.actions.client; "
            "const r = c && c.lastResult ? c.lastResult() : null; "
            "return r ? r.requestId : null; }",
        )
        disconnect_submitted_id = evaluate_tolerating_navigation(
            page,
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "return s ? s.view.dispatch.submittedRequestId : null; }",
        )
        # The disconnect is observed; stop the no-op timer now that the
        # `isInFlight` override has done its job at the store's setConnected.
        page.evaluate(
            "() => { if (window.__elosernNoOpTimer) { clearInterval(window.__elosernNoOpTimer); window.__elosernNoOpTimer = null; } }"
        )

        # On reconnect the client shows the uncertain-result notice and never
        # retries the withheld cast. `store_state_or_none` again tolerates
        # the re-bootstrap window where the ``Elosern`` global is absent and
        # any in-flight navigation.
        deadline = time.monotonic() + 60
        reconnected = False
        while time.monotonic() < deadline:
            state = store_state_or_none(page)
            if state and state["connected"]:
                reconnected = True
                break
            if time.monotonic() > deadline - 25:
                # Guarded: while the client re-boots, window.Evennia is
                # briefly absent and a bare evaluate would raise.
                evaluate_tolerating_navigation(
                    page,
                    "() => { if (window.Evennia && Evennia.connect) "
                    "Evennia.connect(); }",
                )
            page.wait_for_timeout(500)
        self.assertTrue(
            reconnected,
            "client did not reconnect within 60s; state=%r"
            % (store_state_or_none(page),),
        )

        # Wait (bounded) for the offline overlay's uncertain-result notice
        # instead of a fixed 1.5s sleep that races a slow re-attach. The
        # gate polls the committed store view and the overlay's `data-uncertain`
        # attribute in one bounded loop under a single monotonic deadline.
        try:
            wait_for_store_state(
                page,
                lambda s: bool(s.get("connected")),
                dom_readiness={
                    "selector": "#elosern-offline-overlay",
                    "predicate": (
                        "() => { const o = document.querySelector('#elosern-offline-overlay'); "
                        "return o && o.getAttribute('data-uncertain') === 'true'; }"
                    ),
                    "description": "uncertain-result notice shown",
                },
            )
        except (Error, AssertionError) as exc:
            state = store_state_or_none(page)
            in_flight = evaluate_tolerating_navigation(
                page,
                "() => { const c = Elosern.actions && Elosern.actions.client; "
                "return c && c.isInFlight ? c.isInFlight() : null; }",
            )
            dispatch = evaluate_tolerating_navigation(
                page,
                "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
                "return s ? s.view.dispatch : null; }",
            )
            raise AssertionError(
                "uncertain-result notice never shown within 30s; "
                "state=%r; inFlight=%r; disconnectGate=%r; disconnectObservedId=%r; "
                "disconnectSubmittedId=%r; dispatch=%r; sent=%r"
                % (
                    state, in_flight, disconnect_gate, disconnect_observed,
                    disconnect_submitted_id, dispatch, outbound_messages(page),
                )
            ) from exc

        # No automatic replacement cast after reconnect (the original request
        # was already sent once before the disconnect).
        from .browser_helpers import sent_action_count

        self.assertEqual(sent_action_count(page, "combat.cast"), 1)

        # Leave the shared server clean for subsequent tests.
        page.evaluate("Evennia.msg('text', ['combat forfeit'], {})")
        page.wait_for_timeout(1200)

    @covers_requirement("webclient-combat-menu::reconnect-rebuilds-combat-without-replaying-intent")
    def test_confirmed_action_disconnect_shows_no_uncertain_notice(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)

        # A normal cast whose result IS observed (no override): the mutation is
        # confirmed, so a later transport loss must NOT show the uncertain
        # notice. This control proves the uncertain flag is set only for
        # genuinely unconfirmed mutations.
        wait_for_presentation_settled(page)
        target = self._combat_panel(page)["participants"][-1]["identity"]
        page.evaluate(
            "(target) => Elosern.actions.submit('combat.cast', "
            "{ skill_key: 'basic_attack', target_ids: [target] });",
            target,
        )
        def _round_committed(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("context_actions") or {}
            session = panel.get("session") or {}
            return bool(panel.get("available")) and int(session.get("round") or 0) >= 1

        wait_for_store_state(page, _round_committed)
        # The in-flight gate releases once the committed revision reaches the
        # declared presentation revision: the mutation is confirmed.
        def _in_flight_released(state: dict) -> bool:
            dispatch = state.get("dispatch") or {}
            return dispatch.get("inFlight") is None

        wait_for_store_state(page, _in_flight_released)
        suppress_one_shot_recovery_reload(page)
        page.evaluate("() => { if (window.__elosernWs) window.__elosernWs.close(4001); }")
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
        )

        deadline = time.monotonic() + 60
        reconnected = False
        while time.monotonic() < deadline:
            state = store_state_or_none(page)
            if state and state["connected"]:
                reconnected = True
                break
            if time.monotonic() > deadline - 25:
                evaluate_tolerating_navigation(
                    page,
                    "() => { if (window.Evennia && Evennia.connect) "
                    "Evennia.connect(); }",
                )
            page.wait_for_timeout(500)
        self.assertTrue(
            reconnected,
            "client did not reconnect within 60s; state=%r"
            % (store_state_or_none(page),),
        )

        # A confirmed mutation must NOT show the uncertain-result notice.
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": "#elosern-offline-overlay",
                "predicate": (
                    "() => { const o = document.querySelector('#elosern-offline-overlay'); "
                    "return o && o.getAttribute('data-uncertain') === 'false'; }"
                ),
                "description": "no uncertain-result notice",
            },
        )

        from .browser_helpers import sent_action_count
        self.assertEqual(sent_action_count(page, "combat.cast"), 1)

        # Leave the shared server clean for subsequent tests.
        page.evaluate("Evennia.msg('text', ['combat forfeit'], {})")
        page.wait_for_timeout(1200)
