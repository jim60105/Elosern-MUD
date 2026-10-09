"""Data-contract test: approved first-batch bestiary narrative, balance-profile and danger-grade contract

The shipped species/variant registries are authored content: this is the one
place allowed to name it. It pins the six approved species and their twelve
approved named variant directions (content-approved 2026-10-05), the approved
zh-TW narrative landed in the published fields, the user-approved complete
combat profile and guild danger grade of every shipped variant together with
its membership in the tier band that variant declares (balance-approved
2026-10-08), the values and numeric source a constructed individual stores, the
shared stable-key contract, and the negative guarantee that the registries name
no skill key, behaviour profile, or combat trait.
"""

import ast
import dataclasses
import pathlib
import re
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
    initial_trait_config_for_variant,
)
from world.skills.registry import SKILL_REGISTRY

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
BESTIARY = REPO_ROOT / "docs" / "lore" / "bestiary.md"
BEHAVIOUR_SELECTION_MODULE = REPO_ROOT / "world" / "rules" / "monster_behaviour.py"


def _normalised(text: str) -> str:
    """The text with whitespace and markdown emphasis removed."""
    return re.sub(r"[\s`*]+", "", text)


def _sentences(text: str) -> list[str]:
    """The full-stop separated sentences of one shipped display string."""
    return [piece for piece in text.split("。") if piece.strip()]

# The approved bestiary batch: species key -> (display name, default variant key).
APPROVED_SPECIES = {
    "sway_whistle_sparrow": ("穗鳴雀", "grain_pecker"),
    "tide_lamp_crab": ("潮燈蟹", "shore_walker"),
    "ridge_burrow_hare": ("築埂兔", "burrow_maker"),
    "rock_echo_goat": ("岩響山羊", "cliff_stepper"),
    "fog_mane_lynx": ("霧鬃山貓", "wood_stalker"),
    "tide_devouring_crocodile": ("吞潮鱷", "bank_lurker"),
}

# The approved named variant directions: variant key ->
# (owning species key, display name, threat tier, ordinary classification).
APPROVED_VARIANTS = {
    "grain_pecker": ("sway_whistle_sparrow", "啄穗型", "low", True),
    "flock_leader": ("sway_whistle_sparrow", "領群型", "low", False),
    "shore_walker": ("tide_lamp_crab", "灘行型", "low", True),
    "reef_warden": ("tide_lamp_crab", "守礁型", "low", False),
    "burrow_maker": ("ridge_burrow_hare", "掘巢型", "low", True),
    "nest_guard": ("ridge_burrow_hare", "護巢型", "low", False),
    "cliff_stepper": ("rock_echo_goat", "踏崖型", "mid", True),
    "pass_warden": ("rock_echo_goat", "守隘型", "mid", False),
    "wood_stalker": ("fog_mane_lynx", "林伏型", "mid", True),
    "trail_hunter": ("fog_mane_lynx", "獵道型", "mid", False),
    "bank_lurker": ("tide_devouring_crocodile", "潛岸型", "mid", True),
    "bay_warden": ("tide_devouring_crocodile", "守灣型", "mid", False),
}

