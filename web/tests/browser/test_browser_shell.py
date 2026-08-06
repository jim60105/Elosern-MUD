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

        # Open the drawer with `/` and send an ordinary command. The field
        # clears, the drawer stays open, and focus remains in the field so
        # consecutive commands need no pointer interaction.
        page.evaluate("document.getElementById('action-dock').focus()")
        page.keyboard.press("/")
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        self.assertTrue(page.evaluate("Elosern.drawer.isOpen()"))

        page.keyboard.type("look")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "(n) => document.querySelector('.elosern-narrative').innerText.length > n",
            arg=narrative_before.__len__(),
        )
        # Focus retained in the field, drawer still open, field cleared.
        self.assertTrue(page.evaluate("Elosern.drawer.isOpen()"))
        self.assertTrue(
            page.evaluate(
                "document.activeElement === document.getElementById('inputfield')"
            )
        )
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"), ""
        )
        narrative_after = page.locator(".elosern-narrative").inner_text()
        self.assertNotEqual(
            narrative_after, narrative_before, "drawer send produced no narrative"
        )

        # A second command can be sent with no pointer interaction.
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "(n) => document.querySelector('.elosern-narrative').innerText.length > n",
            arg=narrative_after.__len__(),
        )
        self.assertTrue(page.evaluate("Elosern.drawer.isOpen()"))
        self.assertTrue(
            page.evaluate(
                "document.activeElement === document.getElementById('inputfield')"
            )
        )

        # Cancel path: reopen, type, and Escape must not send anything; the
        # drawer closes and action-dock focus is restored (the action dock
        # forwards focus to the mounted listbox row container).
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !Elosern.drawer.isOpen() && (() => {"
            "  const dock = document.getElementById('action-dock');"
            "  return document.activeElement === dock || "
            "    (document.activeElement && dock.contains(document.activeElement));"
            "})()"
        )
        page.evaluate("document.getElementById('action-dock').focus()")
        page.keyboard.press("/")
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        page.keyboard.type("look")
        narrative_before_cancel = page.locator(".elosern-narrative").inner_text()
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !Elosern.drawer.isOpen() && (() => {"
            "  const dock = document.getElementById('action-dock');"
            "  return document.activeElement === dock || "
            "    (document.activeElement && dock.contains(document.activeElement));"
            "})()"
        )
        self.assertEqual(
            page.locator(".elosern-narrative").inner_text(),
            narrative_before_cancel,
            "Escape must not send drawer text",
        )

    @covers_requirement(
        "webclient-narrative-markup::the-narrative-renders-the-transport-stream-through-a-strict-allowlist-markup-pipeline"
    )
    @covers_requirement(
        "webclient-narrative-markup::the-narrative-palette-is-generated-with-a-contrast-floor-and-honors-reduced-motion"
    )
    def test_narrative_renders_styled_prose_not_markup_source(self):
        page = self.logged_in_page()
        narrative_before = page.locator(".elosern-narrative").inner_text()

        # A real room look through the server; the narrative must grow with
        # the room's prose. The *visible text* must never show element or
        # entity source characters (the DOM may legitimately contain rendered
        # span elements -- that is the pipeline working).
        page.evaluate("Evennia.msg('text', ['look'], {})")
        page.wait_for_function(
            "(before) => document.querySelector('.elosern-narrative')"
            ".innerText.length > before",
            arg=narrative_before.__len__(),
        )
        page.wait_for_timeout(300)
        narrative_text = page.locator(".elosern-narrative").inner_text()
        self.assertNotIn("&lt;", narrative_text)
        self.assertNotIn("&amp;", narrative_text)
        self.assertNotIn("<span", narrative_text)
        self.assertNotIn("</span>", narrative_text)

        # A converted colored line renders with a palette class, never as
        # markup source.
        page.evaluate(
            "() => Elosern.goldenlayout.onText("
            "['|r南大道|n|g 綠|n'], {})"
        )
        page.wait_for_function(
            "() => document.querySelectorAll("
            "'.elosern-narrative span[class*=\"color-\"]').length >= 2"
        )
        colored = page.locator(".elosern-narrative span[class*='color-']")
        self.assertGreaterEqual(colored.count(), 2)
        for index in range(colored.count()):
            cls = colored.nth(index).get_attribute("class")
            self.assertRegex(cls, r"(?:^|\s)color-\d{3}(?:\s|$)")
        # The styled text is visible, not its source.
        text = page.locator(".elosern-narrative").inner_text()
        self.assertIn("南大道", text)
        self.assertNotIn("<span", text)

    @covers_requirement(
        "webclient-narrative-markup::the-narrative-palette-is-generated-with-a-contrast-floor-and-honors-reduced-motion"
    )
    def test_narrative_wide_row_soft_wraps_inside_the_pane(self):
        page = self.logged_in_page()
        # Baseline: the GoldenLayout shell itself may carry a small fixed
        # layout overflow; the wide row must not add to it.
        baseline_scroll = page.evaluate(
            "() => document.documentElement.scrollWidth - "
            "document.documentElement.clientWidth"
        )
        # A row wider than the narrative pane's content width soft-wraps
        # inside the pane: no clipping, no additional page-level scroll.
        wide = "X" * 400 + " 尾部"
        page.evaluate(
            "(text) => Elosern.goldenlayout.onText([text], {})", wide
        )
        page.wait_for_function(
            "(text) => {"
            "  const outs = document.querySelectorAll('.elosern-narrative .out');"
            "  const last = outs[outs.length - 1];"
            "  return last && last.innerText.indexOf('尾部') !== -1;"
            "}",
            arg=wide,
        )
        # The full text is present (nothing clipped from the DOM).
        text = page.locator(".elosern-narrative .out").last.inner_text()
        self.assertIn("尾部", text)
        # The wide row did not widen the page.
        horizontal_scroll = page.evaluate(
            "() => document.documentElement.scrollWidth - "
            "document.documentElement.clientWidth"
        )
        self.assertEqual(
            horizontal_scroll,
            baseline_scroll,
            "a wide narrative row must soft-wrap without widening the page",
        )

    @covers_requirement(
        "webclient-pointer-activation::keyboard-input-is-dispatched-through-the-webclient-plugin-contract"
    )
    def test_keydown_noise_is_gone_during_keyboard_navigation(self):
        page = self.logged_in_page()
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg.text))

        # Navigate the action dock with the keyboard: arrows, Enter, Escape,
        # and drawer typing must never report an unhandled keydown.
        page.evaluate("document.getElementById('action-dock').focus()")
        for _ in range(3):
            page.keyboard.press("ArrowDown")
        page.keyboard.press("ArrowUp")
        page.keyboard.press("Escape")
        page.keyboard.press("/")
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)

        noise = [
            message
            for message in console_messages
            if "NO plugin handled this Keydown" in message
        ]
        self.assertEqual(
            noise,
            [],
            "the plugin must claim exactly the events its router consumed",
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
