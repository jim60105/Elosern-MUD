"""Data-contract test: monster tier data contract
Approved independent authoring envelopes and canonical threat partitions."""

import unittest

from tools.spec_traceability import covers_requirement
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY


class MonsterRegistryTests(unittest.TestCase):
    def test_four_tiers_partition_guild_ranks(self):
        self.assertEqual(len(MONSTER_TIER_REGISTRY), 4)
        order = {key: rank.order for key, rank in GUILD_RANK_REGISTRY.items()}
        covered = []
        for tier in MONSTER_TIER_REGISTRY.values():
            start, end = tier.guild_rank_range
            covered.extend(key for key, position in order.items() if order[start] <= position <= order[end])
        self.assertEqual(sorted(covered), sorted(GUILD_RANK_REGISTRY))

    def test_every_tier_has_examples(self):
        for tier in MONSTER_TIER_REGISTRY.values():
            self.assertTrue(tier.example_monsters_zh)

    @covers_requirement("lore-registries::monstertier-registry-has-physical-stat-and-hp-bands-derived-from-guild-rank")
    def test_approved_independent_envelopes(self):
        expected = {
            "low": ((25, 70), (3, 12), (3, 12), (2, 8)),
            "mid": ((110, 230), (18, 28), (10, 24), (10, 16)),
            "high": ((300, 750), (26, 40), (16, 30), (18, 32)),
            "calamity": ((1200, None), (60, None), (60, None), (60, None)),
        }
        self.assertEqual(set(MONSTER_TIER_REGISTRY), set(expected))
        for key, bounds in expected.items():
            with self.subTest(tier=key):
                tier = MONSTER_TIER_REGISTRY[key]
                self.assertEqual((tier.hp_band, tier.static_band.atk_phys, tier.static_band.agility, tier.static_band.defense), bounds)
                self.assertEqual(tier.static_band.magic_power, (0, 0))
