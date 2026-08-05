"""Shell acceptance tests (section 6.5) at both supported desktop viewports."""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import store_state

REQUIRED_SURFACES = (
    ".elosern-header",
    ".elosern-narrative",
    ".elosern-status",
    ".elosern-action-dock",
    ".elosern-drawer",
    "#action-dock",
    "#inputfield",
)


class ShellAcceptanceTest(BrowserAcceptanceTest):
    """Every required surface at 1440x900 and 1280x720, plus keyboard journeys."""

    def assert_surfaces_visible(self, page):
        for selector in REQUIRED_SURFACES:
            locator = page.locator(selector)
            self.assertEqual(locator.count(), 1, f"missing surface {selector}")
            self.assertTrue(locator.is_visible(), f"{selector} is not visible")

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable"
    )
    def test_surfaces_visible_at_1440x900(self):
        page = self.logged_in_page((1440, 900))
        self.assert_surfaces_visible(page)

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable"
    )
    def test_surfaces_visible_at_1280x720(self):
        page = self.logged_in_page((1280, 720))
        self.assert_surfaces_visible(page)

    @covers_requirement(
        "webclient-desktop-shell::theme-and-controls-remain-accessible"
    )
    def test_unavailable_placeholders_and_numeric_status(self):
        page = self.logged_in_page()
        # The art component is now the real renderer: no foundation placeholder
        # remains, and a scene without a generated asset renders the truthful
        # art placeholder inside the art surface.
        placeholders = page.locator(".elosern-placeholder").all_inner_texts()
        self.assertEqual(len(placeholders), 0, "no foundation placeholder remains")
        art_surface = page.locator(".elosern-art")
        self.assertEqual(art_surface.count(), 1, "art surface present")
        self.assertTrue(art_surface.is_visible())
        # The minimap surface renders (or gracefully reports unavailable) and
        # is no longer a placeholder.
        local_map_surface = page.locator(".elosern-local-map")
        self.assertEqual(local_map_surface.count(), 1, "local-map surface present")
        self.assertTrue(local_map_surface.is_visible())

        resources = page.locator(".resource-value").all_inner_texts()
        self.assertEqual(len(resources), 3, "hp, mp, sp resource rows")
        for value in resources:
            current, maximum = value.split(" / ")
            self.assertTrue(current.isdigit(), f"current not numeric: {current!r}")
            self.assertTrue(maximum.isdigit(), f"maximum not numeric: {maximum!r}")

        header_conn = page.locator(".header-conn").inner_text()
        self.assertEqual(header_conn, "已連線")

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_keyboard_drawer_open_send_cancel_and_focus_restoration(self):
        page = self.logged_in_page()
        narrative_before = page.locator(".elosern-narrative").inner_text()

        page.evaluate("document.getElementById('action-dock').focus()")
        page.keyboard.press("/")
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        self.assertTrue(page.evaluate("Elosern.ui.isDrawerOpen()"))

        page.keyboard.type("look")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "() => !Elosern.ui.isDrawerOpen() && "
            "document.activeElement === document.getElementById('action-dock')"
        )
        page.wait_for_function(
            "(n) => document.querySelector('.elosern-narrative').innerText.length > n",
            arg=narrative_before.__len__(),
        )
        narrative_after = page.locator(".elosern-narrative").inner_text()
        self.assertNotEqual(
            narrative_after, narrative_before, "drawer send produced no narrative"
        )

        # Cancel path: reopen and Escape must not send anything.
        page.evaluate("document.getElementById('action-dock').focus()")
        page.keyboard.press("/")
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        page.keyboard.type("look")
        narrative_before_cancel = page.locator(".elosern-narrative").inner_text()
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !Elosern.ui.isDrawerOpen() && "
            "document.activeElement === document.getElementById('action-dock')"
        )
        self.assertEqual(
            page.locator(".elosern-narrative").inner_text(),
            narrative_before_cancel,
            "Escape must not send drawer text",
        )

    @covers_requirement(
        "webclient-desktop-shell::narrative-output-remains-the-authoritative-text-surface"
    )
    def test_scrollback_unread_behavior(self):
        page = self.logged_in_page()
        narrative = page.locator(".elosern-narrative")

        # Guarantee overflow so the narrative can be scrolled up.
        page.evaluate(
            "() => { for (let i = 0; i < 80; i++) { "
            "Elosern.goldenlayout.onText(['filler line ' + i], {}); } }"
        )
        page.wait_for_timeout(300)
        page.evaluate(
            "() => { const el = document.querySelector('.elosern-narrative'); "
            "el.scrollTop = 0; }"
        )
        page.wait_for_timeout(100)
        scroll_top = page.evaluate(
            "() => document.querySelector('.elosern-narrative').scrollTop"
        )
        self.assertEqual(scroll_top, 0)

        page.evaluate(
            "() => Elosern.goldenlayout.onText(['unread probe line'], {})"
        )
        page.wait_for_function(
            "() => (document.getElementById('narrative-unread').textContent || '')"
            ".indexOf('未讀') !== -1"
        )
        unread = page.locator("#narrative-unread").inner_text()
        self.assertRegex(unread, r"未讀 \d+")

        # The viewport must not have been forced to the bottom.
        scroll_top_after = page.evaluate(
            "() => document.querySelector('.elosern-narrative').scrollTop"
        )
        self.assertEqual(scroll_top_after, 0)

        # Scrolling to the bottom clears the unread marker.
        page.evaluate(
            "() => { const el = document.querySelector('.elosern-narrative'); "
            "el.scrollTop = el.scrollHeight; }"
        )
        page.wait_for_function(
            "() => (document.getElementById('narrative-unread').textContent || '')"
            " === ''"
        )
        self.assertEqual(page.locator("#narrative-unread").inner_text(), "")

    @covers_requirement(
        "webclient-status-presentation::server-time-and-location-are-read-only-presentation-data"
    )
    def test_header_shows_mode_and_server_time(self):
        page = self.logged_in_page()
        state = store_state(page)
        self.assertEqual(state["mode"], "exploration")
        self.assertEqual(page.locator(".header-mode").inner_text(), "模式：exploration")
        self.assertIsNotNone(state["serverTime"])


if __name__ == "__main__":
    import unittest

    unittest.main()
