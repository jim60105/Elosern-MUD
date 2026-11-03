"""Full multi-lineage round trip: every exit lineage charges exactly its own
cost, and one deliberate failure charges nothing (map-movement-clock task 8)."""

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import GridRoom, Room, TerrainRoom
from world.lore.sync import sync_all
from world.tests.geography_fixture import sync_test_settlements, sync_test_wilderness
from world.maps.limbo import LIMBO_KEY
from world.maps.static_references import settlement_node_xyz
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import CLOCK_YAML, get_world_clock
from world.tests.geography_fixture import publish_shipped_geography


publish_shipped_geography()


MOVE = CLOCK_YAML["command_defaults"]["move"]

#: One open-ground wilderness step stays 1,200 s (no threshold crossed).
WILDERNESS_STEP_SECONDS = 1200


def _polyline_metres(points):
    """Authored length only; the charged seconds come from the clock, never from here."""
    import math

    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


class _ChargeAssertions:
    def assertChargedFor(self, delta, metres):
        """The spec's healthy settlement speed is 1.25 m/s with one upward rounding."""
        self.assertGreater(delta, 0)
        self.assertLess((delta - 1) * 1.25, metres)
        self.assertLessEqual(metres, delta * 1.25)


def _gate_approach_metres():
    from world.maps import geography
    from world.maps.map_data import current

    document = current().settlements[_ENTRY.anchor_key]
    cell_x, cell_y = geography.current().locations.locations[document.location_ref].cell
    anchor_x, anchor_y = document.local_anchor_m
    gate_x, gate_y = document.nodes[_EAST_GATE.destination.object_id].coordinate
    gate_world = (
        1000 * cell_x + 500 + gate_x - anchor_x,
        1000 * cell_y + 500 + gate_y - anchor_y,
    )
    approach = _ENTRY.approach_cell(_EAST_GATE)
    approach_world = (1000 * approach[0] + 500, 1000 * approach[1] + 500)
    return _polyline_metres([gate_world, approach_world])


def live_gateway_entry():
    """The settlement entry authoring both gateway faces (north + west).

    Several settlements can author both faces, so the pick is the lowest
    authored anchor key: deterministic, and the same entry on every call.
    """
    import importlib

    entries = getattr(
        importlib.import_module("world.lore.wilderness_entry"),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    ).values()
    candidates = sorted(
        (
            entry
            for entry in entries
            if entry.gate_for("n") is not None and entry.gate_for("w") is not None
        ),
        key=lambda entry: entry.anchor_key,
    )
    if not candidates:
        raise AssertionError("no wilderness entry authors both gateway faces")
    return candidates[0]


_ENTRY = live_gateway_entry()
_EAST_GATE = _ENTRY.gate_for("w")
EAST_GATE_XYZ = settlement_node_xyz(_EAST_GATE.destination)
SOUTH_GATE_XYZ = settlement_node_xyz(_ENTRY.gate_for("n").destination)


