"""Input echo and command-line browser acceptance (webclient-input-narrative).

These journeys verify the narrative input line contract: the command line starts
collapsed and expands on `/` or the ⌨ toggle (webclient-collapsible-command-line),
`/` expands and focuses the field without firing inside an editable control,
typed command-line commands and button-triggered mutations echo exactly one `.inp` line with a preceding
`.narrative-divider`, locked submissions never echo, and the display catalog
never alters the `ui_action` envelope.

The pure command-line/narrative journeys run on the shared foundation server
(they never mutate game state); the move/free-form journeys boot one
dedicated isolated exploration server each so their mutations never leak into
another journey. All fixtures are deterministic; no remote, LLM, or image
service is involved.
"""

from __future__ import annotations

import json
import time

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    activate_first_overview_exit,
    activate_overview_chip,
    fixture_home_node_id,
    focus_action_dock,
    install_outbound_recorder,
    narrative_log_length,
    narrative_log_text,
    outbound_messages,
    sent_action_count,
    store_state,
    wait_for_narrative_settled,
    wait_for_page_shown,
    wait_for_presentation_settled,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin, wait_command_field_released
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


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


def _wait_inp_line(page, count, text=None, exact=False, timeout=30000, keep_open=False):
    """Gate on the full-log overlay's player-input (``.inp``) DOM line count (optionally matching text).

    Opens ``[data-testid="fulllog-overlay"]`` via the shell's ``message-log-open``
    control when not already open, verifies the rendered ``.inp`` elements in the
    DOM, and closes the overlay (restoring prior focus) unless ``keep_open`` is True
    or the caller had already opened it.
    """
    was_open = page.evaluate(
        """() => {
          if (document.querySelector('[data-testid="fulllog-overlay"]')) {
            return true;
          }
          const btn = document.querySelector('[data-testid="message-log-open"]');
          if (btn) { btn.click(); }
          return false;
        }"""
    )
    if text is None:
        predicate_js = (
            "() => document.querySelectorAll("
            "'[data-testid=\"fulllog-overlay\"] .inp').length === %d" % count
        )
    else:
        js_text = json.dumps(text)
        if exact:
            cmp = "lines[lines.length - 1].innerText === %s" % js_text
        else:
            cmp = "lines[lines.length - 1].innerText.indexOf(%s) !== -1" % js_text
        predicate_js = (
            "() => { const lines = document.querySelectorAll("
            "'[data-testid=\"fulllog-overlay\"] .inp');"
            " return lines.length === %d && %s; }" % (count, cmp)
        )
    try:
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="fulllog-overlay"]',
                "predicate": predicate_js,
                "description": "full-log overlay input lines",
            },
            timeout=timeout,
        )
    finally:
        if not keep_open and not was_open:
            page.evaluate(
                """() => {
                  const closeBtn = document.querySelector('[data-testid="fulllog-close"]');
                  if (closeBtn) { closeBtn.click(); }
                }"""
            )
            page.wait_for_selector(
                '[data-testid="fulllog-overlay"]', state="detached", timeout=15000
            )


def _clear_narrative(page):
    """Reset the store's narrative log so the next input line is the log's first line.

    The store is a Pinia store, so ``store.narrative`` is the unwrapped array;
    clear it in place (``.length = 0``) to keep the reactive reference intact.
    """
    page.evaluate("() => { window.__elosernBridge.store.narrative.length = 0; }")


def _append_multipage_response(page):
    """Append a multi-page response with distinct tagged sentences and wait for page 1.

    These journeys assert paging, not typing, so the helper pins the reader's
    text speed to `instant` first (webclient-typewriter-reading-prefs design
    D11): every page is fully shown, with its marker, as soon as it shows.
    """
    # Ensure MessageWindow has completed its initial mount pass (`initialized = true`)
    # on an earlier response before the new multi-page response arrives; otherwise
    # the mount rule (`!initialized -> setPage(last)`) opens on the last page.
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
        f"【段落{i}】霧氣沿著灰河的水面緩緩蔓延過青石長街與古老橋墩，遠處燈火在夜色中明滅不定。"
        for i in range(1, 16)
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
                " && parseInt(p.getAttribute('data-pages') || '0', 10) >= 2; }"
            ),
            "description": "message-page opened at page 1 of a multi-page response",
        },
        timeout=30000,
    )
    return sentences


