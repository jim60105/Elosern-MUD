"""Authored monster placement registries (monster-site-placement design D-P1).

Design §5 splits monster placement in two: deterministic regional ambient
species rules, and explicitly authored camps, nests, and boss sites with their
own lifecycle. Both kinds reference the same variant keys and validate against
the same species/habitat data, so they live in one module and share one
construction-time validation.

This module is data and validation only (requirement R1 of the change's
`lore-registries` delta). Placement *execution* belongs to ``world/maps/``:
``wilderness_population.ensure_population`` reconciles the ambient half and
``monster_sites`` owns the site half, both reading these registries. Nothing
here spawns, places, reconciles, recovers, or mutates any game state — the
public surface is the frozen registries, the builder/validator, and pure read
helpers.

Habitat tags constrain what an author MAY place, never what spawns: the
``region_key`` of every rule and site is checked against every referenced
variant's species ``habitat_tags`` at construction time, and no runtime spawn
decision anywhere reads a habitat tag.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .monster_species import MONSTER_SPECIES_REGISTRY, MONSTER_VARIANT_REGISTRY
from .registry_refs import ref, ref_many
from .wilderness_regions import WILDERNESS_REGION_REGISTRY
# Read the variant registry as a MODULE attribute at call time (never a
# from-import binding captured once): the synthetic test-data kit patches the
# owner module's attribute, so a scoped behavior test observes its stand-in
# here exactly as the map layer does (the ``wilderness_provider`` precedent).
from . import monster_species as _monster_species_module


class MonsterPlacementRegistryError(ValueError):
    """A placement registry row violates the authored-data contract."""


# The closed site-kind vocabulary: authored camps, nests, and boss sites.
MONSTER_SITE_KINDS: tuple[str, ...] = ("camp", "nest", "boss_site")

# The closed recovery-condition vocabulary. One in-game-clock condition ships
# (`recover_after_ticks`, measured in game seconds by the world clock); a future
# approved deterministic predicate joins this tuple by name — never free-form
# text and never wall-clock time. Validation reads the vocabulary from here, so
# a condition no reader understands cannot be authored.
RECOVERY_CONDITION_FIELDS: tuple[str, ...] = ("recover_after_ticks",)


@dataclass(frozen=True, slots=True)
class AmbientPlacementRule:
    """One region's deterministic ambient species placement.

    ``region_key`` doubles as the rule's registry key and as the habitat the
    authoring check runs against. ``variant_keys`` is the eligible set the
    ambient selection chooses from; ``quantity`` is how many living
    species-bearing individuals reconciliation maintains per covered
    coordinate and ``capacity`` is the ceiling it never exceeds there.
    ``selection_salt`` is the determinism parameter: a fixed integer mixed into
    the shared coordinate hash so an author can vary which eligible variant a
    cell selects, with no RNG, database read, or wall-clock input.
    """

    region_key: str = field(metadata=ref("wilderness_regions", inverse="ambient_placements"))
    variant_keys: tuple[str, ...] = field(
        metadata=ref_many("monster_variants", inverse="ambient_placements")
    )
    quantity: int
    capacity: int
    selection_salt: int = 0


@dataclass(frozen=True, slots=True)
class MonsterSite:
    """One authored camp, nest, or boss site and its authored lifecycle.

    ``coordinates`` is the wilderness cell the site owns; every individual the
    site owner creates is registered there and carries the site's ``key`` as its
    persistent ownership marker. ``capacity`` is the number of individuals the
    site holds when populated. ``one_shot`` sites stay cleared after their
    individuals are defeated until an author-side re-issue; a recoverable site
    declares exactly one condition from the closed
    :data:`RECOVERY_CONDITION_FIELDS` vocabulary.
    """

    key: str
    kind: str
    region_key: str = field(metadata=ref("wilderness_regions", inverse="monster_sites"))
    coordinates: tuple[int, int]
    variant_keys: tuple[str, ...] = field(
        metadata=ref_many("monster_variants", inverse="monster_sites")
    )
    capacity: int
    one_shot: bool
    recover_after_ticks: int | None = None


def _require_int(value: object, what: str, minimum: int) -> None:
    """Reject a non-integer (bools included) or out-of-range authored count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise MonsterPlacementRegistryError(
            f"{what} must be an integer literal, got {value!r}"
        )
    if value < minimum:
        raise MonsterPlacementRegistryError(
            f"{what} must be at least {minimum}, got {value!r}"
        )


