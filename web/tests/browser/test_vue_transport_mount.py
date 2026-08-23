"""C3 (webclient-vue-09-wire-transport-mount) managed-browser acceptance.

Proves the Vue app is live-capable over the evennia.js OOB transport against
a real managed Evennia server:

- the store adopts server snapshots/updates (``ui_snapshot``/``ui_update``);
- the C2 bridge dispatches ``ui_action`` (dispatch-only, one mutation in flight);
- the D10 vanilla text console is the degradation fallback (the Vite bundle
  blocked keeps the text path live);
- an incompatible OOB presentation (``ui_protocol_error`` / unsupported_version)
  locks the graphical controls while the text path keeps working;
- the C4 production flip: the ``base.html`` default is now the Vue SPA.

The ``?__vue=1`` fixture forces the Vue branch in the test config; the
production ``base.html`` default (now Vue) is asserted unchanged here.
"""

from __future__ import annotations

import unittest

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    BROWSER_ACCOUNT,
    BROWSER_PASSWORD,
    evaluate_tolerating_navigation,
    install_outbound_recorder,
    sent_action_count,
    wait_for_store_state,
)


def _store_active(state: dict) -> bool:
    """The transport is connected and the session is in the active phase."""
    return bool(state.get("connected")) and state.get("phase") == "active"