# The user's balance approval (2026-10-08, `human-monster-balance-data`):
# variant key -> the approved complete combat profile and guild danger grade.
# These are the approved literals verbatim; the registry must reproduce them
# field for field, and a value that differs is a content defect, not a
# re-tuning decision. MP, SP and magic_power are authored zeros: no approved
# ability mechanic consumes a pool and every tier's magic band is (0, 0).
APPROVED_BALANCE = {
    "grain_pecker": {
        "hp": 30,
        "mp": 0,
        "sp": 0,
        "atk_phys": 4,
        "agility": 7,
        "defense": 3,
        "magic_power": 0,
        "danger_grade": "F",
    },
    "flock_leader": {
        "hp": 55,
        "mp": 0,
        "sp": 0,
        "atk_phys": 8,
        "agility": 10,
        "defense": 4,
        "magic_power": 0,
        "danger_grade": "E",
    },
    "shore_walker": {
        "hp": 30,
        "mp": 0,
        "sp": 0,
        "atk_phys": 5,
        "agility": 4,
        "defense": 5,
        "magic_power": 0,
        "danger_grade": "F",
    },
    "reef_warden": {
        "hp": 60,
        "mp": 0,
        "sp": 0,
        "atk_phys": 12,
        "agility": 4,
        "defense": 7,
        "magic_power": 0,
        "danger_grade": "E",
    },
    "burrow_maker": {
        "hp": 30,
        "mp": 0,
        "sp": 0,
        "atk_phys": 4,
        "agility": 8,
        "defense": 3,
        "magic_power": 0,
        "danger_grade": "F",
    },
    "nest_guard": {
        "hp": 55,
        "mp": 0,
        "sp": 0,
        "atk_phys": 11,
        "agility": 6,
        "defense": 6,
        "magic_power": 0,
        "danger_grade": "E",
    },
    "cliff_stepper": {
        "hp": 130,
        "mp": 0,
        "sp": 0,
        "atk_phys": 20,
        "agility": 16,
        "defense": 12,
        "magic_power": 0,
        "danger_grade": "D",
    },
    "pass_warden": {
        "hp": 170,
        "mp": 0,
        "sp": 0,
        "atk_phys": 26,
        "agility": 14,
        "defense": 14,
        "magic_power": 0,
        "danger_grade": "C",
    },
    "wood_stalker": {
        "hp": 115,
        "mp": 0,
        "sp": 0,
        "atk_phys": 20,
        "agility": 20,
        "defense": 10,
        "magic_power": 0,
        "danger_grade": "D",
    },
    "trail_hunter": {
        "hp": 165,
        "mp": 0,
        "sp": 0,
        "atk_phys": 25,
        "agility": 22,
        "defense": 12,
        "magic_power": 0,
        "danger_grade": "C",
    },
    "bank_lurker": {
        "hp": 140,
        "mp": 30,
        "sp": 40,
        "atk_phys": 22,
        "agility": 12,
        "defense": 14,
        "magic_power": 0,
        "danger_grade": "D",
    },
    "bay_warden": {
        "hp": 210,
        "mp": 50,
        "sp": 60,
        "atk_phys": 28,
        "agility": 12,
        "defense": 15,
        "magic_power": 0,
        "danger_grade": "C",
    },
}

# The seven numeric fields a profile carries, read from the record itself, so
# the approval table can never drift away from the profile it pins.
PROFILE_FIELDS = tuple(field.name for field in dataclasses.fields(MonsterCombatProfile))

# One approved ability-limit clause per species: the narrative carries each
# approved special ability's own boundary text and nothing executable.
APPROVED_ABILITY_LIMITS = {
    "sway_whistle_sparrow": "無法掀翻糧車",
    "tide_lamp_crab": "不能製造幻覺或偽裝物體",
    "ridge_burrow_hare": "無法鑽穿岩盤",
    "rock_echo_goat": "脈動無法粉碎完整岩盤",
    "fog_mane_lynx": "不能完全隱形",
    "tide_devouring_crocodile": "不能隔著整條河抽取魔力",
}

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