def _check_region(region_key: object, regions: frozenset[str], what: str) -> None:
    """Reject a placement whose region is not an authored wilderness region."""
    if not isinstance(region_key, str) or not region_key:
        raise MonsterPlacementRegistryError(f"{what} has no region key")
    if region_key not in regions:
        raise MonsterPlacementRegistryError(
            f"{what} names unknown wilderness region {region_key!r}"
        )


def _check_variant_keys(
    variant_keys: object,
    region_key: str,
    variant_face: Mapping[str, object],
    species_face: Mapping[str, object],
    what: str,
) -> None:
    """Reject a non-variant reference or a habitat-incompatible placement.

    Both rejections are authoring-data errors: a placement may name only
    registered variants, and only for a region their species' compatibility
    tags include. This is the sole consumer of habitat tags (requirement R5 of
    `monster-species-registry`), and it runs at construction, never at runtime.
    """
    if not isinstance(variant_keys, tuple) or not variant_keys:
        raise MonsterPlacementRegistryError(
            f"{what} declares no eligible variant keys"
        )
    for variant_key in variant_keys:
        if not isinstance(variant_key, str) or not variant_key:
            raise MonsterPlacementRegistryError(f"{what} has an empty variant key")
        variant = variant_face.get(variant_key)
        if variant is None:
            raise MonsterPlacementRegistryError(
                f"{what} references unknown monster variant {variant_key!r}"
            )
        species = species_face.get(variant.species_key)
        if species is None:
            raise MonsterPlacementRegistryError(
                f"{what} variant {variant_key!r} names unknown species "
                f"{variant.species_key!r}"
            )
        if region_key not in species.habitat_tags:
            raise MonsterPlacementRegistryError(
                f"{what} places variant {variant_key!r} in habitat "
                f"{region_key!r}, which its species habitat tags "
                f"{species.habitat_tags!r} do not include"
            )


def _check_coordinates(coordinates: object, what: str) -> None:
    """Reject an authored host anchor that is not one integer cell pair."""
    if (
        not isinstance(coordinates, tuple)
        or len(coordinates) != 2
        or any(
            isinstance(axis, bool) or not isinstance(axis, int)
            for axis in coordinates
        )
    ):
        raise MonsterPlacementRegistryError(
            f"{what} must name one (x, y) integer cell, got {coordinates!r}"
        )


def build_monster_site_registry(
    declarations: Iterable[MonsterSite],
) -> dict[str, MonsterSite]:
    """Merge declared sites into the keyed registry, rejecting key duplication.

    A site key names exactly one authored site: a second declaration of the same
    key is an authoring error that fails at construction rather than silently
    overwriting the first site (the same discipline
    :func:`world.lore.monster_species.build_monster_variant_registry` applies to
    variant keys).
    """
    registry: dict[str, MonsterSite] = {}
    for site in declarations:
        if site.key in registry:
            raise MonsterPlacementRegistryError(
                f"monster site key {site.key!r} is declared more than once"
            )
        registry[site.key] = site
    return registry


