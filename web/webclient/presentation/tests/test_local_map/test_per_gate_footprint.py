from tools.spec_traceability import covers_requirement
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.rooms import GridRoom, InstanceRoom, Room
from web.webclient.presentation.registry import build_production_registry
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.maps.wilderness_provider import is_valid_wilderness_cell
from world.rules.map_knowledge import record_arrival

from ._support import (
    EAST_APPROACH,
    EAST_GATE_XYZ,
    SOUTH_APPROACH,
    SOUTH_GATE_XYZ,
    _context,
    _inserted_multiple,
    _live_gateway_entry,
    _payload_cell_divisor,
    _t_grid_id,
)


class LocalMapPerGateFootprintTests(EvenniaTest):
    """Per-gate presentation on both sides and the footprint boundary (P1b).

    Registry geometry (probed, not authored): the sample city's footprint is
    a five-by-five mask; gate "n" -> 南門 ``SOUTH_GATE_XYZ`` with its
    south-approach cell, gate "w" -> 東門 ``EAST_GATE_XYZ`` with its
    east-approach cell. ``EvenniaTest`` because the round-trips traverse
    real gateway exits (same fixture need as
    ``LocalMapGatewayPairTests``).
    """

    SOUTH_ID = _t_grid_id(*SOUTH_GATE_XYZ[:2])  # 南門
    EAST_ID = _t_grid_id(*EAST_GATE_XYZ[:2])  # 東門
    _ENTRY = _live_gateway_entry()
    SOUTH_APPROACH = "wild:%s:%d:%d" % ("elosern", *SOUTH_APPROACH)
    EAST_APPROACH = "wild:%s:%d:%d" % ("elosern", *EAST_APPROACH)
    _CELLS = _ENTRY.footprint_cells
    FOOTPRINT_X = {x for x, _ in _CELLS}
    FOOTPRINT_Y = {y for _, y in _CELLS}

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()

    def _registry(self):
        return build_production_registry()

    def _wild_node_ids(self, payload):
        ids = set()
        for node in payload["nodes"]:
            if not node["id"].startswith("wild:elosern:"):
                continue
            _, _, x, y = node["id"].split(":")
            if (int(x), int(y)) in self._CELLS:
                ids.add(node["id"])
        return ids

    def _at_wild(self, coordinates):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
        from world.maps.wilderness_provider import WILDERNESS_NAME

        entered = enter_wilderness(self.char1, coordinates=coordinates, name=WILDERNESS_NAME)
        self.assertTrue(entered, coordinates)
        record_arrival(self.char1)
        # Pin the reveal precondition explicitly: one synthetic cell of ground
        # sight reveals every adjacent cell, so a footprint assertion below can
        # never pass merely because the disclosure filter withheld everything.
        from world.rules.clock import get_world_clock
        from world.rules.map_knowledge import record_ground_observation

        record_ground_observation(
            self.char1, tuple(coordinates), int(get_world_clock().tick), 1
        )

    @covers_requirement(
        "webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel"
    )
    def test_footprint_never_renders_as_walkable_wild_node(self):
        # Every non-gate approach vantage facing the footprint renders absent
        # ground: no footprint wild node anywhere in the payload and no edge
        # for the footprint-facing direction (delta scenario, vantages off
        # the two gate approach cells).
        # The east gate's own approach cell sits immediately east of the
        # footprint's middle row, so the east-side vantage moves one cell
        # north of it.
        ex, ey = EAST_APPROACH
        sx, sy = SOUTH_APPROACH
        minx, maxx = min(self.FOOTPRINT_X), max(self.FOOTPRINT_X)
        miny, maxy = min(self.FOOTPRINT_Y), max(self.FOOTPRINT_Y)
        # The top row faces the capital's own river on one column, so the
        # north-facing vantage is the top-row cell whose neighbour is walkable
        # ground -- never a fixed offset into the mask.
        north_vantages = [
            (x, maxy + 1)
            for x, y in sorted(self._CELLS)
            if y == maxy and is_valid_wilderness_cell((x, maxy + 1))
        ]
        self.assertTrue(
            north_vantages, "the footprint keeps one walkable north-facing vantage"
        )
        vantages = [
            ((minx - 1, sy + 3), "e"),  # west of the mask -> footprint face
            ((maxx + 1, sy), "w"),      # east of the mask -> footprint face
            ((minx, miny - 1), "n"),    # south of the mask -> footprint face
            *((cell, "s") for cell in north_vantages),  # north of the mask -> footprint face
        ]
        for coordinates, blocked in vantages:
            with self.subTest(vantage=coordinates, direction=blocked):
                self._at_wild(coordinates)
                payload = self._registry().render("local_map", _context(self.char1))
                self.assertEqual(payload["layer"], "wilderness")
                self.assertEqual(self._wild_node_ids(payload), set())
                # The view is genuinely populated: the revealed, non-footprint
                # neighbours are drawn, so the empty footprint set above is the
                # provider rule's effect and not an empty payload.
                drawn_wild = {
                    node["id"]
                    for node in payload["nodes"]
                    if node["id"].startswith("wild:elosern:")
                    and node["id"] != payload["current_node"]
                }
                self.assertTrue(
                    drawn_wild, f"no revealed neighbour was drawn at {coordinates}"
                )
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
        # registry face -- never the other gate's approach cell. The slot
        # stands whole lattice cells beyond the gate room on its facing axis
        # and never introduces a finer pairwise delta than the drawing it is
        # added to: a metric settlement's spacing is tens to hundreds of
        # metres, so a one-unit slot would collapse the renderer's divisor.
        for room, approach_id, other_id, dx, dy in (
            (self.south_gate, self.SOUTH_APPROACH, self.EAST_APPROACH, 0, -1),
            (self.east_gate, self.EAST_APPROACH, self.SOUTH_APPROACH, 1, 0),
        ):
            with self.subTest(room=room.key):
                self.char1.location = room
                record_arrival(self.char1)
                payload = self._registry().render("local_map", _context(self.char1))
                by_id = {node["id"]: node for node in payload["nodes"]}
                self.assertIn(approach_id, by_id)
                self.assertNotIn(other_id, by_id)
                node = by_id[approach_id]
                divisor = _payload_cell_divisor(payload, exclude=approach_id)
                self.assertEqual(
                    _payload_cell_divisor(payload),
                    divisor,
                    "the gate slot must not refine the drawing's cell",
                )
                slot = (node["x"], node["y"])
                if dx:
                    self.assertEqual(slot[1], room.xyz[1])
                    self.assertGreaterEqual(_inserted_multiple(slot, room.xyz, 0, divisor) * dx, 1)
                else:
                    self.assertEqual(slot[0], room.xyz[0])
                    self.assertGreaterEqual(_inserted_multiple(slot, room.xyz, 1, divisor) * dy, 1)
                self.assertIsNotNone(node["action"])

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_both_gates_render_independently_on_the_wild_side(self):
        # Each approach cell resolves ONLY its own gateway: the south
        # approach's north step is 南門, the east approach's west step is
        # 東門, and the other gate never appears.
        for coordinates, gate_id, other_id, direction in (
            (SOUTH_APPROACH, self.SOUTH_ID, self.EAST_ID, "n"),
            (EAST_APPROACH, self.EAST_ID, self.SOUTH_ID, "w"),
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
        east_exit = next(
            exit_obj
            for exit_obj in self.east_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        )
        self.assertEqual(south_exit.key, "荒野")
        self.assertEqual(east_exit.key, "荒野")
        # 南門's face is "s"; alias it as if it led north. 東門's face is "e";
        # alias it as if it led west.
        south_exit.aliases.clear()
        south_exit.aliases.add("north", "n")
        east_exit.aliases.clear()
        east_exit.aliases.add("west", "w")

        for room, approach_id, dx, dy, exit_obj in (
            (self.south_gate, self.SOUTH_APPROACH, 0, -1, south_exit),
            (self.east_gate, self.EAST_APPROACH, 1, 0, east_exit),
        ):
            with self.subTest(room=room.key):
                self.char1.location = room
                record_arrival(self.char1)
                payload = self._registry().render("local_map", _context(self.char1))
                by_id = {node["id"]: node for node in payload["nodes"]}
                self.assertIn(approach_id, by_id)
                node = by_id[approach_id]
                divisor = _payload_cell_divisor(payload, exclude=approach_id)
                self.assertEqual(
                    _payload_cell_divisor(payload),
                    divisor,
                    "the gate slot must not refine the drawing's cell",
                )
                slot = (node["x"], node["y"])
                if dx:
                    self.assertEqual(slot[1], room.xyz[1])
                    self.assertGreaterEqual(_inserted_multiple(slot, room.xyz, 0, divisor) * dx, 1)
                else:
                    self.assertEqual(slot[0], room.xyz[0])
                    self.assertGreaterEqual(_inserted_multiple(slot, room.xyz, 1, divisor) * dy, 1)
                self.assertEqual(node["action"]["exit_ref"], str(int(exit_obj.id)))

    @covers_requirement(
        "webclient-local-map::the-minimap-gate-nodes-match-traversal-in-both-directions"
    )
    def test_each_gate_pair_round_trips_through_real_traversal(self):
        from typeclasses.exits import WildernessGateExit
        from web.webclient.actions.node_ids import node_id_for_location

        for room, gate_id, approach_id, return_key in (
            (self.south_gate, self.SOUTH_ID, self.SOUTH_APPROACH, "north"),
            (self.east_gate, self.EAST_ID, self.EAST_APPROACH, "west"),
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
