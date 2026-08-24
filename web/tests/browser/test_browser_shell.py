"""Shell acceptance tests (section 6.5) at both supported desktop viewports."""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    sent_action_count,
    snapshot_envelope,
    store_state,
    valid_local_map_panel,
    wait_for_narrative_settled,
    wait_for_store_state,
)

REQUIRED_SURFACES = (
    '[data-testid="topbar"]',
    '[data-testid="narrative-feed"]',
    '[data-testid="command-drawer"]',
)


def _wait_field_focused(page, timeout=30000):
    """Gate on the drawer's ``#inputfield`` being focused (after ``/`` or entry click)."""
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": "#inputfield",
            "predicate": (
                "() => document.activeElement === "
                "document.getElementById('inputfield')"
            ),
            "description": "#inputfield focused",
        },
        timeout=timeout,
    )


def _wait_drawer_closed_dock_focused(page, timeout=30000):
    """Gate on the command drawer being closed and the action dock holding focus."""
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": "#action-dock",
            "predicate": (
                "() => { const d = document.querySelector('[data-testid=\"command-drawer\"]');"
                " const open = d && d.getAttribute('data-open') === 'true';"
                " const dock = document.getElementById('action-dock');"
                " return !open && dock && "
                "(document.activeElement === dock || "
                "(document.activeElement && dock.contains(document.activeElement))); }"
            ),
            "description": "command-drawer closed and #action-dock focused",
        },
        timeout=timeout,
    )


def _wait_narrative_grew(page, before_len, timeout=30000):
    """Gate on the narrative feed's text length exceeding a previous length."""
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": '[data-testid="narrative-feed"]',
            "predicate": (
                "() => { const n = document.querySelector('[data-testid=\"narrative-feed\"]');"
                " return n && n.innerText.length > %d; }" % before_len
            ),
            "description": "narrative feed text grew past the previous length",
        },
        timeout=timeout,
    )


def _wait_unread_count_nonzero(page, timeout=30000):
    """Gate on the unread marker's ``data-count`` becoming non-zero."""
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": "#narrative-unread",
            "predicate": (
                "() => document.getElementById('narrative-unread')"
                ".getAttribute('data-count') !== '0'"
            ),
            "description": "narrative-unread count non-zero",
        },
        timeout=timeout,
    )


def _wait_unread_count_zero(page, timeout=30000):
    """Gate on the unread marker's ``data-count`` clearing to zero."""
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": "#narrative-unread",
            "predicate": (
                "() => document.getElementById('narrative-unread')"
                ".getAttribute('data-count') === '0'"
            ),
            "description": "narrative-unread count cleared to zero",
        },
        timeout=timeout,
    )


def _append_narrative_fillers(page, count=80):
    """Seed the store's narrative with server-text filler lines (the scroll-keep tests need overflow)."""
    page.evaluate(
        "(count) => { const store = window.__elosernBridge.store;"
        " for (let i = 0; i < count; i++) { store.appendText('out', 'filler line ' + i); } }",
        count,
    )