class ApprovedBestiaryContentTests(unittest.TestCase):
    @covers_requirement(
        "monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently"
    )
    def test_the_registry_carries_the_six_approved_species_and_no_others(self):
        self.assertEqual(set(MONSTER_SPECIES_REGISTRY), set(APPROVED_SPECIES))
        for key, (display_name, default_variant) in APPROVED_SPECIES.items():
            with self.subTest(species=key):
                species = MONSTER_SPECIES_REGISTRY[key]
                self.assertEqual(species.key, key)
                self.assertEqual(species.display_name_zh, display_name)
                self.assertEqual(species.default_variant_key, default_variant)
                self.assertTrue(species.ordinary_variant)

    @covers_requirement(
        "monster-species-registry::every-variant-belongs-to-its-species-and-the-default-variant-is-an-ordinary-variant-of-it"
    )
    def test_each_species_baseline_is_its_own_ordinary_variant(self):
        for key, (_display_name, default_variant) in APPROVED_SPECIES.items():
            with self.subTest(species=key):
                variant = MONSTER_VARIANT_REGISTRY[default_variant]
                self.assertEqual(variant.species_key, key)
                self.assertTrue(variant.ordinary_variant)

    @covers_requirement(
        "monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently"
    )
    def test_the_registry_carries_the_twelve_approved_variant_directions(self):
        self.assertEqual(set(MONSTER_VARIANT_REGISTRY), set(APPROVED_VARIANTS))
        for key, (species_key, display_name, tier, ordinary) in APPROVED_VARIANTS.items():
            with self.subTest(variant=key):
                variant = MONSTER_VARIANT_REGISTRY[key]
                self.assertEqual(variant.key, key)
                self.assertEqual(variant.species_key, species_key)
                self.assertEqual(variant.display_name_zh, display_name)
                self.assertEqual(variant.threat_tier, tier)
                self.assertEqual(variant.ordinary_variant, ordinary)

    @covers_requirement(
        "monster-species-registry::every-variant-belongs-to-its-species-and-the-default-variant-is-an-ordinary-variant-of-it"
    )
    def test_every_variant_is_an_ordinary_or_stronger_form_of_one_species(self):
        owners = {
            key: row.species_key for key, row in MONSTER_VARIANT_REGISTRY.items()
        }
        self.assertEqual(len(owners), len(APPROVED_VARIANTS))
        for species_key, (_name, default_variant) in APPROVED_SPECIES.items():
            owned = sorted(
                key for key, owner in owners.items() if owner == species_key
            )
            self.assertEqual(len(owned), 2)
            self.assertIn(default_variant, owned)
            self.assertEqual(
                sum(MONSTER_VARIANT_REGISTRY[key].ordinary_variant for key in owned), 1
            )

    @covers_requirement(
        "monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently"
    )
    def test_the_published_narrative_is_the_approved_zh_tw_prose(self):
        for key in APPROVED_SPECIES:
            with self.subTest(species=key):
                species = MONSTER_SPECIES_REGISTRY[key]
                self.assertTrue(species.published_description_zh)
                self.assertTrue(species.published_appearance_zh)
                self.assertTrue(species.published_ecology_zh)
                self.assertIn(
                    APPROVED_ABILITY_LIMITS[key],
                    species.published_ecology_zh,
                    "the approved ability boundary clause is missing",
                )
                self.assertNotEqual(
                    species.published_description_zh, species.published_ecology_zh
                )

    def test_the_author_private_notes_keep_the_unknown_origin_boundary(self):
        for key in APPROVED_SPECIES:
            with self.subTest(species=key):
                species = MONSTER_SPECIES_REGISTRY[key]
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
        "monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently"
    )
    def test_every_published_string_is_verbatim_approved_prose_in_order(self):
        """Each published sentence is the approved bestiary text, in its order."""
        haystack = _normalised(BESTIARY.read_text(encoding="utf-8"))
        self.assertTrue(haystack)

        def assert_sentences_are_approved(source: str, field: str, value: str) -> None:
            sentences = [_normalised(piece) for piece in _sentences(value)]
            self.assertTrue(sentences, f"{source}.{field} carries no prose")
            cursor = 0
            for sentence in sentences:
                index = haystack.find(sentence, cursor)
                self.assertGreaterEqual(
                    index,
                    cursor,
                    f"{source}.{field} sentence {sentence!r} is not approved "
                    "bestiary prose in its published order",
                )
                cursor = index + len(sentence)

        for key in APPROVED_SPECIES:
            with self.subTest(species=key):
                species = MONSTER_SPECIES_REGISTRY[key]
                for field in (
                    "published_description_zh",
                    "published_appearance_zh",
                    "published_ecology_zh",
                ):
                    assert_sentences_are_approved(key, field, getattr(species, field))
        for key in APPROVED_VARIANTS:
            with self.subTest(variant=key):
                assert_sentences_are_approved(
                    key, "description_zh", MONSTER_VARIANT_REGISTRY[key].description_zh
                )

    @covers_requirement(
        "monster-species-registry::habitat-tags-are-compatibility-data-and-never-authorize-spawning"
    )
    def test_habitat_compatibility_tags_name_known_habitats(self):
        for key in APPROVED_SPECIES:
            with self.subTest(species=key):
                tags = MONSTER_SPECIES_REGISTRY[key].habitat_tags
                self.assertTrue(tags)
                for tag in tags:
                    self.assertIn(tag, WILDERNESS_REGION_REGISTRY)


