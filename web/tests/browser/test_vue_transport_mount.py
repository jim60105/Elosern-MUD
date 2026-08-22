"""C3 (webclient-vue-09-wire-transport-mount) managed-browser acceptance.

Proves the Vue app is live-capable over the evennia.js OOB transport against
a real managed Evennia server:

- the store adopts server snapshots/updates (``ui_snapshot``/``ui_update``);
- the C2 bridge dispatches ``ui_action`` (dispatch-only, one mutation in flight);
- the D10 vanilla text console is the degradation fallback (the Vite bundle
  blocked keeps the text path live);
- an incompatible OOB presentation (``ui_protocol_error`` / unsupported_version)
  locks the graphical controls while the text path keeps working;
- the production ``base.html`` default stays on the legacy shell (the
  production flip is C4).

The Vue branch is forced in the test config only (the ``?__vue=1`` review
fixture); the production ``base.html`` default is asserted unchanged here.
"""

from __future__ import annotations

import unittest

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    BROWSER_ACCOUNT,
    BROWSER_PASSWORD,
    install_outbound_recorder,
    sent_action_count,
)

VUE_QUERY = "?__vue=1"

CONSOLE = '[data-testid="text-console"]'
CONSOLE_LOG = '[data-testid="text-console-log"]'
CONSOLE_INPUT = '[data-testid="text-console-input"]'


