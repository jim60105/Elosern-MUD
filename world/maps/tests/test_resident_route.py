"""Behavior tests: the resident home ↔ village public node route resolver.

The settlement and its nodes come from the published authored map world at
runtime; the home is a synthetic tagged room with a patched exterior doorway.
No shipped node or room identity is named in this file.
"""

from unittest.mock import patch
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from elosern_map_core.references import settlement_node_ref

from typeclasses.exits import Exit
from typeclasses.rooms import Room
from world.maps import bootstrap, interiors
from world.maps.bootstrap import resolve_public_route
from world.maps.static_references import settlement_node_xyz
from world.tests.geography_fixture import publish_shipped_map_world, sync_test_settlements

publish_shipped_map_world()


class ResidentPublicRouteTests(EvenniaTest):
    """A resident home's doorway node is the village public room it walks to."""

    def setUp(self):
        super().setUp()
        published = interiors.current()
        exteriors = [row for row in published.exteriors.values() if row.settlement]
        self.settlement = exteriors[0].settlement
        self.doorway = next(
            row for row in exteriors if row.settlement == self.settlement
        )
        self.public_node = self.doorway.node
        sync_test_settlements((self.settlement,))
        bootstrap.sync_interiors()
        rooms = list(
            bootstrap.GridRoom.objects.filter_xyz(
                xyz=settlement_node_xyz(
                    settlement_node_ref(self.settlement, self.public_node)
                )
            )
        )
        self.assertEqual(len(rooms), 1)
        self.public = rooms[0]
        self.home = create_object(Room, key="t-resident-home", tags=["t_resident_home"])
        self.exits = {}
        for role, source, target in (
            ("home_public", self.home, self.public),
            ("public_home", self.public, self.home),
        ):
            self.exits[role] = create_object(
                Exit, key=role, location=source, destination=target
            )
        real_exterior_for = interiors.exterior_for

        def exterior_for(room_id):
            if room_id == "t_resident_home":
                return self.doorway
            return real_exterior_for(room_id)

        self.patch = patch.object(interiors, "exterior_for", side_effect=exterior_for)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    @covers_requirement(
        "npc-residents::residents-live-in-their-home-and-move-on-a-schedule"
    )
    def test_route_returns_home_public_and_its_own_frontage(self):
        route = resolve_public_route("t_resident_home", self.settlement, self.public_node)
        self.assertIs(route["home"], self.home)
        self.assertIs(route["public"], self.public)
        # A resident's doorstep and public space are the same room: the
        # interior's one exterior doorway is its only authored way out.
        self.assertIs(route["frontage"], self.public)

    def test_a_missing_scheduled_exit_rejects_by_name(self):
        self.exits["home_public"].delete()
        with self.assertRaises(ValueError) as caught:
            resolve_public_route("t_resident_home", self.settlement, self.public_node)
        self.assertIn("t_resident_home", str(caught.exception))
        self.assertIn("home->public", str(caught.exception))

    def test_a_missing_return_exit_rejects_by_name(self):
        self.exits["public_home"].delete()
        with self.assertRaises(ValueError) as caught:
            resolve_public_route("t_resident_home", self.settlement, self.public_node)
        self.assertIn("public->home", str(caught.exception))

    def test_a_home_doorway_on_another_node_rejects(self):
        with self.assertRaises(ValueError) as caught:
            resolve_public_route("t_resident_home", self.settlement, "t_other_node")
        self.assertIn("t_resident_home", str(caught.exception))
        self.assertIn("declared public node", str(caught.exception))

    def test_a_home_on_another_settlement_rejects(self):
        with self.assertRaises(ValueError) as caught:
            resolve_public_route("t_resident_home", "t_other_settlement", self.public_node)
        self.assertIn("t_other_settlement", str(caught.exception))

    def test_a_missing_home_rejects(self):
        with self.assertRaises(ValueError) as caught:
            resolve_public_route("t_missing_home", self.settlement, self.public_node)
        self.assertIn("t_missing_home", str(caught.exception))

    def test_public_node_resolves_to_one_materialized_room(self):
        self.assertIsNotNone(self.public)
        self.assertEqual(
            len(
                bootstrap.GridRoom.objects.filter_xyz(
                    xyz=settlement_node_xyz(
                        settlement_node_ref(self.settlement, self.public_node)
                    )
                )
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
