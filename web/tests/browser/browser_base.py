"""Shared browser acceptance test base.

Each test class boots the one per-process managed server in ``setUpClass``,
launches headless Chromium, guards every non-local request, and logs in with
the deterministic seeded account. All fixtures are local and deterministic.
"""

from __future__ import annotations

import unittest

from playwright.sync_api import sync_playwright

from .browser_helpers import guard_local_only, login_and_open
from .harness import get_shared_server

DEFAULT_VIEWPORT = (1440, 900)

# Captures every WebSocket the page creates so tests can interrupt the active
# transport with an abnormal close (which, unlike Evennia's graceful
# ``websocket_close``, preserves the Django-session authentication used to
# re-login on reconnect).
_WS_CAPTURE_SCRIPT = """
window.__elosernWs = null;
(function () {
  var Native = window.WebSocket;
  function Wrapped(url, protocols) {
    var ws = new Native(url, protocols);
    window.__elosernWs = ws;
    return ws;
  }
  Wrapped.prototype = Native.prototype;
  Wrapped.CONNECTING = Native.CONNECTING;
  Wrapped.OPEN = Native.OPEN;
  Wrapped.CLOSING = Native.CLOSING;
  Wrapped.CLOSED = Native.CLOSED;
  window.WebSocket = Wrapped;
})();
"""


class BrowserAcceptanceTest(unittest.TestCase):
    """Boots the managed server once and provides logged-in Chromium pages."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = get_shared_server()
        cls.base_url = f"http://127.0.0.1:{cls.server.runtime.http_port}"
        cls.webclient_url = cls.server.runtime.webclient_url

    def setUp(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._contexts = []
        self.addCleanup(self._close_playwright)

    def _close_playwright(self) -> None:
        for context in self._contexts:
            try:
                context.close()
            except Exception:
                pass
        try:
            self._browser.close()
        except Exception:
            pass
        self._playwright.stop()

    def new_page(self, viewport: tuple[int, int] = DEFAULT_VIEWPORT):
        """Open a fresh context with the localhost-only request guard."""
        context = self._browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]}
        )
        self._contexts.append(context)
        page = context.new_page()
        page.add_init_script(_WS_CAPTURE_SCRIPT)
        guard_local_only(page)
        return page

    def logged_in_page(self, viewport: tuple[int, int] = DEFAULT_VIEWPORT):
        """A logged-in WebClient page with the active shell rendered."""
        page = self.new_page(viewport)
        login_and_open(page, self.webclient_url, self.base_url)
        return page
