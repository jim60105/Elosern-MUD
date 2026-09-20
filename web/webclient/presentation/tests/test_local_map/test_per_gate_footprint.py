from tools.spec_traceability import covers_requirement
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.rooms import GridRoom, InstanceRoom, Room
from web.webclient.presentation.registry import build_production_registry
from world.maps.bootstrap import NORTH_GATE_XYZ, SOUTH_GATE_XYZ, sync_grid, sync_wilderness
from world.rules.map_knowledge import record_arrival

from ._support import _context, _t_grid_id



class LocalMapPerGateFootprintTests(EvenniaTest):
    """Per-gate presentation on both sides and the footprint boundary (P1b).

    Registry geometry: footprint x=58..62, y=98..102; gate "n" -> 南門
    ``SOUTH_GATE_XYZ`` with approach (60, 97); gate "s" -> 北門
    ``NORTH_GATE_XYZ`` with approach (60, 103). ``EvenniaTest``
    because the round-trips traverse real gateway exits (same fixture need as
    ``LocalMapGatewayPairTests``).
    """

    SOUTH_ID = _t_grid_id(2, 0)  # 南門
    NORTH_ID = _t_grid_id(2, 4)  # 北門
    SOUTH_APPROACH = "wild:elosern:60:97"
    NORTH_APPROACH = "wild:elosern:60:103"
    FOOTPRINT_X = range(58, 63)
    FOOTPRINT_Y = range(98, 103)

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()

    def _registry(self):
        return build_production_registry()

    def _wild_node_ids(self, payload):
        ids = set()
        for node in payload["nodes"]:
            if not node["id"].startswith("wild:elosern:"):
                continue
            _, _, x, y = node["id"].split(":")
            if int(x) in self.FOOTPRINT_X and int(y) in self.FOOTPRINT_Y:
                ids.add(node["id"])
        return ids

    def _at_wild(self, coordinates):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
        from world.maps.wilderness_provider import WILDERNESS_NAME

        entered = enter_wilderness(self.char1, coordinates=coordinates, name=WILDERNESS_NAME)
        self.assertTrue(entered, coordinates)
        record_arrival(self.char1)

    @covers_requirement(
        "webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel"
    )
    def test_footprint_never_renders_as_walkable_wild_node(self):
        # Every non-gate approach vantage facing the footprint renders absent
        # ground: no footprint wild node anywhere in the payload and no edge
        # for the footprint-facing direction (delta scenario, vantages off
        # the two gate approach cells).
        vantages = [
            ((57, 100), "e"),  # -> (58, 100)
            ((63, 100), "w"),  # -> (62, 100)
            ((59, 97), "n"),   # -> (59, 98)
            ((59, 103), "s"),  # -> (59, 102)
        ]
        for coordinates, blocked in vantages:
            with self.subTest(vantage=coordinates, direction=blocked):
                self._at_wild(coordinates)
                payload = self._registry().render("local_map", _context(self.char1))
                self.assertEqual(payload["layer"], "wilderness")
                self.assertEqual(self._wild_node_ids(payload), set())
                edges = {
                    edge["label"]
                    for edge in payload["edges"]
                    if edge["source"] == payload["current_node"]
                }
                self.assertNotIn(blocked, edges)
                self.char1.location = self.south_gate

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_both_gates_render_independently_on_the_grid_side(self):
        # Each city gate room shows its OWN approach cell, drawn toward its
        # registry face -- never the other gate's approach cell.
        for room, approach_id, other_id, slot in (
            (self.south_gate, self.SOUTH_APPROACH, self.NORTH_APPROACH, (2, -1)),
            (self.north_gate, self.NORTH_APPROACH, self.SOUTH_APPROACH, (2, 5)),
        ):
            with self.subTest(room=room.key):
                self.char1.location = room
                record_arrival(self.char1)
                payload = self._registry().render("local_map", _context(self.char1))
                by_id = {node["id"]: node for node in payload["nodes"]}
                self.assertIn(approach_id, by_id)
                self.assertNotIn(other_id, by_id)
                node = by_id[approach_id]
                self.assertEqual((node["x"], node["y"]), slot)
                self.assertIsNotNone(node["action"])

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_both_gates_render_independently_on_the_wild_side(self):
        # Each approach cell resolves ONLY its own gateway: the south
        # approach's north step is 南門, the north approach's south step is
        # 北門, and the other gate never appears.
        for coordinates, gate_id, other_id, direction in (
            ((60, 97), self.SOUTH_ID, self.NORTH_ID, "n"),
            ((60, 103), self.NORTH_ID, self.SOUTH_ID, "s"),
        ):
            with self.subTest(cell=coordinates):
                self._at_wild(coordinates)
                payload = self._registry().render("local_map", _context(self.char1))
                by_id = {node["id"]: node for node in payload["nodes"]}
                self.assertIn(gate_id, by_id)
                self.assertNotIn(other_id, by_id)
                edge = next(
                    edge
                    for edge in payload["edges"]
                    if edge["source"] == payload["current_node"]
                    and edge["destination"] == gate_id
                )
                self.assertEqual(edge["label"], direction)
                self.assertTrue(edge["traversable"])

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_gate_identity_survives_identical_keys_and_rewritten_aliases(self):
        # sync_wilderness() provisions BOTH gate exits keyed 荒野; display
        # aliases are affordances, not identity. With deliberately misleading
        # aliases, each gate room still renders its OWN approach cell at its
        # OWN face slot, and no candidate is dropped to key deduplication.
        from typeclasses.exits import WildernessGateExit

        south_exit = next(
            exit_obj
            for exit_obj in self.south_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        )
        north_exit = next(
            exit_obj
            for exit_obj in self.north_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        )
        self.assertEqual(south_exit.key, "荒野")
        self.assertEqual(north_exit.key, "荒野")
        # 南門's face is "s"; alias it as if it led north. 北門's face is "n";
        # alias it as if it led south.
        south_exit.aliases.clear()
        south_exit.aliases.add("north", "n")
        north_exit.aliases.clear()
        north_exit.aliases.add("south", "s")

        for room, approach_id, face_slot, exit_obj in (
            (self.south_gate, self.SOUTH_APPROACH, (2, -1), south_exit),
            (self.north_gate, self.NORTH_APPROACH, (2, 5), north_exit),
        ):
            with self.subTest(room=room.key):
                self.char1.location = room
                record_arrival(self.char1)
                payload = self._registry().render("local_map", _context(self.char1))
                by_id = {node["id"]: node for node in payload["nodes"]}
                self.assertIn(approach_id, by_id)
                node = by_id[approach_id]
                self.assertEqual((node["x"], node["y"]), face_slot)
                self.assertEqual(node["action"]["exit_ref"], str(int(exit_obj.id)))

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_each_gate_pair_round_trips_through_real_traversal(self):
        from typeclasses.exits import WildernessGateExit
        from web.webclient.actions.node_ids import node_id_for_location

        for room, gate_id, approach_id, return_key in (
            (self.south_gate, self.SOUTH_ID, self.SOUTH_APPROACH, "north"),
            (self.north_gate, self.NORTH_ID, self.NORTH_APPROACH, "south"),
        ):
            with self.subTest(gate=gate_id):
                gate = next(
                    exit_obj
                    for exit_obj in room.exits
                    if isinstance(exit_obj, WildernessGateExit)
                )
                # Grid side: the rendered node is the real wilderness arrival.
                self.char1.location = room
                record_arrival(self.char1)
                payload = self._registry().render("local_map", _context(self.char1))
                node = next(n for n in payload["nodes"] if n["id"] == approach_id)
                gate.at_traverse(self.char1, room)
                self.assertEqual(node_id_for_location(self.char1.location), node["id"])
                self.assertEqual(node["action"]["destination"], node["id"])
                # Wild side: the rendered node is the real gate arrival.
                payload = self._registry().render("local_map", _context(self.char1))
                gateway = next(n for n in payload["nodes"] if n["id"] == gate_id)
                return_exit = next(
                    exit_obj
                    for exit_obj in self.char1.location.exits
                    if exit_obj.key == return_key
                )
                return_exit.at_traverse(self.char1, self.char1.location)
                self.assertEqual(self.char1.location.id, room.id)
                self.assertEqual(node_id_for_location(room), gateway["id"])
                self.assertEqual(gateway["action"]["destination"], gateway["id"])


if __name__ == "__main__":
    unittest.main()
