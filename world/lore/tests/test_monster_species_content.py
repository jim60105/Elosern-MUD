"""Data-contract test: shipped bestiary identity, narrative, profile integrity and construction wiring

The six species and twelve variant identities retain their published narrative
and taxonomy. Current complete profiles and grades satisfy authoring bounds;
construction and reload observe the selected profile without numerical
approval copies. Delivered kits and deferred kits remain distinct.
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

# The complete profile shape is stable; its authored magnitudes are mutable.
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

# Each delivered species whose contact kit has landed also publishes its
# approved environment-independent contact clause, so the executable kit's
# prose boundary is pinned beside the retained limit above.
APPROVED_CONTACT_CLAUSES = {
    "sway_whistle_sparrow": (
        "近身時，牠會配合短促氣流啄擊，命中後使對手短暫分心；"
        "此招不需要穀物，也不產生強風或擊退。"
    ),
    "tide_lamp_crab": (
        "牠會在螯擊時收緊甲殼，短暫提高自身防禦；這項動作不依賴光源，"
        "發光斑紋與螯擊皆無治療效果，也不屬於光屬性治療術。"
    ),
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
        "monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently",
        "monster-resource-abilities::crocodile-ecology-documents-implemented-limits",
        "monster-resource-abilities::穗鳴雀-public-ecology-reflects-the-completed-contact-kit",
        "monster-resource-abilities::潮燈蟹-public-ecology-reflects-the-completed-contact-kit",
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
                contact_clause = APPROVED_CONTACT_CLAUSES.get(key)
                if contact_clause is not None:
                    self.assertIn(
                        contact_clause,
                        species.published_ecology_zh,
                        "the approved contact clause is missing",
                    )
                self.assertNotEqual(
                    species.published_description_zh, species.published_ecology_zh
                )

    @covers_requirement(
        "monster-resource-abilities::穗鳴雀-public-ecology-reflects-the-completed-contact-kit"
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
    """Detect missing, partial or malformed current authored balance slots."""

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    @covers_requirement(
        "monster-species-registry::the-approved-first-batch-profiles-and-grades-are-user-approved-literals"
    )
    def test_every_shipped_variant_carries_a_complete_profile_and_registered_grade(self):
        self.assertEqual(
            set(PROFILE_FIELDS),
            {"hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power"},
        )
        for key in APPROVED_VARIANTS:
            with self.subTest(variant=key):
                variant = MONSTER_VARIANT_REGISTRY[key]
                profile = variant.combat_profile
                self.assertIsInstance(profile, MonsterCombatProfile)
                for name in PROFILE_FIELDS:
                    value = getattr(profile, name)
                    self.assertIs(type(value), int, name)
                    self.assertGreaterEqual(value, 0, name)
                self.assertGreater(profile.hp, 0)
                self.assertIn(variant.danger_grade, GUILD_RANK_REGISTRY)


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
    """Observe current profile selection across construction and persistence."""

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    @covers_requirement(
        "monster-individual-construction::individual-numerics-come-only-from-approved-sources-with-no-scaling-and-no-baked-multipliers",
        "monster-individual-construction::穗鳴雀-construction-persists-both-approved-contact-kits",
        "monster-individual-construction::潮燈蟹-construction-persists-both-approved-contact-kits",
    )
    def test_every_shipped_variant_constructs_an_individual_with_those_values(self):
        from typeclasses.monsters import Monster

        for key in APPROVED_VARIANTS:
            with self.subTest(variant=key):
                variant = MONSTER_VARIANT_REGISTRY[key]
                profile = variant.combat_profile
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
                # Detect wrong variant selection and multipliers baked into bases.
                for actual in (individual, Monster.objects.get(pk=individual.pk)):
                    self.assertEqual(actual.species_key, variant.species_key)
                    self.assertEqual(actual.variant_key, key)
                    for name in PROFILE_FIELDS:
                        stored = getattr(actual.traits, name)
                        self.assertEqual(stored.base, getattr(profile, name), name)
                    self.assertEqual(actual.danger_grade, variant.danger_grade)
                    if variant.active_skill_keys:
                        self.assertEqual(
                            actual.db.skills["active"], list(variant.active_skill_keys),
                        )
                        self.assertEqual(
                            actual.db.skills["passive"], list(variant.passive_skill_keys),
                        )
                        self.assertEqual(actual.db.behaviour_tree, variant.behaviour_profile_key)
                    else:
                        # Deferred kits must stay absent, not acquire a new mount.
                        self.assertIsNone(actual.db.skills)


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
        # The delivered variants carry their validated authored kit and
        # profile; every other row must name none of these faces anywhere.
        delivered = {
            "bank_lurker": ("tide_devouring_bite", "ambush_predator"),
            "bay_warden": ("tide_devouring_bite", "ambush_predator"),
            "grain_pecker": ("grain_shaking_peck", "instinctive"),
            "flock_leader": ("grain_shaking_peck", "instinctive"),
            "shore_walker": ("lamp_carapace_claw", "instinctive"),
            "reef_warden": ("lamp_carapace_claw", "instinctive"),
        }
        for source, registry in (
            ("species", MONSTER_SPECIES_REGISTRY),
            ("variants", MONSTER_VARIANT_REGISTRY),
        ):
            for key, row in registry.items():
                with self.subTest(registry=source, row=key):
                    if source == "variants" and key in delivered:
                        skill_key, profile_key = delivered[key]
                        narrative = {row.display_name_zh, row.description_zh}
                        self.assertEqual(narrative & faces, set())
                        self.assertEqual(row.active_skill_keys, (skill_key,))
                        self.assertEqual(row.behaviour_profile_key, profile_key)
                        self.assertEqual(row.passive_skill_keys, ())
                        self.assertIn(skill_key, SKILL_REGISTRY)
                        self.assertIn(profile_key, BEHAVIOUR_PROFILES)
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
