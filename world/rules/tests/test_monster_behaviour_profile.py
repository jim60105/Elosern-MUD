"""Rulebook coverage and monster profile resolution."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.rules.monster_behaviour import (
    BEHAVIOUR_PROFILES,
    MONSTER_BEHAVIOUR_YAML,
    resolve_behaviour_profile,
)


class MonsterBehaviourProfileTests(unittest.TestCase):
    @covers_requirement("monster-behaviour-profile::behaviour-parameters-are-data-driven-not-hardcoded-in-python", "monster-behaviour-profile::behaviour-tiers-are-grounded-in-monstertier-and-named-world-info-md-examples-not")
    def test_rulebook_covers_distinct_tier_defaults_and_override(self):
        defaults = MONSTER_BEHAVIOUR_YAML["tier_default_archetype"]
        archetypes = MONSTER_BEHAVIOUR_YAML["archetypes"]
        self.assertEqual(set(defaults), set(MONSTER_TIER_REGISTRY))
        self.assertTrue(set(defaults.values()) <= set(archetypes))
        self.assertEqual(len(set(defaults.values())), len(defaults))
        self.assertTrue(set(archetypes) - set(defaults.values()))
        for values in archetypes.values():
            self.assertEqual(
                set(values),
                {
                    "target_strategy",
                    "skill_choice",
                    "prefer_area_when_multiple_enemies",
                    "flee_hp_fraction",
                },
            )
            self.assertIn(
                values["target_strategy"],
                {"lowest_hp", "highest_effective_power"},
            )
            self.assertIn(
                values["skill_choice"],
                {"first_owned", "highest_expected_damage"},
            )
            self.assertIsInstance(
                values["prefer_area_when_multiple_enemies"],
                bool,
            )
            self.assertTrue(
                values["flee_hp_fraction"] is None
                or 0.0 <= values["flee_hp_fraction"] <= 1.0
            )

    @covers_requirement("monster-behaviour-profile::monster-behaviour-tree-resolves-to-a-real-archetype-defaulting-from-threat-tier")
    def test_unset_profile_defaults_for_every_tier(self):
        for tier, archetype in MONSTER_BEHAVIOUR_YAML[
            "tier_default_archetype"
        ].items():
            monster = type(
                "MonsterFixture",
                (),
                {"threat_tier": tier, "behaviour_tree": None},
            )()
            self.assertEqual(
                resolve_behaviour_profile(monster),
                BEHAVIOUR_PROFILES[archetype],
            )

    def test_instance_override_wins(self):
        monster = type(
            "MonsterFixture",
            (),
            {"threat_tier": "high", "behaviour_tree": "tactical_caster"},
        )()
        self.assertEqual(
            resolve_behaviour_profile(monster),
            BEHAVIOUR_PROFILES["tactical_caster"],
        )
