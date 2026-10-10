"""Data-contract test: magic tier data contract
Self-consistency checks for the magic-tier cost bands."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.magic import MAGIC_TIER_REGISTRY

class MagicRegistryTests(unittest.TestCase):
    @covers_requirement("lore-registries::magictier-bands-are-contiguous-and-non-overlapping")
    def test_tier_bands_are_contiguous(self):
        tiers = sorted(MAGIC_TIER_REGISTRY.values(), key=lambda tier: tier.level_min)
        # The ladder is anchored at level 0 and every later tier starts exactly
        # after its predecessor's ceiling; the interior boundaries are authored
        # data, so only the contiguity relation is asserted.
        self.assertEqual(tiers[0].level_min, 0)
        for previous, current in zip(tiers, tiers[1:]):
            self.assertIsNotNone(previous.level_max)
            self.assertEqual(current.level_min, previous.level_max + 1)
        self.assertIsNone(tiers[-1].level_max)
