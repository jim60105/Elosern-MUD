"""Local-map browser acceptance: lattice geometry budgets — island-content containment, the type ladder, the marker height budget, and dense/tall lattice scaling without overlap.
"""

from __future__ import annotations

import re
from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import store_state, wait_for_store_state


def _srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def _contrast_ratio(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    l1 = _relative_luminance(rgb1)
    l2 = _relative_luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _alpha_composite(fg: tuple[int, int, int], bg: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    return (
        round(fg[0] * alpha + bg[0] * (1 - alpha)),
        round(fg[1] * alpha + bg[1] * (1 - alpha)),
        round(fg[2] * alpha + bg[2] * (1 - alpha)),
    )


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join([c * 2 for c in h])
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class LocalMapBrowserTest(BrowserAcceptanceTest):
    """Dedicated minimap server with pre-recorded knowledge, shared per process."""
    @classmethod
    def setUpClass(cls) -> None:
        from . import fixtures
        from .harness import ManagedServer

        runtime = fixtures.create_runtime(prefix="elosern-minimap-")
        runtime.env["ELOSERN_BROWSER_MINIMAP"] = "1"
        cls.server = ManagedServer(runtime=runtime)
        cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.runtime.http_port}"
        cls.webclient_url = cls.server.runtime.webclient_url

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "server", None) is not None:
            try:
                cls.server.stop()
            finally:
                cls.server = None

    def _local_map_panel(self, page):
        return store_state(page)["panels"].get("local_map")

    def _wait_local_map_available(self, page, timeout=30000):
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("local_map", {}).get("available") is True,
            timeout=timeout,
        )
        return self._local_map_panel(page)

    def _local_map_nodes(self, page):
        return self._wait_local_map_available(page)["nodes"]

    def _send(self, page, command):
        page.evaluate(
            "(args) => Evennia.msg('text', [args.cmd], {})", {"cmd": command}
        )

    def _repin_at_home(self, page) -> None:
        """Deterministically pin the shared character back at the fixture's
        home grid room (capital map, slot (2, 0) — the bootstrap anchor the
        minimap fixture starts its knowledge walk from).

        Earlier journeys may have submitted one ``explore.move``, leaving the
        character on another grid node when this journey starts. The seeded
        account is a superuser, so the XYZ-grid ``teleport`` re-pins the
        character without traversing a costed exit; the panel refresh rides
        ``at_post_move``. The coordinate form is used instead of a room name:
        the map key comes from the boot mode's own grid catalog, and no ORM
        or registry read happens in the journey process (the server owns
        the boot-mode catalogs).
        """
        from world.quests.definitions import KNOWN_GRID_MAP_KEYS

        z_map = sorted(KNOWN_GRID_MAP_KEYS)[0]
        self._send(page, f"teleport (2, 0, {z_map})")
        wait_for_store_state(
            page,
            lambda s: (
                ((s.get("panels") or {}).get("local_map") or {}).get("current_node")
                == f"grid:{z_map}:2:0"
            ),
            timeout=15000,
        )

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    @covers_requirement(
        "webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention",
    )
    def test_minimap_content_stays_inside_its_island(self):
        # H2 re-map (task 9.2): the minimap is now the stage's right-anchor
        # island; the canvas, legend, remembered list, and detail line must
        # stay inside the island's bounded height without overprinting each
        # other, at both supported viewports.
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                # Deterministic geometry: re-pin at the fixture's home room
                # so the drawn extent (and its scaled cell budget) is the
                # fixture's own view in either boot mode, whatever an
                # earlier journey moved the shared character onto.
                self._repin_at_home(page)
                self._wait_local_map_available(page)
                wait_for_store_state(
                    page,
                    lambda s: (s.get("panels") or {}).get("local_map", {}).get("available") is True,
                    dom_readiness={
                        "selector": '[data-testid="local-map__lattice"]',
                        "predicate": "() => !!document.querySelector('[data-testid=\"local-map__lattice\"]')",
                        "description": "map lattice canvas rendered",
                    },
                    timeout=30000,
                )

                # Every node marker's bounding box is inside the map canvas.
                # (Remembered remote nodes render in the bounded list below
                # the canvas and are excluded here.) The check targets the
                # marker shapes (current rect / unvisited & visited circles),
                # not the whole node group whose decorative label may
                # overhang the canvas bottom edge (H2 re-map, task 9.2).
                canvas = page.locator('[data-testid="local-map__lattice"]')
                canvas_box = canvas.bounding_box()
                # Every node's primary marker shape (the current rect, the
                # unvisited/visited circles) — selected by the shared
                # `local-map__marker` class, not just the testid hooks (the
                # circle markers carry no testid).
                canvas_markers = page.locator(
                    '[data-testid="local-map__lattice"] .local-map__marker'
                )
                marker_count = canvas_markers.count()
                self.assertGreaterEqual(marker_count, 1)
                for index in range(marker_count):
                    inside = page.evaluate(
                        """(i) => {
                          const canvas = document.querySelector('[data-testid="local-map__lattice"]');
                          const marker = document.querySelectorAll(
                            '[data-testid="local-map__lattice"] .local-map__marker')[i];
                          const cr = canvas.getBoundingClientRect();
                          const nr = marker.getBoundingClientRect();
                          return nr.left >= cr.left - 1 && nr.right <= cr.right + 1 &&
                                 nr.top >= cr.top - 1 && nr.bottom <= cr.bottom + 1;
                        }""",
                        index,
                    )
                    self.assertTrue(
                        inside,
                        f"marker {index} must stay inside the map canvas at {viewport}",
                    )
                self.assertIsNotNone(canvas_box)

                # The crowding fix (fix-webclient-local-map-node-crowding):
                # no two node markers overlap, and no node label intersects a
                # marker or another label. The check requires a strictly
                # positive minimum visible gap (≥2px) between every rendered
                # marker/marker, marker/label, and label/label pair — the
                # old `+ 1` tolerance accepted the zero-gap crowding that
                # shipped.
                # NOTE: Playwright's string-evaluate context mis-parses a
                # chained `Array.from(x).map(f)` form ("missing ) after
                # argument list"); the two-argument `Array.from(x, f)` form
                # parses cleanly. Markers are selected by the shared
                # `local-map__marker` class (the circle markers carry no
                # testid), so every node's marker shape is checked.
                marker_boxes = page.evaluate(
                    """() => Array.from(
                        document.querySelectorAll('[data-testid="local-map__lattice"] .local-map__marker'),
                        (el) => {
                            const r = el.getBoundingClientRect();
                            return {left: r.left, top: r.top, right: r.right, bottom: r.bottom};
                        }
                    )"""
                )
                label_boxes = page.evaluate(
                    """() => Array.from(
                        document.querySelectorAll('[data-testid="local-map__lattice"] .local-map__node-label'),
                        (el) => {
                            const r = el.getBoundingClientRect();
                            return {left: r.left, top: r.top, right: r.right, bottom: r.bottom};
                        }
                    )"""
                )
                self.assertGreaterEqual(len(marker_boxes), 1)
                self.assertGreaterEqual(len(label_boxes), 1)

                def separated(a, b):
                    return (
                        a["right"] + 2 <= b["left"]
                        or b["right"] + 2 <= a["left"]
                        or a["bottom"] + 2 <= b["top"]
                        or b["bottom"] + 2 <= a["top"]
                    )

                for i in range(len(marker_boxes)):
                    for j in range(i + 1, len(marker_boxes)):
                        self.assertTrue(
                            separated(marker_boxes[i], marker_boxes[j]),
                            f"markers {i} and {j} lack a ≥2px gap at {viewport}",
                        )
                for m in marker_boxes:
                    for l in label_boxes:
                        self.assertTrue(
                            separated(m, l),
                            f"marker vs label lacks a ≥2px gap at {viewport}",
                        )
                for i in range(len(label_boxes)):
                    for j in range(i + 1, len(label_boxes)):
                        self.assertTrue(
                            separated(label_boxes[i], label_boxes[j]),
                            f"labels {i} and {j} lack a ≥2px gap at {viewport}",
                        )

                # The detail line remains visible below the canvas, and the
                # whole island's content (title/meta, canvas, remembered
                # list, detail) stays inside the island's bounded height —
                # no required surface has to be scrolled to (slim-minimap-
                # island: the legend left the island's section list).
                # Wave 1 & 3: Coordinate dot field, vignette, axis, and contrast gates (Tasks 3.1 - 3.3)
                dot_field = page.locator('[data-testid="local-map__dot-field"]')
                self.assertEqual(dot_field.count(), 1, "coordinate dot field must exist")
                self.assertTrue(dot_field.is_visible())
                dot_fill = dot_field.get_attribute("fill") or ""
                self.assertTrue(
                    dot_fill.startswith("url(#map-lattice-grid-"),
                    f"dot field fill must reference grid pattern, got {dot_fill}"
                )

                # Task 3.1: canvas spans roughly 5 coordinate cells across (~206 / 40 ≈ 5.15)
                pattern_width = float(page.locator("defs pattern").first.get_attribute("width"))
                canvas_user_width = float(page.locator('[data-testid="local-map__lattice"]').get_attribute("width"))
                cells_across = canvas_user_width / pattern_width
                self.assertGreaterEqual(cells_across, 4.5, f"cells across {cells_across} must be >= 4.5")
                self.assertLessEqual(cells_across, 5.5, f"cells across {cells_across} must be <= 5.5")

                # Task 3.2: Contrast gate (band from spec: >= 1.15 everywhere, >= 1.35 inner field, <= connector edge)
                tokens = page.evaluate("""() => {
                    const s = window.getComputedStyle(document.documentElement);
                    return {
                        ink860: s.getPropertyValue('--ink-860').trim() || '#151219',
                        inkEdge: s.getPropertyValue('--ink-edge').trim() || '#3a3344',
                        mapCanvasLo: s.getPropertyValue('--map-canvas-lo').trim() || '#0c0a10',
                    };
                }""")
                ground_rgb = _hex_to_rgb(tokens["ink860"])
                edge_ink_rgb = _hex_to_rgb(tokens["inkEdge"])
                fog_ink_rgb = _hex_to_rgb(tokens["mapCanvasLo"])

                # Read mounted SVG paint attributes from the DOM:
                dot_circle = page.locator("defs pattern circle").first
                dot_fill_opacity = float(dot_circle.get_attribute("fill-opacity") or 0.85)
                axis_el = page.locator('[data-testid="local-map__axis"]')
                self.assertEqual(axis_el.count(), 1, "axis cross must exist")
                self.assertTrue(axis_el.is_visible())
                axis_opacity = float(axis_el.get_attribute("opacity") or 0.80)

                vignette_el = page.locator('[data-testid="local-map__vignette"]')
                self.assertEqual(vignette_el.count(), 1, "vignette must exist")
                self.assertTrue(vignette_el.is_visible())
                vignette_stops = page.locator("defs radialGradient stop")
                outer_stop_opacity = float(vignette_stops.last.get_attribute("stop-opacity") or 0.50)
                self.assertLessEqual(outer_stop_opacity, 0.50, "vignette outer stop opacity must be <= 0.50")

                # Inner field (vignette opacity 0.0):
                inner_dot_rgb = _alpha_composite(edge_ink_rgb, ground_rgb, dot_fill_opacity)
                inner_axis_rgb = _alpha_composite(edge_ink_rgb, ground_rgb, axis_opacity)
                edge_rgb = edge_ink_rgb

                inner_dot_contrast = _contrast_ratio(inner_dot_rgb, ground_rgb)
                inner_axis_contrast = _contrast_ratio(inner_axis_rgb, ground_rgb)
                edge_contrast = _contrast_ratio(edge_rgb, ground_rgb)

                self.assertGreaterEqual(inner_dot_contrast, 1.35, "inner dot contrast must be >= 1.35:1")
                self.assertGreaterEqual(inner_axis_contrast, 1.35, "inner axis contrast must be >= 1.35:1")
                self.assertLessEqual(inner_dot_contrast, edge_contrast, "dot contrast must never exceed connector edge contrast")
                self.assertLessEqual(inner_axis_contrast, edge_contrast, "axis contrast must never exceed connector edge contrast")

                # Near corner (vignette outer stop opacity read from DOM):
                corner_ground_rgb = _alpha_composite(fog_ink_rgb, ground_rgb, outer_stop_opacity)
                corner_dot_rgb = _alpha_composite(fog_ink_rgb, inner_dot_rgb, outer_stop_opacity)
                corner_dot_contrast = _contrast_ratio(corner_dot_rgb, corner_ground_rgb)
                self.assertGreaterEqual(round(corner_dot_contrast, 2), 1.15, "corner dot contrast must be >= 1.15:1")

                # Task 3.3: Audit exclusions and single tab stop
                self.assertEqual(
                    page.locator('.local-map__dot-field.local-map__marker, .local-map__vignette.local-map__marker, .local-map__axis.local-map__marker').count(),
                    0,
                    "decoration layers must not carry local-map__marker class"
                )
                self.assertEqual(
                    page.locator('.local-map__dot-field.local-map__node-label, .local-map__vignette.local-map__node-label, .local-map__axis.local-map__node-label').count(),
                    0,
                    "decoration layers must not carry local-map__node-label class"
                )
                tab_stops = page.evaluate("""() => {
                    const island = document.querySelector('[data-testid="local-map"]');
                    const candidates = island.querySelectorAll(
                        'button:not([disabled]), [tabindex]:not([tabindex="-1"]), a[href]'
                    );
                    return Array.from(candidates).filter(el => {
                        const style = window.getComputedStyle(el);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    }).length;
                }""")
                self.assertEqual(tab_stops, 1, f"the island must expose exactly one tab stop at {viewport}")

                island_box = page.locator('[data-testid="local-map"]').bounding_box()
                self.assertIsNotNone(island_box)
                self.assertEqual(
                    page.locator('[data-testid="local-map__legend"]').count(), 0,
                    "the island mounts no state legend",
                )
                for testid in ("local-map-detail",):
                    box = page.locator(f'[data-testid="{testid}"]').bounding_box()
                    self.assertIsNotNone(box)
                    self.assertTrue(box["y"] >= island_box["y"] - 1)
                    self.assertTrue(box["y"] + box["height"] <= island_box["y"] + island_box["height"] + 1)
                self.assertTrue(page.locator('[data-testid="local-map-detail"]').is_visible())
                page.close()

    @covers_requirement(
        "webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention",
    )
    def test_island_type_ladder_stays_under_its_own_chrome_step(self):
        """No text the island draws outweighs the island's own chrome step.

        The spec bounds the node label at "the surface's own smallest chrome
        type step" and states the readout and the marker names at that same
        step. Because the island's coordinate margin resolves the uniform scale
        to ~1, a lattice user unit IS a drawn CSS pixel, so this is a single
        measurable ladder: header 10, readout 10, marker name 10, node label 9.
        It shipped inverted — the readout at 11 and the marker names at
        --text-sm (13), which drew the largest text on the card over the map it
        annotates.
        """
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                # Deterministic start: the island measures its edge markers
                # from the fixture's home view — the remembered gateway only
                # presents as a marker from a room whose field of view omits
                # it (earlier journeys may have moved the shared character
                # onto one that draws it in range).
                self._repin_at_home(page)
                page.wait_for_selector('[data-testid="local-map__lattice"]', timeout=30000)
                # The seeded grid payload carries a remembered gateway, so the
                # island draws at least one named edge marker to measure.
                page.wait_for_selector(
                    '[data-testid^="local-map__edge-marker--"]', timeout=15000
                )

                ladder = page.evaluate(
                    """() => {
                      const island = document.querySelector('[data-testid="local-map"]');
                      const svg = island.querySelector('[data-testid="local-map__lattice"]');
                      const cs = (el) => window.getComputedStyle(el);
                      const box = svg.getBoundingClientRect();
                      const svgStyle = cs(svg);
                      const drawnWidth =
                        box.width -
                        parseFloat(svgStyle.borderLeftWidth) -
                        parseFloat(svgStyle.borderRightWidth);
                      const viewBoxWidth = Number(svg.getAttribute('viewBox').split(' ')[2]);
                      const scale = drawnWidth / viewBoxWidth;
                      const px = (el) => parseFloat(cs(el).fontSize);
                      const drawn = (sel) =>
                        Array.from(island.querySelectorAll(sel)).map(
                          (el) => Math.round(px(el) * scale * 100) / 100
                        );
                      return {
                        scale: Math.round(scale * 1000) / 1000,
                        header: px(island.querySelector('[data-testid="local-map__title"]')),
                        readout: px(island.querySelector('[data-testid="local-map-detail"]')),
                        nodeLabels: drawn('.local-map__node-label'),
                        markerNames: drawn('.local-map__edge-marker-name--island'),
                      };
                    }"""
                )
                # The desktop redesign re-budgeted the draft's `.mini .mt`
                # header row for authored payload titles (LocalMap.vue
                # `.local-map__meta` at 12px), while the readout keeps the
                # spec's "island's smallest type step" (10px, the
                # token-driven closing-readout rule). The ladder is now
                # header 12 > chrome step 10 (webclient-local-map spec:
                # readout at the island's smallest type step; node labels at
                # most 9-unit type size, below the island's own 10px chrome
                # step).
                self.assertEqual(ladder["header"], 12, "the island's header type step is 12px")
                chrome_step = ladder["readout"]
                self.assertEqual(
                    chrome_step,
                    10,
                    "the readout states its figure at the island's smallest type step",
                )
                self.assertLessEqual(
                    ladder["scale"], 1, "coordinate margin never magnifies the drawing"
                )
                self.assertTrue(ladder["markerNames"], "at least one marker name is drawn")
                for size in ladder["markerNames"]:
                    self.assertLessEqual(
                        size,
                        chrome_step,
                        f"a marker name drawn at {size}px outweighs the island's chrome",
                    )
                self.assertTrue(ladder["nodeLabels"], "at least one node label is drawn")
                for size in ladder["nodeLabels"]:
                    self.assertLessEqual(
                        size,
                        chrome_step,
                        f"a node label drawn at {size}px outweighs the island's chrome",
                    )
                page.close()

    @covers_requirement(
        "webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone"
    )
    def test_marker_mirror_is_out_of_the_island_height_budget(self):
        """The AT mirror is presentation-free: it costs the island no height.

        ``measureCanvasBudget()`` reserves height for the meta row, the canvas,
        and at most one of {the graph-variant remembered list, the readout}.
        The visually-hidden marker mirror is deliberately not among them, so it
        MUST stay out of the flex flow — otherwise it spends its own box plus a
        full inter-section gap of budget nobody reserved, and its clip-rect
        hiding stops applying (``clip`` only affects absolutely positioned
        boxes).
        """
        page = self.logged_in_page()
        # The mirror mirrors the home view's remembered gateway marker (see
        # the remembered-node journey): re-pin so the marker exists no
        # matter where an earlier journey left the shared character.
        self._repin_at_home(page)
        self._wait_local_map_available(page)
        page.wait_for_selector('[data-testid="local-map-edge-markers-mirror"]', timeout=30000)

        layout = page.evaluate(
            """() => {
              const island = document.querySelector('[data-testid="local-map"]');
              const mirror = island.querySelector('[data-testid="local-map-edge-markers-mirror"]');
              const out = (el) => ['absolute', 'fixed'].includes(
                window.getComputedStyle(el).position
              );
              const inFlow = Array.from(island.children).filter((el) => !out(el));
              const detail = island.querySelector('[data-testid="local-map-detail"]');
              return {
                mirrorPosition: window.getComputedStyle(mirror).position,
                mirrorEntries: mirror.querySelectorAll('li').length,
                mirrorInFlow: inFlow.includes(mirror),
                inFlowCount: inFlow.length,
                hasRememberedList:
                  island.querySelectorAll('[data-testid="local-map-remembered"]').length > 0,
                readoutLaidOut: detail.getBoundingClientRect().height > 0,
              };
            }"""
        )
        self.assertGreaterEqual(layout["mirrorEntries"], 1, "the mirror lists its markers")
        self.assertEqual(
            layout["mirrorPosition"],
            "absolute",
            "the mirror must stay absolutely positioned, or clip-rect hiding stops applying",
        )
        self.assertFalse(layout["mirrorInFlow"], "the mirror is not a laid-out island section")
        # The laid-out sections are exactly the ones the budget counts.
        expected = 2 + int(layout["hasRememberedList"]) + int(layout["readoutLaidOut"])
        self.assertEqual(
            layout["inFlowCount"],
            expected,
            "the island lays out only the sections measureCanvasBudget() reserves for",
        )
