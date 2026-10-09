"""Behavior tests for species-backed monster individual construction.

Every row here is synthetic: the kit's monster catalogs plus file-local fixture
rows with invented keys and prose, and tiers whose bands are invented for these
tests. No shipped key, display string, tier, or grade is named.
"""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
from dataclasses import replace
from unittest.mock import patch

from django.db import transaction

from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.monsters import Monster
from world.lore.monster_species import MonsterCombatProfile
from world.lore.races import StaticBand
from world.rules import traits as trait_rules
from world.rules.monster_individual import (
    MonsterConstructionError,
    construct_species_individual,
)
from world.rules.traits import (
    NUMERIC_SOURCE_APPROVED_PROFILE,
    NUMERIC_SOURCE_INTERIM_TIER_BAND,
)
from world.tests.synthetic_data import (
    make_monster_species,
    make_monster_tier,
    make_monster_variant,
    synthetic_registries,
)

SPECIES = "t_made_species"
OTHER_SPECIES = "t_made_other_species"
ORDINARY = "t_made_ordinary"
STRONGER = "t_made_stronger"
ORPHAN = "t_made_orphan"
TIER = "t_made_band"
STRONGER_TIER = "t_made_band_above"
ABSENT_SPECIES = "t_made_absent_species"
ABSENT_VARIANT = "t_made_absent_variant"
GRADE = "t_made_grade"

#: The invented band the interim rule resolves through: the physical axes carry
#: distinguishable floors, MP/SP are the tier path's documented zeros, and the
#: magic axis is the zero band every monster tier declares.
BAND = StaticBand(atk_phys=(5, 9), agility=(4, 8), defense=(3, 7), magic_power=(0, 0))
STRONGER_BAND = StaticBand(
    atk_phys=(25, 29), agility=(24, 28), defense=(23, 27), magic_power=(0, 0)
)

TIER_ROW = make_monster_tier(TIER, hp_band=(11, 21), static_band=BAND)
STRONGER_TIER_ROW = make_monster_tier(
    STRONGER_TIER, hp_band=(31, 41), static_band=STRONGER_BAND
)

SPECIES_ROW = make_monster_species(
    SPECIES, default_variant_key=ORDINARY, ordinary_variant=True
)
OTHER_SPECIES_ROW = make_monster_species(
    OTHER_SPECIES, default_variant_key=ORDINARY, ordinary_variant=True
)

#: The ordinary variant carries no approved profile and flavour prose that
#: mentions magic, so the interim rule cannot borrow a number from the narrative.
ORDINARY_ROW = make_monster_variant(
    ORDINARY,
    species_key=SPECIES,
    description_zh="合成敘述：以魔力震落穀粒，並能汲取附近的法力。",
    threat_tier=TIER,
    ordinary_variant=True,
    combat_profile=None,
    danger_grade=None,
)
#: The stronger variant authors a complete profile whose literals differ from
#: every band value, so "the approved source replaced the interim one" is
#: observable without any signature change.
PROFILE = MonsterCombatProfile(
    hp=61, mp=17, sp=9, atk_phys=13, agility=5, defense=7, magic_power=3
)
STRONGER_ROW = make_monster_variant(
    STRONGER,
    species_key=SPECIES,
    threat_tier=STRONGER_TIER,
    ordinary_variant=False,
    combat_profile=PROFILE,
    danger_grade=GRADE,
)
#: Registered in the variant registry while its species key resolves nowhere.
ORPHAN_ROW = make_monster_variant(
    ORPHAN, species_key=ABSENT_SPECIES, threat_tier=TIER
)

_SCOPE = synthetic_registries(
    "monster_tiers",
    "monster_species",
    "monster_variants",
    extra={
        "monster_tiers": {TIER: TIER_ROW, STRONGER_TIER: STRONGER_TIER_ROW},
        "monster_species": {SPECIES: SPECIES_ROW, OTHER_SPECIES: OTHER_SPECIES_ROW},
        "monster_variants": {
            ORDINARY: ORDINARY_ROW,
            STRONGER: STRONGER_ROW,
            ORPHAN: ORPHAN_ROW,
        },
    },
)


def _object_count() -> int:
    """Every database row of any object: the before/after construction probe."""
    return ObjectDB.objects.count()


def _stored_values(individual) -> dict[str, int]:
    return {key: getattr(individual.traits, key).base for key in trait_rules.TRAIT_KEYS}