class VueTransportMountBrowserTest(BrowserAcceptanceTest):
    """Live evennia.js OOB transport mounted in the test config only."""

    def _login(self, page) -> None:
        """Log in with the deterministic seeded account (bounded retry)."""
        login_url = f"{self.base_url}/auth/login/"
        for attempt in range(4):
            page.goto(login_url)
            try:
                page.wait_for_selector("#id_username", timeout=20000)
                break
            except Exception:
                if attempt == 3:
                    raise
                page.wait_for_timeout(1500)
        page.fill("#id_username", BROWSER_ACCOUNT)
        page.fill("#id_password", BROWSER_PASSWORD)
        page.click('input[type="submit"]')
        page.wait_for_load_state("networkidle")

    def open_vue_page(self, capture_responses: bool = False, block_bundle: bool = False):
        """Log in and open the WebClient Vue branch; optionally block the bundle."""
        page = self.new_page()
        responses: list = []
        if capture_responses:
            page.on("response", lambda response: responses.append(response))
        if block_bundle:
            # Degrade path: the Vite bundle cannot load; the D10 console must
            # keep round-tripping text.
            page.route("**/webclient/app/dist/**", lambda route: route.abort())
        self._login(page)
        page.goto(f"{self.webclient_url}{VUE_QUERY}")
        # If the bundle is blocked, the Vue app never mounts (main.js does not
        # run), so the console is NOT retired and drives the live transport.
        if block_bundle:
            page.wait_for_function(
                f"() => {{ const c = document.querySelector('{CONSOLE}');"
                " return c && c.getAttribute('data-status') === 'ready'; }",
                timeout=30000,
            )
        else:
            page.wait_for_function(
                "() => { const b = window.__elosernBridge; const s = b && b.store;"
                " return s && s.view.connected && s.view.phase === 'active'; }",
                timeout=45000,
            )
        return page, responses

    def _store_active(self, page) -> None:
        page.wait_for_function(
            "() => { const b = window.__elosernBridge; const s = b && b.store;"
            " return s && s.view.connected && s.view.phase === 'active' && !s.view.mutationsLocked; }",
            timeout=45000,
        )

    def test_live_transport_round_trips_and_store_adopts_snapshot(self):
        """C3 task 2.2: transport round-trip + store snapshot adoption."""
        page, _ = self.open_vue_page(capture_responses=True)
        self._store_active(page)
        install_outbound_recorder(page)
        # Send a text command through the C1 store (the single text path).
        page.evaluate("() => window.__elosernBridge.store.sendText('look')")
        # The command crosses the wire and the server's room text returns
        # through the D10 coordinator into the store's narrative.
        page.wait_for_function(
            "() => (window.__elosernSent || []).some("
            "(m) => m[0] === 'text' && m[1] && m[1][0] === 'look')",
            timeout=20000,
        )
        page.wait_for_function(
            "() => { const s = window.__elosernBridge.store;"
            " return s.narrative.some(l => l.kind === 'out' && l.text.length > 0); }",
            timeout=45000,
        )

    def test_dispatch_via_bridge(self):
        """C3 task 2.2: dispatch-only ui_action through the C2 bridge."""
        page, _ = self.open_vue_page()
        self._store_active(page)
        install_outbound_recorder(page)
        # Ensure the presentation revision is settled before dispatching so the
        # ui_action names the server's newest revision (stale guard).
        page.wait_for_function(
            "() => { const s = window.__elosernBridge.store; return s.view.revision; }",
            timeout=45000,
        )
        # The first submit dispatches a ui_action; the gate keeps exactly one
        # mutation in flight. Both submits run in ONE evaluate so no server
        # result/revision can land between them (the in-flight lock holds
        # synchronously).
        submits = page.evaluate(
            """() => {
              const bridge = window.__elosernBridge;
              const req = bridge.facade.actions.submit('explore.look', {}) || null;
              const dup = bridge.facade.actions.submit('explore.look', {}) || null;
              return { req, dup };
            }"""
        )
        self.assertIsNotNone(submits["req"], "the bridge submit must return a request id")
        self.assertIsNone(submits["dup"], "a second ui_action is gated while one is in flight")
        self.assertEqual(sent_action_count(page, "explore.look"), 1,
                         "exactly one ui_action may cross the wire (one mutation in flight)")
        # Release the in-flight lock once the presentation revision is
        # accepted (the store's releaseIfReady clears inFlight when the
        # committed revision reaches the declared presentation revision).
        page.evaluate(
            """(req) => {
             const s = window.__elosernBridge.store;
             window.__elosernBridge.facade.actions.handleActionResult({
               protocolVersion: 1, requestId: req, epoch: s.view.epoch,
               outcome: 'success', code: 'ok', message: '', presentationRevision: s.view.revision
             });
             return true; }""",
            submits["req"],
        )
        page.wait_for_function(
            "() => { const s = window.__elosernBridge.store;"
            " return !(s.view.dispatch.inFlight); }",
            timeout=20000,
        )

    @covers_requirement(
        "webclient-vue-application::degraded-text-remains-playable-alongside-the-vue-shell"
    )
    def test_bundle_blocked_keeps_text_playable(self):
        """C3 task 2.3: if the Vite bundle cannot load, text stays playable."""
        page, _ = self.open_vue_page(block_bundle=True)
        # The D10 console is NOT retired (the bundle never mounted the shell),
        # so it remains the authoritative text surface.
        self.assertTrue(page.locator(CONSOLE).is_visible(),
                        "the D10 text console stays visible when the Vue bundle loads")
        install_outbound_recorder(page)
        field = page.locator(CONSOLE_INPUT)
        field.fill("look")
        field.press("Enter")
        page.wait_for_function(
            "() => (window.__elosernSent || []).some("
            "(m) => m[0] === 'text' && m[1] && m[1][0] === 'look')",
            timeout=20000,
        )
        page.wait_for_function(
            f"() => {{ const log = document.querySelector('{CONSOLE_LOG}');"
            " return log && log.textContent.length > 0; }",
            timeout=45000,
        )

    @covers_requirement(
        "webclient-vue-application::degraded-text-remains-playable-alongside-the-vue-shell"
    )
    def test_incompatible_oob_locks_graphical_keeps_text(self):
        """C3 task 2.3: an incompatible OOB presentation locks graphical controls."""
        page, _ = self.open_vue_page()
        self._store_active(page)
        install_outbound_recorder(page)
        # Force an incompatible presentation: send ui_sync with an unsupported
        # protocol_version so the server replies ui_protocol_error(unsupported_version).
        page.evaluate(
            "() => Evennia.msg('ui_sync', [{ protocol_version: 2 }], {})"
        )
        page.wait_for_function(
            "() => { const s = window.__elosernBridge.store;"
            " const pe = s.view.protocolError;"
            " return pe && pe.code === 'unsupported_version'; }",
            timeout=45000,
        )
        self.assertTrue(
            page.evaluate("() => window.__elosernBridge.store.view.mutationsLocked"),
            "the incompatible OOB presentation must lock the graphical controls",
        )
        # The text path is independent of the OOB panel channel: a text command
        # still round-trips while the graphical dock is locked.
        page.evaluate("() => window.__elosernBridge.store.sendText('look')")
        page.wait_for_function(
            "() => { const s = window.__elosernBridge.store;"
            " return s.narrative.some(l => l.kind === 'out' && l.text.length > 0); }",
            timeout=45000,
        )

    def test_production_base_html_default_stays_legacy(self):
        """C3 task 2.4: the production base.html default is UNCHANGED (legacy)."""
        # The logged_in_page helper opens the production webclient_url (no Vue
        # flag) and waits for the legacy GoldenLayout shell (task 2.4).
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # The legacy shell is active; the Vue bundle is NOT loaded under the
        # production default.
        self.assertIsNone(
            page.evaluate("window.__elosernBridge ?? null"),
            "the Vue bridge only exists in the Vue branch (test config)",
        )
        self.assertIsNotNone(
            page.evaluate("window.Elosern && window.Elosern.StateController ? window.Elosern.StateController : null"),
            "the legacy GoldenLayout shell owns the production default",
        )