class DrawerNarrativeBrowserTest(BrowserAcceptanceTest):
    """Command-line focus, toggle, and input-echo acceptance (no mutation).

    H5 (webclient-hud-05-overlays-and-command-line): the command drawer is
    replaced by the permanently-present command line (design D1) — the field
    is in the DOM, visible and focusable without any opening action.
    """

    def _open_command_line(self, page):
        # H5: no opening action — the field is already in the DOM; the dock's
        # free-form borrow (design D6) or the shell's `/` claim (design D2)
        # both focus the always-present field.
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)

    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-command-line-is-a-collapsible-row-docked-on-the-message-region-s-top-edge"
    )
    def test_command_line_is_permanently_present_and_focusable(self):
        page = self.logged_in_page()
        # webclient-collapsible-command-line (design D1/D2): the command line
        # stays mounted in the DOM (`#inputfield` inside `.inputfieldwrapper`),
        # collapsed by default (`data-expanded="false"`), with the ⌨ toggle
        # rendered in `#band-message` (`aria-expanded="false"`), and `/`
        # expands the row and focuses `#inputfield`.
        self.assertEqual(
            page.locator('[data-testid="command-line"]').count(), 1,
            "the command line surface stays mounted in the DOM",
        )
        self.assertEqual(page.locator(".drawer-entry").count(), 0, "no drawer entry control")
        self.assertEqual(
            page.locator('[data-testid="anchor-command-line"]').get_attribute("data-expanded"),
            "false",
        )
        self.assertEqual(
            page.locator('[data-testid="command-line-toggle"]').get_attribute("aria-expanded"),
            "false",
        )
        self.assertFalse(
            page.locator(".inputfieldwrapper").is_visible(),
            "the input row is collapsed (display:none) by default",
        )
        self._open_command_line(page)
        self.assertTrue(
            page.locator(".inputfieldwrapper").is_visible(),
            "the input row is visible once expanded",
        )
        self.assertTrue(
            page.locator('[data-testid="command-line-prompt"]').is_visible(),
            "the prompt chevron is visible once expanded",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-command-line-advertises-only-affordances-this-client-implements"
    )
    def test_command_line_hint_names_history_and_completion_and_controls_share_the_walk(self):
        """The hint cluster states the command-history recall keys and the
        Tab-completion affordance (both implemented, webclient-align-02); Tab
        completes a committed exit name in the live app; the history controls
        drive the same walk state the keys drive, and neither submits."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._open_command_line(page)
        # The hint cluster names the history recall keys AND the completion
        # affordance — the draft wording, both implemented.
        self.assertEqual(
            page.locator(".hint").inner_text(),
            "↑↓ 歷史 · Tab 補全",
            "the hint states the history recall keys and the completion affordance",
        )
        # Seed the command history deterministically by sending two distinct text
        # commands through the client's single send path (each accepted send
        # collapses the line).
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_command_field_released(page)
        self._open_command_line(page)
        page.keyboard.type("take sword")
        page.keyboard.press("Enter")
        wait_command_field_released(page)
        page.wait_for_function(
            "() => window.__elosernBridge.store.commandHistory.length >= 2",
            timeout=15000,
        )
        self._open_command_line(page)
        # The two seeded sends are already on the wire; capture that baseline so
        # the walk is proven to add no new message.
        baseline = len(outbound_messages(page))
        # The history-up control and the ↑ recall key drive the same walk state:
        # the button walks to the most recent entry, the key walks to the one
        # before it, and the unsent draft is preserved across the walk. Neither
        # submits (the walk is display-only).
        page.locator('[data-testid="command-line-history-up"]').click()
        self.assertEqual(
            page.evaluate("() => document.getElementById('inputfield').value"),
            "take sword",
            "the history control walked to the most recent entry",
        )
        # The recall key only drives the walk while the field is focused.
        page.locator("#inputfield").focus()
        page.keyboard.press("ArrowUp")
        self.assertEqual(
            page.evaluate("() => document.getElementById('inputfield').value"),
            "look",
            "the recall key walked to the prior entry (same shared walk state)",
        )
        self.assertEqual(
            len(outbound_messages(page)),
            baseline,
            "neither the history control nor the recall key submitted (no new wire messages)",
        )
        # Tab completion over the live committed sources (webclient-align-02):
        # the seeded history entry completes uniquely from its prefix, the
        # draft ends up holding the full candidate, and completion sends
        # nothing on its own.
        page.locator("#inputfield").focus()
        page.keyboard.press("Control+a")
        page.keyboard.type("take sw")
        page.keyboard.press("Tab")
        page.wait_for_function(
            "() => document.getElementById('inputfield').value === 'take sword'",
            timeout=10000,
        )
        self.assertEqual(
            len(outbound_messages(page)),
            baseline,
            "Tab completion itself sent no client->server message",
        )
        # An unmatched draft leaves text and focus untouched.
        page.keyboard.press("Control+a")
        page.keyboard.type("zzz")
        page.keyboard.press("Tab")
        page.wait_for_timeout(150)
        self.assertEqual(
            page.evaluate("() => document.getElementById('inputfield').value"),
            "zzz",
            "an unmatched draft is left alone",
        )
        self.assertTrue(
            page.evaluate("document.activeElement === document.getElementById('inputfield')"),
            "Tab never moved focus out of the field",
        )

    @covers_requirement(
        "webclient-contextual-hud::narrative-prose-scale-is-a-client-local-preference-the-settings-surface-owns"
    )
    def test_settings_prose_scale_is_a_client_local_preference(self):
        """The settings surface owns the narrative prose scale as client-local
        presentation state: three steps with a non-colour current-step indicator,
        and no `ui_action` is dispatched for the change."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # Open the settings overlay through the top navigation bar's 設定 control.
        page.locator('[data-testid="nav-settings"]').click()
        page.wait_for_selector('[data-testid="settings-overlay"]', timeout=15000)
        # The three-step prose-scale selector renders; the current step is marked
        # by a non-colour indicator (aria-pressed / the `on` class).
        for testid in ("settings-overlay-scale-A−", "settings-overlay-scale-A", "settings-overlay-scale-A+"):
            self.assertEqual(
                page.locator('[data-testid="%s"]' % testid).count(),
                1,
                f"{testid} renders",
            )
        self.assertTrue(
            page.evaluate(
                "() => { const el = document.querySelector('[data-testid=\"settings-overlay-scale-A\"]');"
                " return el && (el.getAttribute('aria-pressed') === 'true' || el.classList.contains('on')); }"
            ),
            "the current prose-scale step is marked without colour alone",
        )
        # Changing the scale is client-local: it applies the value to the
        # ``--prose-scale`` presentation token, persists it through the versioned
        # layout store, and dispatches no ``ui_action``.
        page.locator('[data-testid="settings-overlay-scale-A+"]').click()
        page.wait_for_function(
            "() => { const s = window.__elosernBridge.store;"
            " return s && s.view && s.view.fontScale === 1.12; }",
            timeout=15000,
        )
        self.assertEqual(
            page.evaluate(
                "() => document.documentElement.style.getPropertyValue('--prose-scale')"
            ),
            "1.12",
            "the prose scale is applied to the presentation token",
        )
        self.assertEqual(
            page.evaluate(
                "() => { const raw = localStorage.getItem('elosern.layout');"
                " return raw ? JSON.parse(raw).preferences.fontScale : null; }"
            ),
            1.12,
            "the prose scale is persisted as client-local presentation state",
        )
        self.assertEqual(
            sent_action_count(page),
            0,
            "the prose-scale change is client-local presentation state, not a ui_action",
        )

    # ---- webclient-typewriter-reading-prefs (task 7.4) ----

    def _settle_window_mount(self, page):
        """Give the message window a first response so its mount pass has run
        (a later response then opens on page 1 instead of being treated as the
        mount's last page)."""
        page.evaluate(
            """() => {
              const store = window.__elosernBridge.store;
              if (!store.narrative.some((l) => l && l.kind !== 'in')) {
                store.appendText('out', '初始段落。');
              }
            }"""
        )
        page.wait_for_selector('[data-testid="message-page-marker"]', state="attached", timeout=30000)

    def _line_boxes(self, page):
        """The page text's rendered line boxes, one per line (hidden text keeps its boxes)."""
        return page.evaluate(
            """() => {
              const p = document.querySelector('[data-testid="message-page"]');
              const range = document.createRange();
              range.selectNodeContents(p);
              // One box per rendered line: the reveal's span boundary splits a
              // line into several rects, so rects sharing a top are unioned.
              const lines = new Map();
              for (const r of range.getClientRects()) {
                const top = Math.round(r.top);
                const box = lines.get(top) || { left: Infinity, right: -Infinity, height: 0 };
                box.left = Math.min(box.left, Math.round(r.left));
                box.right = Math.max(box.right, Math.round(r.right));
                box.height = Math.max(box.height, Math.round(r.height));
                lines.set(top, box);
              }
              return Array.from(lines, ([top, b]) => [b.left, top, b.right, b.height])
                .sort((x, y) => x[1] - y[1]);
            }"""
        )

    @covers_requirement(
        "webclient-input-narrative::a-page-types-in-at-the-reader-s-text-speed-and-auto-advance-is-opt-in"
    )
    def test_message_page_types_and_completes(self):
        page = self.logged_in_page((1920, 1080))
        self._settle_window_mount(page)
        sentences = "".join(
            f"【段落{i}】霧氣沿著灰河的水面緩緩蔓延過青石長街與古老橋墩，遠處燈火在夜色中明滅不定。"
            for i in range(1, 16)
        )
        page.evaluate(
            """(text) => {
              const store = window.__elosernBridge.store;
              store.appendText('in', 'look');
              store.appendText('out', text);
            }""",
            sentences,
        )
        page.wait_for_function(
            """() => { const w = document.querySelector('[data-testid="message-window"]');
              const p = document.querySelector('[data-testid="message-page"]');
              return w && p && p.getAttribute('data-page') === '1'
                && parseInt(p.getAttribute('data-pages') || '0', 10) >= 2
                && w.getAttribute('data-typing') === 'true'
                && p.querySelector('.narrative-unrevealed, .narrative-line.unrevealed') !== null; }""",
            timeout=30000,
        )
        # Typing: no marker, and the page already occupies its final layout.
        self.assertEqual(page.locator('[data-testid="message-page-marker"]').count(), 0)
        typing_boxes = self._line_boxes(page)
        surface = page.locator('[data-testid="message-page"]')
        self.assertNotIn("【段落15】", surface.inner_text())

        # Enter on the page surface completes the page without advancing.
        surface.focus()
        page.keyboard.press("Enter")
        wait_for_page_shown(page)
        self.assertEqual(surface.get_attribute("data-page"), "1")
        self.assertEqual(page.locator('[data-testid="message-page-marker"]').inner_text(), "▼")
        self.assertEqual(
            self._line_boxes(page),
            typing_boxes,
            "the rendered line boxes do not change between typing and complete",
        )
        self.assertIn("【段落1】", surface.inner_text())

        # The next Enter advances, and page 2 types in.
        page.keyboard.press("Enter")
        page.wait_for_function(
            """() => document.querySelector('[data-testid="message-page"]').getAttribute('data-page') === '2'""",
            timeout=15000,
        )
        self.assertEqual(sent_action_count(page), 0)
        page.close()

    @covers_requirement(
        "webclient-input-narrative::a-page-types-in-at-the-reader-s-text-speed-and-auto-advance-is-opt-in"
    )
    def test_reduced_motion_pages_are_instant(self):
        page = self.logged_in_page((1920, 1080))
        page.emulate_media(reduced_motion="reduce")
        self._settle_window_mount(page)
        page.evaluate("() => window.__elosernBridge.store.setTextSpeed('slow')")
        sentences = "".join(
            f"第{i}句：霧氣沿著灰河的水面緩緩蔓延過青石長街與古老橋墩，遠處燈火在夜色中明滅不定。"
            for i in range(1, 16)
        )
        page.evaluate(
            """(text) => {
              const store = window.__elosernBridge.store;
              store.appendText('in', 'look');
              store.appendText('out', text);
            }""",
            sentences,
        )
        page.wait_for_function(
            """() => { const p = document.querySelector('[data-testid="message-page"]');
              return p && p.getAttribute('data-page') === '1'
                && parseInt(p.getAttribute('data-pages') || '0', 10) >= 2; }""",
            timeout=30000,
        )
        state = page.evaluate(
            """() => ({
              typing: document.querySelector('[data-testid="message-window"]').getAttribute('data-typing'),
              hidden: document.querySelectorAll(
                '[data-testid="message-page"] .narrative-unrevealed, [data-testid="message-page"] .narrative-line.unrevealed').length,
              marker: (document.querySelector('[data-testid="message-page-marker"]') || {}).textContent || null,
            })"""
        )
        self.assertEqual(state, {"typing": "false", "hidden": 0, "marker": "▼"})
        # An explicit reduced-motion preference of off lets pages type again.
        page.evaluate("() => window.__elosernBridge.store.setReducedMotion('off')")
        page.locator('[data-testid="message-window"]').click()
        page.wait_for_function(
            """() => { const w = document.querySelector('[data-testid="message-window"]');
              return document.querySelector('[data-testid="message-page"]').getAttribute('data-page') === '2'
                && w.getAttribute('data-typing') === 'true'; }""",
            timeout=15000,
        )
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::text-speed-and-auto-advance-are-client-local-reading-preferences-the-settings-surface-owns"
    )
    def test_reading_preferences_persist(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        page.locator('[data-testid="nav-settings"]').click()
        page.wait_for_selector('[data-testid="settings-overlay"]', timeout=15000)
        normal = page.locator('[data-testid="settings-overlay-text-speed-normal"]')
        fast = page.locator('[data-testid="settings-overlay-text-speed-fast"]')
        auto = page.locator('[data-testid="settings-overlay-auto-advance"]')
        self.assertEqual(normal.get_attribute("aria-pressed"), "true")
        self.assertFalse(auto.is_checked(), "auto-advance is off by default")

        fast.click()
        auto.check()
        page.wait_for_function(
            "() => { const v = window.__elosernBridge.store.view;"
            " return v.textSpeed === 'fast' && v.autoAdvance === true; }",
            timeout=15000,
        )
        self.assertEqual(fast.get_attribute("aria-pressed"), "true")
        self.assertIn("on", fast.get_attribute("class").split())
        stored = page.evaluate("() => JSON.parse(localStorage.getItem('elosern.layout'))")
        self.assertEqual(stored["layout_version"], 2)
        self.assertEqual(stored["preferences"]["textSpeed"], "fast")
        self.assertIs(stored["preferences"]["autoAdvance"], True)
        self.assertEqual(sent_action_count(page), 0, "no reading preference dispatches a ui_action")

        page.reload()
        wait_for_store_state(page, lambda s: bool(s.get("connected")))
        page.wait_for_function(
            "() => { const v = window.__elosernBridge.store.view;"
            " return v.textSpeed === 'fast' && v.autoAdvance === true; }",
            timeout=15000,
        )
        # After the reload a fully shown page with a next page advances on its
        # own: a short `out` page, then a `sys` line that starts page 2. The
        # reconnect's own lines settle first so none joins this response.
        wait_for_presentation_settled(page)
        wait_for_narrative_settled(page, 0)
        self._settle_window_mount(page)
        page.evaluate(
            """() => {
              const store = window.__elosernBridge.store;
              store.appendText('in', 'look');
              store.appendText('out', '渡口。');
              store.appendText('sys', '渡口有 1 名可互動的人物。');
            }"""
        )
        page.wait_for_function(
            """() => { const p = document.querySelector('[data-testid="message-page"]');
              return p && p.getAttribute('data-page') === '2'; }""",
            timeout=30000,
        )
        page.locator('[data-testid="nav-settings"]').click()
        page.wait_for_selector('[data-testid="settings-overlay"]', timeout=15000)
        self.assertTrue(page.locator('[data-testid="settings-overlay-auto-advance"]').is_checked())
        self.assertEqual(
            page.locator('[data-testid="settings-overlay-text-speed-fast"]').get_attribute("aria-pressed"),
            "true",
        )
        self.assertEqual(sent_action_count(page), 0)
        page.close()

    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control"
    )
    def test_field_is_focusable_without_an_opening_action(self):
        page = self.logged_in_page()
        # webclient-collapsible-command-line: the field is one pointer action
        # away through the ⌨ toggle in `#band-message`.
        self.assertFalse(page.locator("#inputfield").is_visible())
        page.locator('[data-testid="command-line-toggle"]').click()
        _wait_field_focused(page)
        self.assertEqual(
            page.locator('[data-testid="anchor-command-line"]').get_attribute("data-expanded"),
            "true",
        )
        self.assertTrue(page.locator(".inputfieldwrapper").is_visible())

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe"
    )
    def test_slash_focuses_the_always_present_field(self):
        page = self.logged_in_page()
        # `/` outside an editable control expands the collapsed command line
        # and moves focus into `#inputfield` without inserting a literal `/`.
        anchor = page.locator('[data-testid="anchor-command-line"]')
        self.assertEqual(anchor.get_attribute("data-expanded"), "false")
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)
        self.assertEqual(anchor.get_attribute("data-expanded"), "true")
        # A second `/` while the field is focused types the slash (the shell's
        # claim is not made over an editable control).
        page.keyboard.press("/")
        page.wait_for_timeout(150)
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            "/",
            "a repeated / while the field is focused types a literal slash",
        )
        # Escape collapses the line and returns focus to the dock; pressing `/`
        # expands and focuses the field again.
        page.keyboard.press("Escape")
        wait_command_field_released(page)
        page.keyboard.press("/")
        _wait_field_focused(page)
        self.assertEqual(anchor.get_attribute("data-expanded"), "true")

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe"
    )
    def test_slash_typed_in_a_focused_editable_stays_ordinary_text(self):
        page = self.logged_in_page()
        self._open_command_line(page)
        page.keyboard.type("whisper ")
        page.keyboard.press("/")
        page.wait_for_timeout(120)
        # The slash is ordinary text inside the field; the command line is
        # permanently present (H5, design D1) — it never opens or closes.
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            "whisper /",
        )
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"))
        self.assertTrue(
            page.evaluate(
                "document.activeElement === document.getElementById('inputfield')"
            )
        )

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe"
    )
    def test_slash_while_the_rest_form_is_open_never_toggles_the_command_line(self):
        page = self.logged_in_page()
        # Open the rest form (Wait/休息 → 休息一段時間).
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
            _press(page, "ArrowRight")
        else:
            raise AssertionError("the wait tab never reached focus")
        _press(page, "Enter")  # Wait/休息
        _press(page, "ArrowRight")  # 睡眠至完全恢復
        _press(page, "ArrowRight")  # 休息 N 小時 (opens the rest form)
        _press(page, "Enter")
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
        self.assertEqual(
            page.locator('[data-testid="anchor-command-line"]').get_attribute("data-expanded"),
            "false",
        )
        # A slash while the rest form owns the keyboard is claimed: the command
        # line stays collapsed.
        page.keyboard.press("/")
        page.wait_for_timeout(150)
        self.assertEqual(
            page.locator('[data-testid="anchor-command-line"]').get_attribute("data-expanded"),
            "false",
            "the command line stays collapsed while the rest form owns the keyboard",
        )
        self.assertTrue(
            page.evaluate("document.querySelector('[data-testid=\"exploration-rest-form\"]') !== null")
        )

    @covers_requirement(
        "webclient-desktop-shell::player-input-lines-are-part-of-the-narrative-stream-with-a-divider"
    )
    def test_typed_command_echoes_one_input_line_with_a_divider(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._open_command_line(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        # The accepted ordinary send clears the field, collapses the command
        # line, and restores focus to the action dock.
        wait_command_field_released(page)
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"), ""
        )
        self.assertEqual(
            page.locator('[data-testid="message-window"] .inp').count(),
            0,
            "input lines never render in the message window",
        )
        _wait_inp_line(page, 1, keep_open=True)
        inp = page.locator('[data-testid="fulllog-overlay"] .inp').first
        self.assertEqual(inp.inner_text(), "look")
        # The echo line is preceded by exactly one divider hairline in the full log.
        self.assertEqual(page.locator('[data-testid="fulllog-overlay"] .narrative-divider').count(), 1)
        self.assertTrue(
            page.evaluate(
                "() => {"
                "  const line = document.querySelector('[data-testid=\"fulllog-overlay\"] .inp');"
                "  return line.previousElementSibling !== null && "
                "    line.previousElementSibling.classList.contains('narrative-divider');"
                "}"
            )
        )
        sends = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "text"
        ]
        self.assertTrue(any("look" in str(item) for item in sends))

    @covers_requirement(
        "webclient-desktop-shell::player-input-lines-are-part-of-the-narrative-stream-with-a-divider"
    )
    def test_typed_command_while_reading_flushes_to_new_response_and_logs_divider(self):
        page = self.logged_in_page()
        _clear_narrative(page)
        _append_multipage_response(page)
        surface = page.locator('[data-testid="message-page"]')
        marker = page.locator('[data-testid="message-page-marker"]')
        self.assertEqual(surface.get_attribute("data-page"), "1")
        self.assertEqual(marker.inner_text(), "▼")
        self.assertIn("【段落1】", surface.inner_text())
        self.assertNotIn("【段落15】", surface.inner_text())

        # Sending a typed command while page 1 of the previous response is on
        # screen flushes the unread pages to the full log and presents the
        # command's reply from its first page, with no .inp in the window.
        before_len = narrative_log_length(page)
        self._open_command_line(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_command_field_released(page)
        wait_for_narrative_settled(page, before_len)
        self.assertEqual(page.locator('[data-testid="message-window"] .inp').count(), 0)
        self.assertEqual(surface.get_attribute("data-page"), "1")

        # The full log shows the earlier response's unread text and the .inp
        # line preceded by a .narrative-divider.
        _wait_inp_line(page, 2, "look", exact=True, keep_open=True)
        overlay_text = page.locator('[data-testid="fulllog-overlay"]').inner_text()
        self.assertIn("【段落1】", overlay_text)
        self.assertIn("【段落15】", overlay_text)
        self.assertEqual(
            page.locator('[data-testid="fulllog-overlay"] .narrative-divider').count(),
            2,
        )

    @covers_requirement(
        "webclient-input-narrative::the-message-window-s-reading-controls-advance-pages-and-a-new-action-flushes-unread-pages"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-message-window-presents-the-current-response-one-page-at-a-time-in-the-band-s-message-region"
    )
    def test_message_window_repages_on_resize(self):
        page = self.logged_in_page((1920, 1080))
        _append_multipage_response(page)
        surface = page.locator('[data-testid="message-page"]')
        page.locator('[data-testid="message-window"]').click()
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="message-page"]',
                "predicate": (
                    "() => document.querySelector('[data-testid=\"message-page\"]')"
                    ".getAttribute('data-page') === '2'"
                ),
                "description": "advanced to page 2 at 1920x1080",
            },
        )
        page_2_text = surface.inner_text().strip()
        self.assertTrue(page_2_text)
        anchor_prefix = page_2_text[:6]
        self.assertNotIn(
            anchor_prefix,
            "【段落1】",
            "page 2's leading tag must be distinct from page 1's leading tag",
        )
        live_before = page.locator('[data-testid="message-live"]').inner_text()

        # Shrink the viewport from 1920x1080 to 1280x720 and wait for the
        # ResizeObserver re-page pass to settle across two consecutive reads.
        page.set_viewport_size({"width": 1280, "height": 720})
        page.wait_for_timeout(150)
        previous_sig = None
        for _ in range(20):
            page.wait_for_timeout(120)
            sig = (surface.get_attribute("data-page"), surface.get_attribute("data-pages"))
            if sig == previous_sig and sig[0] is not None:
                break
            previous_sig = sig
        after_text = surface.inner_text()
        self.assertIn(
            anchor_prefix,
            after_text,
            "re-paging on resize must keep the page-2 anchor substring on screen",
        )
        self.assertEqual(
            page.locator('[data-testid="message-live"]').inner_text(),
            live_before,
            "a resize re-page announces nothing new",
        )
        page.close()

    @covers_requirement(
        "webclient-desktop-shell::player-input-lines-are-part-of-the-narrative-stream-with-a-divider"
    )
    def test_first_log_line_needs_no_divider(self):
        page = self.logged_in_page()
        # Reset the store's narrative log so the next input line is the log's
        # first line (no divider hairline before the very first line). The store is
        # a Pinia store: clear the unwrapped array in place; the clear and the
        # append run in ONE evaluate so no server update can interleave.
        page.evaluate(
            """() => {
              const store = window.__elosernBridge.store;
              store.narrative.length = 0;
              Elosern.narrativeInput.appendInput('first');
            }"""
        )
        _wait_inp_line(page, 1, keep_open=True)
        self.assertEqual(
            page.locator('[data-testid="fulllog-overlay"] .narrative-divider').count(),
            0,
            "the first log line carries no divider",
        )
        page.evaluate("() => Elosern.narrativeInput.appendInput('second')")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="fulllog-overlay"]',
                "predicate": (
                    "() => document.querySelectorAll("
                    "'[data-testid=\"fulllog-overlay\"] .narrative-divider').length === 1"
                ),
                "description": "narrative divider rendered",
            },
        )
        self.assertEqual(
            page.locator('[data-testid="fulllog-overlay"] .inp').count(), 2
        )
        self.assertTrue(
            page.evaluate(
                "() => {"
                "  const lines = document.querySelectorAll('[data-testid=\"fulllog-overlay\"] .inp');"
                "  const second = lines[lines.length - 1];"
                "  return second.previousElementSibling !== null && "
                "    second.previousElementSibling.classList.contains('narrative-divider');"
                "}"
            )
        )

    @covers_requirement(
        "webclient-input-narrative::a-deliberate-mutation-echo-appears-exactly-once-at-dispatch"
    )
    def test_catalog_echo_never_alters_the_ui_action_envelope(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # A staged submit with a display descriptor echoes its resolved line,
        # while the wire envelope carries exactly the action payload. The clear
        # and the dispatch run in ONE evaluate (Pinia store: clear the unwrapped
        # array in place) so no server update interleaves.
        # The staged payload and display descriptors are inert here: the
        # journey proves the envelope passes through byte-identical and the
        # echo renders from the descriptor only — nothing resolves these
        # values against a catalog — so they are authored fixture data.
        payload = {"skill_key": "t_ember_burst", "target_ids": [1]}
        page.evaluate(
            """(p) => {
              window.__elosernBridge.store.narrative.length = 0;
              return Elosern.actions.submit('combat.cast', p,
                { skillLabel: '燼心爆', targetLabel: '燼殼工蟲' });
            }""",
            payload,
        )
        _wait_inp_line(page, 1, "cast 燼心爆=燼殼工蟲")
        envelopes = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "ui_action"
        ]
        self.assertEqual(len(envelopes), 1)
        envelope = envelopes[0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(
            json.dumps(envelope["payload"], sort_keys=True),
            json.dumps(payload, sort_keys=True),
            "the echo must never leak display data into the payload",
        )
        # The identical submission without a display descriptor dispatches the
        # byte-identical payload; the catalog cannot resolve a cast line
        # without the skill label, so nothing echoes.
        self._wait_action_idle(page)
        page.evaluate(
            "() => Elosern.actions.submit('combat.cast', "
            "{ skill_key: 't_ember_burst', target_ids: [1] })"
        )
        self._wait_action_idle(page)
        envelopes = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "ui_action"
        ]
        self.assertEqual(len(envelopes), 2)
        self.assertEqual(
            json.dumps(envelopes[0]["payload"], sort_keys=True),
            json.dumps(envelopes[1]["payload"], sort_keys=True),
        )
        _wait_inp_line(page, 1, "cast 燼心爆=燼殼工蟲")
        # A mutation the catalog can resolve without any display descriptor
        # still echoes exactly once at dispatch (forfeit needs no label).
        page.evaluate("() => Elosern.actions.submit('combat.forfeit')")
        _wait_inp_line(page, 2, "combat forfeit", exact=True)

    def _wait_action_idle(self, page, timeout=20000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            if not page.evaluate("Elosern.actions.client.isInFlight()"):
                return
            page.wait_for_timeout(250)
        raise AssertionError("action client never released its lock")

    @covers_requirement(
        "webclient-input-narrative::echoed-command-lines-never-affect-state"
    )
    def test_markup_like_labels_render_as_literal_text(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # Clear the store's narrative and dispatch in one evaluate so no server
        # update interleaves. (Pinia store: clear the unwrapped array in place.)
        page.evaluate(
            """() => {
              window.__elosernBridge.store.narrative.length = 0;
              Elosern.actions.submit('explore.engage', { monster_id: 'no_such_monster' },
              { targetLabel: '<script>alert(1)</script>' });
            }"""
        )
        _wait_inp_line(page, 1, "<script>alert(1)</script>", keep_open=True)
        # The line is a single literal text node: no element was created.
        self.assertEqual(
            page.evaluate(
                "() => {"
                "  const lines = document.querySelectorAll('[data-testid=\"fulllog-overlay\"] .inp');"
                "  return lines[lines.length - 1].childElementCount;"
                "}"
            ),
            0,
        )
        self.assertEqual(page.locator('[data-testid="fulllog-overlay"] .inp script').count(), 0)


class InputEchoExplorationTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Move/free-form input-echo journeys on one isolated exploration server."""

    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_EXPLORATION"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def _wait_exploration_available(self, page, timeout=30000):
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("exploration", {}).get("available") is True,
            timeout=timeout,
        )
        return store_state(page)["panels"].get("exploration")

    def _wait_panel(self, page, name, predicate, timeout=30000):
        def _panel_ready(state):
            panel = (state.get("panels") or {}).get(name)
            return panel is not None and predicate(panel)
        wait_for_store_state(page, _panel_ready, timeout=timeout)
        return store_state(page)["panels"].get(name)

    def _reset_root(self, page):
        focus_action_dock(page)
        page.evaluate("window.__elosernBridge.store.resetFramesToRoot()")
        page.wait_for_timeout(60)


    @covers_requirement(
        "webclient-desktop-shell::player-input-lines-are-part-of-the-narrative-stream-with-a-divider"
    )
    @covers_requirement(
        "webclient-input-narrative::the-command-line-catalog-resolves-a-display-line-deterministically"
    )
    def test_button_action_echoes_its_resolved_command_line(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_exploration_available(page)
        move_rows = panel.get("move") or []
        self.assertTrue(move_rows, "the fixture must offer exits")
        first_exit_label = move_rows[0]["label"]

        activate_first_overview_exit(page)  # the overview's first exit chip
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True
            and p["current_node"] != fixture_home_node_id(),
        )
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        _wait_inp_line(page, 1, keep_open=True)
        inp = page.locator('[data-testid="fulllog-overlay"] .inp').first
        self.assertEqual(
            inp.inner_text(),
            first_exit_label,
            "exit traversal echoes the server-authored exit label, never a guessed command",
        )
        self.assertEqual(page.locator('[data-testid="fulllog-overlay"] .narrative-divider').count(), 1)

    @covers_requirement(
        "webclient-input-narrative::a-deliberate-mutation-echo-appears-exactly-once-at-dispatch"
    )
    def test_freeform_dialogue_echoes_exactly_one_line_at_dispatch(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_exploration_available(page)
        # The seed creates the scripted host first, so the LLMNPC bard is the
        # SECOND present target carrying the v3 conversation affordance (the
        # panel no longer marks free-form talk).
        talking = [
            target
            for target in panel.get("interact") or []
            if any(
                affordance.get("action_id") == "explore.talk_open"
                for affordance in target.get("affordances") or []
            )
        ]
        self.assertGreaterEqual(
            len(talking), 2, "the fixture must offer the host and the LLMNPC bard"
        )
        bard = talking[1]

        # The overview's 人物 chip for the bard opens its verb popover
        # (webclient-scene-overview-swap); 交談 opens the conversation, whose
        # caption carries the free row.
        activate_overview_chip(page, "target-%s" % bard["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        page.wait_for_selector('[data-testid="dialogue-freeform"]', timeout=30000)
        page.click('[data-testid="dialogue-freeform"]')
        _wait_field_focused(page)
        speech = "你好，詩人"
        page.keyboard.type(speech)
        page.keyboard.press("Enter")
        # The interaction completed: focus back on the dock (H5, design D2)
        # and the command line is still present (it is never closed).
        wait_command_field_released(page)
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 1)
        # Two deliberate mutations echoed: the conversation open, then the
        # one free-form send.
        _wait_inp_line(page, 2, keep_open=True)
        lines = page.locator('[data-testid="fulllog-overlay"] .inp')
        self.assertEqual(
            lines.nth(0).inner_text(),
            "talk %s" % bard["display_name"],
            "opening the conversation echoes the keyword-less talk line",
        )
        self.assertEqual(
            lines.nth(1).inner_text(),
            "talk %s %s" % (bard["display_name"], speech),
            "the free-form send echoes exactly one resolved line",
        )
        self.assertEqual(
            lines.count(),
            2,
            "no second raw-text echo may appear",
        )

    @covers_requirement(
        "webclient-input-narrative::a-deliberate-mutation-echo-appears-exactly-once-at-dispatch"
    )
    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control"
    )
    def test_locked_borrowed_send_keeps_the_speech_and_never_echoes(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # The overview's 人物 chip for the bard opens its verb popover; 交談
        # opens the conversation (whose caption carries the free row) and the
        # locked send is attempted after that open.
        panel = self._wait_exploration_available(page)
        talking = [
            target
            for target in panel.get("interact") or []
            if any(
                affordance.get("action_id") == "explore.talk_open"
                for affordance in target.get("affordances") or []
            )
        ]
        self.assertGreaterEqual(
            len(talking), 2, "the fixture must offer the host and the LLMNPC bard"
        )
        bard = talking[1]
        activate_overview_chip(page, "target-%s" % bard["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        page.wait_for_selector('[data-testid="dialogue-freeform"]', timeout=30000)
        page.click('[data-testid="dialogue-freeform"]')
        _wait_field_focused(page)
        inp_before = page.evaluate(
            "() => window.__elosernBridge.store.narrative.filter((l) => l && l.kind === 'in').length"
        )

        # Disconnect: the store locks all mutations while preserving the view.
        page.evaluate("Evennia.connection.close()")
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
        )
        speech = "話到嘴邊又吞了回去"
        page.keyboard.type(speech)
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        # Nothing dispatched, nothing echoed, and the speech is not lost.
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 0)
        self.assertEqual(
            page.evaluate(
                "() => window.__elosernBridge.store.narrative.filter((l) => l && l.kind === 'in').length"
            ),
            inp_before,
            "a locked borrowed send must never echo",
        )
        self.assertEqual(
            page.locator('[data-testid="anchor-command-line"]').get_attribute("data-expanded"),
            "true",
            "a locked borrowed send keeps the command line expanded",
        )
        self.assertTrue(
            page.evaluate("document.activeElement === document.getElementById('inputfield')"),
            "a locked borrowed send keeps focus in the field",
        )
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            speech,
            "the typed speech must remain in the field",
        )

    @covers_requirement(
        "webclient-input-narrative::the-message-window-s-reading-controls-advance-pages-and-a-new-action-flushes-unread-pages"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-message-window-presents-the-current-response-one-page-at-a-time-in-the-band-s-message-region"
    )
    def test_message_window_pages_and_flushes(self):
        page = self.logged_in_page((1920, 1080))
        self._wait_exploration_available(page)
        _append_multipage_response(page)

        surface = page.locator('[data-testid="message-page"]')
        marker = page.locator('[data-testid="message-page-marker"]')
        self.assertEqual(surface.get_attribute("data-page"), "1")
        self.assertEqual(marker.inner_text(), "▼")

        # At 1920x1080 with default prose scale (1), computed font size is 28px (±0.5px),
        # every line's content box is at most 42em wide, and the control strip's
        # marker, 日誌, and ⌨ rects are pairwise disjoint left-to-right.
        metrics = page.evaluate(
            """() => {
              const p = document.querySelector('[data-testid="message-page"]');
              const cs = getComputedStyle(p);
              const fontSize = parseFloat(cs.fontSize);
              const contentWidth = p.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
              const lineWidths = Array.from(p.querySelectorAll('.narrative-line'), (el) => el.getBoundingClientRect().width);
              const mRect = document.querySelector('[data-testid="message-page-marker"]').getBoundingClientRect();
              const lRect = document.querySelector('[data-testid="message-log-open"]').getBoundingClientRect();
              const tRect = document.querySelector('[data-testid="command-line-toggle"]').getBoundingClientRect();
              return {
                fontSize,
                contentWidth,
                maxLineWidth: Math.max(0, ...lineWidths),
                markerRight: mRect.right,
                logLeft: lRect.left,
                logRight: lRect.right,
                toggleLeft: tRect.left,
              };
            }"""
        )
        self.assertAlmostEqual(metrics["fontSize"], 28.0, delta=0.5)
        self.assertLessEqual(metrics["contentWidth"], metrics["fontSize"] * 42.0 + 1.0)
        self.assertLessEqual(metrics["maxLineWidth"], metrics["fontSize"] * 42.0 + 1.0)
        self.assertLessEqual(metrics["markerRight"], metrics["logLeft"])
        self.assertLessEqual(metrics["logRight"], metrics["toggleLeft"])

        # Enter on the dock activates the dock and does not advance the page.
        focus_action_dock(page)
        _press(page, "Enter")
        self.assertEqual(surface.get_attribute("data-page"), "1")
        _press(page, "Escape")

        # Enter on the focused page surface advances to page 2 without activating the dock.
        surface.focus()
        page.keyboard.press("Enter")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="message-page"]',
                "predicate": (
                    "() => document.querySelector('[data-testid=\"message-page\"]')"
                    ".getAttribute('data-page') === '2'"
                ),
                "description": "message-page advanced to page 2 via Enter",
            },
        )
        self.assertEqual(sent_action_count(page), 0)

        # Inject a fresh multi-page response with an unread tail, then dispatch
        # a real dock move while still on page 1: the window flushes to page 1
        # of the move's response, and the full log retains the unread tail.
        _append_multipage_response(page)
        self.assertEqual(surface.get_attribute("data-page"), "1")
        self.assertNotIn("【段落15】", surface.inner_text())

        activate_first_overview_exit(page)  # the overview's first exit chip
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True
            and p["current_node"] != fixture_home_node_id(),
        )
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="message-page"]',
                "predicate": (
                    "() => { const p = document.querySelector('[data-testid=\"message-page\"]');"
                    " return !!p && p.getAttribute('data-page') === '1'"
                    " && !p.innerText.includes('【段落1】'); }"
                ),
                "description": "message-page shows page 1 of the move response",
            },
        )
        page.locator('[data-testid="message-log-open"]').click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', timeout=15000)
        self.assertIn(
            "【段落15】",
            page.locator('[data-testid="fulllog-overlay"]').inner_text(),
            "the full log retains the unread pages flushed by the move",
        )
        page.close()


if __name__ == "__main__":
    import unittest

    unittest.main()
