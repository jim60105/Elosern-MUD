"""Data-contract test: registry-derived monster identity, profile/kit coverage and public narrative contract

Identity, ownership, default membership and the authored profile obligation are
read from the live registries themselves, so adding, renaming or retiring a row
needs no edit here and no roster is pinned. The shipped profiles and grades are
band-checked independently of the registry's own validator, construction and
reload observe the selected declaration without numerical approval copies, and
whether a row delivers a kit is its own declared data rather than a species
allowlist. The published narrative is checked for presence and public/private
separation only; the keyed bestiary documentation relationship lives in
``test_bestiary_documentation.py`` and never compares a prose sentence.
"""

import dataclasses
import unittest
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement

from world.art.subjects import is_valid_subject_key, subject_key_violation
from world.lore.combat_traits import COMBAT_TRAITS_VOCABULARY
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.monster_species import (
    MONSTER_SPECIES_REGISTRY,
    MONSTER_VARIANT_REGISTRY,
    MonsterCombatProfile,
    MonsterSpecies,
    MonsterVariant,
    validate_monster_species_registry,
)
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
from world.rules.monster_behaviour import BEHAVIOUR_PROFILES, MONSTER_BEHAVIOUR_YAML
from world.rules.monster_individual import construct_species_individual
from world.rules.traits import (
    NUMERIC_SOURCE_APPROVED_PROFILE,
    NUMERIC_SOURCE_INTERIM_TIER_BAND,
)
from world.skills.handler import INNATE_SKILL_KEYS
from world.skills.registry import SKILL_REGISTRY
from world.tests.synthetic_data import (
    make_monster_species,
    make_monster_tier,
    make_monster_variant,
    synthetic_registries,
)


def _tier_band_bases(tier_key: str) -> dict[str, int]:
    """The documented tier-band floor an optional-absence row falls back to.

    Read straight from the tier registry rather than from the rules helper, so
    the expectation is independent of the code under test.
    """
    tier = MONSTER_TIER_REGISTRY[tier_key]
    return {
        "hp": tier.hp_band[0],
        "mp": 0,
        "sp": 0,
        "atk_phys": tier.static_band.atk_phys[0],
        "agility": tier.static_band.agility[0],
        "defense": tier.static_band.defense[0],
        "magic_power": tier.static_band.magic_power[0],
    }


# The complete profile shape is stable; its authored magnitudes are mutable.
PROFILE_FIELDS = tuple(field.name for field in dataclasses.fields(MonsterCombatProfile))

# No registry field may stand in for an ability seam.
FORBIDDEN_SEAM_FIELDS = frozenset(
    {
        "skills",
        "skill_keys",
        "skill",
        "behaviour",
        "behaviour_tree",
        "behaviour_profile",
        "traits",
        "combat_traits",
        "abilities",
        "ability_key",
    }
)

PRIVATE_NOTES = ("author_hidden_truth_zh", "author_explanation_zh", "author_conjecture_zh")


def _string_values(value: object, seen: set[int], out: set[str]) -> None:
    """Collect every string reachable from one registry row."""
    if id(value) in seen:
        return
    seen.add(id(value))
    if isinstance(value, str):
        out.add(value)
    elif isinstance(value, dict):
        for key, item in value.items():
            _string_values(key, seen, out)
            _string_values(item, seen, out)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _string_values(item, seen, out)
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            _string_values(getattr(value, field.name), seen, out)


