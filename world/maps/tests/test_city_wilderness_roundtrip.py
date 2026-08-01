"""Full-suite round trip: lore sync, grid city, wilderness, and back (map-wilderness)."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import WildernessGateExit
from typeclasses.rooms import GridRoom, Room, TerrainRoom
from world.lore.sync import sync_all
from world.maps.bootstrap import NORTH_GATE_XYZ, sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME, terrain_description
from world.rules.clock import get_world_clock


class CityWildernessRoundTripTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key="Limbo", location=None)
        sync_all()
        sync_grid()
        sync_wilderness()
        self.north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
        self.gate = [e for e in self.north_gate.exits if isinstance(e, WildernessGateExit)][0]

    def _exit(self, direction):
        return [e for e in self.char1.location.exits if e.key == direction][0]

    def test_full_round_trip_leaves_no_leaked_bookkeeping(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        before = get_world_clock().tick

        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        self.assertEqual(self.char1.location.coordinates, (60, 100))
        entry_room = self.char1.location

        # One east step crosses from western_hills_valleys into the central
        # mountain band, so the region and description change.
        self._exit("east").at_traverse(self.char1, self.char1.location)
        self.assertEqual(self.char1.location.coordinates, (61, 100))
        self.assertEqual(
            self.char1.location.ndb.active_desc,
            terrain_description(61, 100),
        )

        # Return west to the entry coordinate, then south to the North Gate.
        self._exit("west").at_traverse(self.char1, self.char1.location)
        self._exit("south").at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, self.north_gate)

        # 1 entry + 1 east + 1 west + 1 return = 4 legs.
        self.assertEqual(get_world_clock().tick, before + 4 * 9000)
        self.assertEqual(dict(script.db.itemcoordinates), {})
        retained = list(script.db.rooms.values())
        self.assertIn(entry_room, retained or script.db.unused_rooms)

    def test_wilderness_room_renders_via_return_appearance(self):
        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertTrue(self.char1.location.return_appearance(self.char1))
        self.assertEqual(self.char1.location.location_name, "西部丘陵與谷地")

    def test_intra_city_grid_traversal_advances_clock_by_move(self):
        # map-movement-clock: intra-city exits are CostedXYZExit and each
        # successful step charges the ordinary move cost -- the wilderness-
        # gateway "grid traversal stays unwired" posture was deliberately
        # retired by that change.
        from typeclasses.exits import CostedXYZExit
        from world.rules.clock import CLOCK_YAML

        south_gate = GridRoom.objects.filter_xyz(xyz=(2, 0, "capital_altoria")).first()
        self.char1.location = south_gate
        city_exit = [e for e in south_gate.exits if e.destination.key == "南大道"][0]
        self.assertIsInstance(city_exit, CostedXYZExit)
        before = get_world_clock().tick
        city_exit.at_traverse(self.char1, city_exit.destination)
        self.assertEqual(self.char1.location.key, "南大道")
        self.assertEqual(
            get_world_clock().tick,
            before + CLOCK_YAML["command_defaults"]["move"],
        )
