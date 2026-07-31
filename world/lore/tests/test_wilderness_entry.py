"""Self-consistency checks for wilderness entry points (map-wilderness)."""

import unittest

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY


class WildernessEntryRegistryTests(unittest.TestCase):
    def test_registry_has_exactly_one_entry_keyed_capital_altoria(self):
        self.assertEqual(list(WILDERNESS_ENTRY_REGISTRY), ["capital_altoria"])
        entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
        self.assertEqual(entry.anchor_key, "capital_altoria")
        self.assertEqual(entry.wilderness_xy, (60, 100))

    def test_every_entrys_anchor_key_exists_in_anchor_placement_registry(self):
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            self.assertIn(entry.anchor_key, ANCHOR_PLACEMENT_REGISTRY)

    def test_entry_wilderness_xy_is_within_provider_bounds(self):
        from world.maps.wilderness_provider import WILDERNESS_MAX_X, WILDERNESS_MAX_Y

        x, y = WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)
        self.assertLessEqual(x, WILDERNESS_MAX_X)
        self.assertLessEqual(y, WILDERNESS_MAX_Y)

    def test_every_entry_has_a_south_bound_returnable_coordinate(self):
        # The return path (WildernessReturnExit) routes back to the grid via a
        # "south" traversal at the entry coordinate; a y == 0 entry would have
        # its south exit locked invalid by the contrib's edge locking and be
        # unreachable. Guard that here so a future registry addition cannot
        # silently create an unreturnable gateway.
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            self.assertGreater(entry.wilderness_xy[1], 0)
