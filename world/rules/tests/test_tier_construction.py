"""Regression tests for explicit named static tiers."""

import unittest

from world.lore.races import STATIC_TIER_REGISTRY
from world.rules.traits import build_initial_traits


class TierConstructionTests(unittest.TestCase):
    def test_named_human_tiers_land_on_their_documented_floor(self):
        for tier_key in ("human_swordmaster", "human_commoner"):
            values = build_initial_traits("human", tier=tier_key)
            band = STATIC_TIER_REGISTRY[tier_key].band
            for key in ("atk_phys", "agility", "defense"):
                self.assertGreaterEqual(values[key], band[0])
                self.assertLessEqual(values[key], band[1])

    def test_cross_race_tier_fails_and_omission_preserves_floor(self):
        with self.assertRaisesRegex(ValueError, "belongs to race"):
            build_initial_traits("elf", tier="human_swordmaster")
        self.assertEqual(
            build_initial_traits("human"),
            build_initial_traits("human", tier=None),
        )