@_SCOPE
class MonsterIndividualConstructionTests(EvenniaTestCase):
    """The one validated entry point and the numeric sources it may use."""

    @covers_requirement(
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point"
    )
    def test_unknown_and_mismatched_identities_build_nothing(self):
        cases = (
            ("unknown species", ABSENT_SPECIES, ORDINARY),
            ("unknown variant", SPECIES, ABSENT_VARIANT),
            ("variant of another species", OTHER_SPECIES, ORDINARY),
            ("variant naming an unregistered species", ABSENT_SPECIES, ORPHAN),
        )
        for label, species_key, variant_key in cases:
            with self.subTest(case=label):
                before = _object_count()
                with self.assertRaises(MonsterConstructionError):
                    construct_species_individual(species_key, variant_key)
                self.assertEqual(_object_count(), before)

    def test_an_unresolvable_numeric_source_builds_nothing(self):
        before = _object_count()
        with self.assertRaises(MonsterConstructionError):
            construct_species_individual(SPECIES, ORDINARY, position="nowhere")
        self.assertEqual(_object_count(), before)

    @covers_requirement(
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point"
    )
    def test_a_failed_application_leaves_no_individual_and_no_event(self):
        before = _object_count()
        with (
            patch.object(Monster, "_apply_trait_config", side_effect=RuntimeError("boom")),
            patch("world.rules.monster_individual.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(MonsterConstructionError):
                construct_species_individual(SPECIES, ORDINARY)
        self.assertEqual(_object_count(), before)
        self.assertEqual(info.call_count, 0)

    def test_a_creation_failure_surfaces_as_the_named_construction_error(self):
        before = _object_count()
        with (
            patch(
                "evennia.utils.create.create_object",
                side_effect=RuntimeError("creation hook failed"),
            ),
            patch("world.rules.monster_individual.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(MonsterConstructionError):
                construct_species_individual(SPECIES, ORDINARY)
        self.assertEqual(_object_count(), before)
        self.assertEqual(info.call_count, 0)

    @covers_requirement(
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point"
    )
    def test_a_rolled_back_construction_leaves_no_row_and_no_event(self):
        before = _object_count()
        with (
            patch("world.rules.monster_individual.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                individual = construct_species_individual(SPECIES, ORDINARY)
                self.assertIsNotNone(individual.pk)
                transaction.set_rollback(True)
        # The construction boundary records a durable commit, so a rollback
        # leaves neither the individual nor a log line for it.
        self.assertEqual(_object_count(), before)
        self.assertEqual(info.call_count, 0)

    @covers_requirement(
        "monster-individual-construction::threat-tier-and-individual-danger-resolve-from-the-variant-never-as-independent-truth"
    )
    def test_a_retired_variant_record_degrades_the_reads(self):
        individual = construct_species_individual(SPECIES, ORDINARY)
        before = _stored_values(individual)
        with patch("world.rules.monster_individual.MONSTER_VARIANT_REGISTRY", {}):
            # A read must not raise out of the surfaces that render, examine, or
            # attack this individual: the derived values become the same optional
            # absence a tier-only individual carries.
            self.assertIsNone(individual.threat_tier)
            self.assertIsNone(individual.danger_grade)
            self.assertEqual(str(individual.key), ORDINARY_ROW.display_name_zh)
            self.assertEqual(_stored_values(individual), before)
        # The identity keys survive, so a registry repair restores the reads.
        self.assertEqual(individual.threat_tier, TIER)

    @covers_requirement(
        "monster-individual-construction::individual-numerics-come-only-from-approved-sources-with-no-scaling-and-no-baked-multipliers"
    )
    def test_the_interim_source_is_the_declared_tier_band_literally(self):
        individual = construct_species_individual(SPECIES, ORDINARY)
        expected = trait_rules.initial_trait_config_for_monster_tier(TIER, "floor")
        for trait_key, properties in expected.items():
            self.assertEqual(
                getattr(individual.traits, trait_key).base, properties["base"], trait_key
            )
        # The magical prose contributes no resource: the tier band's values are
        # used exactly as they are.
        self.assertEqual(individual.traits.mp.base, 0)
        self.assertEqual(individual.traits.sp.base, 0)
        self.assertEqual(
            individual.traits.magic_power.base, BAND.magic_power[0]
        )
        self.assertEqual(individual.traits.hp.base, TIER_ROW.hp_band[0])

    @covers_requirement(
        "monster-individual-construction::individual-numerics-come-only-from-approved-sources-with-no-scaling-and-no-baked-multipliers"
    )
    def test_an_approved_profile_replaces_the_interim_source(self):
        individual = construct_species_individual(SPECIES, STRONGER)
        self.assertEqual(
            _stored_values(individual),
            {
                "hp": PROFILE.hp,
                "mp": PROFILE.mp,
                "sp": PROFILE.sp,
                "atk_phys": PROFILE.atk_phys,
                "agility": PROFILE.agility,
                "defense": PROFILE.defense,
                "magic_power": PROFILE.magic_power,
                "guild_merit": 0,
            },
        )
        # The stored values are the authored literals: no damage or effect
        # multiplier is folded in, and no skill multiplier is pre-merged.
        self.assertEqual(individual.traits.atk_phys.mod, 0)
        self.assertEqual(individual.traits.magic_power.mod, 0)

    @covers_requirement(
        "monster-individual-construction::individual-numerics-come-only-from-approved-sources-with-no-scaling-and-no-baked-multipliers"
    )
    def test_construction_takes_no_player_input_and_repeats_identically(self):
        parameters = set(inspect.signature(construct_species_individual).parameters)
        self.assertEqual(
            parameters & {"actor", "player", "level", "tick", "clock", "progression"},
            set(),
        )
        first = construct_species_individual(SPECIES, ORDINARY)
        second = construct_species_individual(SPECIES, ORDINARY)
        self.assertEqual(_stored_values(first), _stored_values(second))
        self.assertEqual(first.threat_tier, second.threat_tier)
        self.assertEqual(first.traits.hp.max, second.traits.hp.max)

    @covers_requirement(
        "monster-individual-construction::threat-tier-and-individual-danger-resolve-from-the-variant-never-as-independent-truth"
    )
    def test_the_variant_resolves_the_individual_tier_and_grade(self):
        individual = construct_species_individual(SPECIES, STRONGER)
        self.assertEqual(individual.threat_tier, STRONGER_ROW.threat_tier)
        self.assertEqual(individual.danger_grade, GRADE)
        # No copy of the derived tier is stored, so no attribute can ever drift
        # away from the registry record it resolves from.
        self.assertFalse(individual.attributes.has("threat_tier"))

    @covers_requirement(
        "monster-individual-construction::individual-numerics-come-only-from-approved-sources-with-no-scaling-and-no-baked-multipliers"
    )
    def test_one_boundary_event_records_the_numeric_source(self):
        cases = (
            (ORDINARY, NUMERIC_SOURCE_INTERIM_TIER_BAND),
            (STRONGER, NUMERIC_SOURCE_APPROVED_PROFILE),
        )
        for variant_key, expected_source in cases:
            with self.subTest(variant=variant_key):
                with (
                    patch("world.rules.monster_individual.log_info") as info,
                    self.captureOnCommitCallbacks(execute=True),
                ):
                    individual = construct_species_individual(SPECIES, variant_key)
                self.assertEqual(info.call_count, 1)
                self.assertEqual(
                    info.call_args.args[0], "monster_individual_constructed"
                )
                self.assertEqual(
                    info.call_args.kwargs["context"],
                    {
                        "individual": individual.pk,
                        "species": SPECIES,
                        "variant": variant_key,
                        "numeric_source": expected_source,
                        "kit": (),
                        "profile": None,
                    },
                )

    @covers_requirement(
        "monster-individual-construction::threat-tier-and-individual-danger-resolve-from-the-variant-never-as-independent-truth"
    )
    def test_a_registry_edit_does_not_rescale_an_existing_individual(self):
        individual = construct_species_individual(SPECIES, ORDINARY)
        before = _stored_values(individual)
        gauges = {
            key: getattr(individual.traits, key).current for key in ("hp", "mp", "sp")
        }
        rebalanced = {
            ORDINARY: replace(
                ORDINARY_ROW,
                description_zh="合成敘述：重新平衡後的版本。",
                threat_tier=STRONGER_TIER,
                combat_profile=PROFILE,
                danger_grade=GRADE,
            ),
            STRONGER: STRONGER_ROW,
            ORPHAN: ORPHAN_ROW,
        }
        with patch("world.rules.monster_individual.MONSTER_VARIANT_REGISTRY", rebalanced):
            self.assertEqual(_stored_values(individual), before)
            self.assertEqual(
                {
                    key: getattr(individual.traits, key).current
                    for key in ("hp", "mp", "sp")
                },
                gauges,
            )
            # The tier is a registry-derived read, never a stored copy, so the
            # edit changes what the individual resolves to without touching the
            # resources it already holds.
            self.assertEqual(individual.threat_tier, STRONGER_TIER)

    @covers_requirement(
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point"
    )
    def test_identity_is_carried_by_keys_and_survives_a_reload(self):
        individual = construct_species_individual(SPECIES, ORDINARY, key="標籤")
        self.assertEqual(str(individual.key), "標籤")
        reloaded = Monster.objects.get(pk=individual.pk)
        self.assertEqual(reloaded.species_key, SPECIES)
        self.assertEqual(reloaded.variant_key, ORDINARY)
        # The default display label is the variant's approved text; identity is
        # still the keys, never the name.
        self.assertEqual(
            str(construct_species_individual(SPECIES, ORDINARY).key),
            ORDINARY_ROW.display_name_zh,
        )

    @covers_requirement(
        "monster-individual-construction::species-backed-individuals-are-constructed-through-one-validated-deterministic-entry-point",
        "monster-species-registry::variant-skill-kits-and-behavior-references-are-immutable-authored-configuration",
    )
    def test_kit_and_behaviour_profile_validation_and_assignment(self):
        from world.tests.synthetic_data import make_skill
        from world.skills.registry import SkillKind, TargetSpec

        # Valid active skill
        valid_skill = make_skill("t_test_active_monster", kind=SkillKind.ACTIVE, target_spec=TargetSpec.SINGLE)
        invalid_kind = make_skill("t_test_passive_as_active", kind=SkillKind.PASSIVE)

        with patch.dict(
            "world.skills.registry.SKILL_REGISTRY",
            {valid_skill.key: valid_skill, invalid_kind.key: invalid_kind},
        ):
            # Case 1: Unknown skill key
            bad_variant_1 = replace(ORDINARY_ROW, active_skill_keys=("t_nonexistent_skill",))
            base_variants = {ORDINARY: ORDINARY_ROW, STRONGER: STRONGER_ROW, ORPHAN: ORPHAN_ROW}
            mapping_1 = dict(base_variants, **{ORDINARY: bad_variant_1})
            with patch("world.rules.monster_individual.MONSTER_VARIANT_REGISTRY", mapping_1):
                with self.assertRaises(MonsterConstructionError):
                    construct_species_individual(SPECIES, ORDINARY)

            # Case 2: Wrong kind (passive declared as active)
            bad_variant_2 = replace(ORDINARY_ROW, active_skill_keys=(invalid_kind.key,))
            mapping_2 = dict(base_variants, **{ORDINARY: bad_variant_2})
            with patch("world.rules.monster_individual.MONSTER_VARIANT_REGISTRY", mapping_2):
                with self.assertRaises(MonsterConstructionError):
                    construct_species_individual(SPECIES, ORDINARY)

            # Case 3: Unknown behaviour profile key
            bad_variant_3 = replace(ORDINARY_ROW, behaviour_profile_key="unknown_profile")
            mapping_3 = dict(base_variants, **{ORDINARY: bad_variant_3})
            with patch("world.rules.monster_individual.MONSTER_VARIANT_REGISTRY", mapping_3):
                with self.assertRaises(MonsterConstructionError):
                    construct_species_individual(SPECIES, ORDINARY)

            # Case 4: Successful construction with kit and profile
            good_variant = replace(
                ORDINARY_ROW,
                active_skill_keys=(valid_skill.key,),
                behaviour_profile_key="ambush_predator",
            )
            mapping_good = dict(base_variants, **{ORDINARY: good_variant})
            with patch("world.rules.monster_individual.MONSTER_VARIANT_REGISTRY", mapping_good):
                with (
                    patch("world.rules.monster_individual.log_info") as info,
                    self.captureOnCommitCallbacks(execute=True),
                ):
                    individual = construct_species_individual(SPECIES, ORDINARY)
                self.assertEqual(individual.db.skills["active"], [valid_skill.key])
                self.assertEqual(individual.db.behaviour_tree, "ambush_predator")
                self.assertEqual(
                    info.call_args.kwargs["context"]["kit"], (valid_skill.key,)
                )
                self.assertEqual(
                    info.call_args.kwargs["context"]["profile"], "ambush_predator"
                )

            # Case 5: Rollback suppresses boundary event
            with patch("world.rules.monster_individual.log_info") as info:
                try:
                    with transaction.atomic():
                        construct_species_individual(SPECIES, ORDINARY)
                        raise RuntimeError("rollback injection")
                except RuntimeError:
                    pass
            self.assertEqual(info.call_count, 0)


if __name__ == "__main__":
    unittest.main()