class ShippedRegistryIdentityTests(unittest.TestCase):
    """Requirement: registry membership, not a named roster, is the authority."""

    @covers_requirement(
        "monster-species-registry::authored-monster-narratives-synchronize-without-a-fixed-roster"
    )
    def test_every_shipped_species_declares_its_key_and_public_narrative(self):
        self.assertTrue(MONSTER_SPECIES_REGISTRY)
        for mapping_key, species in MONSTER_SPECIES_REGISTRY.items():
            with self.subTest(species=mapping_key):
                self.assertEqual(species.key, mapping_key)
                self.assertTrue(species.display_name_zh)
                self.assertTrue(species.published_description_zh)
                self.assertTrue(species.published_appearance_zh)
                self.assertTrue(species.published_ecology_zh)
                self.assertTrue(species.habitat_tags)
                self.assertIsInstance(species.ordinary_variant, bool)

    @covers_requirement(
        "monster-species-registry::authored-monster-narratives-synchronize-without-a-fixed-roster"
    )
    def test_every_shipped_variant_declares_its_key_owner_display_and_tier(self):
        self.assertTrue(MONSTER_VARIANT_REGISTRY)
        for mapping_key, variant in MONSTER_VARIANT_REGISTRY.items():
            with self.subTest(variant=mapping_key):
                self.assertEqual(variant.key, mapping_key)
                self.assertTrue(variant.display_name_zh)
                self.assertTrue(variant.description_zh)
                self.assertIn(variant.species_key, MONSTER_SPECIES_REGISTRY)
                self.assertIn(variant.threat_tier, MONSTER_TIER_REGISTRY)
                self.assertIsInstance(variant.ordinary_variant, bool)
                self.assertIsInstance(variant.profile_required, bool)

    @covers_requirement(
        "monster-species-registry::every-variant-belongs-to-its-species-and-the-default-variant-is-an-ordinary-variant-of-it"
    )
    def test_every_variant_is_owned_and_every_species_default_is_its_baseline(self):
        owners = {
            key: row.species_key for key, row in MONSTER_VARIANT_REGISTRY.items()
        }
        self.assertEqual(set(owners), set(MONSTER_VARIANT_REGISTRY))
        # Membership is total in both directions and no count is pinned: the
        # registry is the authority, so an added or retired row follows from
        # the data rather than from this test.
        for species_key, species in MONSTER_SPECIES_REGISTRY.items():
            with self.subTest(species=species_key):
                owned = [key for key, owner in owners.items() if owner == species_key]
                self.assertTrue(owned, "every species owns at least one variant")
                default_key = species.default_variant_key
                self.assertIn(default_key, MONSTER_VARIANT_REGISTRY)
                baseline = MONSTER_VARIANT_REGISTRY[default_key]
                self.assertEqual(baseline.species_key, species_key)
                self.assertTrue(baseline.ordinary_variant)
                self.assertEqual(species.ordinary_variant, baseline.ordinary_variant)

    @covers_requirement(
        "monster-species-registry::habitat-tags-are-compatibility-data-and-never-authorize-spawning"
    )
    def test_habitat_compatibility_tags_name_known_habitats(self):
        for key, species in MONSTER_SPECIES_REGISTRY.items():
            with self.subTest(species=key):
                self.assertTrue(species.habitat_tags)
                for tag in species.habitat_tags:
                    self.assertIn(tag, WILDERNESS_REGION_REGISTRY)


class ShippedNarrativeTests(unittest.TestCase):
    """The authored narrative fields: present, bounded and public-private split."""

    @covers_requirement(
        "monster-species-registry::authored-monster-narratives-synchronize-without-a-fixed-roster"
    )
    def test_every_shipped_species_publishes_distinct_nonempty_prose(self):
        """Detect a missing, empty or duplicated published narrative field.

        Presence and separation only: which sentences the publication carries
        is authored prose, and the keyed relationship between the publication
        and the registries is checked by the documentation contract, never by
        comparing sentences.
        """
        for key, species in MONSTER_SPECIES_REGISTRY.items():
            with self.subTest(species=key):
                self.assertTrue(species.published_description_zh)
                self.assertTrue(species.published_appearance_zh)
                self.assertTrue(species.published_ecology_zh)
                self.assertNotEqual(
                    species.published_description_zh, species.published_ecology_zh
                )

    @covers_requirement(
        "monster-species-registry::authored-monster-narratives-synchronize-without-a-fixed-roster"
    )
    def test_the_author_private_notes_keep_the_unknown_origin_boundary(self):
        for key, species in MONSTER_SPECIES_REGISTRY.items():
            with self.subTest(species=key):
                self.assertIn("沒有已定", species.author_hidden_truth_zh)
                self.assertIn("作者解釋", species.author_explanation_zh)
                self.assertIn("尚未證實", species.author_conjecture_zh)
                for private in PRIVATE_NOTES:
                    self.assertTrue(getattr(species, private))
                    for published in (
                        "published_description_zh",
                        "published_appearance_zh",
                        "published_ecology_zh",
                    ):
                        self.assertNotEqual(
                            getattr(species, private), getattr(species, published)
                        )

    @covers_requirement(
        "monster-species-registry::authored-monster-narratives-synchronize-without-a-fixed-roster"
    )
    def test_every_shipped_variant_publishes_a_nonempty_description(self):
        for key, variant in MONSTER_VARIANT_REGISTRY.items():
            with self.subTest(variant=key):
                self.assertTrue(variant.description_zh)
                self.assertTrue(variant.display_name_zh)


