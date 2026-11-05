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
from world.lore import monster_species as species_registry
from world.lore.monster_activity import (
    ActivityArea,
    AggressionCondition,
    MonsterActivity,
)
from world.lore.monster_placement import (
    RECOVERY_CONDITION_FIELDS,
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    MonsterPlacementRegistryError,
    MonsterSite,
    SettlementBirthPolicy,
    WeightedComposition,
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
COMPOSITION = "t_fixture_composition"
OTHER_COMPOSITION = "t_fixture_other_composition"
ZONE = "t_fixture_zone"
OTHER_ZONE = "t_fixture_other_zone"
POLICY_ANCHOR = "t_fixture_policy_anchor"
AREA = "t_fixture_activity_area"
ACTIVITY = "t_fixture_activity"
OTHER_ACTIVITY = "t_fixture_other_activity"

# The registry's public callables, in full: read and validate. An execution
# entry point (spawn/place/populate/reconcile/respawn/recover) would have to
# appear here to exist, and the module must never offer one.
EXPECTED_PUBLIC_CALLABLES = frozenset(
    {
        "build_encounter_composition_registry",
        "build_ecology_zone_registry",
        "build_monster_site_registry",
        "build_settlement_birth_policy_registry",
        "composition_bounds",
        "composition_variant_keys",
        "validate_ecology_registries",
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
        False,
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
        "kind_face": ("camp", "nest", "boss_site", "stray", "encounter"),
        "compositions": {COMPOSITION: _composition()},
        "activities": {ACTIVITY: _activity()},
    }
    faces.update(overrides)
    return faces


def _site(**overrides) -> MonsterSite:
    fields = {
        "key": SITE,
        "kind": "camp",
        "region_key": REGION,
        "coordinates": (4, 4),
        "composition_key": COMPOSITION,
        "activity_key": ACTIVITY,
        "capacity": 1,
        "one_shot": True,
        "recover_after_ticks": None,
    }
    fields.update(overrides)
    return MonsterSite(**fields)


def _recovered_site(**overrides) -> MonsterSite:
    return _site(one_shot=False, recover_after_ticks=3600, **overrides)


def _member(
    variant_key: str = ORDINARY, minimum: int = 1, maximum: int = 1
) -> CompositionMember:
    return CompositionMember(variant_key, minimum, maximum)


def _composition(key: str = COMPOSITION, members=None) -> EncounterComposition:
    return EncounterComposition(
        key, ACTIVITY, (_member(),) if members is None else tuple(members)
    )


def _area(**overrides) -> ActivityArea:
    fields = {"key": AREA, "home_radius": 0}
    fields.update(overrides)
    return ActivityArea(**fields)


def _activity(
    key: str = ACTIVITY, policy: str = "stationary", **overrides
) -> MonsterActivity:
    fields = {
        "key": key,
        "policy": policy,
        "area_key": AREA,
        "decision_interval": 1,
        "aggression": AggressionCondition("passive"),
    }
    fields.update(overrides)
    return MonsterActivity(**fields)


def _zone(**overrides) -> EcologyZone:
    fields = {
        "key": ZONE,
        "region_key": REGION,
        "rectangles": ((10, 12, 20, 22),),
        "pool": (WeightedComposition(COMPOSITION, 1),),
        "lower_density": 1,
        "upper_density": 10,
        "cell_capacity": 3,
        "recovery_delay": 3600,
        "replenishment_interval": 600,
        "wave_budget": 3,
    }
    fields.update(overrides)
    return EcologyZone(**fields)


def _ecology_faces(**overrides):
    """The injected vocabularies every ecology validation case runs against."""
    faces = {
        "region_face": (REGION, SPARE_REGION),
        "variant_face": {
            ORDINARY: _variant_row(ORDINARY),
            STRONGER: _variant_row(STRONGER),
        },
        "species_face": {SPECIES: _species_row()},
        "activities": {ACTIVITY: _activity()},
    }
    faces.update(overrides)
    return faces


class PlacementValidationTests(unittest.TestCase):
    """Requirement: placements are validated at construction, before publication."""

    def _reject(self, sites=None, **faces):
        with self.assertRaises(MonsterPlacementRegistryError):
            registry.validate_monster_placement_registry(
                {SITE: _site()} if sites is None else sites,
                **_faces(**faces),
            )

    @covers_requirement("lore-registries::placement-registries-follow-the-frozen-keyed-lore-data-contract")
    @covers_requirement("monster-site-placement::ambient-and-site-placement-are-frozen-keyed-lore-data-validated-at-construction")
    def test_an_unknown_region_is_rejected_for_sites(self):
        self._reject(sites={SITE: _site(region_key=ABSENT_REGION)})

    def test_an_unknown_variant_reference_is_rejected(self):
        self._reject(
            sites={SITE: _site()},
            compositions={
                COMPOSITION: _composition(
                    members=(_member(ORDINARY), _member(ABSENT_VARIANT))
                )
            },
        )

    def test_a_placement_may_not_name_a_non_variant_reference(self):
        # A species key is not a variant key: the pair's variant half is the
        # only reference placement authors.
        self._reject(
            sites={SITE: _site()},
            compositions={COMPOSITION: _composition(members=(_member(SPECIES),))},
        )

    @covers_requirement("monster-site-placement::ambient-and-site-placement-are-frozen-keyed-lore-data-validated-at-construction")
    def test_habitat_incompatible_authoring_fails_at_construction(self):
        mismatched = {SPECIES: _species_row(habitat_tags=(SPARE_REGION,))}
        self._reject(species_face=mismatched)
        self._reject(sites={SITE: _site()}, species_face=mismatched)

    def test_a_variant_of_an_unregistered_species_is_rejected(self):
        orphan = {ORDINARY: _variant_row(ORDINARY, species_key="t_fixture_absent_species")}
        self._reject(variant_face=orphan)

    @covers_requirement("monster-site-placement::one-shot-sites-stay-cleared-and-recoverable-sites-recover-only-on-approved-conditions")
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

    def test_site_capacity_must_be_a_positive_integer(self):
        self._reject(sites={SITE: _site(capacity=0)})

    @covers_requirement("monster-site-placement::ambient-and-site-placement-are-frozen-keyed-lore-data-validated-at-construction")
    def test_a_site_names_one_known_complete_composition(self):
        # A site's membership is the composition it names, never an inferred
        # set: an empty, non-string or unknown reference fails at construction.
        for composition_key in ("", None, "t_fixture_absent_composition"):
            with self.subTest(composition_key=composition_key):
                self._reject(sites={SITE: _site(composition_key=composition_key)})

    @covers_requirement("monster-site-placement::ambient-and-site-placement-are-frozen-keyed-lore-data-validated-at-construction")
    def test_every_legal_composition_outcome_must_fit_the_site_capacity(self):
        # The minimum outcome fits but the maximum does not: capacity is the
        # ceiling of every legal outcome, not of the smallest one.
        varying = _composition(COMPOSITION, (_member(ORDINARY, 1, 3),))
        self._reject(
            sites={SITE: _site(capacity=2)},
            compositions={COMPOSITION: varying},
        )
        registry.validate_monster_placement_registry(
            {SITE: _site(capacity=3)},
            **_faces(compositions={COMPOSITION: varying}),
        )

    @covers_requirement("monster-site-placement::ambient-and-site-placement-are-frozen-keyed-lore-data-validated-at-construction")
    def test_explicit_site_kinds_admit_solitary_and_mixed_placements(self):
        for kind in ("stray", "encounter"):
            with self.subTest(kind=kind):
                registry.validate_monster_placement_registry(
                    {SITE: _site(kind=kind)},
                    **_faces(),
                )

    def test_a_site_is_keyed_by_its_ownership_marker(self):
        self._reject(sites={OTHER_SITE: _site()})

    def test_a_malformed_host_anchor_is_rejected(self):
        self._reject(sites={SITE: _site(coordinates=(4,))})
        self._reject(sites={SITE: _site(coordinates=(4, "5"))})

    def test_a_site_must_name_a_known_activity(self):
        self._reject(sites={SITE: _site(activity_key=OTHER_ACTIVITY)})

    @covers_requirement(
        "monster-field-activity::activity-declarations-publish-complete-validated-bindings"
    )
    def test_a_solitary_site_override_accepts_a_multi_member_composition(self):
        # Publication never lets a member count select or reject a policy: a
        # solitary override of a two-member composition is lawful, and
        # construction disperses the members into one-member groups.
        group = _composition(
            COMPOSITION, (_member(ORDINARY, 1, 1), _member(STRONGER, 1, 1))
        )
        solitary = _activity(OTHER_ACTIVITY, "solitary_roaming")
        registry.validate_monster_placement_registry(
            {SITE: _site(capacity=2, activity_key=OTHER_ACTIVITY)},
            **_faces(
                compositions={COMPOSITION: group},
                activities={ACTIVITY: _activity(), OTHER_ACTIVITY: solitary},
            ),
        )

    def test_a_stationary_site_override_accepts_a_complete_group(self):
        group = _composition(
            COMPOSITION, (_member(ORDINARY, 1, 1), _member(STRONGER, 1, 1))
        )
        registry.validate_monster_placement_registry(
            {SITE: _site(capacity=2)},
            **_faces(compositions={COMPOSITION: group}),
        )

    def test_a_duplicate_site_key_is_rejected(self):
        with self.assertRaises(MonsterPlacementRegistryError):
            registry.build_monster_site_registry((_site(), _site()))

    def test_valid_rows_are_accepted_and_unchanged(self):
        sites = {SITE: _recovered_site(), OTHER_SITE: _site(key=OTHER_SITE)}
        before = dict(sites)
        registry.validate_monster_placement_registry(sites, **_faces())
        self.assertEqual(sites, before)

    @covers_requirement("monster-site-placement::ambient-and-site-placement-are-frozen-keyed-lore-data-validated-at-construction")
    def test_validation_is_pure_and_publishes_nothing(self):
        sites = {SITE: _site(one_shot=False)}
        published_before = dict(_published("MONSTER_SITE"))
        with self.assertRaises(MonsterPlacementRegistryError):
            registry.validate_monster_placement_registry(sites, **_faces())
        self.assertEqual(sites, {SITE: _site(one_shot=False)})
        self.assertEqual(dict(_published("MONSTER_SITE")), published_before)


class EcologyDeclarationTests(unittest.TestCase):
    """Requirement: ecology declarations publish only complete bounded habitats."""

    def _reject(self, zones=None, compositions=None, policies=None, **faces):
        with self.assertRaises(MonsterPlacementRegistryError):
            registry.validate_ecology_registries(
                {ZONE: _zone()} if zones is None else zones,
                {COMPOSITION: _composition()}
                if compositions is None
                else compositions,
                {} if policies is None else policies,
                **_ecology_faces(**faces),
            )

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_composition_forms_resolve_their_explicit_ranges(self):
        # Solitary, repeated-variant and mixed compositions: the range totals
        # come from the declared member ranges alone, never from prose.
        solitary = _composition(COMPOSITION)
        repeated = _composition(OTHER_COMPOSITION, (_member(ORDINARY, 2, 3),))
        mixed = EncounterComposition(
            "t_fixture_mixed",
            ACTIVITY,
            (_member(ORDINARY, 1, 1), _member(STRONGER, 2, 2)),
        )
        compositions = {
            composition.key: composition
            for composition in (solitary, repeated, mixed)
        }
        zone = _zone(
            pool=(
                WeightedComposition(COMPOSITION, 1),
                WeightedComposition(OTHER_COMPOSITION, 2),
                WeightedComposition("t_fixture_mixed", 3),
            )
        )
        registry.validate_ecology_registries(
            {ZONE: zone}, compositions, {}, **_ecology_faces()
        )
        self.assertEqual(registry.composition_bounds(solitary), (1, 1))
        self.assertEqual(registry.composition_bounds(repeated), (2, 3))
        self.assertEqual(registry.composition_bounds(mixed), (3, 3))
        self.assertEqual(
            [row.composition_key for row in zone.pool],
            [COMPOSITION, OTHER_COMPOSITION, "t_fixture_mixed"],
        )
        self.assertEqual([row.weight for row in zone.pool], [1, 2, 3])

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_unknown_and_non_variant_references_are_rejected(self):
        self._reject(
            compositions={
                COMPOSITION: _composition(members=(_member(ABSENT_VARIANT),))
            }
        )
        # A species key is not a variant key, so it can never be a member.
        self._reject(
            compositions={COMPOSITION: _composition(members=(_member(SPECIES),))}
        )

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_habitat_mismatch_is_rejected_for_a_pooled_member(self):
        mismatched = {SPECIES: _species_row(habitat_tags=(SPARE_REGION,))}
        self._reject(species_face=mismatched)
        # The mirror case: a spare-region zone pooling a variant whose species
        # declares only the primary habitat.
        self._reject(
            zones={ZONE: _zone(region_key=SPARE_REGION)},
            species_face={SPECIES: _species_row(habitat_tags=(REGION,))},
        )

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_duplicate_keys_are_rejected(self):
        builders = (
            (
                registry.build_encounter_composition_registry,
                (_composition(), _composition()),
            ),
            (registry.build_ecology_zone_registry, (_zone(), _zone())),
            (
                registry.build_settlement_birth_policy_registry,
                (
                    SettlementBirthPolicy(POLICY_ANCHOR, 1),
                    SettlementBirthPolicy(POLICY_ANCHOR, 1),
                ),
            ),
        )
        for builder, rows in builders:
            with self.subTest(builder=builder.__name__):
                with self.assertRaises(MonsterPlacementRegistryError):
                    builder(rows)
        # A composition names each variant once; repetition is one range.
        self._reject(
            compositions={
                COMPOSITION: _composition(
                    members=(_member(ORDINARY, 1, 1), _member(ORDINARY, 1, 1))
                )
            }
        )
        # A pool names each composition once.
        self._reject(
            zones={
                ZONE: _zone(
                    pool=(
                        WeightedComposition(COMPOSITION, 1),
                        WeightedComposition(COMPOSITION, 2),
                    )
                )
            }
        )

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_inverted_or_non_positive_counts_and_timings_are_rejected(self):
        zone_cases = (
            {"lower_density": True},
            {"lower_density": 0},
            {"upper_density": 0},
            {"upper_density": 100},
            {"lower_density": 5, "upper_density": 4},
            {"cell_capacity": 0},
            {"cell_capacity": True},
            {"recovery_delay": 0},
            {"replenishment_interval": -1},
            {"wave_budget": 0},
        )
        for overrides in zone_cases:
            with self.subTest(overrides=overrides):
                self._reject(zones={ZONE: _zone(**overrides)})
        member_cases = (
            _member(ORDINARY, 0, 1),
            _member(ORDINARY, 2, 1),
            _member(ORDINARY, 1, True),
            _member(ORDINARY, True, 1),
        )
        for member in member_cases:
            with self.subTest(member=member):
                self._reject(
                    compositions={COMPOSITION: _composition(members=(member,))}
                )

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_pool_weights_must_be_positive_and_reference_known_compositions(self):
        self._reject(
            zones={
                ZONE: _zone(
                    pool=(WeightedComposition("t_fixture_absent_composition", 1),)
                )
            }
        )
        for weight in (0, -1, True):
            with self.subTest(weight=weight):
                self._reject(
                    zones={
                        ZONE: _zone(pool=(WeightedComposition(COMPOSITION, weight),))
                    }
                )

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_bounded_geometry_must_be_inclusive_integer_rectangles(self):
        rectangles = (
            (),
            ((10, 12, 20),),
            ((12, 10, 20, 22),),
            ((10, 12, 22, 20),),
            ((10, True, 20, 22),),
            ((10, 12, 20, 22.0),),
        )
        for geometry in rectangles:
            with self.subTest(rectangles=geometry):
                self._reject(zones={ZONE: _zone(rectangles=geometry)})

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats",
        "regional-ecology::density-intervals-permit-complete-unobstructed-recovery",
    )
    def test_a_complete_group_must_fit_cell_capacity_and_wave_budget(self):
        group = _composition(COMPOSITION, (_member(ORDINARY, 1, 4),))
        self._reject(
            zones={ZONE: _zone(cell_capacity=3, wave_budget=4)},
            compositions={COMPOSITION: group},
        )
        self._reject(
            zones={ZONE: _zone(cell_capacity=4, wave_budget=3)},
            compositions={COMPOSITION: group},
        )
        # The same group is legal once both limits can hold it.
        registry.validate_ecology_registries(
            {ZONE: _zone(cell_capacity=4, wave_budget=4)},
            {COMPOSITION: group},
            {},
            **_ecology_faces(),
        )

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_policy_buffers_are_positive_and_keyed_by_their_anchor(self):
        for buffer in (0, -1, True, 1.0):
            with self.subTest(buffer=buffer):
                self._reject(
                    policies={
                        POLICY_ANCHOR: SettlementBirthPolicy(POLICY_ANCHOR, buffer)
                    }
                )
        self._reject(
            policies={
                "t_fixture_other_anchor": SettlementBirthPolicy(POLICY_ANCHOR, 2)
            }
        )
        registry.validate_ecology_registries(
            {ZONE: _zone()},
            {COMPOSITION: _composition()},
            {POLICY_ANCHOR: SettlementBirthPolicy(POLICY_ANCHOR, 2)},
            **_ecology_faces(),
        )

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_validation_is_pure_and_publishes_nothing(self):
        names = ("ENCOUNTER_COMPOSITION", "ECOLOGY_ZONE", "SETTLEMENT_BIRTH_POLICY")
        zones = {ZONE: _zone()}
        compositions = {COMPOSITION: _composition()}
        policies = {POLICY_ANCHOR: SettlementBirthPolicy(POLICY_ANCHOR, 2)}
        before = (
            dict(zones),
            dict(compositions),
            dict(policies),
            [dict(_published(name)) for name in names],
        )
        registry.validate_ecology_registries(
            zones, compositions, policies, **_ecology_faces()
        )
        self.assertEqual(
            (dict(zones), dict(compositions), dict(policies)), before[:3]
        )
        self.assertEqual([dict(_published(name)) for name in names], before[3])
        with self.assertRaises(MonsterPlacementRegistryError):
            registry.validate_ecology_registries(
                {ZONE: _zone(rectangles=())}, compositions, policies,
                **_ecology_faces(),
            )
        self.assertEqual([dict(_published(name)) for name in names], before[3])


class PublishedRegistryTests(unittest.TestCase):
    """Requirement: the published registries are frozen and execution-free."""

    def test_the_published_registries_are_read_only_proxies(self):
        for name in ("MONSTER_SITE",):
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

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_the_published_ecology_registries_are_read_only_proxies(self):
        # The birth-policy registry ships empty (every inhabited settlement
        # already gets the generic minimum ring), so only a populated registry
        # can demonstrate key deletion.
        for name in ("ENCOUNTER_COMPOSITION", "ECOLOGY_ZONE", "SETTLEMENT_BIRTH_POLICY"):
            with self.subTest(registry=name):
                published = _published(name)
                self.assertIsInstance(published, MappingProxyType)
                with self.assertRaises(TypeError):
                    published["t_fixture_intruder"] = None
                if published:
                    with self.assertRaises(TypeError):
                        del published[next(iter(published))]

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

    def test_variant_species_key_reads_the_variant_registry(self):
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

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_every_shipped_row_validates_against_the_shipped_vocabularies(self):
        # The module-level call already ran at import; this re-runs the same
        # validation over the published rows, so a registry that ever ships an
        # invalid row fails here as well as at import.
        registry.validate_monster_placement_registry(
            dict(_published("MONSTER_SITE"))
        )

    def test_every_shipped_site_habitat_is_the_region_of_its_coordinates(self):
        from world.maps.wilderness_provider import is_footprint_cell, region_for_coordinates

        compositions = _published("ENCOUNTER_COMPOSITION")
        for key, site in _published("MONSTER_SITE").items():
            with self.subTest(site=key):
                self.assertEqual(
                    site.region_key, region_for_coordinates(*site.coordinates)
                )
                # A site may only own walkable wild ground: an anchor footprint
                # cell has no wilderness room to host its individuals.
                self.assertFalse(is_footprint_cell(site.coordinates))
                # Every site names a complete authored composition whose legal
                # outcomes all fit the site's own ceiling.
                composition = compositions[site.composition_key]
                _smallest, largest = registry.composition_bounds(composition)
                self.assertGreaterEqual(largest, 1)
                self.assertLessEqual(largest, site.capacity)


class ShippedEcologyContentTests(unittest.TestCase):
    """The authored ecology layer is coherent without naming a shipped key."""

    def test_every_shipped_row_validates_against_the_shipped_vocabularies(self):
        registry.validate_ecology_registries(
            dict(_published("ECOLOGY_ZONE")),
            dict(_published("ENCOUNTER_COMPOSITION")),
            dict(_published("SETTLEMENT_BIRTH_POLICY")),
        )

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_every_shipped_zone_is_keyed_sparse_and_bounded(self):
        published = _published("ECOLOGY_ZONE")
        self.assertTrue(published)
        for key, zone in published.items():
            with self.subTest(zone=key):
                self.assertEqual(key, zone.key)
                self.assertTrue(zone.rectangles)
                self.assertTrue(zone.pool)
                self.assertGreaterEqual(zone.lower_density, 1)
                self.assertLessEqual(zone.lower_density, zone.upper_density)
                # Automatic population can never occupy every eligible cell.
                self.assertLess(zone.upper_density, 100)

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_every_shipped_composition_declares_complete_positive_ranges(self):
        for key, composition in _published("ENCOUNTER_COMPOSITION").items():
            with self.subTest(composition=key):
                self.assertEqual(key, composition.key)
                self.assertTrue(composition.members)
                smallest, largest = registry.composition_bounds(composition)
                self.assertGreaterEqual(smallest, len(composition.members))
                self.assertGreaterEqual(largest, smallest)

    @covers_requirement(
        "regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats"
    )
    def test_every_shipped_pooled_member_belongs_to_its_zone_habitat(self):
        species = getattr(species_registry, "MONSTER_SPECIES" + "_REGISTRY")
        variants = getattr(species_registry, "MONSTER_VARIANT" + "_REGISTRY")
        compositions = _published("ENCOUNTER_COMPOSITION")
        for zone_key, zone in _published("ECOLOGY_ZONE").items():
            for row in zone.pool:
                composition = compositions[row.composition_key]
                for member in composition.members:
                    species_key = variants[member.variant_key].species_key
                    habitat_tags = species[species_key].habitat_tags
                    with self.subTest(zone=zone_key, variant=member.variant_key):
                        self.assertIn(zone.region_key, habitat_tags)

    def test_every_shipped_composition_is_pooled_by_a_zone_or_owned_by_a_site(self):
        # An unreferenced composition would be an authoring leftover: every
        # authored composition exists so some bounded habitat can select it,
        # or an explicit manual site can own its complete membership.
        pooled = {
            row.composition_key
            for zone in _published("ECOLOGY_ZONE").values()
            for row in zone.pool
        }
        owned = {site.composition_key for site in _published("MONSTER_SITE").values()}
        self.assertEqual(
            pooled | owned, set(_published("ENCOUNTER_COMPOSITION"))
        )

    @covers_requirement(
        "regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings"
    )
    def test_explicit_site_placement_never_reads_automatic_birth_geometry(self):
        # The design keeps explicit manual/quest placement outside automatic
        # birth exclusions and density while shared placement validity still
        # applies: the site owner must not consult the ecology geometry at all.
        from pathlib import Path

        from world.maps import monster_sites

        source = Path(monster_sites.__file__).read_text(encoding="utf-8")
        self.assertNotIn("population_geometry", source)
        self.assertNotIn("ECOLOGY_ZONE", source)


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
        category = MONSTER_PLACEMENT_CATEGORIES[0]
        key = next(iter(_ALL_REGISTRIES[category]))
        fields = search_script(f"lore:{category}:{key}")[0].db.fields
        for value in fields.values():
            self.assertIn(type(value), (str, int, bool, tuple, type(None)))
