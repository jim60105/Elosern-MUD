"""Data-contract test: anchor data contract
Self-consistency checks for geographic anchors."""

from tools.spec_traceability import covers_requirement

import unittest
from collections import Counter

from world.lore.anchors import (
    ANCHOR_GEOGRAPHY_REGISTRY,
    ANCHOR_REGISTRY,
    AnchorKind,
    GeographicAnchor,
)


class AnchorRegistryTests(unittest.TestCase):
    def test_nine_anchors_split_evenly_by_kind(self):
        counts = Counter(anchor.kind for anchor in ANCHOR_REGISTRY.values())
        self.assertEqual(len(ANCHOR_REGISTRY), 9)
        self.assertEqual(
            counts,
            {AnchorKind.CAPITAL: 3, AnchorKind.ELVEN_VILLAGE: 3, AnchorKind.DUNGEON: 3},
        )

    @covers_requirement("lore-registries::anchor-registry-covers-capitals-elven-villages-and-known-dungeons")
    def test_dungeon_floor_counts(self):
        self.assertEqual(ANCHOR_REGISTRY["dungeon_eternal_night"].floors, 80)
        self.assertEqual(ANCHOR_REGISTRY["dungeon_dragon_nest"].floors, 50)
        self.assertEqual(ANCHOR_REGISTRY["dungeon_arcane_ruins"].floors, 60)

    def test_elven_villages_are_neutral(self):
        for anchor in ANCHOR_REGISTRY.values():
            if anchor.kind == AnchorKind.ELVEN_VILLAGE:
                self.assertIsNone(anchor.nation_key)

    @covers_requirement(
        "continental-geography::the-known-continent-has-frozen-geographic-declarations"
    )
    def test_geographic_cells_are_the_authored_table_for_all_nine_anchors(self):
        self.assertEqual(
            {key: entry.cell for key, entry in ANCHOR_GEOGRAPHY_REGISTRY.items()},
            {
                "capital_altoria": (860, 1080),
                "capital_grandia": (1970, 1280),
                "capital_valhalla": (780, 1910),
                "village_ciaran": (1340, 1220),
                "village_fionnen": (1490, 1510),
                "village_eolas": (1410, 2150),
                "dungeon_eternal_night": (900, 2350),
                "dungeon_dragon_nest": (2340, 1220),
                "dungeon_arcane_ruins": (480, 1160),
            },
        )
        self.assertEqual(set(ANCHOR_GEOGRAPHY_REGISTRY), set(ANCHOR_REGISTRY))
        self.assertTrue(GeographicAnchor.__dataclass_params__.frozen)
        for key, entry in ANCHOR_GEOGRAPHY_REGISTRY.items():
            with self.subTest(anchor=key):
                self.assertEqual(entry.anchor_key, key)
                self.assertTrue(entry.geographic_constraint)
