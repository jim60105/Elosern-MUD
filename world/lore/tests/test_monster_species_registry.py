"""Behavior tests for the species/variant registries (synthetic fixtures only).

Every row here is a file-local synthetic fixture with invented keys and prose:
the shipped bestiary content is asserted exclusively by the tagged
data-contract test in ``test_monster_species_content.py``, per the repository's
test-data-independence rule. The vocabularies the registry validates against
are injected, and so are the band rows the tier-band invariant reads, so no
shipped habitat, tier, grade, band, or rank range appears here either.
"""

import ast
import dataclasses
import hashlib
import inspect
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB
from evennia.utils.search import search_script
from evennia.utils.test_resources import EvenniaTestCase

from world.art.store import ArtAssetRecord
from world.lore import monster_species as registry
from world.lore.monster_species import (
    MonsterCombatProfile,
    MonsterSpecies,
    MonsterSpeciesRegistryError,
    MonsterVariant,
)
from world.lore.sync import MONSTER_SPECIES_CATEGORIES, _ALL_REGISTRIES, sync_monster_species

HABITAT = "t_fixture_hollow"
SPARE_HABITAT = "t_fixture_mere"
TIER = "t_fixture_band"
STRONGER_TIER = "t_fixture_band_above"
GRADE = "t_fixture_grade"

# The invented band rows carry HP, attack, agility, defense, magic and ranks.
# They are wide enough for the invented profile
# the balance-slot tests build, and they are injected like every other face, so
# the band invariant is exercised without reading a shipped tier's bands.
TIER_HP_BAND = (10, 20)
TIER_PHYSICAL_BAND = (3, 8)
TIER_MAGIC_BAND = (0, 2)
TIER_RANK_RANGE = (GRADE, GRADE)

# The registry's public callables, in full: read, validate, and project. A
# spawn/place/populate/reconcile entry point would have to appear here to exist.
EXPECTED_PUBLIC_CALLABLES = frozenset(
    {
        "build_monster_variant_registry",
        "published_species_view",
        "published_variant_view",
        "validate_monster_species_registry",
    }
)
PLACEMENT_NAME_FRAGMENTS = (
    "spawn",
    "place",
    "populate",
    "reconcile",
    "respawn",
    "recover",
    "summon",
    "presence",
)
ABILITY_BASELINE_FIELDS = frozenset(
    {"hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power"}
)
INHERITANCE_FIELDS = frozenset(
    {"parent", "parent_key", "base", "base_key", "inherit", "inherits", "override", "overrides"}
)
PRIVATE_FIELDS = ("author_hidden_truth_zh", "author_explanation_zh", "author_conjecture_zh")


def _no_violation(_key: object) -> str | None:
    """A stand-in for the shared stable-key predicate that accepts every key."""
    return None


def _faces(**overrides: object) -> dict[str, object]:
    """The injected validation faces: no shipped vocabulary appears in this file."""
    faces: dict[str, object] = {
        "key_violation_face": _no_violation,
        "habitat_face": (HABITAT, SPARE_HABITAT),
        "tier_face": (TIER, STRONGER_TIER),
        "grade_face": (GRADE,),
        "tier_band_face": {
            TIER: (TIER_HP_BAND, TIER_PHYSICAL_BAND, TIER_PHYSICAL_BAND,
                   TIER_PHYSICAL_BAND, TIER_MAGIC_BAND, TIER_RANK_RANGE),
            STRONGER_TIER: (
                TIER_HP_BAND,
                TIER_PHYSICAL_BAND,
                TIER_PHYSICAL_BAND,
                TIER_PHYSICAL_BAND,
                TIER_MAGIC_BAND,
                TIER_RANK_RANGE,
            ),
        },
    }
    faces.update(overrides)
    return faces


