from tools.spec_traceability import covers_requirement
import types
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from unittest.mock import patch
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import GridRoom, InstanceRoom, Room
from web.webclient.presentation.local_map import MAX_NODES
from web.webclient.presentation.registry import build_production_registry
from world.maps.bootstrap import NORTH_GATE_XYZ, SOUTH_GATE_XYZ, sync_grid, sync_wilderness
from world.rules.map_knowledge import record_arrival

from ._support import _T_MAP_KEY, _T_PLAZA_XYZ, _context, _t_grid_id



class LocalMapGridGateCapacityTests(EvenniaTestCase):
    """Capacity reservation and slot probing for grid-side gate nodes."""

    ENTRY_ID = "wild:elosern:60:103"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        cls._north_gate = GridRoom.objects.filter_xyz(
            xyz=NORTH_GATE_XYZ
        ).first()
        cls._plaza = GridRoom.objects.filter_xyz(xyz=_T_PLAZA_XYZ).first()
        from typeclasses.exits import WildernessGateExit

        cls._gate = [
            exit_obj
            for exit_obj in cls._north_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        ][0]

    def setUp(self):
        self.room1 = create_object(Room, key="Room1")
        self.char1 = create_object(PlayerCharacter, key="Char", location=self.room1)
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        # filter_xyz, not get(id): the plaza is an AnchorRoom, and the plain
        # typeclass manager does not resolve subclass typeclasses.
        self.north_gate = GridRoom.objects.filter_xyz(
            xyz=NORTH_GATE_XYZ
        ).first()
        self.plaza = GridRoom.objects.filter_xyz(
            xyz=_T_PLAZA_XYZ
        ).first()

    def _registry(self):
        return build_production_registry()

    def _make_gate(
        self, location, key="荒野", aliases=("wilderness", "north", "n"), gate_direction="s"
    ):
        from typeclasses.exits import WildernessGateExit

        gate = create_object(
            WildernessGateExit, key=key, aliases=list(aliases),
            location=location, destination=location,
        )
        gate.db.anchor_key = _T_MAP_KEY
        # The presenter refuses a gate row whose direction names no gate
        # (same refusal as the traversal), so synthetic gates carry the
        # identity the tests pin: "s" -> approach cell (60, 103), face "n";
        # "n" -> approach cell (60, 97), face "s".
        gate.db.gate_direction = gate_direction
        return gate

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_capacity_trim_keeps_the_gate_and_farthers_first(self):
        # At the real north gate: in-range {(2,4),(2,3),(1,3),(3,3)} + gate.
        # Cap 4 reserves one slot for the gate, so exactly one far node goes.
        self.char1.location = self.north_gate
        record_arrival(self.char1)
        with patch(
            "web.webclient.presentation.local_map.grid.MAX_NODES", 4
        ):
            payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        ids = {node["id"] for node in payload["nodes"]}
        self.assertEqual(len(ids), 4)
        # In range from (2,4): {(2,4),(2,3),(1,3),(3,3),(2,2)}; cap 4 reserves
        # one slot for the gate -> trim drops the two farthest in Chebyshev/
        # Y/X descending order: (2,2) then the (1,3)/(2,3)/(3,3) tie-break
        # loser (3,3).
        self.assertIn(self.ENTRY_ID, ids)
        self.assertNotIn(_t_grid_id(3, 3), ids)
        self.assertNotIn(_t_grid_id(2, 2), ids)
        self.assertIn(_t_grid_id(2, 4), ids)
        self.assertIn(_t_grid_id(2, 3), ids)
        self.assertIn(_t_grid_id(1, 3), ids)
        gate_node = next(n for n in payload["nodes"] if n["id"] == self.ENTRY_ID)
        self.assertEqual((gate_node["x"], gate_node["y"]), (2, 5))
        self.assertIsNotNone(gate_node["action"])

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_full_budget_synthetic_map_still_carries_the_gate(self):
        # A synthetic xymap already filled to MAX_NODES still renders the
        # gate: the trim absorbs the pressure, never the gateway identity.
        # The cap is patched to the 3x3 grid's 9 decodeable nodes (the real
        # the sample city decodes only 0..4 per axis, so the full 64 would
        # fabricate unencodable ids -- the cap semantics are identical).
        self._make_gate(self.plaza)
        nodes = [
            types.SimpleNamespace(
                X=col, Y=row, node_index=row * 100 + col, links={}, symbol="#"
            )
            for row in range(3)
            for col in range(3)
        ]
        current = nodes[0]
        current.links = {f"l{index}": node for index, node in enumerate(nodes[1:])}

        class FakeMap:
            Z = _T_MAP_KEY
            options = {"map_mode": "nodes", "map_visual_range": 8}
            node_index_map = {node.node_index: node for node in nodes}

            def get_node_from_coord(self, coord):
                return next((n for n in nodes if (n.X, n.Y) == coord), None)

        class EmptyQuery:
            def first(self):
                return None

        self.char1.location = self.plaza
        record_arrival(self.char1)
        with (
            patch.object(type(self.plaza), "xyz", (0, 0, _T_MAP_KEY)),
            patch.object(type(self.plaza), "xymap", FakeMap()),
            patch("web.webclient.presentation.local_map.grid.MAX_NODES", 9),
            patch(
                "typeclasses.rooms.GridRoom.objects.filter_xyz",
                return_value=EmptyQuery(),
            ),
        ):
            payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        self.assertEqual(len(payload["nodes"]), 9)
        by_id = {node["id"]: node for node in payload["nodes"]}
        self.assertIn(self.ENTRY_ID, by_id)
        self.assertIsNotNone(by_id[self.ENTRY_ID]["action"])

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_out_of_bounds_preferred_slot_probes_back_in_range(self):
        # Run-2 remediation (rubber-duck run 2): a preferred slot outside the
        # payload coordinate bounds must probe to the nearest legal free slot,
        # never emit an out-of-bounds node that kills the whole panel.
        self._make_gate(self.plaza)
        current = types.SimpleNamespace(X=1024, Y=1024, node_index=1, links={}, symbol="#")

        class FakeMap:
            Z = _T_MAP_KEY
            options = {"map_mode": "nodes", "map_visual_range": 1}
            node_index_map = {current.node_index: current}

            def get_node_from_coord(self, coord):
                return current if (current.X, current.Y) == coord else None

        class EmptyQuery:
            def first(self):
                return None

        self.char1.location = self.plaza
        record_arrival(self.char1)
        with (
            patch.object(type(self.plaza), "xyz", (1024, 1024, _T_MAP_KEY)),
            patch.object(type(self.plaza), "xymap", FakeMap()),
            # A map whose registered bounds reach the payload edge is the
            # only way a room coordinate of 1024 can be legal at all.
            patch(
                "world.rules.map_knowledge._registered_grid_bounds",
                return_value=(1100, 1100),
            ),
            patch(
                "typeclasses.rooms.GridRoom.objects.filter_xyz",
                return_value=EmptyQuery(),
            ),
        ):
            payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        by_id = {node["id"]: node for node in payload["nodes"]}
        gate_node = by_id[self.ENTRY_ID]
        # Preferred (1024,1025) is out of bounds; diamond ring 1 (dy,dx)-
        # sorted: (1024,1024) occupied by the current node, (1023,1025)/
        # (1025,1025)/(1024,1026) out of bounds; ring 2 opens at dy=-2 ->
        # (1024,1023), the first legal free slot.
        self.assertEqual((gate_node["x"], gate_node["y"]), (1024, 1023))
        self.assertIsNotNone(gate_node["action"])

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_occupied_preferred_slot_probes_deterministically(self):
        # Plaza (2,2): a registered gate's north slot (2,3) is an in-range
        # node; the gate takes the nearest free slot, not a dropped identity.
        gate = self._make_gate(self.plaza)
        self.char1.location = self.plaza
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        by_id = {node["id"]: node for node in payload["nodes"]}
        self.assertIn(_t_grid_id(2, 3), by_id)
        self.assertIn(self.ENTRY_ID, by_id)
        gate_node = by_id[self.ENTRY_ID]
        # Sweep from (2,3): ring 1 visits (2,2),(1,3),(3,3),(2,4) -- all
        # in-range city nodes; ring 2 visits (2,1),(1,2),(3,2) (city nodes)
        # before (0,3), which no city node occupies. Renderer-local geometry
        # is slot freedom, never identity.
        self.assertEqual((gate_node["x"], gate_node["y"]), (0, 3))
        slots = [(n["x"], n["y"]) for n in payload["nodes"] if n["id"] != self.ENTRY_ID]
        self.assertNotIn((gate_node["x"], gate_node["y"]), slots)
        self.assertEqual(gate_node["action"]["exit_ref"], str(int(gate.id)))
        edge = next(
            e for e in payload["edges"] if e["destination"] == self.ENTRY_ID
        )
        self.assertEqual(edge["label"], "n")
        self.assertTrue(edge["traversable"])

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_slot_direction_follows_registry_face_not_key_aliases(self):
        # wilderness-anchor-footprint-local-map D2: the slot direction is the
        # registry gate face (db.gate_direction "s" -> face "n"), never a
        # parse of the exit's key or aliases -- key/alias direction parsing is
        # deleted, and display aliases may name any direction they like.
        self._make_gate(self.plaza, key="捷徑", aliases=("southeast", "east"))
        self.char1.location = self.plaza
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        edge = next(
            e for e in payload["edges"] if e["destination"] == self.ENTRY_ID
        )
        self.assertEqual(edge["label"], "n")
        gate_node = next(n for n in payload["nodes"] if n["id"] == self.ENTRY_ID)
        self.assertIsNotNone(gate_node["action"])
        # Exactly one gate edge exists and it names the face, never a
        # direction any alias mentions.
        labels = {
            edge["label"]
            for edge in payload["edges"]
            if edge["destination"] == self.ENTRY_ID
        }
        self.assertEqual(labels, {"n"})

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_duplicate_gate_exits_render_one_node_from_lowest_dbid(self):
        first = self._make_gate(self.plaza)
        second = self._make_gate(self.plaza, key="北境之門")
        self.char1.location = self.plaza
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        gate_nodes = [n for n in payload["nodes"] if n["id"] == self.ENTRY_ID]
        self.assertEqual(len(gate_nodes), 1)
        self.assertEqual(gate_nodes[0]["action"]["exit_ref"], str(int(first.id)))
        edges = [e for e in payload["edges"] if e["destination"] == self.ENTRY_ID]
        self.assertEqual(len(edges), 1)
        self.assertFalse(
            any(n["id"] == self.ENTRY_ID for n in payload["nodes"] if n["action"] is None)
        )

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_gate_row_without_usable_direction_renders_no_node(self):
        # The presenter refuses exactly what the traversal refuses: a
        # WildernessGateExit whose db.gate_direction is unset or names no gate
        # of the entry cannot move anyone, so it is never advertised.
        unconfigured = self._make_gate(self.plaza)
        unconfigured.db.gate_direction = None
        bogus = self._make_gate(self.plaza, key="北境之門")
        bogus.db.gate_direction = "q"
        self.char1.location = self.plaza
        record_arrival(self.char1)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        self.assertFalse(
            any(node["id"] == self.ENTRY_ID for node in payload["nodes"])
        )
        self.assertFalse(
            any(edge["destination"] == self.ENTRY_ID for edge in payload["edges"])
        )

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_two_gates_reserve_capacity_and_render_both(self):
        # The reservation is len(gate_candidates), not one: with two distinct
        # gates and a full-budget fake map the trim absorbs the pressure for
        # BOTH reservations -- neither gate may be silently omitted, and only
        # ordinary farthest nodes are trimmed in the pinned order.
        self._make_gate(self.plaza, gate_direction="s")  # -> 60:103, face n
        self._make_gate(self.plaza, key="北境之門", gate_direction="n")  # -> 60:97, face s
        nodes = [
            types.SimpleNamespace(
                X=col, Y=row, node_index=row * 100 + col, links={}, symbol="#"
            )
            for row in range(3)
            for col in range(3)
        ]
        current = nodes[0]  # (0, 0)
        current.links = {f"l{index}": node for index, node in enumerate(nodes[1:])}

        class FakeMap:
            Z = _T_MAP_KEY
            options = {"map_mode": "nodes", "map_visual_range": 8}
            node_index_map = {node.node_index: node for node in nodes}

            def get_node_from_coord(self, coord):
                return next((n for n in nodes if (n.X, n.Y) == coord), None)

        class EmptyQuery:
            def first(self):
                return None

        self.char1.location = self.plaza
        record_arrival(self.char1)
        with (
            patch.object(type(self.plaza), "xyz", (0, 0, _T_MAP_KEY)),
            patch.object(type(self.plaza), "xymap", FakeMap()),
            patch("web.webclient.presentation.local_map.grid.MAX_NODES", 4),
            patch(
                "typeclasses.rooms.GridRoom.objects.filter_xyz",
                return_value=EmptyQuery(),
            ),
        ):
            payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        by_id = {node["id"]: node for node in payload["nodes"]}
        # Cap 4 reserves 2 slots for the gates -> visible cap 2: the current
        # node plus the single nearest droppable (ascending (cheb, Y, X):
        # (1,0)). Both gate identities survive untouched.
        self.assertEqual(len(payload["nodes"]), 4)
        self.assertIn(_t_grid_id(0, 0), by_id)
        self.assertIn(_t_grid_id(1, 0), by_id)
        self.assertIn("wild:elosern:60:103", by_id)
        self.assertIn("wild:elosern:60:97", by_id)
        self.assertIsNotNone(by_id["wild:elosern:60:103"]["action"])
        self.assertIsNotNone(by_id["wild:elosern:60:97"]["action"])
        # Faces: 60:103 draws north to (0, 1), 60:97 draws south to (0, -1);
        # both preferred slots are free after the trim.
        self.assertEqual((by_id["wild:elosern:60:103"]["x"], by_id["wild:elosern:60:103"]["y"]), (0, 1))
        self.assertEqual((by_id["wild:elosern:60:97"]["x"], by_id["wild:elosern:60:97"]["y"]), (0, -1))
        edge_labels = {
            edge["label"]
            for edge in payload["edges"]
            if edge["destination"] in ("wild:elosern:60:103", "wild:elosern:60:97")
        }
        self.assertEqual(edge_labels, {"n", "s"})


if __name__ == "__main__":
    unittest.main()