def _store_active_unlocked(state: dict) -> bool:
    """The transport is connected, active, and not mutation-locked."""
    return _store_active(state) and state.get("mutationsLocked") is not True

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
        # The degraded (bundle-blocked) page has no C4 bridge or store, so the
        # deterministic readiness is the D10 console's data-status (DOM); the
        # store predicate is trivially true and the DOM descriptor carries the
        # actual gate.
        if block_bundle:
            wait_for_store_state(
                page,
                lambda state: True,
                dom_readiness={
                    "selector": CONSOLE,
                    "predicate": (
                        f"() => {{ const c = document.querySelector('{CONSOLE}');"
                        " return c && c.getAttribute('data-status') === 'ready'; }}"
                    ),
                    "description": "the D10 text console reports data-status=ready",
                },
                timeout=30000,
            )
        else:
            wait_for_store_state(page, _store_active, timeout=45000)
        return page, responses

    def _store_active(self, page) -> None:
        wait_for_store_state(page, _store_active_unlocked, timeout=45000)

    def test_live_transport_round_trips_and_store_adopts_snapshot(self):
        """C3 task 2.2: transport round-trip + store snapshot adoption."""
        page, _ = self.open_vue_page(capture_responses=True)
        self._store_active(page)
        install_outbound_recorder(page)
        # Send a text command through the C1 store (the single text path).
        page.evaluate("() => window.__elosernBridge.store.sendText('look')")
        # The command crosses the wire and the server's room text returns
        # through the D10 coordinator into the store's narrative.

        def _text_command_crossed(state: dict) -> bool:
            return bool(evaluate_tolerating_navigation(
                page,
                "() => (window.__elosernSent || []).some("
                "(m) => m[0] === 'text' && m[1] && m[1][0] === 'look')",
            ))

        def _narrative_has_out_line(state: dict) -> bool:
            return bool(evaluate_tolerating_navigation(
                page,
                "() => { const s = window.__elosernBridge.store;"
                " return s && s.narrative.some(l => l.kind === 'out' && l.text.length > 0); }",
            ))

        wait_for_store_state(
            page,
            _text_command_crossed,
            timeout=20000,
        )
        wait_for_store_state(
            page,
            _narrative_has_out_line,
            timeout=45000,
        )

    @covers_requirement(
        "webclient-vue-application::the-view-layer-is-fully-reactive-and-store-bound-with-no-legacy-imperative-view-plugin"
    )
    def test_dispatch_via_bridge(self):
        """C3 task 2.2: dispatch-only ui_action through the C2 bridge."""
        page, _ = self.open_vue_page()
        self._store_active(page)
        install_outbound_recorder(page)
        # Ensure the presentation revision is settled before dispatching so the
        # ui_action names the server's newest revision (stale guard).
        wait_for_store_state(
            page,
            lambda state: bool(state.get("revision")),
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
        wait_for_store_state(
            page,
            lambda state: not (state.get("dispatch") or {}).get("inFlight"),
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

        # The degraded (bundle-blocked) page has no Vue store/bridge, so the
        # deterministic readiness is the D10 console and the ``__elosernSent``
        # outbound recorder; the store predicate is trivially true and the
        # gate is carried by the recorder closure and the console-log DOM check.
        def _text_command_crossed(state: dict) -> bool:
            return bool(evaluate_tolerating_navigation(
                page,
                "() => (window.__elosernSent || []).some("
                "(m) => m[0] === 'text' && m[1] && m[1][0] === 'look')",
            ))

        wait_for_store_state(
            page,
            _text_command_crossed,
            timeout=20000,
        )
        wait_for_store_state(
            page,
            lambda state: True,
            dom_readiness={
                "selector": CONSOLE_LOG,
                "predicate": (
                    f"() => {{ const log = document.querySelector('{CONSOLE_LOG}');"
                    " return log && log.textContent.length > 0; }"
                ),
                "description": "the D10 console log is non-empty",
            },
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
        wait_for_store_state(
            page,
            lambda state: (state.get("protocolError") or {}).get("code") == "unsupported_version",
            timeout=45000,
        )
        self.assertTrue(
            page.evaluate("() => window.__elosernBridge.store.view.mutationsLocked"),
            "the incompatible OOB presentation must lock the graphical controls",
        )
        # The text path is independent of the OOB panel channel: a text command
        # still round-trips while the graphical dock is locked.
        page.evaluate("() => window.__elosernBridge.store.sendText('look')")

        def _narrative_has_out_line(state: dict) -> bool:
            return bool(evaluate_tolerating_navigation(
                page,
                "() => { const s = window.__elosernBridge.store;"
                " return s && s.narrative.some(l => l.kind === 'out' && l.text.length > 0); }",
            ))

        wait_for_store_state(
            page,
            _narrative_has_out_line,
            timeout=45000,
        )

    @covers_requirement(
        "webclient-vue-application::the-view-layer-is-fully-reactive-and-store-bound-with-no-legacy-imperative-view-plugin"
    )
    def test_production_base_html_default_is_vue(self):
        """C4: the production base.html default is the Vue SPA (the C4 flip)."""
        # The logged_in_page helper opens the production webclient_url (no
        # forced-Vue flag needed anymore) and waits for the Vue shell.
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # The Vue bridge is active under the production default; the legacy
        # GoldenLayout shell globals and jQuery are retired from the load path.
        self.assertIsNotNone(
            page.evaluate("window.__elosernBridge ?? null"),
            "the Vue bridge owns the production default (C4 flip)",
        )
        self.assertIsNone(
            page.evaluate("window.Elosern && window.Elosern.StateController ? window.Elosern.StateController : null"),
            "the legacy GoldenLayout shell is retired from the load path",
        )
        self.assertIsNone(
            page.evaluate("window.jQuery ?? null"),
            "the legacy jQuery view plugin is retired from the C4 load path",
        )

    @covers_requirement(
        "webclient-vue-application::the-design-system-carries-over-from-the-design-draft-and-stays-offline"
    )
    def test_reduced_motion_and_status_not_color_only(self):
        """C4 task 3.2: reduced-motion is honored; status is never color-only."""
        page, _ = self.open_vue_page()
        self._store_active(page)

        # Reduced motion: emulate prefers-reduced-motion: reduce; the tokens.css
        # @media block must resolve the motion tokens to 1ms.
        page.emulate_media(reduce_motion="reduce")
        motion_base = page.evaluate(
            "() => getComputedStyle(document.documentElement)."
            "getPropertyValue('--motion-base').trim()"
        )
        self.assertEqual(
            motion_base,
            "1ms",
            "prefers-reduced-motion must resolve the motion tokens to 1ms",
        )

        # Not color-only: each vitals gauge carries a symbol glyph, a text
        # label, and a numeric current/maximum value, so health is never
        # conveyed by the colored bar alone.
        for key in ("hp", "mp", "sp"):
            value_el = page.locator(f'[data-testid="status-panel__gauge-value--{key}"]')
            self.assertEqual(
                value_el.count(),
                1,
                f"the {key} gauge numeric value element must be present",
            )
            text = value_el.inner_text().strip()
            self.assertRegex(
                text,
                r"\d+\s*/\s*\d+",
                f"the {key} gauge value must show a numeric current/maximum, not color alone",
            )
