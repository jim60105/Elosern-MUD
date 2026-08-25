"""Vue foundation acceptance (A2, webclient-vue-01-foundation) + B1 core family.

Exercises the mutually-exclusive Vue branch of the WebClient through the
``?__vue=1`` fixture (the C4 flip makes the Vue SPA the production default;
the flag remains a per-request test-route override):
the Vite bundle, its styles, and its self-hosted fonts load from the project
origin while every non-local request is blocked, the dependency-free vanilla
text console round-trips commands through ``evennia.js`` without jQuery (the
D10 transport-bootstrap spike), the B1 core narrative family renders visible
and pointer-usable at both supported desktop viewports, and the Storybook
showcase stories render from local assets with every non-local request
blocked (webclient-vue-02-showcase-core).
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    BROWSER_ACCOUNT,
    BROWSER_PASSWORD,
    evaluate_tolerating_navigation,
    fresh_epoch,
    install_outbound_recorder,
    snapshot_envelope,
    valid_status_panel,
    wait_for_shell_active,
    wait_for_store_state,
)


def _store_active(state: dict) -> bool:
    """The transport is connected and the session is in the active phase."""
    return bool(state.get("connected")) and state.get("phase") == "active"

REPO_ROOT = Path(__file__).resolve().parents[3]
STORYBOOK_OUT = REPO_ROOT / ".storybook-out"

# Mirror of the component-coverage gate's `title:` extraction (the same
# regex the gate applies to every `*.stories.js` file under web/webclient-app).
STORY_TITLE_RE = re.compile(r"""title:\s*["'`]([^"'`]+)["'`]""")


def _collect_story_titles() -> set[str]:
    """Collect the Storybook story titles the component-coverage gate sees.

    Mirrors `scripts/component-coverage.mjs`'s collector: walk
    `web/webclient-app` for `*.stories.js`, skip `node_modules` and
    dot-directories, and extract each file's `title:` literal.
    """
    titles: set[str] = set()
    app_root = REPO_ROOT / "web" / "webclient-app"
    for path in app_root.rglob("*.stories.js"):
        parts = path.relative_to(app_root).parts
        if "node_modules" in parts or any(part.startswith(".") for part in parts):
            continue
        match = STORY_TITLE_RE.search(path.read_text(encoding="utf-8"))
        if match:
            titles.add(match.group(1))
    return titles


# The deterministic story rendered by the offline-rendering check: the
# narrative centerpiece bound to the fixture sample.
STORY_ID = "core-narrativefeed--world-narrative"
STORY_SAMPLE_LINE = "你站在測試起點的石板廣場上，夜霧低垂，遠燈明滅。"

VUE_QUERY = "?__vue=1"

CONSOLE = '[data-testid="text-console"]'
CONSOLE_LOG = '[data-testid="text-console-log"]'
CONSOLE_INPUT = '[data-testid="text-console-input"]'
VUE_ROOT = '[data-testid="elosern-vue-root"]'

# The B1 core family's top-level surfaces that must be visible at both
# supported desktop viewports (the pre-store shell mounts the usable "ready"
# slice, so all of these render unobscured — the narrative feed is present
# but empty until the C1 store feeds it). The connect overlay is a state
# surface rendered only for non-ready statuses, so its absence on the ready
# mount is asserted separately (proving the shell is not covered).
CORE_SURFACE_TESTIDS = (
    "topbar",
    "narrative-feed",
    "command-drawer",
    "command-drawer-entry",
)


class VueFoundationBrowserTest(BrowserAcceptanceTest):
    """Shared managed server; Vue branch page via the review-window flag."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # The offline story-rendering check serves the static Storybook build;
        # build it once per process when the checkout has none (CI workspaces
        # only build the app dist).
        if not (STORYBOOK_OUT / "iframe.html").is_file():
            result = subprocess.run(
                ["npm", "run", "build-storybook"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=900,
            )
            assert (
                result.returncode == 0
            ), "Storybook build failed under browser acceptance:\n" + result.stdout + result.stderr

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

    def open_vue_page(self, capture_responses=False):
        """Log in and open the WebClient Vue branch; return (page, responses)."""
        page = self.new_page()
        responses: list = []
        if capture_responses:
            page.on("response", lambda response: responses.append(response))
        self._login(page)
        page.goto(f"{self.webclient_url}{VUE_QUERY}")
        # The B1 shell retires the replaced text fallback on mount (hidden,
        # never removed), so readiness is asserted on transport state, not
        # visibility.
        wait_for_store_state(
            page,
            _store_active,
            dom_readiness={
                "selector": CONSOLE,
                "predicate": (
                    f"() => {{ const c = document.querySelector('{CONSOLE}');"
                    " return c && c.getAttribute('data-status') === 'ready'; }"
                ),
                "description": "the D10 text console reports data-status=ready",
            },
            timeout=30000,
        )
        return page, responses

    @covers_requirement(
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps",
        "webclient-vue-application::the-webclient-loads-a-self-contained-offline-vue-spa",
        "webclient-vue-application::the-design-system-carries-over-from-the-design-draft-and-stays-offline",
    )
    def test_vue_bundle_loads_from_origin_offline(self):
        """The built page makes no remote runtime request (delta scenario)."""
        page, responses = self.open_vue_page(capture_responses=True)
        wait_for_store_state(
            page,
            _store_active,
            dom_readiness={
                "selector": VUE_ROOT,
                "predicate": (
                    f"() => !!document.querySelector('{VUE_ROOT}')"
                ),
                "description": "the Vue SPA root element is connected",
            },
            timeout=30000,
        )

        ok_urls = [response.url for response in responses if response.status == 200]
        origin_prefix = f"http://127.0.0.1:{self.server.runtime.http_port}"
        for url in ok_urls:
            assert url.startswith(origin_prefix), f"non-origin response: {url}"
        self.assertTrue(
            any(url.endswith("/static/webclient/app/dist/index.js") for url in ok_urls),
            "the stable Vite entry was not served from the project origin",
        )
        self.assertTrue(
            any(url.endswith("/static/webclient/app/dist/index.css") for url in ok_urls),
            "the bundle stylesheet was not served from the project origin",
        )
        self.assertTrue(
            any(
                "/static/webclient/app/dist/assets/" in url and url.endswith(".woff2")
                for url in ok_urls
            ),
            "no self-hosted woff2 font slice was served from the project origin",
        )
        self.assertEqual(
            page.get_attribute(VUE_ROOT, "data-elosern-stage"),
            "showcase-core",
            "the B1 core-family AppShell must be the mounted stage",
        )
        self.assertEqual(
            page.get_attribute(VUE_ROOT, "data-elosern-mode"),
            "exploration",
            "the live shell mounts in the server's contextual world mode",
        )

    @covers_requirement(
        "webclient-vue-application::the-webclient-loads-a-self-contained-offline-vue-spa"
    )
    def test_core_surfaces_render_usable_at_supported_viewports(self):
        """Each required B1 core surface is visible, in-bounds, and usable.

        The B1 shell mounts the usable "ready" slice, so the pre-connection
        splash must be absent. At BOTH supported desktop viewports the
        surfaces stay fully in-bounds and a real pointer round-trip on the
        command drawer must succeed (a covered shell or a surface pushed off
        the input path would fail): the entry button opens the drawer, the
        field accepts text, Enter sends (the field clears), and Escape
        releases back to the narrative pane.
        """
        page, _responses = self.open_vue_page()
        wait_for_store_state(
            page,
            _store_active,
            dom_readiness={
                "selector": VUE_ROOT,
                "predicate": (
                    f"() => !!document.querySelector('{VUE_ROOT}')"
                ),
                "description": "the Vue SPA root element is connected",
            },
            timeout=30000,
        )

        # The ready mount renders no blocking pre-connection layer.
        self.assertEqual(
            page.locator('[data-testid="connect-overlay"]').count(),
            0,
            "the ready mount must not render the pre-connection splash",
        )
        self.assertEqual(
            page.get_attribute("#elosern-offline-overlay", "data-visible"),
            "false",
            "the offline alert must stay hidden while the shell is ready",
        )

        for viewport in ((1440, 900), (1280, 720)):
            page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
            page.wait_for_timeout(300)
            for testid in CORE_SURFACE_TESTIDS:
                element = page.locator(f'[data-testid="{testid}"]')
                self.assertEqual(
                    element.count(),
                    1,
                    f"{testid} is not uniquely present at {viewport[0]}x{viewport[1]}",
                )
                self.assertTrue(
                    element.first.is_visible(),
                    f"{testid} is not visible at {viewport[0]}x{viewport[1]}",
                )
                # The whole required surface stays inside the viewport:
                # nothing is pushed below the fold or clipped off-screen.
                bounded = element.first.evaluate(
                    "(el) => { const r = el.getBoundingClientRect();"
                    " return r.top >= 0 && r.left >= 0"
                    " && r.bottom <= window.innerHeight"
                    " && r.right <= window.innerWidth && r.width > 0; }"
                )
                self.assertTrue(
                    bounded,
                    f"{testid} is not fully inside the {viewport[0]}x{viewport[1]}"
                    " viewport",
                )

            # Usability with a real pointer at this viewport: the entry
            # button opens the drawer, the field accepts text, Enter sends
            # (the field clears), and Escape releases the drawer back to the
            # action dock (webclient-desktop-shell: closing the open drawer
            # restores action-dock focus) — a covered or clipped surface
            # would fail here.
            page.locator('[data-testid="command-drawer-entry"]').click()
            wait_for_store_state(
                page,
                _store_active,
                dom_readiness={
                    "selector": '[data-testid="command-drawer"][data-open="true"]',
                    "predicate": (
                        "() => { const d = document.querySelector('[data-testid=\"command-drawer\"]');"
                        " return d && d.getAttribute('data-open') === 'true'; }"
                    ),
                    "description": "the command drawer is open",
                },
                timeout=10000,
            )
            field = page.locator('[data-testid="command-drawer-input"]')
            wait_for_store_state(
                page,
                _store_active,
                dom_readiness={
                    "selector": '[data-testid="command-drawer-input"]',
                    "predicate": (
                        "() => { const i = document.querySelector('[data-testid=\"command-drawer-input\"]'); "
                        "if (!i) { return false; } "
                        "const r = i.getBoundingClientRect(); "
                        "return r.width > 0 && r.height > 0 && i.offsetParent !== null; }"
                    ),
                    "description": "the drawer command input field is visible",
                },
                timeout=10000,
            )
            field.fill("look")
            field.press("Enter")
            wait_for_store_state(
                page,
                _store_active,
                dom_readiness={
                    "selector": '[data-testid="command-drawer-input"]',
                    "predicate": (
                        "() => { const i = document.querySelector('[data-testid=\"command-drawer-input\"]'); "
                        "return i && i.value === ''; }"
                    ),
                    "description": "the drawer command input cleared after send",
                },
                timeout=10000,
            )
            field.press("Escape")
            wait_for_store_state(
                page,
                _store_active,
                dom_readiness={
                    "selector": '[data-testid="command-drawer"][data-open="false"]',
                    "predicate": (
                        "() => { const d = document.querySelector('[data-testid=\"command-drawer\"]');"
                        " return d && d.getAttribute('data-open') === 'false'; }"
                    ),
                    "description": "the command drawer is closed",
                },
                timeout=10000,
            )
            self.assertTrue(
                page.evaluate(
                    "() => { const a = document.activeElement; "
                    "const dock = document.getElementById('action-dock'); "
                    "return !!dock && !!a && (a === dock || dock.contains(a)); }"
                ),
                "Escape must return focus to the action dock, not body",
            )

        self.assertIsNone(
            page.evaluate("window.jQuery ?? null"),
            "the Vue branch must not load full jQuery",
        )

    @covers_requirement(
        "webclient-browser-verification::browser-tests-are-localhost-only-and-deterministic",
        "webclient-vue-application::the-webclient-loads-a-self-contained-offline-vue-spa",
    )
    def test_text_console_round_trips_commands_without_jquery(self):
        """D10 spike: evennia.js round-trips text without full jQuery.

        The B1 shell retires the replaced fallback on mount, so the console
        is hidden; the round-trip is driven through the hidden element and
        the retirement itself is asserted. Reactivation on degradation lands
        with the C3 store wiring.
        """
        page, _responses = self.open_vue_page()
        wait_for_store_state(
            page,
            _store_active,
            dom_readiness={
                "selector": CONSOLE,
                "predicate": (
                    f"() => {{ const c = document.querySelector('{CONSOLE}');"
                    " return c && c.getAttribute('data-status') === 'ready'; }"
                ),
                "description": "the D10 text console reports data-status=ready",
            },
            timeout=30000,
        )
        self.assertFalse(
            page.locator(CONSOLE).is_visible(),
            "the B1 shell must retire the replaced text fallback on mount",
        )
        install_outbound_recorder(page)
        # A retired (display:none) element is not focusable; reveal the
        # console and its retired #messagewindow host for the duration of the
        # round-trip so real key events reach the console's listeners.
        page.evaluate(
            "() => { for (const sel of ['#messagewindow',"
            " '[data-testid=\"text-console\"]']) {"
            " for (const el of document.querySelectorAll(sel)) {"
            " el.style.display = ''; } } }"
        )
        field = page.locator(CONSOLE_INPUT)
        wait_for_store_state(
            page,
            _store_active,
            dom_readiness={
                "selector": CONSOLE_INPUT,
                "predicate": (
                    f"() => {{ const i = document.querySelector('{CONSOLE_INPUT}');"
                    " if (!i) { return false; }"
                    " const r = i.getBoundingClientRect();"
                    " return r.width > 0 && r.height > 0 && i.offsetParent !== null; }"
                ),
                "description": "the D10 console input field is visible",
            },
            timeout=10000,
        )
        field.fill("look")
        field.press("Enter")

        def _text_command_crossed(state: dict) -> bool:
            return bool(evaluate_tolerating_navigation(
                page,
                "() => (window.__elosernSent || []).some("
                "(m) => m[0] === 'text' && m[1] && m[1][0] === 'look')",
            ))

        wait_for_store_state(
            page,
            _text_command_crossed,
            timeout=15000,
        )
        # The command echo rendered and the server's deterministic room text
        # came back through the same jQuery-free transport.
        wait_for_store_state(
            page,
            _store_active,
            dom_readiness={
                "selector": CONSOLE_LOG,
                "predicate": (
                    f"() => {{ const log = document.querySelector('{CONSOLE_LOG}');"
                    " return log && log.textContent.includes('look'); }"
                ),
                "description": "the console log shows the command echo",
            },
            timeout=15000,
        )
        wait_for_store_state(
            page,
            _store_active,
            dom_readiness={
                "selector": CONSOLE_LOG,
                "predicate": (
                    f"() => {{ const log = document.querySelector('{CONSOLE_LOG}');"
                    " return log && log.textContent.includes('測試起點'); }"
                ),
                "description": "the console log shows the server room text",
            },
            timeout=30000,
        )
        self.assertIsNone(
            page.evaluate("window.jQuery ?? null"),
            "the text round-trip must not depend on full jQuery",
        )

    def test_vue_default_loads_when_flag_is_absent(self):
        """The C4 flip: the production default is the Vue SPA (no flag needed)."""
        page = self.new_page()
        self._login(page)
        page.goto(self.webclient_url)
        # The production default is now the Vue SPA: the bridge hook exists and
        # the full legacy jQuery is not loaded (only the scoped ready-shim).
        wait_for_shell_active(page)
        self.assertIsNone(page.evaluate("window.jQuery ?? null"))
        self.assertIsNotNone(
            page.evaluate("window.__elosernBridge ? true : null"),
            "the Vue bridge hook owns the production default (C4 flip)",
        )

    @covers_requirement(
        "webclient-component-showcase::storybook-stories-use-deterministic-offline-data-only",
        "webclient-component-showcase::every-required-ui-component-is-a-vue-sfc-with-a-documented-storybook-story",
        "webclient-component-showcase::the-frozen-component-set-grows-only-through-a-governed-redesign-wave",
    )
    def test_storybook_stories_render_offline(self):
        """A story renders from local assets with non-local requests blocked.

        The static Storybook build is served from a local throwaway HTTP
        origin; the base-class localhost guard aborts every other request, so
        the story must render entirely from the built local assets. The
        asserted fixture line also establishes that the story is bound to its
        representative prop values (the documented contract renders).
        """
        index = json.loads((STORYBOOK_OUT / "index.json").read_text(encoding="utf-8"))
        self.assertIn(
            STORY_ID,
            index.get("entries", {}),
            "the deterministic showcase story must be registered in the build",
        )

        class _StaticHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(
                    *args, directory=str(STORYBOOK_OUT), **kwargs
                )

            def log_message(self, format, *args):
                pass

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), _StaticHandler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.shutdown)
        port = httpd.server_address[1]

        page = self.new_page()
        failed: list[str] = []
        page.on("response", lambda response: failed.append(response.url) if response.status >= 400 else None)
        page.goto(f"http://127.0.0.1:{port}/iframe.html?id={STORY_ID}&viewMode=story")
        # The Storybook story page is a pure component render with no C4 bridge
        # or store, so readiness is purely DOM-based: wait for the
        # narrative-feed's visibility (the stable `data-testid` hook).
        page.wait_for_function(
            "() => { const f = document.querySelector('[data-testid=\"narrative-feed\"]'); "
            "if (!f) { return false; } "
            "const r = f.getBoundingClientRect(); "
            "return r.width > 0 && r.height > 0 && f.offsetParent !== null; }",
            timeout=30000,
        )
        feed = page.locator('[data-testid="narrative-feed"]')
        self.assertIn(
            STORY_SAMPLE_LINE,
            feed.inner_text(),
            "the story must render its bound fixture data through the "
            "markup pipeline",
        )
        self.assertEqual(
            failed, [], f"the offline story render made failing requests: {failed}"
        )


    @covers_requirement(
        "webclient-vue-application::the-app-preserves-the-client-dom-contract-hooks-and-exposes-stable-test-hooks",
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe",
        "webclient-pointer-activation::keyboard-input-is-dispatched-through-the-webclient-plugin-contract",
    )
    def test_window_elosern_bridge_facades_resolve_and_route(self):
        """C2: the window.Elosern public-contract bridge resolves and routes.

        The A1 frozen façade surface (five façades, exact member sets) resolves
        on the Vue test-config page; narrative input routes through the store's
        single append path; the action-dispatch entry is single (one mutation in
        flight); and document key events are claimed exactly when the router
        consumes the key, with unclaimed keys falling through to the text path
        (the live transport's text round-trip is proven by C3).
        """
        page, _responses = self.open_vue_page()
        wait_for_store_state(
            page,
            _store_active,
            dom_readiness={
                "selector": VUE_ROOT,
                "predicate": (
                    f"() => !!document.querySelector('{VUE_ROOT}')"
                ),
                "description": "the Vue SPA root element is connected",
            },
            timeout=30000,
        )

        surface = page.evaluate(
            """() => {
                const e = window.Elosern;
                return {
                    facades: e ? Object.keys(e).sort() : null,
                    protocolVersion: e && e.Protocol ? e.Protocol.PROTOCOL_VERSION : null,
                    hasRouter: e && e.KeyboardRouter ? typeof e.KeyboardRouter.createRouter === "function" : false,
                    narrativeMembers: e && e.narrativeInput ? Object.keys(e.narrativeInput).sort() : null,
                    actionMembers: e && e.actions ? Object.keys(e.actions).sort() : null,
                    clientMembers: e && e.actions.client ? Object.keys(e.actions.client).sort() : null,
                };
            }"""
        )
        self.assertEqual(
            surface["facades"],
            ["KeyboardRouter", "LayoutStore", "Protocol", "actions", "narrativeInput"],
            "the bridge exposes exactly the five frozen façades (A1 audit §1)",
        )
        self.assertEqual(surface["protocolVersion"], 1)
        self.assertTrue(surface["hasRouter"])
        self.assertEqual(
            surface["narrativeMembers"],
            [
                "appendInput",
                "mountChoicePoint",
                "replaceChoicePoint",
                "unmountChoicePoint",
            ],
        )
        self.assertEqual(
            surface["actionMembers"],
            [
                "client",
                "handleActionResult",
                "handlePresentation",
                "handleReconnect",
                "handleTransportReset",
                "requestResync",
                "resetResyncEpisode",
                "submit",
                "sync",
            ],
        )
        self.assertEqual(
            surface["clientMembers"],
            [
                "inFlightRequestId",
                "isInFlight",
                "isLocked",
                "lastResult",
                "onActionResult",
                "onDetached",
                "onPresentationAccepted",
                "onReconnect",
                "onTransportReset",
                "submit",
                "sync",
                "uncertain",
            ],
        )

        # Drive the store to an active session through the stable test hook
        # (the live OOB delivery of these envelopes is C3's transport work).
        context_actions = {
            "schema_version": 5,
            "available": True,
            "kind": "exploration",
            "affordances": [
                {
                    "action_id": "explore.wait",
                    "label": "等待",
                    "params": {"daypart": "dusk"},
                    "freeform": False,
                    "navigation": False,
                    "enabled": True,
                    "disabled_reason": None,
                },
                {
                    "surface": "guild",
                    "label": "公會",
                    "navigation": True,
                    "enabled": True,
                    "disabled_reason": None,
                },
            ],
            "suggestions": {"status": "generating"},
        }
        envelope = snapshot_envelope(
            fresh_epoch(),
            1,
            {
                "status": valid_status_panel("測試起點", "p1"),
                "context_actions": context_actions,
            },
        )
        # The live C3 transport (bound by base.html) already advanced the
        # transport generation on `connection_open`, so the driven generation
        # must be strictly greater than the store's current generation.
        established = page.evaluate(
            """(envelope) => {
                const { store } = window.__elosernBridge;
                const nextGen = store.view.generation + 1;
                store.beginTransport(nextGen);
                store.setConnected(true);
                const result = store.receive(nextGen, "ui_snapshot", [envelope]);
                return { accepted: result.accepted, gen: nextGen };
            }""",
            envelope,
        )
        self.assertTrue(
            established["accepted"], "the new-epoch snapshot must be adopted"
        )
        gen = established["gen"]

        # The narrative append path is single: one appendInput call adds exactly
        # one `.inp` line (no duplicated append path). The live C3 transport also
        # appends the server's own text lines to the store, so compare against
        # the pre-append count rather than assuming an empty narrative.
        append = page.evaluate(
            """() => {
                const { store, facade } = window.__elosernBridge;
                const before = store.narrative.length;
                const accepted = facade.narrativeInput.appendInput("look");
                return { accepted, before: before, lines: store.narrative.length };
            }"""
        )
        self.assertTrue(append["accepted"])
        self.assertEqual(
            append["lines"],
            append["before"] + 1,
            "one appendInput must add exactly one narrative line",
        )

        # The action dispatch entry is single: the first submit returns a
        # request id; a second submit while one mutation is in flight
        # dispatches nothing.
        dispatch = page.evaluate(
            """() => {
                const { facade } = window.__elosernBridge;
                const first = facade.actions.submit("explore.wait", { daypart: "dusk" });
                const second = facade.actions.submit("explore.wait", { daypart: "dusk" });
                return {
                    first,
                    second,
                    isInFlight: facade.actions.client.isInFlight(),
                    requestId: facade.actions.client.inFlightRequestId(),
                    uncertain: facade.actions.client.uncertain(),
                };
            }"""
        )
        # The request id is the action-dispatch session counter (session:1 is the
        # first dispatched action), independent of the transport generation.
        self.assertEqual(dispatch["first"], "session:1")
        self.assertIsNone(dispatch["second"], "no duplicate action path")
        self.assertTrue(dispatch["isInFlight"])
        self.assertEqual(dispatch["requestId"], "session:1")
        self.assertFalse(dispatch["uncertain"])

        # The release gate: feed the presentation revision through the bridge
        # entry point; the in-flight lock releases once the committed revision
        # reaches the declared presentation revision.
        released = page.evaluate(
            """(gen) => {
                const { store, facade } = window.__elosernBridge;
                const result = store.receive(
                    gen,
                    "ui_action_result",
                    [{
                        protocol_version: 1,
                        presentation_epoch: store.view.epoch,
                        request_id: "session:1",
                        outcome: "success",
                        code: "completed",
                        message: "完成",
                        presentation_revision: 2,
                    }],
                );
                facade.actions.handlePresentation({
                    protocol_version: 1,
                    presentation_epoch: store.view.epoch,
                    revision: 2,
                    mode: "exploration",
                    panels: { status: store.view.panels.status },
                    layout_version: 1,
                    server_time: {
                        year: 1204,
                        season_index: 0,
                        season_label: "春季",
                        day_in_season: 3,
                        hour: 12,
                        minute: 0,
                        second: 0,
                    },
                });
                return {
                    resultAccepted: result.accepted,
                    stillInFlight: facade.actions.client.isInFlight(),
                };
            }""",
            gen,
        )
        self.assertTrue(released["resultAccepted"])
        self.assertFalse(released["stillInFlight"])

        # Document key events route through the bridge's key routing. The
        # keyboard router's exploration focus frame is the G2 hierarchical
        # root (Move / Look / Interact / Character / Quests / Inventory /
        # Wait), rendered as a single-row grid — so ArrowDown is a no-op and
        # focus stays on the first cell (`move`). This replaces the legacy
        # B2 flat `action-`/`target-` affordance-list key contract. Unclaimed
        # letter keys fall through to the text path.
        keys = page.evaluate(
            """() => {
                const { store, facade } = window.__elosernBridge;
                const down = new KeyboardEvent("keydown", { key: "ArrowDown", cancelable: true });
                document.dispatchEvent(down);
                const letter = new KeyboardEvent("keydown", { key: "g", cancelable: true });
                document.dispatchEvent(letter);
                return {
                    focusKey: store.view.focus.key,
                    focusEnabled: store.view.focus.enabled,
                    downClaimed: down.defaultPrevented,
                    letterSwallowed: letter.defaultPrevented,
                    inFlight: facade.actions.client.isInFlight(),
                };
            }"""
        )
        self.assertEqual(keys["focusKey"], "move")
        self.assertTrue(keys["focusEnabled"])
        self.assertTrue(keys["downClaimed"])
        self.assertFalse(keys["letterSwallowed"], "unclaimed keys must fall through to the text path")

        # Enter on the G2 exploration root's focused item (`move`) pushes its
        # client-local move submenu (the dock depth becomes 2) without
        # dispatching a ui_action. With no traversal exits in the committed
        # exploration panel, the pushed move submenu's first row is the
        # disabled `move-empty` item.
        enter_result = page.evaluate(
            """() => {
                const { store, facade } = window.__elosernBridge;
                const enter = new KeyboardEvent("keydown", { key: "Enter", cancelable: true });
                document.dispatchEvent(enter);
                return {
                    dockDepth: store.view.dockDepth,
                    focusKey: store.view.focus.key,
                    focusEnabled: store.view.focus.enabled,
                    inFlight: facade.actions.client.isInFlight(),
                    prevented: enter.defaultPrevented,
                };
            }"""
        )
        self.assertEqual(enter_result["dockDepth"], 2)
        self.assertEqual(enter_result["focusKey"], "move-empty")
        self.assertFalse(enter_result["focusEnabled"], "the pushed move submenu's first row is the disabled move-empty item")
        self.assertFalse(enter_result["inFlight"], "a navigation item must not dispatch a ui_action")
        self.assertTrue(enter_result["prevented"])

    @covers_requirement(
        "webclient-component-showcase::the-frozen-component-set-grows-only-through-a-governed-redesign-wave"
    )
    def test_frozen_manifest_grows_only_in_lockstep_with_stories(self):
        """The component-coverage gate enforces the frozen required set.

        A governed redesign wave adds a component only in lockstep: the same
        change adds the manifest title, ships the Storybook story (bound to
        deterministic offline `args:` values), and extends the spec. The gate
        (`scripts/component-coverage.mjs`) fails closed when a manifest title
        has no matching story, a registered story has no manifest entry (the
        component is wired into the live app before its manifest row exists),
        or a frozen manifest is empty.
        """
        collected = _collect_story_titles()
        self.assertGreater(
            len(collected),
            0,
            "the webclient-app must register story titles for the gate probe",
        )

        def run_gate(manifest: dict) -> subprocess.CompletedProcess:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "component-manifest.json"
                path.write_text(json.dumps(manifest), encoding="utf-8")
                return subprocess.run(
                    ["node", "scripts/component-coverage.mjs", str(path)],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

        # Lockstep pass: the wave that ships the story also adds its
        # manifest title in the same change — the gate passes with the
        # complete set re-frozen.
        lockstep = run_gate({"required": sorted(collected), "frozen": True})
        self.assertEqual(
            lockstep.returncode,
            0,
            "a lockstep wave (manifest title + story in the same change) "
            "must pass the component-coverage gate:\n"
            + lockstep.stdout
            + lockstep.stderr,
        )

        # A manifest title added without a matching story: the wave edited
        # the manifest alone, so the gate fails and the change cannot land.
        missing_story = run_gate(
            {"required": sorted(collected | {"Core/PhantomComponent"}), "frozen": True}
        )
        self.assertNotEqual(
            missing_story.returncode,
            0,
            "a manifest edit without a matching story must fail the gate",
        )
        self.assertIn("Core/PhantomComponent", missing_story.stderr)
        self.assertIn("missing a story file", missing_story.stderr)

        # A registered story whose title is absent from the manifest: the
        # component is wired into the live app before its story/manifest
        # entry exists, so the frozen set would grow silently.
        dropped = sorted(collected)[0]
        unlisted = run_gate({"required": sorted(collected - {dropped}), "frozen": True})
        self.assertNotEqual(
            unlisted.returncode,
            0,
            "a story without a manifest entry must fail the gate",
        )
        self.assertIn(dropped, unlisted.stderr)
        self.assertIn("missing from the", unlisted.stderr)

        # A frozen manifest with an empty required set fails closed: the
        # complete set cannot be empty while frozen.
        empty_frozen = run_gate({"required": [], "frozen": True})
        self.assertNotEqual(
            empty_frozen.returncode,
            0,
            "a frozen required-component manifest must not be empty",
        )
        self.assertIn(
            "frozen required-component manifest is empty",
            empty_frozen.stderr,
        )


if __name__ == "__main__":
    unittest.main()
