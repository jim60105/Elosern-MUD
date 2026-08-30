"""Self-consistency checks for race, tier, and subrace registries."""

from tools.spec_traceability import covers_requirement

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
HUMAN_SUBRACES = {
    "human_royal",
    "human_noble",
    "human_wealthy",
    "human_commoner",
    "human_laborer",
}


class RaceRegistryTests(unittest.TestCase):
    def test_registry_membership(self):
        self.assertEqual(set(RACE_REGISTRY), {"human", "beastfolk", "elf"})
        self.assertEqual(len(STATIC_TIER_REGISTRY), 11)
        self.assertEqual(len(SUBRACE_REGISTRY), 15)

    def test_magic_power_band_ordering_and_divine_arts(self):
        bands = {
            key: race.static_baseline.magic_power
            for key, race in RACE_REGISTRY.items()
        }
        self.assertEqual(bands, {"human": (5, 90), "beastfolk": (1, 30), "elf": (100, 900)})
        # Ordering by upper bound: beastfolk < human < elf on the interim table
        # 1-30 / 5-90 / 100-900; the elf floor clears the human ceiling outright.
        self.assertLess(bands["beastfolk"][1], bands["human"][1])
        self.assertLess(bands["human"][1], bands["elf"][1])
        self.assertGreater(bands["elf"][0], bands["human"][1])
        self.assertFalse(RACE_REGISTRY["human"].can_use_divine_arts)
        self.assertFalse(RACE_REGISTRY["beastfolk"].can_use_divine_arts)
        self.assertTrue(RACE_REGISTRY["elf"].can_use_divine_arts)

    @covers_requirement("lore-registries::raceprofile-encodes-the-three-race-power-gap")
    def test_magic_power_axis_is_the_only_race_magic_bound(self):
        for race in RACE_REGISTRY.values():
            with self.subTest(race=race.key):
                band = race.static_baseline.magic_power
                self.assertIsInstance(band, tuple)
                self.assertEqual(len(band), 2)
                self.assertIs(type(band[0]), int)
                self.assertIs(type(band[1]), int)
                self.assertLessEqual(band[0], band[1])
                # The deleted magic-only fields must not resurface.
                self.assertFalse(hasattr(race, "magic_cap"))
                self.assertFalse(hasattr(race, "starting_magic_level"))

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

    @covers_requirement("lore-registries::statictier-registry-records-named-power-bands-within-each-race-s-static-baseline")
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

    @covers_requirement("lore-registries::subrace-registry-covers-elf-branches-beastfolk-subspecies-and-human-social-classes-with-stat-modifiers")
    def test_beastfolk_modifiers_sum_to_zero(self):
        for key in BEASTFOLK_SUBRACES:
            modifiers = SUBRACE_REGISTRY[key].static_modifiers
            total = modifiers.atk_phys + modifiers.agility + modifiers.defense
            self.assertLessEqual(abs(total), 1e-12, key)

    def test_human_subraces_exist_with_social_class_names(self):
        expected_names = {
            "human_royal": "王族",
            "human_noble": "貴族",
            "human_wealthy": "富裕平民",
            "human_commoner": "平民",
            "human_laborer": "底層平民",
        }
        for key, display_name in expected_names.items():
            subrace = SUBRACE_REGISTRY[key]
            self.assertEqual(subrace.display_name_zh, display_name)
            self.assertEqual(subrace.race_key, "human")
            self.assertIsNone(subrace.population)

    def test_every_race_has_at_least_one_subrace(self):
        for race_key in RACE_REGISTRY:
            with self.subTest(race=race_key):
                self.assertTrue(
                    any(
                        subrace.race_key == race_key
                        for subrace in SUBRACE_REGISTRY.values()
                    ),
                    f"race {race_key} has no subrace",
                )

    @covers_requirement("lore-registries::subrace-registry-covers-elf-branches-beastfolk-subspecies-and-human-social-classes-with-stat-modifiers")
    def test_human_modifiers_sum_to_zero(self):
        for key in HUMAN_SUBRACES:
            modifiers = SUBRACE_REGISTRY[key].static_modifiers
            total = modifiers.atk_phys + modifiers.agility + modifiers.defense
            self.assertLessEqual(abs(total), 1e-12, key)

    def test_human_royal_overrides_the_mp_vital_band(self):
        self.assertEqual(SUBRACE_REGISTRY["human_royal"].vital_overrides, {"mp": (120, 220)})

    def test_subrace_population_and_overrides(self):
        for key in BEASTFOLK_SUBRACES:
            self.assertIsNone(SUBRACE_REGISTRY[key].population)
        for key in ELF_BRANCHES:
            self.assertEqual(SUBRACE_REGISTRY[key].static_modifiers, StatModifiers())
            self.assertIsNone(SUBRACE_REGISTRY[key].vital_overrides)
        self.assertEqual(SUBRACE_REGISTRY["foxkin"].vital_overrides, {"mp": (50, 70)})
        for key, subrace in SUBRACE_REGISTRY.items():
            if key not in ("foxkin", "human_royal"):
                self.assertIsNone(subrace.vital_overrides)


if __name__ == "__main__":
    unittest.main()
