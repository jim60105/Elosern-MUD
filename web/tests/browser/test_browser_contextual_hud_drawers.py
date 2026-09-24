"""Contextual HUD drawer acceptance (webclient-contextual-hud): reference drawers and recession marks, the codex drawer pair, the quest drawer, and status-drawer geometry.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
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
        "inventory-panel",
        "shop-panel",
        "quest-drawer",
        "lore-codex-drawer",
        "character-status-drawer",
    ]

    def _open_status_drawer(self, page):
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('status'); }"
        )
        page.wait_for_selector('[data-testid="hud-drawer"]', timeout=15000)

    def _stage_anchor_rects(self, page):
        return page.evaluate(
            """() => {
              const ids = ["anchor-hud-left", "anchor-hud-right", "anchor-band-message", "anchor-band-command", "anchor-command-line"];
              return ids.map((id) => {
                const el = document.getElementById(id);
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
                overlap = not (
                    a.right <= b.left or b.right <= a.left
                    or a.bottom <= b.top or b.bottom <= a.top
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
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                # The focus-restoration contract: the drawer is opened while the
                # preserved #action-dock holds focus, so Escape returns focus
                # there (the opener is the dock, not <body>).
                focus_action_dock(page)
                self._open_status_drawer(page)
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
        self._open_status_drawer(page)
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
        "webclient-lore-codex-panel::the-codex-opens-from-the-command-line-utility-strip-not-from-the-quest-drawer",
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

        # The real trigger path: a clean-state click on the utility-strip
        # control (no modal covers the command line).
        page.locator('[data-testid="command-line-lore"]').click()
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
        self.assertIn("人類", body_text, "the discovered race entry renders")
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
        page.close()

    @covers_requirement(
        "webclient-lore-codex-panel::the-codex-opens-from-the-command-line-utility-strip-not-from-the-quest-drawer",
    )
    def test_codex_drawer_replaces_the_open_drawer_or_overlay(self):
        """At most one focus-trapped surface is open: opening the codex drawer
        through the store's single open-drawer entry point closes an open
        reference drawer, and opening an overlay closes the codex drawer."""
        page = self.logged_in_page()
        _inject_snapshot(page, {"lore_codex": valid_lore_codex_panel()}, mode="exploration")
        _wait_mode(page, "exploration")

        # Drawer-vs-drawer: the status drawer is open (the public test seam
        # the H4 journeys use), then the codex opens through the same single
        # store entry point the utility-strip control routes to.
        self._open_status_drawer(page)
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('lore'); }"
        )
        page.wait_for_selector('[data-testid="lore-codex-drawer"]', timeout=15000)
        self.assertEqual(
            page.locator('[data-testid="character-status-drawer"]').count(),
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
        "webclient-lore-codex-panel::the-codex-opens-from-the-command-line-utility-strip-not-from-the-quest-drawer",
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
        "webclient-lore-codex-panel::the-codex-opens-from-the-command-line-utility-strip-not-from-the-quest-drawer",
    )
    def test_the_two_codex_controls_are_distinguishable(self):
        """The world-codex control and the title-codex control in the utility
        strip carry distinct accessible labels and distinct glyphs — they sit
        side by side and open different systems."""
        page = self.logged_in_page()
        _wait_mode(page, "exploration")

        lore = page.locator('[data-testid="command-line-lore"]')
        codex = page.locator('[data-testid="command-line-codex"]')
        lore_label = lore.get_attribute("aria-label")
        codex_label = codex.get_attribute("aria-label")
        self.assertNotEqual(
            lore_label,
            codex_label,
            "the two codex controls carry distinct accessible labels",
        )
        lore_glyph = page.evaluate(
            "() => { const b = document.querySelector('[data-testid=\"command-line-lore\"]');"
            " return Array.from(b.querySelectorAll('path, circle, ellipse'))"
            ".map((n) => n.outerHTML); }"
        )
        codex_glyph = page.evaluate(
            "() => { const b = document.querySelector('[data-testid=\"command-line-codex\"]');"
            " return Array.from(b.querySelectorAll('path, circle, ellipse'))"
            ".map((n) => n.outerHTML); }"
        )
        self.assertNotEqual(
            lore_glyph,
            codex_glyph,
            "the two codex controls carry distinct glyph shapes",
        )
        page.close()

    def test_status_drawer_tiles_and_pills_fit_with_no_overlap(self):
        """The re-chromed 角色狀態 drawer: the stat tiles and condition pills
        wrap without overlap or horizontal overflow at both viewports, and
        every tile and pill stays reachable inside the drawer's bounded
        scroll (the design's card-tile / pill-badge presentation; the drawer
        body is the bounded, vertically scrollable surface).

        Exercises a low-HP resource (the 危險 marker case) and a 9-condition
        roster spanning all five severities (more than the H2 island's 6-item
        cap), including a multi-modifier condition and several durations.
        """
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                focus_action_dock(page)
                status = valid_status_panel("艾倫·灰誓", "char-42")
                status["resources"]["hp"] = {"current": 12, "maximum": 405}
                # The signed modifier values mirror the deterministic
                # combat_modifiers.yaml (defense -15, agility -10, hp -3):
                # the global JSON-safety bound now spans the full
                # JavaScript-safe range, so the roster reaches the drawer.
                status["conditions"] = [
                    {"code": "regen", "label": "再生", "severity": "beneficial", "remaining_seconds": 30},
                    {"code": "fog_veil", "label": "霧隱", "severity": "informational"},
                    {
                        "code": "focus",
                        "label": "專注",
                        "severity": "warning",
                        "remaining_seconds": 10,
                        "modifiers": {"atk_phys": 5},
                    },
                    {
                        "code": "exposure",
                        "label": "高露出",
                        "severity": "harmful",
                        "modifiers": {"defense": -15, "agility": -10},
                    },
                    {
                        "code": "bleed",
                        "label": "出血",
                        "severity": "harmful",
                        "remaining_seconds": 20,
                        "modifiers": {"hp": -3},
                    },
                    {"code": "paralyze", "label": "癱瘓", "severity": "critical"},
                    {"code": "shield", "label": "護盾", "severity": "beneficial", "remaining_seconds": 15},
                    {"code": "chill", "label": "失溫", "severity": "harmful", "remaining_seconds": 8},
                    {"code": "lucky", "label": "幸運", "severity": "informational", "remaining_seconds": 60},
                ]
                character = valid_character_panel()
                _inject_snapshot(page, {"status": status, "character": character}, mode="exploration")
                _wait_mode(page, "exploration")
                self._open_status_drawer(page)
                page.wait_for_selector('[data-testid="character-status-drawer__condition--regen"]', timeout=15000)

                fit = page.evaluate(
                    """() => {
                      const body = document.querySelector('.hud-drawer__body');
                      if (!body) return { ok: false, reason: 'drawer body missing' };
                      const bodyRect = body.getBoundingClientRect();
                      const tiles = Array.from(document.querySelectorAll(
                        '[data-testid^="character-status-drawer__vital--"], ' +
                        '[data-testid^="character-status-drawer__trait--"], ' +
                        '[data-testid="character-status-drawer__guild-rank"], ' +
                        '[data-testid="character-status-drawer__guild-merit"]'));
                      const pills = Array.from(document.querySelectorAll('.character-status-drawer__pill'));
                      const els = [...tiles, ...pills];
                      // Per-element overflow: a tile or pill whose text content
                      // is wider than its own box would scroll internally.
                      for (const el of els) {
                        if (el.scrollWidth > el.clientWidth + 1) {
                          return { ok: false, reason: 'element content overflows its box' };
                        }
                      }
                      const boxes = els.map((el) => el.getBoundingClientRect());
                      // Non-intersection pattern (fix-webclient-local-map-node-crowding):
                      // no two tiles/pills may overlap.
                      for (let i = 0; i < boxes.length; i++) {
                        for (let j = i + 1; j < boxes.length; j++) {
                          const a = boxes[i], b = boxes[j];
                          const overlap = !(
                            a.right <= b.left || b.right <= a.left ||
                            a.bottom <= b.top || b.bottom <= a.top
                          );
                          if (overlap) return { ok: false, reason: 'tile/pill pair overlaps' };
                        }
                      }
                      // Boundary: no tile/pill spills past the drawer's horizontal
                      // content box.
                      for (const box of boxes) {
                        if (box.left < bodyRect.left || box.right > bodyRect.right) {
                          return { ok: false, reason: 'box outside drawer horizontal bounds' };
                        }
                      }
                      // The drawer body is the design's bounded, vertically
                      // scrollable surface (HudDrawer.vue .hud-drawer__body
                      // overflow-y: auto), so a roster taller than the body
                      // is reached by scrolling — the horizontal bounds and
                      // the no-overlap rule above carry the fit contract.
                      // What must never happen is unreachable content: each
                      // element scrolled into view must become fully visible
                      // inside the body's visible box.
                      for (const el of els) {
                        el.scrollIntoView({ block: 'nearest' });
                        const b = el.getBoundingClientRect();
                        if (b.top < bodyRect.top - 1 || b.bottom > bodyRect.bottom + 1) {
                          return { ok: false, reason: 'box unreachable inside the scrollable drawer body' };
                        }
                      }
                      // No unexpected horizontal overflow in the drawer body.
                      if (body.scrollWidth > body.clientWidth + 1) {
                        return { ok: false, reason: 'drawer body has horizontal overflow' };
                      }
                      return { ok: true, tileCount: tiles.length, pillCount: pills.length };
                    }"""
                )
                self.assertTrue(fit["ok"], f"status drawer tiles and pills fit at {viewport}: {fit}")
                self.assertEqual(fit["pillCount"], 9, "all 9 conditions render as pills")
                self.assertEqual(fit["tileCount"], 6, "3 vitals + 1 trait + 2 guild tiles render")
                # Visual evidence for the design-alignment check (task 6.5).
                if viewport == (1440, 900):
                    page.screenshot(path=f"tmp/status_drawer_{viewport[0]}x{viewport[1]}.png")
                page.close()
