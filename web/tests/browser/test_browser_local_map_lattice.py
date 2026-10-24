"""Local-map browser acceptance: dense/tall lattice scaling within the island height budget and metric transport into the island.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest, ui_scale
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
                    "gateway": None,
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
                    "gateway": None,
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

    @covers_requirement(
        "webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure",
        "webclient-vue-application::the-monospace-type-role-is-a-self-hosted-sliced-jim-mono-tc-face",
    )
    def test_densely_populated_lattice_scales_down_without_reintroducing_overlap(self):
        # A densely populated lattice (2 cols × 64 rows) must scale the
        # canvas down to fit the island's 240px square — pre-scale
        # geometry satisfies the non-overlap invariant, and the scaled-down
        # render keeps markers and labels non-intersecting. Verified at
        # both acceptance viewports (the reference's 240px square is the
        # binding case; the capped viewport only magnifies the same drawing).
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_local_map_available(page)
                payload = self._tall_lattice_payload()
                result = self._inject_panel(page, payload)
                self.assertTrue(result["accepted"], f"ui_update rejected: {result}")
                # The committed model carries the payload's own in-view nodes
                # at their raw coordinates (the lattice cell left with the
                # full-map overlay), so the gate is the node count plus the
                # payload's own current node.
                wait_for_store_state(
                    page,
                    lambda s: len((s.get("localMapModel") or {}).get("nodes") or []) == 64,
                    timeout=30000,
                )
                wait_for_store_state(
                    page,
                    lambda s: (s.get("localMapModel") or {}).get("currentNode")
                    == payload["current_node"],
                    timeout=30000,
                )

            # The canvas is the island's fixed 240px square (scaled once by
            # the chrome factor): the tall lattice cannot fit it, so the
            # island shows the drawing through its 0.75-floor window, and the
            # drawing itself is never magnified past the square's own scale.
            lattice_box = page.locator('[data-testid="local-map__lattice"]').bounding_box()
            self.assertIsNotNone(lattice_box)
            canvas_side = 240.0 * ui_scale(viewport)
            self.assertAlmostEqual(lattice_box["width"], canvas_side, delta=1.0)
            self.assertAlmostEqual(lattice_box["height"], canvas_side, delta=1.0)
            scale = page.evaluate(
                """() => {
                  const svg = document.querySelector('[data-testid="local-map__lattice"]');
                  return svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
                }"""
            )
            self.assertLessEqual(
                scale,
                ui_scale(viewport) + 1e-6,
                "the drawing is never magnified past the island's own scale",
            )

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

    @covers_requirement("webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure")
    def test_long_remembered_list_never_resizes_the_island(self):
        # Task 5.2: adding remembered nodes never resizes the island or its
        # 240x240 canvas, renders no local-map-remembered, and mirrors all entries.
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_local_map_available(page)

                # 1. Base payload without remembered nodes
                self._inject_panel(page, self._tall_lattice_payload(rows=48, remembered_count=0))
                wait_for_store_state(
                    page,
                    lambda s: len((s.get("localMapModel") or {}).get("nodes") or []) == 48,
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
                    # Remembered far nodes stay out of the in-view model.
                    lambda s: len((s.get("localMapModel") or {}).get("nodes") or []) == 48,
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

                # - 240 x 240 canvas (scaled once by the chrome factor)
                canvas_box = page.locator('[data-testid="local-map__lattice"]').bounding_box()
                self.assertIsNotNone(canvas_box)
                canvas_side = 240.0 * ui_scale(viewport)
                self.assertAlmostEqual(canvas_box["width"], canvas_side, delta=1.0)
                self.assertAlmostEqual(canvas_box["height"], canvas_side, delta=1.0)

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
        "webclient-local-map::metric-coordinates-survive-authoritative-transport-and-uniform-projection"
    )
    @covers_requirement(
        "webclient-local-map::minimap-adjacent-movement-remains-bound-to-authoritative-descriptors"
    )
    def test_metric_projection_keeps_gap_ratio_and_actions(self):
        """Metric coordinates survive transport; the island keeps its
        exit-driven automatic projection and exact action identity.

        Injects the requirement's own frame — (0,0), (100,0), (1000,0),
        (1000,6500) plus a (100,100) diagonal control and an east-remembered
        landmark — and checks the real surfaces: the island centres the
        current node and scales by its two labelled exits (level 200: the
        100 m exit at 50 units, the diagonal on its exact bearing) while the
        far context it cannot fit is omitted, and the adjacent node keeps its
        exact move identity.
        """
        from .browser_helpers import install_outbound_recorder, sent_action_count

        metric_panel = {
            "schema_version": 1,
            "available": True,
            "layer": "grid",
            "title": "度量城區",
            "current_node": "grid:metric:0:0",
            "nodes": [
                {"id": "grid:metric:0:0", "label": "原點", "x": 0, "y": 0, "visibility": "current", "current": True, "anchor": False, "landmark": False, "gateway": None, "action": None},
                {"id": "grid:metric:100:0", "label": "東街", "x": 100, "y": 0, "visibility": "visible_unvisited", "current": False, "anchor": False, "landmark": False, "gateway": None, "action": {"kind": "move", "exit_ref": "e", "destination": "grid:metric:100:0"}},
                {"id": "grid:metric:1000:0", "label": "遠東", "x": 1000, "y": 0, "visibility": "visible_unvisited", "current": False, "anchor": False, "landmark": False, "gateway": None, "action": None},
                {"id": "grid:metric:1000:6500", "label": "北關", "x": 1000, "y": 6500, "visibility": "visible_unvisited", "current": False, "anchor": False, "landmark": False, "gateway": None, "action": None},
                {"id": "grid:metric:100:100", "label": "東北", "x": 100, "y": 100, "visibility": "visible_visited", "current": False, "anchor": False, "landmark": False, "gateway": None, "action": None},
                {"id": "grid:metric:7000:-100", "label": "東境關隘", "x": 7000, "y": -100, "visibility": "remembered", "current": False, "anchor": False, "landmark": True, "gateway": None, "action": None},
                {"id": "grid:metric:6500:6350", "label": "度量北坊", "x": 6500, "y": 6350, "visibility": "visible_unvisited", "current": False, "anchor": False, "landmark": False, "gateway": None, "action": None},
            ],
            "edges": [
                {"source": "grid:metric:0:0", "destination": "grid:metric:100:0", "label": "e", "known": True, "traversable": True},
                {"source": "grid:metric:100:0", "destination": "grid:metric:1000:0", "label": "e", "known": True, "traversable": True},
                {"source": "grid:metric:1000:0", "destination": "grid:metric:1000:6500", "label": "n", "known": True, "traversable": True},
                {"source": "grid:metric:0:0", "destination": "grid:metric:100:100", "label": "ne", "known": True, "traversable": False},
            ],
            "legend": [
                "你目前所在的位置",
                "尚未探索的相鄰位置",
                "已經探索過的相鄰位置",
                "記憶中的邊界",
            ],
        }

        page = self.logged_in_page()
        self._wait_local_map_available(page)
        install_outbound_recorder(page)
        self._inject_panel(page, metric_panel)
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("local_map", {}).get("current_node")
            == "grid:metric:0:0",
            timeout=30000,
        )

        # 1. Transport: the accepted payload keeps every committed coordinate.
        committed = {
            node["id"]: (node["x"], node["y"]) for node in self._local_map_panel(page)["nodes"]
        }
        self.assertEqual(
            committed,
            {
                "grid:metric:0:0": (0, 0),
                "grid:metric:100:0": (100, 0),
                "grid:metric:1000:0": (1000, 0),
                "grid:metric:1000:6500": (1000, 6500),
                "grid:metric:100:100": (100, 100),
                "grid:metric:7000:-100": (7000, -100),
                "grid:metric:6500:6350": (6500, 6350),
            },
        )

        def centers(scope):
            return page.evaluate(
                """(scope) => {
                  const read = (id) => {
                    const el = document.querySelector(
                      `${scope} [data-testid="local-map__node--${id}"]`
                    );
                    if (!el) return null;
                    const m = el.getAttribute("transform").match(/-?[\\d.]+/g);
                    return { x: Number(m[0]), y: Number(m[1]) };
                  };
                  return {
                    origin: read("grid:metric:0:0"),
                    near: read("grid:metric:100:0"),
                    far: read("grid:metric:1000:0"),
                    north: read("grid:metric:1000:6500"),
                    diagonal: read("grid:metric:100:100"),
                  };
                }""",
                scope,
            )

        # 2. The island projects by its labelled exits (render-auto-scaled-
        #    minimap-island): current centred, 100 m east at 50 units (level
        #    200), the 141 m diagonal on its exact 45-degree bearing, and the
        #    1 km / 6.5 km places it cannot fit omitted from the island only.
        island = centers('[data-testid="local-map"]')
        self.assertEqual(island["origin"], {"x": 120, "y": 120})
        self.assertAlmostEqual(island["near"]["x"] - island["origin"]["x"], 50, places=3)
        self.assertAlmostEqual(island["near"]["y"], island["origin"]["y"], places=3)
        self.assertAlmostEqual(
            island["origin"]["y"] - island["diagonal"]["y"],
            island["diagonal"]["x"] - island["origin"]["x"],
            places=3,
            msg="the diagonal exit keeps its exact bearing",
        )
        self.assertIsNone(island["far"])
        self.assertIsNone(island["north"])
        self.assertEqual(
            page.locator('[data-testid="local-map__scale"]').inner_text().strip(), "格距 40 m"
        )

        # 3. A remembered place keeps its physical bearing on the island.
        mirror_text = page.locator(
            '[data-testid="local-map-edge-markers-mirror"]'
        ).inner_text()
        self.assertIn("東境關隘", mirror_text)
        self.assertIn("東", mirror_text)

        # 4. The adjacent node keeps its exact move identity on the island.
        #    (The full map is the drawer's area view, whose metric geometry
        #    is pinned by the drawer and area-view suites.)
        #    The group's box spans its marker and its placed label, and the
        #    shared node glyph paints its travel halo beneath the state glyph
        #    (the label is pointer-inert), so the topmost paint at the node's
        #    centre is its marker: the journey clicks that marker — the
        #    element a real pointer lands on, inside the same activating
        #    group.
        page.locator(
            '[data-testid="local-map"] [data-testid="local-map__node--grid:metric:100:0"] .local-map__marker'
        ).click()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "explore.move") >= 1:
                break
            page.wait_for_timeout(250)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "explore.move"
        )
        self.assertEqual(payload["exit_ref"], "e")
        self.assertEqual(payload["current_node"], "grid:metric:0:0")

        # 6. The wilderness frame's expanded bound renders too: a (2699,2699)
        #    payload commits through the real client validator and draws.
        wilderness_panel = {
            "schema_version": 1,
            "available": True,
            "layer": "wilderness",
            "title": "東境荒野",
            "current_node": "wild:elosern:2699:2699",
            "nodes": [
                {"id": "wild:elosern:2699:2699", "label": "東境荒野", "x": 2699, "y": 2699, "visibility": "current", "current": True, "anchor": False, "landmark": False, "gateway": None, "action": None},
                {"id": "wild:elosern:2698:2699", "label": "林地", "x": 2698, "y": 2699, "visibility": "visible_unvisited", "current": False, "anchor": False, "landmark": False, "gateway": None, "action": {"kind": "move", "exit_ref": "w", "destination": "wild:elosern:2698:2699"}},
            ],
            "edges": [
                {"source": "wild:elosern:2699:2699", "destination": "wild:elosern:2698:2699", "label": "w", "known": True, "traversable": True},
            ],
            "legend": ["你目前所在的位置", "尚未探索的相鄰位置"],
        }
        self._inject_panel(page, wilderness_panel)
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("local_map", {}).get("current_node")
            == "wild:elosern:2699:2699",
            timeout=30000,
        )
        corner = page.evaluate(
            """() => {
              const el = document.querySelector(
                '[data-testid="local-map"] [data-testid="local-map__node--wild:elosern:2699:2699"]'
              );
              const m = el.getAttribute("transform").match(/-?[\\d.]+/g);
              return { x: Number(m[0]), y: Number(m[1]) };
            }"""
        )
        self.assertTrue(all(isinstance(value, (int, float)) for value in corner.values()))
        page.close()
