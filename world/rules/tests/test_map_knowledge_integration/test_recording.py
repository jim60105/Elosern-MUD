"""Map-knowledge journeys (recording)."""

from ._support import _MapKnowledgeFixture, _grid_node, _node_ids
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from evennia.utils.create import create_object
from typeclasses.exits import Exit
from typeclasses.rooms import GridRoom, Room, TerrainRoom
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import parse_knowledge


class MapKnowledgeRecordingTests(_MapKnowledgeFixture):
    """One map-knowledge recording rule per journey."""


    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_grid_traversal_records_destination_grid_node(self):
        self.char1.location = self.south_gate
        # Any inter-grid exit from the south-gate room: the seam must record the
        # node derived from the room actually arrived at, whatever the bootstrapped
        # street is named or where it sits.
        city_exit = [e for e in self.south_gate.exits if isinstance(e.destination, GridRoom)][0]
        destination = city_exit.destination
        city_exit.at_traverse(self.char1, destination)
        self.assertIs(self.char1.location, destination)
        self.assertIn(_grid_node(destination), _node_ids(self.char1))


    def test_plain_exit_records_room_node(self):
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        self.char1.location = self.room1
        exit_obj.at_traverse(self.char1, self.room2)
        self.assertIn(f"room:{self.room2.id}", _node_ids(self.char1))


    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_limbo_bridge_records_grid_node(self):
        limbo = create_object(Room, key="LimboBridge", location=None)
        south_gate = GridRoom.objects.filter_xyz(xyz=self.south_gate_xyz).first()
        bridge = create_object(
            Exit,
            key=self.gate_row.exit_key,
            aliases=list(self.gate_row.exit_aliases),
            location=limbo,
            destination=south_gate,
        )
        self.char1.location = limbo
        bridge.at_traverse(self.char1, south_gate)
        self.assertIn(_grid_node(south_gate), _node_ids(self.char1))


    def test_instance_doorway_records_room_node(self):
        from world.maps.instance import spawn_instance_room

        room = spawn_instance_room(
            self.room1,
            {"prototype_parent": "instance_room", "key": "cave"},
            exit_key="in",
            return_key="out",
            ttl_seconds=10,
        )
        door = [e for e in self.room1.exits if e.key == "in"][0]
        self.char1.location = self.room1
        door.at_traverse(self.char1, room)
        self.assertIs(self.char1.location, room)
        self.assertIn(f"room:{room.id}", _node_ids(self.char1))


    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_gate_entry_records_wilderness_node(self):
        before = get_world_clock().tick
        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        self.assertEqual(self.char1.location.coordinates, self.entry_xy)
        expected = f"wild:{self.wild}:{self.entry_xy[0]}:{self.entry_xy[1]}"
        self.assertIn(expected, _node_ids(self.char1))
        self.assertGreater(get_world_clock().tick, before)


    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_ordinary_wilderness_step_records_wilderness_node(self):
        self.gate.at_traverse(self.char1, self.east_gate)
        start = self.char1.location.coordinates
        self._exit("east").at_traverse(self.char1, self.char1.location)
        expected = f"wild:{self.wild}:{start[0] + 1}:{start[1]}"
        self.assertIn(expected, _node_ids(self.char1))


    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_wilderness_arrival_records_the_ground_radius_at_the_final_tick(self):
        # The sight boundary is injected, so the assertion establishes the
        # arrival seam's use of the committed cell radius without pinning the
        # shipped rulebook numbers.
        # Two committed consumers read the one ground-radius rule on this
        # traversal: the arrival seam below (this test's subject) and the travel
        # notice collector's live-sight hostile check
        # (wilderness-travel-log-ui), which reads the same disc for its own
        # comparison. The travel consumer is stubbed so the single-call claim
        # keeps naming the arrival seam alone.
        with (
            patch("world.rules.travel_events._hostiles_in_sight", return_value=()),
            patch("world.rules.sight.ground_radius_at", return_value=5) as radius,
        ):
            self.gate.at_traverse(self.char1, self.east_gate)
        radius.assert_called_once()
        self.assertEqual(radius.call_args.args[0], self.entry_xy)
        tick = get_world_clock().tick
        visits = {visit.node_id: visit for visit in parse_knowledge(self.char1)}
        visit = visits[f"wild:{self.wild}:{self.entry_xy[0]}:{self.entry_xy[1]}"]
        self.assertEqual((visit.last_seen_tick, visit.sight), (tick, 5))

        # A non-wilderness arrival keeps the schema-2 pair and adds no sight.
        self.char1.location = self.room1
        exit_obj = create_object(Exit, key="bare", location=self.room1, destination=self.room2)
        exit_obj.at_traverse(self.char1, self.room2)
        rooms = {visit.node_id: visit for visit in parse_knowledge(self.char1)}
        self.assertEqual(rooms[f"room:{self.room2.id}"].sight, 0)


    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_west_return_records_grid_node(self):
        self.gate.at_traverse(self.char1, self.east_gate)
        self._exit("west").at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, self.east_gate)
        self.assertIn(_grid_node(self.east_gate), _node_ids(self.char1))

