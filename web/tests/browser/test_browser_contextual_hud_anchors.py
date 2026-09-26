"""Contextual HUD stage-geometry acceptance (webclient-contextual-hud): caption width against stage anchors, anchor non-overlap, and the registry-owned map-unavailable reason in the map overlay.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import valid_local_map_panel
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
        "webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces"
    )
    def test_dialogue_host_stands_opposite_the_player(self):
        """webclient-dialogue-stage-actors: in dialogue the host's stage actor
        stands in `actor-right` on the band, as tall as the player, 6% in
        from the right at 1920x1080 and far enough in at 1440x900 and
        1280x720 that its face (the anchor's centre) clears the minimap; no
        interactive anchor overlaps another; the return to exploration empties
        `actor-right`."""
        dialogue = {
            "schema_version": 2,
            "available": True,
            "kind": "dialogue",
            "host": {"identity": 11, "display_name": "小販", "portrait_ref": None},
            "bond_stage": None,
            "line": "歡迎光臨。",
            "choices": [{"keyword_id": "goods", "label": "有什麼貨？"}],
        }
        for viewport in ((1920, 1080), (1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                _inject_snapshot(page, {"local_map": valid_local_map_panel(), "dialogue": dialogue}, mode="dialogue")
                _wait_mode(page, "dialogue")
                page.wait_for_selector('[data-anchor="actor-right"] [data-testid="stage-actor"]', timeout=15000)
                geo = page.evaluate(
                    """() => {
                      const r = (sel) => { const el = document.querySelector(sel); return el ? el.getBoundingClientRect() : null; };
                      const host = r('[data-anchor="actor-right"]');
                      const player = r('[data-anchor="actor-left"]');
                      const band = r('[data-testid="stage-band"]');
                      const map = r('.local-map');
                      const focusable = document.querySelectorAll(
                        '[data-anchor="actor-right"] :is(button, a, input, textarea, select, [tabindex])').length;
                      return {
                        hostRight: host.right, hostBottom: host.bottom, hostHeight: host.height,
                        hostCentre: (host.left + host.right) / 2, playerHeight: player.height,
                        bandTop: band.top, mapLeft: map ? map.left : null, focusable,
                        width: innerWidth,
                      };
                    }"""
                )
                self.assertAlmostEqual(geo["hostBottom"], geo["bandTop"], delta=1.0)
                self.assertAlmostEqual(geo["hostHeight"], geo["playerHeight"], delta=1.0)
                self.assertEqual(geo["focusable"], 0)
                inset = geo["width"] - geo["hostRight"]
                if viewport == (1920, 1080):
                    self.assertAlmostEqual(inset, 0.06 * 1920, delta=1.0)
                else:
                    self.assertGreaterEqual(inset, 0.06 * viewport[0] - 1)
                self.assertIsNotNone(geo["mapLeft"])
                self.assertLess(geo["hostCentre"], geo["mapLeft"], f"the host's face is under the minimap at {viewport}")
                self.assertFalse(self._anchors_overlap(page), f"stage anchors overlap in dialogue at {viewport}")

                _inject_snapshot(page, {"local_map": valid_local_map_panel()}, mode="exploration")
                _wait_mode(page, "exploration")
                self.assertEqual(
                    page.evaluate("() => document.querySelector('[data-anchor=\"actor-right\"]').children.length"),
                    0,
                )
                page.close()

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
