"""Self-consistency checks for the wilderness terrain registry (map-wilderness)."""

import unittest

from world.lore.nations import NATION_REGISTRY
from world.lore.wilderness_regions import (
    WILDERNESS_REGION_REGISTRY,
    WildernessRegion,
)

EXPECTED_KEYS = {
    "central_mountains",
    "eastern_plains",
    "southeast_coast",
    "western_hills_valleys",
    "southwest_coast",
    "northwest_highland_forest",
    "north_deep_forest",
}


class WildernessRegionRegistryTests(unittest.TestCase):
    def test_registry_has_exactly_seven_entries_with_unique_names(self):
        self.assertEqual(set(WILDERNESS_REGION_REGISTRY), EXPECTED_KEYS)
        names = [region.display_name_zh for region in WILDERNESS_REGION_REGISTRY.values()]
        self.assertEqual(len(names), len(set(names)))

    def test_every_region_carries_at_least_two_flavor_variants(self):
        for region in WILDERNESS_REGION_REGISTRY.values():
            self.assertGreaterEqual(len(region.terrain_flavor_zh), 2)

    def test_every_non_none_nation_key_exists_in_nation_registry(self):
        for region in WILDERNESS_REGION_REGISTRY.values():
            if region.nation_key is not None:
                self.assertIn(region.nation_key, NATION_REGISTRY)

    def test_dataclass_is_frozen_and_keyed_by_key_field(self):
        self.assertTrue(WildernessRegion.__dataclass_params__.frozen)
        for key, region in WILDERNESS_REGION_REGISTRY.items():
            self.assertEqual(region.key, key)
