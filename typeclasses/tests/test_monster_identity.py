"""Species-backed identity on the Monster typeclass (monster-identity-construction).

The kit's synthetic monster species/variant slice stands in for shipped lore and
the tier keys are the kit's, so no shipped key, display string, tier, or grade
appears here.
"""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.monsters import Monster
from world.rules.monster_individual import (
    MonsterIdentityError,
    MonsterTierConflictError,
    construct_species_individual,
)
from world.tests.synthetic_data import (
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_TIERS,
    SYNTH_MONSTER_VARIANTS,
    make_monster_species,
    make_monster_variant,
    synthetic_registries,
)

SPECIES_KEY = SYNTH_MONSTER_SPECIES["t_whisper_quail"].key
ORDINARY = SYNTH_MONSTER_VARIANTS["t_whisper_quail_ordinary"]
STRONGER = SYNTH_MONSTER_VARIANTS["t_whisper_quail_stronger"]
#: Two distinct registered tiers, so a contradiction is never a no-op.
TIER_KEYS = tuple(sorted(SYNTH_MONSTER_TIERS))
TIER_KEY = TIER_KEYS[0]
OTHER_TIER_KEY = TIER_KEYS[1]

_SCOPE = synthetic_registries("monster_tiers", "monster_species", "monster_variants")