def validate_monster_placement_registry(
    ambient: Mapping[str, AmbientPlacementRule],
    sites: Mapping[str, MonsterSite],
    *,
    region_face: Iterable[str] | None = None,
    variant_face: Mapping[str, object] | None = None,
    species_face: Mapping[str, object] | None = None,
    kind_face: Iterable[str] | None = None,
) -> None:
    """Raise :class:`MonsterPlacementRegistryError` unless every row is valid.

    Pure and DB-free, mirroring ``world/lore/monster_species.py``'s
    ``validate_monster_species_registry`` shape: the module-level registries are
    validated through this one function while they are built, so a malformed
    authored row can never be observed by a consumer.

    The four vocabulary faces default to the static lore registries and the
    closed local kind vocabulary, and are injectable so behavior tests can
    exercise this function with invented keys. Validation only reads its inputs
    and raises before anything is published.
    """
    regions = (
        frozenset(WILDERNESS_REGION_REGISTRY)
        if region_face is None
        else frozenset(region_face)
    )
    variants = MONSTER_VARIANT_REGISTRY if variant_face is None else variant_face
    species = MONSTER_SPECIES_REGISTRY if species_face is None else species_face
    kinds = frozenset(MONSTER_SITE_KINDS) if kind_face is None else frozenset(kind_face)

    for mapping_key, rule in ambient.items():
        what = f"ambient placement rule {mapping_key!r}"
        if mapping_key != rule.region_key:
            raise MonsterPlacementRegistryError(
                f"{what} has region key {rule.region_key!r}; a rule is keyed by "
                "the region it covers"
            )
        _check_region(rule.region_key, regions, what)
        _check_variant_keys(rule.variant_keys, rule.region_key, variants, species, what)
        _require_int(rule.quantity, f"{what} quantity", 1)
        _require_int(rule.capacity, f"{what} capacity", rule.quantity)
        _require_int(rule.selection_salt, f"{what} selection salt", 0)

    for mapping_key, site in sites.items():
        what = f"monster site {mapping_key!r}"
        if not isinstance(site.key, str) or not site.key:
            raise MonsterPlacementRegistryError(f"{what} has no stable site key")
        if mapping_key != site.key:
            raise MonsterPlacementRegistryError(
                f"{what} has key {site.key!r}; a site's registry key is its "
                "ownership marker"
            )
        if site.kind not in kinds:
            raise MonsterPlacementRegistryError(
                f"{what} declares unknown kind {site.kind!r}"
            )
        _check_region(site.region_key, regions, what)
        _check_coordinates(site.coordinates, what)
        _check_variant_keys(site.variant_keys, site.region_key, variants, species, what)
        _require_int(site.capacity, f"{what} capacity", 1)
        if not isinstance(site.one_shot, bool):
            raise MonsterPlacementRegistryError(
                f"{what} must author its one-shot/recoverable life cycle as a "
                "boolean"
            )
        declared = [
            name
            for name in RECOVERY_CONDITION_FIELDS
            if getattr(site, name) is not None
        ]
        if site.one_shot:
            if declared:
                raise MonsterPlacementRegistryError(
                    f"{what} is one-shot and must declare no recovery condition, "
                    f"found {declared!r}"
                )
            continue
        if len(declared) != 1:
            raise MonsterPlacementRegistryError(
                f"{what} is recoverable and must declare exactly one recovery "
                f"condition from {RECOVERY_CONDITION_FIELDS!r}"
            )
        _require_int(
            getattr(site, declared[0]),
            f"{what} recovery condition {declared[0]!r}",
            1,
        )


def ambient_rule(region_key: str) -> AmbientPlacementRule | None:
    """The authored ambient rule covering a region, or ``None``.

    A read helper only: the caller decides whether a coordinate is covered
    (``world/maps/wilderness_population.py`` keeps the hunting band and the
    coordinate hash), because placement execution is not lore's business.
    """
    return AMBIENT_PLACEMENT_REGISTRY.get(region_key)


def variant_species_key(variant_key: str) -> str:
    """The species a registered variant belongs to.

    Placement authors variant references and builds individuals through the
    construction owner, which takes the validated species/variant pair; this is
    the read that supplies the pair's other half from the one variant registry.
    """
    return _monster_species_module.MONSTER_VARIANT_REGISTRY[variant_key].species_key


