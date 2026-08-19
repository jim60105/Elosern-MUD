"""Vue foundation acceptance (A2, webclient-vue-01-foundation).

Exercises the mutually-exclusive Vue branch of the WebClient through the
review-window ``?__vue=1`` fixture (the production default stays legacy):
the Vite bundle, its styles, and its self-hosted fonts load from the project
origin while every non-local request is blocked, and the dependency-free
vanilla text console round-trips commands through ``evennia.js`` without
jQuery (the D10 transport-bootstrap spike).
"""

from __future__ import annotations

import unittest

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    BROWSER_ACCOUNT,
    BROWSER_PASSWORD,
    install_outbound_recorder,
    wait_for_shell_active,
)

VUE_QUERY = "?__vue=1"

CONSOLE = '[data-testid="text-console"]'
CONSOLE_LOG = '[data-testid="text-console-log"]'
CONSOLE_INPUT = '[data-testid="text-console-input"]'
VUE_ROOT = '[data-testid="elosern-vue-root"]'


class VueFoundationBrowserTest(BrowserAcceptanceTest):
    """Shared managed server; Vue branch page via the review-window flag."""

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
        page.wait_for_selector(CONSOLE, timeout=30000)
        return page, responses

    @covers_requirement(
        "webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps"
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
            "foundation-stub",
            "the Vue root build stub must be the mounted stage",
        )
        self.assertIsNone(
            page.evaluate("window.jQuery ?? null"),
            "the Vue branch must not load full jQuery",
        )

    @covers_requirement(
        "webclient-browser-verification::browser-tests-are-localhost-only-and-deterministic"
    )
    def test_text_console_round_trips_commands_without_jquery(self):
        """D10 spike: evennia.js round-trips text without full jQuery."""
        page, _responses = self.open_vue_page()
        page.wait_for_function(
            f"() => {{ const c = document.querySelector('{CONSOLE}');"
            " return c && c.getAttribute('data-status') === 'ready'; }",
            timeout=30000,
        )
        install_outbound_recorder(page)
        page.fill(CONSOLE_INPUT, "look")
        page.press(CONSOLE_INPUT, "Enter")

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


if __name__ == "__main__":
    unittest.main()