class MovementLineageRoundTripTests(_ChargeAssertions, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_all()
        declared = (_EAST_GATE.destination.map_id,)
        sync_test_settlements(declared)
        sync_test_wilderness(declared)
        self.limbo = search_object(LIMBO_KEY, exact=True)[0]
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.gate = [
            e for e in self.east_gate.exits if isinstance(e, WildernessGateExit)
        ][0]

    def test_every_lineage_charges_and_one_failure_charges_nothing(self):
        from collections import deque

        from typeclasses.exits import CostedXYZExit
        from world.maps.map_data import current

        # 1. Limbo -> South Gate via the bridging Exit (move).
        limbo_to_city = [
            e for e in self.limbo.exits if e.destination == self.south_gate
        ][0]
        self.assertIsInstance(limbo_to_city, Exit)
        self.char1.location = self.limbo
        previous = get_world_clock().tick
        limbo_to_city.at_traverse(self.char1, self.south_gate)
        self.assertEqual(get_world_clock().tick - previous, MOVE)
        self.assertIs(self.char1.location, self.south_gate)

        # 2. Across the city via CostedXYZExit links, along the authored road
        #    route from the South Gate to the East Gate. Each leg is checked
        #    against its own authored polyline, never a copied duration.
        document = current().settlements[_ENTRY.anchor_key]
        frontier = deque([(self.south_gate, [])])
        seen, route = {self.south_gate}, None
        while frontier and route is None:
            room, path = frontier.popleft()
            if room.pk == self.east_gate.pk:
                route = path
                break
            for exit_obj in room.exits:
                if not isinstance(exit_obj, CostedXYZExit):
                    continue
                destination = exit_obj.destination
                if destination not in seen:
                    seen.add(destination)
                    frontier.append((destination, path + [exit_obj]))
        self.assertTrue(route, "the authored roads must connect both gates")
        for exit_obj in route:
            road = next(
                road
                for road in document.roads
                if road.source == exit_obj.location.sparse_node_id
                and road.destination == exit_obj.destination.sparse_node_id
            )
            points = [
                document.nodes[road.source].coordinate,
                *[(bend.x_m, bend.y_m) for bend in road.bends],
                document.nodes[road.destination].coordinate,
            ]
            previous = get_world_clock().tick
            exit_obj.at_traverse(self.char1, exit_obj.destination)
            self.assertChargedFor(
                get_world_clock().tick - previous, _polyline_metres(points)
            )
            self.assertIs(self.char1.location, exit_obj.destination)
        self.assertIs(self.char1.location, self.east_gate)

        # 3. Into the wilderness through WildernessGateExit (wilderness_move),
        #    two intermediate steps, and back via WildernessReturnExit's
        #    special-cased return (3 more wilderness_move legs).
        previous = get_world_clock().tick
        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertChargedFor(
            get_world_clock().tick - previous, _gate_approach_metres()
        )
        self.assertIsInstance(self.char1.location, TerrainRoom)
        entry_xy = self.char1.location.coordinates
        for direction in ("east", "west"):
            exit_obj = [e for e in self.char1.location.exits if e.key == direction][0]
            previous = get_world_clock().tick
            exit_obj.at_traverse(self.char1, self.char1.location)
            self.assertEqual(
                get_world_clock().tick - previous, WILDERNESS_STEP_SECONDS
            )
        self.assertEqual(self.char1.location.coordinates, entry_xy)
        exit_obj = [e for e in self.char1.location.exits if e.key == "west"][0]
        previous = get_world_clock().tick
        exit_obj.at_traverse(self.char1, self.char1.location)
        self.assertChargedFor(
            get_world_clock().tick - previous, _gate_approach_metres()
        )
        self.assertIs(self.char1.location, self.east_gate)

        # 4. A synthetic origin/return Exit pair, mirroring change 14's
        #    spawn_instance_room() call shape (2 move legs).
        origin, _ = GridRoom.create(key="instance_origin", xyz=(99, 99, "roundtrip"))
        target, _ = GridRoom.create(key="instance_target", xyz=(100, 99, "roundtrip"))
        instance_enter, _ = Exit.create(key="door", location=origin, destination=target)
        instance_return, _ = Exit.create(
            key="return", location=target, destination=origin
        )
        self.char1.location = origin
        previous = get_world_clock().tick
        instance_enter.at_traverse(self.char1, target)
        self.assertEqual(get_world_clock().tick - previous, MOVE)
        self.assertIs(self.char1.location, target)
        previous = get_world_clock().tick
        instance_return.at_traverse(self.char1, origin)
        self.assertEqual(get_world_clock().tick - previous, MOVE)
        self.assertIs(self.char1.location, origin)

        # 5. A deliberately failed traversal (locked exit) contributes 0.
        from evennia.objects.objects import ExitCommand

        locked, _ = Exit.create(key="locked", location=origin, destination=target)
        locked.locks.add("traverse:false()")
        command = ExitCommand()
        command.obj = locked
        command.caller = self.char1
        previous = get_world_clock().tick
        command.func()
        self.assertEqual(get_world_clock().tick - previous, 0)
        self.assertIs(self.char1.location, origin)
