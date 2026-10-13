"""Desktop-shell acceptance: the action-dock mockup command surface, its shortcut legend, and the bounded full-log action.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from ._journey_support import _combat_panel, _inject_snapshot, _wait_mode
from .browser_helpers import (
    activate_overview_chip,
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
    """Every required surface at 1451x790 and 2560x1440, plus keyboard journeys."""
    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable",
        "webclient-desktop-shell::theme-and-controls-remain-accessible",
        "webclient-contextual-hud::the-bottom-band-separates-material-and-focus-without-obscuring-controls",
        "webclient-exit-compass::compass-behavior-is-verified-in-the-live-client-at-two-viewports",
        "webclient-room-actions::retired-exploration-surfaces-are-gone-and-room-actions-are-verified-in-the-live-client",
    )
    def test_action_dock_renders_the_mockup_command_surface(self):
        for viewport in ((1451, 790), (2560, 1440)):
            page = self.logged_in_page(viewport)
            dock = page.locator("#action-dock")
            self.assertTrue(dock.is_visible())
            # webclient-avg-stage-shell (design D1): the painted band lives
            # on the full-width bottom band (`.stage-band`). Its stage seam
            # (webclient-band-material-pass) is decoration drawn by the
            # band's pseudo layers: a gold edge on `::after` and a feather on
            # `::before`, both inert to the pointer.
            frame = page.locator('[data-testid="stage-band"]').evaluate(
                """el => {
                  const style = getComputedStyle(el);
                  const edge = getComputedStyle(el, '::after');
                  const feather = getComputedStyle(el, '::before');
                  return { backgroundImage: style.backgroundImage,
                           edge: edge.backgroundImage,
                           edgeEvents: edge.pointerEvents,
                           feather: feather.backgroundImage,
                           featherEvents: feather.pointerEvents };
                }"""
            )
            self.assertIn(
                "gradient",
                frame["backgroundImage"],
                "the full-width band paints its ink ground",
            )
            self.assertIn("gradient", frame["edge"], "the band draws its gold seam edge")
            self.assertIn("gradient", frame["feather"], "the band draws the seam feather")
            self.assertEqual(frame["edgeEvents"], "none", "the seam edge is pointer-inert")
            self.assertEqual(frame["featherEvents"], "none", "the seam feather is pointer-inert")
            # The exploration command panel carries no key-hint legend
            # (exploration-exit-compass): its bindings live in the help
            # overlay, and the pane runs to the band's foot instead.
            self.assertEqual(
                page.locator('[data-testid="action-dock-description"]').count(),
                0,
                f"no legend in exploration {viewport}",
            )
            geometry = page.evaluate(
                """() => {
                  const pane = document.querySelector('.action-dock__pane').getBoundingClientRect();
                  const region = document.querySelector('[data-testid="anchor-band-command"]').getBoundingClientRect();
                  const compass = document.querySelector('#action-dock [data-testid="exit-compass"]').getBoundingClientRect();
                  return { paneBottom: pane.bottom, regionBottom: region.bottom,
                           compassBottom: compass.bottom, compassTop: compass.top,
                           paneTop: pane.top, compassWidth: compass.width, compassHeight: compass.height };
                }"""
            )
            self.assertLessEqual(geometry["paneBottom"], geometry["regionBottom"] + 0.5, f"{viewport} {geometry}")
            self.assertGreaterEqual(geometry["compassTop"], geometry["paneTop"] - 0.5, f"{viewport} {geometry}")
            self.assertLessEqual(geometry["compassBottom"], geometry["paneBottom"] + 0.5, f"{viewport} {geometry}")
            self.assertAlmostEqual(geometry["compassWidth"], geometry["compassHeight"], delta=1)
            # The exploration root is the exit compass beside the 建議 pill
            # and the readout (exploration-room-actions): no chip row, no
            # combat list, and no dock row at all.
            self.assertEqual(
                page.locator('#action-dock [data-pane-kind="commands"]').count(),
                0,
                "exploration renders the compass pane, never the combat command list",
            )
            # A negative check read through `evaluate`, so the frozen-contract
            # scanner does not re-register the retired hook.
            self.assertEqual(page.evaluate("() => document.querySelectorAll('.scene-overview').length"), 0)
            self.assertEqual(
                page.locator('#action-dock [data-testid="exploration-root"]').count(),
                1,
                "the exploration root renders exactly one compass pane",
            )
            self.assertEqual(page.locator("#action-dock [data-item-key]").count(), 0)
            # A pointed-at room action carries the muted-gold fill
            # (webclient-desktop-shell: the focused or hovered control is
            # marked by a muted-gold fill) — the flat --gold-glow token,
            # resolved through a probe node inside the client root (the token
            # is declared on .elosern-root, not :root).
            wait_button = page.locator('[data-anchor="map"] [data-testid="place-card-wait"]')
            wait_button.hover()
            page.wait_for_timeout(200)
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
                wait_button.evaluate("el => getComputedStyle(el).backgroundColor"),
                gold_glow,
                "the hovered 等待 button carries the muted-gold --gold-glow fill",
            )
            page.mouse.move(0, 0)
            # The exploration screen draws no detail pane: server-authored
            # reasons appear in the shared readout.
            self.assertEqual(page.locator('[data-testid="exploration-detail"]').count(), 0)
            # The place card's 等待 opens the wait card over the stage; the
            # command region keeps its geometry.
            activate_overview_chip(page, "wait")
            page.wait_for_selector('[data-anchor="choices"] [data-testid="wait-card"]', timeout=15000)
            pane_display = page.evaluate(
                "() => { const v = document.querySelector('[data-anchor=\"choices\"] [data-testid=\"wait-card\"]');"
                " return v ? getComputedStyle(v).display : null; }"
            )
            self.assertEqual(pane_display, "flex", "the wait card uses the card frame's layout")
            # Escape closes the card and returns focus to 等待; the router never
            # left its root.
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)
            self.assertEqual(store_state(page)["dockDepth"], 1)
            self.assertIsNone(store_state(page)["roomCard"])
            self.assertTrue(
                page.evaluate(
                    "() => document.activeElement === document.querySelector("
                    "'[data-anchor=\"map\"] [data-testid=\"place-card-wait\"]')"
                ),
                "Escape returns focus to the 等待 button",
            )
            self.assertEqual(page.locator('[data-anchor="choices"] [data-testid="wait-card"]').count(), 0)

    @covers_requirement(
        "webclient-contextual-hud::the-dock-s-shortcut-legend-names-only-real-keyboard-behaviour-and-renders-as-one-visible-instance"
    )
    @covers_requirement(
        "webclient-exit-compass::the-controls-reference-documents-the-compass-and-the-exploration-panel-shows-no-key-hints"
    )
    def test_dock_shortcut_legend_renders_once_with_real_behaviour_wording(self):
        """The dock's shortcut legend renders as exactly one visible instance,
        carries the reference draft's wording and ``<kbd>`` structure, and is
        the only element carrying the legend's test hook
        (webclient-align-01-dock-chrome).

        The old visually-hidden ``action-dock-description`` duplicate was
        deleted: the dock's own legend strip IS the hook (webclient-scene-
        overview-swap D3 re-homed it out of the tab bar). It shows in combat;
        the exploration panel carries none (exploration-exit-compass). The legend names only implemented behaviour (1–9 pick rows,
        Enter activates, Esc pops one frame); the ``/`` focus binding stays
        implemented but the reference's legend does not advertise it, so
        neither does this one.
        """
        page = self.logged_in_page()
        # The exploration panel shows no legend (exploration-exit-compass);
        # combat keeps it.
        self.assertEqual(page.locator(".action-dock__legend").count(), 0)
        _inject_snapshot(page, {"context_actions": _combat_panel()}, mode="combat")
        _wait_mode(page, "combat")
        focus_action_dock(page)
        hint = page.locator(".action-dock__legend")
        # Exactly one legend element, and it carries the test hook.
        self.assertEqual(
            hint.count(), 1, "the dock carries exactly one legend"
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
        self.assertEqual(hint_text, "數字鍵 1–9 ‧ Enter 執行 ‧ Esc 返回")
        self.assertNotIn("/ 聚焦指令列", hint_text)
        self.assertNotIn("方向鍵選擇", hint_text)
        # The draft's <kbd> structure: exactly two styled kbd elements.
        kbd = page.locator(".action-dock__legend kbd")
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
