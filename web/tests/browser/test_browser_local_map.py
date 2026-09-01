"""Minimap browser acceptance journeys (map-knowledge-minimap 5.2-5.4).

These journeys boot a dedicated managed server seeded with
``ELOSERN_BROWSER_MINIMAP=1`` so the activated character is relocated to 南門
with map knowledge already recorded (grid, wilderness, interior, and instance
layers). They prove the minimap renders the validated payload, distinguishes
states without color alone, focuses remembered remote nodes without a travel
action, never reveals unknown nodes, rebuilds from server-persisted knowledge
on reconnect, and stays visible and keyboard-operable at both supported
viewports.
"""

from __future__ import annotations

import re
import time

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

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_minimap_renders_and_distinguishes_states_without_color(self):
        page = self.logged_in_page()
        panel = self._wait_local_map_available(page)
        self.assertEqual(panel["layer"], "grid")
        # The shared server character may already stand at an adjacent grid
        # node (an earlier journey submits ``explore.move``), so the current
        # node is asserted position-agnostic: any capital grid node renders.
        self.assertTrue(panel["current_node"].startswith("grid:capital_altoria:"))

        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("local_map", {}).get("available") is True,
            dom_readiness={
                "selector": '[data-testid="local-map__title"]',
                "predicate": "() => !!document.querySelector('[data-testid=\"local-map__title\"]')",
                "description": "local map title rendered",
            },
            timeout=30000,
        )
        # slim-minimap-island (amended requirement): the state legend is an
        # overlay-only presentation — the island mounts no legend element
        # for any payload, and the shape ladder below is what distinguishes
        # states on the island without colour. (The overlay is opened at the
        # END of this test: opening it first would make the island-scoped
        # node assertions below match both surfaces.)
        self.assertEqual(
            page.locator('[data-testid="local-map__legend"]').count(), 0,
            "the island mounts no state legend",
        )

        # The seeded knowledge includes wilderness, interior, and instance
        # visits, so the grid layer carries remembered grid-adjacent nodes and
        # the current node is distinguishable by non-color indicators.
        # H2 re-map: the current node is located through its per-node
        # `data-testid` hook (the `class`-literal selector is retired).
        current_id = panel["current_node"]
        current = page.locator(f'[data-testid="local-map__node--{current_id}"]')
        self.assertEqual(current.count(), 1)
        self.assertEqual(current.get_attribute("data-visibility"), "current")
        self.assertEqual(
            current.locator('[data-testid="local-map__marker--current"]').count(),
            1,
        )
        self.assertTrue(current.is_visible())

        # The full-map overlay keeps the payload's legend, chips paired with
        # their text labels (slim-minimap-island).
        page.evaluate("window.__elosernBridge.store.openOverlay('map')")
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)
        legend_text = page.locator(
            '[data-testid="map-overlay"] [data-testid="local-map__legend"]'
        ).inner_text()
        self.assertIn("你目前所在的位置", legend_text)

    def _repin_at_south_gate(self, page) -> None:
        """Deterministically pin the shared character back at 南門 (2, 0).

        Earlier journeys may have submitted one ``explore.move``, leaving the
        character on another grid node when this journey starts. The seeded
        account is a superuser, so ``teleport`` re-pins the character without
        traversing a costed exit; the panel refresh rides ``at_post_move``.
        """
        self._send(page, "teleport 南門")
        wait_for_store_state(
            page,
            lambda s: (
                ((s.get("panels") or {}).get("local_map") or {}).get("current_node")
                == "grid:capital_altoria:2:0"
            ),
            timeout=15000,
        )

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_remembered_remote_node_focus_shows_name_without_travel_action(self):
        page = self.logged_in_page()
        self._wait_local_map_available(page)
        # The seeded fixture recorded 北門 (2,4), which is outside the visual
        # range from 南門, so the grid layer carries a remembered remote node.
        # H2 re-map: the remembered list items are selected through their
        # `data-visibility` data hook (the preserved `data-node-id` family).
        remembered = page.locator('[data-testid="local-map-remembered"] [data-visibility="remembered"]')
        self.assertGreaterEqual(remembered.count(), 1)
        remembered.first.click()
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="local-map-detail"]',
                "predicate": (
                    "() => { const d = document.querySelector('[data-testid=\"local-map-detail\"]'); "
                    "return (d && d.textContent || '').indexOf('已探索') !== -1; }"
                ),
                "description": "map detail shows the explored state",
            },
            timeout=30000,
        )
        detail = page.locator('[data-testid="local-map-detail"]').inner_text()
        self.assertIn("已探索", detail)
        self.assertIn("北門", detail)
        # No travel control appears for a remembered remote node.
        self.assertEqual(page.locator('[data-testid="local-map-detail"] button').count(), 0)

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_unknown_nodes_never_appear_in_the_dom(self):
        page = self.logged_in_page()
        panel = self._wait_local_map_available(page)
        presented = {node["id"] for node in panel["nodes"]}
        node_count = page.locator('[data-testid="local-map__lattice"] [data-testid^="local-map__node--"]').count()
        self.assertLessEqual(node_count, len(presented))
        # Every rendered node corresponds to a presented node id.
        for index in range(node_count):
            node_id = page.evaluate(
                """(i) => document.querySelectorAll(
                    '[data-testid="local-map__lattice"] [data-testid^="local-map__node--"]'
                )[i].dataset.nodeId""",
                index,
            )
            self.assertIn(node_id, presented)

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    @covers_requirement(
        "webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel"
    )
    def test_gate_room_renders_its_own_approach_cell_and_no_footprint(self):
        # Deterministic start: an earlier journey may have submitted one
        # explore.move, so walk back to 南門 first. Its provisioned gate exit
        # (key 荒野) is the registry gate whose face is "s", so the grid
        # payload carries that gate's OWN approach cell (60, 97) -- never the
        # 北門 gate's approach cell -- and the anchor footprint
        # (x=58..62, y=98..102) never appears as a walkable wild node.
        page = self.logged_in_page()
        self._repin_at_south_gate(page)
        panel = self._wait_local_map_available(page)
        self.assertEqual(panel["layer"], "grid")
        self.assertEqual(panel["current_node"], "grid:capital_altoria:2:0")
        ids = {node["id"] for node in panel["nodes"]}
        self.assertIn("wild:elosern:60:97", ids)
        self.assertNotIn("wild:elosern:60:103", ids)
        footprint = {
            f"wild:elosern:{x}:{y}"
            for x in range(58, 63)
            for y in range(98, 103)
        }
        self.assertEqual(ids & footprint, set())
        # DOM truth follows the payload: the gate node carries its own hook.
        gate_node = page.locator('[data-testid="local-map__node--wild:elosern:60:97"]')
        self.assertEqual(gate_node.count(), 1)

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_reconnect_rebuilds_minimap_from_persisted_knowledge(self):
        page = self.logged_in_page()
        self._wait_local_map_available(page)
        nodes_before = self._local_map_nodes(page)
        self.assertTrue(nodes_before)

        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
            timeout=30000,
        )
        page.evaluate("Evennia.connect()")
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("local_map", {}).get("available") is True,
            timeout=45000,
        )
        nodes_after = self._local_map_nodes(page)
        # No client map cache is authoritative: the rebuilt map carries the
        # same server-persisted current node and knowledge.
        self.assertEqual(
            {node["id"] for node in nodes_after},
            {node["id"] for node in nodes_before},
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
            self.assertLess(lattice_box["width"], 60)
            self.assertLessEqual(lattice_box["height"], 300)

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
                  a.x + a.width + 2 <= b.x ||
                  b.x + b.width + 2 <= a.x ||
                  a.y + a.height + 2 <= b.y ||
                  b.y + b.height + 2 <= a.y
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
            # stays visible without scrolling: the hud-right anchor must not
            # need to scroll a required surface out of view.
            fit = page.evaluate(
                """() => {
              const anchor = document.querySelector('[data-anchor="hud-right"]');
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
    def test_tall_lattice_with_long_remembered_list_stays_within_the_island(self):
        # The blocking combination the crowding fix targets: a tall in-view
        # lattice (2 cols × 48 rows) plus a long remembered list (16 nodes —
        # 48 + 16 = 64 hits the model's MAX_NODES bound). The canvas's
        # dynamically measured max-height must shrink to the space left after
        # the remembered list, so the hud-right anchor never has to scroll a
        # required island surface out of view.
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_local_map_available(page)
                result = self._inject_panel(
                    page, self._tall_lattice_payload(rows=48, remembered_count=16)
                )
                self.assertTrue(result["accepted"], f"ui_update rejected: {result}")
                wait_for_store_state(
                    page,
                    lambda s: (s.get("localMapModel") or {}).get("rows") == 48,
                    timeout=30000,
                )
                # The remembered list renders as a bounded, focusable list
                # outside the coordinate canvas (16 items).
                remembered_items = page.locator('[data-testid="local-map-remembered"] li')
                self.assertEqual(remembered_items.count(), 16)

                # The anchor must not need to scroll: the dynamic canvas cap
                # reserved space for the remembered list.
                fit = page.evaluate(
                    """() => {
                      const anchor = document.querySelector('[data-anchor="hud-right"]');
                      return {
                        scroll: anchor.scrollHeight,
                        client: anchor.clientHeight,
                      };
                    }"""
                )
                # Same sub-pixel rounding tolerance as above: the island
                # budget leaves its own 1px border-box border unreserved
                # (reserving it regresses the >=2px marker/label separation
                # contract), so a <=1px scroll range is the accepted
                # residual; a real overflow fails this bound.
                self.assertLessEqual(fit["scroll"], fit["client"] + 1)
                for testid in ("local-map__title", "local-map-detail", "local-map-remembered"):
                    self.assertTrue(
                        page.locator(f'[data-testid="{testid}"]').is_visible(),
                        f"{testid} must stay visible without scrolling at {viewport}",
                    )
                page.close()

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable"
    )
    @covers_requirement("webclient-local-map::adjacent-traversable-map-nodes-submit-explore-move-through-their-move-descriptor")
    def test_adjacent_traversable_node_submits_explore_move(self):
        page = self.logged_in_page()
        from .browser_helpers import install_outbound_recorder, sent_action_count

        install_outbound_recorder(page)
        self._wait_local_map_available(page)
        action_ready = page.locator('[data-testid="local-map__actionable"]')
        self.assertGreaterEqual(action_ready.count(), 1)
        action_ready.first.click()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "explore.move") >= 1:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "explore.move"
        )
        panel = self._local_map_panel(page)
        self.assertEqual(payload["current_node"], panel["current_node"])
        self.assertTrue(payload["exit_ref"])

    def test_minimap_visible_and_keyboard_usable_at_both_viewports(self):
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_local_map_available(page)
                for selector in (
                    '[data-testid="narrative-feed"]',
                    '[data-testid="status-panel"]',
                    '[data-testid="local-map"]',
                ):
                    self.assertTrue(
                        page.locator(selector).is_visible(),
                        f"{selector} not visible at {viewport}",
                    )
                page.close()


class LayoutVariantsBrowserTest(BrowserAcceptanceTest):
    """Map-02 layout variants: data-derived lattice/radial on both surfaces.

    Reuses the dedicated minimap server (seeded at 南門 with 北門, the guild
    hall interior, a wilderness node, and the ``minimap-cave`` instance).
    These journeys prove the resolved layout follows the committed payload's
    layer on BOTH the island and the full-map overlay, edge markers appear
    only for lattice payloads with remembered places outside the drawn
    extent, the radial graph carries neither orientation marks nor markers,
    no layout control exists anywhere in the map chrome, and no outbound
    envelope is emitted beyond the existing flows.
    """

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

    def _send(self, page, command):
        page.evaluate(
            "(args) => Evennia.msg('text', [args.cmd], {})", {"cmd": command}
        )

    def _wait_local_map(self, page, layer=None, timeout=30000):
        def ready(store):
            panel = (store.get("panels") or {}).get("local_map") or {}
            if panel.get("available") is not True:
                return False
            return layer is None or panel.get("layer") == layer

        wait_for_store_state(page, ready, timeout=timeout)

    def _open_overlay(self, page):
        page.evaluate("window.__elosernBridge.store.openOverlay('map')")
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)

    @staticmethod
    def _surface(page, root_selector):
        """(variant, node positions, marker ids) read from one surface's DOM.

        The variant comes from the rendered DOM itself (the orientation span
        exists only for the lattice variant); node positions are the node
        groups' translate coordinates; marker identities come from the edge
        markers' testid hook, which carries the remembered node id on both
        surfaces (the accessible name only exists at the overlay scale).
        """
        return page.evaluate(
            """(rootSelector) => {
              const root = document.querySelector(rootSelector);
              if (!root) return null;
              const svg = root.querySelector('[data-testid="local-map__lattice"]');
              if (!svg) return null;
              const nodes = {};
              for (const g of svg.querySelectorAll('[data-testid^="local-map__node--"]')) {
                const match = /translate\\(([^,]+),\\s*([^)]+)\\)/.exec(
                  g.getAttribute("transform") || ""
                );
                nodes[g.dataset.nodeId] = match
                  ? { x: parseFloat(match[1]), y: parseFloat(match[2]) }
                  : null;
              }
              const markers = Array.from(
                svg.querySelectorAll('[data-testid^="local-map__edge-marker--"]'),
                (g) => g.getAttribute("data-testid").replace("local-map__edge-marker--", "")
              ).sort();
              return {
                lattice: !!svg,
                // The orientation span lives in the island's header row (the
                // overlay never renders one), so it is looked up under root.
                orientation: !!root.querySelector('[data-testid="local-map__orientation"]'),
                nodes,
                markers,
              };
            }""",
            root_selector,
        )

    @staticmethod
    def _expected_marker_ids(panel):
        """Remembered nodes strictly outside the in-view coordinate bbox."""
        current = next(n for n in panel["nodes"] if n["current"])
        in_view = [n for n in panel["nodes"] if n["visibility"] != "remembered"]
        xs = [n["x"] for n in in_view]
        ys = [n["y"] for n in in_view]
        lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
        ids = []
        for node in panel["nodes"]:
            if node["visibility"] != "remembered":
                continue
            if node["x"] == current["x"] and node["y"] == current["y"]:
                continue
            if not (lo_x <= node["x"] <= hi_x and lo_y <= node["y"] <= hi_y):
                ids.append(node["id"])
        return sorted(ids)

    @staticmethod
    def _interior_panel():
        """A minimal interior room-graph payload for the live-swap journey."""
        nodes = [
            {
                "id": "room:guild-hall",
                "label": "公會大廳",
                "x": 0,
                "y": 0,
                "visibility": "current",
                "current": True,
                "anchor": True,
                "landmark": True,
                "action": None,
            },
            {
                "id": "room:vault",
                "label": "金庫",
                "x": 1,
                "y": 0,
                "visibility": "visible_visited",
                "current": False,
                "anchor": False,
                "landmark": False,
                "action": None,
            },
        ]
        return {
            "schema_version": 1,
            "available": True,
            "layer": "interior",
            "current_node": "room:guild-hall",
            "title": "公會大廳",
            "nodes": nodes,
            "edges": [
                {
                    "source": "room:guild-hall",
                    "destination": "room:vault",
                    "label": "側門",
                    "known": True,
                    "traversable": True,
                }
            ],
            "legend": ["你目前所在的位置", "尚未探索的相鄰位置", "已經探索過的相鄰位置"],
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
    @covers_requirement(
        "webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention"
    )
    def test_layout_follows_payload_layer_without_any_control(self):
        # Grid layer (seeded 南門): BOTH surfaces resolve to the lattice —
        # orientation marks on the island, edge markers for the remembered
        # 北門 outside the drawn extent, and no layout control anywhere.
        page = self.logged_in_page()
        from .browser_helpers import install_outbound_recorder, sent_action_count

        install_outbound_recorder(page)
        self._wait_local_map(page, layer="grid")
        panel = store_state(page)["panels"]["local_map"]
        island = self._surface(page, '[data-testid="local-map"]')
        self.assertIsNotNone(island)
        self.assertTrue(island["orientation"], "the lattice island renders orientation marks")
        expected = self._expected_marker_ids(panel)
        self.assertGreaterEqual(len(expected), 1, "fixture must carry an off-extent remembered node")
        self.assertEqual(island["markers"], expected)

        # slim-minimap-island (amended contextual-hud requirement): the
        # island's position statement is the header's axis marks PLUS the
        # current node's own two payload integers on the detail line —
        # exactly as committed. Selecting the current node deterministically
        # (its action is null, so activation sends nothing outbound) removes
        # any drift from an earlier journey moving the shared character.
        current = next(node for node in panel["nodes"] if node["current"])
        # Click the current node's marker itself: the node GROUP's bounding
        # box centre falls in the transparent gap between the marker and the
        # label, so a group click hit-tests nothing (the current node has no
        # actionable halo). The marker's action is null, so activation still
        # sends nothing outbound.
        page.locator(
            '[data-testid="local-map"]'
            f' [data-testid="local-map__node--{panel["current_node"]}"]'
            ' [data-testid="local-map__marker--current"]'
        ).first.click()
        expected_figure = f"座標 {current['x']},{current['y']}"
        page.wait_for_function(
            """(figure) => {
              const detail = document.querySelector('[data-testid="local-map-detail"]');
              return !!detail && detail.textContent.includes(figure);
            }""",
            arg=expected_figure,
        )
        detail_text = page.locator('[data-testid="local-map-detail"]').inner_text()
        self.assertIn(expected_figure, detail_text)
        self.assertEqual(
            len(re.findall(r"座標\s*-?\d+,-?\d+", detail_text)), 1,
            "the current node's own pair is the only coordinate figure",
        )

        # The full-map overlay shares the resolved variant and marker set.
        self._open_overlay(page)
        overlay = self._surface(page, '[data-testid="map-overlay"]')
        self.assertIsNotNone(overlay)
        self.assertTrue(overlay["lattice"])
        self.assertEqual(overlay["markers"], expected)
        # The overlay states no coordinate figure anywhere (island-only).
        self.assertNotIn(
            "座標",
            page.locator('[data-testid="map-overlay"]').inner_text(),
        )

        # Interior payload (committed without movement): BOTH surfaces
        # live-swap to the radial graph — no orientation marks, no markers,
        # and every node group's translate equals the model's scaled radial
        # placement.
        result = self._inject_panel(page, self._interior_panel())
        self.assertTrue(result["accepted"], f"ui_update rejected: {result}")
        wait_for_store_state(
            page,
            lambda s: (s.get("localMapModel") or {}).get("layoutVariant") == "graph",
            timeout=30000,
        )
        # Both surfaces must re-render from the swapped payload before the
        # DOM read below (the store flips first; Vue commits on next tick).
        wait_for_store_state(
            page,
            lambda s: (s.get("localMapModel") or {}).get("layoutVariant") == "graph",
            dom_readiness={
                "selector": '[data-testid="map-overlay"] [data-testid^="local-map__node--room"]',
                "predicate": (
                    "() => document.querySelectorAll("
                    "'[data-testid=\"map-overlay\"] [data-testid^=\"local-map__node--room\"]')"
                    ".length === 2 && document.querySelectorAll("
                    "'[data-testid=\"local-map\"] [data-testid^=\"local-map__node--room\"]')"
                    ".length === 2"
                ),
                "description": "both surfaces re-rendered from the interior payload",
            },
            timeout=30000,
        )
        radial = store_state(page)["localMapModel"]["radial"]
        island = self._surface(page, '[data-testid="local-map"]')
        overlay = self._surface(page, '[data-testid="map-overlay"]')
        # The island renders the radial at markerScale 1 (the prop default) and
        # the overlay at its shipped 4.83 ladder; node groups translate by the
        # scaled placement, and the viewBox spans the same scaled canvas, so
        # the comparison is exact per surface.
        placed = {node["id"]: node for node in radial["nodes"]}
        for name, surface, scale in (("island", island, 1.0), ("overlay", overlay, 4.83)):
            self.assertEqual(
                set(placed), set(surface["nodes"]),
                f"{name}: the surface draws exactly the radial-placed nodes",
            )
            for node_id, position in surface["nodes"].items():
                self.assertAlmostEqual(
                    position["x"], placed[node_id]["x"] * scale, places=1,
                    msg=f"{name} {node_id}: translate matches scaled radial placement",
                )
                self.assertAlmostEqual(
                    position["y"], placed[node_id]["y"] * scale, places=1,
                    msg=f"{name} {node_id}: translate matches scaled radial placement",
                )

        # The coordinate-free interior payload renders neither the axis
        # marks nor a coordinate figure (slim-minimap-island): the island
        # header drops the marks and the detail line loses the figure.
        self.assertFalse(island["orientation"], "the graph island omits the axis marks")
        island_detail = page.locator('[data-testid="local-map-detail"]').inner_text()
        self.assertNotIn("座標", island_detail)

        # Absence: neither surface's chrome contains a layout-control element.
        # Scan BOTH map surfaces' interactive controls (button/input/select/
        # role=button) for any layout/variant wording in text, accessible
        # name, testid, or class — the withdrawn switch must leave no residue
        # under any markup, not just the testid/`.seg` shapes it shipped as.
        controls = page.evaluate(
            """() => {
              const surfaces = document.querySelectorAll(
                '[data-testid="local-map"], [data-testid="map-overlay"]');
              const offenders = [];
              for (const surface of surfaces) {
                for (const el of surface.querySelectorAll(
                  'button, input, select, textarea, [role="button"], [role="radio"], '
                  + '[role="checkbox"], [role="switch"], [role="combobox"], a[href]')) {
                  const haystack = [
                    el.getAttribute('data-testid') || '',
                    el.getAttribute('aria-label') || '',
                    (el.getAttribute('class') || ''),
                    (el.textContent || '').trim(),
                  ].join(' ');
                  if (/layout|variant|版面/i.test(haystack)) offenders.push(haystack);
                }
                for (const el of surface.querySelectorAll('[data-testid], [class]')) {
                  const id = (el.getAttribute('data-testid') || '') + ' '
                    + (el.getAttribute('class') || '');
                  if (/layout|variant/i.test(id)) offenders.push(id);
                }
              }
              return offenders;
            }"""
        )
        self.assertEqual(controls, [], "the map chrome exposes no layout control")

        # No outbound envelope beyond the existing flows: none of these
        # commits is a player action.
        self.assertEqual(sent_action_count(page), 0)
        page.close()

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    @covers_requirement("webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention")
    @covers_requirement(
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully"
    )
    def test_walked_instance_layer_renders_radial_on_both_surfaces(self):
        # A REAL movement (the seeded 進洞窟 exit) commits an instance payload;
        # both surfaces must render the radial graph truthfully from the
        # committed data — no orientation marks, no edge markers, node
        # positions equal to the model's scaled radial placement.
        page = self.logged_in_page()
        from .browser_helpers import install_outbound_recorder, sent_action_count

        install_outbound_recorder(page)
        self._wait_local_map(page, layer="grid")
        self._send(page, "進洞窟")
        self._wait_local_map(page, layer="instance", timeout=45000)
        wait_for_store_state(
            page,
            lambda s: (s.get("localMapModel") or {}).get("layoutVariant") == "graph",
            timeout=30000,
        )
        self._open_overlay(page)
        model = store_state(page)["localMapModel"]
        self.assertEqual(model["layoutVariant"], "graph")
        island = self._surface(page, '[data-testid="local-map"]')
        overlay = self._surface(page, '[data-testid="map-overlay"]')
        for name, surface in (("island", island), ("overlay", overlay)):
            self.assertTrue(surface["lattice"], f"{name}: the canvas is mounted")
            self.assertFalse(
                surface["orientation"], f"{name}: the coordinate-free layer omits orientation marks"
            )
            self.assertEqual(surface["markers"], [], f"{name}: the graph variant never marks")
        # The island renders the radial at markerScale 1 (the prop default) and
        # the overlay at its shipped 4.83 ladder; the viewBox spans the same
        # scaled canvas, so the translate comparison is exact per surface.
        placed = {node["id"]: node for node in model["radial"]["nodes"]}
        for name, surface, scale in (("island", island, 1.0), ("overlay", overlay, 4.83)):
            self.assertEqual(
                set(placed), set(surface["nodes"]),
                f"{name}: the surface draws exactly the radial-placed nodes",
            )
            for node_id, position in surface["nodes"].items():
                self.assertAlmostEqual(
                    position["x"], placed[node_id]["x"] * scale, places=1,
                    msg=f"{name} {node_id}: translate matches scaled radial placement",
                )
                self.assertAlmostEqual(
                    position["y"], placed[node_id]["y"] * scale, places=1,
                    msg=f"{name} {node_id}: translate matches scaled radial placement",
                )
        # The walk itself is the only movement; no layout/variant flow emits
        # an outbound ui_action.
        self.assertEqual(sent_action_count(page), 0)
        page.close()


if __name__ == "__main__":
    import unittest

    unittest.main()
