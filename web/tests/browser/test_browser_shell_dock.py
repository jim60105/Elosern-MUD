"""Desktop-shell acceptance: the action-dock mockup command surface, its shortcut legend, and the bounded full-log action.
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


class ShellAcceptanceTest(BrowserAcceptanceTest):
    """Every required surface at 1440x900 and 1280x720, plus keyboard journeys."""
    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable",
        "webclient-desktop-shell::theme-and-controls-remain-accessible",
    )
    def test_action_dock_renders_the_mockup_command_surface(self):
        for viewport in ((1440, 900), (1280, 720)):
            page = self.logged_in_page(viewport)
            dock = page.locator("#action-dock")
            self.assertTrue(dock.is_visible())
            # webclient-avg-stage-shell (design D1): the painted band (the
            # draft's `.dockwrap` chrome) lives on the full-width bottom band
            # (`.stage-band`) — the `--line` top border
            # (`1px solid var(--ink-700)`) is drawn there.
            # The obsidian-gold wave re-pointed the ink tokens (tokens.css:
            # --ink-700 = #363638); assert against the resolved token instead
            # of a pinned rgb literal so the pin follows the token, not a
            # color value.
            tokens = page.evaluate(
                """() => {
                  const rgb = (name) => {
                    const raw = getComputedStyle(document.documentElement)
                      .getPropertyValue(name).trim();
                    const n = parseInt(raw.slice(1), 16);
                    return 'rgb(' + [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(', ') + ')';
                  };
                  return { line: rgb('--ink-700'), ground: rgb('--ink-780') };
                }"""
            )
            frame = page.locator('[data-testid="stage-band"]').evaluate(
                """el => {
                  const style = getComputedStyle(el);
                  return { borderTop: style.borderTopColor,
                           backgroundImage: style.backgroundImage };
                }"""
            )
            self.assertEqual(
                frame["borderTop"], tokens["line"],
                "the dock band's top border is the shared --ink-700 token",
            )
            self.assertIn(
                "gradient",
                frame["backgroundImage"],
                "the full-width band paints the draft's upward gradient",
            )
            # The shortcut legend is the tab bar's trailing hint carrying the
            # draft's markup (the single `action-dock-description` element).
            description = page.locator('[data-testid="action-dock-description"]').inner_text()
            for keyword in ("數字鍵 1–4", "Enter 執行", "Esc 返回"):
                self.assertIn(keyword, description)
            # The root is now the tab bar (H3): one row of tabs (the root
            # frame's items as tabs). The tab count varies 5-8 with
            # quest/inventory capability availability (H3 design D5 adds the
            # 建議 tab whenever the suggestions envelope is not `unavailable`).
            cells = page.locator("#action-dock [data-item-key]")
            self.assertGreaterEqual(cells.count(), 5)
            self.assertLessEqual(cells.count(), 8)
            # The open/focused tab carries the muted-gold fill (the `--on`
            # class; webclient-desktop-shell: "the open entry marked by a
            # muted-gold fill") — the obsidian-gold wave re-pointed the
            # draft's seal-red gradient to the flat --gold-glow token
            # (DockTabBar.vue .dock-tab-bar__tab--on). Assert the computed
            # fill against the token resolved through a probe node inside
            # the dock subtree (the token is declared on .elosern-root, not
            # :root, so a documentElement read resolves to nothing; and the
            # raw token text is not the computed color string).
            focused = page.locator("#action-dock .dock-tab-bar__tab--on").first
            gold_glow = page.evaluate(
                """() => {
                    const probe = document.createElement('span');
                    probe.style.background = 'var(--gold-glow)';
                    document.querySelector('#action-dock').appendChild(probe);
                    const rgb = getComputedStyle(probe).backgroundColor;
                    probe.remove();
                    return rgb;
                }"""
            )
            self.assertEqual(
                focused.evaluate("el => getComputedStyle(el).backgroundColor"),
                gold_glow,
                "the focused tab carries the muted-gold --gold-glow fill",
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
        "webclient-contextual-hud::the-dock-s-shortcut-legend-names-only-real-keyboard-behaviour-and-renders-as-one-visible-instance"
    )
    def test_dock_shortcut_legend_renders_once_with_real_behaviour_wording(self):
        """The dock's shortcut legend renders as exactly one visible instance,
        carries the reference draft's wording and ``<kbd>`` structure, and is
        the only element carrying the legend's test hook
        (webclient-align-01-dock-chrome).

        The old visually-hidden ``action-dock-description`` duplicate was
        deleted: the tab bar's trailing hint IS the hook. The legend names
        only implemented behaviour (1–4 pick cards, Enter activates, Esc pops
        one frame); the ``/`` focus binding stays implemented but the
        reference's legend does not advertise it, so neither does this one.
        """
        page = self.logged_in_page()
        focus_action_dock(page)
        hint = page.locator(".dock-tab-bar__hint")
        # Exactly one legend element, and it carries the test hook.
        self.assertEqual(
            hint.count(), 1, "the tab bar carries exactly one legend"
        )
        self.assertEqual(
            page.locator('[data-testid="action-dock-description"]').count(), 1,
            "exactly one element carries the legend hook",
        )
        self.assertTrue(
            page.locator('[data-testid="action-dock-description"]').first.is_visible(),
            "the hook-bearing element IS the visible legend",
        )
        self.assertEqual(
            page.locator(".action-dock__description").count(), 0,
            "the visually-hidden duplicate is gone",
        )
        # The reference draft's wording (index.html line 855).
        hint_text = hint.first.inner_text()
        self.assertEqual(hint_text, "數字鍵 1–4 · Enter 執行 · Esc 返回")
        self.assertNotIn("/ 聚焦指令列", hint_text)
        self.assertNotIn("方向鍵選擇", hint_text)
        # The draft's <kbd> structure: exactly two styled kbd elements.
        kbd = page.locator(".dock-tab-bar__hint kbd")
        self.assertEqual(kbd.count(), 2, "the legend renders two kbd elements")
        self.assertEqual(
            [kbd.nth(0).inner_text(), kbd.nth(1).inner_text()],
            ["Enter", "Esc"],
        )
        kbd_style = kbd.first.evaluate(
            """el => {
              const s = getComputedStyle(el);
              return { background: s.backgroundColor,
                       borderBottomWidth: s.borderBottomWidth };
            }"""
        )
        self.assertEqual(
            kbd_style["background"],
            page.evaluate(
                """() => {
                  const raw = getComputedStyle(document.documentElement)
                    .getPropertyValue('--ink-780').trim();
                  const n = parseInt(raw.slice(1), 16);
                  return 'rgb(' + [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(', ') + ')';
                }"""
            ),
            "the kbd carries the --ink-780 ground",
        )
        self.assertEqual(
            kbd_style["borderBottomWidth"], "2px",
            "the kbd carries the draft's 2px bottom border",
        )

    @covers_requirement(
        "webclient-desktop-shell::narrative-output-remains-the-authoritative-text-surface-and-is-read-page-by-page"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-message-window-presents-the-current-response-one-page-at-a-time-in-the-band-s-message-region"
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
        control = page.locator('[data-testid="message-log-open"]')
        self.assertEqual(control.count(), 1, "the full-log control renders in the message region")
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
            "() => { const c = document.querySelector('[data-testid=\"message-log-open\"]'); "
            "const a = document.activeElement; return c && c === a; }"
        )
        self.assertTrue(focus_restored, "focus is restored to the control that opened the full log")
