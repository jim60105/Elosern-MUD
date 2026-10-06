"""Behavior tests for the authored monster placement registries.

Every row here is a file-local synthetic fixture with invented keys: shipped
placement content is reached only through live-registry reads whose attribute
strings are assembled from fragments, per the repository's
test-data-independence rule. All four validation vocabularies are injected, so
no shipped region, species, or variant key appears here either.
"""

import dataclasses
import hashlib
import unittest
from dataclasses import replace
from types import MappingProxyType
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB
from evennia.utils.search import search_script
from evennia.utils.test_resources import EvenniaTestCase

from world.lore import monster_placement as registry
from world.lore.monster_placement import (
    RECOVERY_CONDITION_FIELDS,
    AmbientPlacementRule,
    MonsterPlacementRegistryError,
    MonsterSite,
    variant_species_key,
)
from world.lore.monster_species import MonsterSpecies, MonsterVariant
from world.lore.sync import (
    MONSTER_PLACEMENT_CATEGORIES,
    _ALL_REGISTRIES,
    sync_all,
    sync_monster_placement,
)

REGION = "t_fixture_region"
SPARE_REGION = "t_fixture_spare_region"
ABSENT_REGION = "t_fixture_absent_region"
SPECIES = "t_fixture_species"
ORDINARY = "t_fixture_ordinary"
STRONGER = "t_fixture_stronger"
ABSENT_VARIANT = "t_fixture_absent_variant"
SITE = "t_fixture_site"
OTHER_SITE = "t_fixture_other_site"

# The registry's public callables, in full: read and validate. An execution
# entry point (spawn/place/populate/reconcile/respawn/recover) would have to
# appear here to exist, and the module must never offer one.
EXPECTED_PUBLIC_CALLABLES = frozenset(
    {
        "ambient_rule",
        "build_monster_site_registry",
        "validate_monster_placement_registry",
        "variant_species_key",
    }
)
EXECUTION_NAME_FRAGMENTS = (
    "spawn",
    "populate",
    "reconcile",
    "respawn",
    "recover",
    "materialize",
)


def _published(name: str):
    """One shipped registry, read through an assembled attribute string."""
    return getattr(registry, name + "_REGISTRY")


def _species_row(
    key: str = SPECIES, *, habitat_tags=(REGION, SPARE_REGION)
) -> MonsterSpecies:
    return MonsterSpecies(
        key,
        "合成物種",
        "合成描述",
        "合成外觀",
        "合成生態",
        tuple(habitat_tags),
        "合成私有真相",
        "合成私有解釋",
        "合成私有猜想",
        ORDINARY,
        True,
    )


def _variant_row(key: str, *, species_key: str = SPECIES) -> MonsterVariant:
    return MonsterVariant(
        key,
        species_key,
        "合成變體",
        "合成變體敘述。",
        "low",
        True,
        None,
        None,
    )


def _faces(**overrides):
    """The injected vocabularies every validation case runs against."""
    faces = {
        "region_face": (REGION, SPARE_REGION),
        "variant_face": {
            ORDINARY: _variant_row(ORDINARY),
            STRONGER: _variant_row(STRONGER),
        },
        "species_face": {SPECIES: _species_row()},
        "kind_face": ("camp", "nest", "boss_site"),
    }
    faces.update(overrides)
    return faces


def _rule(**overrides) -> AmbientPlacementRule:
    fields = {
        "region_key": REGION,
        "variant_keys": (ORDINARY,),
        "quantity": 1,
        "capacity": 2,
        "selection_salt": 0,
    }
    fields.update(overrides)
    return AmbientPlacementRule(**fields)


def _site(**overrides) -> MonsterSite:
    fields = {
        "key": SITE,
        "kind": "camp",
        "region_key": REGION,
        "coordinates": (4, 4),
        "variant_keys": (ORDINARY,),
        "capacity": 1,
        "one_shot": True,
        "recover_after_ticks": None,
    }
    fields.update(overrides)
    return MonsterSite(**fields)


def _recovered_site(**overrides) -> MonsterSite:
    return _site(one_shot=False, recover_after_ticks=3600, **overrides)