class BalanceSlotContentTests(unittest.TestCase):
    """Detect missing, partial or malformed current authored balance slots."""

    @covers_requirement(
        "monster-species-registry::authored-profile-requirements-are-declared-per-variant"
    )
    @covers_requirement(
        "monster-species-registry::shipped-profile-completeness-follows-authored-declarations"
    )
    def test_every_declared_required_row_carries_a_complete_profile_and_grade(self):
        self.assertEqual(
            set(PROFILE_FIELDS),
            {"hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power"},
        )
        self.assertTrue(MONSTER_VARIANT_REGISTRY)
        required = 0
        for key, variant in MONSTER_VARIANT_REGISTRY.items():
            with self.subTest(variant=key):
                self.assertIs(type(variant.profile_required), bool)
                if not variant.profile_required:
                    # Optional absence is legitimate: the row declares no
                    # obligation, and whatever it does carry is still judged
                    # against its own tier by the band check below.
                    continue
                required += 1
                profile = variant.combat_profile
                self.assertIsInstance(profile, MonsterCombatProfile)
                for name in PROFILE_FIELDS:
                    value = getattr(profile, name)
                    self.assertIs(type(value), int, name)
                    self.assertGreaterEqual(value, 0, name)
                self.assertGreater(profile.hp, 0)
                self.assertIn(variant.danger_grade, GUILD_RANK_REGISTRY)
        self.assertTrue(required, "the shipped rows declare required profiles")


    @covers_requirement(
        "monster-species-registry::authored-profile-requirements-are-declared-per-variant"
    )
    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_every_shipped_profile_and_grade_lies_inside_its_declared_tier_band(self):
        # An independent reading of the shipped facts: this does not call the
        # registry's own validator, so a validator that stopped checking would
        # still fail here. A row declaring no obligation may carry no rating at
        # all; everything a row does carry is judged against its own tier.
        self.assertTrue(MONSTER_VARIANT_REGISTRY)
        checked = 0
        for key, variant in MONSTER_VARIANT_REGISTRY.items():
            with self.subTest(variant=key):
                if variant.profile_required:
                    self.assertIsNotNone(variant.combat_profile)
                    self.assertIsNotNone(variant.danger_grade)
                tier = MONSTER_TIER_REGISTRY[variant.threat_tier]
                profile = variant.combat_profile
                if profile is not None:
                    checked += 1
                    self.assertLessEqual(tier.hp_band[0], profile.hp)
                    if tier.hp_band[1] is not None:
                        self.assertLessEqual(profile.hp, tier.hp_band[1])
                    for axis in ("atk_phys", "agility", "defense"):
                        band = getattr(tier.static_band, axis)
                        value = getattr(profile, axis)
                        self.assertLessEqual(band[0], value, axis)
                        if band[1] is not None:
                            self.assertLessEqual(value, band[1], axis)
                    magic_band = tier.static_band.magic_power
                    self.assertLessEqual(magic_band[0], profile.magic_power)
                    if magic_band[1] is not None:
                        self.assertLessEqual(profile.magic_power, magic_band[1])
                if variant.danger_grade is not None:
                    grade = GUILD_RANK_REGISTRY[variant.danger_grade]
                    bounds = [
                        GUILD_RANK_REGISTRY[rank].order
                        for rank in tier.guild_rank_range
                    ]
                    self.assertLessEqual(min(bounds), grade.order)
                    self.assertLessEqual(grade.order, max(bounds))
        self.assertTrue(checked, "the shipped rows carry rated profiles")

    def test_no_species_field_carries_an_ability_baseline(self):
        species_fields = {field.name for field in dataclasses.fields(MonsterSpecies)}
        self.assertEqual(
            species_fields
            & {"hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power"},
            set(),
        )


