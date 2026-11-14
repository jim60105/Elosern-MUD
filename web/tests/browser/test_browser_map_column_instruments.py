"""Live-client acceptance for the map column's instrument panels.

map-column-instrument-geometry: the `map` anchor's width floor, right gutter,
paint-free box, 10px stack gap, presence-rail clearance, hidden scrollbar and
scroll-edge fade. The later changes of this batch add their methods here.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest, ui_scale
from .browser_helpers import (
    inject_snapshot,
    valid_art_panel,
    valid_local_map_panel,
    valid_status_panel,
)


def _objectives_panel(count: int) -> dict:
    """A committed objectives v1 panel with ``count`` tracked rows."""
    return {
        "schema_version": 1,
        "available": True,
        "rows": [
            {
                "quest_id": f"q_{1042 + i}",
                "display_name": f"委託{i + 1}",
                "objective_line": f"前往第{i + 1}個渡口",
                "stage_index": 1,
                "stage_total": 1,
                "stage_progress": 0,
                "objective_quantity": 1,
                "reward_copper": 80 if i else None,
                "deadline_line": "剩餘 2 日" if i == 1 else None,
            }
            for i in range(count)
        ],
    }


_ANCHOR = '[data-anchor="map"]'

_GEOMETRY_JS = """() => {
  const anchor = document.querySelector('[data-anchor="map"]');
  const stage = document.querySelector('[data-testid="elosern-stage"]');
  const presence = document.querySelector('[data-anchor="presence"]');
  const card = document.querySelector('[data-testid="place-card"]');
  const style = getComputedStyle(anchor);
  let cardChild = card;
  while (cardChild && cardChild.parentElement !== anchor) cardChild = cardChild.parentElement;
  const next = cardChild ? cardChild.nextElementSibling : null;
  const a = anchor.getBoundingClientRect();
  return {
    left: a.left,
    right: a.right,
    width: a.width,
    stageRight: stage.getBoundingClientRect().right,
    presenceRight: presence.getBoundingClientRect().right,
    offsetWidth: anchor.offsetWidth,
    clientWidth: anchor.clientWidth,
    background: style.backgroundColor,
    borderTop: style.borderTopWidth,
    boxShadow: style.boxShadow,
    cardBottom: cardChild ? cardChild.getBoundingClientRect().bottom : null,
    nextTop: next ? next.getBoundingClientRect().top : null,
  };
}"""

_EDGES_JS = """() => {
  const anchor = document.querySelector('[data-anchor="map"]');
  return {
    above: anchor.hasAttribute('data-more-above'),
    below: anchor.hasAttribute('data-more-below'),
    mask: getComputedStyle(anchor).maskImage,
  };
}"""

_WAIT_EDGES_JS = """([above, below]) => {
  const anchor = document.querySelector('[data-anchor="map"]');
  return anchor.hasAttribute('data-more-above') === above
    && anchor.hasAttribute('data-more-below') === below;
}"""

# The probe is test-made, not a client surface, so it carries a plain data
# attribute rather than a frozen-audit `data-testid`.
_ADD_PROBE_JS = """() => {
  const probe = document.createElement('div');
  probe.setAttribute('data-map-overflow-probe', '');
  probe.style.cssText = 'height: 600px; flex: none';
  document.querySelector('[data-anchor="map"]').appendChild(probe);
}"""

_REMOVE_PROBE_JS = """() => {
  document.querySelector('[data-map-overflow-probe]')?.remove();
}"""

_SCROLL_JS = """(position) => {
  const anchor = document.querySelector('[data-anchor="map"]');
  const span = anchor.scrollHeight - anchor.clientHeight;
  anchor.scrollTop = position === 'top' ? 0 : position === 'middle' ? span / 2 : anchor.scrollHeight;
}"""

# Two animation frames: the observers' callbacks have run for the current
# layout before an absence is asserted.
_SETTLE_JS = "() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(() => done(true))))"


class MapColumnInstrumentBrowserTest(BrowserAcceptanceTest):
    """The `map` column's instrument geometry and its scroll-edge fade."""

    def _open_populated_column(self, viewport):
        page = self.logged_in_page(viewport)
        inject_snapshot(
            page,
            {
                "status": valid_status_panel("艾倫‧灰誓", "char-42"),
                "local_map": valid_local_map_panel(),
                "art": valid_art_panel(),
                "objectives": _objectives_panel(1),
            },
            mode="exploration",
        )
        page.wait_for_selector('[data-testid="place-card"]', timeout=15000)
        page.wait_for_selector('[data-testid="local-map"]', timeout=15000)
        page.wait_for_selector('[data-testid="objective-tracker"]', timeout=15000)
        page.evaluate("document.fonts.ready")
        page.mouse.move(viewport[0] // 2, viewport[1] // 2)
        page.evaluate(_SETTLE_JS)
        return page

    def _wait_edges(self, page, above: bool, below: bool) -> None:
        page.wait_for_function(_WAIT_EDGES_JS, arg=[above, below], timeout=5000)

    @covers_requirement(
        "webclient-contextual-hud::the-map-column-holds-its-instrument-geometry-and-fades-hidden-overflow",
    )
    def test_map_column_holds_its_width_and_fades_hidden_overflow(self):
        """At 1280x720, 1451x790 and 2560x1440 the `map` anchor is the
        floored column width with a 16px x S right gutter, paints nothing,
        takes no scrollbar width, stacks its surfaces 10px x S apart and
        stands 24px x S right of the presence rail; a fitting column is
        unmasked; an over-tall column masks exactly the edges with content
        beyond them, and content changes update the fade without a scroll."""
        for viewport, expected_width in (((1280, 720), 282.0), ((1451, 790), 291.2), ((2560, 1440), 464.8)):
            with self.subTest(viewport=viewport):
                scale = ui_scale(viewport)
                page = self._open_populated_column(viewport)
                geo = page.evaluate(_GEOMETRY_JS)
                self.assertAlmostEqual(geo["width"], expected_width, delta=1.0, msg=f"column width at {viewport}")
                self.assertAlmostEqual(geo["stageRight"] - geo["right"], 16 * scale, delta=1.0, msg="right gutter")
                self.assertEqual(geo["offsetWidth"], geo["clientWidth"], "the scrollbar takes no width")
                self.assertEqual(geo["background"], "rgba(0, 0, 0, 0)")
                self.assertEqual(geo["borderTop"], "0px")
                self.assertEqual(geo["boxShadow"], "none")
                self.assertAlmostEqual(geo["presenceRight"], geo["left"] - 24 * scale, delta=1.0, msg="presence clearance")
                self.assertIsNotNone(geo["cardBottom"], "the place card is an anchor child")
                self.assertIsNotNone(geo["nextTop"], "a surface follows the place card")
                self.assertAlmostEqual(geo["nextTop"] - geo["cardBottom"], 10 * scale, delta=1.0, msg="stack gap")

                if viewport != (1280, 720):
                    edges = page.evaluate(_EDGES_JS)
                    self.assertFalse(edges["above"], f"no top fade at {viewport}")
                    self.assertFalse(edges["below"], f"no bottom fade at {viewport}")
                    self.assertEqual(edges["mask"], "none", f"a fitting column is unmasked at {viewport}")

                try:
                    if viewport == (1280, 720):
                        # Whether the populated column fits here changes across
                        # this batch, so the baseline's bottom edge is recorded,
                        # not asserted; a probe makes it overflow for certain.
                        page.evaluate(_SCROLL_JS, "top")
                        page.evaluate(_SETTLE_JS)
                        baseline = page.evaluate(_EDGES_JS)
                        self.assertFalse(baseline["above"], "scrolled to the top, nothing lies above")
                        page.evaluate(_ADD_PROBE_JS)
                        page.wait_for_function(
                            "() => document.querySelector('[data-anchor=\"map\"]').hasAttribute('data-more-below')",
                            timeout=5000,
                        )
                        edges = page.evaluate(_EDGES_JS)
                        self.assertFalse(edges["above"], "at the top only the bottom edge fades")
                        self.assertNotEqual(edges["mask"], "none", "the bottom edge is masked")
                        page.evaluate(_SCROLL_JS, "middle")
                        self._wait_edges(page, True, True)
                        self.assertNotEqual(page.evaluate(_EDGES_JS)["mask"], "none")
                        page.evaluate(_SCROLL_JS, "bottom")
                        self._wait_edges(page, True, False)
                        self.assertNotEqual(page.evaluate(_EDGES_JS)["mask"], "none")
                        page.evaluate(_REMOVE_PROBE_JS)
                        page.evaluate(_SCROLL_JS, "top")
                        self._wait_edges(page, False, baseline["below"])
                    elif viewport == (1451, 790):
                        # A column that starts to overflow gains its bottom
                        # fade, and loses every fade once it fits again, with
                        # no scroll event.
                        page.evaluate(_ADD_PROBE_JS)
                        page.wait_for_function(
                            "() => document.querySelector('[data-anchor=\"map\"]').hasAttribute('data-more-below')",
                            timeout=5000,
                        )
                        page.evaluate(_REMOVE_PROBE_JS)
                        self._wait_edges(page, False, False)
                        page.evaluate(_SETTLE_JS)
                        self.assertEqual(page.evaluate(_EDGES_JS)["mask"], "none")
                finally:
                    page.evaluate(_REMOVE_PROBE_JS)