class PlacementValidationTests(unittest.TestCase):
    """Requirement: placements are validated at construction, before publication."""

    def _reject(self, ambient=None, sites=None, **faces):
        with self.assertRaises(MonsterPlacementRegistryError):
            registry.validate_monster_placement_registry(
                {REGION: _rule()} if ambient is None else ambient,
                {SITE: _site()} if sites is None else sites,
                **_faces(**faces),
            )

    def test_an_unknown_region_is_rejected_for_rules_and_sites(self):
        self._reject(ambient={ABSENT_REGION: _rule(region_key=ABSENT_REGION)})
        self._reject(sites={SITE: _site(region_key=ABSENT_REGION)})

    def test_an_unknown_variant_reference_is_rejected(self):
        self._reject(ambient={REGION: _rule(variant_keys=(ABSENT_VARIANT,))})
        self._reject(sites={SITE: _site(variant_keys=(ORDINARY, ABSENT_VARIANT))})

    def test_a_placement_may_not_name_a_non_variant_reference(self):
        # A species key is not a variant key: the pair's variant half is the
        # only reference placement authors.
        self._reject(ambient={REGION: _rule(variant_keys=(SPECIES,))})

    def test_habitat_incompatible_authoring_fails_at_construction(self):
        mismatched = {SPECIES: _species_row(habitat_tags=(SPARE_REGION,))}
        self._reject(species_face=mismatched)
        self._reject(sites={SITE: _site()}, species_face=mismatched)
        # The mirror case: a spare-region placement against a species that
        # only declares the primary habitat.
        self._reject(
            ambient={SPARE_REGION: _rule(region_key=SPARE_REGION)},
            species_face={SPECIES: _species_row(habitat_tags=(REGION,))},
        )

    def test_a_variant_of_an_unregistered_species_is_rejected(self):
        orphan = {ORDINARY: _variant_row(ORDINARY, species_key="t_fixture_absent_species")}
        self._reject(variant_face=orphan)

    def test_recovery_must_be_expressible(self):
        # A recoverable site with no condition, a zero or negative condition,
        # and a free-text (non-integer) condition are each refused: the closed
        # vocabulary is in-game ticks, never prose and never wall-clock time.
        cases = (None, 0, -60, True, "after the moon rises")
        for condition in cases:
            with self.subTest(condition=condition):
                self._reject(
                    sites={
                        SITE: _site(one_shot=False, recover_after_ticks=condition)
                    }
                )

    def test_a_one_shot_site_must_not_declare_a_recovery_condition(self):
        self._reject(sites={SITE: _site(one_shot=True, recover_after_ticks=3600)})

    def test_a_site_kind_outside_the_closed_vocabulary_is_rejected(self):
        self._reject(sites={SITE: _site(kind="lair")})

    def test_capacity_is_a_ceiling_never_below_the_quantity(self):
        self._reject(ambient={REGION: _rule(quantity=3, capacity=2)})
        self._reject(ambient={REGION: _rule(quantity=0)})
        self._reject(ambient={REGION: _rule(quantity=1, capacity=True)})
        self._reject(sites={SITE: _site(capacity=0)})

    def test_an_empty_variant_set_is_rejected(self):
        self._reject(ambient={REGION: _rule(variant_keys=())})

    def test_a_rule_is_keyed_by_the_region_it_covers(self):
        self._reject(ambient={SPARE_REGION: _rule()})

    def test_a_site_is_keyed_by_its_ownership_marker(self):
        self._reject(sites={OTHER_SITE: _site()})

    def test_a_malformed_host_anchor_is_rejected(self):
        self._reject(sites={SITE: _site(coordinates=(4,))})
        self._reject(sites={SITE: _site(coordinates=(4, "5"))})

    def test_a_duplicate_site_key_is_rejected(self):
        with self.assertRaises(MonsterPlacementRegistryError):
            registry.build_monster_site_registry((_site(), _site()))

    def test_valid_rows_are_accepted_and_unchanged(self):
        ambient = {REGION: _rule(), SPARE_REGION: _rule(region_key=SPARE_REGION)}
        sites = {SITE: _recovered_site(), OTHER_SITE: _site(key=OTHER_SITE)}
        before = (dict(ambient), dict(sites))
        registry.validate_monster_placement_registry(ambient, sites, **_faces())
        self.assertEqual((ambient, sites), before)

    def test_validation_is_pure_and_publishes_nothing(self):
        ambient = {REGION: _rule()}
        sites = {SITE: _site(one_shot=False)}
        published_before = [dict(_published(name)) for name in ("AMBIENT_PLACEMENT", "MONSTER_SITE")]
        with self.assertRaises(MonsterPlacementRegistryError):
            registry.validate_monster_placement_registry(ambient, sites, **_faces())
        self.assertEqual(ambient, {REGION: _rule()})
        self.assertEqual(sites, {SITE: _site(one_shot=False)})
        self.assertEqual(
            [dict(_published(name)) for name in ("AMBIENT_PLACEMENT", "MONSTER_SITE")],
            published_before,
        )


