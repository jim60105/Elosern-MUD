"""Integration tests for registry-driven permanent service interiors (task 3.2, sample-city spec).

Interiors are created by iterating ``PLACE_REGISTRY`` grouped by settlement
(place-driven-service-sync task 1.x): each place yields one tagged room in its
settlement's coordinate space, two doorway exits to its exterior, and an
authored description re-applied in place on every sync. A place whose exterior
cannot be resolved warns naming the row and is skipped alone.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.exits import Exit
from typeclasses.rooms import GridRoom, Room
from world.lore.settlements.places import PLACE_REGISTRY
from world.lore.settlements.settlements import SETTLEMENT_REGISTRY
from world.maps.bootstrap import (
    sync_grid,
    sync_service_interiors,
)

GUILD_HALL = PLACE_REGISTRY["altoria_guild_hall"]
GENERAL_STORE = PLACE_REGISTRY["altoria_general_store"]


class ServiceInteriorTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()

    def _count_grid_rooms(self):
        return GridRoom.objects.all_family().count()

    def _interior(self, place):
        rooms = search_object_by_tag(place.key)
        return rooms[0] if rooms else None

    def _exterior(self, place):
        zcoord = SETTLEMENT_REGISTRY[place.settlement_key].zcoord
        return GridRoom.objects.filter_xyz(xyz=(*place.exterior_xy, zcoord)).first()

    def test_fresh_sync_creates_one_permanent_interior_per_place(self):
        sync_service_interiors()
        for place in PLACE_REGISTRY.values():
            room = self._interior(place)
            self.assertIsNotNone(room, place.key)
            self.assertIsInstance(room, Room)
            self.assertEqual(room.key, place.room_name_zh)
            self.assertIsNone(room.db.expire_tick)
            self.assertEqual(room.location, None)
            self.assertEqual(room.db.desc, place.room_desc_zh)

    def test_interiors_have_bidirectional_doorways_to_documented_exteriors(self):
        sync_service_interiors()
        for place in PLACE_REGISTRY.values():
            interior = self._interior(place)
            exterior = self._exterior(place)
            self.assertIn(
                interior, {exit_obj.destination for exit_obj in exterior.exits}
            )
            self.assertIn(
                exterior, {exit_obj.destination for exit_obj in interior.exits}
            )

    @covers_requirement("sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached")
    def test_grid_topology_is_unchanged(self):
        sync_service_interiors()
        # Two settlements are spawned (13 capital + 6 village nodes); the
        # interiors are still not xyzgrid nodes.
        self.assertEqual(self._count_grid_rooms(), 19)

    def test_interiors_are_not_xyzgrid_nodes(self):
        sync_service_interiors()
        grid_keys = {room.key for room in GridRoom.objects.all_family()}
        for place in PLACE_REGISTRY.values():
            self.assertNotIn(place.room_name_zh, grid_keys)

    @covers_requirement("sample-city-altoria::altoria-service-content-synchronizes-idempotently-without-resetting-live-state")
    @covers_requirement(
        "place-driven-service-sync::interiors-are-created-by-iterating-the-place-registry"
    )
    def test_repeated_sync_reuses_tags_reapplies_desc_and_duplicates_no_doorway(self):
        sync_service_interiors()
        first = {
            place.key: (room.pk, sorted(e.key for e in room.exits))
            for place in PLACE_REGISTRY.values()
            for room in search_object_by_tag(place.key)
        }
        room_count = Room.objects.all_family().count()
        exit_count = Exit.objects.all().count()
        # Drift the authored description the way a legacy database has it:
        # the next sync must re-apply the authored text in place.
        for place in PLACE_REGISTRY.values():
            room = search_object_by_tag(place.key)[0]
            room.db.desc = "drifted description"
            room.save()

        sync_service_interiors()

        second = {
            place.key: (room.pk, sorted(e.key for e in room.exits))
            for place in PLACE_REGISTRY.values()
            for room in search_object_by_tag(place.key)
        }
        self.assertEqual(first, second)
        self.assertEqual(Room.objects.all_family().count(), room_count)
        self.assertEqual(Exit.objects.all().count(), exit_count)
        for place in PLACE_REGISTRY.values():
            room = search_object_by_tag(place.key)[0]
            self.assertEqual(room.db.desc, place.room_desc_zh)

    def test_doorway_keys_and_aliases_are_the_places_authored_pair(self):
        sync_service_interiors()
        for place in PLACE_REGISTRY.values():
            interior = self._interior(place)
            exterior = self._exterior(place)
            forward = [
                exit_obj
                for exit_obj in exterior.exits
                if exit_obj.destination == interior
            ]
            self.assertEqual(len(forward), 1)
            self.assertEqual(forward[0].key, place.doorway_key_zh)
            self.assertEqual(set(forward[0].aliases.all()), set(place.doorway_aliases))
            back = [
                exit_obj
                for exit_obj in interior.exits
                if exit_obj.destination == exterior
            ]
            self.assertEqual(len(back), 1)
            self.assertEqual(back[0].key, "外")

    def test_interior_reachable_from_and_back_to_exterior(self):
        sync_service_interiors()
        for place in PLACE_REGISTRY.values():
            interior = self._interior(place)
            exterior = self._exterior(place)
            self.assertTrue(
                interior.access(exterior, "traverse", default=True),
                place.key,
            )
            self.assertIn(exterior, {e.destination for e in interior.exits})

    @covers_requirement("guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster")
    @covers_requirement(
        "place-driven-service-sync::interiors-are-created-by-iterating-the-place-registry"
    )
    def test_one_unresolvable_exterior_warns_and_skips_only_that_place(self):
        # The extra place's exterior coordinate resolves to no grid room
        # (capital map has no node there); the two shipped places must still
        # synchronize, exactly the warn-and-skip contract.
        bad_place = replace(
            GENERAL_STORE,
            key="t_missing_exterior",
            room_name_zh="測試無外景點",
            room_desc_zh="No exterior backs this place.",
            exterior_xy=(9, 9),
        )
        with patch("world.maps.bootstrap.log_warn") as warned:
            with patch.dict(PLACE_REGISTRY, {"t_missing_exterior": bad_place}, clear=False):
                sync_service_interiors()
        events = [
            call for call in warned.call_args_list
            if call.args and call.args[0] == "bootstrap_service_exterior_missing"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kwargs["context"]["place"], "t_missing_exterior")
        self.assertEqual(events[0].kwargs["context"]["exterior_xyz"], (9, 9, "capital_altoria"))
        self.assertEqual(events[0].kwargs["context"]["action"], "skip_place")
        self.assertIsNone(self._interior(bad_place))
        self.assertIsNotNone(self._interior(GUILD_HALL))
        self.assertIsNotNone(self._interior(GENERAL_STORE))


if __name__ == "__main__":
    import unittest

    unittest.main()