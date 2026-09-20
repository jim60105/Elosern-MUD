"""Local-map layout-variant acceptance: the island and full-map surfaces follow the payload layer without any control.
"""

from __future__ import annotations

import re
from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import store_state, wait_for_store_state


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
        # the overlay at its shipped 2.2 ladder
        # (MapOverlay.vue :marker-scale="2.2", re-pointed from the draft's 4.83
        # by the desktop redesign 0522f09); node groups translate by the
        # scaled placement, and the viewBox spans the same scaled canvas, so
        # the comparison is exact per surface.
        placed = {node["id"]: node for node in radial["nodes"]}
        for name, surface, scale in (("island", island, 1.0), ("overlay", overlay, 2.2)):
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
        # the overlay at its shipped 2.2 ladder
        # (MapOverlay.vue :marker-scale="2.2", re-pointed from the draft's 4.83
        # by the desktop redesign 0522f09); the viewBox spans the same
        # scaled canvas, so the translate comparison is exact per surface.
        placed = {node["id"]: node for node in model["radial"]["nodes"]}
        for name, surface, scale in (("island", island, 1.0), ("overlay", overlay, 2.2)):
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