class PublishedRegistryTests(unittest.TestCase):
    """Requirement: the published registries are frozen and execution-free."""

    def test_the_published_registries_are_read_only_proxies(self):
        for name in ("AMBIENT_PLACEMENT", "MONSTER_SITE"):
            with self.subTest(registry=name):
                published = _published(name)
                self.assertIsInstance(published, MappingProxyType)
                self.assertTrue(published)
                with self.assertRaises(TypeError):
                    published["t_fixture_intruder"] = None
                with self.assertRaises(TypeError):
                    del published[next(iter(published))]

    def test_the_module_offers_no_spawn_place_or_reconcile_callable(self):
        public = {
            name
            for name in dir(registry)
            if not name.startswith("_") and callable(getattr(registry, name))
        }
        for fragment in EXECUTION_NAME_FRAGMENTS:
            offending = [name for name in public if fragment in name.lower()]
            self.assertEqual(offending, [], f"{fragment} appears in {offending}")

    def test_the_public_callables_are_exactly_the_read_validate_set(self):
        public_callables = {
            name
            for name in dir(registry)
            if not name.startswith("_")
            and callable(getattr(registry, name))
            and not isinstance(getattr(registry, name), type)
            and getattr(getattr(registry, name), "__module__", "") == registry.__name__
        }
        self.assertEqual(public_callables, set(EXPECTED_PUBLIC_CALLABLES))

    def test_the_recovery_vocabulary_is_closed_and_complete(self):
        site_fields = {field.name for field in dataclasses.fields(MonsterSite)}
        self.assertEqual(
            tuple(RECOVERY_CONDITION_FIELDS),
            tuple(
                name
                for name in site_fields
                if name in RECOVERY_CONDITION_FIELDS
            ),
        )
        self.assertTrue(set(RECOVERY_CONDITION_FIELDS) <= site_fields)

    def test_ambient_rule_reads_the_published_registry(self):
        with patch.object(
            registry,
            "AMBIENT_PLACEMENT" + "_REGISTRY",
            MappingProxyType({REGION: _rule()}),
        ):
            self.assertEqual(registry.ambient_rule(REGION).region_key, REGION)
            self.assertIsNone(registry.ambient_rule(SPARE_REGION))

    def test_variant_species_key_reads_the_variant_registry(self):
        from world.lore import monster_species as species_registry

        with patch.object(
            species_registry,
            "MONSTER_VARIANT" + "_REGISTRY",
            {ORDINARY: _variant_row(ORDINARY)},
        ):
            self.assertEqual(variant_species_key(ORDINARY), SPECIES)
        with self.assertRaises(KeyError):
            variant_species_key(ABSENT_VARIANT)


class ShippedPlacementContentTests(unittest.TestCase):
    """The authored placement layer is coherent without naming a shipped key."""

    def test_every_shipped_row_validates_against_the_shipped_vocabularies(self):
        # The module-level call already ran at import; this re-runs the same
        # validation over the published rows, so a registry that ever ships an
        # invalid row fails here as well as at import.
        registry.validate_monster_placement_registry(
            dict(_published("AMBIENT_PLACEMENT")), dict(_published("MONSTER_SITE"))
        )

    def test_every_shipped_site_habitat_is_the_region_of_its_coordinates(self):
        from world.maps.wilderness_provider import is_footprint_cell, region_for_coordinates

        for key, site in _published("MONSTER_SITE").items():
            with self.subTest(site=key):
                self.assertEqual(
                    site.region_key, region_for_coordinates(*site.coordinates)
                )
                # A site may only own walkable wild ground: an anchor footprint
                # cell has no wilderness room to host its individuals.
                self.assertFalse(is_footprint_cell(site.coordinates))

    def test_every_shipped_ambient_rule_covers_an_authored_capability(self):
        published = _published("AMBIENT_PLACEMENT")
        self.assertTrue(published)
        for key, rule in published.items():
            with self.subTest(region=key):
                self.assertEqual(key, rule.region_key)
                self.assertTrue(rule.variant_keys)


