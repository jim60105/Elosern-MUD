"""Local-map browser acceptance: the minimap island renders committed knowledge truthfully across states, remembered remote nodes, gate rooms, and reconnect.
"""

from __future__ import annotations

import re
from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    fixture_home_node_id,
    fixture_home_xyz_arg,
    store_state,
    wait_for_store_state,
)


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

    def _repin_at_home(self, page) -> None:
        """Deterministically pin the shared character back at the fixture's
        home grid room — the city-gate anchor the minimap fixture starts its
        knowledge walk from, resolved from the live registry module rather
        than a coordinate literal.

        Earlier journeys may have submitted one ``explore.move``, leaving the
        character on another grid node when this journey starts. The seeded
        account is a superuser, so the XYZ-grid ``teleport`` re-pins the
        character without traversing a costed exit; the panel refresh rides
        ``at_post_move``. The coordinate form is used instead of a room name:
        the coordinate comes from the shared registry-module helper (a pure
        module-constant read; the kit row borrows the same cell in synthetic
        mode), and no ORM query happens in the journey process (the server
        owns the boot-mode catalogs).
        """
        self._send(page, f"teleport {fixture_home_xyz_arg()}")
        wait_for_store_state(
            page,
            lambda s: (
                ((s.get("panels") or {}).get("local_map") or {}).get("current_node")
                == fixture_home_node_id()
            ),
            timeout=15000,
        )

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_remembered_remote_node_presentation_and_accessibility(self):
        page = self.logged_in_page()
        # Deterministic start: earlier journeys may have moved the shared
        # character onto a node whose field of view covers the fixture's
        # remembered gateway (which would present it as an in-range node,
        # not an edge marker). Re-pin at the fixture's home room, whose
        # view never covers the recorded gateway in either boot mode.
        self._repin_at_home(page)
        self._wait_local_map_available(page)
        # On the lattice variant (grid/wilderness), remembered places render as
        # named edge markers and no remembered list is rendered beneath the map.
        self.assertEqual(
            page.locator('[data-testid="local-map-remembered"]').count(),
            0,
            "lattice variant renders no remembered list",
        )
        edge_markers = page.locator('[data-testid^="local-map__edge-marker--"]')
        self.assertGreaterEqual(edge_markers.count(), 1)
        # local-map-remembered-are-map-gateways: the remembered gate's marker
        # is named for the place its traversal reaches (the far-side
        # wilderness region), not the gate room's own name. Which gateway the
        # fixture recorded is the boot mode's business — the journey reads the
        # presented panel for the remembered gateway's identity and name.
        remembered = [
            node for node in self._local_map_nodes(page)
            if node["visibility"] == "remembered"
        ]
        self.assertEqual(len(remembered), 1, "the fixture records exactly one gateway")
        gateway = remembered[0]
        gateway_marker = page.locator(
            f'[data-testid="local-map__edge-marker--{gateway["id"]}"]'
        )
        self.assertEqual(gateway_marker.count(), 1)
        marker_name = gateway_marker.locator("title").evaluate("el => el.textContent")
        self.assertIn(gateway["label"], marker_name)
        # Assistive technology mirror is present
        mirror = page.locator('[data-testid="local-map-edge-markers-mirror"]')
        self.assertEqual(mirror.count(), 1)

        # Exactly one tab stop on the island
        tab_stops = page.evaluate(
            "() => document.querySelectorAll('.local-map button, .local-map a, .local-map [tabindex]:not([tabindex=\"-1\"])').length"
        )
        self.assertEqual(tab_stops, 1)

        # On the graph variant (interior), the remembered list is present
        interior_payload = {
            "schema_version": 1,
            "available": True,
            "layer": "interior",
            "current_node": "room:201",
            "title": "公會大廳",
            "nodes": [
                {
                    "id": "room:201",
                    "label": "公會大廳",
                    "x": 0,
                    "y": 0,
                    "visibility": "current",
                    "current": True,
                    "anchor": False,
                    "landmark": False,
                    "action": None,
                },
                {
                    "id": "room:202",
                    "label": "訓練場",
                    "x": 1,
                    "y": 0,
                    "visibility": "visible_visited",
                    "current": False,
                    "anchor": False,
                    "landmark": False,
                    "action": {"kind": "move", "exit_ref": "e_hall_training", "destination": "room:202"},
                },
                {
                    "id": "room:203",
                    "label": "地下金庫",
                    "x": 0,
                    "y": 1,
                    "visibility": "remembered",
                    "current": False,
                    "anchor": False,
                    "landmark": False,
                    "action": None,
                },
            ],
            "edges": [
                {"source": "room:201", "destination": "room:202", "label": "訓練場", "known": True, "traversable": True},
            ],
            "legend": ["你目前所在的位置", "已經探索過的相鄰位置", "曾經到過、但不在附近的遠方位置"],
        }
        self._inject_panel(page, interior_payload)
        page.wait_for_selector('[data-testid="local-map-remembered"]', timeout=15000)
        self.assertEqual(page.locator('[data-testid="local-map-remembered"]').count(), 1)
        self.assertEqual(page.locator('[data-testid="local-map-edge-markers-mirror"]').count(), 0)

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
        # Deterministic start: re-pin at the fixture's home room, then stand
        # on the remembered gateway's own grid room — the boot mode's
        # registry gate (kit gate room under synth, the shipped install's
        # south-gate entry otherwise), whose identity is read from the
        # presented payload rather than from shipped coordinates. There, the
        # provisioned gate exit renders its OWN approach cell as a
        # traversable wild node — never another registered gate's — and no
        # anchor-footprint cell ever appears as a walkable wild node.
        from world.maps.wilderness_provider import WILDERNESS_NAME

        page = self.logged_in_page()
        self._repin_at_home(page)
        panel = self._wait_local_map_available(page)
        remembered = [
            node for node in panel["nodes"] if node["visibility"] == "remembered"
        ]
        self.assertEqual(len(remembered), 1, "the fixture records exactly one gateway")
        gate_room = remembered[0]
        self.assertTrue(gate_room["id"].startswith("grid:"))
        z_map = gate_room["id"].split(":")[1]
        self._send(page, f"teleport ({gate_room['x']}, {gate_room['y']}, {z_map})")
        wait_for_store_state(
            page,
            lambda s: (
                ((s.get("panels") or {}).get("local_map") or {}).get("current_node")
                == gate_room["id"]
            ),
            timeout=20000,
        )
        panel = self._wait_local_map_available(page)
        self.assertEqual(panel["layer"], "grid")
        self.assertEqual(panel["current_node"], gate_room["id"])
        # The gate's own approach cell is presented as a wild node whose
        # traversal action targets it (the both-directions contract's grid
        # side: the node the presented action lands on is the approach cell).
        gate_nodes = [
            node
            for node in panel["nodes"]
            if node["id"].startswith(f"wild:{WILDERNESS_NAME}:")
        ]
        self.assertEqual(len(gate_nodes), 1, "exactly this room's registered gate renders")
        gate = gate_nodes[0]
        self.assertIsNotNone(gate["action"], "the seeded character may traverse the gate")
        self.assertEqual(gate["action"]["destination"], gate["id"])
        # No anchor-footprint cell ever renders as a walkable wild node at
        # the grid layer: the footprint is walkable wilderness ground, so it
        # only ever appears once traversed (layer wilderness), never as a
        # grid-layer candidate.
        grid_layer_wild = [
            node["id"] for node in panel["nodes"] if node["id"].startswith("wild:")
        ]
        self.assertEqual(grid_layer_wild, [gate["id"]])
        # DOM truth follows the payload: the gate node carries its own hook.
        gate_node = page.locator(f'[data-testid="local-map__node--{gate["id"]}"]')
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
