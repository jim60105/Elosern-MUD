"""Regression tests for independent vital and static race scales."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.races import RACE_REGISTRY, STATIC_TIER_REGISTRY
from world.rules.traits import initial_trait_config


class RaceScaleTests(unittest.TestCase):
    @covers_requirement("entity-trait-scales::race-driven-gauge-and-counter-initial-values-come-from-raceprofile-never-a-hardcoded-per-race-number", "entity-trait-scales::static-combat-trait-bases-are-read-directly-from-raceprofile-static-baseline-never-derived-from-vital-baseline")
    def test_vitals_magic_and_statics_use_their_own_registry_axes(self):
        human = initial_trait_config("human")
        elf = initial_trait_config("elf")
        self.assertEqual(human["hp"]["base"], RACE_REGISTRY["human"].vital_baseline.hp[0])
        self.assertEqual(elf["hp"]["base"], RACE_REGISTRY["elf"].vital_baseline.hp[0])
        self.assertGreaterEqual(elf["hp"]["base"], human["hp"]["base"] * 50)
        # magic_power is a static axis now: its base is the race band floor.
        self.assertEqual(elf["magic_power"]["trait_type"], "static")
        self.assertEqual(
            elf["magic_power"]["base"],
            RACE_REGISTRY["elf"].static_baseline.magic_power[0],
        )
        self.assertEqual(
            human["magic_power"]["base"],
            RACE_REGISTRY["human"].static_baseline.magic_power[0],
        )
        self.assertEqual(human["guild_merit"]["base"], 0)
        self.assertIsNone(human["guild_merit"]["max"])
        for key in ("atk_phys", "agility", "defense"):
            self.assertEqual(
                human[key]["base"],
                getattr(RACE_REGISTRY["human"].static_baseline, key)[0],
            )
            self.assertEqual(
                elf[key]["base"],
                getattr(RACE_REGISTRY["elf"].static_baseline, key)[0],
            )
        ratio = elf["atk_phys"]["base"] / STATIC_TIER_REGISTRY["human_elite"].band[0]
        self.assertGreaterEqual(ratio, 8)
        self.assertLessEqual(ratio, 10)
