"""Tests for the deterministic terrain model and bounded map provider (map-wilderness)."""

from tools.spec_traceability import covers_requirement

import inspect
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import TerrainRoom
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
from world.maps.wilderness_provider import (
    WILDERNESS_KM_PER_CELL,
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
    terrain_description,
)


class TerrainModelTests(unittest.TestCase):
    def test_functions_are_pure(self):
        for x, y in ((0, 0), (60, 100), (123, 189), (223, 223)):
            self.assertEqual(region_for_coordinates(x, y), region_for_coordinates(x, y))
            self.assertEqual(terrain_description(x, y), terrain_description(x, y))

    def test_all_seven_region_keys_are_reachable(self):
        reached = set()
        for x in range(WILDERNESS_MAX_X + 1):
            for y in range(WILDERNESS_MAX_Y + 1):
                reached.add(region_for_coordinates(x, y))
        self.assertEqual(reached, set(WILDERNESS_REGION_REGISTRY))

    @covers_requirement("wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map")
    def test_central_mountain_band_spans_full_y(self):
        for x in (100, 123):
            self.assertEqual(region_for_coordinates(x, 0), "central_mountains")
            self.assertEqual(region_for_coordinates(x, 149), "central_mountains")
            self.assertEqual(region_for_coordinates(x, 189), "central_mountains")

    @covers_requirement("wilderness-terrain::terrain-description-is-a-pure-deterministic-function-with-no-llm-or-randomness")
    def test_capital_altoria_entry_resolves_to_western_hills_valleys(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

        x, y = WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy
        self.assertEqual(region_for_coordinates(x, y), "western_hills_valleys")

    def test_description_always_matches_its_regions_variants(self):
        for x, y in ((0, 0), (60, 100), (111, 50), (200, 200), (223, 223)):
            region = WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)]
            self.assertIn(terrain_description(x, y), region.terrain_flavor_zh)

    def test_literal_pin_for_terrain_description_60_100(self):
        self.assertEqual(
            terrain_description(60, 100),
            "谷地間河流蜿蜒，兩岸散落著手工業者的作坊與磨坊。",
        )

    def test_no_llm_or_random_dependency_in_source(self):
        source = inspect.getsource(__import__("world.maps.wilderness_provider"))
        self.assertNotIn("world.ai", source)
        self.assertNotIn("random", source)
        self.assertNotIn("import urllib", source)
        self.assertNotIn("import requests", source)


class MapProviderTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.provider = ElosernWildernessMapProvider()

    def test_coordinate_bounds(self):
        self.assertTrue(self.provider.is_valid_coordinates(None, (0, 0)))
        self.assertTrue(self.provider.is_valid_coordinates(None, (223, 223)))
        self.assertFalse(self.provider.is_valid_coordinates(None, (-1, 0)))
        self.assertFalse(self.provider.is_valid_coordinates(None, (224, 0)))

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-bounds-the-map-to-a-224x224-grid-at-10-km-per-cell")
    def test_bound_area_matches_continent_size(self):
        side_km = (WILDERNESS_MAX_X + 1) * WILDERNESS_KM_PER_CELL
        area = side_km * side_km
        self.assertAlmostEqual(area, 5_000_000, delta=5_000_000 * 0.01)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_get_location_name_matches_region_registry(self):
        for x, y in ((60, 100), (111, 189), (200, 30), (0, 220)):
            expected = WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)].display_name_zh
            self.assertEqual(self.provider.get_location_name((x, y)), expected)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_enter_wilderness_prepares_terrain_room(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=self.provider)
        ok = enter_wilderness(
            self.char1, coordinates=(60, 100), name=WILDERNESS_NAME
        )
        self.assertTrue(ok)
        room = self.char1.location
        self.assertIsInstance(room, TerrainRoom)
        self.assertEqual(room.ndb.active_desc, terrain_description(60, 100))
        self.assertEqual(room.scene_archetype, region_for_coordinates(60, 100))

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_at_prepare_room_is_population_noop_without_wilderness_script(self):
        from typeclasses.monsters import Monster

        from world.maps.wilderness_provider import (
            terrain_description as _terrain_description,
        )

        room = create_object(TerrainRoom, key="scriptless")
        self.assertIsNone(room.wilderness)
        self.provider.at_prepare_room((60, 100), None, room)
        self.assertEqual(room.scene_archetype, region_for_coordinates(60, 100))
        self.assertEqual(room.ndb.active_desc, _terrain_description(60, 100))
        self.assertEqual(Monster.objects.all().count(), 0)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_enter_wilderness_populates_the_entry_coordinate(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )
        from typeclasses.monsters import Monster

        create_wilderness(name=WILDERNESS_NAME, mapprovider=self.provider)
        enter_wilderness(self.char1, coordinates=(60, 100), name=WILDERNESS_NAME)
        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        monsters = [
            obj
            for obj in script.get_objs_at_coordinates((60, 100))
            if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        self.assertEqual(monsters[0].db.population_key, "wilderness:60:100")
        self.assertIs(monsters[0].location, self.char1.location)

    @covers_requirement("wilderness-map-provider::get-location-name-and-at-prepare-room-delegate-to-the-deterministic-terrain-model")
    def test_recycled_room_gets_fresh_scene_archetype(self):
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=self.provider)
        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        # Enter at (60, 100) in western_hills_valleys; the room gets that region's archetype.
        enter_wilderness(self.char1, coordinates=(60, 100), name=WILDERNESS_NAME)
        room_a = self.char1.location
        self.assertEqual(room_a.scene_archetype, "western_hills_valleys")
        # Leave the wilderness; then force the room back into the reuse pool
        # (task 7.7's sanctioned "inspect unused_rooms directly" route) so the
        # next entry is guaranteed to be handed this exact object again.
        self.char1.move_to(self.room1)
        del script.db.rooms[(60, 100)]
        del room_a.ndb.active_coordinates
        script.db.unused_rooms.append(room_a)
        # Re-enter at a coordinate in a different region: the pooled room is
        # reused and must reflect the new region, never the stale first value.
        enter_wilderness(self.char1, coordinates=(200, 100), name=WILDERNESS_NAME)
        self.assertIs(self.char1.location, room_a)
        self.assertEqual(self.char1.location.scene_archetype, "eastern_plains")
        self.assertEqual(
            self.char1.location.ndb.active_desc, terrain_description(200, 100)
        )
