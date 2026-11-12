"""Data-contract test: monster behaviour rulebook contract
Rulebook coverage and monster profile resolution."""

from tools.spec_traceability import covers_requirement

import unittest
from numbers import Real

from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.monster_species import MONSTER_VARIANT_REGISTRY
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
_OPTIONAL_FIELDS = {"decision_mode", "utility_weights", "reflex_temperature"}
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
            self.assertIn(values["decision_mode"], {"reflex", "deliberation"})
            # A highest_expected_damage profile must author the temperature it
            # samples by; a first_owned profile may omit it entirely.
            if values["skill_choice"] == "highest_expected_damage":
                self.assertGreater(values["reflex_temperature"], 0)
                self.assertIsInstance(values["reflex_temperature"], Real)
                self.assertNotIsInstance(values["reflex_temperature"], bool)
            else:
                self.assertNotIn("reflex_temperature", values)

    @covers_requirement("monster-behaviour-profile::ai-tuning-is-strict-and-startup-scoped")
    def test_all_six_archetypes_stay_available_with_their_own_reflex_modes(self):
        self.assertEqual(set(MONSTER_AI_TUNING.behaviour_profiles), _SIX_ARCHETYPES)
        self.assertEqual(set(BEHAVIOUR_PROFILES), _SIX_ARCHETYPES)
        for key, profile in BEHAVIOUR_PROFILES.items():
            with self.subTest(archetype=key):
                authored = MONSTER_BEHAVIOUR_YAML["archetypes"][key]
                self.assertIs(profile.decision_mode, DecisionMode.REFLEX)
                self.assertEqual(profile.target_strategy, authored["target_strategy"])
                self.assertEqual(profile.skill_choice, authored["skill_choice"])
                self.assertEqual(
                    profile.prefer_area_when_multiple_enemies,
                    authored["prefer_area_when_multiple_enemies"],
                )
                self.assertEqual(
                    profile.flee_hp_fraction, authored["flee_hp_fraction"]
                )
                if profile.skill_choice == "highest_expected_damage":
                    # The evaluating profiles sample exact own-output estimates
                    # by their own authored raw-E-unit temperature.
                    self.assertGreater(profile.reflex_temperature, 0)
                    self.assertIsInstance(profile.reflex_temperature, float)
                else:
                    self.assertIsNone(profile.reflex_temperature)
        # Every archetype keeps its own reflex mode, so the ONLY way a
        # production variant leaves the reflex decision is its own registered
        # override: each mapped key is a registered variant with a recorded
        # binding and an explicit intelligence. Which variants those are, and
        # that every other registered variant still resolves reflex, is
        # established behaviourally by
        # ``world.rules.tests.test_monster_ai_activation``.
        for key, mode in MONSTER_AI_TUNING.variant_decision_mode.items():
            with self.subTest(variant=key):
                self.assertIn(key, MONSTER_VARIANT_REGISTRY)
                self.assertIsInstance(mode, DecisionMode)
                self.assertIn(key, MONSTER_AI_TUNING.variant_bindings)
        for key, value in MONSTER_AI_TUNING.variant_intelligence.items():
            with self.subTest(variant=key):
                self.assertIn(key, MONSTER_VARIANT_REGISTRY)
                self.assertIsInstance(value, int)
                self.assertNotIsInstance(value, bool)
        self.assertEqual(
            set(MONSTER_AI_TUNING.variant_bindings),
            set(MONSTER_AI_TUNING.variant_decision_mode)
            | set(MONSTER_AI_TUNING.variant_intelligence),
        )
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

    def test_a_tier_default_installed_after_import_reaches_resolution(self):
        """A tier this process mounts later still resolves one archetype."""
        from world.rules import monster_behaviour as behaviour

        monster = type(
            "MonsterFixture",
            (),
            {"threat_tier": "t_grafted", "behaviour_tree": None},
        )()
        before = behaviour.resolve_monster_ai(monster)
        self.assertIs(
            before.invalid_reason, behaviour.InvalidDecisionReason.INVALID_BINDING
        )
        self.addCleanup(
            setattr, behaviour, "MONSTER_AI_TUNING", behaviour.MONSTER_AI_TUNING
        )
        installed = behaviour.install_tier_defaults({"t_grafted": "instinctive"})
        after = behaviour.resolve_monster_ai(monster)
        self.assertEqual(after.archetype_key, "instinctive")
        self.assertIsNone(after.invalid_reason)
        # A tier default is a decision-relevant input, so the record's
        # fingerprint changes with it.
        self.assertNotEqual(installed.fingerprint, before.tuning_fingerprint)
        with self.assertRaises(behaviour.MonsterBehaviourConfigError):
            behaviour.install_tier_defaults({"t_grafted": "no_such_archetype"})
