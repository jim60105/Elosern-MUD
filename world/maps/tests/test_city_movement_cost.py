"""Integration tests for wiring CostedXYZExit into the sample city (map-movement-clock)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import CostedXYZExit, Exit
from typeclasses.rooms import GridRoom, Room
from world.lore.sync import sync_all
from world.maps.altoria_capital import XYMAP_DATA_LIST
from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid
from world.maps.limbo import LIMBO_KEY
from world.rules.clock import CLOCK_YAML, get_world_clock

MOVE = CLOCK_YAML["command_defaults"]["move"]


class SampleCityCostedExitTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key="Room3", location=None)

    def _intra_city_exits(self):
        # all_family() counts CostedXYZExit (exact-typeclass all() filters them out).
        return [obj for obj in XYZExit.objects.all_family()]

    def test_fresh_spawn_every_intra_city_exit_is_costed_xyz_exit(self):
        sync_grid()
        exits = self._intra_city_exits()
        self.assertEqual(len(exits), 24)
        for exit_obj in exits:
            self.assertIsInstance(exit_obj, CostedXYZExit)

    def test_retype_path_updates_db_row_but_not_loaded_objects(self):
        # First sync WITHOUT the wildcard override: bare XYZExit instances.
        old_data = dict(XYMAP_DATA_LIST[0])
        old_data["prototypes"] = dict(XYMAP_DATA_LIST[0]["prototypes"])
        old_data["prototypes"].pop(("*", "*", "*"))
        with patch("world.maps.bootstrap.XYMAP_DATA_LIST", [old_data]):
            sync_grid()

        loaded = self._intra_city_exits()
        self.assertEqual(len(loaded), 24)
        for exit_obj in loaded:
            self.assertEqual(type(exit_obj).__name__, "XYZExit")

        # Second sync WITH the wildcard override.
        sync_grid()
        for exit_obj in loaded:
            self.assertEqual(
                exit_obj.db_typeclass_path, "typeclasses.exits.CostedXYZExit"
            )
            # The already-loaded Python object is not retyped in this process
            # (spawner.batch_update_objects_with_prototype writes the raw field;
            # it never calls swap_typeclass).
            self.assertEqual(type(exit_obj).__name__, "XYZExit")

        # A traversal through one of the still-loaded bare objects does not charge.
        exit_obj = loaded[0]
        traverser_location = exit_obj.location
        destination = exit_obj.destination
        before = get_world_clock().tick
        self.char1.location = traverser_location
        exit_obj.at_traverse(self.char1, destination)
        self.assertEqual(get_world_clock().tick, before)

    def test_fresh_intra_city_traversal_advances_clock_by_move(self):
        sync_grid()
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.char1.location = south_gate
        city_exit = [e for e in south_gate.exits if e.destination.key == "南大道"][0]
        self.assertIsInstance(city_exit, CostedXYZExit)
        before = get_world_clock().tick
        city_exit.at_traverse(self.char1, city_exit.destination)
        self.assertEqual(self.char1.location.key, "南大道")
        self.assertEqual(get_world_clock().tick, before + MOVE)

    @covers_requirement("sample-city-altoria::the-sample-city-s-twelve-intra-city-exits-spawn-as-costedxyzexit-not-the-bare-contrib-xyzexit", "world-clock::move-and-converse-command-default-time-costs-are-declared-as-rulebook-data-only")
    def test_limbo_bridge_exit_advances_clock_on_successful_traversal(self):
        sync_grid()
        limbo = self.room2
        limbo.key = LIMBO_KEY
        limbo.save()
        sync_grid()
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        from_each = [
            exit_obj
            for exit_obj in Exit.objects.all()
            if exit_obj.location == limbo and exit_obj.destination == south_gate
        ]
        self.assertEqual(len(from_each), 1)
        exit_obj = from_each[0]
        self.assertIsInstance(exit_obj, Exit)
        before = get_world_clock().tick
        self.char1.location = limbo
        exit_obj.at_traverse(self.char1, south_gate)
        self.assertIs(self.char1.location, south_gate)
        self.assertEqual(get_world_clock().tick, before + MOVE)
