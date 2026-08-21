"""Vue foundation acceptance (A2, webclient-vue-01-foundation) + B1 core family.

Exercises the mutually-exclusive Vue branch of the WebClient through the
review-window ``?__vue=1`` fixture (the production default stays legacy):
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
import subprocess
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    BROWSER_ACCOUNT,
    BROWSER_PASSWORD,
    install_outbound_recorder,
    wait_for_shell_active,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
STORYBOOK_OUT = REPO_ROOT / ".storybook-out"

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
        page.wait_for_function(
            f"() => {{ const c = document.querySelector('{CONSOLE}');"
            " return c && c.getAttribute('data-status') === 'ready'; }",
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
        page.wait_for_selector(VUE_ROOT, timeout=30000)

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
            "explore",
            "the pre-store shell must mount in the default world mode",
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
        page.wait_for_selector(VUE_ROOT, timeout=30000)

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
            # (the field clears), and Escape releases back to the narrative
            # pane — a covered or clipped surface would fail here.
            page.locator('[data-testid="command-drawer-entry"]').click()
            page.wait_for_selector(
                '[data-testid="command-drawer"][data-open="true"]', timeout=10000
            )
            field = page.locator("#inputfield")
            field.wait_for(state="visible", timeout=10000)
            field.fill("look")
            field.press("Enter")
            page.wait_for_function(
                "() => document.getElementById('inputfield') &&"
                " document.getElementById('inputfield').value === ''",
                timeout=10000,
            )
            field.press("Escape")
            page.wait_for_selector(
                '[data-testid="command-drawer"][data-open="false"]', timeout=10000
            )
            self.assertEqual(
                page.evaluate(
                    "document.activeElement && "
                    "document.activeElement.getAttribute('data-testid')"
                ),
                "narrative-feed",
                "Escape must return focus to the narrative pane, not body",
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
        page.wait_for_function(
            f"() => {{ const c = document.querySelector('{CONSOLE}');"
            " return c && c.getAttribute('data-status') === 'ready'; }",
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
        field.wait_for(state="visible", timeout=10000)
        field.fill("look")
        field.press("Enter")

        page.wait_for_function(
            "() => (window.__elosernSent || []).some("
            "(m) => m[0] === 'text' && m[1] && m[1][0] === 'look')",
            timeout=15000,
        )
        # The command echo rendered and the server's deterministic room text
        # came back through the same jQuery-free transport.
        page.wait_for_function(
            f"() => {{ const log = document.querySelector('{CONSOLE_LOG}');"
            " return log && log.textContent.includes('look');"
            " }",
            timeout=15000,
        )
        page.wait_for_function(
            f"() => {{ const log = document.querySelector('{CONSOLE_LOG}');"
            " return log && log.textContent.includes('測試起點');"
            " }",
            timeout=30000,
        )
        self.assertIsNone(
            page.evaluate("window.jQuery ?? null"),
            "the text round-trip must not depend on full jQuery",
        )

    def test_legacy_default_stays_when_flag_is_absent(self):
        """The XOR flag is off by default: the legacy shell still loads."""
        page = self.new_page()
        self._login(page)
        page.goto(self.webclient_url)
        # The production default is the legacy shell: full jQuery present and
        # the shell active.
        wait_for_shell_active(page)
        self.assertIsNotNone(page.evaluate("window.jQuery ?? null"))
        self.assertIsNone(
            page.evaluate("window.ElosernVue ?? null"),
            "the Vue bundle must not load on the legacy default page",
        )

    @covers_requirement(
        "webclient-component-showcase::storybook-stories-use-deterministic-offline-data-only",
        "webclient-component-showcase::every-required-ui-component-is-a-vue-sfc-with-a-documented-storybook-story",
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
        feed = page.locator('[data-testid="narrative-feed"]')
        feed.wait_for(state="visible", timeout=30000)
        self.assertIn(
            STORY_SAMPLE_LINE,
            feed.inner_text(),
            "the story must render its bound fixture data through the "
            "markup pipeline",
        )
        self.assertEqual(
            failed, [], f"the offline story render made failing requests: {failed}"
        )


if __name__ == "__main__":
    unittest.main()