class ShellAcceptanceTest(BrowserAcceptanceTest):
    """Every required surface at 1440x900 and 1280x720, plus keyboard journeys."""

    def assert_surfaces_visible(self, page):
        surfaces_js = ", ".join(repr(s) for s in REQUIRED_SURFACES)
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": REQUIRED_SURFACES[0],
                "predicate": (
                    "() => { const sels = [" + surfaces_js + "]; "
                    "for (const sel of sels) { if (!document.querySelector(sel)) { return false; } } "
                    "return true; }"
                ),
                "description": "guaranteed shell surfaces rendered",
            },
        )
        for selector in REQUIRED_SURFACES:
            locator = page.locator(selector)
            self.assertEqual(locator.count(), 1, f"missing surface {selector}")
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
        art_surface = page.locator(".art-panel")
        self.assertEqual(art_surface.count(), 1, "art surface present")
        self.assertTrue(art_surface.is_visible())
        # The minimap surface renders (or gracefully reports unavailable) and
        # is no longer a placeholder.
        local_map_surface = page.locator(".local-map")
        self.assertEqual(local_map_surface.count(), 1, "local-map surface present")
        self.assertTrue(local_map_surface.is_visible())

        resources = page.locator(".status-gauge__value").all_inner_texts()
        self.assertEqual(len(resources), 3, "hp, mp, sp resource rows")
        for value in resources:
            current, maximum = value.split(" / ")
            self.assertTrue(current.isdigit(), f"current not numeric: {current!r}")
            self.assertTrue(maximum.isdigit(), f"maximum not numeric: {maximum!r}")

        # The mockup gauge bars complement the mandated numeric text.
        bars = page.locator(".status-gauge__bar").all_inner_texts()
        self.assertEqual(len(bars), 3, "hp, mp, sp gauge bars")

        header_conn = page.locator(".meta-conn").inner_text()
        self.assertIn("已連線", header_conn)

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_keyboard_drawer_open_send_cancel_and_focus_restoration(self):
        page = self.logged_in_page()
        narrative_before = page.locator('[data-testid="narrative-feed"]').inner_text()

        # Open the drawer with `/` and send an ordinary command. The field
        # clears, the drawer stays open, and focus remains in the field so
        # consecutive commands need no pointer interaction.
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))

        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_for_narrative_settled(page, narrative_before.__len__())
        # Focus retained in the field, drawer still open, field cleared.
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))
        self.assertTrue(
            page.evaluate(
                "document.activeElement === document.getElementById('inputfield')"
            )
        )
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"), ""
        )
        narrative_after = page.locator('[data-testid="narrative-feed"]').inner_text()
        self.assertNotEqual(
            narrative_after, narrative_before, "drawer send produced no narrative"
        )

        # A second command can be sent with no pointer interaction.
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_for_narrative_settled(page, narrative_after.__len__())
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))
        self.assertTrue(
            page.evaluate(
                "document.activeElement === document.getElementById('inputfield')"
            )
        )

        # Cancel path: reopen, type, and Escape must not send anything; the
        # drawer closes and action-dock focus is restored (the action dock
        # forwards focus to the mounted listbox row container).
        page.keyboard.press("Escape")
        _wait_drawer_closed_dock_focused(page)
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)
        page.keyboard.type("look")
        narrative_before_cancel = page.locator('[data-testid="narrative-feed"]').inner_text()
        page.keyboard.press("Escape")
        _wait_drawer_closed_dock_focused(page)
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"]').inner_text(),
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
        narrative_before = page.locator('[data-testid="narrative-feed"]').inner_text()

        # A real room look through the server; the narrative must grow with
        # the room's prose. The *visible text* must never show element or
        # entity source characters (the DOM may legitimately contain rendered
        # span elements -- that is the pipeline working).
        page.evaluate("Evennia.msg('text', ['look'], {})")
        _wait_narrative_grew(page, narrative_before.__len__())
        page.wait_for_timeout(300)
        narrative_text = page.locator('[data-testid="narrative-feed"]').inner_text()
        self.assertNotIn("&lt;", narrative_text)
        self.assertNotIn("&amp;", narrative_text)
        self.assertNotIn("<span", narrative_text)
        self.assertNotIn("</span>", narrative_text)

        # A converted colored line renders with a palette class, never as
        # markup source.
        page.evaluate(
            "() => window.__elosernBridge.store.appendText('out', '|r南大道|n|g 綠|n')"
        )
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => document.querySelectorAll("
                    "'[data-testid=\"narrative-feed\"] span[class*=\"color-\"]').length >= 2"
                ),
                "description": "colored palette spans rendered in the narrative feed",
            },
        )
        colored = page.locator('[data-testid="narrative-feed"] span[class*="color-"]')
        self.assertGreaterEqual(colored.count(), 2)
        for index in range(colored.count()):
            cls = colored.nth(index).get_attribute("class")
            self.assertRegex(cls, r"(?:^|\s)color-\d{3}(?:\s|$)")
        # The styled text is visible, not its source.
        text = page.locator('[data-testid="narrative-feed"]').inner_text()
        self.assertIn("南大道", text)
        self.assertNotIn("<span", text)

    @covers_requirement(
        "webclient-narrative-markup::the-narrative-palette-is-generated-with-a-contrast-floor-and-honors-reduced-motion"
    )
    def test_narrative_wide_row_soft_wraps_inside_the_pane(self):
        page = self.logged_in_page()
        # Baseline: the Vue SPA desktop shell itself may carry a small fixed
        # layout overflow; the wide row must not add to it.
        baseline_scroll = page.evaluate(
            "() => document.documentElement.scrollWidth - "
            "document.documentElement.clientWidth"
        )
        # A row wider than the narrative pane's content width soft-wraps
        # inside the pane: no clipping, no additional page-level scroll.
        wide = "X" * 400 + " 尾部"
        page.evaluate(
            "(text) => window.__elosernBridge.store.appendText('out', text)", wide
        )
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const outs = document.querySelectorAll("
                    "'[data-testid=\"narrative-feed\"] .out');"
                    " const last = outs[outs.length - 1];"
                    " return last && last.innerText.indexOf('尾部') !== -1; }"
                ),
                "description": "wide narrative row rendered in the feed",
            },
        )
        # The full text is present (nothing clipped from the DOM).
        text = page.locator('[data-testid="narrative-feed"] .out').last.inner_text()
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
        focus_action_dock(page)
        for _ in range(3):
            page.keyboard.press("ArrowDown")
        page.keyboard.press("ArrowUp")
        page.keyboard.press("Escape")
        page.keyboard.press("/")
        _wait_field_focused(page)
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
        narrative = page.locator('[data-testid="narrative-feed"]')

        # The marker is absent entirely while the count is zero.
        marker = page.locator("#narrative-unread")
        self.assertEqual(marker.count(), 1)
        self.assertEqual(marker.get_attribute("data-count"), "0")

        # Guarantee overflow so the narrative can be scrolled up.
        _append_narrative_fillers(page, 80)
        # Scroll to the top, then gate on the scroll actually reaching the top
        # (the feed uses smooth scrolling, so a fixed timeout can race the
        # animation and the at-bottom decision is captured mid-scroll).
        page.evaluate(
            "() => { document.querySelector('[data-testid=\"narrative-feed\"]').scrollTop = 0; }"
        )
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => document.querySelector('[data-testid=\"narrative-feed\"]').scrollTop === 0"
                ),
                "description": "narrative feed scrolled to the top",
            },
            timeout=30000,
        )
        scroll_top = page.evaluate(
            "() => document.querySelector('[data-testid=\"narrative-feed\"]').scrollTop"
        )
        self.assertEqual(scroll_top, 0)

        page.evaluate(
            "() => window.__elosernBridge.store.appendText('out', 'unread probe line')"
        )
        _wait_unread_count_nonzero(page)
        unread = page.locator("#narrative-unread .narrative-unread-button").inner_text()
        self.assertRegex(unread, r"↓ \d+ 則新訊息（點擊返回最新）")

        # The viewport must not have been forced to the bottom.
        scroll_top_after = page.evaluate(
            "() => document.querySelector('[data-testid=\"narrative-feed\"]').scrollTop"
        )
        self.assertEqual(scroll_top_after, 0)

        # Clicking the marker jumps to the bottom, clears the count, and hides
        # the marker.
        page.locator(".narrative-unread-button").click()
        _wait_unread_count_zero(page)
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
        _append_narrative_fillers(page, 80)
        page.evaluate(
            "() => { document.querySelector('[data-testid=\"narrative-feed\"]').scrollTop = 0; }"
        )
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => document.querySelector('[data-testid=\"narrative-feed\"]').scrollTop === 0"
                ),
                "description": "narrative feed scrolled to the top",
            },
            timeout=30000,
        )
        page.evaluate(
            "() => window.__elosernBridge.store.appendText('out', 'unread probe line')"
        )
        _wait_unread_count_nonzero(page)
        # Keyboard activation (Enter on the focused marker button) jumps to the
        # bottom and parks focus on the narrative pane, never a hidden element.
        page.locator(".narrative-unread-button").focus()
        page.keyboard.press("Enter")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => document.activeElement === "
                    "document.querySelector('[data-testid=\"narrative-feed\"]')"
                ),
                "description": "narrative feed holds focus",
            },
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
        header = page.locator('[data-testid="topbar"]')
        self.assertEqual(header.evaluate("el => el.classList.contains('connected')"), True)
        location = page.locator('[data-testid="topbar-location"]').inner_text()
        self.assertNotEqual(location, "位置：--", "location must be synced")
        self.assertTrue(location.strip())
        clock = page.locator('[data-testid="topbar-clock"]').inner_text()
        self.assertRegex(clock, r"\d+ 日 · \d{2}:\d{2}")
        conn = page.locator(".meta-conn").inner_text()
        self.assertIn("●", conn)
        self.assertIn("已連線", conn)
        self.assertEqual(page.locator(".header-mode").count(), 0, "no raw mode label")

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_pointer_focused_field_sends_on_enter(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        narrative_before = page.locator('[data-testid="narrative-feed"]').inner_text()

        # A pointer activation of the drawer's entry button opens and focuses
        # the field; Enter must send exactly one ordinary text message through
        # the single drawer-owned path, clear the field, and keep focus in it.
        page.locator(".drawer-entry").click()
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))
        _wait_field_focused(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        _wait_narrative_grew(page, narrative_before.__len__())
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
        narrative_before = page.locator('[data-testid="narrative-feed"]').inner_text()
        page.locator(".drawer-entry").click()
        _wait_field_focused(page)
        page.keyboard.type("first line")
        page.keyboard.press("Shift+Enter")
        page.keyboard.type("second line")
        page.keyboard.press("Enter")
        _wait_narrative_grew(page, narrative_before.__len__())
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
        focus_action_dock(page)
        cell_count = page.evaluate(
            "document.querySelectorAll('#action-dock [data-item-key]').length"
        )
        for _ in range(cell_count - 1):
            page.keyboard.press("ArrowRight")
        page.keyboard.press("Enter")  # Wait/休息
        page.keyboard.press("ArrowDown")  # 等待至正午
        page.keyboard.press("ArrowDown")  # 休息一段時間
        page.keyboard.press("Enter")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="exploration-rest-form"]',
                "predicate": (
                    "() => document.querySelector('[data-testid=\"exploration-rest-form\"]') !== null"
                ),
                "description": "rest form rendered",
            },
        )
        # Open the drawer through its entry button and send: the rest form's
        # capture-phase handler must yield, and the command travels as
        # ordinary text (never an explore.wait submission).
        page.locator(".drawer-entry").click()
        _wait_field_focused(page)
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
            _wait_field_focused(page)
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
            frame = dock.evaluate(
                """el => {
                  const style = getComputedStyle(el);
                  return { borderTop: style.borderTopColor,
                           background: style.backgroundColor };
                }"""
            )
            self.assertEqual(frame["borderTop"], "rgb(169, 50, 42)")
            guidance = page.locator('[data-testid="action-dock-guidance"]').inner_text()
            for keyword in ("方向鍵選擇", "Enter 確認", "Esc 返回", "/ 開啟指令"):
                self.assertIn(keyword, guidance)
            # The root is one equal-width row of grid cells with the mockup
            # chrome: focused cell = seal-red fill + leading glyph. The cell
            # count varies 5-7 with quest/inventory capability availability.
            cells = page.locator("#action-dock [data-item-key]")
            self.assertGreaterEqual(cells.count(), 5)
            self.assertLessEqual(cells.count(), 7)
            focused = page.locator("#action-dock .dock-menu-item--focused").first
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
            self.assertEqual(page.locator('[data-testid="exploration-detail"]').count(), 0)
            page.keyboard.press("Enter")  # Move
            wait_for_store_state(
                page,
                lambda s: bool(s.get("connected")),
                dom_readiness={
                    "selector": '[data-testid="exploration-detail"]',
                    "predicate": (
                        "() => document.querySelector('[data-testid=\"exploration-detail\"]') !== null"
                    ),
                    "description": "exploration detail pane rendered",
                },
            )
            detail = page.locator('[data-testid="exploration-detail"]')
            self.assertTrue(detail.is_visible())
            self.assertEqual(
                page.evaluate(
                    "() => { const el = document.querySelector('[data-testid=\"dock-menu\"]');"
                    " return el && getComputedStyle(el).display === 'grid'; }"
                ),
                True,
                "submenu item lists render as a CSS grid",
            )
            # The detail pane names the focused item's next key action.
            page.evaluate("window.__elosernBridge.router.focusItemByKey('back')")
            page.wait_for_timeout(120)
            self.assertIn(
                "返回上一層",
                detail.inner_text(),
                "the detail pane names the back cell's next key action",
            )

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable"
    )
    def test_stage_anchors_do_not_intersect_at_both_viewports(self):
        """H1 group 8.3: the full-bleed stage's named HUD anchors must not overlap.

        The stage anchors (``hud-left``, ``hud-right``, ``feed``, ``dock``,
        ``command-line``) are absolutely positioned; any pair of *visible*
        anchors sharing a non-zero-area intersection would visually collide,
        breaking the "surfaces remain usable" contract. Verified at both
        supported desktop viewports.
        """
        for viewport in ((1440, 900), (1280, 720)):
            page = self.logged_in_page(viewport)
            overlap = page.evaluate(
                """() => {
                  const testids = ["anchor-hud-left", "anchor-hud-right", "anchor-feed",
                                   "anchor-dock", "anchor-command-line"];
                  const anchors = testids
                    .map((t) => {
                      const el = document.querySelector('[data-testid="' + t + '"]');
                      if (!el) { return null; }
                      const r = el.getBoundingClientRect();
                      const visible = r.width > 0 && r.height > 0 && el.offsetParent !== null;
                      return { testid: t, r: r, visible: visible };
                    })
                    .filter(Boolean)
                    .filter((a) => a.visible);
                  const intersecting = [];
                  for (let i = 0; i < anchors.length; i++) {
                    for (let j = i + 1; j < anchors.length; j++) {
                      const a = anchors[i].r, b = anchors[j].r;
                      const xOverlap = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
                      const yOverlap = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
                      if (xOverlap > 0 && yOverlap > 0) {
                        intersecting.push(anchors[i].testid + " <-> " + anchors[j].testid);
                      }
                    }
                  }
                  return { intersecting: intersecting };
                }"""
            )
            self.assertEqual(
                overlap["intersecting"],
                [],
                f"stage anchors intersect at {viewport[0]}x{viewport[1]}: {overlap['intersecting']}",
            )

    @covers_requirement(
        "webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone"
    )
    def test_minimap_present_in_exploration_absent_in_combat(self):
        """H1 group 8.4: the minimap is visible in exploration and hidden in combat.

        The seeded exploration scene does not always carry a map-knowledge
        record, so the test injects a valid local_map panel through the
        wired reducer. The HUD mode-gating matrix (design D2) hides the
        minimap in combat (and creation) via ``display:none !important`` on
        ``data-elosern-mode``.
        """
        page = self.logged_in_page()
        state = store_state(page)

        # Exploration: inject an available local_map panel; the minimap renders.
        expl = page.evaluate(
            "(args) => window.__elosernBridge.store.receive("
            "args.generation, 'ui_snapshot', [args.envelope], {})",
            {
                "generation": state["generation"],
                "envelope": snapshot_envelope(
                    state["epoch"],
                    state["revision"] + 1,
                    {"local_map": valid_local_map_panel()},
                    mode="exploration",
                ),
            },
        )
        self.assertTrue(expl["accepted"], "the exploration snapshot was accepted")
        page.wait_for_timeout(150)
        lm = page.locator(".local-map")
        self.assertEqual(lm.count(), 1, "minimap renders in exploration mode")
        self.assertTrue(lm.is_visible(), "minimap is visible in exploration mode")

        # Combat: force combat mode; the minimap is hidden by the CSS mode-gate.
        state = store_state(page)
        combat = page.evaluate(
            "(args) => window.__elosernBridge.store.receive("
            "args.generation, 'ui_snapshot', [args.envelope], {})",
            {
                "generation": state["generation"],
                "envelope": snapshot_envelope(
                    state["epoch"],
                    state["revision"] + 1,
                    {"local_map": valid_local_map_panel()},
                    mode="combat",
                ),
            },
        )
        self.assertTrue(combat["accepted"], "the combat-mode snapshot was accepted")
        page.wait_for_timeout(150)
        lm = page.locator(".local-map")
        self.assertEqual(lm.count(), 1, "the minimap element remains in the DOM")
        hidden = page.evaluate(
            "() => { const el = document.querySelector('.local-map'); "
            "return el ? (el.offsetParent === null) : false; }"
        )
        self.assertTrue(hidden, "the minimap is hidden (display:none) in combat mode")

    @covers_requirement(
        "webclient-desktop-shell::narrative-output-remains-the-authoritative-text-surface"
    )
    def test_full_log_opens_in_one_action_and_escapes_with_focus_restoration(self):
        """H1 group 8.5: the full log is a one-action escape hatch.

        Clicking the caption card's `完整日誌` control opens the full-screen,
        scrollable view of the complete retained narrative. While open, focus
        is trapped in the overlay; pressing Escape closes it and focus is
        restored to the control that opened it (design D4).
        """
        page = self.logged_in_page()
        control = page.locator('[data-testid="narrative-fulllog-control"]')
        self.assertEqual(control.count(), 1, "the full-log control renders in the feed head")
        # One action: click the control and the full log must open.
        control.click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', timeout=15000)
        overlay = page.locator('[data-testid="fulllog-overlay"]')
        self.assertTrue(overlay.is_visible(), "the full log overlay is visible after one click")
        # While open, focus is trapped in the overlay.
        focused_overlay = page.evaluate(
            "() => { const o = document.querySelector('[data-testid=\"fulllog-overlay\"]'); "
            "const a = document.activeElement; return o && (o === a || (o && o.contains(a))); }"
        )
        self.assertTrue(focused_overlay, "focus is trapped in the full log overlay while open")
        # Escape closes the overlay and restores focus to the opener control.
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"fulllog-overlay\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            page.locator('[data-testid="fulllog-overlay"]').count(),
            0,
            "the full log overlay is removed after Escape",
        )
        focus_restored = page.evaluate(
            "() => { const c = document.querySelector('[data-testid=\"narrative-fulllog-control\"]'); "
            "const a = document.activeElement; return c && c === a; }"
        )
        self.assertTrue(focus_restored, "focus is restored to the control that opened the full log")



if __name__ == "__main__":
    import unittest

    unittest.main()
