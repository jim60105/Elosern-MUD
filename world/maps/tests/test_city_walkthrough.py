"""Data-contract test: capital map walkability contract
End-to-end walkthrough of the capital_altoria sample city (map-anchor-grid)."""

from tools.spec_traceability import covers_requirement

from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import AnchorRoom, GridRoom
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.limbo import LIMBO_KEY
from world.maps.static_references import settlement_node_xyz
from world.lore.sync import sync_all
from world.tests.geography_fixture import (
    publish_shipped_geography,
    sync_test_settlements,
    sync_test_wilderness,
)

publish_shipped_geography()

SOUTH_GATE_XYZ = settlement_node_xyz(
    WILDERNESS_ENTRY_REGISTRY["capital_altoria"].gate_for("n").destination
)


class SampleCityWalkthroughTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room2.key = LIMBO_KEY
        self.room2.save()
        sync_all()
        sync_test_settlements((SOUTH_GATE_XYZ[2],))

    def test_walk_from_south_gate_to_central_plaza_and_render(self):
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.assertIsNotNone(south_gate)
        self.assertEqual(type(south_gate).__name__, "GridRoom")

        plaza = None
        seen, frontier = {south_gate}, [south_gate]
        while frontier and plaza is None:
            room = frontier.pop(0)
            for exit_obj in room.exits:
                nxt = exit_obj.destination
                if isinstance(nxt, AnchorRoom):
                    plaza = nxt
                    break
                if isinstance(nxt, GridRoom) and nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        self.assertIsInstance(plaza, AnchorRoom)
        self.assertEqual(plaza.anchor_key, "capital_altoria")

        self.assertTrue(plaza.return_appearance(self.char1))

    def test_every_room_is_reachable_from_south_gate(self):
        from world.maps.map_data import current

        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        seen = {south_gate}
        frontier = [south_gate]
        while frontier:
            room = frontier.pop()
            for exit_obj in room.exits:
                destination = exit_obj.destination
                if destination not in seen and isinstance(destination, GridRoom):
                    seen.add(destination)
                    frontier.append(destination)

        self.assertEqual(len(seen), len(current().settlements["capital_altoria"].nodes))
        self.assertEqual(len([room for room in seen if isinstance(room, AnchorRoom)]), 1)

    @covers_requirement(
        "sample-city-altoria::the-sample-city-connects-to-the-world-only-through-its-wilderness-gates"
    )
    def test_wilderness_gates_are_the_only_way_out_and_no_room_joins_limbo(self):
        from typeclasses.exits import WildernessGateExit
        from world.maps.map_data import current

        limbo = self.room2
        map_key = SOUTH_GATE_XYZ[2]
        sync_test_wilderness((map_key,), zone_keys=())
        document = current().settlements[map_key]
        entry = WILDERNESS_ENTRY_REGISTRY[document.location_ref]

        for gate in entry.gates:
            node_id = gate.destination.object_id
            room = GridRoom.objects.filter_xyz(xyz=settlement_node_xyz(gate.destination)).first()
            self.assertIsNotNone(room, node_id)
            city_exits = [e for e in room.exits if not isinstance(e, WildernessGateExit)]
            gate_exits = [e for e in room.exits if isinstance(e, WildernessGateExit)]
            authored = [road for road in document.roads if road.source == node_id]
            self.assertTrue(city_exits, f"{node_id} is a dead end")
            self.assertEqual(len(city_exits), len(authored), node_id)
            self.assertEqual(
                len(gate_exits),
                len([other for other in entry.gates if other.destination == gate.destination]),
                node_id,
            )

        city_rooms = list(GridRoom.objects.filter_xyz(xyz=("*", "*", map_key)))
        self.assertTrue(city_rooms)
        for room in city_rooms:
            self.assertEqual(
                [e for e in room.exits if e.destination == limbo], [], room.key
            )
        self.assertEqual(
            [e for e in limbo.exits if e.destination in city_rooms], []
        )