def _species(key: str = "t_fixture_species", **overrides: object) -> MonsterSpecies:
    values: dict[str, object] = {
        "key": key,
        "display_name_zh": "試製物種",
        "published_description_zh": "試製物種描述。",
        "published_appearance_zh": "試製物種外觀。",
        "published_ecology_zh": "試製物種生態。",
        "habitat_tags": (HABITAT,),
        "author_hidden_truth_zh": "試製隱秘真相註記（不公開）。",
        "author_explanation_zh": "試製作者解釋註記（不公開）。",
        "author_conjecture_zh": "試製未經證實的猜想註記（不公開）。",
        "default_variant_key": "t_fixture_ordinary",
        "ordinary_variant": True,
    }
    values.update(overrides)
    return MonsterSpecies(**values)


def _variant(key: str = "t_fixture_ordinary", **overrides: object) -> MonsterVariant:
    values: dict[str, object] = {
        "key": key,
        "species_key": "t_fixture_species",
        "display_name_zh": "試製普通型",
        "description_zh": "試製變體描述。",
        "threat_tier": TIER,
        "ordinary_variant": True,
        "combat_profile": None,
        "danger_grade": None,
    }
    values.update(overrides)
    return MonsterVariant(**values)


def _valid_registry() -> tuple[dict[str, MonsterSpecies], dict[str, MonsterVariant]]:
    """One valid synthetic species with an ordinary and a stronger variant."""
    species = {"t_fixture_species": _species()}
    variants = {
        "t_fixture_ordinary": _variant(),
        "t_fixture_stronger": _variant(
            "t_fixture_stronger",
            display_name_zh="試製強勢型",
            threat_tier=STRONGER_TIER,
            ordinary_variant=False,
        ),
    }
    return species, variants


def _script_keys() -> set[str]:
    """Every Script key currently in the database."""
    return set(ScriptDB.objects.values_list("db_key", flat=True))


