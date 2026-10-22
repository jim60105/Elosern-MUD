from tools.spec_traceability import covers_requirement
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from unittest.mock import patch
from typeclasses.rooms import GridRoom, InstanceRoom, Room
from web.webclient.presentation.registry import PanelUnavailableError, build_production_registry
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.rules.map_knowledge import record_arrival

from ._support import (
    EAST_APPROACH,
    EAST_GATE_XYZ,
    SOUTH_APPROACH,
    SOUTH_GATE_XYZ,
    _T_MAP_KEY,
    _T_PLAZA_XYZ,
    _context,
    _inserted_multiple,
    _live,
    _payload_cell_divisor,
    _t_anchor_display,
    _t_grid_id,
    _t_region_display_for,
)


class LocalMapGridGatewayTests(EvenniaTest):
    """Remembered grid nodes are stood-on map gateways (wave 4, and 1.4's
    distinctness qualifier)."""

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.plaza = GridRoom.objects.filter_xyz(xyz=_T_PLAZA_XYZ).first()

    def _registry(self):
        return build_production_registry()

    @patch("web.webclient.presentation.local_map.grid._grid_nodes_in_range", return_value=[])
    def test_a_stood_on_gate_room_out_of_range_is_remembered(self, _mock_range):
        self.char1.location = self.east_gate
        record_arrival(self.char1)
        self.char1.location = self.south_gate
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "grid")
        remembered = [node for node in payload["nodes"] if node["visibility"] == "remembered"]
        self.assertEqual(len(remembered), 1)
        node = remembered[0]
        self.assertEqual(node["id"], _t_grid_id(*EAST_GATE_XYZ[:2]))
        self.assertEqual((node["x"], node["y"]), EAST_GATE_XYZ[:2])
        self.assertEqual(node["label"], _t_region_display_for(*EAST_APPROACH))
        self.assertTrue(node["landmark"])
        self.assertFalse(node["anchor"])
        self.assertIsNone(node["action"])
        # The remembered gate room still hosts its registered gateway.
        self.assertEqual(node["gateway"], {"leads_to": _t_region_display_for(*EAST_APPROACH)})
        # The current south gate room names its own far side.
        current = next(node for node in payload["nodes"] if node["current"])
        self.assertEqual(current["gateway"], {"leads_to": _t_region_display_for(*SOUTH_APPROACH)})

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_an_in_view_gate_room_names_its_far_side_and_ordinary_rooms_carry_null(self):
        # Stand on an ordinary street one step from the south gate: the gate
        # room drawn in view carries its far-side region, every other grid
        # room (not a registered gate room) carries null.
        self.char1.location = self.south_gate
        record_arrival(self.char1)
        at_gate = self._registry().render("local_map", _context(self.char1))
        gate_ids = {
            _t_grid_id(*SOUTH_GATE_XYZ[:2]): _t_region_display_for(*SOUTH_APPROACH),
            _t_grid_id(*EAST_GATE_XYZ[:2]): _t_region_display_for(*EAST_APPROACH),
        }
        neighbour = next(
            node
            for node in at_gate["nodes"]
            if node["action"] is not None
            and node["id"].startswith("grid:")
            and node["id"] not in gate_ids
        )
        self.char1.location = GridRoom.objects.filter_xyz(
            xyz=(neighbour["x"], neighbour["y"], _T_MAP_KEY)
        ).first()
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "grid")
        south = next(node for node in payload["nodes"] if node["id"] == _t_grid_id(*SOUTH_GATE_XYZ[:2]))
        self.assertEqual(south["visibility"], "visible_visited")
        self.assertEqual(south["gateway"], {"leads_to": gate_ids[south["id"]]})
        ordinary = [
            node
            for node in payload["nodes"]
            if node["id"].startswith("grid:") and node["id"] not in gate_ids
        ]
        self.assertTrue(ordinary)
        for node in ordinary:
            with self.subTest(node=node["id"]):
                self.assertIsNone(node["gateway"])
        for node in payload["nodes"]:
            if node["id"] in gate_ids:
                self.assertEqual(node["gateway"], {"leads_to": gate_ids[node["id"]]})

    @patch("web.webclient.presentation.local_map.grid._grid_nodes_in_range", return_value=[])
    def test_an_in_map_landmark_is_not_a_way_out_of_the_map(self, _mock_range):
        self.char1.location = self.plaza
        record_arrival(self.char1)
        self.char1.location = self.south_gate
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        remembered_ids = {node["id"] for node in payload["nodes"] if node["visibility"] == "remembered"}
        self.assertNotIn(_t_grid_id(*_T_PLAZA_XYZ[:2]), remembered_ids)

    @patch("web.webclient.presentation.local_map.grid._grid_nodes_in_range", return_value=[])
    def test_two_capital_gate_rooms_stay_distinguishable_when_both_remembered(self, _mock_range):
        self.char1.location = self.east_gate
        record_arrival(self.char1)
        self.char1.location = self.south_gate
        record_arrival(self.char1)
        self.char1.location = self.plaza
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        remembered = {
            node["id"]: node["label"]
            for node in payload["nodes"]
            if node["visibility"] == "remembered"
        }
        self.assertEqual(
            remembered,
            {
                _t_grid_id(*SOUTH_GATE_XYZ[:2]): f"{_t_region_display_for(*SOUTH_APPROACH)}（{self.south_gate.key}）",
                _t_grid_id(*EAST_GATE_XYZ[:2]): f"{_t_region_display_for(*EAST_APPROACH)}（{self.east_gate.key}）",
            },
        )
        self.assertEqual(len(set(remembered.values())), 2)

    def test_a_gateway_on_a_different_grid_map_is_omitted_not_fabricated(self):
        from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate

        registry_attribute = "WILDERNESS" + "_ENTRY_REGISTRY"
        shipped_entries = _live("world.lore.wilderness_entry", registry_attribute)

        other_entry = WildernessEntryPoint(
            anchor_key=_T_MAP_KEY,
            shape=("#",),
            origin_xy=(90, 90),
            gates=(WildernessGate("n", (2, 4), "other_capital"),),
        )
        self.char1.location = self.south_gate
        record_arrival(self.char1)
        record = {
            "schema_version": 1,
            "visited": {
                _t_grid_id(*SOUTH_GATE_XYZ[:2]): {"first_seen_tick": 1, "last_seen_tick": 1},
                "grid:other_capital:2:4": {"first_seen_tick": 2, "last_seen_tick": 2},
            },
        }
        self.char1.attributes.add("map_knowledge", record)
        with (
            patch(
                "world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY",
                {**shipped_entries, "other_capital_entry": other_entry},
            ),
            patch(
                "world.rules.map_knowledge._registered_grid_bounds",
                return_value=(10_000_000, 10_000_000),
            ),
        ):
            payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        ids = {node["id"] for node in payload["nodes"]}
        self.assertNotIn("grid:other_capital:2:4", ids)

    @covers_requirement(
        "webclient-local-map::metric-coordinates-survive-authoritative-transport-and-uniform-projection"
    )
    def test_metric_coordinates_reach_the_payload_unchanged(self):
        """The presenter projects nothing: server coordinates stay authoritative.

        A metric settlement frame (metres, not cell indices) is carried through
        the grid layer exactly as the room model holds it, and the move
        descriptor keeps the real destination identity. The projection into
        presentation geometry happens only in the client render model.
        """
        import types

        current_coord = (6500, 6350)
        neighbour_coord = (6500, 6450)

        current_node = types.SimpleNamespace(
            X=current_coord[0], Y=current_coord[1], node_index=0, symbol="#"
        )
        neighbour_node = types.SimpleNamespace(
            X=neighbour_coord[0], Y=neighbour_coord[1], node_index=1, symbol="#"
        )
        current_node.links = {"n": neighbour_node}

        class FakeMap:
            Z = _T_MAP_KEY
            options = {"map_mode": "nodes", "map_visual_range": 2}
            node_index_map = {0: current_node, 1: neighbour_node}

            def get_node_from_coord(self, coord):
                return {current_coord: current_node, neighbour_coord: neighbour_node}.get(coord)

        class EmptyQuery:
            def first(self):
                return None

        self.char1.location = self.plaza
        with (
            patch.object(type(self.plaza), "xyz", (*current_coord, _T_MAP_KEY)),
            patch.object(type(self.plaza), "xymap", FakeMap()),
            patch("world.maps.map_data.settlement_graph", return_value=None),
            patch(
                "web.webclient.presentation.local_map.grid._grid_nodes_in_range",
                return_value=[current_node, neighbour_node],
            ),
            # The metric extent itself is declared by the settlement map; this
            # change owns the transport envelope, so the synthetic frame is
            # registered explicitly instead of inventing a shipped coordinate.
            patch(
                "world.rules.map_knowledge._registered_grid_bounds",
                return_value=(10_000_000, 10_000_000),
            ),
            patch(
                "typeclasses.rooms.GridRoom.objects.filter_xyz",
                return_value=EmptyQuery(),
            ),
        ):
            record_arrival(self.char1)
            payload = self._registry().render("local_map", _context(self.char1))

        self.assertTrue(payload["available"])
        self.assertEqual(payload["layer"], "grid")
        by_id = {node["id"]: node for node in payload["nodes"]}
        current = by_id[_t_grid_id(*current_coord)]
        self.assertEqual((current["x"], current["y"]), current_coord)
        self.assertEqual(current["visibility"], "current")
        neighbour = by_id[_t_grid_id(*neighbour_coord)]
        self.assertEqual((neighbour["x"], neighbour["y"]), neighbour_coord)
        self.assertEqual(neighbour["visibility"], "visible_unvisited")
        # No exit exists at the synthetic neighbour, so no move is advertised:
        # the projection never manufactures one.
        self.assertIsNone(neighbour["action"])


