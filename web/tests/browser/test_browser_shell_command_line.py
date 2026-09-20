"""Desktop-shell acceptance: command-line field focus/send/cancel behavior and narrative scrollback/unread journeys.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    sent_action_count,
    store_state,
    valid_art_panel,
    valid_character_panel,
    valid_local_map_panel,
    valid_status_panel,
    wait_for_narrative_settled,
    wait_for_store_state,
)
from .harness import wait_command_field_released


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
        wait_command_field_released(page)
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)
        page.keyboard.type("look")
        narrative_before_cancel = page.locator('[data-testid="narrative-feed"]').inner_text()
        page.keyboard.press("Escape")
        wait_command_field_released(page)
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"]').inner_text(),
            narrative_before_cancel,
            "Escape must not send command-line text",
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
        # The feed stylesheet sets `scroll-behavior: smooth`, so a direct
        # `scrollTop = 0` triggers an animation that races the gate. Force an
        # instant scroll for this single assignment (the same override pattern
        # the feed's own `scrollToBottom` and the scrolled-away test use) so
        # the exact-top gate and the assertion below cannot observe a
        # mid-flight animation frame.
        page.evaluate(
            "() => { const f = document.querySelector('[data-testid=\"narrative-feed\"]');"
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
                    "() => { const f = document.querySelector('[data-testid=\"narrative-feed\"]');"
                    " return f && f.scrollTop === 0 && f.scrollHeight - f.scrollTop - f.clientHeight >= 8; }"
                ),
                "description": "narrative feed scrolled to the top (and not at the bottom)",
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
            "() => { const f = document.querySelector('[data-testid=\"narrative-feed\"]');"
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
                    "() => { const f = document.querySelector('[data-testid=\"narrative-feed\"]');"
                    " return f && f.scrollTop === 0 && f.scrollHeight - f.scrollTop - f.clientHeight >= 8; }"
                ),
                "description": "narrative feed scrolled to the top (and not at the bottom)",
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
        # Navigate to the Wait/休息 tab by the store's committed focus KEY,
        # not by cell arithmetic: the declarative root's tab set is
        # capability-driven (H3 design D5 appends the 建議 tab when the
        # suggestions envelope is not `unavailable`), so the wait cell is
        # no longer guaranteed to be last.
        focus_action_dock(page)
        for _ in range(10):
            focused = page.evaluate(
                "() => window.__elosernBridge.store.view.focus.key"
            )
            if focused == "wait":
                break
            page.keyboard.press("ArrowRight")
        else:
            raise AssertionError("the wait tab never reached focus")
        page.keyboard.press("Enter")  # Wait/休息
        # The shipped Wait surface is the three-operation frame (dawn /
        # sleep / 休息 N 小時 cards; stores/elosern.js resolves the wait
        # frame with gridCols: 3, one row + 返回). Dawn and sleep confirm
        # their `explore.wait` dispatch directly — only 休息 N 小時
        # (wait-rest) opens the custom-duration form — so the form is
        # reached with two ArrowRight steps, not vertical arrows.
        page.keyboard.press("ArrowRight")  # 睡眠至完全恢復
        page.keyboard.press("ArrowRight")  # 休息 N 小時 (opens the rest form)
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
