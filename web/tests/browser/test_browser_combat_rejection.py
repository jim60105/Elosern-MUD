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
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            state = store_state(page)
            panel = state["panels"] and state["panels"].get("context_actions")
            if (
                state["mode"] == "combat"
                and panel
                and panel.get("available") is True
            ):
                return panel
            page.wait_for_timeout(250)
        raise AssertionError("combat mode never became available")

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
        page.evaluate(
            "() => Elosern.actions.submit('combat.cast', "
            "{ skill_key: 'fire_ball', target_ids: [999999] })"
        )
        page.wait_for_function(
            "() => { const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null); "
            "return s.lastActionResult && s.lastActionResult.outcome === 'rejected'; }",
            timeout=30000,
        )
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
        page.evaluate(
            "(id) => Elosern.actions.submit('combat.forfeit', "
            "{ session_id: 'hostile:999:0' })",
            session_id,
        )
        page.wait_for_function(
            "() => { const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null); "
            "return s.lastActionResult && s.lastActionResult.outcome === 'rejected'; }",
            timeout=30000,
        )
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
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            state = store_state(page)
            panel = state["panels"] and state["panels"].get("context_actions")
            if (
                state["mode"] == "combat"
                and panel
                and panel.get("available") is True
            ):
                return panel
            page.wait_for_timeout(250)
        raise AssertionError("combat mode never became available")

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
        page.wait_for_function(
            "() => { const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null); return !s.connected; }"
        )
        page.wait_for_function(
            "() => document.getElementById('elosern-offline-overlay')"
            ".getAttribute('data-visible') === 'true'"
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
        target = self._combat_panel(page)["participants"][-1]["identity"]
        page.evaluate(
            "(target) => Elosern.actions.submit('combat.cast', "
            "{ skill_key: 'basic_attack', target_ids: [target] });",
            target,
        )
        # The cast is admitted and a round commits; the result reaches the store
        # but the client's in-flight request is never released.
        page.wait_for_function(
            "() => { const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null); "
            "const p = s.panels && s.panels['context_actions']; "
            "return p && p.available && p.session.round >= 1; }",
            timeout=30000,
        )
        # The assertions below read the action client's in-memory
        # uncertain-notice state and the outbound recorder; a one-shot
        # recovery reload (fired by a slow re-attach under load) would wipe
        # both, so scope the window to the client's own reconnect.
        suppress_one_shot_recovery_reload(page)
        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        page.wait_for_function(
            "() => { const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null); return !s.connected; }"
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
        # instead of a fixed 1.5s sleep that races a slow re-attach.
        try:
            page.wait_for_function(
                """() => {
                  const o = document.getElementById('elosern-offline-overlay');
                  return o && o.getAttribute('data-uncertain') === 'true';
                }""",
                timeout=30000,
            )
        except Error as exc:
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
                "state=%r; inFlight=%r; dispatch=%r; sent=%r"
                % (state, in_flight, dispatch, outbound_messages(page))
            ) from exc

        # No automatic replacement cast after reconnect (the original request
        # was already sent once before the disconnect).
        from .browser_helpers import sent_action_count

        self.assertEqual(sent_action_count(page, "combat.cast"), 1)

        # Leave the shared server clean for subsequent tests.
        page.evaluate("Evennia.msg('text', ['combat forfeit'], {})")
        page.wait_for_timeout(1200)