class MonsterPlacementSyncTests(EvenniaTestCase):
    """Requirement: the mirror is idempotent, bounded, and leaves runtime alone."""

    @staticmethod
    def _expected_record_keys() -> set[str]:
        keys: set[str] = set()
        for category in MONSTER_PLACEMENT_CATEGORIES:
            keys |= {f"lore:{category}:{key}" for key in _ALL_REGISTRIES[category]}
        return keys

    @staticmethod
    def _script_keys() -> set[str]:
        return set(ScriptDB.objects.values_list("db_key", flat=True))

    @staticmethod
    def _runtime_digest(model, *, exclude_prefix: str | None = None) -> tuple:
        rows = []
        for obj in model.objects.all().order_by("pk").values_list("pk", "db_key"):
            if exclude_prefix is not None and (obj[1] or "").startswith(exclude_prefix):
                continue
            rows.append((obj[0], obj[1]))
        return tuple(rows)

    def _runtime_state(self) -> tuple:
        return (
            self._runtime_digest(ObjectDB),
            self._runtime_digest(ScriptDB, exclude_prefix="lore:"),
        )

    @covers_requirement(
        "lore-startup-sync::every-lore-registry-entry-is-mirrored-into-the-db-keyed-by-key"
    )
    def test_the_step_mirrors_exactly_the_placement_records(self):
        expected = self._expected_record_keys()
        self.assertTrue(expected)
        before = self._script_keys()
        sync_monster_placement()
        created = self._script_keys() - before
        self.assertEqual(created, expected - before)
        for category in MONSTER_PLACEMENT_CATEGORIES:
            for key in _ALL_REGISTRIES[category]:
                records = search_script(f"lore:{category}:{key}")
                self.assertEqual(len(records), 1, f"{category}:{key}")
                self.assertEqual(records[0].db.category, category)

    @covers_requirement(
        "lore-startup-sync::every-lore-registry-entry-is-mirrored-into-the-db-keyed-by-key"
    )
    def test_sync_all_mirrors_each_placement_record_exactly_once(self):
        # The generic _ALL_REGISTRIES loop skips the placement categories, so
        # the named step is their only writer and no record is written twice.
        sync_all()
        for category in MONSTER_PLACEMENT_CATEGORIES:
            with self.subTest(category=category):
                self.assertEqual(
                    ScriptDB.objects.filter(db_key__startswith=f"lore:{category}:").count(),
                    len(_ALL_REGISTRIES[category]),
                )

    @covers_requirement(
        "lore-startup-sync::every-lore-registry-entry-is-mirrored-into-the-db-keyed-by-key"
    )
    def test_repeating_the_step_is_a_no_op(self):
        def mirrored_rows():
            return [
                (script.id, script.db.category, script.db.fields)
                for category in MONSTER_PLACEMENT_CATEGORIES
                for key in _ALL_REGISTRIES[category]
                for script in search_script(f"lore:{category}:{key}")
            ]

        sync_monster_placement()
        first_rows = mirrored_rows()
        first_keys = self._script_keys()

        sync_monster_placement()
        self.assertTrue(first_rows)
        self.assertEqual(first_rows, mirrored_rows())
        self.assertEqual(first_keys, self._script_keys())

    def test_one_boundary_event_carries_the_registry_context(self):
        with patch("world.lore.sync.log_info") as info:
            sync_monster_placement()
        self.assertEqual(info.call_count, 1)
        self.assertEqual(info.call_args.args[0], "monster_placement_sync")
        self.assertEqual(
            info.call_args.kwargs["context"],
            {
                category: len(_ALL_REGISTRIES[category])
                for category in MONSTER_PLACEMENT_CATEGORIES
            },
        )

    def test_the_mirror_touches_no_monster_room_or_quest_record(self):
        before = self._runtime_state()
        sync_monster_placement()
        after_first_run = self._runtime_state()
        self.assertEqual(before, after_first_run)
        sync_monster_placement()
        self.assertEqual(after_first_run, self._runtime_state())

    def test_the_mirrored_payload_is_primitive_data(self):
        sync_monster_placement()
        category = MONSTER_PLACEMENT_CATEGORIES[1]
        key = next(iter(_ALL_REGISTRIES[category]))
        fields = search_script(f"lore:{category}:{key}")[0].db.fields
        for value in fields.values():
            self.assertIn(type(value), (str, int, bool, tuple, type(None)))