class BalanceSlotContentTests(unittest.TestCase):
    """The approved literals, and only them, in the shipped balance slots."""

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    @covers_requirement(
        "monster-species-registry::the-approved-first-batch-profiles-and-grades-are-user-approved-literals"
    )
    def test_every_shipped_variant_carries_its_approved_literal_profile_and_grade(self):
        for key, approved in APPROVED_BALANCE.items():
            with self.subTest(variant=key):
                self.assertEqual(
                    set(approved), set(PROFILE_FIELDS) | {"danger_grade"}
                )
                variant = MONSTER_VARIANT_REGISTRY[key]
                profile = variant.combat_profile
                self.assertIsInstance(profile, MonsterCombatProfile)
                for name in PROFILE_FIELDS:
                    self.assertEqual(
                        getattr(profile, name), approved[name], name
                    )
                self.assertEqual(variant.danger_grade, approved["danger_grade"])

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    @covers_requirement(
        "monster-species-registry::the-approved-first-batch-profiles-and-grades-are-user-approved-literals"
    )
    def test_no_variant_outside_the_approved_batch_carries_a_profile_or_grade(self):
        unapproved = set(MONSTER_VARIANT_REGISTRY) - set(APPROVED_BALANCE)
        for key in sorted(unapproved):
            with self.subTest(variant=key):
                variant = MONSTER_VARIANT_REGISTRY[key]
                self.assertIsNone(variant.combat_profile)
                self.assertIsNone(variant.danger_grade)

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    @covers_requirement(
        "monster-species-registry::every-shipped-combat-profile-and-danger-grade-lies-inside-its-declared-tier-band"
    )
    def test_every_shipped_profile_and_grade_lies_inside_its_declared_tier_band(self):
        # An independent reading of the shipped facts: this does not call the
        # registry's own validator, so a validator that stopped checking would
        # still fail here.
        self.assertTrue(MONSTER_VARIANT_REGISTRY)
        for key, variant in MONSTER_VARIANT_REGISTRY.items():
            with self.subTest(variant=key):
                tier = MONSTER_TIER_REGISTRY[variant.threat_tier]
                profile = variant.combat_profile
                self.assertIsNotNone(profile)
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
                grade = GUILD_RANK_REGISTRY[variant.danger_grade]
                bounds = [
                    GUILD_RANK_REGISTRY[rank].order
                    for rank in tier.guild_rank_range
                ]
                self.assertLessEqual(min(bounds), grade.order)
                self.assertLessEqual(grade.order, max(bounds))

    def test_no_species_field_carries_an_ability_baseline(self):
        species_fields = {field.name for field in dataclasses.fields(MonsterSpecies)}
        self.assertEqual(
            species_fields
            & {"hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power"},
            set(),
        )


