"""Desktop-shell acceptance: command-line field focus/send/cancel behavior and message-window paging journeys.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    narrative_log_length,
    narrative_log_text,
    open_command_line,
    open_dialogue_choices,
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
                "() => { const f = document.getElementById('inputfield');"
                " const a = document.querySelector('[data-anchor=\"command-line\"]');"
                " return !!f && !!a && a.getAttribute('data-expanded') === 'true' && document.activeElement === f; }"
            ),
            "description": "#inputfield focused",
        },
        timeout=timeout,
    )


def _wait_narrative_grew(page, before_len, timeout=30000):
    """Gate on the retained narrative log length exceeding a previous length."""
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected"))
        and narrative_log_length(page) > before_len,
        timeout=timeout,
    )


# The paging journeys' own fixture: one sentence per line, tagged so a gate can
# name the response it appended. Fifteen of them exceed one page, so appending
# the same body again must add a page — the observation the tail gate needs.
_SENTENCE_BODY = "霧氣沿著灰河的水面緩緩蔓延過青石長街與古老橋墩，遠處燈火在夜色中明滅不定。"
_APPENDED_TAG = "第{}句："
_APPENDED_MARK = _APPENDED_TAG.format(1)
_TAIL_TAG = "尾聲第{}句："


def _append_multipage_response(page):
    """Append a multi-page response and gate on `[data-testid="message-page"]` showing it at page 1.

    These journeys assert paging, not typing, so the helper pins the reader's
    text speed to `instant` first (webclient-typewriter-reading-prefs design
    D11): every page is fully shown, with its marker, as soon as it shows.
    The gate names the appended response's own first sentence: the retained
    log already opens at page 1 of a two-page response, so a gate on the
    paging attributes alone passes on the response that was on screen before
    the append, and the journey then measures that stale page.
    """
    page.evaluate(
        """() => {
          const store = window.__elosernBridge.store;
          store.setTextSpeed('instant');
          if (!store.narrative.some((l) => l && l.kind !== 'in')) {
            store.appendText('out', '初始段落。');
          }
        }"""
    )
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": '[data-testid="message-page-marker"]',
            "predicate": (
                "() => !!document.querySelector('[data-testid=\"message-page-marker\"]')"
            ),
            "description": "message-window initial mount pass settled",
        },
        timeout=30000,
    )
    sentences = "".join(
        _APPENDED_TAG.format(i) + _SENTENCE_BODY for i in range(1, 16)
    )
    page.evaluate(
        """(text) => {
          const store = window.__elosernBridge.store;
          store.appendText('in', 'look');
          store.appendText('out', text);
        }""",
        sentences,
    )
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": '[data-testid="message-page"]',
            "predicate": (
                "() => { const p = document.querySelector('[data-testid=\"message-page\"]');"
                " return !!p && p.getAttribute('data-page') === '1'"
                " && parseInt(p.getAttribute('data-pages') || '0', 10) >= 2"
                f" && p.innerText.indexOf('{_APPENDED_MARK}') !== -1; }}"
            ),
            "description": "message-page shows the appended response at page 1",
        },
        timeout=30000,
    )


class ShellAcceptanceTest(BrowserAcceptanceTest):
    """Every required surface at 1451x790 and 2560x1440, plus keyboard journeys."""
    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow",
        "webclient-contextual-hud::the-command-line-is-a-collapsible-row-docked-on-the-message-region-s-top-edge",
    )
    def test_keyboard_field_focus_send_cancel_and_focus_restoration(self):
        page = self.logged_in_page()
        before_len = narrative_log_length(page)
        narrative_before = narrative_log_text(page)
        anchor = page.locator('[data-testid="anchor-command-line"]')
        toggle = page.locator('[data-testid="command-line-toggle"]')

        # Collapsed on load; `#inputfield` stays in the DOM inside its wrapper
        # but is hidden, and the ⌨ toggle is visible with aria-expanded="false".
        self.assertEqual(anchor.get_attribute("data-expanded"), "false")
        self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
        self.assertEqual(page.locator("#inputfield").count(), 1)
        self.assertFalse(page.locator("#inputfield").is_visible())

        # `/` expands the row and focuses `#inputfield`.
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)
        self.assertEqual(anchor.get_attribute("data-expanded"), "true")
        self.assertEqual(toggle.get_attribute("aria-expanded"), "true")
        self.assertTrue(page.locator("#inputfield").is_visible())

        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_for_narrative_settled(page, before_len)
        # Accepted send clears the field, collapses the line, and restores focus to #action-dock.
        wait_command_field_released(page)
        self.assertEqual(anchor.get_attribute("data-expanded"), "false")
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"), ""
        )
        after_len = narrative_log_length(page)
        narrative_after = narrative_log_text(page)
        self.assertNotEqual(
            narrative_after, narrative_before, "command-line send produced no narrative"
        )

        # A second consecutive command is sent without pointer interaction by
        # pressing `/` first.
        page.keyboard.press("/")
        _wait_field_focused(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_for_narrative_settled(page, after_len)
        wait_command_field_released(page)

        # Cancel path: Escape from the focused field sends nothing and
        # restores action-dock focus while collapsing the command line and
        # preserving the unsent draft for the next expansion.
        page.keyboard.press("/")
        _wait_field_focused(page)
        page.keyboard.type("unsent draft")
        narrative_before_cancel = narrative_log_text(page)
        page.keyboard.press("Escape")
        wait_command_field_released(page)
        self.assertEqual(
            narrative_log_text(page),
            narrative_before_cancel,
            "Escape must not send command-line text",
        )
        page.keyboard.press("/")
        _wait_field_focused(page)
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            "unsent draft",
            "Escape preserves the unsent draft for the next expansion",
        )

    @covers_requirement(
        "webclient-desktop-shell::narrative-output-remains-the-authoritative-text-surface-and-is-read-page-by-page"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-message-window-presents-the-current-response-one-page-at-a-time-in-the-band-s-message-region"
    )
    def test_paging_marker_and_append_keep_page(self):
        page = self.logged_in_page()
        # No unread counter or jump-to-latest control is rendered in the window.
        self.assertEqual(
            page.locator('[data-testid="message-window"] [data-count]').count(),
            0,
        )
        _append_multipage_response(page)
        surface = page.locator('[data-testid="message-page"]')
        marker = page.locator('[data-testid="message-page-marker"]')
        self.assertEqual(marker.count(), 1)
        self.assertEqual(marker.inner_text(), "▼")
        self.assertEqual(marker.get_attribute("aria-hidden"), "true")
        page_1_text = surface.inner_text()
        total_before = int(surface.get_attribute("data-pages") or "0")

        # Appending another line to the same response never moves the reader
        # off the page on screen. The appended text is a whole response's
        # worth, so the window's re-page for it must add a page: gating on
        # that growth is what distinguishes the re-paged layout from the
        # layout the append has not reached yet.
        tail = "".join(
            _TAIL_TAG.format(i) + _SENTENCE_BODY for i in range(1, 16)
        )
        page.evaluate(
            "(text) => window.__elosernBridge.store.appendText('out', text)", tail
        )
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="message-page"]',
                "predicate": (
                    "() => { const p = document.querySelector('[data-testid=\"message-page\"]');"
                    " return !!p && p.getAttribute('data-page') === '1'"
                    f" && parseInt(p.getAttribute('data-pages') || '0', 10) > {total_before}; }}"
                ),
                "description": "the appended tail re-paged with the reader still on page 1",
            },
        )
        self.assertEqual(surface.get_attribute("data-page"), "1")
        self.assertEqual(surface.inner_text(), page_1_text)
        self.assertEqual(marker.inner_text(), "▼")
        self.assertGreater(int(surface.get_attribute("data-pages") or "0"), total_before)

        # Clicking the window advances page by page to ■ on the last page.
        total = int(surface.get_attribute("data-pages") or "0")
        for step in range(2, total + 1):
            page.locator('[data-testid="message-window"]').click()
            wait_for_store_state(
                page,
                lambda s: bool(s.get("connected")),
                dom_readiness={
                    "selector": '[data-testid="message-page"]',
                    "predicate": (
                        "() => document.querySelector('[data-testid=\"message-page\"]')"
                        f".getAttribute('data-page') === '{step}'"
                    ),
                    "description": f"message-page advanced to page {step}",
                },
            )
        self.assertEqual(marker.inner_text(), "■")

    @covers_requirement(
        "webclient-desktop-shell::narrative-output-remains-the-authoritative-text-surface-and-is-read-page-by-page"
    )
    def test_page_surface_keyboard_advance_and_dock_isolation(self):
        page = self.logged_in_page()
        _append_multipage_response(page)
        surface = page.locator('[data-testid="message-page"]')
        marker = page.locator('[data-testid="message-page-marker"]')
        self.assertEqual(surface.get_attribute("data-page"), "1")
        self.assertEqual(marker.inner_text(), "▼")

        # Enter while focus is on #action-dock activates the dock and does not
        # advance the message window's page.
        focus_action_dock(page)
        page.keyboard.press("Enter")
        page.wait_for_timeout(120)
        self.assertEqual(
            surface.get_attribute("data-page"),
            "1",
            "Enter on the action dock must not advance the message window",
        )

        # Focusing the page surface and pressing Enter advances one page and
        # keeps keyboard focus on the page surface.
        surface.focus()
        page.keyboard.press("Enter")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="message-page"]',
                "predicate": (
                    "() => { const p = document.querySelector('[data-testid=\"message-page\"]');"
                    " return !!p && p.getAttribute('data-page') === '2'"
                    " && document.activeElement === p; }"
                ),
                "description": "message-page advanced to page 2 and holds focus",
            },
        )
        total = int(surface.get_attribute("data-pages") or "0")
        for step in range(3, total + 1):
            page.keyboard.press(" ")
            wait_for_store_state(
                page,
                lambda s: bool(s.get("connected")),
                dom_readiness={
                    "selector": '[data-testid="message-page"]',
                    "predicate": (
                        "() => document.querySelector('[data-testid=\"message-page\"]')"
                        f".getAttribute('data-page') === '{step}'"
                    ),
                    "description": f"message-page advanced to page {step}",
                },
            )
        self.assertEqual(marker.inner_text(), "■")

    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow",
        "webclient-contextual-hud::the-command-line-is-a-collapsible-row-docked-on-the-message-region-s-top-edge",
    )
    def test_pointer_focused_field_sends_on_enter(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        before_len = narrative_log_length(page)
        anchor = page.locator('[data-testid="anchor-command-line"]')
        toggle = page.locator('[data-testid="command-line-toggle"]')
        self.assertEqual(anchor.get_attribute("data-expanded"), "false")

        # Clicking the ⌨ toggle expands the row and focuses `#inputfield`;
        # Enter sends once, clears the field, collapses the row, and returns
        # focus to `#action-dock`.
        toggle.click()
        _wait_field_focused(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        _wait_narrative_grew(page, before_len)
        wait_command_field_released(page)
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            "",
            "the field must clear after a pointer-focused send",
        )
        sends = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "text"
        ]
        self.assertEqual(len(sends), 1, "exactly one text message is sent")
        self.assertTrue(any("look" in str(item) for item in sends))

    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow",
        "webclient-contextual-hud::the-command-line-is-a-collapsible-row-docked-on-the-message-region-s-top-edge",
    )
    def test_rejected_send_keeps_the_line_open(self):
        page = self.logged_in_page()
        anchor = page.locator('[data-testid="anchor-command-line"]')
        open_command_line(page)
        # Inject a reload-required protocol error so mutationsLocked becomes true.
        generation = store_state(page)["generation"]
        accepted = page.evaluate(
            """(args) => window.__elosernBridge.store.receive(
              args.generation, 'ui_protocol_error', [{
                protocol_version: 1,
                code: 'unsupported_version',
                message: '不支援的協定版本',
                reload_required: true,
              }], {})""",
            {"generation": generation},
        )
        self.assertTrue(accepted["accepted"])
        self.assertTrue(store_state(page)["mutationsLocked"])

        page.keyboard.type("keep this draft")
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        self.assertEqual(anchor.get_attribute("data-expanded"), "true")
        self.assertTrue(page.locator("#inputfield").is_visible())
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            "keep this draft",
        )
        self.assertTrue(
            page.evaluate("document.activeElement === document.getElementById('inputfield')"),
            "a rejected send keeps focus in #inputfield",
        )

    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow",
        "webclient-contextual-hud::the-command-line-is-a-collapsible-row-docked-on-the-message-region-s-top-edge",
    )
    def test_borrowed_send_outside_the_active_phase_keeps_the_speech(self):
        """webclient-dialogue-choices-overlay D9: the dialogue free row borrows
        the field; with the presentation phase no longer active (a transport
        reset awaiting its first snapshot, injected through the bridge), Enter
        submits nothing, the field keeps the speech and the focus, the row
        stays expanded, and the borrow stays bound to the host."""
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        inject_snapshot(
            page,
            {
                "local_map": valid_local_map_panel(),
                "dialogue": {
                    "schema_version": 2,
                    "available": True,
                    "kind": "dialogue",
                    "host": {"identity": 11, "display_name": "小販", "portrait_ref": None},
                    "bond_stage": None,
                    "line": "歡迎光臨。",
                    "choices": [{"keyword_id": "goods", "label": "有什麼貨？"}],
                },
            },
            mode="dialogue",
        )
        wait_for_store_state(page, lambda s: s.get("mode") == "dialogue")
        # Read any unread page of the latest response first.
        open_dialogue_choices(page)
        page.click('[data-testid="dialogue-freeform"]')
        _wait_field_focused(page)
        self.assertTrue(store_state(page)["freeformBound"])
        # A transport reset through the bridge: connected, awaiting the first
        # snapshot of the new generation (the phase is no longer active).
        page.evaluate(
            """() => {
              const store = window.__elosernBridge.store;
              store.beginTransport(store.view.generation + 1);
              store.setConnected(true);
            }"""
        )
        state = store_state(page)
        self.assertNotEqual(state["phase"], "active")
        self.assertFalse(state["commandAccepts"])
        page.keyboard.type("話到嘴邊")
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 0)
        self.assertEqual(page.evaluate("document.getElementById('inputfield').value"), "話到嘴邊")
        self.assertEqual(
            page.locator('[data-testid="anchor-command-line"]').get_attribute("data-expanded"), "true"
        )
        self.assertTrue(
            page.evaluate("document.activeElement === document.getElementById('inputfield')"),
            "a refused borrowed send keeps focus in #inputfield",
        )
        self.assertTrue(store_state(page)["freeformBound"], "the borrow stays bound to the host")
        texts = [args for cmd, args, _kw in page.evaluate("window.__elosernSent || []") if cmd == "text"]
        self.assertEqual(texts, [], "a refused borrowed send never goes out as ordinary text")

    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow",
        "webclient-contextual-hud::the-command-line-is-a-collapsible-row-docked-on-the-message-region-s-top-edge",
    )
    def test_toggle_collapses_and_keeps_focus(self):
        page = self.logged_in_page()
        anchor = page.locator('[data-testid="anchor-command-line"]')
        toggle = page.locator('[data-testid="command-line-toggle"]')
        open_command_line(page)
        self.assertEqual(anchor.get_attribute("data-expanded"), "true")

        toggle.click()
        page.wait_for_function(
            "() => document.querySelector('[data-anchor=\"command-line\"]').getAttribute('data-expanded') === 'false'",
            timeout=10000,
        )
        self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
        self.assertFalse(page.locator("#inputfield").is_visible())
        self.assertTrue(
            page.evaluate(
                "document.activeElement === document.querySelector('[data-testid=\"command-line-toggle\"]')"
            ),
            "collapsing with the ⌨ toggle leaves focus on the toggle",
        )

    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow"
    )
    def test_shift_enter_in_field_inserts_newline_without_sending(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        before_len = narrative_log_length(page)
        open_command_line(page)
        page.keyboard.type("first line")
        page.keyboard.press("Shift+Enter")
        page.keyboard.type("second line")
        page.keyboard.press("Enter")
        _wait_narrative_grew(page, before_len)
        sends = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "text"
        ]
        self.assertEqual(len(sends), 1, "Shift+Enter must not send")
        self.assertIn("first line\nsecond line", str(sends[0]))

    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow"
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
        # Expand the command line via the ⌨ toggle and send; the rest form's
        # handler must yield, and the command travels as ordinary text (never
        # an explore.wait submission).
        page.locator('[data-testid="command-line-toggle"]').click()
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
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow"
    )
    def test_command_line_field_button_alignment_at_both_viewports(self):
        for viewport in ((1451, 790), (2560, 1440)):
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
