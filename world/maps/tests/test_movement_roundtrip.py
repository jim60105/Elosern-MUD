"""Full multi-lineage round trip: every exit lineage charges exactly its own
cost, and one deliberate failure charges nothing (map-movement-clock task 8)."""

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import GridRoom, Room, TerrainRoom
from world.lore.sync import sync_all
from world.maps.bootstrap import NORTH_GATE_XYZ, SOUTH_GATE_XYZ, sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import CLOCK_YAML, get_world_clock

MOVE = CLOCK_YAML["command_defaults"]["move"]
WILD = CLOCK_YAML["command_defaults"]["wilderness_move"]


class MovementLineageRoundTripTests(EvenniaTest):
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
        self.limbo = search_object("Limbo", exact=True)[0]
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
        self.gate = [
            e for e in self.north_gate.exits if isinstance(e, WildernessGateExit)
        ][0]

    def test_every_lineage_charges_and_one_failure_charges_nothing(self):
        before = get_world_clock().tick

        # 1. Limbo -> South Gate via the bridging Exit (move).
        limbo_to_city = [
            e for e in self.limbo.exits if e.destination == self.south_gate
        ][0]
        self.assertIsInstance(limbo_to_city, Exit)
        self.char1.location = self.limbo
        limbo_to_city.at_traverse(self.char1, self.south_gate)
        self.assertIs(self.char1.location, self.south_gate)

        # 2. Across the city via CostedXYZExit links: South Gate -> 南大道 ->
        #    中央廣場 -> 北大道 -> North Gate (4 move legs).
        path = ["南大道", "中央廣場", "北大道", "北門"]
        for expected_key in path:
            exit_obj = [
                e
                for e in self.char1.location.exits
                if e.destination.key == expected_key
            ][0]
            exit_obj.at_traverse(self.char1, exit_obj.destination)
            self.assertEqual(self.char1.location.key, expected_key)
        self.assertIs(self.char1.location, self.north_gate)

        # 3. Into the wilderness through WildernessGateExit (wilderness_move),
        #    two intermediate steps, and back via WildernessReturnExit's
        #    special-cased return (3 more wilderness_move legs).
        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        entry_xy = self.char1.location.coordinates
        for direction in ("east", "west"):
            exit_obj = [e for e in self.char1.location.exits if e.key == direction][0]
            exit_obj.at_traverse(self.char1, self.char1.location)
        self.assertEqual(self.char1.location.coordinates, entry_xy)
        exit_obj = [e for e in self.char1.location.exits if e.key == "south"][0]
        exit_obj.at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, self.north_gate)

        # 4. A synthetic origin/return Exit pair, mirroring change 14's
        #    spawn_instance_room() call shape (2 move legs).
        origin, _ = GridRoom.create(key="instance_origin", xyz=(99, 99, "roundtrip"))
        target, _ = GridRoom.create(key="instance_target", xyz=(100, 99, "roundtrip"))
        instance_enter, _ = Exit.create(key="door", location=origin, destination=target)
        instance_return, _ = Exit.create(
            key="return", location=target, destination=origin
        )
        self.char1.location = origin
        instance_enter.at_traverse(self.char1, target)
        self.assertIs(self.char1.location, target)
        instance_return.at_traverse(self.char1, origin)
        self.assertIs(self.char1.location, origin)

        # 5. A deliberately failed traversal (locked exit) contributes 0.
        from evennia.objects.objects import ExitCommand

        locked, _ = Exit.create(key="locked", location=origin, destination=target)
        locked.locks.add("traverse:false()")
        command = ExitCommand()
        command.obj = locked
        command.caller = self.char1
        command.func()
        self.assertIs(self.char1.location, origin)

        grid_legs = 1 + 4 + 2  # Limbo bridge + 4 city links + instance pair
        wild_legs = 1 + 2 + 1  # entry + east + west + return
        self.assertEqual(
            get_world_clock().tick,
            before + grid_legs * MOVE + wild_legs * WILD,
        )
