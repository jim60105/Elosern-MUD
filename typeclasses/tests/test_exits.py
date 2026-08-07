"""Integration tests for the wilderness gateway exits (map-wilderness, map-movement-clock)."""

from tools.spec_traceability import covers_requirement

import inspect

from evennia.contrib.grid.wilderness.wilderness import WildernessExit
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import WildernessGateExit, WildernessReturnExit
from typeclasses.rooms import GridRoom, Room
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import get_world_clock

NORTH_GATE_XYZ = (2, 4, "capital_altoria")
ENTRY_XY = WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy


class WildernessGatewayExitTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
        self.gate = [e for e in self.north_gate.exits if isinstance(e, WildernessGateExit)][0]

    def _exit(self, direction):
        return [e for e in self.char1.location.exits if e.key == direction][0]

    def _tick(self):
        return get_world_clock().tick

    @covers_requirement("wilderness-gateway::wildernessgateexit-moves-a-traversing-object-from-a-grid-room-into-the-wilderness")
    def test_gate_exit_places_traverser_at_entry_coordinate_and_advances_clock(self):
        before = self._tick()
        self.gate.at_traverse(self.char1, self.north_gate)
        from typeclasses.rooms import TerrainRoom

        self.assertIsInstance(self.char1.location, TerrainRoom)
        self.assertEqual(self.char1.location.coordinates, ENTRY_XY)
        self.assertEqual(self._tick(), before + 9000)

    def test_failed_enter_wilderness_does_not_advance_clock(self):
        from unittest.mock import patch

        original_location = self.char1.location
        before = self._tick()
        with patch("typeclasses.exits.enter_wilderness", return_value=False):
            result = self.gate.at_traverse(self.char1, self.north_gate)
        self.assertFalse(result)
        self.assertIs(self.char1.location, original_location)
        self.assertEqual(self._tick(), before)

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-uses-terrainroom-and-wildernessreturnexit")
    def test_eight_directional_exits_are_wilderness_return_exits(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        for exit_obj in self.char1.location.exits:
            self.assertIsInstance(exit_obj, WildernessReturnExit)

    @covers_requirement("wilderness-gateway::wildernessreturnexit-routes-exactly-one-registered-coordinate-and-direction-pair-back-to-the-grid")
    def test_south_from_entry_returns_to_exact_grid_room(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        before = self._tick()
        self._exit("south").at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, self.north_gate)
        self.assertEqual(self._tick(), before + 9000)

    def test_intermediate_steps_each_advance_clock_by_one_wilderness_move(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        expected = self._tick()
        for _ in range(3):
            expected += 9000
            self._exit("east").at_traverse(self.char1, self.char1.location)
            self.assertEqual(self._tick(), expected)

    def test_eight_leg_round_trip_advances_clock_by_exactly_72000(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript
        from typeclasses.monsters import Monster

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        before = self._tick()
        self.gate.at_traverse(self.char1, self.north_gate)
        for _ in range(3):
            self._exit("east").at_traverse(self.char1, self.char1.location)
        for _ in range(3):
            self._exit("west").at_traverse(self.char1, self.char1.location)
        self._exit("south").at_traverse(self.char1, self.char1.location)
        self.assertEqual(self._tick(), before + 8 * 9000)
        self.assertIs(self.char1.location, self.north_gate)
        # The return-exit cleanup drops the player, but each visited coordinate
        # keeps its deterministic population monster (wilderness-monster-
        # population); the leak-check intent -- no player bookkeeping left
        # behind -- is preserved.
        coordinates = dict(script.db.itemcoordinates)
        self.assertNotIn(self.char1, coordinates)
        self.assertTrue(
            all(isinstance(obj, Monster) for obj in coordinates),
            "only population monsters may remain registered",
        )

    def test_other_directions_route_as_ordinary_wilderness_exit(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        start = self.char1.location.coordinates
        self._exit("east").at_traverse(self.char1, self.char1.location)
        self.assertEqual(self.char1.location.coordinates, (start[0] + 1, start[1]))

    def test_vetoed_at_pre_move_blocks_gate_traversal_entirely(self):
        original_location = self.char1.location
        before = self._tick()
        self.char1.at_pre_move = lambda *a, **k: False
        result = self.gate.at_traverse(self.char1, self.north_gate)
        self.assertFalse(result)
        self.assertIs(self.char1.location, original_location)
        self.assertEqual(self._tick(), before)

    def test_vacated_room_is_not_orphaned_and_is_reused_on_reentry(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript
        from typeclasses.monsters import Monster

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.gate.at_traverse(self.char1, self.north_gate)
        first_room = self.char1.location
        self._exit("south").at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, self.north_gate)
        # The player's bookkeeping is cleaned up on the return exit; only the
        # deterministic population monster stays registered (wilderness-
        # monster-population).
        coordinates = dict(script.db.itemcoordinates)
        self.assertNotIn(self.char1, coordinates)
        self.assertTrue(
            all(isinstance(obj, Monster) for obj in coordinates)
            and len(coordinates) == 1,
            "only the entry population monster may remain registered",
        )
        # The vacated room is either in unused_rooms or retained in db.rooms,
        # never orphaned -- and re-entry reuses the same room object.
        retained = list(script.db.rooms.values())
        in_pool = first_room in script.db.unused_rooms
        in_retained = first_room in retained
        self.assertTrue(in_pool or in_retained, "vacated room was orphaned")
        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIs(self.char1.location, first_room)

    def test_failed_return_to_missing_gate_does_not_advance_clock(self):
        from unittest.mock import patch

        self.gate.at_traverse(self.char1, self.north_gate)
        before = self._tick()
        wilderness_location = self.char1.location
        # Simulate a vanished gate (the true misconfiguration this guards
        # against) by patching _grid_room_for_anchor to return None.
        from typeclasses import exits as exits_module

        with patch.object(exits_module, "_grid_room_for_anchor", return_value=None):
            result = self._exit("south").at_traverse(
                self.char1, self.char1.location
            )
        self.assertFalse(result)
        self.assertIs(self.char1.location, wilderness_location)
        self.assertEqual(self._tick(), before)

    def test_vetoed_return_move_does_not_advance_clock(self):
        self.gate.at_traverse(self.char1, self.north_gate)
        before = self._tick()
        wilderness_location = self.char1.location
        self.char1.at_pre_move = lambda *a, **k: False
        result = self._exit("south").at_traverse(self.char1, self.char1.location)
        self.assertFalse(result)
        self.assertIs(self.char1.location, wilderness_location)
        self.assertEqual(self._tick(), before)


class WildernessClockChargeSourceTests(EvenniaTest):
    """Source-inspection: the wilderness wiring goes through charge_movement
    (map-movement-clock task 5.4), never an inline get_world_clock().advance."""

    def test_gate_exit_uses_charge_movement_not_inline_advance(self):
        source = inspect.getsource(WildernessGateExit.at_traverse)
        self.assertIn("charge_movement(traversing_object, \"wilderness_move\")", source)
        self.assertNotIn("get_world_clock().advance", source)

    def test_return_exit_both_branches_use_charge_movement(self):
        source = inspect.getsource(WildernessReturnExit.at_traverse)
        self.assertEqual(
            source.count("charge_movement(traversing_object, \"wilderness_move\")"),
            2,
        )
        self.assertNotIn("get_world_clock().advance", source)
