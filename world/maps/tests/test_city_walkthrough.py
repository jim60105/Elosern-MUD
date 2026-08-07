"""End-to-end walkthrough of the capital_altoria sample city (map-anchor-grid)."""

from tools.spec_traceability import covers_requirement

from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import AnchorRoom, GridRoom, Room
from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid
from world.maps.limbo import LIMBO_KEY
from world.lore.sync import sync_all


class SampleCityWalkthroughTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room2.key = LIMBO_KEY
        self.room2.save()
        sync_all()
        sync_grid()

    def test_walk_from_limbo_to_central_plaza_and_render(self):
        limbo = self.room2
        south_gate = limbo.exits[0].destination
        self.assertEqual(south_gate.xyz, SOUTH_GATE_XYZ)
        self.assertEqual(type(south_gate).__name__, "GridRoom")

        south_street = next(
            exit_obj.destination
            for exit_obj in south_gate.exits
            if exit_obj.destination.key == "南大道"
        )
        plaza = next(
            exit_obj.destination
            for exit_obj in south_street.exits
            if exit_obj.destination.key == "中央廣場"
        )
        self.assertIsInstance(plaza, AnchorRoom)
        self.assertEqual(plaza.anchor_key, "capital_altoria")

        self.assertTrue(plaza.return_appearance(self.char1))

    @covers_requirement("sample-city-altoria::the-sample-city-connects-to-the-rest-of-the-world-through-exactly-one-bridging-exit")
    def test_every_room_is_reachable_from_south_gate(self):
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        seen = {south_gate}
        frontier = [south_gate]
        while frontier:
            current = frontier.pop()
            for exit_obj in current.exits:
                room = exit_obj.destination
                if room not in seen and isinstance(room, GridRoom):
                    seen.add(room)
                    frontier.append(room)

        self.assertEqual(len(seen), 13)
        self.assertEqual(len([room for room in seen if isinstance(room, AnchorRoom)]), 1)
