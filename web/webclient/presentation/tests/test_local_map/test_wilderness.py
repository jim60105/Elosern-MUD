from tools.spec_traceability import covers_requirement
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from unittest.mock import patch
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import GridRoom, InstanceRoom, Room
from web.webclient.presentation.local_map import LEGEND_LABELS, MAX_LEGEND, MAX_STRING_CODE_POINTS
from web.webclient.presentation.registry import build_production_registry
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.rules.map_knowledge import record_arrival

from ._support import (
    EAST_APPROACH,
    EAST_GATE_XYZ,
    SOUTH_APPROACH,
    SOUTH_GATE_XYZ,
    _T_MAP_KEY,
    _context,
    _live_gateway_entry,
    _t_anchor_display,
    _t_grid_id,
    _t_region_display_for,
    _t_wild_id,
)



class LocalMapWildernessTests(EvenniaTestCase):
    """Wilderness-layer adapter tests (task 3.3)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        cls._east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        cls._gate = [e for e in cls._east_gate.exits if e.key == "荒野"][0]

    def setUp(self):
        self.room1 = create_object(Room, key="Room1")
        self.char1 = create_object(PlayerCharacter, key="Char", location=self.room1)
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.east_gate = GridRoom.objects.get(id=self._east_gate.id)
        self.gate = [e for e in self.east_gate.exits if e.key == "荒野"][0]

    def _registry(self):
        return build_production_registry()

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_wilderness_payload_uses_provider_bounds_and_terrain_labels(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["layer"], "wilderness")
        x, y = self.char1.location.coordinates
        self.assertEqual(payload["current_node"], f"wild:elosern:{x}:{y}")
        for node in payload["nodes"]:
            self.assertTrue(node["label"].strip())
        # Legal adjacent cells bounded by the provider.
        for node in payload["nodes"]:
            if node["id"] == payload["current_node"]:
                continue
            # A resolved gateway renders the grid gate node, not a wild cell;
            # provider bounds only constrain wild identities.
            if not node["id"].startswith("wild:"):
                continue
            decoded = node["id"].split(":")
            self.assertLessEqual(int(decoded[2]), 223)
            self.assertLessEqual(int(decoded[3]), 223)

    @covers_requirement("webclient-local-map::the-wilderness-payload-legend-states-the-cell-scale-from-the-provider-constant")
    def test_wilderness_legend_appends_scale_note_after_the_states(self):
        self.gate.at_traverse(self.char1, self.east_gate)
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "wilderness")
        # The four state labels keep their exact order/positions, and the
        # scale note is the fifth entry (webclient-map-scale-legend D2).
        self.assertEqual(len(payload["legend"]), len(LEGEND_LABELS) + 1)
        self.assertEqual(payload["legend"][: len(LEGEND_LABELS)], list(LEGEND_LABELS))
        from world.maps import wilderness_provider

        scale_note = payload["legend"][len(LEGEND_LABELS)]
        self.assertIn(str(wilderness_provider.WILDERNESS_KM_PER_CELL), scale_note)
        # The extended legend stays inside the shared bounds the validators
        # pin (5 <= 16 entries, the note far below 256 code points); the
        # payload above already passed the exact Python validator in render.
        self.assertLessEqual(len(payload["legend"]), MAX_LEGEND)
        self.assertLessEqual(len(scale_note), MAX_STRING_CODE_POINTS)

    @covers_requirement("webclient-local-map::the-wilderness-payload-legend-states-the-cell-scale-from-the-provider-constant")
    def test_scale_note_figure_follows_the_provider_module_attribute(self):
        self.gate.at_traverse(self.char1, self.east_gate)
        with patch("world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL", 42):
            payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "wilderness")
        scale_note = payload["legend"][len(LEGEND_LABELS)]
        # The note is derived from the provider module attribute at
        # legend-assembly time -- never a duplicated literal.
        self.assertIn("42", scale_note)
        self.assertNotIn("10", scale_note)

    # test_visited_cells_beyond_adjacency_become_remembered pinned the old
    # "every previously-visited cell becomes remembered" meaning; it is
    # replaced by test_only_stood_on_gateways_are_remembered_in_the_wilderness
    # and its siblings in LocalMapWildernessGatewayTests below (local-map-
    # remembered-are-map-gateways wave 3), which need the full ``EvenniaTest``
    # fixture for ``enter_wilderness`` teleports rather than this class's
    # ``EvenniaTestCase`` base.

    @covers_requirement("webclient-local-map::wilderness-minimap-nodes-are-actionable")
    def test_wilderness_adjacent_nodes_carry_move_actions_with_canonical_destinations(self):
        from world.maps.wilderness_destination import resolve_wilderness_destination

        self.gate.at_traverse(self.char1, self.east_gate)
        room = self.char1.location
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(payload["layer"], "wilderness")
        current = payload["current_node"]
        moves = [node for node in payload["nodes"] if node["action"] is not None]
        # At the east gate's approach cell six directions are actionable:
        # the gate (w) plus five ordinary steps. The two diagonals facing the
        # anchor footprint (nw, sw) are refused by the provider and render
        # nothing (wilderness-anchor-footprint).
        self.assertEqual(len(moves), 6)
        for move in moves:
            self.assertEqual(move["action"]["kind"], "move")
            self.assertTrue(move["action"]["exit_ref"].isascii())
        directions = {
            edge["label"]: edge["destination"]
            for edge in payload["edges"]
            if edge["source"] == current
        }
        self.assertEqual(len(directions), 6)
        self.assertNotIn("nw", directions)
        self.assertNotIn("sw", directions)
        for direction, node_id in directions.items():
            node = next(node for node in payload["nodes"] if node["id"] == node_id)
            expected = resolve_wilderness_destination(room, direction)
            self.assertIsNotNone(expected, direction)
            self.assertEqual(node["action"]["destination"], expected, direction)
            edge = next(
                edge for edge in payload["edges"]
                if edge["source"] == current and edge["label"] == direction
            )
            self.assertTrue(edge["traversable"], direction)
        # The gateway west node advertises the grid arrival node, not a wild cell.
        west_node_id = directions["w"]
        west_node = next(node for node in payload["nodes"] if node["id"] == west_node_id)
        self.assertEqual(west_node["action"]["destination"], _t_grid_id(6, 3))

    @covers_requirement("webclient-local-map::wilderness-minimap-nodes-are-actionable")
    def test_locked_wilderness_node_stays_inert(self):
        self.gate.at_traverse(self.char1, self.east_gate)
        room = self.char1.location
        west_exit = [exit_obj for exit_obj in room.exits if exit_obj.key == "west"][0]
        west_exit.locks.add("traverse:false()")
        payload = self._registry().render("local_map", _context(self.char1))
        current = payload["current_node"]
        edge = next(
            edge for edge in payload["edges"]
            if edge["source"] == current and edge["label"] == "w"
        )
        node = next(node for node in payload["nodes"] if node["id"] == edge["destination"])
        self.assertIsNone(node["action"])
        self.assertFalse(edge["traversable"])
        # The other five actionable directions still carry move actions.
        self.assertEqual(
            len([node for node in payload["nodes"] if node["action"] is not None]),
            5,
        )

    def test_aliased_unrelated_exit_does_not_hijack_the_west_action(self):
        from typeclasses.exits import WildernessReturnExit

        self.gate.at_traverse(self.char1, self.east_gate)
        room = self.char1.location
        west_exit = [exit_obj for exit_obj in room.exits if exit_obj.key == "west"][0]
        # An unrelated exit aliased "w" must never replace the real west
        # exit in the move descriptor (direction mapping is key-based only).
        extra = create_object(
            WildernessReturnExit,
            key="密道",
            aliases=["w"],
            location=room,
            destination=room,
        )
        payload = self._registry().render("local_map", _context(self.char1))
        current = payload["current_node"]
        edge = next(
            edge for edge in payload["edges"]
            if edge["source"] == current and edge["label"] == "w"
        )
        node = next(node for node in payload["nodes"] if node["id"] == edge["destination"])
        self.assertEqual(node["action"]["exit_ref"], str(int(west_exit.id)))
        self.assertNotEqual(node["action"]["exit_ref"], str(int(extra.id)))


class LocalMapWildernessGatewayTests(EvenniaTest):
    """Remembered wilderness nodes are stood-on map gateways (waves 3, 5, 6).

    ``EvenniaTest`` (not ``EvenniaTestCase``): ``enter_wilderness`` teleports
    need the full-evennia fixture, same as ``LocalMapPerGateFootprintTests``.
    """

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()

    def _registry(self):
        return build_production_registry()

    def _at_wild(self, coordinates):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
        from world.maps.wilderness_provider import WILDERNESS_NAME

        entered = enter_wilderness(self.char1, coordinates=coordinates, name=WILDERNESS_NAME)
        self.assertTrue(entered, coordinates)
        record_arrival(self.char1)

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_only_stood_on_gateways_are_remembered_in_the_wilderness(self):
        # Stand on the east gate's approach cell (records it honestly, the
        # way arrival recording already works), then walk far enough away
        # that it drops out of the drawn 3x3 field of view.
        ex, ey = EAST_APPROACH
        self._at_wild((ex, ey))
        self._at_wild((ex + 10, ey))
        payload = self._registry().render("local_map", _context(self.char1))
        self.assertTrue(payload["available"])
        remembered = [node for node in payload["nodes"] if node["visibility"] == "remembered"]
        self.assertEqual(len(remembered), 1)
        node = remembered[0]
        self.assertEqual(node["id"], _t_wild_id(ex, ey))
        self.assertEqual((node["x"], node["y"]), (ex, ey))
        self.assertEqual(node["label"], _t_anchor_display(_T_MAP_KEY))
        self.assertTrue(node["landmark"])
        self.assertFalse(node["anchor"])
        self.assertIsNone(node["action"])

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_a_gateway_the_player_has_never_reached_is_absent(self):
        # The gate room (grid side) was visited, but the approach cell (wild
        # side) never was -- design D4: an honest "you don't know where in
        # the wilds this comes out."
        self.char1.location = self.east_gate
        record_arrival(self.char1)
        self._at_wild((73, 100))
        payload = self._registry().render("local_map", _context(self.char1))
        remembered_ids = {node["id"] for node in payload["nodes"] if node["visibility"] == "remembered"}
        self.assertEqual(remembered_ids, set())

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_walked_wilderness_ground_is_not_remembered(self):
        # Eight ordinary cells of one region -- the reported seven-chips
        # defect -- yields zero remembered nodes, not seven+ identical chips.
        for i in range(8):
            self._at_wild((70 + i, 103))
        self._at_wild((90, 103))
        payload = self._registry().render("local_map", _context(self.char1))
        remembered = [node for node in payload["nodes"] if node["visibility"] == "remembered"]
        self.assertEqual(remembered, [])

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_remembered_nodes_never_cross_coordinate_spaces(self):
        # A completed traversal records both ends (design D4): walking
        # through the gate leaves both the approach cell and the gate room
        # in the knowledge record.
        gate = [
            exit_obj for exit_obj in self.east_gate.exits if exit_obj.key == "荒野"
        ][0]
        self.char1.location = self.east_gate
        record_arrival(self.char1)
        gate.at_traverse(self.char1, self.east_gate)  # now at the approach
        ex, ey = EAST_APPROACH
        self._at_wild((ex + 10, ey))  # walk far away, keeping both memories

        wild_payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(wild_payload["layer"], "wilderness")
        remembered_wild = [
            node for node in wild_payload["nodes"] if node["visibility"] == "remembered"
        ]
        self.assertTrue(remembered_wild)
        for node in remembered_wild:
            self.assertTrue(node["id"].startswith("wild:"))
            _, _, x, y = node["id"].split(":")
            self.assertEqual((node["x"], node["y"]), (int(x), int(y)))
        self.assertNotIn(wild_payload["current_node"], {n["id"] for n in remembered_wild})

        self.char1.location = self.south_gate
        record_arrival(self.char1)
        grid_payload = self._registry().render("local_map", _context(self.char1))
        self.assertEqual(grid_payload["layer"], "grid")
        remembered_grid = [
            node for node in grid_payload["nodes"] if node["visibility"] == "remembered"
        ]
        self.assertTrue(remembered_grid)
        for node in remembered_grid:
            self.assertTrue(node["id"].startswith("grid:"))
            _, _, x, y = node["id"].split(":")
            self.assertEqual((node["x"], node["y"]), (int(x), int(y)))
        self.assertNotIn(grid_payload["current_node"], {n["id"] for n in remembered_grid})

    @covers_requirement("webclient-local-map::the-map-surfaces-state-a-place-name-only-where-it-adds-information")
    def test_an_in_view_gate_approach_cell_names_the_place_behind_it(self):
        # FLAGGED/STRIKEABLE wave 6 (design D8a): standing one cell from the
        # east gate's approach cell, that in-view neighbour is named for
        # what it leads to, not the region it stands on -- while its ID,
        # action, and edge stay exactly what they already were.
        ex, ey = EAST_APPROACH
        self._at_wild((ex + 1, ey))
        payload = self._registry().render("local_map", _context(self.char1))
        neighbor = next(
            node for node in payload["nodes"] if node["id"] == _t_wild_id(ex, ey)
        )
        self.assertEqual(neighbor["label"], _t_anchor_display(_T_MAP_KEY))
        self.assertEqual(neighbor["visibility"], "visible_unvisited")
        edge = next(
            edge
            for edge in payload["edges"]
            if edge["source"] == payload["current_node"] and edge["destination"] == neighbor["id"]
        )
        self.assertEqual(edge["label"], "w")

    @covers_requirement("webclient-local-map::the-map-surfaces-state-a-place-name-only-where-it-adds-information")
    def test_a_cell_in_a_different_region_still_says_so(self):
        # A same-region in-view neighbour still gets the plain region label
        # (only registered gate approach cells get the far-side name).
        self._at_wild((73, 100))
        payload = self._registry().render("local_map", _context(self.char1))
        neighbor = next(
            node for node in payload["nodes"] if node["id"] == "wild:elosern:74:100"
        )
        self.assertEqual(neighbor["label"], _t_region_display_for(73, 100))

    @covers_requirement("webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered")
    def test_two_wilderness_gateways_of_one_anchor_stay_distinguishable(self):
        # rubber-duck run 2: a single WildernessEntryPoint can register more
        # than one gate (the sample city already has two), so the anchor's
        # display name alone is NOT unique on the wilderness layer -- the
        # same collision-then-qualify rule the grid layer already had must
        # also apply here, or two genuinely different boundaries render the
        # identical anchor-name chip, reproducing this change's own target
        # defect.
        entry = _live_gateway_entry()
        south_approach = entry.approach_cell(entry.gate_for("n"))
        east_approach = entry.approach_cell(entry.gate_for("w"))
        self._at_wild(south_approach)  # the south gate's approach cell
        self._at_wild(east_approach)  # the east gate's approach cell
        self._at_wild((90, 100))  # far from both
        payload = self._registry().render("local_map", _context(self.char1))
        remembered = {
            node["id"]: node["label"]
            for node in payload["nodes"]
            if node["visibility"] == "remembered"
        }
        # Labels qualify by the gate room's own key (the shipped city gate
        # rooms), read from the live rooms -- never authored here.
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.assertEqual(
            remembered,
            {
                _t_wild_id(*south_approach): f"{_t_anchor_display(_T_MAP_KEY)}（{south_gate.key}）",
                _t_wild_id(*east_approach): f"{_t_anchor_display(_T_MAP_KEY)}（{east_gate.key}）",
            },
        )
        self.assertEqual(len(set(remembered.values())), 2)


if __name__ == "__main__":
    unittest.main()
