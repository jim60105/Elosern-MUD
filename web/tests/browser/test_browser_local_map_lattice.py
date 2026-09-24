"""Local-map browser acceptance: dense/tall lattice scaling within the island height budget and crowded edge-overlay marker-name separation.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import store_state, wait_for_store_state


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

    # The maximal-height, minimal-width lattice (task 3.5): 64 in-view nodes,
    # one per row across 64 rows, alternating the two columns — a legal
    # 64-node payload (the model's node bound). Mirrors
    # LOCAL_MAP_TALL_LATTICE_SAMPLE in web/webclient-app/stories/fixtures.js.
    def _tall_lattice_payload(self, rows: int = 64, remembered_count: int = 0) -> dict:
        # `rows` in-view nodes (2 cols × rows, current at the middle row),
        # plus up to `remembered_count` remembered far nodes outside the
        # in-view coordinate range. 48 + 16 = 64 hits the model's node
        # bound (MAX_NODES), the blocking combination the crowding fix
        # targets.
        cur = rows // 2
        cur_x = cur % 2
        nodes = []
        for y in range(rows):
            x = y % 2
            is_current = y == cur
            nodes.append(
                {
                    "id": f"grid:altoria:{x}:{y}",
                    "label": "霧骨渡口碼頭" if y % 16 == 0 else f"渡口{y % 8}",
                    "x": x,
                    "y": y,
                    "visibility": "current" if is_current else "visible_unvisited",
                    "current": is_current,
                    "anchor": is_current,
                    "landmark": is_current,
                    "action": None,
                }
            )
        for i in range(remembered_count):
            nodes.append(
                {
                    "id": f"grid:altoria:{5 + i % 6}:{100 + i}",
                    "label": "遠方路網",
                    "x": 5 + i % 6,
                    "y": 100 + i,
                    "visibility": "remembered",
                    "current": False,
                    "anchor": False,
                    "landmark": True,
                    "action": None,
                }
            )
        other_x = 1 - cur_x
        return {
            "schema_version": 1,
            "available": True,
            "layer": "grid",
            "current_node": f"grid:altoria:{cur_x}:{cur}",
            "title": "霧骨渡口",
            "nodes": nodes,
            "edges": [
                {
                    "source": f"grid:altoria:{cur_x}:{cur}",
                    "destination": f"grid:altoria:{other_x}:{cur + 1}",
                    "label": "北岸",
                    "known": True,
                    "traversable": True,
                },
                {
                    "source": f"grid:altoria:{cur_x}:{cur}",
                    "destination": f"grid:altoria:{other_x}:{cur - 1}",
                    "label": "南門",
                    "known": True,
                    "traversable": False,
                },
            ],
            "legend": [
                "你目前所在的位置",
                "尚未探索的相鄰位置",
                "已經探索過的相鄰位置",
            ],
        }

    def _inject_panel(self, page, panel) -> dict:
        return page.evaluate(
            """(panel) => {
              const bridge = window.__elosernBridge;
              const v = bridge.store.view;
              const envelope = {
                protocol_version: 1,
                presentation_epoch: v.epoch,
                revision: v.revision + 1,
                mode: v.mode,
                layout_version: v.layoutVersion ?? 1,
                panels: { local_map: panel },
                server_time: { year: 1, season_index: 0, season_label: "春", day_in_season: 1, hour: 12, minute: 0, second: 0 },
              };
              return bridge.store.receive(v.generation, "ui_update", [envelope], {});
            }""",
            panel,
        )

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_densely_populated_lattice_scales_down_without_reintroducing_overlap(self):
        # A densely populated lattice (2 cols × 64 rows) must scale the
        # canvas down to fit the island's bounded height — pre-scale
        # geometry satisfies the non-overlap invariant, and the scaled-down
        # render keeps markers and labels non-intersecting. Verified at
        # both supported viewports (the 296px cap was computed from the
        # 1280×720 budget, so that smaller viewport is the binding case).
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_local_map_available(page)
                result = self._inject_panel(page, self._tall_lattice_payload())
                self.assertTrue(result["accepted"], f"ui_update rejected: {result}")
                wait_for_store_state(
                    page,
                    lambda s: (s.get("localMapModel") or {}).get("rows") == 64,
                    timeout=30000,
                )
                wait_for_store_state(
                    page,
                    lambda s: (s.get("localMapModel") or {}).get("cols") == 2,
                    timeout=30000,
                )

            # The canvas is capped by the island's bounded height: the
            # natural 116×2830 SVG scales down to the dynamically measured
            # max-height cap (≤296px + 2px border) — at the smaller viewport
            # the cap can be tighter than 296px, so assert the scaled-down
            # size rather than a fixed lower bound.
            lattice_box = page.locator('[data-testid="local-map__lattice"]').bounding_box()
            self.assertIsNotNone(lattice_box)
            self.assertAlmostEqual(lattice_box["width"], 208.0, delta=1.0)
            self.assertAlmostEqual(lattice_box["height"], 208.0, delta=1.0)
            scale = page.evaluate(
                """() => {
                  const svg = document.querySelector('[data-testid="local-map__lattice"]');
                  return svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
                }"""
            )
            self.assertLess(scale, 1.0)

            # Pre-scale (viewBox) non-intersection: compute every marker/label
            # bounding box in the SVG's root (viewBox) coordinates — the
            # rendered bounding boxes divided by the uniform scale factor — so a
            # scaled-down lattice is checked at its natural geometry, and the
            # uniform scale-down cannot reintroduce a collision.
            geometry = page.evaluate(
                """() => {
              const svg = document.querySelector('[data-testid="local-map__lattice"]');
              const cr = svg.getBoundingClientRect();
              const scale = cr.width / svg.viewBox.baseVal.width;
              // Rendered boxes converted to viewBox user units; stroked
              // circles get the 2px stroke folded back in (visual footprint).
              function toUserUnits(el, includeStroke) {
                const r = el.getBoundingClientRect();
                const box = {
                  x: (r.left - cr.left) / scale,
                  y: (r.top - cr.top) / scale,
                  width: r.width / scale,
                  height: r.height / scale,
                };
                if (includeStroke && el.tagName === 'circle') {
                  box.x -= 1;
                  box.y -= 1;
                  box.width += 2;
                  box.height += 2;
                }
                return box;
              }
              const markers = Array.from(
                  svg.querySelectorAll('.local-map__marker'),
                  (el) => toUserUnits(el, true)
              );
              const labels = Array.from(
                  svg.querySelectorAll('.local-map__node-label'),
                  (el) => toUserUnits(el, false)
              );
              function separated(a, b) {
                return (
                  a.x + a.width <= b.x + 0.5 ||
                  b.x + b.width <= a.x + 0.5 ||
                  a.y + a.height <= b.y + 0.5 ||
                  b.y + b.height <= a.y + 0.5
                );
              }
              let markerMarker = 0, markerLabel = 0, labelLabel = 0;
              for (let i = 0; i < markers.length; i += 1)
                for (let j = i + 1; j < markers.length; j += 1)
                  if (separated(markers[i], markers[j])) markerMarker += 1;
              for (const m of markers)
                for (const l of labels)
                  if (separated(m, l)) markerLabel += 1;
              for (let i = 0; i < labels.length; i += 1)
                for (let j = i + 1; j < labels.length; j += 1)
                  if (separated(labels[i], labels[j])) labelLabel += 1;
              const edgeVisible = Array.from(
                  svg.querySelectorAll('.local-map__edge'),
                  (el) => {
                    const x1 = parseFloat(el.getAttribute('x1'));
                    const y1 = parseFloat(el.getAttribute('y1'));
                    const x2 = parseFloat(el.getAttribute('x2'));
                    const y2 = parseFloat(el.getAttribute('y2'));
                    // Visible segment = center-to-center distance minus the
                    // two 26px marker footprints.
                    return Math.hypot(x2 - x1, y2 - y1) - 26;
                  }
              );
              return {
                markerMarker,
                markerLabel,
                labelLabel,
                markerPairs: markers.length * (markers.length - 1) / 2,
                markerLabelPairs: markers.length * labels.length,
                labelPairs: labels.length * (labels.length - 1) / 2,
                edgeVisible,
              };
            }"""
            )
            self.assertGreater(geometry["markerMarker"], 0)
            self.assertEqual(geometry["markerMarker"], geometry["markerPairs"])
            self.assertEqual(geometry["markerLabel"], geometry["markerLabelPairs"])
            self.assertEqual(geometry["labelLabel"], geometry["labelPairs"])
            for length in geometry["edgeVisible"]:
                self.assertGreater(length, 0, "a connector edge must stay visible outside the marker footprints")

            # The island's required content (meta/title, legend, detail line)
            # stays visible without scrolling: the `map` anchor must not
            # need to scroll a required surface out of view.
            fit = page.evaluate(
                """() => {
              const anchor = document.querySelector('[data-anchor="map"]');
              return {
                anchorScrollHeight: anchor.scrollHeight,
                anchorClientHeight: anchor.clientHeight,
              };
            }"""
            )
            # The +1 absorbs sub-pixel layout rounding: scrollHeight rounds
            # fractional content heights up against an integer clientHeight
            # (the budget formula's own 1px slack covers the same case).
            self.assertLessEqual(
                fit["anchorScrollHeight"], fit["anchorClientHeight"] + 1
            )
            for testid in ("local-map__title", "local-map-detail"):
                self.assertTrue(
                    page.locator(f'[data-testid="{testid}"]').is_visible(),
                    f"{testid} must stay visible without scrolling at {viewport}",
                )
            page.close()

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_long_remembered_list_never_resizes_the_island(self):
        # Task 5.2: adding remembered nodes never resizes the island or its
        # 208x208 canvas, renders no local-map-remembered, and mirrors all entries.
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_local_map_available(page)

                # 1. Base payload without remembered nodes
                self._inject_panel(page, self._tall_lattice_payload(rows=48, remembered_count=0))
                wait_for_store_state(
                    page,
                    lambda s: (s.get("localMapModel") or {}).get("rows") == 48,
                    timeout=30000,
                )
                base_island_box = page.locator('[data-testid="local-map"]').bounding_box()

                # 2. Inject 16 remembered nodes
                result = self._inject_panel(
                    page, self._tall_lattice_payload(rows=48, remembered_count=16)
                )
                self.assertTrue(result["accepted"], f"ui_update rejected: {result}")
                wait_for_store_state(
                    page,
                    lambda s: (s.get("localMapModel") or {}).get("rows") == 48,
                    timeout=30000,
                )

                # - no local-map-remembered
                self.assertEqual(
                    page.locator('[data-testid="local-map-remembered"]').count(),
                    0,
                )
                # - mirror entry count equal to remembered count
                mirror_entries = page.locator('[data-testid="local-map-edge-markers-mirror"] li').count()
                self.assertEqual(mirror_entries, 16)

                # - 208 x 208 canvas
                canvas_box = page.locator('[data-testid="local-map__lattice"]').bounding_box()
                self.assertIsNotNone(canvas_box)
                self.assertAlmostEqual(canvas_box["width"], 208.0, delta=1.0)
                self.assertAlmostEqual(canvas_box["height"], 208.0, delta=1.0)

                # - island box equal to that of the same payload without remembered nodes
                with_rem_island_box = page.locator('[data-testid="local-map"]').bounding_box()
                self.assertAlmostEqual(with_rem_island_box["width"], base_island_box["width"], delta=1.0)
                self.assertAlmostEqual(with_rem_island_box["height"], base_island_box["height"], delta=1.0)

                for testid in ("local-map__title", "local-map-detail"):
                    self.assertTrue(
                        page.locator(f'[data-testid="{testid}"]').is_visible(),
                        f"{testid} must stay visible without scrolling at {viewport}",
                    )
                page.close()

    @covers_requirement(
        "webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone"
    )
    def test_crowded_edge_overlay_marker_names_stay_separated_and_outside_canvas(self):
        """Task 5.1: crowded remembered gateways on overlay edge keep names apart and outside canvas."""
        page = self.logged_in_page()
        self._wait_local_map_available(page)

        # 3x3 in-view lattice with current at (1, 1), plus 4 remembered gateways crowding left edge
        crowded_panel = {
            "schema_version": 1,
            "available": True,
            "layer": "grid",
            "title": "霧骨渡口",
            "current_node": "grid:altoria:1:1",
            "nodes": [
                {"id": "grid:altoria:0:0", "label": "0,0", "x": 0, "y": 0, "visibility": "visible_visited", "current": False, "anchor": False, "landmark": False, "action": None},
                {"id": "grid:altoria:1:0", "label": "1,0", "x": 1, "y": 0, "visibility": "visible_visited", "current": False, "anchor": False, "landmark": False, "action": None},
                {"id": "grid:altoria:2:0", "label": "2,0", "x": 2, "y": 0, "visibility": "visible_visited", "current": False, "anchor": False, "landmark": False, "action": None},
                {"id": "grid:altoria:0:1", "label": "0,1", "x": 0, "y": 1, "visibility": "visible_visited", "current": False, "anchor": False, "landmark": False, "action": None},
                {"id": "grid:altoria:1:1", "label": "1,1", "x": 1, "y": 1, "visibility": "current", "current": True, "anchor": True, "landmark": True, "action": None},
                {"id": "grid:altoria:2:1", "label": "2,1", "x": 2, "y": 1, "visibility": "visible_visited", "current": False, "anchor": False, "landmark": False, "action": None},
                {"id": "grid:altoria:0:2", "label": "0,2", "x": 0, "y": 2, "visibility": "visible_visited", "current": False, "anchor": False, "landmark": False, "action": None},
                {"id": "grid:altoria:1:2", "label": "1,2", "x": 1, "y": 2, "visibility": "visible_visited", "current": False, "anchor": False, "landmark": False, "action": None},
                {"id": "grid:altoria:2:2", "label": "2,2", "x": 2, "y": 2, "visibility": "visible_visited", "current": False, "anchor": False, "landmark": False, "action": None},
                {"id": "grid:altoria:-10:-5", "label": "灰鬮荒原駐軍第一要塞前哨營地", "x": -10, "y": -5, "visibility": "remembered", "current": False, "anchor": False, "landmark": True, "action": None},
                {"id": "grid:altoria:-10:0", "label": "灰鬮荒原駐軍第二要塞前哨營地", "x": -10, "y": 0, "visibility": "remembered", "current": False, "anchor": False, "landmark": True, "action": None},
                {"id": "grid:altoria:-10:2", "label": "灰鬮荒原駐軍第三要塞前哨營地", "x": -10, "y": 2, "visibility": "remembered", "current": False, "anchor": False, "landmark": True, "action": None},
                {"id": "grid:altoria:-10:5", "label": "灰鬮荒原駐軍第四要塞前哨營地", "x": -10, "y": 5, "visibility": "remembered", "current": False, "anchor": False, "landmark": True, "action": None},
            ],
            "edges": [],
            "legend": [
                "你目前所在的位置",
                "尚未探索的相鄰位置",
                "已經探索過的相鄰位置",
                "曾經到過、但不在附近的遠方位置",
            ],
        }
        res = self._inject_panel(page, crowded_panel)
        self.assertTrue(res.get("accepted"), f"ui_update rejected: {res}")

        page.evaluate("window.__elosernBridge.store.openOverlay('map')")
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)
        page.wait_for_selector(
            '[data-testid="map-overlay"] .local-map__edge-marker-name', timeout=15000
        )

        result = page.evaluate(
            """() => {
              const overlay = document.querySelector('[data-testid="map-overlay"]');
              const svg = overlay.querySelector('svg.local-map__lattice');
              // webclient-full-map-fit-view: the surface draws through a
              // fitted viewBox window, so the SVG rect no longer maps the
              // canvas rect. Map the canvas's own user-unit box (its
              // width/height attributes) through the live screen CTM —
              // the same transform every getBoundingClientRect below lives
              // under — instead of pinning any absolute pixel figure.
              const ctm = svg.getScreenCTM();
              const W = Number(svg.getAttribute("width"));
              const H = Number(svg.getAttribute("height"));
              // The node core spans the natural 840 × 650 units at the
              // overlay's declared pitches; the marker gutter is the rest.
              const gutter = (W - 840) / 2;
              const canvasRect = {
                left: ctm.a * gutter + ctm.e,
                right: ctm.a * (W - gutter) + ctm.e,
                top: ctm.d * gutter + ctm.f,
                bottom: ctm.d * (H - gutter) + ctm.f,
              };

              const nameEls = Array.from(svg.querySelectorAll('.local-map__edge-marker-name'));
              const names = nameEls.map((el) => {
                const r = el.getBoundingClientRect();
                return {
                  text: el.textContent,
                  left: r.left,
                  right: r.right,
                  top: r.top,
                  bottom: r.bottom,
                  width: r.width,
                  height: r.height,
                };
              });

              function separated(a, b) {
                return (
                  a.right + 1 <= b.left ||
                  b.right + 1 <= a.left ||
                  a.bottom + 1 <= b.top ||
                  b.bottom + 1 <= a.top
                );
              }

              let overlaps = 0;
              for (let i = 0; i < names.length; i++) {
                for (let j = i + 1; j < names.length; j++) {
                  if (!separated(names[i], names[j])) {
                    overlaps++;
                  }
                }
              }

              let insideCanvasCount = 0;
              for (const n of names) {
                if (n.right > canvasRect.left + 1e-3) {
                  insideCanvasCount++;
                }
              }

              return {
                count: names.length,
                overlaps,
                insideCanvasCount,
                texts: names.map(n => n.text),
              };
            }"""
        )

        self.assertEqual(result["count"], 4)
        self.assertEqual(result["overlaps"], 0)
        self.assertEqual(result["insideCanvasCount"], 0)
        for text in result["texts"]:
            self.assertIn("…", text)
            self.assertEqual(len(text), 11)

        page.close()
