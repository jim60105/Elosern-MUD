"""Self-consistency checks for race, tier, and subrace registries."""

import unittest

from world.lore.anchors import ANCHOR_REGISTRY, AnchorKind
from world.lore.races import (
    RACE_REGISTRY,
    STATIC_TIER_REGISTRY,
    SUBRACE_REGISTRY,
    StatModifiers,
)


BEASTFOLK_SUBRACES = {
    "wolfkin",
    "catkin",
    "bearkin",
    "rabbitkin",
    "bovinekin",
    "tigerkin",
    "foxkin",
}
ELF_BRANCHES = {"fionnen", "ciaran", "eolas"}


class RaceRegistryTests(unittest.TestCase):
    def test_registry_membership(self):
        self.assertEqual(set(RACE_REGISTRY), {"human", "beastfolk", "elf"})
        self.assertEqual(len(STATIC_TIER_REGISTRY), 11)
        self.assertEqual(len(SUBRACE_REGISTRY), 10)

    def test_magic_cap_and_divine_arts(self):
        beastfolk = RACE_REGISTRY["beastfolk"]
        human = RACE_REGISTRY["human"]
        elf = RACE_REGISTRY["elf"]
        self.assertLess(beastfolk.magic_cap, human.magic_cap)
        self.assertLess(human.magic_cap, elf.magic_cap)
        self.assertFalse(human.can_use_divine_arts)
        self.assertFalse(beastfolk.can_use_divine_arts)
        self.assertTrue(elf.can_use_divine_arts)

    def test_vital_pool_scale_is_independent(self):
        human_ceiling = RACE_REGISTRY["human"].vital_baseline.hp[1]
        elf_floor = RACE_REGISTRY["elf"].vital_baseline.hp[0]
        self.assertGreaterEqual(elf_floor, human_ceiling * 50)

    def test_static_stat_scale_is_independent(self):
        human_elite_ceiling = STATIC_TIER_REGISTRY["human_elite"].band[1]
        self.assertIsNotNone(human_elite_ceiling)
        elf_floor = RACE_REGISTRY["elf"].static_baseline.atk_phys[0]
        ratio = elf_floor / human_elite_ceiling
        self.assertGreaterEqual(ratio, 5)
        self.assertLessEqual(ratio, 15)

    def test_static_tiers_reference_races_and_fit_species_bands(self):
        for tier in STATIC_TIER_REGISTRY.values():
            with self.subTest(tier=tier.key):
                race_band = RACE_REGISTRY[tier.race_key].static_baseline.atk_phys
                self.assertGreaterEqual(tier.band[0], race_band[0])
                if tier.band[1] is not None:
                    self.assertLessEqual(tier.band[1], race_band[1])

    def test_human_tier_order_reaches_species_ceiling(self):
        tiers = sorted(
            (tier for tier in STATIC_TIER_REGISTRY.values() if tier.race_key == "human"),
            key=lambda tier: tier.order,
        )
        self.assertEqual(
            [tier.display_name_zh for tier in tiers],
            ["平民與非戰鬥者", "一般冒險者", "精銳", "一流", "大劍豪"],
        )
        self.assertEqual([tier.order for tier in tiers], [1, 2, 3, 4, 5])
        self.assertEqual(tiers[-1].band[1], RACE_REGISTRY["human"].static_baseline.atk_phys[1])

    def test_guild_rank_hints_only_appear_on_correlated_human_tiers(self):
        expected = {
            "human_commoner": None,
            "human_adventurer": "F",
            "human_elite": "C",
            "human_veteran": "A",
            "human_swordmaster": "S",
        }
        for key, tier in STATIC_TIER_REGISTRY.items():
            with self.subTest(tier=key):
                self.assertEqual(tier.guild_rank_hint, expected.get(key))

    def test_elf_prodigy_has_open_upper_bound(self):
        self.assertEqual(STATIC_TIER_REGISTRY["elf_prodigy"].band, (95, None))

    def test_subraces_reference_races_and_elf_villages(self):
        for subrace in SUBRACE_REGISTRY.values():
            self.assertIn(subrace.race_key, RACE_REGISTRY)
        for key in ELF_BRANCHES:
            subrace = SUBRACE_REGISTRY[key]
            anchor = ANCHOR_REGISTRY[subrace.home_anchor_key]
            self.assertEqual(anchor.kind, AnchorKind.ELVEN_VILLAGE)

    def test_beastfolk_modifier_values(self):
        expected = {
            "wolfkin": StatModifiers(),
            "catkin": StatModifiers(-0.10, 0.40, -0.30),
            "bearkin": StatModifiers(0.45, -0.40, -0.05),
            "rabbitkin": StatModifiers(-0.35, 0.50, -0.15),
            "bovinekin": StatModifiers(-0.10, -0.35, 0.45),
            "tigerkin": StatModifiers(0.35, 0.10, -0.45),
            "foxkin": StatModifiers(-0.05, 0.15, -0.10),
        }
        for key, modifiers in expected.items():
            self.assertEqual(SUBRACE_REGISTRY[key].static_modifiers, modifiers)

    def test_beastfolk_modifiers_sum_to_zero(self):
        for key in BEASTFOLK_SUBRACES:
            modifiers = SUBRACE_REGISTRY[key].static_modifiers
            total = modifiers.atk_phys + modifiers.agility + modifiers.defense
            self.assertLessEqual(abs(total), 1e-12, key)

    def test_subrace_population_and_overrides(self):
        for key in BEASTFOLK_SUBRACES:
            self.assertIsNone(SUBRACE_REGISTRY[key].population)
        for key in ELF_BRANCHES:
            self.assertEqual(SUBRACE_REGISTRY[key].static_modifiers, StatModifiers())
            self.assertIsNone(SUBRACE_REGISTRY[key].vital_overrides)
        self.assertEqual(SUBRACE_REGISTRY["foxkin"].vital_overrides, {"mp": (50, 70)})
        for key, subrace in SUBRACE_REGISTRY.items():
            if key != "foxkin":
                self.assertIsNone(subrace.vital_overrides)


if __name__ == "__main__":
    unittest.main()
