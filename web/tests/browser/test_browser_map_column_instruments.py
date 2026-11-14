"""Live-client acceptance for the map column's instrument panels.

map-column-instrument-geometry: the `map` anchor's width floor, right gutter,
paint-free box, 10px stack gap, presence-rail clearance, hidden scrollbar and
scroll-edge fade. place-card-instrument-panel: the place card as an instrument
panel. local-map-instrument-panel: the minimap as a card-free island inside
its own instrument panel. objective-tracker-instrument-panel: the objective
line as an instrument panel with its completion lozenge and quantity strokes.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from ._journey_support import _exploration_context_actions_panel, _exploration_panel
from .browser_base import BrowserAcceptanceTest, ui_scale
from .browser_helpers import (
    PLACE_LOOK_SELECTOR,
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

_PLACE_PANEL_JS = """() => {
  const anchor = document.querySelector('[data-anchor="map"]');
  const card = document.querySelector('[data-testid="place-card"]');
  const cs = getComputedStyle(card);
  const before = getComputedStyle(card, '::before');
  const after = getComputedStyle(card, '::after');
  const box = (el) => {
    const r = el.getBoundingClientRect();
    return { left: r.left, right: r.right, width: r.width, height: r.height };
  };
  const q = (id) => card.querySelector(`[data-testid="${id}"]`);
  const button = (id) => {
    const el = q(id);
    const style = getComputedStyle(el);
    return {
      ...box(el),
      border: style.borderTopWidth,
      background: style.backgroundColor,
      tick: getComputedStyle(el, '::after').opacity,
      text: el.innerText.trim(),
    };
  };
  return {
    card: box(card),
    anchorWidth: anchor.getBoundingClientRect().width,
    scrollHeight: anchor.scrollHeight,
    clientHeight: anchor.clientHeight,
    borderTop: cs.borderTopWidth,
    borderLeft: cs.borderLeftWidth,
    radius: cs.borderTopLeftRadius,
    shadow: cs.boxShadow,
    background: cs.backgroundColor,
    paddingRight: parseFloat(cs.paddingRight),
    groundMask: before.maskImage || before.webkitMaskImage,
    groundBackground: before.backgroundColor,
    fittingImage: after.backgroundImage,
    fittingPointer: after.pointerEvents,
    headingAlign: getComputedStyle(q('place-card__location')).textAlign,
    timeAlign: getComputedStyle(q('place-card__time')).textAlign,
    rule: box(q('place-card__rule')),
    location: box(q('place-card__location')),
    time: box(q('place-card__time')),
    look: button('place-card-look'),
    wait: button('place-card-wait'),
  };
}"""

_TICK_JS = """(id) => getComputedStyle(
  document.querySelector(`[data-testid="${id}"]`), '::after').opacity"""

_MINIMAP_PANEL_JS = """() => {
  const anchor = document.querySelector('[data-anchor="map"]');
  const card = document.querySelector('[data-testid="place-card"]');
  const panel = document.querySelector('[data-testid="local-map-panel"]');
  const island = document.querySelector('[data-testid="local-map"]');
  const lattice = island.querySelector('[data-testid="local-map__lattice"]');
  const ps = getComputedStyle(panel);
  const before = getComputedStyle(panel, '::before');
  const after = getComputedStyle(panel, '::after');
  const is = getComputedStyle(island);
  const rect = (el) => {
    const r = el.getBoundingClientRect();
    return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height };
  };
  return {
    anchor: rect(anchor),
    card: rect(card),
    panel: rect(panel),
    lattice: rect(lattice),
    panelBorders: [ps.borderTopWidth, ps.borderRightWidth, ps.borderBottomWidth, ps.borderLeftWidth],
    panelRadius: ps.borderTopLeftRadius,
    panelShadow: ps.boxShadow,
    panelBackground: ps.backgroundColor,
    groundMask: before.maskImage || before.webkitMaskImage,
    fittingPointer: after.pointerEvents,
    islandBorders: [is.borderTopWidth, is.borderRightWidth, is.borderBottomWidth, is.borderLeftWidth],
    islandShadow: is.boxShadow,
    islandBackground: is.backgroundColor,
    islandPadding: [is.paddingTop, is.paddingRight, is.paddingBottom, is.paddingLeft],
    latticeImage: getComputedStyle(lattice).backgroundImage,
    legends: document.querySelectorAll('[data-testid="local-map__orientation"]').length,
    axes: document.querySelectorAll('.local-map [data-testid="local-map__axis"]').length,
  };
}"""

def _counted_objectives_panel(quantity: int, progress: int) -> dict:
    """An objectives panel whose first row counts ``progress`` of ``quantity``
    and whose second row is a single-count quest with an 80-copper reward."""
    return {
        "schema_version": 1,
        "available": True,
        "rows": [
            {
                "quest_id": "q_1042",
                "display_name": "清點貨箱",
                "objective_line": "清點碼頭倉庫的貨箱",
                "stage_index": 1,
                "stage_total": 1,
                "stage_progress": progress,
                "objective_quantity": quantity,
                "reward_copper": None,
                "deadline_line": None,
            },
            {
                "quest_id": "q_1043",
                "display_name": "過河商議",
                "objective_line": "與灰婆婆議價過河",
                "stage_index": 1,
                "stage_total": 1,
                "stage_progress": 0,
                "objective_quantity": 1,
                "reward_copper": 80,
                "deadline_line": None,
            },
        ],
    }


_OBJECTIVE_PANEL_JS = """() => {
  const card = document.querySelector('[data-testid="place-card"]');
  const tracker = document.querySelector('[data-testid="objective-tracker"]');
  const cs = getComputedStyle(tracker);
  const before = getComputedStyle(tracker, '::before');
  const rect = (el) => {
    const r = el.getBoundingClientRect();
    return { left: r.left, right: r.right, width: r.width };
  };
  const box = tracker.querySelector('[data-testid^="objective-tracker__box--"]');
  const stroke = tracker.querySelector('[data-testid="objective-tracker__stroke"]');
  const fill = tracker.querySelector('[data-testid="objective-tracker__stroke-fill"]');
  return {
    card: rect(card),
    tracker: rect(tracker),
    borders: [cs.borderTopWidth, cs.borderRightWidth, cs.borderBottomWidth, cs.borderLeftWidth],
    radius: cs.borderTopLeftRadius,
    shadow: cs.boxShadow,
    background: cs.backgroundColor,
    groundMask: before.maskImage || before.webkitMaskImage,
    descendantRights: Array.from(tracker.querySelectorAll('*'))
      .map((el) => el.getBoundingClientRect())
      .filter((r) => r.width > 0 || r.height > 0)
      .map((r) => r.right),
    innerText: tracker.innerText,
    label: tracker.getAttribute('aria-label'),
    boxLabel: box.getAttribute('aria-label'),
    check: !!box.querySelector('.bx__check'),
    ticks: Array.from(tracker.querySelectorAll('[data-testid="objective-tracker__tick"]')).map((el) => ({
      on: el.classList.contains('obj__tick--on'),
      width: el.getBoundingClientRect().width,
    })),
    strokeWidth: stroke ? stroke.getBoundingClientRect().width : null,
    fillWidth: fill ? fill.getBoundingClientRect().width : null,
  };
}"""

_GLYPH_OPACITY_JS = "() => getComputedStyle(document.querySelector('.local-map__expand-icon')).opacity"

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

    @covers_requirement(
        "webclient-contextual-hud::an-instrument-panel-wears-a-feathered-ground-and-one-brass-fitting-instead-of-a-box",
        "webclient-contextual-hud::the-place-card-names-the-current-location-and-the-world-time",
    )
    def test_place_card_is_an_instrument_panel(self):
        """At 1280x720, 1451x790 and 2560x1440 the place card is no box: it
        paints a masked, blurred ground and a brass fitting as decoration,
        spans the column, right-aligns its lines and its rule, keeps every
        content element and both chromeless room actions clear of the spine,
        and ticks only the hovered action; at 1451x790 and 2560x1440 the
        column with the two-row action card still fits its anchor."""
        for viewport in ((1280, 720), (1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                scale = ui_scale(viewport)
                page = self.logged_in_page(viewport)
                inject_snapshot(
                    page,
                    {
                        "status": valid_status_panel("艾倫‧灰誓", "char-42"),
                        "local_map": valid_local_map_panel(),
                        "exploration": _exploration_panel([]),
                        "context_actions": _exploration_context_actions_panel(),
                        "art": valid_art_panel(),
                        "objectives": _objectives_panel(3),
                    },
                    mode="exploration",
                )
                page.wait_for_selector('[data-testid="place-card-wait"]', timeout=15000)
                page.evaluate("document.fonts.ready")
                page.mouse.move(0, 0)
                page.evaluate(_SETTLE_JS)
                panel = page.evaluate(_PLACE_PANEL_JS)

                # The panel itself is not a box.
                self.assertEqual(panel["borderTop"], "0px")
                self.assertEqual(panel["borderLeft"], "0px")
                self.assertEqual(panel["radius"], "0px")
                self.assertEqual(panel["shadow"], "none")
                self.assertEqual(panel["background"], "rgba(0, 0, 0, 0)")
                # The ground and the fitting are painted decoration.
                self.assertTrue(panel["groundMask"], "the ground has a mask")
                self.assertNotEqual(panel["groundMask"], "none", "the ground is masked")
                self.assertNotIn(panel["groundBackground"], ("rgba(0, 0, 0, 0)", "transparent"))
                self.assertTrue(
                    "url(" in panel["fittingImage"] or "gradient" in panel["fittingImage"],
                    f"the fitting paints the ornament: {panel['fittingImage']}",
                )
                self.assertEqual(panel["fittingPointer"], "none")

                card = panel["card"]
                self.assertAlmostEqual(card["width"], panel["anchorWidth"], delta=1.0, msg="the card spans the column")
                self.assertEqual(panel["headingAlign"], "right")
                self.assertEqual(panel["timeAlign"], "right")
                self.assertAlmostEqual(
                    panel["rule"]["right"], card["right"] - panel["paddingRight"], delta=1.0,
                    msg="the rule stands at the content box's right end",
                )
                spine = card["right"] - 14 * scale + 0.5
                for name in ("location", "time", "look", "wait"):
                    self.assertLessEqual(panel[name]["right"], spine, f"{name} stays clear of the spine at {viewport}")

                for name in ("look", "wait"):
                    btn = panel[name]
                    self.assertEqual(btn["border"], "0px", f"{name} has no border")
                    self.assertEqual(btn["background"], "rgba(0, 0, 0, 0)", f"{name} has no fill")
                    self.assertGreaterEqual(btn["width"], 30 * scale - 0.5, f"{name} hit box width")
                    self.assertGreaterEqual(btn["height"], 30 * scale - 0.5, f"{name} hit box height")
                    self.assertEqual(btn["tick"], "0", f"{name} shows no tick at rest")
                self.assertEqual(panel["wait"]["text"], "休息")

                page.hover(PLACE_LOOK_SELECTOR)
                page.wait_for_function(f"() => ({_TICK_JS})('place-card-look') === '1'", timeout=5000)
                self.assertEqual(page.evaluate(_TICK_JS, "place-card-wait"), "0", "only the hovered action ticks")

                if viewport != (1280, 720):
                    self.assertLessEqual(
                        panel["scrollHeight"], panel["clientHeight"] + 1,
                        f"the column fits its anchor at {viewport}: "
                        f"scrollHeight {panel['scrollHeight']}, clientHeight {panel['clientHeight']}",
                    )
                page.close()

    @covers_requirement(
        "webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention",
        "webclient-contextual-hud::an-instrument-panel-wears-a-feathered-ground-and-one-brass-fitting-instead-of-a-box",
        "webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure",
    )
    def test_minimap_is_a_card_free_instrument_panel(self):
        """At 1280x720, 1451x790 and 2560x1440 the minimap's instrument panel
        is no box, spans the column under the place card across the stack
        gap, and paints a masked ground and an inert fitting; the island
        inside it wears no card; the 240px x S canvas keeps its corner
        brackets and stands 22px x S left of the panel's right edge; no
        orientation legend exists while the lattice draws its axis; and the
        open-map glyph is dimmed at rest and fully opaque on hover and on
        keyboard focus."""
        for viewport in ((1280, 720), (1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                scale = ui_scale(viewport)
                page = self.logged_in_page(viewport)
                inject_snapshot(
                    page,
                    {
                        "status": valid_status_panel("艾倫‧灰誓", "char-42"),
                        "local_map": valid_local_map_panel(),
                        "art": valid_art_panel(),
                    },
                    mode="exploration",
                )
                page.wait_for_selector('[data-testid="local-map-panel"]', timeout=15000)
                page.wait_for_selector('[data-testid="local-map__lattice"]', timeout=15000)
                page.evaluate("document.fonts.ready")
                page.mouse.move(5, 5)
                page.evaluate(_SETTLE_JS)
                probe = page.evaluate(_MINIMAP_PANEL_JS)

                # The panel is no box; its ground and fitting are decoration.
                self.assertEqual(probe["panelBorders"], ["0px"] * 4)
                self.assertEqual(probe["panelRadius"], "0px")
                self.assertEqual(probe["panelShadow"], "none")
                self.assertEqual(probe["panelBackground"], "rgba(0, 0, 0, 0)")
                self.assertTrue(probe["groundMask"], "the ground has a mask")
                self.assertNotEqual(probe["groundMask"], "none", "the ground is masked")
                self.assertEqual(probe["fittingPointer"], "none")

                # The panel spans the column directly under the place card.
                panel, card = probe["panel"], probe["card"]
                self.assertAlmostEqual(panel["width"], probe["anchor"]["width"], delta=1.0, msg="the panel spans the column")
                self.assertAlmostEqual(panel["left"], card["left"], delta=1.0, msg="left edge matches the place card")
                self.assertAlmostEqual(panel["right"], card["right"], delta=1.0, msg="right edge matches the place card")
                self.assertAlmostEqual(panel["top"] - card["bottom"], 10 * scale, delta=1.0, msg="stack gap")

                # The island inside it wears no card.
                self.assertEqual(probe["islandBorders"], ["0px"] * 4)
                self.assertEqual(probe["islandShadow"], "none")
                self.assertEqual(probe["islandBackground"], "rgba(0, 0, 0, 0)")
                self.assertEqual(probe["islandPadding"], ["0px"] * 4)

                # The canvas keeps its size and brackets and clears the spine.
                lattice = probe["lattice"]
                self.assertAlmostEqual(lattice["width"], 240 * scale, delta=1.0, msg="canvas width")
                self.assertAlmostEqual(lattice["height"], 240 * scale, delta=1.0, msg="canvas height")
                self.assertAlmostEqual(panel["right"] - lattice["right"], 22 * scale, delta=1.0, msg="spine clearance")
                self.assertIn("linear-gradient", probe["latticeImage"], "the corner brackets stay")

                # No legend; the seeded grid payload is a lattice with its axis.
                self.assertEqual(probe["legends"], 0)
                self.assertEqual(probe["axes"], 1)

                # The open-map glyph answers hover and focus.
                self.assertEqual(page.evaluate(_GLYPH_OPACITY_JS), "0.86")
                page.hover('[data-testid="local-map-detail"]')
                page.wait_for_function(f"() => ({_GLYPH_OPACITY_JS})() === '1'", timeout=5000)
                page.mouse.move(5, 5)
                page.focus('[data-testid="local-map__expand"]')
                page.wait_for_function(f"() => ({_GLYPH_OPACITY_JS})() === '1'", timeout=5000)
                page.close()

    @covers_requirement(
        "webclient-contextual-hud::the-objective-tracker-island-presents-the-committed-objectives-only",
        "webclient-contextual-hud::an-instrument-panel-wears-a-feathered-ground-and-one-brass-fitting-instead-of-a-box",
    )
    def test_objective_line_is_an_instrument_panel_with_quantity_strokes(self):
        """At 1280x720, 1451x790 and 2560x1440 the objective line is no box:
        it paints a masked ground, shares the place card's edges and keeps
        every element clear of the spine; 目標 is its accessible name only;
        a count of 5 draws five 13px x S ticks with the reached ones first;
        a count of 30 draws one stroke filled to the ratio; a reached count
        fills the lozenge with a check named 已達成."""
        for viewport in ((1280, 720), (1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                scale = ui_scale(viewport)
                page = self.logged_in_page(viewport)
                base = {
                    "status": valid_status_panel("艾倫‧灰誓", "char-42"),
                    "local_map": valid_local_map_panel(),
                    "art": valid_art_panel(),
                }
                inject_snapshot(page, {**base, "objectives": _counted_objectives_panel(5, 2)}, mode="exploration")
                page.wait_for_selector('[data-testid="objective-tracker__ticks"]', timeout=15000)
                page.wait_for_selector('[data-testid="place-card"]', timeout=15000)
                page.evaluate("document.fonts.ready")
                page.evaluate(_SETTLE_JS)
                probe = page.evaluate(_OBJECTIVE_PANEL_JS)

                # The panel is no box; its ground is decoration.
                self.assertEqual(probe["borders"], ["0px"] * 4)
                self.assertEqual(probe["radius"], "0px")
                self.assertEqual(probe["shadow"], "none")
                self.assertEqual(probe["background"], "rgba(0, 0, 0, 0)")
                self.assertTrue(probe["groundMask"], "the ground has a mask")
                self.assertNotEqual(probe["groundMask"], "none", "the ground is masked")

                tracker, card = probe["tracker"], probe["card"]
                self.assertAlmostEqual(tracker["left"], card["left"], delta=1.0, msg="left edge matches the place card")
                self.assertAlmostEqual(tracker["right"], card["right"], delta=1.0, msg="right edge matches the place card")
                spine = tracker["right"] - 14 * scale + 0.5
                for right in probe["descendantRights"]:
                    self.assertLessEqual(right, spine, f"content stays clear of the spine at {viewport}")

                # 目標 is the accessible name, never visible text.
                self.assertNotIn("目標", probe["innerText"])
                self.assertEqual(probe["label"], "目標")
                self.assertEqual(probe["boxLabel"], "進行中")
                self.assertFalse(probe["check"], "an open lozenge carries no check")

                # One tick per unit, the reached ones first.
                self.assertEqual([t["on"] for t in probe["ticks"]], [True, True, False, False, False])
                for tick in probe["ticks"]:
                    self.assertAlmostEqual(tick["width"], 13 * scale, delta=1.0, msg="tick width")

                # Above twelve units: one stroke filled to the ratio.
                inject_snapshot(page, {**base, "objectives": _counted_objectives_panel(30, 12)}, mode="exploration")
                page.wait_for_selector('[data-testid="objective-tracker__stroke"]', timeout=15000)
                page.evaluate(_SETTLE_JS)
                probe = page.evaluate(_OBJECTIVE_PANEL_JS)
                self.assertEqual(probe["ticks"], [], "no ticks above twelve units")
                self.assertGreater(probe["strokeWidth"], 0)
                self.assertAlmostEqual(
                    probe["fillWidth"] / probe["strokeWidth"], 0.4,
                    delta=1 / probe["strokeWidth"] + 0.01, msg="the stroke fills to the ratio",
                )

                # A reached count fills the lozenge with a check.
                inject_snapshot(page, {**base, "objectives": _counted_objectives_panel(5, 5)}, mode="exploration")
                page.wait_for_function(
                    "() => document.querySelector('[data-testid=\"objective-tracker__box--q_1042\"]')"
                    "?.getAttribute('aria-label') === '已達成'",
                    timeout=15000,
                )
                probe = page.evaluate(_OBJECTIVE_PANEL_JS)
                self.assertEqual(probe["boxLabel"], "已達成")
                self.assertTrue(probe["check"], "a reached lozenge carries a check")
                page.close()
