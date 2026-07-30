"""Self-consistency checks for geographic anchors."""

import unittest
from collections import Counter

from world.lore.anchors import ANCHOR_REGISTRY, AnchorKind


class AnchorRegistryTests(unittest.TestCase):
    def test_nine_anchors_split_evenly_by_kind(self):
        counts = Counter(anchor.kind for anchor in ANCHOR_REGISTRY.values())
        self.assertEqual(len(ANCHOR_REGISTRY), 9)
        self.assertEqual(
            counts,
            {AnchorKind.CAPITAL: 3, AnchorKind.ELVEN_VILLAGE: 3, AnchorKind.DUNGEON: 3},
        )

    def test_dungeon_floor_counts(self):
        self.assertEqual(ANCHOR_REGISTRY["dungeon_eternal_night"].floors, 80)
        self.assertEqual(ANCHOR_REGISTRY["dungeon_dragon_nest"].floors, 50)
        self.assertEqual(ANCHOR_REGISTRY["dungeon_arcane_ruins"].floors, 60)

    def test_elven_villages_are_neutral(self):
        for anchor in ANCHOR_REGISTRY.values():
            if anchor.kind == AnchorKind.ELVEN_VILLAGE:
                self.assertIsNone(anchor.nation_key)
