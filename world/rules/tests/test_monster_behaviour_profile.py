"""Data-contract test: monster behaviour rulebook contract
Rulebook coverage and monster profile resolution."""

from tools.spec_traceability import covers_requirement

import unittest
from numbers import Real

from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.rules.monster_behaviour import (
    BEHAVIOUR_PROFILES,
    MONSTER_AI_TUNING,
    MONSTER_BEHAVIOUR_YAML,
    UTILITY_WEIGHT_NAMES,
    DecisionMode,
    resolve_behaviour_profile,
)

_MANDATORY_FIELDS = {
    "target_strategy",
    "skill_choice",
    "prefer_area_when_multiple_enemies",
    "flee_hp_fraction",
}
_OPTIONAL_FIELDS = {"decision_mode", "utility_weights"}
_SIX_ARCHETYPES = {
    "instinctive",
    "pack_hunter",
    "brute",
    "tactical_caster",
    "apex_predator",
    "ambush_predator",
}


class MonsterBehaviourProfileTests(unittest.TestCase):
    @covers_requirement("monster-behaviour-profile::behaviour-parameters-are-data-driven-not-hardcoded-in-python", "monster-behaviour-profile::behaviour-tiers-are-grounded-in-monstertier-and-named-world-info-md-examples-not")
    def test_rulebook_covers_distinct_tier_defaults_and_override(self):
        defaults = MONSTER_BEHAVIOUR_YAML["tier_default_archetype"]
        archetypes = MONSTER_BEHAVIOUR_YAML["archetypes"]
        self.assertEqual(set(defaults), set(MONSTER_TIER_REGISTRY))
        self.assertTrue(set(defaults.values()) <= set(archetypes))
        self.assertEqual(len(set(defaults.values())), len(defaults))
        self.assertTrue(set(archetypes) - set(defaults.values()))
        for key, values in archetypes.items():
            declared = set(values)
            self.assertLessEqual(_MANDATORY_FIELDS, declared)
            self.assertEqual(declared - _MANDATORY_FIELDS - _OPTIONAL_FIELDS, set())
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
            # Every authored archetype completes the named utility schema, so
            # no production archetype can carry partial scoring tuning.
            weights = values["utility_weights"]
            self.assertEqual(set(weights), set(UTILITY_WEIGHT_NAMES))
            for name, weight in weights.items():
                with self.subTest(archetype=key, weight=name):
                    self.assertIsInstance(weight, Real)
                    self.assertNotIsInstance(weight, bool)
                    self.assertGreaterEqual(weight, 0)
            self.assertIn(values["decision_mode"], {"legacy", "utility"})

    def test_all_six_archetypes_stay_available_with_all_legacy_production_modes(self):
        self.assertEqual(set(MONSTER_AI_TUNING.behaviour_profiles), _SIX_ARCHETYPES)
        self.assertEqual(set(BEHAVIOUR_PROFILES), _SIX_ARCHETYPES)
        for key, profile in BEHAVIOUR_PROFILES.items():
            with self.subTest(archetype=key):
                authored = MONSTER_BEHAVIOUR_YAML["archetypes"][key]
                self.assertIs(profile.decision_mode, DecisionMode.LEGACY)
                self.assertEqual(profile.target_strategy, authored["target_strategy"])
                self.assertEqual(profile.skill_choice, authored["skill_choice"])
                self.assertEqual(
                    profile.prefer_area_when_multiple_enemies,
                    authored["prefer_area_when_multiple_enemies"],
                )
                self.assertEqual(
                    profile.flee_hp_fraction, authored["flee_hp_fraction"]
                )
        # No production variant authors intelligence or a mode override yet,
        # and no tier, species or archetype supplies one.
        self.assertEqual(dict(MONSTER_AI_TUNING.variant_intelligence), {})
        self.assertEqual(dict(MONSTER_AI_TUNING.variant_decision_mode), {})
        self.assertEqual(MONSTER_AI_TUNING.candidate_budget, 256)
        self.assertRegex(MONSTER_AI_TUNING.fingerprint, r"^[0-9a-f]{64}$")

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