@_SCOPE
class MonsterIdentityTests(EvenniaTestCase):
    """The tier-only shape and the species-backed shape, side by side."""

    def test_a_fresh_monster_stays_a_tier_only_individual(self):
        monster = create_object(Monster, key="bare")
        self.assertIsNone(monster.threat_tier)
        self.assertIsNone(monster.species_key)
        self.assertIsNone(monster.variant_key)
        self.assertIsNone(monster.danger_grade)
        with self.assertRaisesRegex(ValueError, "threat_tier"):
            monster.apply_monster_tier()

    @covers_requirement(
        "monster-individual-construction::threat-tier-and-individual-danger-resolve-from-the-variant-never-as-independent-truth"
    )
    def test_a_tier_only_individual_keeps_the_plain_attribute(self):
        monster = create_object(Monster, key="tier-only")
        monster.threat_tier = TIER_KEY
        monster.apply_monster_tier("floor")
        self.assertEqual(monster.threat_tier, TIER_KEY)
        self.assertEqual(monster.attributes.get("threat_tier"), TIER_KEY)
        self.assertGreater(monster.traits.hp.base, 0)
        self.assertEqual(monster.species_key, None)
        self.assertEqual(monster.danger_grade, None)
        # No species registry is consulted for a tier-only individual: its tier
        # is exactly the field it always was, even with no variants registered.
        with patch("world.rules.monster_individual.MONSTER_VARIANT_REGISTRY", {}):
            self.assertEqual(monster.threat_tier, TIER_KEY)
            monster.apply_monster_tier("floor")
        self.assertEqual(monster.threat_tier, TIER_KEY)

    @covers_requirement(
        "monster-individual-construction::threat-tier-and-individual-danger-resolve-from-the-variant-never-as-independent-truth"
    )
    def test_a_species_backed_individual_resolves_its_variant(self):
        monster = construct_species_individual(SPECIES_KEY, ORDINARY.key)
        self.assertEqual(monster.species_key, SPECIES_KEY)
        self.assertEqual(monster.variant_key, ORDINARY.key)
        self.assertEqual(monster.threat_tier, ORDINARY.threat_tier)
        self.assertGreater(monster.traits.hp.base, 0)
        # No stored copy of the derived tier: the variant record is the only
        # truth, so nothing can hold a value that disagrees with it.
        self.assertFalse(monster.attributes.has("threat_tier"))

    @covers_requirement(
        "monster-individual-construction::threat-tier-and-individual-danger-resolve-from-the-variant-never-as-independent-truth"
    )
    def test_the_variant_resolves_the_danger_grade(self):
        monster = construct_species_individual(SPECIES_KEY, STRONGER.key)
        self.assertEqual(monster.threat_tier, STRONGER.threat_tier)
        self.assertEqual(monster.danger_grade, STRONGER.danger_grade)
        self.assertEqual(monster.danger_grade, STRONGER.danger_grade)

    @covers_requirement(
        "monster-individual-construction::threat-tier-and-individual-danger-resolve-from-the-variant-never-as-independent-truth"
    )
    def test_a_tier_assignment_is_rejected_and_the_derived_tier_stands(self):
        monster = construct_species_individual(SPECIES_KEY, ORDINARY.key)
        for value in (OTHER_TIER_KEY, None, ORDINARY.threat_tier):
            with self.subTest(value=value):
                with self.assertRaises(MonsterTierConflictError):
                    monster.threat_tier = value
                self.assertEqual(monster.threat_tier, ORDINARY.threat_tier)
                self.assertFalse(monster.attributes.has("threat_tier"))

    @covers_requirement(
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point"
    )
    def test_a_display_name_never_carries_identity(self):
        monster = create_object(Monster, key=SYNTH_MONSTER_SPECIES["t_whisper_quail"].display_name_zh)
        self.assertIsNone(monster.species_key)
        self.assertIsNone(monster.variant_key)
        self.assertIsNone(monster.threat_tier)
        monster.threat_tier = TIER_KEY
        self.assertEqual(monster.threat_tier, TIER_KEY)
        self.assertIsNone(monster.danger_grade)

    @covers_requirement(
        "monster-individual-construction::threat-tier-and-individual-danger-resolve-from-the-variant-never-as-independent-truth"
    )
    def test_identity_and_derived_reads_survive_a_reload_and_a_registry_rename(self):
        monster = construct_species_individual(SPECIES_KEY, ORDINARY.key)
        reloaded = Monster.objects.get(pk=monster.pk)
        self.assertEqual(reloaded.species_key, SPECIES_KEY)
        self.assertEqual(reloaded.variant_key, ORDINARY.key)
        renamed = {
            ORDINARY.key: replace(ORDINARY, display_name_zh="改名後的型態"),
            STRONGER.key: STRONGER,
        }
        with patch("world.rules.monster_individual.MONSTER_VARIANT_REGISTRY", renamed):
            self.assertEqual(reloaded.species_key, SPECIES_KEY)
            self.assertEqual(reloaded.variant_key, ORDINARY.key)
            self.assertEqual(reloaded.threat_tier, ORDINARY.threat_tier)

    def test_the_tier_band_path_refuses_an_identity_bearing_individual(self):
        monster = construct_species_individual(SPECIES_KEY, STRONGER.key)
        before = monster.traits.atk_phys.base
        with self.assertRaises(MonsterIdentityError):
            monster.apply_monster_tier("floor")
        # The approved profile is untouched: the tier path cannot overwrite it.
        self.assertEqual(monster.traits.atk_phys.base, before)
        self.assertEqual(monster.traits.atk_phys.base, STRONGER.combat_profile.atk_phys)

    def test_identity_writes_are_validated(self):
        monster = create_object(Monster, key="write-guard")
        # A species key alone is not an identity, and an unresolvable key never
        # lands: the validated entry point is the only complete-identity writer.
        with self.assertRaises(MonsterIdentityError):
            monster.species_key = SPECIES_KEY
        with self.assertRaises(MonsterIdentityError):
            monster.species_key = "t_never_registered"
        with self.assertRaises(MonsterIdentityError):
            monster.variant_key = "t_never_registered"
        self.assertIsNone(monster.species_key)
        self.assertIsNone(monster.variant_key)
        self.assertIsNone(monster.threat_tier)
        # The registered pair is accepted variant-first and then reads derived.
        monster.variant_key = ORDINARY.key
        self.assertIsNone(monster.threat_tier)
        monster.species_key = SPECIES_KEY
        self.assertEqual(monster.threat_tier, ORDINARY.threat_tier)

    def test_a_cross_species_pair_cannot_be_written(self):
        species = make_monster_species(
            "t_other_species", default_variant_key="t_other_variant"
        )
        variant = make_monster_variant("t_other_variant", species_key=species.key)
        with (
            patch(
                "world.rules.monster_individual.MONSTER_SPECIES_REGISTRY",
                {**SYNTH_MONSTER_SPECIES, species.key: species},
            ),
            patch(
                "world.rules.monster_individual.MONSTER_VARIANT_REGISTRY",
                {**SYNTH_MONSTER_VARIANTS, variant.key: variant},
            ),
        ):
            monster = create_object(Monster, key="cross-species")
            monster.variant_key = ORDINARY.key
            with self.assertRaises(MonsterIdentityError):
                monster.species_key = species.key
            self.assertIsNone(monster.species_key)
            self.assertIsNone(monster.threat_tier)


if __name__ == "__main__":
    unittest.main()
