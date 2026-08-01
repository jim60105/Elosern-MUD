"""Self-consistency checks for monster threat bands."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.races import RACE_REGISTRY, STATIC_TIER_REGISTRY


class MonsterRegistryTests(unittest.TestCase):
    def test_four_tiers_partition_guild_ranks(self):
        self.assertEqual(len(MONSTER_TIER_REGISTRY), 4)
        order = {key: rank.order for key, rank in GUILD_RANK_REGISTRY.items()}
        covered: list[str] = []
        for tier in MONSTER_TIER_REGISTRY.values():
            start, end = tier.guild_rank_range
            covered.extend(
                key for key, rank_order in order.items()
                if order[start] <= rank_order <= order[end]
            )
        self.assertEqual(sorted(covered), sorted(GUILD_RANK_REGISTRY))

    def test_every_tier_has_examples(self):
        for tier in MONSTER_TIER_REGISTRY.values():
            self.assertTrue(tier.example_monsters_zh)

    def test_tiers_follow_adventurer_correspondence(self):
        low = MONSTER_TIER_REGISTRY["low"].static_band.atk_phys
        adventurer = STATIC_TIER_REGISTRY["human_adventurer"].band
        self.assertLessEqual(low[0], adventurer[1])
        self.assertGreaterEqual(low[1], adventurer[0])

        mid = MONSTER_TIER_REGISTRY["mid"].static_band.atk_phys
        self.assertGreater(mid[1], STATIC_TIER_REGISTRY["human_elite"].band[1])

        high = MONSTER_TIER_REGISTRY["high"].static_band.atk_phys
        self.assertGreaterEqual(high[0], STATIC_TIER_REGISTRY["human_swordmaster"].band[1])

        calamity = MONSTER_TIER_REGISTRY["calamity"].static_band.atk_phys
        elf_common = STATIC_TIER_REGISTRY["elf_common"].band
        self.assertLessEqual(calamity[0], elf_common[1])
        self.assertGreater(calamity[1], elf_common[1])

    @covers_requirement("lore-registries::monstertier-registry-has-physical-stat-and-hp-bands-derived-from-guild-rank")
    def test_calamity_overlaps_and_exceeds_elf_species_band(self):
        calamity = MONSTER_TIER_REGISTRY["calamity"].static_band.atk_phys
        elf = RACE_REGISTRY["elf"].static_baseline.atk_phys
        self.assertLessEqual(calamity[0], elf[1])
        self.assertGreater(calamity[1], elf[1])

    def test_hp_is_fifteen_to_twenty_times_static_band(self):
        for tier in MONSTER_TIER_REGISTRY.values():
            static = tier.static_band.atk_phys
            lower_ratio = tier.hp_band[0] / static[0]
            upper_ratio = tier.hp_band[1] / static[1]
            self.assertGreaterEqual(lower_ratio, 15)
            self.assertLessEqual(lower_ratio, 20)
            self.assertGreaterEqual(upper_ratio, 15)
            self.assertLessEqual(upper_ratio, 20)