class LocalMapGatewayPairTests(EvenniaTest):
    """The gateway renders as a matched node pair on both layers.

    fix-wilderness-map-adjacency-truth: node identity follows the resolver,
    the wild cell a gateway replaces never appears, and both sides agree with
    real traversal in both directions.

    ``EvenniaTest`` (not ``EvenniaTestCase``): the round-trip test walks the
    character back through the return exit, and the wilderness provider's
    per-character coordinate bookkeeping only completes reliably on the
    full-evennia fixture (same as ``typeclasses.tests.test_exits``).
    """

    ENTRY_ID = "wild:%s:%d:%d" % ("elosern", *EAST_APPROACH)
    GATE_ID = _t_grid_id(*EAST_GATE_XYZ[:2])

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.east_gate = GridRoom.objects.filter_xyz(
            xyz=EAST_GATE_XYZ
        ).first()
        from typeclasses.exits import WildernessGateExit

        self.gate = [
            exit_obj
            for exit_obj in self.east_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        ][0]

    def _registry(self):
        return build_production_registry()

    def _at_gate_room(self):
        self.char1.location = self.east_gate
        record_arrival(self.char1)

    def _at_entry_cell(self):
        # Reaching the gate room records its grid node (as ordinary walking
        # does); only then does the character step through the gate.
        self.char1.location = self.east_gate
        record_arrival(self.char1)
        self.gate.at_traverse(self.char1, self.east_gate)

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_entry_cell_gateway_node_is_the_gate_room_itself(self):
        self._at_entry_cell()
        payload = self._registry().render("local_map", _context(self.char1))
        node = next(node for node in payload["nodes"] if node["id"] == self.GATE_ID)
        self.assertEqual(node["label"], self.east_gate.key)
        # Renderer-local geometry: the adjacent cell of the west step.
        entry = _live("world.lore.wilderness_entry", "WILDERNESS" + "_ENTRY_REGISTRY")[
            _T_MAP_KEY
        ]
        x, y = entry.approach_cell(entry.gate_for("w"))  # east approach cell
        self.assertEqual((node["x"], node["y"]), (x - 1, y))
        # The character walked through the gate: knowledge holds its canonical
        # grid id, so visibility follows it on the far side too.
        self.assertEqual(node["visibility"], "visible_visited")
        self.assertEqual(node["action"]["kind"], "move")
        west_exit = [
            exit_obj for exit_obj in self.char1.location.exits if exit_obj.key == "west"
        ][0]
        self.assertEqual(node["action"]["exit_ref"], str(int(west_exit.id)))
        self.assertEqual(node["action"]["destination"], self.GATE_ID)
        # The wilderness-adjacent grid gate names the settlement it leads
        # into; the current approach cell and every wild node carry null.
        self.assertEqual(node["gateway"], {"leads_to": _t_anchor_display(entry.anchor_key)})
        for other in payload["nodes"]:
            if other["id"] != self.GATE_ID:
                with self.subTest(node=other["id"]):
                    self.assertIsNone(other["gateway"])
        # The replaced geometric wild cell never appears.
        self.assertNotIn(
            f"wild:elosern:{x - 1}:{y}",
            [node["id"] for node in payload["nodes"]],
        )
        # Non-gateway directions stay ordinary terrain cells.
        north = next(
            edge
            for edge in payload["edges"]
            if edge["source"] == payload["current_node"] and edge["label"] == "n"
        )
        self.assertEqual(north["destination"], f"wild:elosern:{x}:{y + 1}")

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_gate_room_panel_shows_the_wild_entry_node(self):
        from world.maps.wilderness_provider import region_for_coordinates

        self._at_gate_room()
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "grid")
        node = next(node for node in payload["nodes"] if node["id"] == self.ENTRY_ID)
        self.assertEqual(
            node["label"],
            _live("world.lore.wilderness_regions", "WILDERNESS" + "_REGION_REGISTRY")[
                region_for_coordinates(*EAST_APPROACH)
            ].display_name_zh,
        )
        # The gate's key normalizes to east; the slot stands whole lattice
        # cells east of the gate room and never refines the drawing's cell
        # (a metric settlement's spacing is not one coordinate unit).
        divisor = _payload_cell_divisor(payload, exclude=self.ENTRY_ID)
        self.assertEqual(_payload_cell_divisor(payload), divisor)
        self.assertEqual(node["y"], EAST_GATE_XYZ[1])
        self.assertGreaterEqual(
            _inserted_multiple(
                (node["x"], node["y"]), EAST_GATE_XYZ[:2], 0, divisor
            ),
            1,
        )
        self.assertEqual(node["action"]["kind"], "move")
        self.assertEqual(node["action"]["exit_ref"], str(int(self.gate.id)))
        self.assertEqual(node["action"]["destination"], self.ENTRY_ID)
        edge = next(
            edge
            for edge in payload["edges"]
            if edge["source"] == payload["current_node"]
            and edge["destination"] == self.ENTRY_ID
        )
        self.assertEqual(edge["label"], "e")
        self.assertTrue(edge["traversable"])
        # The current gate room names the wilderness region its gate opens
        # onto; the cross-layer wild target carries null (a city-side exit
        # stub reads the current gate's metadata).
        current = next(n for n in payload["nodes"] if n["current"])
        self.assertEqual(current["gateway"], {"leads_to": _t_region_display_for(*EAST_APPROACH)})
        self.assertIsNone(node["gateway"])

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_both_directions_agree_with_real_traversal(self):
        from web.webclient.actions.node_ids import node_id_for_location

        # Grid side: the rendered gate node is the actual wilderness arrival.
        self._at_gate_room()
        payload = self._registry().render("local_map", _context(self.char1))
        node = next(n for n in payload["nodes"] if n["id"] == self.ENTRY_ID)
        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertEqual(node_id_for_location(self.char1.location), node["id"])
        self.assertEqual(node["action"]["destination"], node["id"])

        # Wilderness side: the rendered gateway node is the actual gate arrival.
        payload = self._registry().render("local_map", _context(self.char1))
        gateway = next(n for n in payload["nodes"] if n["id"] == self.GATE_ID)
        west_exit = [
            exit_obj for exit_obj in self.char1.location.exits if exit_obj.key == "west"
        ][0]
        west_exit.at_traverse(self.char1, self.char1.location)
        self.assertEqual(self.char1.location.id, self.east_gate.id)
        self.assertEqual(node_id_for_location(self.east_gate), gateway["id"])
        self.assertEqual(gateway["action"]["destination"], gateway["id"])


    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_undecodable_gateway_destination_fails_closed(self):
        # Run-2 remediation (rubber-duck run 1): a resolved gateway id the
        # presenter cannot decode is an identity it cannot name -- the panel
        # fails closed instead of fabricating a label.
        self._at_entry_cell()
        with (
            patch(
                "world.maps.wilderness_destination.resolve_wilderness_destination",
                return_value=_t_grid_id(99999, 0),
            ),
            self.assertRaises(PanelUnavailableError),
        ):
            from web.webclient.presentation.local_map import local_map_presenter

            local_map_presenter(_context(self.char1))

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_missing_gate_room_keeps_canonical_id_as_label(self):
        # Run-2 remediation (rubber-duck run 1): a decoded-but-missing gate
        # room keeps its canonical identity honestly (id as label, no anchor
        # claim) and never re-fabricates the geometric wild cell.
        self._at_entry_cell()

        class EmptyQuery:
            def first(self):
                return None

        # The resolver resolves the gate room (so the gateway renders); the
        # presenter's own label lookup then finds nothing -- the TOCTOU the
        # presenter branch defends against.
        with (
            patch(
                "world.maps.wilderness_destination.grid_room_for_gate",
                return_value=self.east_gate,
            ),
            patch(
                "typeclasses.rooms.GridRoom.objects.filter_xyz",
                return_value=EmptyQuery(),
            ),
        ):
            from web.webclient.presentation.local_map import local_map_presenter

            payload = local_map_presenter(_context(self.char1))
        node = next(n for n in payload["nodes"] if n["id"] == self.GATE_ID)
        self.assertEqual(node["label"], self.GATE_ID)
        self.assertFalse(node["anchor"])
        self.assertFalse(node["landmark"])
        # The footprint cell the gate direction faces never appears as a wild node.
        self.assertNotIn(
            "wild:elosern:%d:%d" % (EAST_APPROACH[0] - 1, EAST_APPROACH[1]),
            {n["id"] for n in payload["nodes"]},
        )


if __name__ == "__main__":
    unittest.main()