# ---------------------------------------------------------------------------
# Authored content (the approved bestiary batch of monster-species-registry).
#
# Every rule and site below names approved species and variants only, and each
# region key is one of the habitat tags those variants' species declare. The
# approved balance profile for a placed individual comes from the construction
# owner's balance-gated rule, so nothing here carries a number.
#
# Content boundary (declared, not a shim): the pre-existing tier-example
# ambient branch stays the ambient source for every region without an authored
# rule — `north_deep_forest` and `central_mountains` have no habitat-compatible
# approved species yet, and `southeast_coast` stays with the tier-example
# branch so the introductory curated content keeps its pinned behaviour. The
# hunting band around the capital is excluded from species coverage in code
# (wilderness_population), because its cells are contract-pinned to the
# tier-example branch.
# ---------------------------------------------------------------------------

_AMBIENT_PLACEMENT_DECLARATIONS: tuple[AmbientPlacementRule, ...] = (
    AmbientPlacementRule(
        "eastern_plains",
        ("grain_pecker", "flock_leader", "burrow_maker", "nest_guard"),
        2,
        3,
        1,
    ),
    AmbientPlacementRule(
        "northwest_highland_forest",
        ("wood_stalker", "trail_hunter"),
        1,
        2,
    ),
    AmbientPlacementRule(
        "southwest_coast",
        ("shore_walker", "reef_warden"),
        1,
        2,
    ),
    AmbientPlacementRule(
        "western_hills_valleys",
        ("burrow_maker", "nest_guard", "cliff_stepper", "pass_warden"),
        1,
        2,
    ),
)

_SITE_DECLARATIONS: tuple[MonsterSite, ...] = (
    # A hare nest: one-shot, so clearing it is a durable authored victory until
    # an author re-issues it. The stronger variant guards the ordinary one.
    MonsterSite(
        "ridge_burrow_nest",
        "nest",
        "western_hills_valleys",
        (44, 120),
        ("burrow_maker", "nest_guard"),
        2,
        True,
    ),
    # A goat camp: recoverable, so the pass re-forms one in-game day after it is
    # cleared, with fresh individuals only.
    MonsterSite(
        "cliff_echo_camp",
        "camp",
        "western_hills_valleys",
        (80, 130),
        ("cliff_stepper", "pass_warden"),
        2,
        False,
        86400,
    ),
    # A river-mouth boss site: one-shot, holding the stronger crocodile variant
    # alone. Its authored site carries no ability mechanic, because the species'
    # resource-drain effect is not part of the approved implementation.
    MonsterSite(
        "tide_mouth_boss_site",
        "boss_site",
        "southeast_coast",
        (150, 25),
        ("bay_warden",),
        1,
        True,
    ),
)

_AMBIENT_PLACEMENT_ROWS: dict[str, AmbientPlacementRule] = {
    rule.region_key: rule for rule in _AMBIENT_PLACEMENT_DECLARATIONS
}
_MONSTER_SITE_ROWS: dict[str, MonsterSite] = build_monster_site_registry(
    _SITE_DECLARATIONS
)

# Shipped content must be valid the moment the module loads (titles.py
# precedent): validation runs here, before either registry is published, so an
# authored typo cannot produce a partially valid registry.
validate_monster_placement_registry(_AMBIENT_PLACEMENT_ROWS, _MONSTER_SITE_ROWS)

# The published registries are read-only proxies: every consumer reads through
# `.get` / `values()` / `[key]` / `in`, and no subsystem may mutate lore data
# in place.
AMBIENT_PLACEMENT_REGISTRY: MappingProxyType = MappingProxyType(_AMBIENT_PLACEMENT_ROWS)
MONSTER_SITE_REGISTRY: MappingProxyType = MappingProxyType(_MONSTER_SITE_ROWS)
