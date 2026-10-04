"""Shared browser acceptance test base.

Each test class boots the one per-process managed server in ``setUpClass``,
launches headless Chromium, guards every non-local request, and logs in with
the deterministic seeded account. All fixtures are local and deterministic.
"""

from __future__ import annotations

import unittest

from playwright.sync_api import sync_playwright

from .browser_helpers import guard_local_only, login_and_open, seed_motion_level
from .harness import get_shared_server

# The acceptance contract's reference viewport (retarget-desktop-viewport-contract):
# every journey that does not pass an explicit viewport opens here.
DEFAULT_VIEWPORT = (1451, 790)

# The acceptance contract's three-element viewport tuple
# (retarget-browser-acceptance-viewports D1): the reference, an uncapped 1.2
# display, and the capped large display.
ACCEPTANCE_VIEWPORT_TUPLE = ((1451, 790), (1741, 948), (2560, 1440))
# The two-element acceptance pair the prose requirements name.
ACCEPTANCE_VIEWPORTS = (ACCEPTANCE_VIEWPORT_TUPLE[0], ACCEPTANCE_VIEWPORT_TUPLE[2])

_UI_SCALE_REFERENCE_WIDTH = 1451
_UI_SCALE_REFERENCE_HEIGHT = 790
_UI_SCALE_MAX = 1.4


def ui_scale(viewport: tuple[int, int]) -> float:
    """The desktop chrome factor for a viewport.

    ``S = clamp(1, min(height / 790, width / 1451), 1.4)`` — the same factor
    ``lib/ui_scale.js`` writes to ``--ui-scale`` (webclient-proportional-ui-scale;
    retarget-desktop-viewport-contract). Chrome geometry scales by it once;
    viewport-relative ``vh``/``vw`` terms never do.
    """
    width, height = viewport
    raw = min(height / _UI_SCALE_REFERENCE_HEIGHT, width / _UI_SCALE_REFERENCE_WIDTH)
    return round(min(_UI_SCALE_MAX, max(1.0, raw)), 4)

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

    def new_page(
        self,
        viewport: tuple[int, int] = DEFAULT_VIEWPORT,
        motion_level: str | None = "off",
    ):
        """Open a fresh context with the localhost-only request guard.

        webclient-motion-level (design D9): the suite runs at the `off` motion
        level, so every transition and every message page is instant and no
        journey races a running animation. Pass ``motion_level=None`` where a
        journey needs first-load defaults or real typing.
        """
        context = self._browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]}
        )
        self._contexts.append(context)
        if motion_level is not None:
            seed_motion_level(context, motion_level)
        page = context.new_page()
        page.add_init_script(_WS_CAPTURE_SCRIPT)
        guard_local_only(page)
        return page

    def logged_in_page(
        self,
        viewport: tuple[int, int] = DEFAULT_VIEWPORT,
        motion_level: str | None = "off",
    ):
        """A logged-in WebClient page with the active shell rendered."""
        page = self.new_page(viewport, motion_level)
        login_and_open(page, self.webclient_url, self.base_url)
        return page