def _stable_repr(value: object) -> str:
    """A deterministic rendering of one persisted attribute value."""
    if isinstance(value, (str, int, float, bool, bytes, type(None))):
        return repr(value)
    if isinstance(value, (tuple, list)):
        return "[" + ",".join(_stable_repr(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            f"{_stable_repr(key)}:{_stable_repr(item)}"
            for key, item in sorted(value.items(), key=lambda pair: repr(pair[0]))
        ) + "}"
    return type(value).__name__


def _runtime_digest(model: type, *, exclude_prefix: str | None = None) -> str:
    """One row's identity plus its whole persisted attribute payload."""
    rows = model.objects.all().order_by("pk")
    if exclude_prefix is not None:
        rows = rows.exclude(db_key__startswith=exclude_prefix)
    payload = "\n".join(
        f"{row.pk}|{row.db_key}|"
        + ",".join(
            f"{key}={_stable_repr(value)}"
            for key, value in sorted(
                row.attributes.all().values_list("db_key", "db_value")
            )
        )
        for row in rows
    )
    return hashlib.sha256(payload.encode("utf-8", "replace")).hexdigest()


class PublishedRegistryReadOnlyTests(unittest.TestCase):
    """Requirement: read-only registries; validation publishes nothing partial."""

    REGISTRY_NAMES = ("MONSTER_SPECIES_REGISTRY", "MONSTER_VARIANT_REGISTRY")

    @staticmethod
    def _published(name: str):
        return getattr(registry, name)

    @covers_requirement(
        "monster-species-registry::species-and-variant-registries-are-frozen-keyed-read-only-lore-data"
    )
    def test_the_published_registries_are_read_only_proxies(self):
        for name in self.REGISTRY_NAMES:
            with self.subTest(registry=name):
                published = self._published(name)
                self.assertIsInstance(published, MappingProxyType)
                self.assertTrue(published)
                with self.assertRaises(TypeError):
                    published["t_fixture_intruder"] = None
                with self.assertRaises(TypeError):
                    del published[next(iter(published))]

    def test_validation_is_pure_and_publishes_nothing(self):
        species, variants = _valid_registry()
        broken = dict(
            species,
            t_fixture_species=replace(
                species["t_fixture_species"], default_variant_key="t_fixture_absent"
            ),
        )
        inputs = (dict(species), dict(variants), dict(broken))
        published_before = [dict(self._published(name)) for name in self.REGISTRY_NAMES]

        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(broken, variants, **_faces())

        self.assertEqual((species, variants, broken), inputs)
        self.assertEqual(
            [dict(self._published(name)) for name in self.REGISTRY_NAMES],
            published_before,
        )


class StableIdentityTests(unittest.TestCase):
    """Requirement: keys are the identity; names and tiers are not."""

    @covers_requirement(
        "monster-species-registry::species-and-variant-registries-are-frozen-keyed-read-only-lore-data"
    )
    def test_a_rename_and_a_tier_change_leave_every_lookup_by_key_intact(self):
        species, variants = _valid_registry()
        registry.validate_monster_species_registry(species, variants, **_faces())

        renamed = dict(
            species, t_fixture_species=replace(species["t_fixture_species"], display_name_zh="改名物種")
        )
        retiered = dict(
            variants,
            t_fixture_ordinary=replace(variants["t_fixture_ordinary"], threat_tier=STRONGER_TIER),
        )
        registry.validate_monster_species_registry(renamed, retiered, **_faces())

        species_view = MappingProxyType(renamed)
        variant_view = MappingProxyType(retiered)
        # The lookup by key resolves the same record; every row's own key is
        # unchanged; and the renamed display name is not an identity.
        self.assertEqual(sorted(species_view), sorted(species))
        self.assertEqual(sorted(variant_view), sorted(variants))
        self.assertEqual(species_view["t_fixture_species"].key, "t_fixture_species")
        self.assertEqual(variant_view["t_fixture_ordinary"].key, "t_fixture_ordinary")
        self.assertEqual(
            {row.key for row in species_view.values()}, set(species)
        )
        self.assertEqual(
            {row.key for row in variant_view.values()}, set(variants)
        )
        with self.assertRaises(KeyError):
            species_view["改名物種"]  # a display name is never an identity
        with self.assertRaises(KeyError):
            variant_view[STRONGER_TIER]  # nor is a threat tier
        view = registry.published_species_view(renamed["t_fixture_species"])
        self.assertEqual(view["key"], "t_fixture_species")
        self.assertEqual(view["display_name_zh"], "改名物種")

    def test_a_record_key_must_be_its_registry_key(self):
        species, variants = _valid_registry()
        mismatched = dict(variants)
        mismatched["t_fixture_elsewhere"] = mismatched.pop("t_fixture_ordinary")
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(species, mismatched, **_faces())

    @covers_requirement(
        "monster-species-registry::species-and-variant-registries-are-frozen-keyed-read-only-lore-data"
    )
    def test_no_lookup_by_display_name_exists(self):
        for name in dir(registry):
            if name.startswith("_"):
                continue
            value = getattr(registry, name)
            if callable(value) and not isinstance(value, type):
                parameters = {
                    parameter.lower() for parameter in inspect.signature(value).parameters
                }
                self.assertNotIn("display_name_zh", parameters, name)
                self.assertNotIn("display_name", parameters, name)
        for absent in ("species_by_name", "variant_by_name", "lookup_by_display_name"):
            self.assertFalse(hasattr(registry, absent))

    @covers_requirement(
        "monster-species-registry::species-and-variant-registries-are-frozen-keyed-read-only-lore-data"
    )
    def test_the_shared_key_contract_gates_both_key_faces(self):
        species, variants = _valid_registry()

        def reject_species_key(key: object) -> str | None:
            return "fixture" if key == "t_fixture_species" else None

        def reject_variant_key(key: object) -> str | None:
            return "fixture" if key == "t_fixture_stronger" else None

        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(
                species, variants, **_faces(key_violation_face=reject_species_key)
            )
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(
                species, variants, **_faces(key_violation_face=reject_variant_key)
            )


class RecordShapeTests(unittest.TestCase):
    """Requirement: complete standalone records, no ability baseline on the species."""

    def _field_names(self, cls: type) -> set[str]:
        return {field.name for field in dataclasses.fields(cls)}

    @covers_requirement(
        "monster-species-registry::species-and-variant-registries-are-frozen-keyed-read-only-lore-data"
    )
    def test_the_species_declares_no_ability_baseline(self):
        self.assertEqual(self._field_names(MonsterSpecies) & ABILITY_BASELINE_FIELDS, set())

    @covers_requirement(
        "monster-species-registry::species-and-variant-registries-are-frozen-keyed-read-only-lore-data"
    )
    def test_neither_class_carries_an_inheritance_or_override_field(self):
        self.assertEqual(self._field_names(MonsterSpecies) & INHERITANCE_FIELDS, set())
        self.assertEqual(self._field_names(MonsterVariant) & INHERITANCE_FIELDS, set())

    @covers_requirement(
        "monster-species-registry::species-and-variant-registries-are-frozen-keyed-read-only-lore-data"
    )
    def test_the_declared_field_sets_are_exactly_the_contract(self):
        self.assertEqual(
            self._field_names(MonsterSpecies),
            {
                "key",
                "display_name_zh",
                "published_description_zh",
                "published_appearance_zh",
                "published_ecology_zh",
                "habitat_tags",
                "author_hidden_truth_zh",
                "author_explanation_zh",
                "author_conjecture_zh",
                "default_variant_key",
                "ordinary_variant",
            },
        )
        self.assertEqual(
            self._field_names(MonsterVariant),
            {
                "key",
                "species_key",
                "display_name_zh",
                "description_zh",
                "threat_tier",
                "ordinary_variant",
                "combat_profile",
                "danger_grade",
                "active_skill_keys",
                "passive_skill_keys",
                "behaviour_profile_key",
            },
        )

    @covers_requirement(
        "monster-species-registry::species-and-variant-registries-are-frozen-keyed-read-only-lore-data"
    )
    def test_a_variant_is_a_standalone_complete_record(self):
        variant = _variant()
        for field in dataclasses.fields(MonsterVariant):
            self.assertTrue(hasattr(variant, field.name), field.name)
        # No resolution step merges species values into a variant: the record
        # carries every field itself, and the registry never returns a merged row.
        self.assertFalse(hasattr(variant, "resolve"))
        self.assertFalse(hasattr(variant, "merged_with"))


class MembershipValidationTests(unittest.TestCase):
    """Requirement: membership, default-variant, and classification rules."""

    @covers_requirement(
        "monster-species-registry::every-variant-belongs-to-its-species-and-the-default-variant-is-an-ordinary-variant-of-it"
    )
    def test_an_orphan_variant_is_rejected(self):
        species, variants = _valid_registry()
        variants = dict(variants, t_fixture_ordinary=_variant(species_key="t_fixture_absent"))
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(species, variants, **_faces())

    @covers_requirement(
        "monster-species-registry::every-variant-belongs-to-its-species-and-the-default-variant-is-an-ordinary-variant-of-it"
    )
    def test_a_variant_key_cannot_be_stolen_by_another_species(self):
        first = _variant("t_contested", species_key="t_fixture_species")
        thief = _variant("t_contested", species_key="t_fixture_other")
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.build_monster_variant_registry((first, thief))
        # The same owner re-registering its own key is an ordinary idempotent merge.
        merged = registry.build_monster_variant_registry((first, first))
        self.assertEqual(sorted(merged), ["t_contested"])

    @covers_requirement(
        "monster-species-registry::every-variant-belongs-to-its-species-and-the-default-variant-is-an-ordinary-variant-of-it"
    )
    def test_a_default_variant_that_is_not_registered_is_rejected(self):
        species = {"t_fixture_species": _species(default_variant_key="t_fixture_absent")}
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(species, {}, **_faces())

    @covers_requirement(
        "monster-species-registry::every-variant-belongs-to-its-species-and-the-default-variant-is-an-ordinary-variant-of-it"
    )
    def test_a_default_variant_from_another_species_is_rejected(self):
        species = {
            "t_fixture_species": _species(default_variant_key="t_fixture_foreign"),
            "t_fixture_other": _species(
                "t_fixture_other", default_variant_key="t_fixture_own"
            ),
        }
        variants = {
            # Both keys exist and resolve, but the species that declares
            # `t_fixture_foreign` as its baseline does not own it.
            "t_fixture_foreign": _variant("t_fixture_foreign", species_key="t_fixture_other"),
            "t_fixture_own": _variant("t_fixture_own", species_key="t_fixture_other"),
        }
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(species, variants, **_faces())

    @covers_requirement(
        "monster-species-registry::every-variant-belongs-to-its-species-and-the-default-variant-is-an-ordinary-variant-of-it"
    )
    def test_a_stronger_variant_cannot_be_the_species_baseline(self):
        species = {"t_fixture_species": _species(default_variant_key="t_fixture_stronger")}
        variants = {
            "t_fixture_stronger": _variant(
                "t_fixture_stronger", threat_tier=STRONGER_TIER, ordinary_variant=False
            )
        }
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(species, variants, **_faces())

    @covers_requirement(
        "monster-species-registry::every-variant-belongs-to-its-species-and-the-default-variant-is-an-ordinary-variant-of-it"
    )
    def test_the_authored_flag_classifies_and_the_name_never_does(self):
        # A strength-sounding name with an authored ordinary classification is
        # ordinary; the same name with the stronger classification cannot be a
        # baseline. No name matching participates in either verdict.
        species = {"t_fixture_species": _species()}
        ordinary = {
            "t_fixture_ordinary": _variant(
                "t_fixture_ordinary", display_name_zh="試製至尊霸主型", ordinary_variant=True
            )
        }
        registry.validate_monster_species_registry(species, ordinary, **_faces())

        stronger = {
            "t_fixture_ordinary": _variant(
                "t_fixture_ordinary", display_name_zh="試製至尊霸主型", ordinary_variant=False
            )
        }
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(species, stronger, **_faces())

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    def test_an_unknown_habitat_tier_or_grade_is_rejected(self):
        species = {"t_fixture_species": _species(habitat_tags=("t_fixture_unmapped",))}
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(species, {}, **_faces())

        good_species, variants = _valid_registry()
        bad_tier = dict(
            variants,
            t_fixture_ordinary=replace(variants["t_fixture_ordinary"], threat_tier="t_fixture_unmapped"),
        )
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(good_species, bad_tier, **_faces())

        bad_grade = dict(
            variants,
            t_fixture_ordinary=replace(variants["t_fixture_ordinary"], danger_grade="t_fixture_unmapped"),
        )
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(good_species, bad_grade, **_faces())

    @covers_requirement(
        "monster-species-registry::every-variant-belongs-to-its-species-and-the-default-variant-is-an-ordinary-variant-of-it"
    )
    def test_the_species_classification_must_be_a_boolean_agreeing_with_its_baseline(self):
        species, variants = _valid_registry()
        registry.validate_monster_species_registry(species, variants, **_faces())

        disagreeing = {
            "t_fixture_species": _species(ordinary_variant=False),
        }
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(disagreeing, variants, **_faces())

        untyped = {"t_fixture_species": _species(ordinary_variant="yes")}
        with self.assertRaises(MonsterSpeciesRegistryError):
            registry.validate_monster_species_registry(untyped, variants, **_faces())


class BalanceSlotTests(unittest.TestCase):
    """Requirement: the numeric and danger-grade slots never carry invented values."""

    def _complete(self, **overrides: object) -> MonsterCombatProfile:
        values: dict[str, object] = {
            "hp": 12,
            "mp": 3,
            "sp": 2,
            "atk_phys": 5,
            "agility": 4,
            "defense": 6,
            "magic_power": 1,
        }
        values.update(overrides)
        return MonsterCombatProfile(**values)  # type: ignore[arg-type]

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    def test_a_partial_profile_cannot_be_constructed(self):
        with self.assertRaises(MonsterSpeciesRegistryError):
            MonsterCombatProfile(hp=1, mp=0, sp=0, atk_phys=1, agility=1, defense=1)

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    def test_an_unpopulated_or_non_integer_or_negative_value_is_rejected(self):
        for overrides in ({"magic_power": None}, {"hp": 1.5}, {"hp": True}, {"hp": -1}):
            with self.subTest(overrides=overrides):
                with self.assertRaises(MonsterSpeciesRegistryError):
                    self._complete(**overrides)

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    def test_a_complete_profile_is_accepted_and_projected_verbatim(self):
        profile = self._complete()
        species, variants = _valid_registry()
        variants["t_fixture_ordinary"] = replace(
            variants["t_fixture_ordinary"], combat_profile=profile, danger_grade=GRADE
        )
        registry.validate_monster_species_registry(species, variants, **_faces())

        view = registry.published_variant_view(variants["t_fixture_ordinary"])
        self.assertEqual(view["danger_grade"], GRADE)
        self.assertEqual(
            view["combat_profile"],
            {
                "hp": 12,
                "mp": 3,
                "sp": 2,
                "atk_phys": 5,
                "agility": 4,
                "defense": 6,
                "magic_power": 1,
            },
        )

    @covers_requirement(
        "monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values"
    )
    def test_a_magic_flavoured_variant_reads_none_and_never_an_inferred_number(self):
        species, variants = _valid_registry()
        variants["t_fixture_ordinary"] = replace(
            variants["t_fixture_ordinary"],
            display_name_zh="試製魔力暴風型",
            description_zh="以魔力與元素風暴吞噬一切的試製敘述。",
            combat_profile=None,
        )
        registry.validate_monster_species_registry(species, variants, **_faces())
        variant = variants["t_fixture_ordinary"]
        self.assertIsNone(variant.combat_profile)
        self.assertIsNone(variant.danger_grade)
        view = registry.published_variant_view(variant)
        self.assertIsNone(view["combat_profile"])
        self.assertIsNone(view["danger_grade"])
        self.assertNotIn("magic_power", view)


class PublishedProjectionTests(unittest.TestCase):
    """Requirement: the published views are allowlists; private notes never leak."""

    @covers_requirement(
        "monster-species-registry::published-projections-expose-only-marked-public-fields"
    )
    def test_the_species_view_is_exactly_the_allowlist(self):
        view = registry.published_species_view(_species())
        self.assertEqual(
            sorted(view),
            [
                "display_name_zh",
                "habitat_tags",
                "key",
                "published_appearance_zh",
                "published_description_zh",
                "published_ecology_zh",
            ],
        )

    @covers_requirement(
        "monster-species-registry::published-projections-expose-only-marked-public-fields"
    )
    def test_the_variant_view_is_exactly_the_allowlist(self):
        view = registry.published_variant_view(_variant())
        self.assertEqual(
            sorted(view),
            [
                "combat_profile",
                "danger_grade",
                "description_zh",
                "display_name_zh",
                "key",
                "ordinary_variant",
                "species_key",
                "threat_tier",
            ],
        )

    @covers_requirement(
        "monster-species-registry::published-projections-expose-only-marked-public-fields"
    )
    def test_private_notes_absent_from_the_serialized_payload_and_its_keys(self):
        row = _species(
            author_hidden_truth_zh="試製隱秘真相哨兵字串",
            author_explanation_zh="試製作者解釋哨兵字串",
            author_conjecture_zh="試製未經證實猜想哨兵字串",
        )
        for view in (registry.published_species_view(row), registry.published_variant_view(_variant())):
            payload = json.dumps(view, ensure_ascii=False)
            for field in PRIVATE_FIELDS:
                self.assertNotIn(field, payload)
            self.assertNotIn("哨兵字串", payload)

    @covers_requirement(
        "monster-species-registry::published-projections-expose-only-marked-public-fields"
    )
    def test_a_missing_public_description_is_not_backfilled_from_private_text(self):
        row = _species(
            published_appearance_zh="",
            author_hidden_truth_zh="試製隱秘真相哨兵字串",
            author_explanation_zh="試製作者解釋哨兵字串",
        )
        view = registry.published_species_view(row)
        self.assertEqual(view["published_appearance_zh"], "")
        self.assertNotIn("哨兵字串", json.dumps(view, ensure_ascii=False))

    @covers_requirement(
        "monster-species-registry::published-projections-expose-only-marked-public-fields"
    )
    def test_published_conjecture_keeps_its_uncertainty_marking(self):
        colophon = "（未經證實的說法）試製學者相信牠們來自北方。"
        normalised = colophon.replace("未經證實", "已知")
        row = _species(published_ecology_zh=colophon)
        view = registry.published_species_view(row)
        self.assertEqual(view["published_ecology_zh"], colophon)
        self.assertIn("未經證實", view["published_ecology_zh"])
        # A projection that rewrote the uncertainty away would return the
        # normalised text instead; the published view never transforms prose.
        self.assertNotEqual(view["published_ecology_zh"], normalised)

    @covers_requirement(
        "monster-species-registry::published-projections-expose-only-marked-public-fields"
    )
    def test_no_whole_record_serializer_is_exposed(self):
        for absent in ("to_dict", "asdict", "dump", "serialize", "species_to_dict"):
            self.assertFalse(hasattr(registry, absent))


class HabitatCompatibilityTests(unittest.TestCase):
    """Requirement: habitat tags are compatibility data and authorize no spawning."""

    @covers_requirement(
        "monster-species-registry::habitat-tags-are-compatibility-data-and-never-authorize-spawning"
    )
    def test_the_module_offers_no_spawn_or_placement_callable(self):
        public = {name for name in dir(registry) if not name.startswith("_")}
        for fragment in PLACEMENT_NAME_FRAGMENTS:
            offending = [name for name in public if fragment in name.lower()]
            self.assertEqual(offending, [], f"{fragment} appears in {offending}")

    @covers_requirement(
        "monster-species-registry::habitat-tags-are-compatibility-data-and-never-authorize-spawning"
    )
    def test_the_public_callables_are_exactly_the_read_validate_project_set(self):
        public_callables = {
            name
            for name in dir(registry)
            if not name.startswith("_")
            and callable(getattr(registry, name))
            and not isinstance(getattr(registry, name), type)
            and getattr(getattr(registry, name), "__module__", "") == registry.__name__
        }
        self.assertEqual(public_callables, set(EXPECTED_PUBLIC_CALLABLES))

    @covers_requirement(
        "monster-species-registry::habitat-tags-are-compatibility-data-and-never-authorize-spawning"
    )
    def test_no_row_or_projection_carries_a_placement_payload(self):
        species_fields = {field.name for field in dataclasses.fields(MonsterSpecies)}
        variant_fields = {field.name for field in dataclasses.fields(MonsterVariant)}
        placement_fields = {
            "location",
            "room",
            "coordinate",
            "coordinates",
            "quantity",
            "capacity",
            "count",
            "respawn",
        }
        self.assertEqual(species_fields & placement_fields, set())
        self.assertEqual(variant_fields & placement_fields, set())
        view = registry.published_species_view(_species(habitat_tags=(HABITAT, SPARE_HABITAT)))
        self.assertEqual(view["habitat_tags"], (HABITAT, SPARE_HABITAT))
        self.assertEqual(set(view) & placement_fields, set())

    @covers_requirement(
        "monster-species-registry::habitat-tags-are-compatibility-data-and-never-authorize-spawning"
    )
    def test_a_tag_matching_species_is_resolvable_only_as_its_own_record(self):
        # Compatibility is not presence: matching every known habitat changes
        # nothing about where the species is, because no callable answers that
        # and no row carries a place. A species whose tags match is still only
        # its registry record.
        _unused, variants = _valid_registry()
        species = {"t_fixture_species": _species(habitat_tags=(HABITAT, SPARE_HABITAT))}
        registry.validate_monster_species_registry(species, variants, **_faces())
        row = species["t_fixture_species"]
        self.assertEqual(row.habitat_tags, (HABITAT, SPARE_HABITAT))
        for absent in ("spawn_species", "place_species", "present_in", "is_present"):
            self.assertFalse(hasattr(registry, absent))


class MonsterSpeciesSyncTests(EvenniaTestCase):
    """Requirement: the mirror is idempotent, bounded, and leaves runtime alone."""

    @staticmethod
    def _expected_record_keys() -> set[str]:
        keys: set[str] = set()
        for category in MONSTER_SPECIES_CATEGORIES:
            keys |= {f"lore:{category}:{key}" for key in _ALL_REGISTRIES[category]}
        return keys

    @staticmethod
    def _runtime_state() -> tuple:
        # Identity AND payload: an in-place attribute change on a monster,
        # room, quest, or art record moves one of these digests. The lore
        # Scripts themselves are the mirror's own output and are excluded.
        return (
            _runtime_digest(ObjectDB),
            _runtime_digest(ArtAssetRecord),
            _runtime_digest(ScriptDB, exclude_prefix="lore:"),
        )

    @covers_requirement(
        "monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently"
    )
    def test_the_step_mirrors_exactly_the_species_and_variant_records(self):
        expected = self._expected_record_keys()
        self.assertTrue(expected)
        before = _script_keys()
        sync_monster_species()
        created = _script_keys() - before
        self.assertEqual(created, expected - before)
        for category in MONSTER_SPECIES_CATEGORIES:
            for key in _ALL_REGISTRIES[category]:
                records = search_script(f"lore:{category}:{key}")
                self.assertEqual(len(records), 1, f"{category}:{key}")
                self.assertEqual(records[0].db.category, category)

    @covers_requirement(
        "monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently"
    )
    def test_repeating_the_step_is_a_no_op(self):
        def mirrored_rows():
            return [
                (script.id, script.db.category, script.db.fields)
                for category in MONSTER_SPECIES_CATEGORIES
                for key in _ALL_REGISTRIES[category]
                for script in search_script(f"lore:{category}:{key}")
            ]

        sync_monster_species()
        first_rows = mirrored_rows()
        first_keys = _script_keys()

        sync_monster_species()
        second_rows = mirrored_rows()
        second_keys = _script_keys()

        self.assertTrue(first_rows)
        self.assertEqual(first_rows, second_rows)
        self.assertEqual(first_keys, second_keys)

    @covers_requirement(
        "monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently"
    )
    def test_the_mirror_touches_no_monster_room_quest_or_art_record(self):
        before = self._runtime_state()
        sync_monster_species()
        after_first_run = self._runtime_state()
        self.assertEqual(before, after_first_run)
        sync_monster_species()
        self.assertEqual(after_first_run, self._runtime_state())

    @covers_requirement(
        "monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently"
    )
    def test_one_boundary_event_carries_the_registry_context(self):
        with patch("world.lore.sync.log_info") as info:
            sync_monster_species()
        self.assertEqual(info.call_count, 1)
        self.assertEqual(info.call_args.args[0], "monster_species_sync")
        self.assertEqual(
            info.call_args.kwargs["context"],
            {
                "monster_species": len(_ALL_REGISTRIES["monster_species"]),
                "monster_variants": len(_ALL_REGISTRIES["monster_variants"]),
            },
        )


class ModuleBoundaryTests(unittest.TestCase):
    """The registry module stays inside the lore layer (no world.art import)."""

    def test_the_module_imports_only_stdlib_and_the_lore_package(self):
        source = Path(registry.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        allowed_stdlib = {"collections", "dataclasses", "types"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split(".")[0], allowed_stdlib, alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                module_name = node.module or ""
                self.assertTrue(
                    module_name.startswith("world.lore.")
                    or module_name.split(".")[0] in allowed_stdlib,
                    module_name,
                )


if __name__ == "__main__":
    unittest.main()
