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
    valid_art_panel,
    valid_character_panel,
    valid_local_map_panel,
    valid_status_panel,
    wait_for_narrative_settled,
    wait_for_store_state,
)

REQUIRED_SURFACES = (
    '[data-testid="topbar"]',
    '[data-testid="narrative-feed"]',
    '[data-testid="command-line"]',
)


def _wait_field_focused(page, timeout=30000):
    """Gate on the command field ``#inputfield`` being focused (after ``/``)."""
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


def _wait_command_field_released(page, timeout=30000):
    """Gate on the action dock holding focus after the command field's Escape.

    H5 (webclient-hud-05-overlays-and-command-line): the command line is
    permanently present, so the release path is focus restoration to
    ``#action-dock`` — not a surface close (the field is never closed).
    """
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": "#action-dock",
            "predicate": (
                "() => { const d = document.querySelector('[data-testid=\"command-line\"]');"
                " const dock = document.getElementById('action-dock');"
                " return d && dock && "
                "(document.activeElement === dock || "
                "(document.activeElement && dock.contains(document.activeElement))); }"
            ),
            "description": "command field released: #action-dock focused, command line still present",
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
        # H5 (task 8.6): the command line is permanently present — the input
        # field is in the DOM, visible and focusable with no opening action:
        # no entry control, no `aria-expanded` state, no closed state.
        self.assertEqual(page.locator('#inputfield').count(), 1)
        self.assertTrue(page.locator('#inputfield').is_visible(), "the command field is visible")
        self.assertEqual(page.locator('.drawer-entry').count(), 0, "no entry control")
        self.assertEqual(page.locator('[aria-expanded]').count(), 0, "no element reports aria-expanded")

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
    @covers_requirement(
        "webclient-contextual-hud::vitals-pair-an-icon-a-label-and-numerals-with-a-trailing-damage-bar",
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
        local_map_surface = page.locator('[data-testid="local-map"]')
        self.assertEqual(local_map_surface.count(), 1, "local-map surface present")
        self.assertTrue(local_map_surface.is_visible())

        # H2 re-map: the preserved `status-panel__gauge-value--<key>` hooks
        # now live on the vitals island's rows (the old `.status-gauge__value`
        # class-literal selector is retired in favour of the data-testid hooks).
        for key in ("hp", "mp", "sp"):
            value = page.locator(
                f'[data-testid="status-panel__gauge-value--{key}"]'
            ).inner_text()
            current, maximum = value.split(" / ")
            self.assertTrue(current.isdigit(), f"current not numeric: {current!r}")
            self.assertTrue(maximum.isdigit(), f"maximum not numeric: {maximum!r}")

        # The mockup gauge tracks complement the mandated numeric text.
        for key in ("hp", "mp", "sp"):
            self.assertEqual(
                page.locator(f'[data-testid="status-panel__gauge--{key}"]').count(),
                1,
                f"{key} gauge row present",
            )

        header_conn = page.locator(".meta-conn").inner_text()
        self.assertIn("已連線", header_conn)

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_keyboard_field_focus_send_cancel_and_focus_restoration(self):
        page = self.logged_in_page()
        narrative_before = page.locator('[data-testid="narrative-feed"]').inner_text()

        # H5: the command line is permanently present — `/` focuses the
        # always-present field (no opening action). Send an ordinary command:
        # the field clears and focus stays in the field, so consecutive
        # commands need no pointer interaction.
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()", "the command line is present"))

        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_for_narrative_settled(page, narrative_before.__len__())
        # Focus retained in the field, command line still present, field cleared.
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"))
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
            narrative_after, narrative_before, "command-line send produced no narrative"
        )

        # A second command can be sent with no pointer interaction.
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_for_narrative_settled(page, narrative_after.__len__())
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"))
        self.assertTrue(
            page.evaluate(
                "document.activeElement === document.getElementById('inputfield')"
            )
        )

        # Cancel path: Escape from the focused field sends nothing and
        # restores action-dock focus; the command line itself is never
        # closed (it is permanently present, design D1).
        page.keyboard.press("Escape")
        _wait_command_field_released(page)
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)
        page.keyboard.type("look")
        narrative_before_cancel = page.locator('[data-testid="narrative-feed"]').inner_text()
        page.keyboard.press("Escape")
        _wait_command_field_released(page)
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"]').inner_text(),
            narrative_before_cancel,
            "Escape must not send command-line text",
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
        # and command-line typing must never report an unhandled keydown.
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
    @covers_requirement(
        "webclient-contextual-hud::the-narrative-is-a-bounded-caption-whose-complete-log-is-reachable-in-one-action"
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
                    "() => document.querySelector('[data-testid=\"narrative-feed\"]').scrollTop <= 8"
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

        # The viewport must not have been forced to the bottom. The feed uses
        # smooth scrolling + browser scroll-anchoring, so a line landing below
        # the fold can nudge the scroll position by a few px (reflow). The
        # "not forced to the bottom" contract is that it stays near the top;
        # a small offset is legitimate browser behavior, not a scroll-to-bottom.
        scroll_top_after = page.evaluate(
            "() => document.querySelector('[data-testid=\"narrative-feed\"]').scrollTop"
        )
        self.assertLess(
            scroll_top_after,
            10,
            "feed stayed near the top; not forced to the bottom",
        )

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
        # The feed stylesheet sets `scroll-behavior: smooth`, so a direct
        # `scrollTop = 0` triggers an animation that races the gate. Force an
        # instant scroll for this single assignment (the same override pattern
        # the feed's own `scrollToBottom` and the scrolled-away test use).
        page.evaluate(
            "() => { const f = document.querySelector('[data-testid=\"narrative-feed\'];"
            " const prev = f.style.scrollBehavior;"
            " f.style.scrollBehavior = 'auto';"
            " f.scrollTop = 0;"
            " f.style.scrollBehavior = prev; }"
        )
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => document.querySelector('[data-testid=\"narrative-feed\"]').scrollTop <= 8"
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

        # H5: the command line is permanently present — pointer activation
        # of the always-present field must send exactly one ordinary text
        # message through the single send path, clear the field, and keep
        # focus in it (the plugin contract reports no unhandled keydown).
        page.locator("#inputfield").click()
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
        # H5: the field is permanently present; focus it directly (no opening
        # action is needed — design D1).
        page.locator("#inputfield").click()
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
    def test_open_rest_form_never_swallows_command_line_enter(self):
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
        # H5: the command line is permanently present — focus the always-present
        # field and send; the rest form's capture-phase handler must yield,
        # and the command travels as ordinary text (never an explore.wait
        # submission).
        page.locator("#inputfield").click()
        _wait_field_focused(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        self.assertEqual(
            sent_action_count(page, "explore.wait"),
            0,
            "the rest form must not swallow the command-line send",
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
    def test_command_line_field_button_alignment_at_both_viewports(self):
        for viewport in ((1440, 900), (1280, 720)):
            page = self.logged_in_page(viewport)
            # H5 (design D1/D2): focus lands on the action dock after sync;
            # the command field never auto-focuses. Establish the design's
            # precondition (dock focus), then press "/" so the shell's global
            # shortcut focuses the field before measuring alignment.
            focus_action_dock(page)
            page.keyboard.press("/")
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
            # The floating panel's `--line` top border (H3 re-chrome):
            # `border-top: var(--line)` = `1px solid var(--ink-700)`.
            frame = dock.evaluate(
                """el => {
                  const style = getComputedStyle(el);
                  return { borderTop: style.borderTopColor,
                           background: style.backgroundColor };
                }"""
            )
            self.assertEqual(frame["borderTop"], "rgb(44, 38, 52)")
            # H3 re-chrome: the shortcut legend moved to the always-rendered
            # `action-dock-description` line (the `action-dock-guidance` line
            # only renders when a per-surface prefix is committed).
            description = page.locator('[data-testid="action-dock-description"]').inner_text()
            for keyword in ("方向鍵選擇", "Enter 確認", "Esc 返回", "/ 開啟指令"):
                self.assertIn(keyword, description)
            # The root is now the tab bar (H3): one row of tabs (the root
            # frame's items as tabs). The tab count varies 5-7 with
            # quest/inventory capability availability.
            cells = page.locator("#action-dock [data-item-key]")
            self.assertGreaterEqual(cells.count(), 5)
            self.assertLessEqual(cells.count(), 7)
            # The open/focused tab carries the seal-red gradient fill (the
            # `--on` class), and its leading glyph is an SVG icon.
            focused = page.locator("#action-dock .dock-tab-bar__tab--on").first
            self.assertTrue(
                "gradient" in focused.evaluate(
                    "el => getComputedStyle(el).backgroundImage"
                ),
                "the focused tab carries the seal-red gradient fill",
            )
            self.assertEqual(
                focused.locator("svg.dock-tab-bar__icon").count(),
                1,
                "the focused tab carries a leading icon",
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
            # H3: at depth >= 2 the active row container is the pane
            # (`[data-testid="dock-menu"]` = the `.dock-menu` div); the
            # pane's row group (the variant container) is the CSS grid.
            # H3: at depth >= 2 the active row container is the pane
            # (`[data-testid="dock-menu"]` = the `.dock-menu` div); the pane's
            # variant container lays out its rows with the CSS layout the pane
            # kind dictates (outlet/cards = grid, plain = block, skills/targets
            # = flex). Assert the first child's computed display is one of the
            # pane variants' valid layouts.
            pane_display = page.evaluate(
                "() => { const el = document.querySelector('[data-testid=\"dock-menu\"]');"
                " const v = el && el.firstElementChild;"
                " return v ? getComputedStyle(v).display : null; }"
            )
            self.assertIn(
                pane_display,
                ("grid", "block", "flex"),
                "the submenu's variant container uses its pane kind's CSS layout",
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
    @covers_requirement(
        "webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode"
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
        lm = page.locator('[data-testid="local-map"]')
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
        lm = page.locator('[data-testid="local-map"]')
        self.assertEqual(lm.count(), 1, "the minimap element remains in the DOM")
        hidden = page.evaluate(
            "() => { const el = document.querySelector('[data-testid=\"local-map\"]'); "
            "return el ? (el.offsetParent === null) : false; }"
        )
        self.assertTrue(hidden, "the minimap is hidden (display:none) in combat mode")

    @covers_requirement(
        "webclient-desktop-shell::narrative-output-remains-the-authoritative-text-surface"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-narrative-is-a-bounded-caption-whose-complete-log-is-reachable-in-one-action"
    )
    @covers_requirement(
        "webclient-contextual-hud::an-open-drawer-or-overlay-dims-the-stage-behind-it"
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
        # The open-surface registry (design D9) marks the stage recessed while
        # an overlay is open, and the mark clears only when it closes.
        self.assertEqual(
            page.locator('[data-testid="elosern-stage"]').get_attribute("data-menu-open"),
            "true",
            "stage is marked menu-open while the full-log overlay is open",
        )
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
        self.assertEqual(
            page.locator('[data-testid="elosern-stage"]').get_attribute("data-menu-open"),
            "false",
            "the stage mark clears once the last open surface closes",
        )
        focus_restored = page.evaluate(
            "() => { const c = document.querySelector('[data-testid=\"narrative-fulllog-control\"]'); "
            "const a = document.activeElement; return c && c === a; }"
        )
        self.assertTrue(focus_restored, "focus is restored to the control that opened the full log")

    @covers_requirement(
        "webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces",
    )
    @covers_requirement(
        "webclient-contextual-hud::the-hud-island-stack-renders-as-bounded-floating-islands-not-column-cards",
    )
    def test_populated_island_stack_fits_its_anchor_at_both_viewports(self):
        """H2 task 9.5: at 1440x900 and 1280x720, the left island stack,
        the minimap island, the narrative caption, and the dock must not
        intersect — with the condition overflow disclosed and ArtPanel
        present and populated (design D12: the assertions run against the
        layout that actually ships, not an idealised three-island stack)."""
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                state = store_state(page)
                # An 8-condition status panel makes the +N overflow chip
                # render, so the assertion runs with the overflow disclosed.
                status = valid_status_panel("艾倫·灰誓", "char-42")
                status["conditions"] = [
                    {
                        "code": f"cond_{i}",
                        "label": f"狀態{i + 1}",
                        "severity": ["beneficial", "informational", "warning", "harmful", "critical"][i % 5],
                        **({"remaining_seconds": i * 10} if i % 4 == 0 else {}),
                    }
                    for i in range(8)
                ]
                page.evaluate(
                    "(args) => window.__elosernBridge.store.receive("
                    "args.generation, 'ui_snapshot', [args.envelope], {})",
                    {
                        "generation": state["generation"],
                        "envelope": snapshot_envelope(
                            state["epoch"],
                            state["revision"] + 1,
                            {
                                "status": status,
                                "local_map": valid_local_map_panel(),
                                "art": valid_art_panel(),
                            },
                            mode="exploration",
                        ),
                    },
                )
                page.wait_for_timeout(300)
                overflow = page.locator('[data-testid="status-panel__condition-overflow"]')
                if overflow.count() > 0:
                    overflow.click()
                    page.wait_for_timeout(200)

                def intersect(sel_a, sel_b):
                    return page.evaluate(
                        """(sels) => {
                          const a = document.querySelector(sels[0]);
                          const b = document.querySelector(sels[1]);
                          if (!a || !b) return false;
                          const ra = a.getBoundingClientRect();
                          const rb = b.getBoundingClientRect();
                          const T = 1;
                          return !(ra.right <= rb.left + T || rb.right <= ra.left + T ||
                                  ra.bottom <= rb.top + T || rb.bottom <= ra.top + T);
                        }""",
                        [sel_a, sel_b],
                    )

                selectors = [
                    '[data-testid="status-panel"]',
                    '[data-testid="local-map"]',
                    '[data-testid="narrative-feed"]',
                    "#action-dock",
                ]
                for i in range(len(selectors)):
                    for j in range(i + 1, len(selectors)):
                        self.assertFalse(
                            intersect(selectors[i], selectors[j]),
                            f"{selectors[i]} intersects {selectors[j]} at {viewport}",
                        )
                # ArtPanel is present and populated in the left anchor
                # (design D12), so the height budget is asserted against the
                # real layout.
                self.assertTrue(
                    page.locator('[data-testid="art-panel"]').count() >= 1,
                    "ArtPanel present in the left anchor",
                )
                page.close()

    @covers_requirement(
        "webclient-contextual-hud::the-character-head-card-renders-only-backed-identity",
    )
    def test_character_head_card_renders_only_backed_identity(self):
        """H2 head-card: the glyph portrait, the numeric magic-level badge,
        the display name, the derived magic-rank title paired with the guild
        rank and merit, and the thousands-grouped wallet — and no race,
        subrace, class, or faction line (none exists in either payload)."""
        page = self.logged_in_page()
        state = store_state(page)
        status = valid_status_panel("艾倫·灰誓", "char-42")
        character = valid_character_panel()
        page.evaluate(
            "(args) => window.__elosernBridge.store.receive("
            "args.generation, 'ui_snapshot', [args.envelope], {})",
            {
                "generation": state["generation"],
                "envelope": snapshot_envelope(
                    state["epoch"],
                    state["revision"] + 1,
                    {"status": status, "character": character},
                    mode="exploration",
                ),
            },
        )
        page.wait_for_timeout(300)

        head = page.locator('[data-testid="character-head"]')
        # Glyph portrait: first grapheme of the display name (艾).
        self.assertEqual(page.locator('[data-testid="character-head__glyph"]').inner_text(), "艾")
        # Numeric magic-level badge from the magic_level trait row.
        self.assertEqual(
            page.locator('[data-testid="character-head__badge"]').inner_text(), "27"
        )
        # The display name from status.actor.name.
        self.assertEqual(
            page.locator('[data-testid="character-head__name"]').inner_text(), "艾倫·灰誓"
        )
        # The rank line pairs the derived magic-rank title (level 27 → 術師)
        # with the guild rank and merit from character.guild.
        rank_text = page.locator('[data-testid="character-head__rank"]').inner_text()
        self.assertIn("魔階·術師", rank_text)
        self.assertIn("公會 銀牌", rank_text)
        self.assertIn("功績 120", rank_text)
        # The wallet, thousands-grouped integer copper (design D11).
        self.assertEqual(
            page.locator('[data-testid="character-head__wallet"]').inner_text(),
            "錢包 3,240 銅",
        )
        # Disguise marker is absent when no disguise is active.
        self.assertEqual(page.locator('[data-testid="character-head__disguise"]').count(), 0)
        # No race / subrace / class / faction line anywhere on the card.
        head_text = head.inner_text()
        for token in ("種族", "職業", "陣營", "subrace", "faction", "class"):
            self.assertNotIn(token, head_text, f"head card must not render a {token} line")
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::the-low-hp-presentation-state-is-derived-client-side-and-drives-the-stage-hook",
    )
    def test_low_hp_state_drives_the_stage_hook(self):
        """H2 low-HP: the client derives the low-HP presentation state from
        the committed hp ratio against the 25% display threshold and drives
        the stage's red vignette through the existing low-HP hook. A low
        ratio (hp 20/100 = 0.2) sets data-lowhp="true"; a healthy ratio
        (hp 100/100 = 1.0) sets data-lowhp="false"."""
        page = self.logged_in_page()
        state = store_state(page)
        revision_cursor = state["revision"]

        def inject_status(hp_current: int, hp_maximum: int) -> None:
            nonlocal revision_cursor
            # The reducer admits only strictly newer revisions (protocol.js
            # rejects `not_newer`), so each injection must advance the
            # revision cursor.
            revision_cursor += 1
            st = valid_status_panel("艾倫·灰誓", "char-42")
            st["resources"] = {
                "hp": {"current": hp_current, "maximum": hp_maximum},
                "mp": {"current": 50, "maximum": 50},
                "sp": {"current": 20, "maximum": 20},
            }
            page.evaluate(
                "(args) => window.__elosernBridge.store.receive("
                "args.generation, 'ui_snapshot', [args.envelope], {})",
                {
                    "generation": state["generation"],
                    "envelope": snapshot_envelope(
                        state["epoch"],
                        revision_cursor,
                        {"status": st},
                        mode="exploration",
                    ),
                },
            )
            page.wait_for_timeout(300)

        # Low hp (0.2 <= 0.25): the stage root carries the low-HP state.
        inject_status(20, 100)
        self.assertEqual(
            page.locator('[data-testid="elosern-stage"]').get_attribute("data-lowhp"),
            "true",
            "a committed hp ratio at or below the 25% threshold must light the stage",
        )
        # Healthy hp (1.0 > 0.25): the stage returns to its ordinary state.
        inject_status(100, 100)
        self.assertEqual(
            page.locator('[data-testid="elosern-stage"]').get_attribute("data-lowhp"),
            "false",
            "a committed hp ratio above the threshold must clear the stage state",
        )
        page.close()


if __name__ == "__main__":
    import unittest

    unittest.main()
