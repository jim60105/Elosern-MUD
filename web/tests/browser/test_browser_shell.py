"""Shell acceptance tests (section 6.5) at both supported desktop viewports."""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    sent_action_count,
    store_state,
    wait_for_narrative_settled,
)

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
            if selector != "#inputfield":
                self.assertTrue(locator.is_visible(), f"{selector} is not visible")
        # The command drawer defaults to closed: the input row exists in the
        # DOM but is hidden behind the actionable entry button (D2).
        self.assertFalse(
            page.locator("#inputfield").is_visible(),
            "the drawer input row must be hidden by default",
        )
        entry = page.locator(".drawer-entry")
        self.assertEqual(entry.count(), 1)
        self.assertTrue(entry.is_visible(), "the entry button is visible by default")
        self.assertEqual(entry.get_attribute("aria-expanded"), "false")

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

        # The mockup gauge bars complement the mandated numeric text.
        bars = page.locator(".resource-bar").all_inner_texts()
        self.assertEqual(len(bars), 3, "hp, mp, sp gauge bars")

        header_conn = page.locator(".header-conn").inner_text()
        self.assertIn("已連線", header_conn)

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
        wait_for_narrative_settled(page, narrative_before.__len__())
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
        wait_for_narrative_settled(page, narrative_after.__len__())
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

        # The marker is absent entirely while the count is zero.
        marker = page.locator("#narrative-unread")
        self.assertEqual(marker.count(), 1)
        self.assertEqual(marker.get_attribute("data-count"), "0")

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
            "() => document.getElementById('narrative-unread')"
            ".getAttribute('data-count') !== '0'"
        )
        unread = page.locator("#narrative-unread .narrative-unread-button").inner_text()
        self.assertRegex(unread, r"↓ \d+ 則新訊息（點擊返回最新）")

        # The viewport must not have been forced to the bottom.
        scroll_top_after = page.evaluate(
            "() => document.querySelector('.elosern-narrative').scrollTop"
        )
        self.assertEqual(scroll_top_after, 0)

        # Clicking the marker jumps to the bottom, clears the count, and hides
        # the marker.
        page.locator(".narrative-unread-button").click()
        page.wait_for_function(
            "() => document.getElementById('narrative-unread')"
            ".getAttribute('data-count') === '0'"
        )
        self.assertEqual(
            page.locator("#narrative-unread").get_attribute("data-count"),
            "0",
        )

    @covers_requirement(
        "webclient-desktop-shell::narrative-output-remains-the-authoritative-text-surface"
    )
    def test_unread_marker_keyboard_activation_moves_focus_to_narrative(self):
        page = self.logged_in_page()
        # Guarantee overflow and scroll up so an unread count accumulates.
        page.evaluate(
            "() => { for (let i = 0; i < 80; i++) { "
            "Elosern.goldenlayout.onText(['filler line ' + i], {}); } }"
        )
        page.wait_for_timeout(300)
        page.evaluate(
            "() => { const el = document.querySelector('.elosern-narrative'); "
            "el.scrollTop = 0; }"
        )
        page.evaluate(
            "() => Elosern.goldenlayout.onText(['unread probe line'], {})"
        )
        page.wait_for_function(
            "() => document.getElementById('narrative-unread')"
            ".getAttribute('data-count') !== '0'"
        )
        # Keyboard activation (Enter on the focused marker button) jumps to the
        # bottom and parks focus on the narrative pane, never a hidden element.
        page.locator(".narrative-unread-button").focus()
        page.keyboard.press("Enter")
        page.wait_for_function(
            "() => document.activeElement === "
            "document.querySelector('.elosern-narrative')"
        )
        self.assertEqual(
            page.locator("#narrative-unread").get_attribute("data-count"),
            "0",
        )

    @covers_requirement(
        "webclient-status-presentation::server-time-and-location-are-read-only-presentation-data",
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable",
    )
    def test_header_shows_location_time_and_connection_dot(self):
        page = self.logged_in_page()
        state = store_state(page)
        self.assertEqual(state["mode"], "exploration")
        self.assertIsNotNone(state["serverTime"])

        # The header identifies location, world time, and the connected state;
        # the raw mode label is gone (the dock content identifies the mode).
        header = page.locator(".elosern-header")
        self.assertEqual(header.evaluate("el => el.classList.contains('connected')"), True)
        location = page.locator(".header-location").inner_text()
        self.assertNotEqual(location, "位置：--", "location must be synced")
        self.assertTrue(location.strip())
        clock = page.locator(".header-clock").inner_text()
        self.assertRegex(clock, r"\d+ 日 · \d{2}:\d{2}")
        conn = page.locator(".header-conn").inner_text()
        self.assertIn("●", conn)
        self.assertIn("已連線", conn)
        self.assertEqual(page.locator(".header-mode").count(), 0, "no raw mode label")

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_pointer_focused_field_sends_on_enter(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        narrative_before = page.locator(".elosern-narrative").inner_text()

        # A pointer activation of the drawer's entry button opens and focuses
        # the field; Enter must send exactly one ordinary text message through
        # the single drawer-owned path, clear the field, and keep focus in it.
        page.locator(".drawer-entry").click()
        self.assertTrue(page.evaluate("Elosern.drawer.isOpen()"))
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "(n) => document.querySelector('.elosern-narrative').innerText.length > n",
            arg=narrative_before.__len__(),
        )
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            "",
            "the field must clear after a pointer-focused send",
        )
        self.assertTrue(
            page.evaluate(
                "document.activeElement === document.getElementById('inputfield')"
            ),
            "focus stays in the field after an input-area send",
        )
        sends = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "text"
        ]
        self.assertEqual(len(sends), 1, "exactly one text message is sent")
        self.assertTrue(any("look" in str(item) for item in sends))

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_shift_enter_in_field_inserts_newline_without_sending(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        narrative_before = page.locator(".elosern-narrative").inner_text()
        page.locator(".drawer-entry").click()
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        page.keyboard.type("first line")
        page.keyboard.press("Shift+Enter")
        page.keyboard.type("second line")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "(n) => document.querySelector('.elosern-narrative').innerText.length > n",
            arg=narrative_before.__len__(),
        )
        sends = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "text"
        ]
        self.assertEqual(len(sends), 1, "Shift+Enter must not send")
        self.assertIn("first line\nsecond line", str(sends[0]))

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_open_rest_form_never_swallows_drawer_field_enter(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # The Wait/休息 entry is always the last root cell (5-7 cells
        # depending on quest/inventory capability availability).
        page.evaluate("document.getElementById('action-dock').focus()")
        cell_count = page.evaluate(
            "document.querySelectorAll('#action-dock [data-item-key]').length"
        )
        for _ in range(cell_count - 1):
            page.keyboard.press("ArrowRight")
        page.keyboard.press("Enter")  # Wait/休息
        page.keyboard.press("ArrowDown")  # 等待至正午
        page.keyboard.press("ArrowDown")  # 休息一段時間
        page.keyboard.press("Enter")
        page.wait_for_function(
            "() => document.getElementById('exploration-rest-form') !== null"
        )
        # Open the drawer through its entry button and send: the rest form's
        # capture-phase handler must yield, and the command travels as
        # ordinary text (never an explore.wait submission).
        page.locator(".drawer-entry").click()
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        self.assertEqual(
            sent_action_count(page, "explore.wait"),
            0,
            "the rest form must not swallow the drawer send",
        )
        sends = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "text"
        ]
        self.assertTrue(
            any("look" in str(item) for item in sends),
            "the command must travel through the text transport",
        )

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_drawer_field_button_alignment_at_both_viewports(self):
        for viewport in ((1440, 900), (1280, 720)):
            page = self.logged_in_page(viewport)
            # The field is hidden until the drawer opens; open it through the
            # entry button before measuring the field/button alignment.
            page.locator(".drawer-entry").click()
            page.wait_for_function(
                "() => document.activeElement === document.getElementById('inputfield')"
            )
            page.wait_for_timeout(200)
            geometry = page.evaluate(
                """() => {
                  const field = document.getElementById('inputfield');
                  const button = document.querySelector('.inputsend');
                  const wrapper = document.querySelector('.inputfieldwrapper');
                  const rect = (el) => {
                    const r = el.getBoundingClientRect();
                    return { left: r.left, right: r.right, top: r.top, bottom: r.bottom };
                  };
                  return { field: rect(field), button: rect(button), wrapper: rect(wrapper) };
                }"""
            )
            for edge in ("top", "bottom"):
                self.assertLessEqual(
                    abs(geometry["button"][edge] - geometry["field"][edge]),
                    1.0,
                    f"{edge} edges must align at {viewport}",
                )
            # The button sits flush at the wrapper's right edge and directly
            # abuts the field (the 0.25rem ragged gap is gone), and neither
            # child extends outside the wrapper.
            self.assertLessEqual(
                abs(geometry["button"]["right"] - geometry["wrapper"]["right"]),
                1.0,
                f"the button must sit flush in the wrapper at {viewport}",
            )
            self.assertLessEqual(
                abs(geometry["field"]["right"] - geometry["button"]["left"]),
                1.0,
                f"the field must abut the button without a gap at {viewport}",
            )
            self.assertLessEqual(
                geometry["field"]["left"],
                geometry["wrapper"]["right"],
                "the field must stay inside the wrapper",
            )
            self.assertGreaterEqual(
                geometry["field"]["left"],
                geometry["wrapper"]["left"],
                "the field must not extend outside the wrapper",
            )
            self.assertLessEqual(
                geometry["button"]["right"],
                geometry["wrapper"]["right"] + 1.0,
                "the button must stay inside the wrapper",
            )

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable",
        "webclient-desktop-shell::theme-and-controls-remain-accessible",
    )
    def test_action_dock_renders_the_mockup_command_surface(self):
        for viewport in ((1440, 900), (1280, 720)):
            page = self.logged_in_page(viewport)
            dock = page.locator("#action-dock")
            self.assertTrue(dock.is_visible())
            # Seal-red frame + guidance line naming the shortcuts.
            frame = page.evaluate(
                """() => {
                  const style = getComputedStyle(document.getElementById('action-dock'));
                  return { borderTop: style.borderTopColor,
                           background: style.backgroundColor };
                }"""
            )
            self.assertEqual(frame["borderTop"], "rgb(169, 50, 42)")
            guidance = page.locator("#action-dock-guidance").inner_text()
            for keyword in ("方向鍵選擇", "Enter 確認", "Esc 返回", "/ 開啟指令"):
                self.assertIn(keyword, guidance)
            # The root is one equal-width row of grid cells with the mockup
            # chrome: focused cell = seal-red fill + leading glyph. The cell
            # count varies 5-7 with quest/inventory capability availability.
            cells = page.locator("#action-dock [data-item-key]")
            self.assertGreaterEqual(cells.count(), 5)
            self.assertLessEqual(cells.count(), 7)
            focused = page.locator("#action-dock .dock-row.focused").first
            self.assertEqual(
                focused.evaluate(
                    "el => getComputedStyle(el).backgroundColor"
                ),
                "rgb(169, 50, 42)",
                "the focused cell carries the seal-red fill",
            )
            self.assertTrue(
                "▶" in focused.evaluate("el => getComputedStyle(el, '::before').content"),
                "the focused cell carries the leading glyph",
            )
            # The mockup root draws no visible detail pane; opening a submenu
            # reveals the grid + detail split.
            self.assertEqual(page.locator(".exploration-detail").count(), 0)
            page.keyboard.press("Enter")  # Move
            page.wait_for_function(
                "() => document.getElementById('exploration-detail') !== null"
            )
            detail = page.locator("#exploration-detail")
            self.assertTrue(detail.is_visible())
            self.assertEqual(
                page.evaluate(
                    "document.querySelector('.exploration-menu')"
                    ".classList.contains('dock-grid')"
                ),
                True,
                "submenu item lists render as a CSS grid",
            )
            # The detail pane names the focused item's next key action.
            page.evaluate("Elosern.keyboard.focusItemByKey('back')")
            page.wait_for_timeout(120)
            self.assertIn(
                "返回上一層",
                detail.inner_text(),
                "the detail pane names the back cell's next key action",
            )


if __name__ == "__main__":
    import unittest

    unittest.main()
