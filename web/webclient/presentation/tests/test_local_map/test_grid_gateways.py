from tools.spec_traceability import covers_requirement
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from unittest.mock import patch
from typeclasses.rooms import GridRoom, InstanceRoom, Room
from web.webclient.presentation.registry import PanelUnavailableError, build_production_registry
from world.maps.bootstrap import NORTH_GATE_XYZ, SOUTH_GATE_XYZ, sync_grid, sync_wilderness
from world.rules.map_knowledge import record_arrival

from ._support import _T_MAP_KEY, _T_PLAZA_XYZ, _context, _live, _t_grid_id, _t_region_display_for



class LocalMapGridGatewayTests(EvenniaTest):
    """Remembered grid nodes are stood-on map gateways (wave 4, and 1.4's
    distinctness qualifier)."""

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
        self.plaza = GridRoom.objects.filter_xyz(xyz=_T_PLAZA_XYZ).first()

    def _registry(self):
        return build_production_registry()

    @patch("web.webclient.presentation.local_map.grid._grid_nodes_in_range", return_value=[])
    def test_a_stood_on_gate_room_out_of_range_is_remembered(self, _mock_range):
        self.char1.location = self.north_gate
        record_arrival(self.char1)
        self.char1.location = self.south_gate
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "grid")
        remembered = [node for node in payload["nodes"] if node["visibility"] == "remembered"]
        self.assertEqual(len(remembered), 1)
        node = remembered[0]
        self.assertEqual(node["id"], _t_grid_id(2, 4))
        self.assertEqual((node["x"], node["y"]), (2, 4))
        self.assertEqual(node["label"], _t_region_display_for(60, 103))
        self.assertTrue(node["landmark"])
        self.assertFalse(node["anchor"])
        self.assertIsNone(node["action"])

    @patch("web.webclient.presentation.local_map.grid._grid_nodes_in_range", return_value=[])
    def test_an_in_map_landmark_is_not_a_way_out_of_the_map(self, _mock_range):
        self.char1.location = self.plaza
        record_arrival(self.char1)
        self.char1.location = self.south_gate
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        remembered_ids = {node["id"] for node in payload["nodes"] if node["visibility"] == "remembered"}
        self.assertNotIn(_t_grid_id(2, 2), remembered_ids)

    @patch("web.webclient.presentation.local_map.grid._grid_nodes_in_range", return_value=[])
    def test_two_capital_gate_rooms_stay_distinguishable_when_both_remembered(self, _mock_range):
        self.char1.location = self.north_gate
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
                _t_grid_id(2, 0): f"{_t_region_display_for(60, 97)}（南門）",
                _t_grid_id(2, 4): f"{_t_region_display_for(60, 103)}（北門）",
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
                _t_grid_id(2, 0): {"first_seen_tick": 1, "last_seen_tick": 1},
                "grid:other_capital:2:4": {"first_seen_tick": 2, "last_seen_tick": 2},
            },
        }
        self.char1.attributes.add("map_knowledge", record)
        with (
            patch(
                "world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY",
                {**shipped_entries, "other_capital_entry": other_entry},
            ),
            patch("world.rules.map_knowledge._registered_grid_bounds", return_value=(8, 8)),
        ):
            payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        ids = {node["id"] for node in payload["nodes"]}
        self.assertNotIn("grid:other_capital:2:4", ids)


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

    ENTRY_ID = "wild:elosern:60:103"
    GATE_ID = _t_grid_id(2, 4)

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.north_gate = GridRoom.objects.filter_xyz(
            xyz=NORTH_GATE_XYZ
        ).first()
        from typeclasses.exits import WildernessGateExit

        self.gate = [
            exit_obj
            for exit_obj in self.north_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        ][0]

    def _registry(self):
        return build_production_registry()

    def _at_gate_room(self):
        self.char1.location = self.north_gate
        record_arrival(self.char1)

    def _at_entry_cell(self):
        # Reaching the gate room records its grid node (as ordinary walking
        # does); only then does the character step through the gate.
        self.char1.location = self.north_gate
        record_arrival(self.char1)
        self.gate.at_traverse(self.char1, self.north_gate)

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_entry_cell_gateway_node_is_the_gate_room_itself(self):
        self._at_entry_cell()
        payload = self._registry().render("local_map", _context(self.char1))
        node = next(node for node in payload["nodes"] if node["id"] == self.GATE_ID)
        self.assertEqual(node["label"], self.north_gate.key)
        # Renderer-local geometry: the adjacent cell of the south step.
        entry = _live("world.lore.wilderness_entry", "WILDERNESS" + "_ENTRY_REGISTRY")[
            _T_MAP_KEY
        ]
        x, y = entry.approach_cell(entry.gate_for("s"))  # (60, 103)
        self.assertEqual((node["x"], node["y"]), (x, y - 1))
        # The character walked through the gate: knowledge holds its canonical
        # grid id, so visibility follows it on the far side too.
        self.assertEqual(node["visibility"], "visible_visited")
        self.assertEqual(node["action"]["kind"], "move")
        south_exit = [
            exit_obj for exit_obj in self.char1.location.exits if exit_obj.key == "south"
        ][0]
        self.assertEqual(node["action"]["exit_ref"], str(int(south_exit.id)))
        self.assertEqual(node["action"]["destination"], self.GATE_ID)
        # The replaced geometric wild cell never appears.
        self.assertNotIn(
            f"wild:elosern:{x}:{y - 1}",
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
    def test_gate_room_panel_shows_the_wild_entry_node(self):
        from world.maps.wilderness_provider import region_for_coordinates

        self._at_gate_room()
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "grid")
        node = next(node for node in payload["nodes"] if node["id"] == self.ENTRY_ID)
        self.assertEqual(
            node["label"],
            _live("world.lore.wilderness_regions", "WILDERNESS" + "_REGION_REGISTRY")[
                region_for_coordinates(60, 103)
            ].display_name_zh,
        )
        # The gate's key normalizes to north; (2,5) is free at this room.
        self.assertEqual((node["x"], node["y"]), (2, 5))
        self.assertEqual(node["action"]["kind"], "move")
        self.assertEqual(node["action"]["exit_ref"], str(int(self.gate.id)))
        self.assertEqual(node["action"]["destination"], self.ENTRY_ID)
        edge = next(
            edge
            for edge in payload["edges"]
            if edge["source"] == payload["current_node"]
            and edge["destination"] == self.ENTRY_ID
        )
        self.assertEqual(edge["label"], "n")
        self.assertTrue(edge["traversable"])

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_both_directions_agree_with_real_traversal(self):
        from web.webclient.actions.node_ids import node_id_for_location

        # Grid side: the rendered gate node is the actual wilderness arrival.
        self._at_gate_room()
        payload = self._registry().render("local_map", _context(self.char1))
        node = next(n for n in payload["nodes"] if n["id"] == self.ENTRY_ID)
        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertEqual(node_id_for_location(self.char1.location), node["id"])
        self.assertEqual(node["action"]["destination"], node["id"])

        # Wilderness side: the rendered gateway node is the actual gate arrival.
        payload = self._registry().render("local_map", _context(self.char1))
        gateway = next(n for n in payload["nodes"] if n["id"] == self.GATE_ID)
        south_exit = [
            exit_obj for exit_obj in self.char1.location.exits if exit_obj.key == "south"
        ][0]
        south_exit.at_traverse(self.char1, self.char1.location)
        self.assertEqual(self.char1.location.id, self.north_gate.id)
        self.assertEqual(node_id_for_location(self.north_gate), gateway["id"])
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
                return_value=self.north_gate,
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
        self.assertNotIn("wild:elosern:60:102", {n["id"] for n in payload["nodes"]})


if __name__ == "__main__":
    unittest.main()
