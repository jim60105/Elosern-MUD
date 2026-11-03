"""Data-contract test: capital map walkability contract
End-to-end walkthrough of the capital_altoria sample city (map-anchor-grid)."""

from tools.spec_traceability import covers_requirement

from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import AnchorRoom, GridRoom, Room
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.limbo import LIMBO_KEY
from world.maps.static_references import settlement_node_xyz
from world.lore.sync import sync_all
from world.tests.geography_fixture import publish_shipped_geography, sync_test_settlements

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

    def test_walk_from_limbo_to_central_plaza_and_render(self):
        limbo = self.room2
        # The registry's rows bridge Limbo; pick the capital's by destination,
        # never by exit ordering.
        south_gate = next(
            exit_obj.destination for exit_obj in limbo.exits if exit_obj.destination.xyz == SOUTH_GATE_XYZ
        )
        self.assertEqual(south_gate.xyz, SOUTH_GATE_XYZ)
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

    @covers_requirement("sample-city-altoria::the-sample-city-connects-to-the-rest-of-the-world-through-exactly-one-bridging-exit")
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
