"""Integration tests for permanent Altoria service interiors (task 3.2, sample-city spec)."""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.exits import Exit
from typeclasses.rooms import GridRoom, Room
from world.maps.altoria_capital import XYMAP_DATA
from world.maps.bootstrap import (
    GENERAL_STORE_EXTERIOR_XYZ,
    GENERAL_STORE_TAG,
    GUILD_HALL_EXTERIOR_XYZ,
    GUILD_HALL_TAG,
    sync_grid,
    sync_service_interiors,
)

SOUTH_GATE_XYZ = (2, 0, "capital_altoria")


class ServiceInteriorTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        self.grid = sync_grid()
        self.grid = None

    def _count_grid_rooms(self):
        return GridRoom.objects.all_family().count()

    def _interior(self, tag):
        rooms = search_object_by_tag(tag)
        return rooms[0] if rooms else None

    def test_fresh_sync_creates_two_permanent_interiors(self):
        sync_service_interiors()
        guild_hall = self._interior(GUILD_HALL_TAG)
        general_store = self._interior(GENERAL_STORE_TAG)
        self.assertIsNotNone(guild_hall)
        self.assertIsNotNone(general_store)
        for room in (guild_hall, general_store):
            self.assertIsInstance(room, Room)
            self.assertIsNone(room.db.expire_tick)
            self.assertEqual(room.location, None)

    def test_interiors_have_bidirectional_doorways_to_documented_exteriors(self):
        sync_service_interiors()
        guild_hall = self._interior(GUILD_HALL_TAG)
        general_store = self._interior(GENERAL_STORE_TAG)
        guild_exterior = GridRoom.objects.filter_xyz(xyz=GUILD_HALL_EXTERIOR_XYZ).first()
        store_exterior = GridRoom.objects.filter_xyz(xyz=GENERAL_STORE_EXTERIOR_XYZ).first()

        self.assertIn(guild_hall, {exit_obj.destination for exit_obj in guild_exterior.exits})
        self.assertIn(general_store, {exit_obj.destination for exit_obj in store_exterior.exits})
        self.assertIn(guild_exterior, {exit_obj.destination for exit_obj in guild_hall.exits})
        self.assertIn(store_exterior, {exit_obj.destination for exit_obj in general_store.exits})

    @covers_requirement("sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached")
    def test_grid_topology_is_unchanged(self):
        sync_service_interiors()
        self.assertEqual(self._count_grid_rooms(), 13)

    def test_interiors_are_not_xyzgrid_nodes(self):
        sync_service_interiors()
        grid_keys = {room.key for room in GridRoom.objects.all_family()}
        self.assertNotIn("阿爾托利亞冒險者公會大廳", grid_keys)
        self.assertNotIn("阿爾托利亞雜貨店", grid_keys)

    def test_repeated_sync_creates_no_duplicates(self):
        sync_service_interiors()
        first = {
            tag: (room.pk, sorted(e.key for e in room.exits))
            for tag in (GUILD_HALL_TAG, GENERAL_STORE_TAG)
            for room in search_object_by_tag(tag)
        }
        room_count = Room.objects.all_family().count()
        exit_count = Exit.objects.all().count()

        sync_service_interiors()

        second = {
            tag: (room.pk, sorted(e.key for e in room.exits))
            for tag in (GUILD_HALL_TAG, GENERAL_STORE_TAG)
            for room in search_object_by_tag(tag)
        }
        self.assertEqual(first, second)
        self.assertEqual(Room.objects.all_family().count(), room_count)
        self.assertEqual(Exit.objects.all().count(), exit_count)

    def test_interior_reachable_from_and_back_to_exterior(self):
        sync_service_interiors()
        guild_hall = self._interior(GUILD_HALL_TAG)
        guild_exterior = GridRoom.objects.filter_xyz(xyz=GUILD_HALL_EXTERIOR_XYZ).first()
        self.assertTrue(guild_hall.access(guild_exterior, "traverse", default=True))
        self.assertIn(guild_exterior, {e.destination for e in guild_hall.exits})


if __name__ == "__main__":
    import unittest

    unittest.main()