class ApprovedProfileConstructionTests(EvenniaTestCase):
    """The approved literals reach every constructed individual, unchanged.

    ``construct_species_individual`` is the one construction entry point every
    owner (wilderness ambient, site, quest provisioning) calls, and it stores
    the configuration and records the numeric source this class pins. No caller
    changed in this change: the values below are the proof that none had to.
    """

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    @covers_requirement(
        "monster-individual-construction::individual-numerics-come-only-from-approved-sources-with-no-scaling-and-no-baked-multipliers"
    )
    def test_the_construction_entry_point_returns_the_approved_values_and_source(self):
        for key, approved in APPROVED_BALANCE.items():
            with self.subTest(variant=key):
                variant = MONSTER_VARIANT_REGISTRY[key]
                config, source = initial_trait_config_for_variant(variant)
                self.assertEqual(source, NUMERIC_SOURCE_APPROVED_PROFILE)
                for name in PROFILE_FIELDS:
                    self.assertEqual(config[name]["base"], approved[name], name)
                self.assertEqual(config["guild_merit"]["base"], 0)

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    def test_every_shipped_variant_constructs_an_individual_with_those_values(self):
        for key, approved in APPROVED_BALANCE.items():
            with self.subTest(variant=key):
                variant = MONSTER_VARIANT_REGISTRY[key]
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
                    NUMERIC_SOURCE_APPROVED_PROFILE,
                )
                for name in PROFILE_FIELDS:
                    stored = getattr(individual.traits, name)
                    self.assertEqual(stored.base, approved[name], name)
                self.assertEqual(
                    individual.danger_grade, approved["danger_grade"]
                )


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
    """Requirement R4: abilities stay narrative; no seam is faked."""

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
        "monster-species-registry::special-abilities-are-narrative-boundaries-with-a-named-mechanics-prerequisite-never-fake-skills"
    )
    def test_no_registry_string_names_a_skill_behaviour_or_combat_trait(self):
        faces = self._forbidden_faces()
        for source, registry in (
            ("species", MONSTER_SPECIES_REGISTRY),
            ("variants", MONSTER_VARIANT_REGISTRY),
        ):
            for key, row in registry.items():
                with self.subTest(registry=source, row=key):
                    if source == "variants" and key in ("bank_lurker", "bay_warden"):
                        # The crocodile variants carry their validated authored kit and profile
                        narrative = {row.display_name_zh, row.description_zh}
                        self.assertEqual(narrative & faces, set())
                        self.assertEqual(row.active_skill_keys, ("tide_devouring_bite",))
                        self.assertEqual(row.behaviour_profile_key, "ambush_predator")
                    else:
                        strings: set[str] = set()
                        _string_values(row, set(), strings)
                        self.assertTrue(strings)
                        self.assertEqual(strings & faces, set())

    @covers_requirement(
        "monster-species-registry::special-abilities-are-narrative-boundaries-with-a-named-mechanics-prerequisite-never-fake-skills"
    )
    def test_no_registry_field_stands_in_for_an_ability_seam(self):
        for cls in (MonsterSpecies, MonsterVariant):
            with self.subTest(cls=cls.__name__):
                names = {field.name for field in dataclasses.fields(cls)}
                self.assertEqual(names & FORBIDDEN_SEAM_FIELDS, set())

    @covers_requirement(
        "monster-species-registry::special-abilities-are-narrative-boundaries-with-a-named-mechanics-prerequisite-never-fake-skills"
    )
    def test_the_behaviour_selection_path_reads_no_species_identity(self):
        # Nothing in the existing behaviour-selection path reads species or
        # variant identity, so a variant's ability narrative cannot unlock an
        # effect. The scan is parsed (not textual), so commentary alone never
        # trips it, and a real identity read would.
        tree = ast.parse(BEHAVIOUR_SELECTION_MODULE.read_text(encoding="utf-8"))
        referenced: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                referenced.add(node.id)
            elif isinstance(node, ast.Attribute):
                referenced.add(node.attr)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    referenced |= set(alias.name.split("."))
            elif isinstance(node, ast.ImportFrom):
                referenced |= set((node.module or "").split("."))
                referenced |= {alias.name for alias in node.names}
        for forbidden in (
            "MONSTER_SPECIES_REGISTRY",
            "MONSTER_VARIANT_REGISTRY",
            "monster_species",
            "species_key",
            "variant_key",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, referenced)


if __name__ == "__main__":
    unittest.main()