class ShippedProfileConstructionTests(EvenniaTestCase):
    """Observe the declared profile selection across construction and persistence."""

    @covers_requirement(
        "monster-species-registry::authored-profile-requirements-are-declared-per-variant"
    )
    @covers_requirement(
        "monster-individual-construction::shipped-variants-construct-their-declared-configuration-through-the-common-boundary",
        "monster-individual-construction::individual-numerics-come-only-from-approved-sources-with-no-scaling-and-no-baked-multipliers",
    )
    def test_every_shipped_variant_constructs_an_individual_with_those_values(self):
        from typeclasses.monsters import Monster

        self.assertTrue(MONSTER_VARIANT_REGISTRY)
        for key, variant in MONSTER_VARIANT_REGISTRY.items():
            with self.subTest(variant=key):
                profile = variant.combat_profile
                if profile is None:
                    expected_source = NUMERIC_SOURCE_INTERIM_TIER_BAND
                    expected = _tier_band_bases(variant.threat_tier)
                else:
                    expected_source = NUMERIC_SOURCE_APPROVED_PROFILE
                    expected = {name: getattr(profile, name) for name in PROFILE_FIELDS}
                with (
                    patch("world.rules.monster_individual.log_info") as info,
                    self.captureOnCommitCallbacks(execute=True),
                ):
                    individual = construct_species_individual(
                        variant.species_key, key
                    )
                self.assertEqual(info.call_count, 1)
                self.assertEqual(
                    info.call_args.kwargs["context"]["numeric_source"],
                    expected_source,
                )
                # Detect wrong variant selection and multipliers baked into bases.
                for actual in (individual, Monster.objects.get(pk=individual.pk)):
                    self.assertEqual(actual.species_key, variant.species_key)
                    self.assertEqual(actual.variant_key, key)
                    for name, base in expected.items():
                        self.assertEqual(getattr(actual.traits, name).base, base, name)
                    self.assertEqual(actual.danger_grade, variant.danger_grade)
                    declared_kit = (
                        *variant.active_skill_keys,
                        *variant.passive_skill_keys,
                    )
                    # The two declarations are independent: a row may deliver a
                    # kit without a behaviour binding, or bind a behaviour
                    # without owning a skill, and neither may fabricate the
                    # other. A row that declares neither keeps the innate
                    # actions, with nothing mounted in either place.
                    if declared_kit:
                        self.assertEqual(
                            actual.db.skills["active"], list(variant.active_skill_keys),
                        )
                        self.assertEqual(
                            actual.db.skills["passive"], list(variant.passive_skill_keys),
                        )
                    else:
                        self.assertIsNone(actual.db.skills)
                    if variant.behaviour_profile_key is not None:
                        self.assertEqual(actual.db.behaviour_tree, variant.behaviour_profile_key)
                    else:
                        self.assertIsNone(actual.db.behaviour_tree)

    @covers_requirement(
        "monster-species-registry::narrative-and-executable-monster-configurations-remain-separate"
    )
    def test_narrated_ability_prose_grants_no_ownership_or_effect(self):
        # The behaviour-selection path legitimately resolves species/variant
        # identity to select authorized tuning, so this seam is established by
        # construction instead of by scanning that module: a row whose prose
        # names a registered skill it never declares still owns none of it.
        narrated = next(
            key for key in sorted(SKILL_REGISTRY) if key not in INNATE_SKILL_KEYS
        )
        species_key = "t_prose_species"
        variant_key = "t_prose_variant"
        tier_key = "t_prose_tier"
        variant = make_monster_variant(
            variant_key,
            species_key=species_key,
            threat_tier=tier_key,
            description_zh=f"合成敘述：能施展 {narrated} 的力量。",
            active_skill_keys=(),
            passive_skill_keys=(),
            combat_profile=None,
            danger_grade=None,
            profile_required=False,
        )
        self.assertIn(narrated, variant.description_zh)
        with (
            synthetic_registries(
                "monster_tiers",
                "monster_species",
                "monster_variants",
                extra={
                    "monster_tiers": {tier_key: make_monster_tier(tier_key)},
                    "monster_species": {
                        species_key: make_monster_species(
                            species_key, default_variant_key=variant_key
                        )
                    },
                    "monster_variants": {variant_key: variant},
                },
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            individual = construct_species_individual(species_key, variant_key)
            self.assertIsNone(individual.db.skills)
            self.assertNotIn(narrated, individual.skills.owned_keys())


class SharedStableKeyContractTests(unittest.TestCase):
    def test_every_shipped_key_satisfies_the_shared_contract(self):
        keys = [*MONSTER_SPECIES_REGISTRY, *MONSTER_VARIANT_REGISTRY]
        keys.extend(row.default_variant_key for row in MONSTER_SPECIES_REGISTRY.values())
        self.assertTrue(keys)
        for key in keys:
            with self.subTest(key=key):
                self.assertTrue(is_valid_subject_key(key))
                self.assertIsNone(subject_key_violation(key))

    def test_the_registry_validates_its_own_shipped_rows_with_that_predicate(self):
        # The same construction-time validation the module runs at import,
        # re-run with the one shared stable-key implementation. Nothing in
        # world/lore/ imports world/art (the documented boundary), so this
        # registered test is where the shipped keys meet the real predicate.
        validate_monster_species_registry(
            MONSTER_SPECIES_REGISTRY,
            MONSTER_VARIANT_REGISTRY,
            key_violation_face=subject_key_violation,
        )


class AbilitySeamNegativeTests(unittest.TestCase):
    """Requirement: abilities stay narrative; no seam is faked.

    Delivery is read from each row's own declared kit, so an added or retired
    kit needs no edit here. The runtime half of the same contract - a kit-less
    row mounting no skills and no behaviour binding - is observed in
    ``ShippedProfileConstructionTests``.
    """

    def _forbidden_faces(self) -> set[str]:
        faces = set(SKILL_REGISTRY)
        faces |= set(MONSTER_BEHAVIOUR_YAML["archetypes"])
        faces |= set(BEHAVIOUR_PROFILES)
        faces |= set(COMBAT_TRAITS_VOCABULARY)
        return faces

    def test_the_comparison_faces_are_non_empty(self):
        faces = self._forbidden_faces()
        self.assertTrue(faces)
        self.assertTrue(SKILL_REGISTRY)
        self.assertTrue(MONSTER_BEHAVIOUR_YAML["archetypes"])
        self.assertTrue(COMBAT_TRAITS_VOCABULARY)

    @covers_requirement(
        "monster-species-registry::narrative-and-executable-monster-configurations-remain-separate"
    )
    def test_no_registry_string_names_a_skill_behaviour_or_combat_trait(self):
        faces = self._forbidden_faces()
        self.assertTrue(MONSTER_VARIANT_REGISTRY)
        delivering = 0
        for key, row in MONSTER_VARIANT_REGISTRY.items():
            with self.subTest(registry="variants", row=key):
                narrative = {row.display_name_zh, row.description_zh}
                self.assertEqual(narrative & faces, set())
                declared = (*row.active_skill_keys, *row.passive_skill_keys)
                if not declared and row.behaviour_profile_key is None:
                    # No delivered kit: nothing anywhere in the row may name a
                    # skill, behaviour profile or combat trait.
                    strings: set[str] = set()
                    _string_values(row, set(), strings)
                    self.assertTrue(strings)
                    self.assertEqual(strings & faces, set())
                    continue
                delivering += 1
                for skill_key in declared:
                    self.assertIn(skill_key, SKILL_REGISTRY)
                if row.behaviour_profile_key is not None:
                    self.assertIn(row.behaviour_profile_key, BEHAVIOUR_PROFILES)
        self.assertTrue(delivering)
        for key, row in MONSTER_SPECIES_REGISTRY.items():
            with self.subTest(registry="species", row=key):
                strings = set()
                _string_values(row, set(), strings)
                self.assertTrue(strings)
                self.assertEqual(strings & faces, set())

    @covers_requirement(
        "monster-species-registry::narrative-and-executable-monster-configurations-remain-separate"
    )
    def test_no_registry_field_stands_in_for_an_ability_seam(self):
        for cls in (MonsterSpecies, MonsterVariant):
            with self.subTest(cls=cls.__name__):
                names = {field.name for field in dataclasses.fields(cls)}
                self.assertEqual(names & FORBIDDEN_SEAM_FIELDS, set())

if __name__ == "__main__":
    unittest.main()
