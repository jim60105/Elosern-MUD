"""Contextual HUD stage-geometry acceptance (webclient-contextual-hud): caption width against stage anchors, anchor non-overlap, and the registry-owned map-unavailable reason in the map overlay.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from ._journey_support import (
    _local_map_unavailable_panel,
    _inject_snapshot,
    _wait_mode,
)


class ContextualHudBrowserTest(BrowserAcceptanceTest):
    """Contextual HUD action-dock behavior on the shared managed server."""
    def _stage_anchor_rects(self, page):
        return page.evaluate(
            """() => {
              const ids = ["anchor-place", "anchor-vitals", "anchor-map", "anchor-band-message", "anchor-band-command", "anchor-command-line"];
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
        "webclient-contextual-hud::the-message-window-presents-the-current-response-one-page-at-a-time-in-the-band-s-message-region"
    )
    def test_caption_wider_and_no_anchor_overlap(self):
        """H4 (task 9.7): with `#panel-right` emptied into drawers, the
        message window is wider at both viewports and no stage anchor
        overlaps another."""
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                feed_width = page.evaluate(
                    "() => { const f = document.querySelector('[data-testid=\"message-window\"]');"
                    "return f ? f.getBoundingClientRect().width : 0; }"
                )
                self.assertGreater(
                    feed_width, 400,
                    f"the message window is wider than 400px at {viewport}",
                )
                self.assertFalse(
                    self._anchors_overlap(page),
                    f"no stage anchor overlaps another at {viewport}",
                )
                page.close()

    @covers_requirement(
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully"
    )
    def test_local_map_unavailable_renders_registry_reason_in_map_overlay(self):
        """8.9 offline-degradation regression: with the `local_map` panel in its
        registry-owned unavailable form, the minimap island renders only the
        registry-owned reason, and the map overlay's opening path still works —
        the map overlay renders only the reason, never a stale lattice."""
        page = self.logged_in_page()
        _inject_snapshot(page, {"local_map": _local_map_unavailable_panel()}, mode="exploration")
        _wait_mode(page, "exploration")

        # The minimap island renders the registry-owned reason (not the lattice).
        island_reason = page.locator('[data-testid="local-map__unavailable"]')
        self.assertTrue(island_reason.is_visible(), "the minimap island shows the registry-owned reason")
        self.assertEqual(
            island_reason.inner_text(),
            "區域地圖目前無法顯示",
            "the island shows the exact registry-owned reason message",
        )
        self.assertEqual(
            page.locator('[data-testid="local-map__lattice"]').count(),
            0,
            "no lattice renders while the local_map panel is unavailable",
        )

        # The map overlay's opening path (the island's 展開全地圖 trigger routes
        # through the store's overlay slice) still opens the surface.
        page.evaluate("window.__elosernBridge.store.openOverlay('map')")
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)

        # The map overlay renders ONLY the registry-owned reason (no lattice).
        overlay_reason = page.locator('[data-testid="map-overlay-unavailable"]')
        self.assertTrue(
            overlay_reason.is_visible(),
            "the map overlay shows the registry-owned reason",
        )
        self.assertEqual(
            overlay_reason.inner_text(),
            "區域地圖目前無法顯示",
            "the map overlay shows the exact registry-owned reason message",
        )
        self.assertEqual(
            page.locator('[data-testid="map-overlay-content"]').count(),
            0,
            "the map overlay renders only the reason, never a stale lattice",
        )
        page.close()
