"""Contextual HUD drawer acceptance (webclient-contextual-hud): reference drawers and recession marks, the codex drawer pair, the quest drawer, and status-drawer geometry.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest, ui_scale
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    outbound_messages,
    sent_action_count,
    store_state,
    valid_character_panel,
    valid_lore_codex_panel,
    valid_local_map_panel,
    valid_status_panel,
    wait_for_store_state,
)
from ._journey_support import (
    _inject_snapshot,
    _wait_mode,
    _press,
)


class ContextualHudBrowserTest(BrowserAcceptanceTest):
    """Contextual HUD action-dock behavior on the shared managed server."""
    # ------------------------------------------------------------------
    # H4 (tasks 9.5-9.7): reference-drawer browser acceptance.
    # ------------------------------------------------------------------

    REFERENCE_SURFACE_TESTIDS = [
        "skill-book",
        "party-window",
        "party-bag-tab",
        "shop-panel",
        "quest-drawer",
        "lore-codex-drawer",
        "party-status-tab",
    ]

    def _open_reference_drawer(self, page):
        # The skill book stands for any framed reference drawer (the
        # character-status drawer retired into the party window's 狀態 tab,
        # webclient-party-status-tab).
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('skill'); }"
        )
        page.wait_for_selector('[data-testid="hud-drawer"]', timeout=15000)

    def _stage_anchor_rects(self, page):
        return page.evaluate(
            """() => {
              const ids = ["anchor-vitals", "anchor-map", "anchor-band-message", "anchor-band-command", "anchor-command-line"];
              return ids.map((id) => {
                const el = document.querySelector('[data-testid="' + id + '"]');
                if (!el) return { id, rect: null };
                return { id, rect: el.getBoundingClientRect() };
              });
            }"""
        )

    def _anchors_overlap(self, page):
        rects = self._stage_anchor_rects(page)
        present = [r for r in rects if r["rect"]]
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                a, b = present[i]["rect"], present[j]["rect"]
                # The rects arrive as plain dicts (DOMRect serialized).
                overlap = not (
                    a["right"] <= b["left"] or b["right"] <= a["left"]
                    or a["bottom"] <= b["top"] or b["bottom"] <= a["top"]
                )
                if overlap:
                    return True
        return False

    @covers_requirement(
        "webclient-contextual-hud::an-open-drawer-or-overlay-dims-the-stage-behind-it"
    )
    def test_reference_drawer_close_focus_and_absent_surfaces(self):
        """H4 (task 9.5): at both viewports an open drawer closes in one
        action, Escape restores focus, and no reference surface is in the DOM
        while every drawer is closed."""
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                # The focus-restoration contract: the drawer is opened while the
                # preserved #action-dock holds focus, so Escape returns focus
                # there (the opener is the dock, not <body>).
                focus_action_dock(page)
                self._open_reference_drawer(page)
                stage = page.locator('[data-testid="elosern-stage"]')

                # The open drawer recesses the stage (task 9.6 assertion inline).
                self.assertEqual(
                    stage.get_attribute("data-menu-open"),
                    "true",
                    f"the stage is recessed while the reference drawer is open at {viewport}",
                )

                # One action (Escape) closes the drawer; focus returns to the
                # preserved action-dock target.
                _press(page, "Escape")
                page.wait_for_function(
                    "() => document.querySelector('[data-testid=\"hud-drawer\"]') === null",
                    timeout=15000,
                )
                self.assertEqual(
                    page.locator('[data-testid="hud-drawer"]').count(),
                    0,
                    f"the drawer closes in one action (Escape) at {viewport}",
                )
                self.assertEqual(
                    stage.get_attribute("data-menu-open"),
                    "false",
                    f"the recession mark clears when the last surface closes at {viewport}",
                )
                # Escape closes the drawer and restores focus to the preserved
                # action-dock focus target (the focus-restoration contract).
                focus_id = page.evaluate(
                    "() => { const a = document.activeElement; "
                    "return a ? (a.id || (a.getAttribute && a.getAttribute('data-testid')) || a.tagName) : null; }"
                )
                self.assertEqual(
                    focus_id,
                    "action-dock",
                    f"Escape restores focus to the preserved #action-dock target at {viewport}",
                )
                dock = page.locator("#action-dock")
                self.assertTrue(dock.count() >= 1, "the preserved action dock is present")

                # No reference surface is in the DOM while every drawer is closed.
                for testid in self.REFERENCE_SURFACE_TESTIDS:
                    self.assertEqual(
                        page.locator(f'[data-testid="{testid}"]').count(),
                        0,
                        f"reference surface {testid} is absent while all drawers are closed at {viewport}",
                    )
                self.assertEqual(
                    page.locator('[data-testid="hud-drawer"]').count(), 0,
                    "no drawer chrome in the DOM while closed")
                self.assertEqual(
                    page.locator('[data-testid="hud-drawer-scrim"]').count(), 0,
                    "no drawer scrim in the DOM while closed")
                page.close()

    @covers_requirement(
        "webclient-contextual-hud::an-open-drawer-or-overlay-dims-the-stage-behind-it"
    )
    def test_reference_drawer_recession_mark_lifecycle(self):
        """H4 (task 9.6): the stage recession mark is present while a
        reference drawer is open and cleared when the last surface closes."""
        page = self.logged_in_page()
        stage = page.locator('[data-testid="elosern-stage"]')
        self.assertEqual(
            stage.get_attribute("data-menu-open"), "false",
            "no surface open: no recession mark",
        )
        # Open the drawer while #action-dock holds focus so the opener (the
        # element focused when the drawer opened) is the preserved dock.
        focus_action_dock(page)
        self._open_reference_drawer(page)
        self.assertEqual(
            stage.get_attribute("data-menu-open"), "true",
            "the open reference drawer recesses the stage",
        )
        _press(page, "Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"hud-drawer\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            stage.get_attribute("data-menu-open"), "false",
            "the recession mark clears when the last surface closes",
        )

    # ------------------------------------------------------------------
    # webclient-lore-codex-drawer: the world-codex drawer surface.
    # ------------------------------------------------------------------

    @covers_requirement(
        "webclient-contextual-hud::an-open-drawer-or-overlay-dims-the-stage-behind-it"
    )
    @covers_requirement(
        "webclient-lore-codex-panel::the-codex-opens-from-the-top-navigation-bar-not-from-the-quest-drawer",
    )
    def test_codex_drawer_opens_from_the_utility_strip(self):
        """The command line's 圖鑑 utility control opens the codex reference
        drawer with a real user click: the drawer body renders the committed
        `lore_codex` panel's discovered entries, the stage recesses while it
        is open, and Escape closes it."""
        page = self.logged_in_page()
        stage = page.locator('[data-testid="elosern-stage"]')
        _inject_snapshot(page, {"lore_codex": valid_lore_codex_panel()}, mode="exploration")
        _wait_mode(page, "exploration")

        # The real trigger path: a clean-state click on the top-bar tool-group
        # control while the command line is collapsed.
        page.locator('[data-testid="nav-tool-lore"]').click()
        page.wait_for_selector('[data-testid="lore-codex-drawer"]', timeout=15000)
        self.assertEqual(
            page.locator('[data-testid="lore-codex-drawer"]').count(),
            1,
            "the utility-strip control opens exactly the codex reference drawer",
        )
        # The body renders the panel's discoveries (not the old guild-quest
        # prose, not an empty stub): the aggregate control and both entries.
        body_text = page.locator('[data-testid="lore-codex-drawer"]').inner_text()
        self.assertIn("全部", body_text, "the aggregate control renders")
        self.assertIn("平原族", body_text, "the discovered race entry renders")
        self.assertIn("霧骨渡口", body_text, "the discovered anchor entry renders")
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "true",
            "the open codex drawer recesses the stage",
        )

        # Escape closes the drawer in one action.
        _press(page, "Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"hud-drawer\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "false",
            "the recession mark clears when the codex drawer closes",
        )
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
            "nav-tool-lore",
            "closing the codex drawer returns focus to the top-bar 圖鑑 control",
        )
        page.close()

    @covers_requirement(
        "webclient-lore-codex-panel::the-codex-opens-from-the-top-navigation-bar-not-from-the-quest-drawer",
    )
    def test_codex_drawer_replaces_the_open_drawer_or_overlay(self):
        """At most one focus-trapped surface is open: opening the codex drawer
        through the store's single open-drawer entry point closes an open
        reference drawer, and opening an overlay closes the codex drawer."""
        page = self.logged_in_page()
        _inject_snapshot(page, {"lore_codex": valid_lore_codex_panel()}, mode="exploration")
        _wait_mode(page, "exploration")

        # Drawer-vs-drawer: the skill drawer is open (the public test seam
        # the H4 journeys use), then the codex opens through the same single
        # store entry point the utility-strip control routes to.
        self._open_reference_drawer(page)
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('lore'); }"
        )
        page.wait_for_selector('[data-testid="lore-codex-drawer"]', timeout=15000)
        self.assertEqual(
            page.locator('[data-testid="skill-book"]').count(),
            0,
            "opening the codex drawer closes the open reference drawer",
        )

        # Drawer-vs-overlay: opening the settings overlay closes the codex
        # drawer (the store keeps one open focus-trapped surface).
        page.evaluate("window.__elosernBridge.store.openOverlay('settings')")
        page.wait_for_selector('[data-testid="settings-overlay"]', timeout=15000)
        self.assertEqual(
            page.locator('[data-testid="lore-codex-drawer"]').count(),
            0,
            "opening the settings overlay closes the codex drawer",
        )
        page.locator('[data-testid="overlay-host-close"]').click()
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"settings-overlay\"]') === null",
            timeout=15000,
        )
        page.close()

    @covers_requirement(
        "webclient-lore-codex-panel::the-codex-opens-from-the-top-navigation-bar-not-from-the-quest-drawer",
    )
    def test_quest_drawer_offers_no_codex_control(self):
        """The quest drawer contains no control that opens the codex: the
        世界圖鑑 button is removed outright, and the split drawer carries no
        codex-opening control of any kind."""
        page = self.logged_in_page()
        _inject_snapshot(page, {"lore_codex": valid_lore_codex_panel()}, mode="exploration")
        _wait_mode(page, "exploration")
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('quest'); }"
        )
        page.wait_for_selector('[data-testid="quest-drawer"]', timeout=15000)

        quest_drawer = page.locator('[data-testid="quest-drawer"]')
        self.assertEqual(
            quest_drawer.get_by_role("button", name="世界圖鑑").count(),
            0,
            "the removed 世界圖鑑 control is gone from the quest drawer",
        )
        self.assertEqual(
            page.locator('[data-testid="lore-codex-drawer"]').count(),
            0,
            "no codex drawer is open beside the quest drawer",
        )
        # No control anywhere inside the quest-drawer body names the codex.
        self.assertNotIn(
            "世界圖鑑",
            quest_drawer.inner_text(),
            "the quest drawer renders no codex-opening control",
        )
        page.close()

    @covers_requirement(
        "webclient-lore-codex-panel::the-codex-opens-from-the-top-navigation-bar-not-from-the-quest-drawer",
    )
    def test_the_two_codex_controls_are_distinguishable(self):
        """The world-codex control and the title-codex control in the utility
        strip carry distinct accessible labels and distinct glyphs — they sit
        side by side and open different systems."""
        page = self.logged_in_page()
        _wait_mode(page, "exploration")

        lore = page.locator('[data-testid="nav-tool-lore"]')
        codex = page.locator('[data-testid="nav-tool-codex"]')
        lore_label = lore.get_attribute("aria-label")
        codex_label = codex.get_attribute("aria-label")
        self.assertNotEqual(
            lore_label,
            codex_label,
            "the two codex controls carry distinct accessible labels",
        )
        lore_glyph = page.evaluate(
            "() => { const b = document.querySelector('[data-testid=\"nav-tool-lore\"]');"
            " return Array.from(b.querySelectorAll('path, circle, ellipse'))"
            ".map((n) => n.outerHTML); }"
        )
        codex_glyph = page.evaluate(
            "() => { const b = document.querySelector('[data-testid=\"nav-tool-codex\"]');"
            " return Array.from(b.querySelectorAll('path, circle, ellipse'))"
            ".map((n) => n.outerHTML); }"
        )
        self.assertNotEqual(
            lore_glyph,
            codex_glyph,
            "the two codex controls carry distinct glyph shapes",
        )
        page.close()

    @covers_requirement("webclient-party-window::the-status-tab-shows-conditions-and-an-honest-disguise")
    def test_status_tab_rows_fit_with_no_overlap(self):
        """The party window's 狀態 tab (webclient-party-status-tab): the
        hero, gauges, trait rows and condition rows fit the list column with
        no overlap or horizontal overflow at both viewports, and every row
        stays reachable inside the column's bounded scroll.

        Exercises a low-HP member row and a 9-condition roster spanning all
        five severities, including a multi-modifier condition and several
        durations.
        """
        def condition(code, label, severity, remaining=None, modifiers=None):
            return {
                "code": code, "label": label, "severity": severity,
                "remaining_seconds": remaining, "modifiers": modifiers or {}, "source": "狀態",
            }

        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                focus_action_dock(page)
                character = valid_character_panel(
                    member_id=42,
                    conditions=[
                        condition("regen", "再生", "beneficial", 30),
                        condition("fog_veil", "霧隱", "informational"),
                        condition("focus", "專注", "warning", 10, {"atk_phys": 5}),
                        condition("exposure", "高露出", "harmful", None, {"defense": -15, "agility": -10}),
                        condition("bleed", "出血", "harmful", 20, {"heal_gain": -3}),
                        condition("paralyze", "癱瘓", "critical"),
                        condition("shield", "護盾", "beneficial", 15),
                        condition("chill", "失溫", "harmful", 8),
                        condition("lucky", "幸運", "informational", 3725),
                    ],
                )
                party = {
                    "schema_version": 3, "available": True,
                    "general_quota": {"used": 0, "limit": 4}, "viewed_member_id": 42,
                    "slots": [{
                        "identity": 42, "display_name": "艾倫‧灰誓", "portrait_ref": None,
                        "hp_current": 12, "hp_maximum": 405, "mp_current": 50, "mp_maximum": 50,
                        "sp_current": 40, "sp_maximum": 40, "role": "commander", "knocked_out": False,
                        "unread": False, "bond_stage": None, "membership": None,
                    }],
                }
                _inject_snapshot(
                    page,
                    {"status": valid_status_panel("艾倫‧灰誓", "42"), "character": character, "party": party},
                    mode="exploration",
                )
                _wait_mode(page, "exploration")
                page.evaluate(
                    "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
                    "if (s) s.openHudDrawer('status'); }"
                )
                page.wait_for_selector('[data-testid="party-status-tab__condition--regen"]', timeout=15000)

                fit = page.evaluate(
                    """() => {
                      const column = document.querySelector('[data-testid="party-status-tab"] [data-testid="list-detail__list"]');
                      if (!column) return { ok: false, reason: 'list column missing' };
                      const colRect = column.getBoundingClientRect();
                      const rows = Array.from(column.querySelectorAll(
                        '[data-testid^="party-status-tab__gauge--"], [role="option"]'));
                      for (const el of rows) {
                        if (el.scrollWidth > el.clientWidth + 1) {
                          return { ok: false, reason: 'row content overflows its box: ' + el.dataset.testid };
                        }
                      }
                      const boxes = rows.map((el) => el.getBoundingClientRect());
                      for (let i = 0; i < boxes.length; i++) {
                        for (let j = i + 1; j < boxes.length; j++) {
                          const a = boxes[i], b = boxes[j];
                          const overlap = !(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top);
                          if (overlap) return { ok: false, reason: 'row pair overlaps' };
                        }
                      }
                      for (const box of boxes) {
                        if (box.left < colRect.left - 1 || box.right > colRect.right + 1) {
                          return { ok: false, reason: 'row outside the column horizontally' };
                        }
                      }
                      for (const el of rows) {
                        el.scrollIntoView({ block: 'nearest' });
                        const b = el.getBoundingClientRect();
                        if (b.top < colRect.top - 1 || b.bottom > colRect.bottom + 1) {
                          return { ok: false, reason: 'row unreachable inside the scrollable column' };
                        }
                      }
                      if (column.scrollWidth > column.clientWidth + 1) {
                        return { ok: false, reason: 'list column has horizontal overflow' };
                      }
                      const options = rows.filter((el) => el.getAttribute('role') === 'option');
                      return {
                        ok: true,
                        gaugeCount: rows.length - options.length,
                        conditionCount: options.filter((el) => el.dataset.severity).length,
                        traitCount: options.filter((el) => !el.dataset.severity).length,
                      };
                    }"""
                )
                self.assertTrue(fit["ok"], f"status tab rows fit at {viewport}: {fit}")
                self.assertEqual(fit["conditionCount"], 9, "all 9 conditions render as rows")
                self.assertEqual(fit["gaugeCount"], 3, "the three gauges render")
                self.assertEqual(fit["traitCount"], 1, "the one static trait renders")
                page.close()

    # ------------------------------------------------------------------
    # webclient-drawer-frame-unification: the shared opaque reference frame.
    # ------------------------------------------------------------------

    _FRAME_PROBE = """(selector) => {
      const vw = window.innerWidth, vh = window.innerHeight;
      const panel = document.querySelector(selector);
      const nav = document.querySelector('.desktop-navigation').getBoundingClientRect();
      const line = document.querySelector('[data-testid="anchor-command-line"]').getBoundingClientRect();
      const r = panel.getBoundingClientRect();
      const cs = getComputedStyle(panel);
      // The panel is opaque on its own: a solid colour or a gradient whose
      // every stop is opaque. No translucent stop may let the stage through.
      const paint = cs.backgroundImage + ' ' + cs.backgroundColor;
      const gradientStops = (cs.backgroundImage.match(/rgba?\\([^)]*\\)/g) || []);
      const translucent = gradientStops.filter((c) => /rgba\\(/.test(c) && !/,\\s*1\\)$/.test(c));
      const hit = (x, y) => document.elementFromPoint(x, y);
      const lineHit = hit(line.left + line.width / 2, line.top + line.height / 2);
      const stripHit = hit(vw / 2, vh - 12);
      const headers = panel.querySelectorAll(':scope > .drawer-header');
      return {
        vw, vh, navBottom: nav.bottom,
        rect: { top: r.top, left: r.left, right: r.right, bottom: r.bottom },
        lineRect: { top: line.top, bottom: line.bottom },
        opaqueGradient: gradientStops.length > 0 && translucent.length === 0,
        paint,
        lineCovered: panel.contains(lineHit),
        stripTestid: stripHit && stripHit.getAttribute('data-testid'),
        headers: headers.length,
        closes: panel.querySelectorAll('.drawer-header__close').length,
      };
    }"""

    def _assert_workspace_frame(self, probe, what, viewport):
        vw, vh = viewport
        scale = ui_scale(viewport)
        r = probe["rect"]
        # The frame's insets are chrome: header + 12px * S, 16px * S on each
        # side, and --workspace-bottom (44px + 12px, both * S) above the edge.
        self.assertAlmostEqual(r["top"], probe["navBottom"] + 12 * scale, delta=1, msg=f"{what} top at {viewport}")
        self.assertAlmostEqual(r["left"], 16 * scale, delta=1, msg=f"{what} left at {viewport}")
        self.assertAlmostEqual(r["right"], vw - 16 * scale, delta=1, msg=f"{what} right at {viewport}")
        self.assertAlmostEqual(r["bottom"], vh - 56 * scale, delta=1, msg=f"{what} bottom at {viewport}")
        self.assertTrue(probe["opaqueGradient"], f"{what} panel is fully opaque at {viewport}: {probe['paint']}")
        self.assertTrue(probe["lineCovered"], f"{what} covers the expanded command-line row at {viewport}")
        self.assertEqual(probe["headers"], 1, f"{what} carries exactly one shared header")
        self.assertEqual(probe["closes"], 1, f"{what} carries exactly one close control")

    @covers_requirement(
        "webclient-contextual-hud::reference-surfaces-share-an-opaque-accessible-frame",
        "webclient-contextual-hud::reference-surfaces-render-in-a-bounded-workspace-drawer-with-one-modal-contract",
        "webclient-contextual-hud::a-full-screen-overlay-is-one-focus-trapped-surface-and-only-one-is-open-at-a-time",
    )
    def test_reference_surfaces_share_one_opaque_workspace_frame(self):
        """Drawers and overlays fill one opaque workspace under the navigation
        that covers the expanded command-line row and leaves only the band's
        lowest strip under a scrim; the overlay scrim absorbs pointer input
        below the navigation while the navigation still switches overlays."""
        for viewport in ((1451, 790), (1741, 948), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                _inject_snapshot(page, {"local_map": valid_local_map_panel()}, mode="exploration")
                _wait_mode(page, "exploration")
                page.locator('[data-testid="command-line-toggle"]').click()
                page.wait_for_selector('[data-testid="anchor-command-line"][data-expanded="true"]', timeout=15000)

                self._open_reference_drawer(page)
                probe = page.evaluate(self._FRAME_PROBE, '[data-testid="hud-drawer"]')
                self._assert_workspace_frame(probe, "the skill drawer", viewport)
                self.assertEqual(probe["stripTestid"], "hud-drawer-scrim",
                                 "the drawer scrim covers the band's exposed strip")
                page.keyboard.press("Escape")
                page.wait_for_function(
                    "() => document.querySelector('[data-testid=\"hud-drawer\"]') === null", timeout=15000)

                page.locator('[data-testid="nav-settings"]').click()
                page.wait_for_selector('[data-testid="settings-overlay"]', timeout=15000)
                probe = page.evaluate(self._FRAME_PROBE, '[data-testid="overlay-host"]')
                self._assert_workspace_frame(probe, "the settings overlay", viewport)
                self.assertEqual(probe["stripTestid"], "overlay-host-scrim",
                                 "the overlay scrim covers the band's exposed strip")
                # A pointer press on the scrim never closes the overlay.
                page.mouse.click(viewport[0] / 2, viewport[1] - 12)
                self.assertEqual(page.locator('[data-testid="settings-overlay"]').count(), 1,
                                 "the overlay scrim absorbs the press without closing the overlay")
                # The navigation stays above the scrim: its 說明 control
                # replaces the open overlay by pointer.
                page.locator('[data-testid="nav-tool-help"]').click()
                page.wait_for_selector('[data-testid="help-overlay"]', timeout=15000)
                self.assertEqual(page.locator('[data-testid="settings-overlay"]').count(), 0)
                self.assertEqual(page.locator('[data-testid="overlay-host"]').get_attribute("aria-label"), "說明")
                page.close()
