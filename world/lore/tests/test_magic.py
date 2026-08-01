"""Self-consistency checks for magic tiers and rank titles."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.magic import MAGIC_TIER_REGISTRY, RANK_TITLE_REGISTRY


class MagicRegistryTests(unittest.TestCase):
    @covers_requirement("lore-registries::magictier-bands-are-contiguous-and-non-overlapping")
    def test_tier_bands_are_contiguous(self):
        tiers = sorted(MAGIC_TIER_REGISTRY.values(), key=lambda tier: tier.level_min)
        self.assertEqual([tier.level_min for tier in tiers], [0, 16, 31, 71, 91])
        for previous, current in zip(tiers, tiers[1:]):
            self.assertIsNotNone(previous.level_max)
            self.assertEqual(current.level_min, previous.level_max + 1)
        self.assertIsNone(tiers[-1].level_max)

    @covers_requirement("lore-registries::ranktitle-registry-is-ordered-and-references-magic-tiers")
    def test_rank_titles_are_ordered_and_resolve_tiers(self):
        titles = sorted(RANK_TITLE_REGISTRY.values(), key=lambda title: title.order)
        self.assertEqual([title.order for title in titles], [1, 2, 3, 4, 5])
        self.assertEqual(
            [title.display_name_zh for title in titles],
            ["學徒", "術師", "大師", "賢者", "主宰"],
        )
        for title in titles:
            if title.unlocks_tier is not None:
                self.assertIn(title.unlocks_tier, MAGIC_TIER_REGISTRY)
