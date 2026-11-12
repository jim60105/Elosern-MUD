"""Authored monster placement registries (monster-site-placement design D-P1).

Explicitly authored camps, nests, and boss sites, the complete encounter
compositions they name, the bounded regional ecology zones that own automatic
births, and the settlement birth-exclusion policies. All kinds reference the
same variant keys and validate against the same species/habitat data, so they
live in one module and share one construction-time validation.

This module is data and validation only (requirement R1 of the change's
`lore-registries` delta). Placement *execution* belongs to ``world/maps/``:
``regional_population`` owns ordinary births and recovery, ``monster_sites``
owns the site half, and both read these registries. Nothing here spawns,
places, reconciles, recovers, or mutates any game state — the public surface
is the frozen registries, the builder/validator, and pure read helpers.

Habitat tags constrain what an author MAY place, never what spawns: the
``region_key`` of every zone and site is checked against every referenced
variant's species ``habitat_tags`` at construction time, and no runtime spawn
decision anywhere reads a habitat tag.

Each composition row MAY declare its own activity binding, a site MAY declare
one override that governs every row, and a site MAY label the one individual of
a composition whose every legal outcome is exactly one. The pure resolver
:func:`composition_row_bindings` is the single precedence rule the zone writer,
the site owner and the read-only forecast all share.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable, TypeVar

from .monster_species import (
    MONSTER_NAME_MAX_CODE_POINTS,
    MONSTER_SPECIES_REGISTRY,
    MONSTER_VARIANT_REGISTRY,
)
from .monster_activity import (
    MONSTER_ACTIVITY_REGISTRY,
    MonsterActivity,
)
from .registry_refs import ref
# Read the variant registry as a MODULE attribute at call time (never a
# from-import binding captured once): the synthetic test-data kit patches the
# owner module's attribute, so a scoped behavior test observes its stand-in
# here exactly as the map layer does (the ``wilderness_provider`` precedent).
from . import monster_species as _monster_species_module


class MonsterPlacementRegistryError(ValueError):
    """A placement registry row violates the authored-data contract."""


# The closed site-kind vocabulary: authored camps, nests, boss sites, and the
# explicit solitary (``stray``) and mixed (``encounter``) manual placements.
MONSTER_SITE_KINDS: tuple[str, ...] = (
    "camp",
    "nest",
    "boss_site",
    "stray",
    "encounter",
)

# The closed recovery-condition vocabulary. One in-game-clock condition ships
# (`recover_after_ticks`, measured in game seconds by the world clock); a future
# approved deterministic predicate joins this tuple by name — never free-form
# text and never wall-clock time. Validation reads the vocabulary from here, so
# a condition no reader understands cannot be authored.
RECOVERY_CONDITION_FIELDS: tuple[str, ...] = ("recover_after_ticks",)


@dataclass(frozen=True, slots=True)
class MonsterSite:
    """One authored manual site and its authored life cycle.

    ``coordinates`` is the wilderness cell the site owns; every individual the
    site owner creates is registered there and carries the site's ``key`` as its
    persistent ownership marker. ``composition_key`` names one complete
    :class:`EncounterComposition`: the site's individuals are exactly that
    composition's member rows, so a mixed group, a same-variant group, and a
    solitary stray each express their whole membership directly. ``capacity``
    is the ceiling every legal outcome of that composition must fit — a
    definition-validation bound, never an instruction to fill absent rows.
    ``one_shot`` sites stay cleared after their individuals are defeated until
    an author-side re-issue; a recoverable site declares exactly one condition
    from the closed :data:`RECOVERY_CONDITION_FIELDS` vocabulary.
    ``activity_key`` is the site's optional override: ``None`` declares none, so
    every member resolves its row's binding, else the composition's.
    ``individual_name_zh`` is the individual name a site gives the one
    individual every legal outcome of its composition places, at birth; after
    construction the individual owns that name. It is never identity.
    """

    key: str
    kind: str
    region_key: str = field(metadata=ref("wilderness_regions", inverse="monster_sites"))
    coordinates: tuple[int, int]
    composition_key: str = field(
        metadata=ref("encounter_compositions", inverse="monster_sites")
    )
    activity_key: str | None = field(
        metadata=ref("monster_activities", inverse="monster_sites", nullable=True)
    )
    capacity: int
    one_shot: bool
    recover_after_ticks: int | None = None
    individual_name_zh: str | None = None


@dataclass(frozen=True, slots=True)
class CompositionMember:
    """One variant row of a complete encounter composition.

    ``minimum`` and ``maximum`` are the inclusive count range the row may
    contribute. A row is never truncated below its minimum at runtime, so every
    achievable composition total lies inside the sum of its members' ranges.
    ``activity_key`` binds this row's individuals on their own; ``None`` keeps
    the composition binding, so a mixed encounter can hold a cohesive pair
    beside an independent individual.
    """

    variant_key: str = field(
        metadata=ref("monster_variants", inverse="composition_members")
    )
    minimum: int
    maximum: int
    activity_key: str | None = field(
        default=None,
        metadata=ref(
            "monster_activities",
            inverse="composition_member_bindings",
            nullable=True,
        ),
    )


@dataclass(frozen=True, slots=True)
class EncounterComposition:
    """One complete authored encounter: every member group is placed together."""

    key: str
    activity_key: str = field(
        metadata=ref("monster_activities", inverse="encounter_compositions")
    )
    members: tuple[CompositionMember, ...]


@dataclass(frozen=True, slots=True)
class WeightedComposition:
    """One pool row: a complete composition and its positive selection weight."""

    composition_key: str = field(
        metadata=ref("encounter_compositions", inverse="ecology_zone_pools")
    )
    weight: int


@dataclass(frozen=True, slots=True)
class EcologyZone:
    """One bounded authored habitat and its sparse population budget.

    ``rectangles`` are inclusive ``(x_min, x_max, y_min, y_max)`` wilderness
    cells intersected with ``region_key``'s classification and the shared
    map-validity rule, so zone geometry is independent of which rooms have
    materialized. ``lower_density`` and ``upper_density`` are integer
    individuals per one hundred eligible birth cells; ``cell_capacity`` is the
    per-cell automatic-birth ceiling, ``recovery_delay`` and
    ``replenishment_interval`` are game-time seconds, and ``wave_budget`` is
    the largest complete composition one wave may place.
    """

    key: str
    region_key: str = field(
        metadata=ref("wilderness_regions", inverse="ecology_zones")
    )
    rectangles: tuple[tuple[int, int, int, int], ...]
    pool: tuple[WeightedComposition, ...]
    lower_density: int
    upper_density: int
    cell_capacity: int
    recovery_delay: int
    replenishment_interval: int
    wave_budget: int


@dataclass(frozen=True, slots=True)
class SettlementBirthPolicy:
    """One inhabited settlement's authored automatic-birth exclusion buffer.

    The generic minimum one-cell buffer applies to every inhabited settlement
    without a row here; a row only enlarges it. ``buffer_cells`` is an
    inclusive Chebyshev distance from the settlement's complete published
    footprint (or its anchor cell when the settlement is a point).
    """

    anchor_key: str = field(
        metadata=ref("anchors", inverse="settlement_birth_policies")
    )
    buffer_cells: int


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
        species = _check_known_variant(
            variant_key, variant_face, species_face, what
        )
        if region_key not in species.habitat_tags:
            raise MonsterPlacementRegistryError(
                f"{what} places variant {variant_key!r} in habitat "
                f"{region_key!r}, which its species habitat tags "
                f"{species.habitat_tags!r} do not include"
            )


def _check_known_variant(
    variant_key: object,
    variant_face: Mapping[str, object],
    species_face: Mapping[str, object],
    what: str,
):
    """Reject an empty, unregistered, or species-orphaned variant reference."""
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
    return species


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


def _check_site_composition(
    site: MonsterSite,
    compositions: Mapping[str, EncounterComposition],
    variants: Mapping[str, object],
    species: Mapping[str, object],
    what: str,
) -> EncounterComposition:
    """Reject a site whose complete composition is unnamed, unknown, or too large.

    A site holds exactly one authored complete composition, so the reference
    must resolve and every member must be a habitat-compatible variant of the
    site's region. ``capacity`` is that composition's legal ceiling: the
    largest outcome it can ever place must fit, not merely its smallest one.
    """
    composition_key = site.composition_key
    if not isinstance(composition_key, str) or not composition_key:
        raise MonsterPlacementRegistryError(
            f"{what} declares no complete composition key"
        )
    composition = compositions.get(composition_key)
    if composition is None:
        raise MonsterPlacementRegistryError(
            f"{what} references unknown encounter composition {composition_key!r}"
        )
    _check_variant_keys(
        composition_variant_keys(composition),
        site.region_key,
        variants,
        species,
        what,
    )
    _, largest = composition_bounds(composition)
    if largest > site.capacity:
        raise MonsterPlacementRegistryError(
            f"{what} composition {composition_key!r} can place {largest} "
            f"individuals, above its capacity {site.capacity}"
        )
    return composition


def _check_composition_activity(
    composition: EncounterComposition,
    activities: Mapping[str, MonsterActivity],
    what: str,
) -> MonsterActivity:
    """Reject a composition whose activity reference does not resolve.

    Membership is deliberately not checked here: a binding's policy decides how
    construction forms movement groups (``monster_activity.movement_units``),
    so a composition that permits several members is a lawful declaration.
    """
    activity_key = composition.activity_key
    if not isinstance(activity_key, str) or not activity_key:
        raise MonsterPlacementRegistryError(
            f"{what} declares no activity binding"
        )
    activity = activities.get(activity_key)
    if activity is None:
        raise MonsterPlacementRegistryError(
            f"{what} references unknown monster activity {activity_key!r}"
        )
    return activity


def _check_member_activities(
    composition: EncounterComposition,
    activities: Mapping[str, MonsterActivity],
    what: str,
) -> None:
    """Reject a row binding that is empty or names no published activity.

    A row that declares no binding is lawful: it inherits the composition
    binding. The check runs even when a site override would mask the row at
    construction, so an authored typo can never hide behind an override.
    """
    for index, member in enumerate(composition.members):
        activity_key = member.activity_key
        if activity_key is None:
            continue
        if not isinstance(activity_key, str) or not activity_key:
            raise MonsterPlacementRegistryError(
                f"{what} row {index} declares no activity binding"
            )
        if activity_key not in activities:
            raise MonsterPlacementRegistryError(
                f"{what} row {index} references unknown monster activity "
                f"{activity_key!r}"
            )


def _check_site_activity(
    site: MonsterSite,
    activities: Mapping[str, MonsterActivity],
    what: str,
) -> MonsterActivity | None:
    """Reject a site override whose activity reference does not resolve.

    ``None`` is lawful: the site declares no override, so every member resolves
    its row's binding, else the composition's.
    """
    activity_key = site.activity_key
    if activity_key is None:
        return None
    if not isinstance(activity_key, str) or not activity_key:
        raise MonsterPlacementRegistryError(
            f"{what} declares no activity binding"
        )
    activity = activities.get(activity_key)
    if activity is None:
        raise MonsterPlacementRegistryError(
            f"{what} references unknown monster activity {activity_key!r}"
        )
    return activity


def _check_individual_name(
    site: MonsterSite,
    composition: EncounterComposition,
    what: str,
) -> None:
    """Reject an empty or over-long name, or one on a site that can place several."""
    name = site.individual_name_zh
    if name is None:
        return
    if not isinstance(name, str) or not name:
        raise MonsterPlacementRegistryError(
            f"{what} declares an empty individual name"
        )
    if len(name) > MONSTER_NAME_MAX_CODE_POINTS:
        raise MonsterPlacementRegistryError(
            f"{what} declares individual name {name!r} longer than "
            f"{MONSTER_NAME_MAX_CODE_POINTS} code points"
        )
    if composition_bounds(composition) != (1, 1):
        raise MonsterPlacementRegistryError(
            f"{what} declares individual name {name!r}, but composition "
            f"{composition.key!r} can place several individuals"
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


_DeclarationRow = TypeVar("_DeclarationRow")


def _build_keyed_registry(
    declarations: Iterable[_DeclarationRow],
    key_of: Callable[[_DeclarationRow], str],
    what: str,
) -> dict[str, _DeclarationRow]:
    """Merge declared rows into a keyed registry, rejecting duplicate keys."""
    registry: dict[str, _DeclarationRow] = {}
    for entry in declarations:
        key = key_of(entry)
        if key in registry:
            raise MonsterPlacementRegistryError(
                f"{what} key {key!r} is declared more than once"
            )
        registry[key] = entry
    return registry


def build_encounter_composition_registry(
    declarations: Iterable[EncounterComposition],
) -> dict[str, EncounterComposition]:
    """Merge declared compositions into the keyed registry, rejecting duplicates."""
    return _build_keyed_registry(
        declarations, lambda entry: entry.key, "encounter composition"
    )


def build_ecology_zone_registry(
    declarations: Iterable[EcologyZone],
) -> dict[str, EcologyZone]:
    """Merge declared zones into the keyed registry, rejecting duplicate keys."""
    return _build_keyed_registry(declarations, lambda entry: entry.key, "ecology zone")


def build_settlement_birth_policy_registry(
    declarations: Iterable[SettlementBirthPolicy],
) -> dict[str, SettlementBirthPolicy]:
    """Merge declared birth policies into the keyed registry, rejecting duplicates."""
    return _build_keyed_registry(
        declarations, lambda entry: entry.anchor_key, "settlement birth policy"
    )


def composition_bounds(composition: EncounterComposition) -> tuple[int, int]:
    """The inclusive total-individual range one complete composition can place.

    Every member's declared range is exhaustive and contiguous, so the sums of
    the members' ranges form one contiguous total range. Runtime selection
    samples a total from this range; it never truncates a member group.
    """
    return (
        sum(member.minimum for member in composition.members),
        sum(member.maximum for member in composition.members),
    )


def composition_variant_keys(composition: EncounterComposition) -> tuple[str, ...]:
    """The variant keys of one complete composition, in member order.

    A site's authored membership is its composition's membership: consumers
    that report or validate "which variants this placement can hold" read this
    one projection instead of re-deriving a row order of their own.
    """
    return tuple(member.variant_key for member in composition.members)


def composition_row_bindings(
    composition: EncounterComposition,
    *,
    site: MonsterSite | None = None,
) -> tuple[str, ...]:
    """One effective activity key per composition member row, in member order.

    A site override governs the whole site: when ``site`` declares one, every
    row resolves it and no row binding is consulted. Without an override, each
    row resolves its own binding when it declares one, else the composition's.
    The result is parallel to the sampled ``(variant_key, count)`` rows, so a
    writer or the forecast passes it to
    :func:`world.lore.monster_activity.movement_units` unchanged.
    """
    if site is not None and site.activity_key is not None:
        return (site.activity_key,) * len(composition.members)
    return tuple(
        composition.activity_key
        if member.activity_key is None
        else member.activity_key
        for member in composition.members
    )


def _check_rectangles(rectangles: object, what: str) -> None:
    """Reject authored zone geometry that is not inclusive integer rectangles."""
    if not isinstance(rectangles, tuple) or not rectangles:
        raise MonsterPlacementRegistryError(f"{what} declares no bounded geometry")
    for rectangle in rectangles:
        if not isinstance(rectangle, tuple) or len(rectangle) != 4:
            raise MonsterPlacementRegistryError(
                f"{what} geometry must be (x_min, x_max, y_min, y_max) "
                f"rectangles, got {rectangle!r}"
            )
        if any(
            isinstance(bound, bool) or not isinstance(bound, int)
            for bound in rectangle
        ):
            raise MonsterPlacementRegistryError(
                f"{what} geometry bounds must be integer cells, got {rectangle!r}"
            )
        x_min, x_max, y_min, y_max = rectangle
        if x_min > x_max or y_min > y_max:
            raise MonsterPlacementRegistryError(
                f"{what} geometry {rectangle!r} has inverted inclusive bounds"
            )


def _check_composition(
    composition: object,
    variants: Mapping[str, object],
    species: Mapping[str, object],
    what: str,
    *,
    activities: Mapping[str, MonsterActivity],
) -> None:
    """Reject an incomplete composition or one naming illegal member ranges."""
    if not isinstance(composition.key, str) or not composition.key:
        raise MonsterPlacementRegistryError(f"{what} has no stable composition key")
    members = composition.members
    if not isinstance(members, tuple) or not members:
        raise MonsterPlacementRegistryError(f"{what} declares no composition members")
    seen: set[str] = set()
    for member in members:
        if not isinstance(member, CompositionMember):
            raise MonsterPlacementRegistryError(
                f"{what} member must be a CompositionMember, got {member!r}"
            )
        if member.variant_key in seen:
            raise MonsterPlacementRegistryError(
                f"{what} names variant {member.variant_key!r} more than once; "
                "declare one inclusive range instead"
            )
        seen.add(member.variant_key)
        # Habitat compatibility is a property of the zone the composition is
        # pooled into, not of the composition alone, so it is checked there.
        _check_known_variant(member.variant_key, variants, species, what)
        _require_int(member.minimum, f"{what} member {member.variant_key!r} minimum", 1)
        _require_int(
            member.maximum,
            f"{what} member {member.variant_key!r} maximum",
            member.minimum,
        )
    _check_member_activities(composition, activities, what)


def validate_ecology_registries(
    zones: Mapping[str, EcologyZone],
    compositions: Mapping[str, EncounterComposition],
    policies: Mapping[str, SettlementBirthPolicy],
    *,
    region_face: Iterable[str] | None = None,
    variant_face: Mapping[str, object] | None = None,
    species_face: Mapping[str, object] | None = None,
    activities: Mapping[str, MonsterActivity] | None = None,
) -> None:
    """Raise unless every authored ecology declaration is complete and legal.

    Pure and DB-free, like :func:`validate_monster_placement_registry`: the
    module-level registries are validated through this one function while they
    are built, so a malformed declaration can never be observed by a consumer.
    The species, variant and region vocabularies default to the static lore
    registries and are injectable so behavior tests can exercise invented keys.

    This function checks what the authored declarations alone can decide:
    references, habitat compatibility, integer ranges, positive weights and
    timings, and whether one complete composition fits the zone's per-cell
    capacity and wave budget. The density interval and recovery proof need the
    candidate world's eligible birth-cell count, so they belong to
    :func:`world.maps.population_geometry.validate_ecology_geometry`, which
    runs at candidate publication.
    """
    regions = None if region_face is None else frozenset(region_face)
    variants = MONSTER_VARIANT_REGISTRY if variant_face is None else variant_face
    species = MONSTER_SPECIES_REGISTRY if species_face is None else species_face
    activity_rows = (
        MONSTER_ACTIVITY_REGISTRY if activities is None else activities
    )

    for mapping_key, composition in compositions.items():
        what = f"encounter composition {mapping_key!r}"
        if mapping_key != composition.key:
            raise MonsterPlacementRegistryError(
                f"{what} declares key {composition.key!r}; a composition is keyed "
                "by its own key"
            )
        _check_composition(
            composition, variants, species, what, activities=activity_rows
        )
        _check_composition_activity(composition, activity_rows, what)

    for mapping_key, zone in zones.items():
        what = f"ecology zone {mapping_key!r}"
        if not isinstance(zone.key, str) or not zone.key:
            raise MonsterPlacementRegistryError(f"{what} has no stable zone key")
        if mapping_key != zone.key:
            raise MonsterPlacementRegistryError(
                f"{what} declares key {zone.key!r}; a zone is keyed by its own key"
            )
        if not isinstance(zone.region_key, str) or not zone.region_key:
            raise MonsterPlacementRegistryError(f"{what} has no parent region key")
        if regions is not None:
            _check_region(zone.region_key, regions, what)
        _check_rectangles(zone.rectangles, what)
        _require_int(zone.lower_density, f"{what} lower density", 1)
        _require_int(zone.upper_density, f"{what} upper density", zone.lower_density)
        if zone.upper_density >= 100:
            raise MonsterPlacementRegistryError(
                f"{what} upper density must stay below one hundred individuals "
                f"per hundred eligible cells, got {zone.upper_density!r}"
            )
        _require_int(zone.cell_capacity, f"{what} cell capacity", 1)
        _require_int(zone.recovery_delay, f"{what} recovery delay", 1)
        _require_int(
            zone.replenishment_interval, f"{what} replenishment interval", 1
        )
        _require_int(zone.wave_budget, f"{what} wave budget", 1)
        if not isinstance(zone.pool, tuple) or not zone.pool:
            raise MonsterPlacementRegistryError(
                f"{what} declares no weighted composition pool"
            )
        seen: set[str] = set()
        for row in zone.pool:
            if not isinstance(row, WeightedComposition):
                raise MonsterPlacementRegistryError(
                    f"{what} pool row must be a WeightedComposition, got {row!r}"
                )
            composition_key = row.composition_key
            if not isinstance(composition_key, str) or not composition_key:
                raise MonsterPlacementRegistryError(
                    f"{what} pool row has no composition key"
                )
            if composition_key in seen:
                raise MonsterPlacementRegistryError(
                    f"{what} repeats composition {composition_key!r} in its pool"
                )
            seen.add(composition_key)
            _require_int(
                row.weight, f"{what} composition {composition_key!r} weight", 1
            )
            composition = compositions.get(composition_key)
            if composition is None:
                raise MonsterPlacementRegistryError(
                    f"{what} references unknown composition {composition_key!r}"
                )
            for member in composition.members:
                _check_variant_keys(
                    (member.variant_key,),
                    zone.region_key,
                    variants,
                    species,
                    f"{what} composition {composition_key!r}",
                )
            _, largest = composition_bounds(composition)
            if largest > zone.cell_capacity:
                raise MonsterPlacementRegistryError(
                    f"{what} composition {composition_key!r} can place "
                    f"{largest} individuals, above its cell capacity "
                    f"{zone.cell_capacity}"
                )
            if largest > zone.wave_budget:
                raise MonsterPlacementRegistryError(
                    f"{what} composition {composition_key!r} can place "
                    f"{largest} individuals, above its wave budget "
                    f"{zone.wave_budget}"
                )

    for mapping_key, policy in policies.items():
        what = f"settlement birth policy {mapping_key!r}"
        if not isinstance(policy.anchor_key, str) or not policy.anchor_key:
            raise MonsterPlacementRegistryError(f"{what} has no anchor key")
        if mapping_key != policy.anchor_key:
            raise MonsterPlacementRegistryError(
                f"{what} declares key {policy.anchor_key!r}; a policy is keyed by "
                "the anchor it excludes births around"
            )
        _require_int(policy.buffer_cells, f"{what} buffer cells", 1)


def validate_monster_placement_registry(
    sites: Mapping[str, MonsterSite],
    *,
    region_face: Iterable[str] | None = None,
    variant_face: Mapping[str, object] | None = None,
    species_face: Mapping[str, object] | None = None,
    kind_face: Iterable[str] | None = None,
    compositions: Mapping[str, EncounterComposition] | None = None,
    activities: Mapping[str, MonsterActivity] | None = None,
) -> None:
    """Raise :class:`MonsterPlacementRegistryError` unless every row is valid.

    Pure and DB-free, mirroring ``world/lore/monster_species.py``'s
    ``validate_monster_species_registry`` shape: the module-level registries are
    validated through this one function while they are built, so a malformed
    authored row can never be observed by a consumer.

    The vocabulary faces and the composition registry default to the static
    lore values and are injectable so behavior tests can exercise this function
    with invented keys. A site is validated against the complete composition it
    names, so a site can never publish a membership the site owner could not
    place. Validation only reads its inputs and raises before anything is
    published.
    """
    # The terrain-region vocabulary is map-owned (a continent declaration), so
    # it has no import-time lore face: publication of the geography candidate
    # validates every placement region key against the regions it declares.
    # An explicit face still checks membership for behavior tests.
    regions = None if region_face is None else frozenset(region_face)
    variants = MONSTER_VARIANT_REGISTRY if variant_face is None else variant_face
    species = MONSTER_SPECIES_REGISTRY if species_face is None else species_face
    kinds = frozenset(MONSTER_SITE_KINDS) if kind_face is None else frozenset(kind_face)
    composition_rows = (
        ENCOUNTER_COMPOSITION_REGISTRY if compositions is None else compositions
    )
    activity_rows = (
        MONSTER_ACTIVITY_REGISTRY if activities is None else activities
    )

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
        if regions is not None:
            _check_region(site.region_key, regions, what)
        _check_coordinates(site.coordinates, what)
        _require_int(site.capacity, f"{what} capacity", 1)
        composition = _check_site_composition(
            site, composition_rows, variants, species, what
        )
        _check_composition_activity(composition, activity_rows, what)
        _check_member_activities(
            composition, activity_rows, f"{what} composition {composition.key!r}"
        )
        _check_site_activity(site, activity_rows, what)
        _check_individual_name(site, composition, what)
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
_SITE_DECLARATIONS: tuple[MonsterSite, ...] = (
    # A hare nest: one-shot, so clearing it is a durable authored victory until
    # an author re-issues it. Its complete composition pairs the stronger
    # variant with the ordinary one.
    MonsterSite(
        "ridge_burrow_nest",
        "nest",
        "western_hills_valleys",
        (700, 1000),
        "ridge_burrow_nest_group",
        "ridge_burrow_nest_stationary",
        2,
        True,
    ),
    # A goat camp: recoverable, so the pass re-forms one in-game day after it is
    # cleared, with fresh individuals only. Its complete composition is the
    # stronger variant beside the ordinary one.
    MonsterSite(
        "cliff_echo_camp",
        "camp",
        "western_hills_valleys",
        (760, 1150),
        "cliff_echo_camp_group",
        "cliff_echo_camp_stationary",
        2,
        False,
        86400,
    ),
    # A river-mouth boss site: one-shot, holding the stronger crocodile variant
    # alone, so its complete composition is one solitary row. Its authored site
    # carries no ability mechanic, because the species' resource-drain effect is
    # not part of the approved implementation.
    MonsterSite(
        "tide_mouth_boss_site",
        "boss_site",
        "southeast_coast",
        (2100, 300),
        "tide_mouth_boss",
        "tide_mouth_boss_stationary",
        1,
        True,
    ),
    # An abandoned hill transport station: a mixed manual encounter whose two
    # goblins forage as one cohesive pair beside a lone rat gathering grain
    # from the same facility. The three are co-located independent animals, and
    # the encounter is one-shot, so clearing it is a durable authored victory
    # until an author re-issues it.
    MonsterSite(
        "abandoned_transfer_station_encounter",
        "encounter",
        "western_hills_valleys",
        (1290, 990),
        "abandoned_transfer_station_group",
        None,
        3,
        True,
    ),
    # A remote southeast tidal backwater: one stronger crocodile holds the deep
    # bay beside inland water, far from every maintained settlement and outside
    # every authored ecology rectangle. The label is the individual's display
    # key only; identity stays the species/variant pair. The site is one-shot,
    # and it declares no activity override, so the composition's territorial
    # binding governs.
    MonsterSite(
        "reservoir_crocodile_boss_site",
        "boss_site",
        "southeast_coast",
        (2076, 381),
        "reservoir_crocodile_boss",
        None,
        1,
        True,
        individual_name_zh="閉灣者",
    ),
    # A remote dry western woodland consistent with the boar's authored old
    # charcoal-kiln and reused-den ecology, also clear of maintained
    # settlements and ecology rectangles. The label is display only, and the
    # one-shot site lets the composition's territorial binding govern.
    MonsterSite(
        "ember_bristle_boss_site",
        "boss_site",
        "western_hills_valleys",
        (710, 530),
        "ember_bristle_boss",
        None,
        1,
        True,
        individual_name_zh="赤背",
    ),
# North deep forest (north-deep-forest-placement): recoverable nests and camps, and the one-shot leader site.
    MonsterSite(
        "fairy_ring_nest",
        "nest",
        "north_deep_forest",
        (1700, 2000),
        "fairy_ring_nest_group",
        None,
        3,
        False,
        86400,
    ),
    MonsterSite(
        "quill_den_nest",
        "nest",
        "north_deep_forest",
        (1080, 1990),
        "quill_den_nest_group",
        None,
        2,
        False,
        86400,
    ),
    MonsterSite(
        "hollow_roost_camp",
        "camp",
        "north_deep_forest",
        (880, 2300),
        "hollow_roost_camp_group",
        None,
        3,
        False,
        86400,
    ),
    MonsterSite(
        "old_hollow_owl_nest",
        "nest",
        "north_deep_forest",
        (1250, 2100),
        "old_hollow_owl_nest_member",
        None,
        1,
        False,
        86400,
    ),
    MonsterSite(
        "trail_net_camp",
        "camp",
        "north_deep_forest",
        (1840, 2120),
        "trail_net_camp_member",
        None,
        1,
        False,
        86400,
    ),
    MonsterSite(
        "moss_crown_boss_site",
        "boss_site",
        "north_deep_forest",
        (1300, 2400),
        "moss_crown_boss",
        None,
        1,
        True,
        individual_name_zh="蒼冠",
    ),
# Central mountains (central-mountains-placement): recoverable nests and camps, and the one-shot leader site.
    MonsterSite(
        "spring_keeper_pool",
        "nest",
        "central_mountains",
        (1420, 420),
        "spring_keeper_pool_group",
        None,
        3,
        False,
        86400,
    ),
    MonsterSite(
        "vent_crack_den",
        "nest",
        "central_mountains",
        (1420, 1300),
        "vent_crack_den_member",
        None,
        1,
        False,
        86400,
    ),
    MonsterSite(
        "crag_nest_ledge",
        "nest",
        "central_mountains",
        (1396, 604),
        "crag_nest_ledge_member",
        None,
        1,
        False,
        86400,
    ),
    MonsterSite(
        "old_veil_lamp_camp",
        "camp",
        "central_mountains",
        (1430, 900),
        "old_veil_lamp_camp_member",
        None,
        1,
        False,
        86400,
    ),
    MonsterSite(
        "rime_coil_boss_site",
        "boss_site",
        "central_mountains",
        (1406, 96),
        "rime_coil_boss",
        None,
        1,
        True,
        individual_name_zh="霜環",
    ),
# Northwest highland forest (northwest-highland-placement): recoverable nests and camps, and the one-shot leader site.
    MonsterSite(
        "lek_master_lek",
        "camp",
        "northwest_highland_forest",
        (1050, 1520),
        "lek_master_lek_group",
        None,
        3,
        False,
        86400,
    ),
    MonsterSite(
        "old_dam_keeper_dam",
        "nest",
        "northwest_highland_forest",
        (320, 1700),
        "old_dam_keeper_dam_group",
        None,
        3,
        False,
        86400,
    ),
    MonsterSite(
        "deep_seam_mole_den",
        "nest",
        "northwest_highland_forest",
        (1240, 1560),
        "deep_seam_mole_den_member",
        None,
        1,
        False,
        86400,
    ),
    MonsterSite(
        "winter_den_glutton_den",
        "nest",
        "northwest_highland_forest",
        (282, 1902),
        "winter_den_glutton_den_member",
        None,
        1,
        False,
        86400,
    ),
    MonsterSite(
        "golden_plume_boss_site",
        "boss_site",
        "northwest_highland_forest",
        (290, 1440),
        "golden_plume_boss",
        None,
        1,
        True,
        individual_name_zh="金翎",
    ),
# Eastern plains (eastern-plains-deep-placement): recoverable nests and camps, and the one-shot leader site.
    MonsterSite(
        "flock_leader_camp",
        "camp",
        "eastern_plains",
        (1700, 1100),
        "flock_leader_camp_group",
        None,
        3,
        False,
        86400,
    ),
    MonsterSite(
        "nest_guard_nest",
        "nest",
        "eastern_plains",
        (2200, 1200),
        "nest_guard_nest_group",
        None,
        3,
        False,
        86400,
    ),
    MonsterSite(
        "heap_brood_keeper_heap",
        "nest",
        "eastern_plains",
        (2150, 800),
        "heap_brood_keeper_heap_group",
        None,
        3,
        False,
        86400,
    ),
    MonsterSite(
        "herd_stallion_camp",
        "camp",
        "eastern_plains",
        (2400, 750),
        "herd_stallion_camp_group",
        None,
        3,
        False,
        86400,
    ),
    MonsterSite(
        "heronry_elder_nest",
        "nest",
        "eastern_plains",
        (1750, 1700),
        "heronry_elder_nest_group",
        None,
        2,
        False,
        86400,
    ),
    MonsterSite(
        "white_reed_boss_site",
        "boss_site",
        "eastern_plains",
        (2150, 1830),
        "white_reed_boss",
        None,
        1,
        True,
        individual_name_zh="白蘆",
    ),
)

# ---------------------------------------------------------------------------
# Authored ecology zones (regional-ecology-authoring).
#
# Each zone is one bounded rectangle inside an approved habitat, with one
# composition per eligible variant plus the two approved mixed groups. The
# declarations carry the balance values; no documentation or test keeps a
# second approval table. Ground outside these rectangles stays outside
# automatic birth geometry: it simply has no zone, never an implicit species
# source.
# ---------------------------------------------------------------------------

_ENCOUNTER_COMPOSITION_DECLARATIONS: tuple[EncounterComposition, ...] = (
    EncounterComposition(
        "eastern_field_grain_pecker",
        "eastern_field_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_field_flock_leader",
        "eastern_field_flock_leader_activity",
        (CompositionMember("flock_leader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_field_burrow_maker",
        "eastern_field_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_field_nest_guard",
        "eastern_field_nest_guard_activity",
        (CompositionMember("nest_guard", 1, 1),),
    ),
    EncounterComposition(
        "eastern_field_grain_and_burrow",
        "eastern_field_grain_and_burrow_activity",
        (
            CompositionMember("grain_pecker", 1, 1),
            CompositionMember("burrow_maker", 1, 1),
        ),
    ),
    EncounterComposition(
        "highland_wood_stalker",
        "highland_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "highland_trail_hunter",
        "highland_trail_hunter_activity",
        (CompositionMember("trail_hunter", 1, 1),),
    ),
    EncounterComposition(
        "southwest_shore_walker",
        "southwest_shore_walker_activity",
        (CompositionMember("shore_walker", 1, 1),),
    ),
    EncounterComposition(
        "southwest_reef_warden",
        "southwest_reef_warden_activity",
        (CompositionMember("reef_warden", 1, 1),),
    ),
    EncounterComposition(
        "western_rockland_burrow_maker",
        "western_rockland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_rockland_nest_guard",
        "western_rockland_nest_guard_activity",
        (CompositionMember("nest_guard", 1, 1),),
    ),
    EncounterComposition(
        "western_rockland_cliff_stepper",
        "western_rockland_cliff_stepper_activity",
        (CompositionMember("cliff_stepper", 1, 1),),
    ),
    EncounterComposition(
        "western_rockland_pass_warden",
        "western_rockland_pass_warden_activity",
        (CompositionMember("pass_warden", 1, 1),),
    ),
    EncounterComposition(
        "western_rockland_burrow_and_cliff",
        "western_rockland_burrow_and_cliff_activity",
        (
            CompositionMember("burrow_maker", 1, 1),
            CompositionMember("cliff_stepper", 1, 1),
        ),
    ),
    # The sparse weak-species habitats of the content expansion: one complete
    # composition per zone, so automatic birth can never select a species
    # outside its authored patch. The slime's members disperse into their own
    # movement units under the solitary binding; the goblin group and the rat
    # family stay cohesive.
    EncounterComposition(
        "eastern_mudbank_dweller",
        "eastern_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 3),),
    ),
    EncounterComposition(
        "western_mudbank_dweller",
        "western_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 3),),
    ),
    EncounterComposition(
        "western_quarry_nest_forager",
        "western_quarry_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 4),),
    ),
    EncounterComposition(
        "eastern_cache_forager",
        "eastern_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 5),),
    ),
    EncounterComposition(
        "western_cache_forager",
        "western_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 5),),
    ),
    # Complete compositions of the three authored manual sites. They are not
    # pooled into any ecology zone: an explicit site names its own composition,
    # so its membership never depends on automatic birth selection.
    EncounterComposition(
        "ridge_burrow_nest_group",
        "ridge_burrow_nest_group_activity",
        (
            CompositionMember("burrow_maker", 1, 1),
            CompositionMember("nest_guard", 1, 1),
        ),
    ),
    EncounterComposition(
        "cliff_echo_camp_group",
        "cliff_echo_camp_group_activity",
        (
            CompositionMember("cliff_stepper", 1, 1),
            CompositionMember("pass_warden", 1, 1),
        ),
    ),
    EncounterComposition(
        "tide_mouth_boss",
        "tide_mouth_boss_activity",
        (CompositionMember("bay_warden", 1, 1),),
    ),
    # The abandoned transfer station's complete membership: the goblin pair
    # keeps its own cohesive binding, and the explicitly authored rat stray
    # keeps its solitary binding instead of the ordinary family birth range.
    # Co-location never merges the two groups.
    EncounterComposition(
        "abandoned_transfer_station_group",
        "transfer_station_nest_activity",
        (
            CompositionMember(
                "hanging_nest_forager",
                2,
                2,
                activity_key="transfer_station_nest_activity",
            ),
            CompositionMember(
                "wax_cache_forager",
                1,
                1,
                activity_key="transfer_station_stray_activity",
            ),
        ),
    ),
    # The two high-tier boss compositions are solitary rows owned by explicit
    # one-shot sites. Neither row joins an ecology pool, so automatic birth can
    # never select a stronger variant.
    EncounterComposition(
        "reservoir_crocodile_boss",
        "reservoir_crocodile_territory_activity",
        (CompositionMember("reservoir_warden", 1, 1),),
    ),
    EncounterComposition(
        "ember_bristle_boss",
        "ember_bristle_territory_activity",
        (CompositionMember("warm_den_boar", 1, 1),),
    ),
# Near-settlement belts (eastern-plains-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    EncounterComposition(
        "capital_grandia_east_hinterland_grain_pecker",
        "capital_grandia_east_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "capital_grandia_east_hinterland_burrow_maker",
        "capital_grandia_east_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "capital_grandia_east_hinterland_mudbank_dweller",
        "capital_grandia_east_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "capital_grandia_east_hinterland_wax_cache_forager",
        "capital_grandia_east_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "capital_grandia_west_hinterland_grain_pecker",
        "capital_grandia_west_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "capital_grandia_west_hinterland_burrow_maker",
        "capital_grandia_west_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "capital_grandia_west_hinterland_mudbank_dweller",
        "capital_grandia_west_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "capital_grandia_west_hinterland_wax_cache_forager",
        "capital_grandia_west_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_imperial_ferry_east_hinterland_grain_pecker",
        "city_imperial_ferry_east_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "city_imperial_ferry_east_hinterland_burrow_maker",
        "city_imperial_ferry_east_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_imperial_ferry_east_hinterland_mudbank_dweller",
        "city_imperial_ferry_east_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_imperial_ferry_east_hinterland_wax_cache_forager",
        "city_imperial_ferry_east_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_imperial_ferry_west_hinterland_grain_pecker",
        "city_imperial_ferry_west_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "city_imperial_ferry_west_hinterland_burrow_maker",
        "city_imperial_ferry_west_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_imperial_ferry_west_hinterland_mudbank_dweller",
        "city_imperial_ferry_west_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_imperial_ferry_west_hinterland_wax_cache_forager",
        "city_imperial_ferry_west_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_spice_road_east_hinterland_grain_pecker",
        "city_spice_road_east_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "city_spice_road_east_hinterland_burrow_maker",
        "city_spice_road_east_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_spice_road_east_hinterland_mudbank_dweller",
        "city_spice_road_east_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_spice_road_east_hinterland_wax_cache_forager",
        "city_spice_road_east_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_spice_road_west_hinterland_grain_pecker",
        "city_spice_road_west_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "city_spice_road_west_hinterland_burrow_maker",
        "city_spice_road_west_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_spice_road_west_hinterland_mudbank_dweller",
        "city_spice_road_west_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_spice_road_west_hinterland_wax_cache_forager",
        "city_spice_road_west_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_starglow_east_hinterland_grain_pecker",
        "city_starglow_east_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "city_starglow_east_hinterland_burrow_maker",
        "city_starglow_east_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_starglow_east_hinterland_mudbank_dweller",
        "city_starglow_east_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_starglow_east_hinterland_wax_cache_forager",
        "city_starglow_east_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_starglow_west_hinterland_grain_pecker",
        "city_starglow_west_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "city_starglow_west_hinterland_burrow_maker",
        "city_starglow_west_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_starglow_west_hinterland_mudbank_dweller",
        "city_starglow_west_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_starglow_west_hinterland_wax_cache_forager",
        "city_starglow_west_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_twin_currents_east_hinterland_grain_pecker",
        "city_twin_currents_east_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "city_twin_currents_east_hinterland_burrow_maker",
        "city_twin_currents_east_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_twin_currents_east_hinterland_mudbank_dweller",
        "city_twin_currents_east_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_twin_currents_east_hinterland_wax_cache_forager",
        "city_twin_currents_east_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_twin_currents_west_hinterland_grain_pecker",
        "city_twin_currents_west_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "city_twin_currents_west_hinterland_burrow_maker",
        "city_twin_currents_west_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_twin_currents_west_hinterland_mudbank_dweller",
        "city_twin_currents_west_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_twin_currents_west_hinterland_wax_cache_forager",
        "city_twin_currents_west_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_wheatwave_east_hinterland_grain_pecker",
        "city_wheatwave_east_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "city_wheatwave_east_hinterland_burrow_maker",
        "city_wheatwave_east_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_wheatwave_east_hinterland_mudbank_dweller",
        "city_wheatwave_east_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_wheatwave_east_hinterland_wax_cache_forager",
        "city_wheatwave_east_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_wheatwave_west_hinterland_grain_pecker",
        "city_wheatwave_west_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "city_wheatwave_west_hinterland_burrow_maker",
        "city_wheatwave_west_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_wheatwave_west_hinterland_mudbank_dweller",
        "city_wheatwave_west_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_wheatwave_west_hinterland_wax_cache_forager",
        "city_wheatwave_west_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "port_dawnlight_hinterland_grain_pecker",
        "port_dawnlight_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "port_dawnlight_hinterland_burrow_maker",
        "port_dawnlight_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "port_dawnlight_hinterland_mudbank_dweller",
        "port_dawnlight_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "port_dawnlight_hinterland_wax_cache_forager",
        "port_dawnlight_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "port_tide_wind_hinterland_grain_pecker",
        "port_tide_wind_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "port_tide_wind_hinterland_burrow_maker",
        "port_tide_wind_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "port_tide_wind_hinterland_mudbank_dweller",
        "port_tide_wind_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "port_tide_wind_hinterland_wax_cache_forager",
        "port_tide_wind_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_black_soil_hinterland_grain_pecker",
        "town_black_soil_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_black_soil_hinterland_burrow_maker",
        "town_black_soil_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_black_soil_hinterland_mudbank_dweller",
        "town_black_soil_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_black_soil_hinterland_wax_cache_forager",
        "town_black_soil_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_crystal_hinterland_grain_pecker",
        "town_crystal_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_crystal_hinterland_burrow_maker",
        "town_crystal_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_crystal_hinterland_mudbank_dweller",
        "town_crystal_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_crystal_hinterland_wax_cache_forager",
        "town_crystal_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_east_pasture_hinterland_grain_pecker",
        "town_east_pasture_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_east_pasture_hinterland_burrow_maker",
        "town_east_pasture_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_east_pasture_hinterland_mudbank_dweller",
        "town_east_pasture_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_east_pasture_hinterland_wax_cache_forager",
        "town_east_pasture_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_emerald_lake_hinterland_grain_pecker",
        "town_emerald_lake_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_emerald_lake_hinterland_burrow_maker",
        "town_emerald_lake_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_emerald_lake_hinterland_mudbank_dweller",
        "town_emerald_lake_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_emerald_lake_hinterland_wax_cache_forager",
        "town_emerald_lake_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_maple_foot_hinterland_grain_pecker",
        "town_maple_foot_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_maple_foot_hinterland_burrow_maker",
        "town_maple_foot_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_maple_foot_hinterland_mudbank_dweller",
        "town_maple_foot_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_maple_foot_hinterland_wax_cache_forager",
        "town_maple_foot_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_north_wood_keep_hinterland_grain_pecker",
        "town_north_wood_keep_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_north_wood_keep_hinterland_burrow_maker",
        "town_north_wood_keep_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_north_wood_keep_hinterland_mudbank_dweller",
        "town_north_wood_keep_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_north_wood_keep_hinterland_wax_cache_forager",
        "town_north_wood_keep_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_orange_blossom_hinterland_grain_pecker",
        "town_orange_blossom_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_orange_blossom_hinterland_burrow_maker",
        "town_orange_blossom_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_orange_blossom_hinterland_mudbank_dweller",
        "town_orange_blossom_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_orange_blossom_hinterland_wax_cache_forager",
        "town_orange_blossom_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_silver_ridge_hinterland_grain_pecker",
        "town_silver_ridge_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_silver_ridge_hinterland_burrow_maker",
        "town_silver_ridge_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_silver_ridge_hinterland_mudbank_dweller",
        "town_silver_ridge_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_silver_ridge_hinterland_wax_cache_forager",
        "town_silver_ridge_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_steed_plain_hinterland_grain_pecker",
        "town_steed_plain_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_steed_plain_hinterland_burrow_maker",
        "town_steed_plain_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_steed_plain_hinterland_mudbank_dweller",
        "town_steed_plain_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_steed_plain_hinterland_wax_cache_forager",
        "town_steed_plain_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_sunken_bell_hinterland_grain_pecker",
        "town_sunken_bell_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_sunken_bell_hinterland_burrow_maker",
        "town_sunken_bell_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_sunken_bell_hinterland_mudbank_dweller",
        "town_sunken_bell_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_sunken_bell_hinterland_wax_cache_forager",
        "town_sunken_bell_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_sunrise_hinterland_grain_pecker",
        "town_sunrise_hinterland_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "town_sunrise_hinterland_burrow_maker",
        "town_sunrise_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_sunrise_hinterland_mudbank_dweller",
        "town_sunrise_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_sunrise_hinterland_wax_cache_forager",
        "town_sunrise_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_01_grain_pecker",
        "eastern_road_01_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_01_burrow_maker",
        "eastern_road_01_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_01_mudbank_dweller",
        "eastern_road_01_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_01_wax_cache_forager",
        "eastern_road_01_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_02_grain_pecker",
        "eastern_road_02_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_02_burrow_maker",
        "eastern_road_02_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_02_mudbank_dweller",
        "eastern_road_02_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_02_wax_cache_forager",
        "eastern_road_02_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_03_grain_pecker",
        "eastern_road_03_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_03_burrow_maker",
        "eastern_road_03_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_03_mudbank_dweller",
        "eastern_road_03_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_03_wax_cache_forager",
        "eastern_road_03_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_04_grain_pecker",
        "eastern_road_04_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_04_burrow_maker",
        "eastern_road_04_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_04_mudbank_dweller",
        "eastern_road_04_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_04_wax_cache_forager",
        "eastern_road_04_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_05_grain_pecker",
        "eastern_road_05_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_05_burrow_maker",
        "eastern_road_05_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_05_mudbank_dweller",
        "eastern_road_05_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_05_wax_cache_forager",
        "eastern_road_05_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_06_grain_pecker",
        "eastern_road_06_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_06_burrow_maker",
        "eastern_road_06_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_06_mudbank_dweller",
        "eastern_road_06_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_06_wax_cache_forager",
        "eastern_road_06_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_07_grain_pecker",
        "eastern_road_07_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_07_burrow_maker",
        "eastern_road_07_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_07_mudbank_dweller",
        "eastern_road_07_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_07_wax_cache_forager",
        "eastern_road_07_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_08_grain_pecker",
        "eastern_road_08_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_08_burrow_maker",
        "eastern_road_08_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_08_mudbank_dweller",
        "eastern_road_08_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_08_wax_cache_forager",
        "eastern_road_08_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_09_grain_pecker",
        "eastern_road_09_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_09_burrow_maker",
        "eastern_road_09_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_09_mudbank_dweller",
        "eastern_road_09_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_09_wax_cache_forager",
        "eastern_road_09_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_10_grain_pecker",
        "eastern_road_10_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_10_burrow_maker",
        "eastern_road_10_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_10_mudbank_dweller",
        "eastern_road_10_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_10_wax_cache_forager",
        "eastern_road_10_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_11_grain_pecker",
        "eastern_road_11_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_11_burrow_maker",
        "eastern_road_11_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_11_mudbank_dweller",
        "eastern_road_11_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_11_wax_cache_forager",
        "eastern_road_11_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "eastern_road_12_grain_pecker",
        "eastern_road_12_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_12_burrow_maker",
        "eastern_road_12_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_12_mudbank_dweller",
        "eastern_road_12_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_12_wax_cache_forager",
        "eastern_road_12_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
# Near-settlement belts (western-hills-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    EncounterComposition(
        "capital_altoria_east_hinterland_burrow_maker",
        "capital_altoria_east_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "capital_altoria_east_hinterland_mudbank_dweller",
        "capital_altoria_east_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "capital_altoria_east_hinterland_wax_cache_forager",
        "capital_altoria_east_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "capital_altoria_east_hinterland_hanging_nest_forager",
        "capital_altoria_east_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "capital_altoria_west_hinterland_burrow_maker",
        "capital_altoria_west_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "capital_altoria_west_hinterland_mudbank_dweller",
        "capital_altoria_west_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "capital_altoria_west_hinterland_wax_cache_forager",
        "capital_altoria_west_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "capital_altoria_west_hinterland_hanging_nest_forager",
        "capital_altoria_west_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_border_bridge_east_hinterland_burrow_maker",
        "city_border_bridge_east_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_border_bridge_east_hinterland_mudbank_dweller",
        "city_border_bridge_east_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_border_bridge_east_hinterland_wax_cache_forager",
        "city_border_bridge_east_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_border_bridge_east_hinterland_hanging_nest_forager",
        "city_border_bridge_east_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_border_bridge_west_hinterland_burrow_maker",
        "city_border_bridge_west_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_border_bridge_west_hinterland_mudbank_dweller",
        "city_border_bridge_west_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_border_bridge_west_hinterland_wax_cache_forager",
        "city_border_bridge_west_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_border_bridge_west_hinterland_hanging_nest_forager",
        "city_border_bridge_west_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_confluence_east_hinterland_burrow_maker",
        "city_confluence_east_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_confluence_east_hinterland_mudbank_dweller",
        "city_confluence_east_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_confluence_east_hinterland_wax_cache_forager",
        "city_confluence_east_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_confluence_east_hinterland_hanging_nest_forager",
        "city_confluence_east_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_confluence_west_hinterland_burrow_maker",
        "city_confluence_west_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_confluence_west_hinterland_mudbank_dweller",
        "city_confluence_west_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_confluence_west_hinterland_wax_cache_forager",
        "city_confluence_west_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_confluence_west_hinterland_hanging_nest_forager",
        "city_confluence_west_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_east_river_north_hinterland_burrow_maker",
        "city_east_river_north_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_east_river_north_hinterland_mudbank_dweller",
        "city_east_river_north_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_east_river_north_hinterland_wax_cache_forager",
        "city_east_river_north_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_east_river_north_hinterland_hanging_nest_forager",
        "city_east_river_north_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_east_river_south_hinterland_burrow_maker",
        "city_east_river_south_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_east_river_south_hinterland_mudbank_dweller",
        "city_east_river_south_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_east_river_south_hinterland_wax_cache_forager",
        "city_east_river_south_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_east_river_south_hinterland_hanging_nest_forager",
        "city_east_river_south_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_greyrock_east_hinterland_burrow_maker",
        "city_greyrock_east_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_greyrock_east_hinterland_mudbank_dweller",
        "city_greyrock_east_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_greyrock_east_hinterland_wax_cache_forager",
        "city_greyrock_east_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_greyrock_east_hinterland_hanging_nest_forager",
        "city_greyrock_east_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_greyrock_west_hinterland_burrow_maker",
        "city_greyrock_west_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "city_greyrock_west_hinterland_mudbank_dweller",
        "city_greyrock_west_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "city_greyrock_west_hinterland_wax_cache_forager",
        "city_greyrock_west_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "city_greyrock_west_hinterland_hanging_nest_forager",
        "city_greyrock_west_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "port_hills_mouth_hinterland_burrow_maker",
        "port_hills_mouth_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "port_hills_mouth_hinterland_mudbank_dweller",
        "port_hills_mouth_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "port_hills_mouth_hinterland_wax_cache_forager",
        "port_hills_mouth_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "port_hills_mouth_hinterland_hanging_nest_forager",
        "port_hills_mouth_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "port_west_ore_hinterland_burrow_maker",
        "port_west_ore_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "port_west_ore_hinterland_mudbank_dweller",
        "port_west_ore_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "port_west_ore_hinterland_wax_cache_forager",
        "port_west_ore_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "port_west_ore_hinterland_hanging_nest_forager",
        "port_west_ore_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "port_westwind_hinterland_burrow_maker",
        "port_westwind_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "port_westwind_hinterland_mudbank_dweller",
        "port_westwind_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "port_westwind_hinterland_wax_cache_forager",
        "port_westwind_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "port_westwind_hinterland_hanging_nest_forager",
        "port_westwind_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_east_ferry_hinterland_burrow_maker",
        "town_east_ferry_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_east_ferry_hinterland_mudbank_dweller",
        "town_east_ferry_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_east_ferry_hinterland_wax_cache_forager",
        "town_east_ferry_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_east_ferry_hinterland_hanging_nest_forager",
        "town_east_ferry_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_honey_vale_hinterland_burrow_maker",
        "town_honey_vale_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_honey_vale_hinterland_mudbank_dweller",
        "town_honey_vale_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_honey_vale_hinterland_wax_cache_forager",
        "town_honey_vale_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_honey_vale_hinterland_hanging_nest_forager",
        "town_honey_vale_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_ruins_gate_hinterland_burrow_maker",
        "town_ruins_gate_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_ruins_gate_hinterland_mudbank_dweller",
        "town_ruins_gate_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_ruins_gate_hinterland_wax_cache_forager",
        "town_ruins_gate_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_ruins_gate_hinterland_hanging_nest_forager",
        "town_ruins_gate_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_scarp_hinterland_burrow_maker",
        "town_scarp_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_scarp_hinterland_mudbank_dweller",
        "town_scarp_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_scarp_hinterland_wax_cache_forager",
        "town_scarp_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_scarp_hinterland_hanging_nest_forager",
        "town_scarp_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_vineyard_hinterland_burrow_maker",
        "town_vineyard_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_vineyard_hinterland_mudbank_dweller",
        "town_vineyard_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_vineyard_hinterland_wax_cache_forager",
        "town_vineyard_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_vineyard_hinterland_hanging_nest_forager",
        "town_vineyard_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_west_ferry_hinterland_burrow_maker",
        "town_west_ferry_hinterland_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "town_west_ferry_hinterland_mudbank_dweller",
        "town_west_ferry_hinterland_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "town_west_ferry_hinterland_wax_cache_forager",
        "town_west_ferry_hinterland_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "town_west_ferry_hinterland_hanging_nest_forager",
        "town_west_ferry_hinterland_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_01_cliff_stepper",
        "western_road_01_cliff_stepper_activity",
        (CompositionMember("cliff_stepper", 1, 1),),
    ),
    EncounterComposition(
        "western_road_01_burrow_maker",
        "western_road_01_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_road_01_hanging_nest_forager",
        "western_road_01_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_02_cliff_stepper",
        "western_road_02_cliff_stepper_activity",
        (CompositionMember("cliff_stepper", 1, 1),),
    ),
    EncounterComposition(
        "western_road_02_burrow_maker",
        "western_road_02_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_road_02_hanging_nest_forager",
        "western_road_02_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_03_burrow_maker",
        "western_road_03_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_road_03_mudbank_dweller",
        "western_road_03_mudbank_dweller_activity",
        (CompositionMember("mudbank_dweller", 1, 2),),
    ),
    EncounterComposition(
        "western_road_03_wax_cache_forager",
        "western_road_03_wax_cache_forager_activity",
        (CompositionMember("wax_cache_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_03_hanging_nest_forager",
        "western_road_03_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_04_cliff_stepper",
        "western_road_04_cliff_stepper_activity",
        (CompositionMember("cliff_stepper", 1, 1),),
    ),
    EncounterComposition(
        "western_road_04_burrow_maker",
        "western_road_04_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_road_04_hanging_nest_forager",
        "western_road_04_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_05_cliff_stepper",
        "western_road_05_cliff_stepper_activity",
        (CompositionMember("cliff_stepper", 1, 1),),
    ),
    EncounterComposition(
        "western_road_05_burrow_maker",
        "western_road_05_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_road_05_hanging_nest_forager",
        "western_road_05_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_06_cliff_stepper",
        "western_road_06_cliff_stepper_activity",
        (CompositionMember("cliff_stepper", 1, 1),),
    ),
    EncounterComposition(
        "western_road_06_burrow_maker",
        "western_road_06_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_road_06_hanging_nest_forager",
        "western_road_06_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_07_cliff_stepper",
        "western_road_07_cliff_stepper_activity",
        (CompositionMember("cliff_stepper", 1, 1),),
    ),
    EncounterComposition(
        "western_road_07_burrow_maker",
        "western_road_07_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_road_07_hanging_nest_forager",
        "western_road_07_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_08_cliff_stepper",
        "western_road_08_cliff_stepper_activity",
        (CompositionMember("cliff_stepper", 1, 1),),
    ),
    EncounterComposition(
        "western_road_08_burrow_maker",
        "western_road_08_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_road_08_hanging_nest_forager",
        "western_road_08_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_09_cliff_stepper",
        "western_road_09_cliff_stepper_activity",
        (CompositionMember("cliff_stepper", 1, 1),),
    ),
    EncounterComposition(
        "western_road_09_burrow_maker",
        "western_road_09_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_road_09_hanging_nest_forager",
        "western_road_09_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
    EncounterComposition(
        "western_road_10_cliff_stepper",
        "western_road_10_cliff_stepper_activity",
        (CompositionMember("cliff_stepper", 1, 1),),
    ),
    EncounterComposition(
        "western_road_10_burrow_maker",
        "western_road_10_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "western_road_10_hanging_nest_forager",
        "western_road_10_hanging_nest_forager_activity",
        (CompositionMember("hanging_nest_forager", 2, 3),),
    ),
# Near-settlement belts (coastal-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    EncounterComposition(
        "port_east_bay_hinterland_shore_walker",
        "port_east_bay_hinterland_shore_walker_activity",
        (CompositionMember("shore_walker", 1, 1),),
    ),
    EncounterComposition(
        "port_east_bay_hinterland_shore_walker_pair",
        "port_east_bay_hinterland_shore_walker_pair_activity",
        (CompositionMember("shore_walker", 2, 2),),
    ),
    EncounterComposition(
        "port_east_bay_hinterland_shore_walker_trio",
        "port_east_bay_hinterland_shore_walker_trio_activity",
        (CompositionMember("shore_walker", 3, 3),),
    ),
    EncounterComposition(
        "port_golden_sheaf_hinterland_shore_walker",
        "port_golden_sheaf_hinterland_shore_walker_activity",
        (CompositionMember("shore_walker", 1, 1),),
    ),
    EncounterComposition(
        "port_golden_sheaf_hinterland_shore_walker_pair",
        "port_golden_sheaf_hinterland_shore_walker_pair_activity",
        (CompositionMember("shore_walker", 2, 2),),
    ),
    EncounterComposition(
        "port_golden_sheaf_hinterland_shore_walker_trio",
        "port_golden_sheaf_hinterland_shore_walker_trio_activity",
        (CompositionMember("shore_walker", 3, 3),),
    ),
    EncounterComposition(
        "port_south_cape_hinterland_shore_walker",
        "port_south_cape_hinterland_shore_walker_activity",
        (CompositionMember("shore_walker", 1, 1),),
    ),
    EncounterComposition(
        "port_south_cape_hinterland_shore_walker_pair",
        "port_south_cape_hinterland_shore_walker_pair_activity",
        (CompositionMember("shore_walker", 2, 2),),
    ),
    EncounterComposition(
        "port_south_cape_hinterland_shore_walker_trio",
        "port_south_cape_hinterland_shore_walker_trio_activity",
        (CompositionMember("shore_walker", 3, 3),),
    ),
    EncounterComposition(
        "southeast_road_01_bank_lurker",
        "southeast_road_01_bank_lurker_activity",
        (CompositionMember("bank_lurker", 1, 1),),
    ),
    EncounterComposition(
        "southeast_road_01_shore_walker",
        "southeast_road_01_shore_walker_activity",
        (CompositionMember("shore_walker", 1, 1),),
    ),
    EncounterComposition(
        "southeast_road_01_shore_walker_pair",
        "southeast_road_01_shore_walker_pair_activity",
        (CompositionMember("shore_walker", 2, 2),),
    ),
    EncounterComposition(
        "port_fishers_cove_hinterland_shore_walker",
        "port_fishers_cove_hinterland_shore_walker_activity",
        (CompositionMember("shore_walker", 1, 1),),
    ),
    EncounterComposition(
        "port_fishers_cove_hinterland_shore_walker_pair",
        "port_fishers_cove_hinterland_shore_walker_pair_activity",
        (CompositionMember("shore_walker", 2, 2),),
    ),
    EncounterComposition(
        "port_fishers_cove_hinterland_shore_walker_trio",
        "port_fishers_cove_hinterland_shore_walker_trio_activity",
        (CompositionMember("shore_walker", 3, 3),),
    ),
    EncounterComposition(
        "port_south_tide_hinterland_shore_walker",
        "port_south_tide_hinterland_shore_walker_activity",
        (CompositionMember("shore_walker", 1, 1),),
    ),
    EncounterComposition(
        "port_south_tide_hinterland_shore_walker_pair",
        "port_south_tide_hinterland_shore_walker_pair_activity",
        (CompositionMember("shore_walker", 2, 2),),
    ),
    EncounterComposition(
        "port_south_tide_hinterland_shore_walker_trio",
        "port_south_tide_hinterland_shore_walker_trio_activity",
        (CompositionMember("shore_walker", 3, 3),),
    ),
    EncounterComposition(
        "port_white_sail_hinterland_shore_walker",
        "port_white_sail_hinterland_shore_walker_activity",
        (CompositionMember("shore_walker", 1, 1),),
    ),
    EncounterComposition(
        "port_white_sail_hinterland_shore_walker_pair",
        "port_white_sail_hinterland_shore_walker_pair_activity",
        (CompositionMember("shore_walker", 2, 2),),
    ),
    EncounterComposition(
        "port_white_sail_hinterland_shore_walker_trio",
        "port_white_sail_hinterland_shore_walker_trio_activity",
        (CompositionMember("shore_walker", 3, 3),),
    ),
    EncounterComposition(
        "southwest_road_01_shore_walker",
        "southwest_road_01_shore_walker_activity",
        (CompositionMember("shore_walker", 1, 1),),
    ),
    EncounterComposition(
        "southwest_road_01_shore_walker_pair",
        "southwest_road_01_shore_walker_pair_activity",
        (CompositionMember("shore_walker", 2, 2),),
    ),
    EncounterComposition(
        "southwest_road_01_shore_walker_trio",
        "southwest_road_01_shore_walker_trio_activity",
        (CompositionMember("shore_walker", 3, 3),),
    ),
    EncounterComposition(
        "southwest_road_02_shore_walker",
        "southwest_road_02_shore_walker_activity",
        (CompositionMember("shore_walker", 1, 1),),
    ),
    EncounterComposition(
        "southwest_road_02_shore_walker_pair",
        "southwest_road_02_shore_walker_pair_activity",
        (CompositionMember("shore_walker", 2, 2),),
    ),
    EncounterComposition(
        "southwest_road_02_shore_walker_trio",
        "southwest_road_02_shore_walker_trio_activity",
        (CompositionMember("shore_walker", 3, 3),),
    ),
# Near-settlement belts (highland-road-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    EncounterComposition(
        "highland_road_01_wood_stalker",
        "highland_road_01_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_02_wood_stalker",
        "highland_road_02_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_03_wood_stalker",
        "highland_road_03_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_04_wood_stalker",
        "highland_road_04_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_05_wood_stalker",
        "highland_road_05_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_06_wood_stalker",
        "highland_road_06_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_07_wood_stalker",
        "highland_road_07_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_08_wood_stalker",
        "highland_road_08_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
# North deep forest (north-deep-forest-placement): hinterland, approach and deep-wild zone compositions.
    EncounterComposition(
        "village_eolas_hinterland_rotlog_sprout",
        "village_eolas_hinterland_rotlog_sprout_activity",
        (CompositionMember("rotlog_sprout", 2, 3),),
    ),
    EncounterComposition(
        "village_eolas_hinterland_quill_forager",
        "village_eolas_hinterland_quill_forager_activity",
        (CompositionMember("quill_forager", 1, 1),),
    ),
    EncounterComposition(
        "village_eolas_hinterland_hollow_roost_flier",
        "village_eolas_hinterland_hollow_roost_flier_activity",
        (CompositionMember("hollow_roost_flier", 2, 3),),
    ),
    EncounterComposition(
        "north_wood_forest_edge_rotlog_sprout",
        "north_wood_forest_edge_rotlog_sprout_activity",
        (CompositionMember("rotlog_sprout", 2, 3),),
    ),
    EncounterComposition(
        "north_wood_forest_edge_quill_forager",
        "north_wood_forest_edge_quill_forager_activity",
        (CompositionMember("quill_forager", 1, 1),),
    ),
    EncounterComposition(
        "north_wood_forest_edge_hollow_roost_flier",
        "north_wood_forest_edge_hollow_roost_flier_activity",
        (CompositionMember("hollow_roost_flier", 2, 3),),
    ),
    EncounterComposition(
        "tiger_roar_forest_edge_rotlog_sprout",
        "tiger_roar_forest_edge_rotlog_sprout_activity",
        (CompositionMember("rotlog_sprout", 2, 3),),
    ),
    EncounterComposition(
        "tiger_roar_forest_edge_quill_forager",
        "tiger_roar_forest_edge_quill_forager_activity",
        (CompositionMember("quill_forager", 1, 1),),
    ),
    EncounterComposition(
        "tiger_roar_forest_edge_hollow_roost_flier",
        "tiger_roar_forest_edge_hollow_roost_flier_activity",
        (CompositionMember("hollow_roost_flier", 2, 3),),
    ),
    EncounterComposition(
        "dragon_nest_lower_wild_hush_wing_hunter",
        "dragon_nest_lower_wild_hush_wing_hunter_activity",
        (CompositionMember("hush_wing_hunter", 1, 1),),
    ),
    EncounterComposition(
        "dragon_nest_lower_wild_vine_weaver",
        "dragon_nest_lower_wild_vine_weaver_activity",
        (CompositionMember("vine_weaver", 1, 1),),
    ),
    EncounterComposition(
        "dragon_nest_lower_wild_quill_forager",
        "dragon_nest_lower_wild_quill_forager_activity",
        (CompositionMember("quill_forager", 1, 1),),
    ),
    EncounterComposition(
        "dragon_nest_lower_wild_hollow_roost_flier",
        "dragon_nest_lower_wild_hollow_roost_flier_activity",
        (CompositionMember("hollow_roost_flier", 2, 3),),
    ),
    EncounterComposition(
        "dragon_nest_upper_wild_hush_wing_hunter",
        "dragon_nest_upper_wild_hush_wing_hunter_activity",
        (CompositionMember("hush_wing_hunter", 1, 1),),
    ),
    EncounterComposition(
        "dragon_nest_upper_wild_vine_weaver",
        "dragon_nest_upper_wild_vine_weaver_activity",
        (CompositionMember("vine_weaver", 1, 1),),
    ),
    EncounterComposition(
        "dragon_nest_upper_wild_quill_forager",
        "dragon_nest_upper_wild_quill_forager_activity",
        (CompositionMember("quill_forager", 1, 1),),
    ),
    EncounterComposition(
        "dragon_nest_upper_wild_hollow_roost_flier",
        "dragon_nest_upper_wild_hollow_roost_flier_activity",
        (CompositionMember("hollow_roost_flier", 2, 3),),
    ),
    EncounterComposition(
        "eternal_night_lower_wild_hush_wing_hunter",
        "eternal_night_lower_wild_hush_wing_hunter_activity",
        (CompositionMember("hush_wing_hunter", 1, 1),),
    ),
    EncounterComposition(
        "eternal_night_lower_wild_vine_weaver",
        "eternal_night_lower_wild_vine_weaver_activity",
        (CompositionMember("vine_weaver", 1, 1),),
    ),
    EncounterComposition(
        "eternal_night_lower_wild_quill_forager",
        "eternal_night_lower_wild_quill_forager_activity",
        (CompositionMember("quill_forager", 1, 1),),
    ),
    EncounterComposition(
        "eternal_night_lower_wild_hollow_roost_flier",
        "eternal_night_lower_wild_hollow_roost_flier_activity",
        (CompositionMember("hollow_roost_flier", 2, 3),),
    ),
    EncounterComposition(
        "eternal_night_upper_wild_hush_wing_hunter",
        "eternal_night_upper_wild_hush_wing_hunter_activity",
        (CompositionMember("hush_wing_hunter", 1, 1),),
    ),
    EncounterComposition(
        "eternal_night_upper_wild_vine_weaver",
        "eternal_night_upper_wild_vine_weaver_activity",
        (CompositionMember("vine_weaver", 1, 1),),
    ),
    EncounterComposition(
        "eternal_night_upper_wild_quill_forager",
        "eternal_night_upper_wild_quill_forager_activity",
        (CompositionMember("quill_forager", 1, 1),),
    ),
    EncounterComposition(
        "eternal_night_upper_wild_hollow_roost_flier",
        "eternal_night_upper_wild_hollow_roost_flier_activity",
        (CompositionMember("hollow_roost_flier", 2, 3),),
    ),
    EncounterComposition(
        "moonvale_outer_wild_hush_wing_hunter",
        "moonvale_outer_wild_hush_wing_hunter_activity",
        (CompositionMember("hush_wing_hunter", 1, 1),),
    ),
    EncounterComposition(
        "moonvale_outer_wild_vine_weaver",
        "moonvale_outer_wild_vine_weaver_activity",
        (CompositionMember("vine_weaver", 1, 1),),
    ),
    EncounterComposition(
        "moonvale_outer_wild_quill_forager",
        "moonvale_outer_wild_quill_forager_activity",
        (CompositionMember("quill_forager", 1, 1),),
    ),
    EncounterComposition(
        "moonvale_outer_wild_hollow_roost_flier",
        "moonvale_outer_wild_hollow_roost_flier_activity",
        (CompositionMember("hollow_roost_flier", 2, 3),),
    ),
# North deep forest (north-deep-forest-placement): site compositions.
    EncounterComposition(
        "fairy_ring_nest_group",
        "fairy_ring_nest_activity",
        (
            CompositionMember("ring_elder", 1, 1),
            CompositionMember("rotlog_sprout", 2, 2),
        ),
    ),
    EncounterComposition(
        "quill_den_nest_group",
        "quill_den_nest_activity",
        (
            CompositionMember("den_sentry", 1, 1),
            CompositionMember("quill_forager", 1, 1),
        ),
    ),
    EncounterComposition(
        "hollow_roost_camp_group",
        "hollow_roost_camp_activity",
        (
            CompositionMember("colony_sentinel", 1, 1),
            CompositionMember("hollow_roost_flier", 2, 2),
        ),
    ),
    EncounterComposition(
        "old_hollow_owl_nest_member",
        "old_hollow_owl_nest_activity",
        (CompositionMember("old_hollow_owl", 1, 1),),
    ),
    EncounterComposition(
        "trail_net_camp_member",
        "trail_net_camp_activity",
        (CompositionMember("trail_netter", 1, 1),),
    ),
    EncounterComposition(
        "moss_crown_boss",
        "moss_crown_boss_activity",
        (CompositionMember("wood_crown_elder", 1, 1),),
    ),
# Central mountains (central-mountains-placement): hinterland, approach and deep-wild zone compositions.
    EncounterComposition(
        "village_ciaran_hinterland_seep_sipper",
        "village_ciaran_hinterland_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "village_ciaran_hinterland_seep_sipper_single",
        "village_ciaran_hinterland_seep_sipper_single_activity",
        (CompositionMember("seep_sipper", 1, 1),),
    ),
    EncounterComposition(
        "village_ciaran_hinterland_ledge_basker",
        "village_ciaran_hinterland_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
    EncounterComposition(
        "village_fionnen_hinterland_seep_sipper",
        "village_fionnen_hinterland_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "village_fionnen_hinterland_seep_sipper_single",
        "village_fionnen_hinterland_seep_sipper_single_activity",
        (CompositionMember("seep_sipper", 1, 1),),
    ),
    EncounterComposition(
        "village_fionnen_hinterland_ledge_basker",
        "village_fionnen_hinterland_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
    EncounterComposition(
        "fox_fire_pass_approach_seep_sipper",
        "fox_fire_pass_approach_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "fox_fire_pass_approach_seep_sipper_single",
        "fox_fire_pass_approach_seep_sipper_single_activity",
        (CompositionMember("seep_sipper", 1, 1),),
    ),
    EncounterComposition(
        "fox_fire_pass_approach_ledge_basker",
        "fox_fire_pass_approach_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
    EncounterComposition(
        "maple_foot_pass_approach_seep_sipper",
        "maple_foot_pass_approach_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "maple_foot_pass_approach_seep_sipper_single",
        "maple_foot_pass_approach_seep_sipper_single_activity",
        (CompositionMember("seep_sipper", 1, 1),),
    ),
    EncounterComposition(
        "maple_foot_pass_approach_ledge_basker",
        "maple_foot_pass_approach_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
    EncounterComposition(
        "scarp_pass_approach_seep_sipper",
        "scarp_pass_approach_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "scarp_pass_approach_seep_sipper_single",
        "scarp_pass_approach_seep_sipper_single_activity",
        (CompositionMember("seep_sipper", 1, 1),),
    ),
    EncounterComposition(
        "scarp_pass_approach_ledge_basker",
        "scarp_pass_approach_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
    EncounterComposition(
        "silver_ridge_pass_approach_seep_sipper",
        "silver_ridge_pass_approach_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "silver_ridge_pass_approach_seep_sipper_single",
        "silver_ridge_pass_approach_seep_sipper_single_activity",
        (CompositionMember("seep_sipper", 1, 1),),
    ),
    EncounterComposition(
        "silver_ridge_pass_approach_ledge_basker",
        "silver_ridge_pass_approach_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
    EncounterComposition(
        "ciaran_ridge_wild_updraft_glider",
        "ciaran_ridge_wild_updraft_glider_activity",
        (CompositionMember("updraft_glider", 1, 1),),
    ),
    EncounterComposition(
        "ciaran_ridge_wild_lamp_seeker",
        "ciaran_ridge_wild_lamp_seeker_activity",
        (CompositionMember("lamp_seeker", 1, 1),),
    ),
    EncounterComposition(
        "ciaran_ridge_wild_seep_sipper",
        "ciaran_ridge_wild_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "ciaran_ridge_wild_ledge_basker",
        "ciaran_ridge_wild_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
    EncounterComposition(
        "fionnen_ridge_wild_updraft_glider",
        "fionnen_ridge_wild_updraft_glider_activity",
        (CompositionMember("updraft_glider", 1, 1),),
    ),
    EncounterComposition(
        "fionnen_ridge_wild_lamp_seeker",
        "fionnen_ridge_wild_lamp_seeker_activity",
        (CompositionMember("lamp_seeker", 1, 1),),
    ),
    EncounterComposition(
        "fionnen_ridge_wild_seep_sipper",
        "fionnen_ridge_wild_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "fionnen_ridge_wild_ledge_basker",
        "fionnen_ridge_wild_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
    EncounterComposition(
        "fox_fire_high_wild_updraft_glider",
        "fox_fire_high_wild_updraft_glider_activity",
        (CompositionMember("updraft_glider", 1, 1),),
    ),
    EncounterComposition(
        "fox_fire_high_wild_lamp_seeker",
        "fox_fire_high_wild_lamp_seeker_activity",
        (CompositionMember("lamp_seeker", 1, 1),),
    ),
    EncounterComposition(
        "fox_fire_high_wild_seep_sipper",
        "fox_fire_high_wild_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "fox_fire_high_wild_ledge_basker",
        "fox_fire_high_wild_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
    EncounterComposition(
        "north_spine_wild_updraft_glider",
        "north_spine_wild_updraft_glider_activity",
        (CompositionMember("updraft_glider", 1, 1),),
    ),
    EncounterComposition(
        "north_spine_wild_lamp_seeker",
        "north_spine_wild_lamp_seeker_activity",
        (CompositionMember("lamp_seeker", 1, 1),),
    ),
    EncounterComposition(
        "north_spine_wild_seep_sipper",
        "north_spine_wild_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "north_spine_wild_ledge_basker",
        "north_spine_wild_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
    EncounterComposition(
        "silver_ridge_high_wild_updraft_glider",
        "silver_ridge_high_wild_updraft_glider_activity",
        (CompositionMember("updraft_glider", 1, 1),),
    ),
    EncounterComposition(
        "silver_ridge_high_wild_lamp_seeker",
        "silver_ridge_high_wild_lamp_seeker_activity",
        (CompositionMember("lamp_seeker", 1, 1),),
    ),
    EncounterComposition(
        "silver_ridge_high_wild_seep_sipper",
        "silver_ridge_high_wild_seep_sipper_activity",
        (CompositionMember("seep_sipper", 2, 3),),
    ),
    EncounterComposition(
        "silver_ridge_high_wild_ledge_basker",
        "silver_ridge_high_wild_ledge_basker_activity",
        (CompositionMember("ledge_basker", 1, 1),),
    ),
# Central mountains (central-mountains-placement): site compositions.
    EncounterComposition(
        "spring_keeper_pool_group",
        "spring_keeper_pool_activity",
        (
            CompositionMember("spring_keeper", 1, 1),
            CompositionMember("seep_sipper", 2, 2),
        ),
    ),
    EncounterComposition(
        "vent_crack_den_member",
        "vent_crack_den_activity",
        (CompositionMember("vent_crack_dweller", 1, 1),),
    ),
    EncounterComposition(
        "crag_nest_ledge_member",
        "crag_nest_ledge_activity",
        (CompositionMember("crag_nest_vulture", 1, 1),),
    ),
    EncounterComposition(
        "old_veil_lamp_camp_member",
        "old_veil_lamp_camp_activity",
        (CompositionMember("old_veil_moth", 1, 1),),
    ),
    EncounterComposition(
        "rime_coil_boss",
        "rime_coil_boss_activity",
        (CompositionMember("white_rime_coil", 1, 1),),
    ),
# Northwest highland forest (northwest-highland-placement): hinterland and deep-wild zone compositions.
    EncounterComposition(
        "capital_valhalla_east_hinterland_pine_floor_grouse",
        "capital_valhalla_east_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "capital_valhalla_east_hinterland_dam_builder",
        "capital_valhalla_east_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "capital_valhalla_east_hinterland_vein_digger",
        "capital_valhalla_east_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "capital_valhalla_west_hinterland_pine_floor_grouse",
        "capital_valhalla_west_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "capital_valhalla_west_hinterland_dam_builder",
        "capital_valhalla_west_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "capital_valhalla_west_hinterland_vein_digger",
        "capital_valhalla_west_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_fox_fire_north_hinterland_pine_floor_grouse",
        "city_fox_fire_north_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_fox_fire_north_hinterland_dam_builder",
        "city_fox_fire_north_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_fox_fire_north_hinterland_vein_digger",
        "city_fox_fire_north_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_fox_fire_south_hinterland_pine_floor_grouse",
        "city_fox_fire_south_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_fox_fire_south_hinterland_dam_builder",
        "city_fox_fire_south_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_fox_fire_south_hinterland_vein_digger",
        "city_fox_fire_south_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_horn_plain_east_hinterland_pine_floor_grouse",
        "city_horn_plain_east_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_horn_plain_east_hinterland_dam_builder",
        "city_horn_plain_east_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_horn_plain_east_hinterland_vein_digger",
        "city_horn_plain_east_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_horn_plain_west_hinterland_pine_floor_grouse",
        "city_horn_plain_west_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_horn_plain_west_hinterland_dam_builder",
        "city_horn_plain_west_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_horn_plain_west_hinterland_vein_digger",
        "city_horn_plain_west_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_iron_claw_east_hinterland_pine_floor_grouse",
        "city_iron_claw_east_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_iron_claw_east_hinterland_dam_builder",
        "city_iron_claw_east_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_iron_claw_east_hinterland_vein_digger",
        "city_iron_claw_east_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_iron_claw_west_hinterland_pine_floor_grouse",
        "city_iron_claw_west_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_iron_claw_west_hinterland_dam_builder",
        "city_iron_claw_west_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_iron_claw_west_hinterland_vein_digger",
        "city_iron_claw_west_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_moon_howl_east_hinterland_pine_floor_grouse",
        "city_moon_howl_east_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_moon_howl_east_hinterland_dam_builder",
        "city_moon_howl_east_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_moon_howl_east_hinterland_vein_digger",
        "city_moon_howl_east_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_moon_howl_west_hinterland_pine_floor_grouse",
        "city_moon_howl_west_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_moon_howl_west_hinterland_dam_builder",
        "city_moon_howl_west_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_moon_howl_west_hinterland_vein_digger",
        "city_moon_howl_west_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_mutual_market_north_hinterland_pine_floor_grouse",
        "city_mutual_market_north_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_mutual_market_north_hinterland_dam_builder",
        "city_mutual_market_north_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_mutual_market_north_hinterland_vein_digger",
        "city_mutual_market_north_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_mutual_market_west_hinterland_pine_floor_grouse",
        "city_mutual_market_west_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_mutual_market_west_hinterland_dam_builder",
        "city_mutual_market_west_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_mutual_market_west_hinterland_vein_digger",
        "city_mutual_market_west_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_shadow_wood_east_hinterland_pine_floor_grouse",
        "city_shadow_wood_east_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_shadow_wood_east_hinterland_dam_builder",
        "city_shadow_wood_east_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_shadow_wood_east_hinterland_vein_digger",
        "city_shadow_wood_east_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_shadow_wood_north_hinterland_pine_floor_grouse",
        "city_shadow_wood_north_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_shadow_wood_north_hinterland_dam_builder",
        "city_shadow_wood_north_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_shadow_wood_north_hinterland_vein_digger",
        "city_shadow_wood_north_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_swift_wind_east_hinterland_pine_floor_grouse",
        "city_swift_wind_east_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_swift_wind_east_hinterland_dam_builder",
        "city_swift_wind_east_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_swift_wind_east_hinterland_vein_digger",
        "city_swift_wind_east_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_swift_wind_west_hinterland_pine_floor_grouse",
        "city_swift_wind_west_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_swift_wind_west_hinterland_dam_builder",
        "city_swift_wind_west_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_swift_wind_west_hinterland_vein_digger",
        "city_swift_wind_west_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_tiger_roar_east_hinterland_pine_floor_grouse",
        "city_tiger_roar_east_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_tiger_roar_east_hinterland_dam_builder",
        "city_tiger_roar_east_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_tiger_roar_east_hinterland_vein_digger",
        "city_tiger_roar_east_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "city_tiger_roar_west_hinterland_pine_floor_grouse",
        "city_tiger_roar_west_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "city_tiger_roar_west_hinterland_dam_builder",
        "city_tiger_roar_west_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "city_tiger_roar_west_hinterland_vein_digger",
        "city_tiger_roar_west_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "town_ancestor_shrine_hinterland_pine_floor_grouse",
        "town_ancestor_shrine_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "town_ancestor_shrine_hinterland_dam_builder",
        "town_ancestor_shrine_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "town_ancestor_shrine_hinterland_vein_digger",
        "town_ancestor_shrine_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "town_east_ford_camp_hinterland_pine_floor_grouse",
        "town_east_ford_camp_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "town_east_ford_camp_hinterland_dam_builder",
        "town_east_ford_camp_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "town_east_ford_camp_hinterland_vein_digger",
        "town_east_ford_camp_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "town_falcon_hinterland_pine_floor_grouse",
        "town_falcon_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "town_falcon_hinterland_dam_builder",
        "town_falcon_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "town_falcon_hinterland_vein_digger",
        "town_falcon_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "town_frost_wind_hinterland_pine_floor_grouse",
        "town_frost_wind_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "town_frost_wind_hinterland_dam_builder",
        "town_frost_wind_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "town_frost_wind_hinterland_vein_digger",
        "town_frost_wind_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "town_grizzly_hinterland_pine_floor_grouse",
        "town_grizzly_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "town_grizzly_hinterland_dam_builder",
        "town_grizzly_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "town_grizzly_hinterland_vein_digger",
        "town_grizzly_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "town_pine_ferry_hinterland_pine_floor_grouse",
        "town_pine_ferry_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "town_pine_ferry_hinterland_dam_builder",
        "town_pine_ferry_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "town_pine_ferry_hinterland_vein_digger",
        "town_pine_ferry_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "town_shaman_cave_hinterland_pine_floor_grouse",
        "town_shaman_cave_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "town_shaman_cave_hinterland_dam_builder",
        "town_shaman_cave_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "town_shaman_cave_hinterland_vein_digger",
        "town_shaman_cave_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "town_stag_ferry_hinterland_pine_floor_grouse",
        "town_stag_ferry_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "town_stag_ferry_hinterland_dam_builder",
        "town_stag_ferry_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "town_stag_ferry_hinterland_vein_digger",
        "town_stag_ferry_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "town_west_ford_camp_hinterland_pine_floor_grouse",
        "town_west_ford_camp_hinterland_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "town_west_ford_camp_hinterland_dam_builder",
        "town_west_ford_camp_hinterland_dam_builder_activity",
        (CompositionMember("dam_builder", 2, 3),),
    ),
    EncounterComposition(
        "town_west_ford_camp_hinterland_vein_digger",
        "town_west_ford_camp_hinterland_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "far_west_wild_trapline_raider",
        "far_west_wild_trapline_raider_activity",
        (CompositionMember("trapline_raider", 1, 1),),
    ),
    EncounterComposition(
        "far_west_wild_wood_stalker",
        "far_west_wild_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "far_west_wild_pine_floor_grouse",
        "far_west_wild_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "far_west_wild_vein_digger",
        "far_west_wild_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "howl_ridge_wild_trapline_raider",
        "howl_ridge_wild_trapline_raider_activity",
        (CompositionMember("trapline_raider", 1, 1),),
    ),
    EncounterComposition(
        "howl_ridge_wild_wood_stalker",
        "howl_ridge_wild_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "howl_ridge_wild_pine_floor_grouse",
        "howl_ridge_wild_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "howl_ridge_wild_vein_digger",
        "howl_ridge_wild_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "pine_ferry_west_wild_trapline_raider",
        "pine_ferry_west_wild_trapline_raider_activity",
        (CompositionMember("trapline_raider", 1, 1),),
    ),
    EncounterComposition(
        "pine_ferry_west_wild_wood_stalker",
        "pine_ferry_west_wild_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "pine_ferry_west_wild_pine_floor_grouse",
        "pine_ferry_west_wild_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "pine_ferry_west_wild_vein_digger",
        "pine_ferry_west_wild_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "valhalla_north_wild_trapline_raider",
        "valhalla_north_wild_trapline_raider_activity",
        (CompositionMember("trapline_raider", 1, 1),),
    ),
    EncounterComposition(
        "valhalla_north_wild_wood_stalker",
        "valhalla_north_wild_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "valhalla_north_wild_pine_floor_grouse",
        "valhalla_north_wild_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "valhalla_north_wild_vein_digger",
        "valhalla_north_wild_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "valhalla_west_wild_trapline_raider",
        "valhalla_west_wild_trapline_raider_activity",
        (CompositionMember("trapline_raider", 1, 1),),
    ),
    EncounterComposition(
        "valhalla_west_wild_wood_stalker",
        "valhalla_west_wild_wood_stalker_activity",
        (CompositionMember("wood_stalker", 1, 1),),
    ),
    EncounterComposition(
        "valhalla_west_wild_pine_floor_grouse",
        "valhalla_west_wild_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "valhalla_west_wild_vein_digger",
        "valhalla_west_wild_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
# Northwest highland forest (northwest-highland-placement): corridor low company.
    EncounterComposition(
        "highland_road_01_pine_floor_grouse",
        "highland_road_01_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "highland_road_01_vein_digger",
        "highland_road_01_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_02_pine_floor_grouse",
        "highland_road_02_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "highland_road_02_vein_digger",
        "highland_road_02_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_03_pine_floor_grouse",
        "highland_road_03_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "highland_road_03_vein_digger",
        "highland_road_03_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_04_pine_floor_grouse",
        "highland_road_04_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "highland_road_04_vein_digger",
        "highland_road_04_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_05_pine_floor_grouse",
        "highland_road_05_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "highland_road_05_vein_digger",
        "highland_road_05_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_06_pine_floor_grouse",
        "highland_road_06_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "highland_road_06_vein_digger",
        "highland_road_06_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_07_pine_floor_grouse",
        "highland_road_07_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "highland_road_07_vein_digger",
        "highland_road_07_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
    EncounterComposition(
        "highland_road_08_pine_floor_grouse",
        "highland_road_08_pine_floor_grouse_activity",
        (CompositionMember("pine_floor_grouse", 2, 3),),
    ),
    EncounterComposition(
        "highland_road_08_vein_digger",
        "highland_road_08_vein_digger_activity",
        (CompositionMember("vein_digger", 1, 1),),
    ),
# Northwest highland forest (northwest-highland-placement): site compositions.
    EncounterComposition(
        "lek_master_lek_group",
        "lek_master_lek_activity",
        (
            CompositionMember("lek_master_cock", 1, 1),
            CompositionMember("pine_floor_grouse", 2, 2),
        ),
    ),
    EncounterComposition(
        "old_dam_keeper_dam_group",
        "old_dam_keeper_dam_activity",
        (
            CompositionMember("old_dam_keeper", 1, 1),
            CompositionMember("dam_builder", 2, 2),
        ),
    ),
    EncounterComposition(
        "deep_seam_mole_den_member",
        "deep_seam_mole_den_activity",
        (CompositionMember("deep_seam_mole", 1, 1),),
    ),
    EncounterComposition(
        "winter_den_glutton_den_member",
        "winter_den_glutton_den_activity",
        (CompositionMember("winter_den_glutton", 1, 1),),
    ),
    EncounterComposition(
        "golden_plume_boss",
        "golden_plume_boss_activity",
        (CompositionMember("windcrest_elder", 1, 1),),
    ),
# Eastern plains (eastern-plains-deep-placement): deep-wild zone compositions.
    EncounterComposition(
        "black_soil_north_wild_plain_runner",
        "black_soil_north_wild_plain_runner_activity",
        (CompositionMember("plain_runner", 2, 3),),
    ),
    EncounterComposition(
        "black_soil_north_wild_sluice_wader",
        "black_soil_north_wild_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "black_soil_north_wild_road_ball_roller",
        "black_soil_north_wild_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "black_soil_north_wild_grain_pecker",
        "black_soil_north_wild_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "black_soil_north_wild_burrow_maker",
        "black_soil_north_wild_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "crystal_north_wild_plain_runner",
        "crystal_north_wild_plain_runner_activity",
        (CompositionMember("plain_runner", 2, 3),),
    ),
    EncounterComposition(
        "crystal_north_wild_sluice_wader",
        "crystal_north_wild_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "crystal_north_wild_road_ball_roller",
        "crystal_north_wild_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "crystal_north_wild_grain_pecker",
        "crystal_north_wild_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "crystal_north_wild_burrow_maker",
        "crystal_north_wild_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "east_pasture_east_wild_plain_runner",
        "east_pasture_east_wild_plain_runner_activity",
        (CompositionMember("plain_runner", 2, 3),),
    ),
    EncounterComposition(
        "east_pasture_east_wild_sluice_wader",
        "east_pasture_east_wild_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "east_pasture_east_wild_road_ball_roller",
        "east_pasture_east_wild_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "east_pasture_east_wild_grain_pecker",
        "east_pasture_east_wild_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "east_pasture_east_wild_burrow_maker",
        "east_pasture_east_wild_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "north_wood_west_wild_plain_runner",
        "north_wood_west_wild_plain_runner_activity",
        (CompositionMember("plain_runner", 2, 3),),
    ),
    EncounterComposition(
        "north_wood_west_wild_sluice_wader",
        "north_wood_west_wild_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "north_wood_west_wild_road_ball_roller",
        "north_wood_west_wild_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "north_wood_west_wild_grain_pecker",
        "north_wood_west_wild_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "north_wood_west_wild_burrow_maker",
        "north_wood_west_wild_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
    EncounterComposition(
        "starglow_east_wild_plain_runner",
        "starglow_east_wild_plain_runner_activity",
        (CompositionMember("plain_runner", 2, 3),),
    ),
    EncounterComposition(
        "starglow_east_wild_sluice_wader",
        "starglow_east_wild_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "starglow_east_wild_road_ball_roller",
        "starglow_east_wild_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "starglow_east_wild_grain_pecker",
        "starglow_east_wild_grain_pecker_activity",
        (CompositionMember("grain_pecker", 1, 2),),
    ),
    EncounterComposition(
        "starglow_east_wild_burrow_maker",
        "starglow_east_wild_burrow_maker_activity",
        (CompositionMember("burrow_maker", 1, 1),),
    ),
# Eastern plains (eastern-plains-deep-placement): compositions added to the landed hinterland and corridor zones.
    EncounterComposition(
        "capital_grandia_east_hinterland_road_ball_roller",
        "capital_grandia_east_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "capital_grandia_west_hinterland_road_ball_roller",
        "capital_grandia_west_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "city_imperial_ferry_east_hinterland_road_ball_roller",
        "city_imperial_ferry_east_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "city_imperial_ferry_west_hinterland_road_ball_roller",
        "city_imperial_ferry_west_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "city_spice_road_east_hinterland_road_ball_roller",
        "city_spice_road_east_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "city_spice_road_west_hinterland_road_ball_roller",
        "city_spice_road_west_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "city_starglow_east_hinterland_road_ball_roller",
        "city_starglow_east_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "city_starglow_west_hinterland_road_ball_roller",
        "city_starglow_west_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "city_twin_currents_east_hinterland_road_ball_roller",
        "city_twin_currents_east_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "city_twin_currents_west_hinterland_road_ball_roller",
        "city_twin_currents_west_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "city_wheatwave_east_hinterland_road_ball_roller",
        "city_wheatwave_east_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "city_wheatwave_west_hinterland_road_ball_roller",
        "city_wheatwave_west_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_01_road_ball_roller",
        "eastern_road_01_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_01_plain_runner",
        "eastern_road_01_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_01_sluice_wader",
        "eastern_road_01_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_02_road_ball_roller",
        "eastern_road_02_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_02_plain_runner",
        "eastern_road_02_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_02_sluice_wader",
        "eastern_road_02_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_03_road_ball_roller",
        "eastern_road_03_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_03_plain_runner",
        "eastern_road_03_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_03_sluice_wader",
        "eastern_road_03_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_04_road_ball_roller",
        "eastern_road_04_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_04_plain_runner",
        "eastern_road_04_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_04_sluice_wader",
        "eastern_road_04_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_05_road_ball_roller",
        "eastern_road_05_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_05_plain_runner",
        "eastern_road_05_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_05_sluice_wader",
        "eastern_road_05_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_06_road_ball_roller",
        "eastern_road_06_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_06_plain_runner",
        "eastern_road_06_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_06_sluice_wader",
        "eastern_road_06_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_07_road_ball_roller",
        "eastern_road_07_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_07_plain_runner",
        "eastern_road_07_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_07_sluice_wader",
        "eastern_road_07_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_08_road_ball_roller",
        "eastern_road_08_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_08_plain_runner",
        "eastern_road_08_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_08_sluice_wader",
        "eastern_road_08_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_09_road_ball_roller",
        "eastern_road_09_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_09_plain_runner",
        "eastern_road_09_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_09_sluice_wader",
        "eastern_road_09_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_10_road_ball_roller",
        "eastern_road_10_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_10_plain_runner",
        "eastern_road_10_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_10_sluice_wader",
        "eastern_road_10_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_11_road_ball_roller",
        "eastern_road_11_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_11_plain_runner",
        "eastern_road_11_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_11_sluice_wader",
        "eastern_road_11_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "eastern_road_12_road_ball_roller",
        "eastern_road_12_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "eastern_road_12_plain_runner",
        "eastern_road_12_plain_runner_activity",
        (CompositionMember("plain_runner", 1, 2),),
    ),
    EncounterComposition(
        "eastern_road_12_sluice_wader",
        "eastern_road_12_sluice_wader_activity",
        (CompositionMember("sluice_wader", 1, 1),),
    ),
    EncounterComposition(
        "port_dawnlight_hinterland_road_ball_roller",
        "port_dawnlight_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "port_tide_wind_hinterland_road_ball_roller",
        "port_tide_wind_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_black_soil_hinterland_road_ball_roller",
        "town_black_soil_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_crystal_hinterland_road_ball_roller",
        "town_crystal_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_east_pasture_hinterland_road_ball_roller",
        "town_east_pasture_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_emerald_lake_hinterland_road_ball_roller",
        "town_emerald_lake_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_maple_foot_hinterland_road_ball_roller",
        "town_maple_foot_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_north_wood_keep_hinterland_road_ball_roller",
        "town_north_wood_keep_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_orange_blossom_hinterland_road_ball_roller",
        "town_orange_blossom_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_silver_ridge_hinterland_road_ball_roller",
        "town_silver_ridge_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_steed_plain_hinterland_road_ball_roller",
        "town_steed_plain_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_sunken_bell_hinterland_road_ball_roller",
        "town_sunken_bell_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
    EncounterComposition(
        "town_sunrise_hinterland_road_ball_roller",
        "town_sunrise_hinterland_road_ball_roller_activity",
        (CompositionMember("road_ball_roller", 2, 2),),
    ),
# Eastern plains (eastern-plains-deep-placement): site compositions.
    EncounterComposition(
        "flock_leader_camp_group",
        "flock_leader_camp_activity",
        (
            CompositionMember("flock_leader", 1, 1),
            CompositionMember("grain_pecker", 2, 2),
        ),
    ),
    EncounterComposition(
        "nest_guard_nest_group",
        "nest_guard_nest_activity",
        (
            CompositionMember("nest_guard", 1, 1),
            CompositionMember("burrow_maker", 2, 2),
        ),
    ),
    EncounterComposition(
        "heap_brood_keeper_heap_group",
        "heap_brood_keeper_heap_activity",
        (
            CompositionMember("heap_brood_keeper", 1, 1),
            CompositionMember("road_ball_roller", 2, 2),
        ),
    ),
    EncounterComposition(
        "herd_stallion_camp_group",
        "herd_stallion_camp_activity",
        (
            CompositionMember("herd_stallion", 1, 1),
            CompositionMember("plain_runner", 2, 2),
        ),
    ),
    EncounterComposition(
        "heronry_elder_nest_group",
        "heronry_elder_nest_activity",
        (
            CompositionMember("heronry_elder", 1, 1),
            CompositionMember("sluice_wader", 1, 1),
        ),
    ),
    EncounterComposition(
        "white_reed_boss",
        "white_reed_boss_activity",
        (CompositionMember("wide_mound_elder", 1, 1),),
    ),
)

_ECOLOGY_ZONE_DECLARATIONS: tuple[EcologyZone, ...] = (
    EcologyZone(
        "eastern_field_habitat",
        "eastern_plains",
        ((1520, 1539, 520, 539),),
        (
            WeightedComposition("eastern_field_grain_pecker", 1),
            WeightedComposition("eastern_field_flock_leader", 1),
            WeightedComposition("eastern_field_burrow_maker", 1),
            WeightedComposition("eastern_field_nest_guard", 1),
            WeightedComposition("eastern_field_grain_and_burrow", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "highland_forest_habitat",
        "northwest_highland_forest",
        ((200, 219, 1320, 1339),),
        (
            WeightedComposition("highland_wood_stalker", 1),
            WeightedComposition("highland_trail_hunter", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "southwest_shore_habitat",
        "southwest_coast",
        ((280, 299, 480, 499),),
        (
            WeightedComposition("southwest_shore_walker", 1),
            WeightedComposition("southwest_reef_warden", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_rockland_habitat",
        "western_hills_valleys",
        ((200, 219, 760, 779),),
        (
            WeightedComposition("western_rockland_burrow_maker", 1),
            WeightedComposition("western_rockland_nest_guard", 1),
            WeightedComposition("western_rockland_cliff_stepper", 1),
            WeightedComposition("western_rockland_pass_warden", 1),
            WeightedComposition("western_rockland_burrow_and_cliff", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    # Sparse weak-species habitats. Each one keeps the shared density interval,
    # delayed recovery and home-owned ceiling of the zones above; only the
    # per-cell capacity and wave budget widen, to the largest group the pool's
    # single composition can place, so one complete birth always fits one cell
    # and one wave. No stronger variant joins any of these ordinary pools.
    EcologyZone(
        "eastern_mudbank_habitat",
        "eastern_plains",
        ((2060, 2079, 820, 839),),
        (WeightedComposition("eastern_mudbank_dweller", 1),),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_mudbank_habitat",
        "western_hills_valleys",
        ((300, 319, 840, 859),),
        (WeightedComposition("western_mudbank_dweller", 1),),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_quarry_habitat",
        "western_hills_valleys",
        ((620, 639, 560, 579),),
        (WeightedComposition("western_quarry_nest_forager", 1),),
        1,
        3,
        4,
        3600,
        600,
        4,
    ),
    EcologyZone(
        "eastern_cache_habitat",
        "eastern_plains",
        ((1580, 1599, 520, 539),),
        (WeightedComposition("eastern_cache_forager", 1),),
        1,
        3,
        5,
        3600,
        600,
        5,
    ),
    EcologyZone(
        "western_cache_habitat",
        "western_hills_valleys",
        ((820, 839, 720, 739),),
        (WeightedComposition("western_cache_forager", 1),),
        1,
        3,
        5,
        3600,
        600,
        5,
    ),
# Near-settlement belts (eastern-plains-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    EcologyZone(
        "capital_grandia_east_hinterland",
        "eastern_plains",
        ((1961, 1980, 1251, 1270),),
        (
            WeightedComposition("capital_grandia_east_hinterland_grain_pecker", 1),
            WeightedComposition("capital_grandia_east_hinterland_burrow_maker", 1),
            WeightedComposition("capital_grandia_east_hinterland_mudbank_dweller", 1),
            WeightedComposition("capital_grandia_east_hinterland_wax_cache_forager", 1),
            WeightedComposition("capital_grandia_east_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "capital_grandia_west_hinterland",
        "eastern_plains",
        ((1930, 1949, 1251, 1270),),
        (
            WeightedComposition("capital_grandia_west_hinterland_grain_pecker", 1),
            WeightedComposition("capital_grandia_west_hinterland_burrow_maker", 1),
            WeightedComposition("capital_grandia_west_hinterland_mudbank_dweller", 1),
            WeightedComposition("capital_grandia_west_hinterland_wax_cache_forager", 1),
            WeightedComposition("capital_grandia_west_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_imperial_ferry_east_hinterland",
        "eastern_plains",
        ((1992, 2011, 1115, 1134),),
        (
            WeightedComposition("city_imperial_ferry_east_hinterland_grain_pecker", 1),
            WeightedComposition("city_imperial_ferry_east_hinterland_burrow_maker", 1),
            WeightedComposition("city_imperial_ferry_east_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_imperial_ferry_east_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_imperial_ferry_east_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_imperial_ferry_west_hinterland",
        "eastern_plains",
        ((1964, 1983, 1115, 1134),),
        (
            WeightedComposition("city_imperial_ferry_west_hinterland_grain_pecker", 1),
            WeightedComposition("city_imperial_ferry_west_hinterland_burrow_maker", 1),
            WeightedComposition("city_imperial_ferry_west_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_imperial_ferry_west_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_imperial_ferry_west_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_spice_road_east_hinterland",
        "eastern_plains",
        ((1981, 2000, 506, 525),),
        (
            WeightedComposition("city_spice_road_east_hinterland_grain_pecker", 1),
            WeightedComposition("city_spice_road_east_hinterland_burrow_maker", 1),
            WeightedComposition("city_spice_road_east_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_spice_road_east_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_spice_road_east_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_spice_road_west_hinterland",
        "eastern_plains",
        ((1953, 1972, 506, 525),),
        (
            WeightedComposition("city_spice_road_west_hinterland_grain_pecker", 1),
            WeightedComposition("city_spice_road_west_hinterland_burrow_maker", 1),
            WeightedComposition("city_spice_road_west_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_spice_road_west_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_spice_road_west_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_starglow_east_hinterland",
        "eastern_plains",
        ((2036, 2055, 958, 977),),
        (
            WeightedComposition("city_starglow_east_hinterland_grain_pecker", 1),
            WeightedComposition("city_starglow_east_hinterland_burrow_maker", 1),
            WeightedComposition("city_starglow_east_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_starglow_east_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_starglow_east_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_starglow_west_hinterland",
        "eastern_plains",
        ((2008, 2027, 945, 964),),
        (
            WeightedComposition("city_starglow_west_hinterland_grain_pecker", 1),
            WeightedComposition("city_starglow_west_hinterland_burrow_maker", 1),
            WeightedComposition("city_starglow_west_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_starglow_west_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_starglow_west_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_twin_currents_east_hinterland",
        "eastern_plains",
        ((2072, 2091, 699, 718),),
        (
            WeightedComposition("city_twin_currents_east_hinterland_grain_pecker", 1),
            WeightedComposition("city_twin_currents_east_hinterland_burrow_maker", 1),
            WeightedComposition("city_twin_currents_east_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_twin_currents_east_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_twin_currents_east_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_twin_currents_west_hinterland",
        "eastern_plains",
        ((2044, 2063, 691, 710),),
        (
            WeightedComposition("city_twin_currents_west_hinterland_grain_pecker", 1),
            WeightedComposition("city_twin_currents_west_hinterland_burrow_maker", 1),
            WeightedComposition("city_twin_currents_west_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_twin_currents_west_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_twin_currents_west_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_wheatwave_east_hinterland",
        "eastern_plains",
        ((2087, 2106, 1512, 1531),),
        (
            WeightedComposition("city_wheatwave_east_hinterland_grain_pecker", 1),
            WeightedComposition("city_wheatwave_east_hinterland_burrow_maker", 1),
            WeightedComposition("city_wheatwave_east_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_wheatwave_east_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_wheatwave_east_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_wheatwave_west_hinterland",
        "eastern_plains",
        ((2059, 2078, 1512, 1531),),
        (
            WeightedComposition("city_wheatwave_west_hinterland_grain_pecker", 1),
            WeightedComposition("city_wheatwave_west_hinterland_burrow_maker", 1),
            WeightedComposition("city_wheatwave_west_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_wheatwave_west_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_wheatwave_west_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "port_dawnlight_hinterland",
        "eastern_plains",
        ((2452, 2471, 1507, 1526),),
        (
            WeightedComposition("port_dawnlight_hinterland_grain_pecker", 1),
            WeightedComposition("port_dawnlight_hinterland_burrow_maker", 1),
            WeightedComposition("port_dawnlight_hinterland_mudbank_dweller", 1),
            WeightedComposition("port_dawnlight_hinterland_wax_cache_forager", 1),
            WeightedComposition("port_dawnlight_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "port_tide_wind_hinterland",
        "eastern_plains",
        ((2559, 2578, 1144, 1163),),
        (
            WeightedComposition("port_tide_wind_hinterland_grain_pecker", 1),
            WeightedComposition("port_tide_wind_hinterland_burrow_maker", 1),
            WeightedComposition("port_tide_wind_hinterland_mudbank_dweller", 1),
            WeightedComposition("port_tide_wind_hinterland_wax_cache_forager", 1),
            WeightedComposition("port_tide_wind_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_black_soil_hinterland",
        "eastern_plains",
        ((1628, 1647, 1412, 1431),),
        (
            WeightedComposition("town_black_soil_hinterland_grain_pecker", 1),
            WeightedComposition("town_black_soil_hinterland_burrow_maker", 1),
            WeightedComposition("town_black_soil_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_black_soil_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_black_soil_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_crystal_hinterland",
        "eastern_plains",
        ((1876, 1895, 1617, 1636),),
        (
            WeightedComposition("town_crystal_hinterland_grain_pecker", 1),
            WeightedComposition("town_crystal_hinterland_burrow_maker", 1),
            WeightedComposition("town_crystal_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_crystal_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_crystal_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_east_pasture_hinterland",
        "eastern_plains",
        ((2305, 2324, 884, 903),),
        (
            WeightedComposition("town_east_pasture_hinterland_grain_pecker", 1),
            WeightedComposition("town_east_pasture_hinterland_burrow_maker", 1),
            WeightedComposition("town_east_pasture_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_east_pasture_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_east_pasture_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_emerald_lake_hinterland",
        "eastern_plains",
        ((1901, 1920, 890, 909),),
        (
            WeightedComposition("town_emerald_lake_hinterland_grain_pecker", 1),
            WeightedComposition("town_emerald_lake_hinterland_burrow_maker", 1),
            WeightedComposition("town_emerald_lake_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_emerald_lake_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_emerald_lake_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_maple_foot_hinterland",
        "eastern_plains",
        ((1649, 1668, 1235, 1254),),
        (
            WeightedComposition("town_maple_foot_hinterland_grain_pecker", 1),
            WeightedComposition("town_maple_foot_hinterland_burrow_maker", 1),
            WeightedComposition("town_maple_foot_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_maple_foot_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_maple_foot_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_north_wood_keep_hinterland",
        "eastern_plains",
        ((1820, 1839, 1869, 1888),),
        (
            WeightedComposition("town_north_wood_keep_hinterland_grain_pecker", 1),
            WeightedComposition("town_north_wood_keep_hinterland_burrow_maker", 1),
            WeightedComposition("town_north_wood_keep_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_north_wood_keep_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_north_wood_keep_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_orange_blossom_hinterland",
        "eastern_plains",
        ((1810, 1829, 502, 521),),
        (
            WeightedComposition("town_orange_blossom_hinterland_grain_pecker", 1),
            WeightedComposition("town_orange_blossom_hinterland_burrow_maker", 1),
            WeightedComposition("town_orange_blossom_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_orange_blossom_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_orange_blossom_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_silver_ridge_hinterland",
        "eastern_plains",
        ((1525, 1544, 745, 764),),
        (
            WeightedComposition("town_silver_ridge_hinterland_grain_pecker", 1),
            WeightedComposition("town_silver_ridge_hinterland_burrow_maker", 1),
            WeightedComposition("town_silver_ridge_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_silver_ridge_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_silver_ridge_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_steed_plain_hinterland",
        "eastern_plains",
        ((1692, 1711, 848, 867),),
        (
            WeightedComposition("town_steed_plain_hinterland_grain_pecker", 1),
            WeightedComposition("town_steed_plain_hinterland_burrow_maker", 1),
            WeightedComposition("town_steed_plain_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_steed_plain_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_steed_plain_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_sunken_bell_hinterland",
        "eastern_plains",
        ((2229, 2248, 1707, 1726),),
        (
            WeightedComposition("town_sunken_bell_hinterland_grain_pecker", 1),
            WeightedComposition("town_sunken_bell_hinterland_burrow_maker", 1),
            WeightedComposition("town_sunken_bell_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_sunken_bell_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_sunken_bell_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_sunrise_hinterland",
        "eastern_plains",
        ((2399, 2418, 1448, 1467),),
        (
            WeightedComposition("town_sunrise_hinterland_grain_pecker", 1),
            WeightedComposition("town_sunrise_hinterland_burrow_maker", 1),
            WeightedComposition("town_sunrise_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_sunrise_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_sunrise_hinterland_road_ball_roller", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_01",
        "eastern_plains",
        ((2333, 2352, 676, 695),),
        (
            WeightedComposition("eastern_road_01_grain_pecker", 1),
            WeightedComposition("eastern_road_01_burrow_maker", 1),
            WeightedComposition("eastern_road_01_mudbank_dweller", 1),
            WeightedComposition("eastern_road_01_wax_cache_forager", 1),
            WeightedComposition("eastern_road_01_road_ball_roller", 1),
            WeightedComposition("eastern_road_01_plain_runner", 1),
            WeightedComposition("eastern_road_01_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_02",
        "eastern_plains",
        ((1617, 1636, 1040, 1059),),
        (
            WeightedComposition("eastern_road_02_grain_pecker", 1),
            WeightedComposition("eastern_road_02_burrow_maker", 1),
            WeightedComposition("eastern_road_02_mudbank_dweller", 1),
            WeightedComposition("eastern_road_02_wax_cache_forager", 1),
            WeightedComposition("eastern_road_02_road_ball_roller", 1),
            WeightedComposition("eastern_road_02_plain_runner", 1),
            WeightedComposition("eastern_road_02_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_03",
        "eastern_plains",
        ((2206, 2225, 532, 551),),
        (
            WeightedComposition("eastern_road_03_grain_pecker", 1),
            WeightedComposition("eastern_road_03_burrow_maker", 1),
            WeightedComposition("eastern_road_03_mudbank_dweller", 1),
            WeightedComposition("eastern_road_03_wax_cache_forager", 1),
            WeightedComposition("eastern_road_03_road_ball_roller", 1),
            WeightedComposition("eastern_road_03_plain_runner", 1),
            WeightedComposition("eastern_road_03_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_04",
        "eastern_plains",
        ((2241, 2260, 1445, 1464),),
        (
            WeightedComposition("eastern_road_04_grain_pecker", 1),
            WeightedComposition("eastern_road_04_burrow_maker", 1),
            WeightedComposition("eastern_road_04_mudbank_dweller", 1),
            WeightedComposition("eastern_road_04_wax_cache_forager", 1),
            WeightedComposition("eastern_road_04_road_ball_roller", 1),
            WeightedComposition("eastern_road_04_plain_runner", 1),
            WeightedComposition("eastern_road_04_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_05",
        "eastern_plains",
        ((2481, 2500, 1308, 1327),),
        (
            WeightedComposition("eastern_road_05_grain_pecker", 1),
            WeightedComposition("eastern_road_05_burrow_maker", 1),
            WeightedComposition("eastern_road_05_mudbank_dweller", 1),
            WeightedComposition("eastern_road_05_wax_cache_forager", 1),
            WeightedComposition("eastern_road_05_road_ball_roller", 1),
            WeightedComposition("eastern_road_05_plain_runner", 1),
            WeightedComposition("eastern_road_05_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_06",
        "eastern_plains",
        ((1790, 1809, 1289, 1308),),
        (
            WeightedComposition("eastern_road_06_grain_pecker", 1),
            WeightedComposition("eastern_road_06_burrow_maker", 1),
            WeightedComposition("eastern_road_06_mudbank_dweller", 1),
            WeightedComposition("eastern_road_06_wax_cache_forager", 1),
            WeightedComposition("eastern_road_06_road_ball_roller", 1),
            WeightedComposition("eastern_road_06_plain_runner", 1),
            WeightedComposition("eastern_road_06_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_07",
        "eastern_plains",
        ((2419, 2438, 1035, 1054),),
        (
            WeightedComposition("eastern_road_07_grain_pecker", 1),
            WeightedComposition("eastern_road_07_burrow_maker", 1),
            WeightedComposition("eastern_road_07_mudbank_dweller", 1),
            WeightedComposition("eastern_road_07_wax_cache_forager", 1),
            WeightedComposition("eastern_road_07_road_ball_roller", 1),
            WeightedComposition("eastern_road_07_plain_runner", 1),
            WeightedComposition("eastern_road_07_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_08",
        "eastern_plains",
        ((2170, 2189, 987, 1006),),
        (
            WeightedComposition("eastern_road_08_grain_pecker", 1),
            WeightedComposition("eastern_road_08_burrow_maker", 1),
            WeightedComposition("eastern_road_08_mudbank_dweller", 1),
            WeightedComposition("eastern_road_08_wax_cache_forager", 1),
            WeightedComposition("eastern_road_08_road_ball_roller", 1),
            WeightedComposition("eastern_road_08_plain_runner", 1),
            WeightedComposition("eastern_road_08_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_09",
        "eastern_plains",
        ((2052, 2071, 1382, 1401),),
        (
            WeightedComposition("eastern_road_09_grain_pecker", 1),
            WeightedComposition("eastern_road_09_burrow_maker", 1),
            WeightedComposition("eastern_road_09_mudbank_dweller", 1),
            WeightedComposition("eastern_road_09_wax_cache_forager", 1),
            WeightedComposition("eastern_road_09_road_ball_roller", 1),
            WeightedComposition("eastern_road_09_plain_runner", 1),
            WeightedComposition("eastern_road_09_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_10",
        "eastern_plains",
        ((1655, 1674, 636, 655),),
        (
            WeightedComposition("eastern_road_10_grain_pecker", 1),
            WeightedComposition("eastern_road_10_burrow_maker", 1),
            WeightedComposition("eastern_road_10_mudbank_dweller", 1),
            WeightedComposition("eastern_road_10_wax_cache_forager", 1),
            WeightedComposition("eastern_road_10_road_ball_roller", 1),
            WeightedComposition("eastern_road_10_plain_runner", 1),
            WeightedComposition("eastern_road_10_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_11",
        "eastern_plains",
        ((1849, 1868, 1741, 1760),),
        (
            WeightedComposition("eastern_road_11_grain_pecker", 1),
            WeightedComposition("eastern_road_11_burrow_maker", 1),
            WeightedComposition("eastern_road_11_mudbank_dweller", 1),
            WeightedComposition("eastern_road_11_wax_cache_forager", 1),
            WeightedComposition("eastern_road_11_road_ball_roller", 1),
            WeightedComposition("eastern_road_11_plain_runner", 1),
            WeightedComposition("eastern_road_11_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eastern_road_12",
        "eastern_plains",
        ((1750, 1769, 1517, 1536),),
        (
            WeightedComposition("eastern_road_12_grain_pecker", 1),
            WeightedComposition("eastern_road_12_burrow_maker", 1),
            WeightedComposition("eastern_road_12_mudbank_dweller", 1),
            WeightedComposition("eastern_road_12_wax_cache_forager", 1),
            WeightedComposition("eastern_road_12_road_ball_roller", 1),
            WeightedComposition("eastern_road_12_plain_runner", 1),
            WeightedComposition("eastern_road_12_sluice_wader", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
# Near-settlement belts (western-hills-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    EcologyZone(
        "capital_altoria_east_hinterland",
        "western_hills_valleys",
        ((867, 886, 1042, 1061),),
        (
            WeightedComposition("capital_altoria_east_hinterland_burrow_maker", 1),
            WeightedComposition("capital_altoria_east_hinterland_mudbank_dweller", 1),
            WeightedComposition("capital_altoria_east_hinterland_wax_cache_forager", 1),
            WeightedComposition("capital_altoria_east_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "capital_altoria_west_hinterland",
        "western_hills_valleys",
        ((837, 856, 1040, 1059),),
        (
            WeightedComposition("capital_altoria_west_hinterland_burrow_maker", 1),
            WeightedComposition("capital_altoria_west_hinterland_mudbank_dweller", 1),
            WeightedComposition("capital_altoria_west_hinterland_wax_cache_forager", 1),
            WeightedComposition("capital_altoria_west_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_border_bridge_east_hinterland",
        "western_hills_valleys",
        ((823, 842, 1347, 1366),),
        (
            WeightedComposition("city_border_bridge_east_hinterland_burrow_maker", 1),
            WeightedComposition("city_border_bridge_east_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_border_bridge_east_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_border_bridge_east_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_border_bridge_west_hinterland",
        "western_hills_valleys",
        ((802, 821, 1341, 1360),),
        (
            WeightedComposition("city_border_bridge_west_hinterland_burrow_maker", 1),
            WeightedComposition("city_border_bridge_west_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_border_bridge_west_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_border_bridge_west_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_confluence_east_hinterland",
        "western_hills_valleys",
        ((611, 630, 797, 816),),
        (
            WeightedComposition("city_confluence_east_hinterland_burrow_maker", 1),
            WeightedComposition("city_confluence_east_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_confluence_east_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_confluence_east_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_confluence_west_hinterland",
        "western_hills_valleys",
        ((582, 601, 804, 823),),
        (
            WeightedComposition("city_confluence_west_hinterland_burrow_maker", 1),
            WeightedComposition("city_confluence_west_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_confluence_west_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_confluence_west_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_east_river_north_hinterland",
        "western_hills_valleys",
        ((1037, 1056, 1078, 1097),),
        (
            WeightedComposition("city_east_river_north_hinterland_burrow_maker", 1),
            WeightedComposition("city_east_river_north_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_east_river_north_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_east_river_north_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_east_river_south_hinterland",
        "western_hills_valleys",
        ((1037, 1056, 1050, 1069),),
        (
            WeightedComposition("city_east_river_south_hinterland_burrow_maker", 1),
            WeightedComposition("city_east_river_south_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_east_river_south_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_east_river_south_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_greyrock_east_hinterland",
        "western_hills_valleys",
        ((335, 354, 984, 1003),),
        (
            WeightedComposition("city_greyrock_east_hinterland_burrow_maker", 1),
            WeightedComposition("city_greyrock_east_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_greyrock_east_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_greyrock_east_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_greyrock_west_hinterland",
        "western_hills_valleys",
        ((307, 326, 984, 1003),),
        (
            WeightedComposition("city_greyrock_west_hinterland_burrow_maker", 1),
            WeightedComposition("city_greyrock_west_hinterland_mudbank_dweller", 1),
            WeightedComposition("city_greyrock_west_hinterland_wax_cache_forager", 1),
            WeightedComposition("city_greyrock_west_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "port_hills_mouth_hinterland",
        "western_hills_valleys",
        ((160, 179, 821, 840),),
        (
            WeightedComposition("port_hills_mouth_hinterland_burrow_maker", 1),
            WeightedComposition("port_hills_mouth_hinterland_mudbank_dweller", 1),
            WeightedComposition("port_hills_mouth_hinterland_wax_cache_forager", 1),
            WeightedComposition("port_hills_mouth_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "port_west_ore_hinterland",
        "western_hills_valleys",
        ((207, 226, 684, 703),),
        (
            WeightedComposition("port_west_ore_hinterland_burrow_maker", 1),
            WeightedComposition("port_west_ore_hinterland_mudbank_dweller", 1),
            WeightedComposition("port_west_ore_hinterland_wax_cache_forager", 1),
            WeightedComposition("port_west_ore_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "port_westwind_hinterland",
        "western_hills_valleys",
        ((137, 156, 993, 1012),),
        (
            WeightedComposition("port_westwind_hinterland_burrow_maker", 1),
            WeightedComposition("port_westwind_hinterland_mudbank_dweller", 1),
            WeightedComposition("port_westwind_hinterland_wax_cache_forager", 1),
            WeightedComposition("port_westwind_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_east_ferry_hinterland",
        "western_hills_valleys",
        ((1132, 1151, 1337, 1356),),
        (
            WeightedComposition("town_east_ferry_hinterland_burrow_maker", 1),
            WeightedComposition("town_east_ferry_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_east_ferry_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_east_ferry_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_honey_vale_hinterland",
        "western_hills_valleys",
        ((1024, 1043, 675, 694),),
        (
            WeightedComposition("town_honey_vale_hinterland_burrow_maker", 1),
            WeightedComposition("town_honey_vale_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_honey_vale_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_honey_vale_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_ruins_gate_hinterland",
        "western_hills_valleys",
        ((510, 529, 1119, 1138),),
        (
            WeightedComposition("town_ruins_gate_hinterland_burrow_maker", 1),
            WeightedComposition("town_ruins_gate_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_ruins_gate_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_ruins_gate_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_scarp_hinterland",
        "western_hills_valleys",
        ((1283, 1302, 693, 712),),
        (
            WeightedComposition("town_scarp_hinterland_burrow_maker", 1),
            WeightedComposition("town_scarp_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_scarp_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_scarp_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_vineyard_hinterland",
        "western_hills_valleys",
        ((1001, 1020, 1145, 1164),),
        (
            WeightedComposition("town_vineyard_hinterland_burrow_maker", 1),
            WeightedComposition("town_vineyard_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_vineyard_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_vineyard_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_west_ferry_hinterland",
        "western_hills_valleys",
        ((431, 450, 1320, 1339),),
        (
            WeightedComposition("town_west_ferry_hinterland_burrow_maker", 1),
            WeightedComposition("town_west_ferry_hinterland_mudbank_dweller", 1),
            WeightedComposition("town_west_ferry_hinterland_wax_cache_forager", 1),
            WeightedComposition("town_west_ferry_hinterland_hanging_nest_forager", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_road_01",
        "western_hills_valleys",
        ((1025, 1044, 506, 525),),
        (
            WeightedComposition("western_road_01_cliff_stepper", 1),
            WeightedComposition("western_road_01_burrow_maker", 1),
            WeightedComposition("western_road_01_hanging_nest_forager", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_road_02",
        "western_hills_valleys",
        ((1186, 1205, 858, 877),),
        (
            WeightedComposition("western_road_02_cliff_stepper", 1),
            WeightedComposition("western_road_02_burrow_maker", 1),
            WeightedComposition("western_road_02_hanging_nest_forager", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_road_03",
        "western_hills_valleys",
        ((464, 483, 541, 560),),
        (
            WeightedComposition("western_road_03_burrow_maker", 1),
            WeightedComposition("western_road_03_mudbank_dweller", 1),
            WeightedComposition("western_road_03_wax_cache_forager", 1),
            WeightedComposition("western_road_03_hanging_nest_forager", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_road_04",
        "western_hills_valleys",
        ((674, 693, 1065, 1084),),
        (
            WeightedComposition("western_road_04_cliff_stepper", 1),
            WeightedComposition("western_road_04_burrow_maker", 1),
            WeightedComposition("western_road_04_hanging_nest_forager", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_road_05",
        "western_hills_valleys",
        ((1151, 1170, 692, 711),),
        (
            WeightedComposition("western_road_05_cliff_stepper", 1),
            WeightedComposition("western_road_05_burrow_maker", 1),
            WeightedComposition("western_road_05_hanging_nest_forager", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_road_06",
        "western_hills_valleys",
        ((738, 757, 902, 921),),
        (
            WeightedComposition("western_road_06_cliff_stepper", 1),
            WeightedComposition("western_road_06_burrow_maker", 1),
            WeightedComposition("western_road_06_hanging_nest_forager", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_road_07",
        "western_hills_valleys",
        ((556, 575, 690, 709),),
        (
            WeightedComposition("western_road_07_cliff_stepper", 1),
            WeightedComposition("western_road_07_burrow_maker", 1),
            WeightedComposition("western_road_07_hanging_nest_forager", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_road_08",
        "western_hills_valleys",
        ((715, 734, 713, 732),),
        (
            WeightedComposition("western_road_08_cliff_stepper", 1),
            WeightedComposition("western_road_08_burrow_maker", 1),
            WeightedComposition("western_road_08_hanging_nest_forager", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_road_09",
        "western_hills_valleys",
        ((293, 312, 595, 614),),
        (
            WeightedComposition("western_road_09_cliff_stepper", 1),
            WeightedComposition("western_road_09_burrow_maker", 1),
            WeightedComposition("western_road_09_hanging_nest_forager", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "western_road_10",
        "western_hills_valleys",
        ((923, 942, 687, 706),),
        (
            WeightedComposition("western_road_10_cliff_stepper", 1),
            WeightedComposition("western_road_10_burrow_maker", 1),
            WeightedComposition("western_road_10_hanging_nest_forager", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
# Near-settlement belts (coastal-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    EcologyZone(
        "port_east_bay_hinterland",
        "southeast_coast",
        ((2385, 2404, 466, 485),),
        (
            WeightedComposition("port_east_bay_hinterland_shore_walker", 1),
            WeightedComposition("port_east_bay_hinterland_shore_walker_pair", 1),
            WeightedComposition("port_east_bay_hinterland_shore_walker_trio", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "port_golden_sheaf_hinterland",
        "southeast_coast",
        ((2061, 2080, 242, 261),),
        (
            WeightedComposition("port_golden_sheaf_hinterland_shore_walker", 1),
            WeightedComposition("port_golden_sheaf_hinterland_shore_walker_pair", 1),
            WeightedComposition("port_golden_sheaf_hinterland_shore_walker_trio", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "port_south_cape_hinterland",
        "southeast_coast",
        ((1704, 1723, 95, 114),),
        (
            WeightedComposition("port_south_cape_hinterland_shore_walker", 1),
            WeightedComposition("port_south_cape_hinterland_shore_walker_pair", 1),
            WeightedComposition("port_south_cape_hinterland_shore_walker_trio", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "southeast_road_01",
        "southeast_coast",
        ((2066, 2085, 348, 367),),
        (
            WeightedComposition("southeast_road_01_bank_lurker", 1),
            WeightedComposition("southeast_road_01_shore_walker", 1),
            WeightedComposition("southeast_road_01_shore_walker_pair", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "port_fishers_cove_hinterland",
        "southwest_coast",
        ((415, 434, 157, 176),),
        (
            WeightedComposition("port_fishers_cove_hinterland_shore_walker", 1),
            WeightedComposition("port_fishers_cove_hinterland_shore_walker_pair", 1),
            WeightedComposition("port_fishers_cove_hinterland_shore_walker_trio", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "port_south_tide_hinterland",
        "southwest_coast",
        ((604, 623, 96, 115),),
        (
            WeightedComposition("port_south_tide_hinterland_shore_walker", 1),
            WeightedComposition("port_south_tide_hinterland_shore_walker_pair", 1),
            WeightedComposition("port_south_tide_hinterland_shore_walker_trio", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "port_white_sail_hinterland",
        "southwest_coast",
        ((294, 313, 362, 381),),
        (
            WeightedComposition("port_white_sail_hinterland_shore_walker", 1),
            WeightedComposition("port_white_sail_hinterland_shore_walker_pair", 1),
            WeightedComposition("port_white_sail_hinterland_shore_walker_trio", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "southwest_road_01",
        "southwest_coast",
        ((349, 368, 268, 287),),
        (
            WeightedComposition("southwest_road_01_shore_walker", 1),
            WeightedComposition("southwest_road_01_shore_walker_pair", 1),
            WeightedComposition("southwest_road_01_shore_walker_trio", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "southwest_road_02",
        "southwest_coast",
        ((378, 397, 211, 230),),
        (
            WeightedComposition("southwest_road_02_shore_walker", 1),
            WeightedComposition("southwest_road_02_shore_walker_pair", 1),
            WeightedComposition("southwest_road_02_shore_walker_trio", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
# Near-settlement belts (highland-road-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    EcologyZone(
        "highland_road_01",
        "northwest_highland_forest",
        ((908, 927, 1827, 1846),),
        (
            WeightedComposition("highland_road_01_wood_stalker", 1),
            WeightedComposition("highland_road_01_pine_floor_grouse", 1),
            WeightedComposition("highland_road_01_vein_digger", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "highland_road_02",
        "northwest_highland_forest",
        ((540, 559, 1784, 1803),),
        (
            WeightedComposition("highland_road_02_wood_stalker", 1),
            WeightedComposition("highland_road_02_pine_floor_grouse", 1),
            WeightedComposition("highland_road_02_vein_digger", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "highland_road_03",
        "northwest_highland_forest",
        ((257, 276, 1631, 1650),),
        (
            WeightedComposition("highland_road_03_wood_stalker", 1),
            WeightedComposition("highland_road_03_pine_floor_grouse", 1),
            WeightedComposition("highland_road_03_vein_digger", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "highland_road_04",
        "northwest_highland_forest",
        ((487, 506, 1537, 1556),),
        (
            WeightedComposition("highland_road_04_wood_stalker", 1),
            WeightedComposition("highland_road_04_pine_floor_grouse", 1),
            WeightedComposition("highland_road_04_vein_digger", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "highland_road_05",
        "northwest_highland_forest",
        ((800, 819, 1548, 1567),),
        (
            WeightedComposition("highland_road_05_wood_stalker", 1),
            WeightedComposition("highland_road_05_pine_floor_grouse", 1),
            WeightedComposition("highland_road_05_vein_digger", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "highland_road_06",
        "northwest_highland_forest",
        ((977, 996, 1434, 1453),),
        (
            WeightedComposition("highland_road_06_wood_stalker", 1),
            WeightedComposition("highland_road_06_pine_floor_grouse", 1),
            WeightedComposition("highland_road_06_vein_digger", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "highland_road_07",
        "northwest_highland_forest",
        ((784, 803, 1769, 1788),),
        (
            WeightedComposition("highland_road_07_wood_stalker", 1),
            WeightedComposition("highland_road_07_pine_floor_grouse", 1),
            WeightedComposition("highland_road_07_vein_digger", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "highland_road_08",
        "northwest_highland_forest",
        ((620, 639, 1706, 1725),),
        (
            WeightedComposition("highland_road_08_wood_stalker", 1),
            WeightedComposition("highland_road_08_pine_floor_grouse", 1),
            WeightedComposition("highland_road_08_vein_digger", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
# North deep forest (north-deep-forest-placement): hinterland, approach and deep-wild zones.
    EcologyZone(
        "village_eolas_hinterland",
        "north_deep_forest",
        ((1414, 1433, 2134, 2153),),
        (
            WeightedComposition("village_eolas_hinterland_rotlog_sprout", 1),
            WeightedComposition("village_eolas_hinterland_quill_forager", 1),
            WeightedComposition("village_eolas_hinterland_hollow_roost_flier", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "north_wood_forest_edge",
        "north_deep_forest",
        ((1805, 1824, 1950, 1969),),
        (
            WeightedComposition("north_wood_forest_edge_rotlog_sprout", 1),
            WeightedComposition("north_wood_forest_edge_quill_forager", 1),
            WeightedComposition("north_wood_forest_edge_hollow_roost_flier", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "tiger_roar_forest_edge",
        "north_deep_forest",
        ((990, 1009, 1950, 1969),),
        (
            WeightedComposition("tiger_roar_forest_edge_rotlog_sprout", 1),
            WeightedComposition("tiger_roar_forest_edge_quill_forager", 1),
            WeightedComposition("tiger_roar_forest_edge_hollow_roost_flier", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "dragon_nest_lower_wild",
        "north_deep_forest",
        ((1830, 1859, 2010, 2039),),
        (
            WeightedComposition("dragon_nest_lower_wild_hush_wing_hunter", 1),
            WeightedComposition("dragon_nest_lower_wild_vine_weaver", 1),
            WeightedComposition("dragon_nest_lower_wild_quill_forager", 1),
            WeightedComposition("dragon_nest_lower_wild_hollow_roost_flier", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "dragon_nest_upper_wild",
        "north_deep_forest",
        ((1770, 1799, 2085, 2114),),
        (
            WeightedComposition("dragon_nest_upper_wild_hush_wing_hunter", 1),
            WeightedComposition("dragon_nest_upper_wild_vine_weaver", 1),
            WeightedComposition("dragon_nest_upper_wild_quill_forager", 1),
            WeightedComposition("dragon_nest_upper_wild_hollow_roost_flier", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eternal_night_lower_wild",
        "north_deep_forest",
        ((965, 994, 2020, 2049),),
        (
            WeightedComposition("eternal_night_lower_wild_hush_wing_hunter", 1),
            WeightedComposition("eternal_night_lower_wild_vine_weaver", 1),
            WeightedComposition("eternal_night_lower_wild_quill_forager", 1),
            WeightedComposition("eternal_night_lower_wild_hollow_roost_flier", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "eternal_night_upper_wild",
        "north_deep_forest",
        ((915, 944, 2200, 2229),),
        (
            WeightedComposition("eternal_night_upper_wild_hush_wing_hunter", 1),
            WeightedComposition("eternal_night_upper_wild_vine_weaver", 1),
            WeightedComposition("eternal_night_upper_wild_quill_forager", 1),
            WeightedComposition("eternal_night_upper_wild_hollow_roost_flier", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "moonvale_outer_wild",
        "north_deep_forest",
        ((1590, 1619, 2140, 2169),),
        (
            WeightedComposition("moonvale_outer_wild_hush_wing_hunter", 1),
            WeightedComposition("moonvale_outer_wild_vine_weaver", 1),
            WeightedComposition("moonvale_outer_wild_quill_forager", 1),
            WeightedComposition("moonvale_outer_wild_hollow_roost_flier", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
# Central mountains (central-mountains-placement): hinterland, approach and deep-wild zones.
    EcologyZone(
        "village_ciaran_hinterland",
        "central_mountains",
        ((1370, 1389, 538, 557),),
        (
            WeightedComposition("village_ciaran_hinterland_seep_sipper", 1),
            WeightedComposition("village_ciaran_hinterland_seep_sipper_single", 1),
            WeightedComposition("village_ciaran_hinterland_ledge_basker", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "village_fionnen_hinterland",
        "central_mountains",
        ((1469, 1488, 1221, 1240),),
        (
            WeightedComposition("village_fionnen_hinterland_seep_sipper", 1),
            WeightedComposition("village_fionnen_hinterland_seep_sipper_single", 1),
            WeightedComposition("village_fionnen_hinterland_ledge_basker", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "fox_fire_pass_approach",
        "central_mountains",
        ((1329, 1348, 1690, 1709),),
        (
            WeightedComposition("fox_fire_pass_approach_seep_sipper", 1),
            WeightedComposition("fox_fire_pass_approach_seep_sipper_single", 1),
            WeightedComposition("fox_fire_pass_approach_ledge_basker", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "maple_foot_pass_approach",
        "central_mountains",
        ((1502, 1521, 1246, 1265),),
        (
            WeightedComposition("maple_foot_pass_approach_seep_sipper", 1),
            WeightedComposition("maple_foot_pass_approach_seep_sipper_single", 1),
            WeightedComposition("maple_foot_pass_approach_ledge_basker", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "scarp_pass_approach",
        "central_mountains",
        ((1309, 1328, 672, 691),),
        (
            WeightedComposition("scarp_pass_approach_seep_sipper", 1),
            WeightedComposition("scarp_pass_approach_seep_sipper_single", 1),
            WeightedComposition("scarp_pass_approach_ledge_basker", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "silver_ridge_pass_approach",
        "central_mountains",
        ((1471, 1490, 751, 770),),
        (
            WeightedComposition("silver_ridge_pass_approach_seep_sipper", 1),
            WeightedComposition("silver_ridge_pass_approach_seep_sipper_single", 1),
            WeightedComposition("silver_ridge_pass_approach_ledge_basker", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "ciaran_ridge_wild",
        "central_mountains",
        ((1351, 1380, 235, 264),),
        (
            WeightedComposition("ciaran_ridge_wild_updraft_glider", 1),
            WeightedComposition("ciaran_ridge_wild_lamp_seeker", 1),
            WeightedComposition("ciaran_ridge_wild_seep_sipper", 1),
            WeightedComposition("ciaran_ridge_wild_ledge_basker", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "fionnen_ridge_wild",
        "central_mountains",
        ((1365, 1394, 1005, 1034),),
        (
            WeightedComposition("fionnen_ridge_wild_updraft_glider", 1),
            WeightedComposition("fionnen_ridge_wild_lamp_seeker", 1),
            WeightedComposition("fionnen_ridge_wild_seep_sipper", 1),
            WeightedComposition("fionnen_ridge_wild_ledge_basker", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "fox_fire_high_wild",
        "central_mountains",
        ((1360, 1389, 1545, 1574),),
        (
            WeightedComposition("fox_fire_high_wild_updraft_glider", 1),
            WeightedComposition("fox_fire_high_wild_lamp_seeker", 1),
            WeightedComposition("fox_fire_high_wild_seep_sipper", 1),
            WeightedComposition("fox_fire_high_wild_ledge_basker", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "north_spine_wild",
        "central_mountains",
        ((1361, 1390, 1805, 1834),),
        (
            WeightedComposition("north_spine_wild_updraft_glider", 1),
            WeightedComposition("north_spine_wild_lamp_seeker", 1),
            WeightedComposition("north_spine_wild_seep_sipper", 1),
            WeightedComposition("north_spine_wild_ledge_basker", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "silver_ridge_high_wild",
        "central_mountains",
        ((1362, 1391, 745, 774),),
        (
            WeightedComposition("silver_ridge_high_wild_updraft_glider", 1),
            WeightedComposition("silver_ridge_high_wild_lamp_seeker", 1),
            WeightedComposition("silver_ridge_high_wild_seep_sipper", 1),
            WeightedComposition("silver_ridge_high_wild_ledge_basker", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
# Northwest highland forest (northwest-highland-placement): hinterland and deep-wild zones.
    EcologyZone(
        "capital_valhalla_east_hinterland",
        "northwest_highland_forest",
        ((718, 737, 1680, 1699),),
        (
            WeightedComposition("capital_valhalla_east_hinterland_pine_floor_grouse", 1),
            WeightedComposition("capital_valhalla_east_hinterland_dam_builder", 1),
            WeightedComposition("capital_valhalla_east_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "capital_valhalla_west_hinterland",
        "northwest_highland_forest",
        ((688, 707, 1680, 1699),),
        (
            WeightedComposition("capital_valhalla_west_hinterland_pine_floor_grouse", 1),
            WeightedComposition("capital_valhalla_west_hinterland_dam_builder", 1),
            WeightedComposition("capital_valhalla_west_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_fox_fire_north_hinterland",
        "northwest_highland_forest",
        ((1283, 1302, 1705, 1724),),
        (
            WeightedComposition("city_fox_fire_north_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_fox_fire_north_hinterland_dam_builder", 1),
            WeightedComposition("city_fox_fire_north_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_fox_fire_south_hinterland",
        "northwest_highland_forest",
        ((1283, 1302, 1677, 1696),),
        (
            WeightedComposition("city_fox_fire_south_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_fox_fire_south_hinterland_dam_builder", 1),
            WeightedComposition("city_fox_fire_south_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_horn_plain_east_hinterland",
        "northwest_highland_forest",
        ((396, 415, 1645, 1664),),
        (
            WeightedComposition("city_horn_plain_east_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_horn_plain_east_hinterland_dam_builder", 1),
            WeightedComposition("city_horn_plain_east_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_horn_plain_west_hinterland",
        "northwest_highland_forest",
        ((368, 387, 1645, 1664),),
        (
            WeightedComposition("city_horn_plain_west_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_horn_plain_west_hinterland_dam_builder", 1),
            WeightedComposition("city_horn_plain_west_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_iron_claw_east_hinterland",
        "northwest_highland_forest",
        ((1180, 1199, 1589, 1608),),
        (
            WeightedComposition("city_iron_claw_east_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_iron_claw_east_hinterland_dam_builder", 1),
            WeightedComposition("city_iron_claw_east_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_iron_claw_west_hinterland",
        "northwest_highland_forest",
        ((1152, 1171, 1589, 1608),),
        (
            WeightedComposition("city_iron_claw_west_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_iron_claw_west_hinterland_dam_builder", 1),
            WeightedComposition("city_iron_claw_west_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_moon_howl_east_hinterland",
        "northwest_highland_forest",
        ((474, 493, 1834, 1853),),
        (
            WeightedComposition("city_moon_howl_east_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_moon_howl_east_hinterland_dam_builder", 1),
            WeightedComposition("city_moon_howl_east_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_moon_howl_west_hinterland",
        "northwest_highland_forest",
        ((446, 465, 1834, 1853),),
        (
            WeightedComposition("city_moon_howl_west_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_moon_howl_west_hinterland_dam_builder", 1),
            WeightedComposition("city_moon_howl_west_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_mutual_market_north_hinterland",
        "northwest_highland_forest",
        ((821, 840, 1374, 1393),),
        (
            WeightedComposition("city_mutual_market_north_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_mutual_market_north_hinterland_dam_builder", 1),
            WeightedComposition("city_mutual_market_north_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_mutual_market_west_hinterland",
        "northwest_highland_forest",
        ((800, 819, 1368, 1387),),
        (
            WeightedComposition("city_mutual_market_west_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_mutual_market_west_hinterland_dam_builder", 1),
            WeightedComposition("city_mutual_market_west_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_shadow_wood_east_hinterland",
        "northwest_highland_forest",
        ((191, 210, 1567, 1586),),
        (
            WeightedComposition("city_shadow_wood_east_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_shadow_wood_east_hinterland_dam_builder", 1),
            WeightedComposition("city_shadow_wood_east_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_shadow_wood_north_hinterland",
        "northwest_highland_forest",
        ((185, 204, 1588, 1607),),
        (
            WeightedComposition("city_shadow_wood_north_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_shadow_wood_north_hinterland_dam_builder", 1),
            WeightedComposition("city_shadow_wood_north_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_swift_wind_east_hinterland",
        "northwest_highland_forest",
        ((605, 624, 1424, 1443),),
        (
            WeightedComposition("city_swift_wind_east_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_swift_wind_east_hinterland_dam_builder", 1),
            WeightedComposition("city_swift_wind_east_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_swift_wind_west_hinterland",
        "northwest_highland_forest",
        ((577, 596, 1424, 1443),),
        (
            WeightedComposition("city_swift_wind_west_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_swift_wind_west_hinterland_dam_builder", 1),
            WeightedComposition("city_swift_wind_west_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_tiger_roar_east_hinterland",
        "northwest_highland_forest",
        ((1005, 1024, 1854, 1873),),
        (
            WeightedComposition("city_tiger_roar_east_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_tiger_roar_east_hinterland_dam_builder", 1),
            WeightedComposition("city_tiger_roar_east_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "city_tiger_roar_west_hinterland",
        "northwest_highland_forest",
        ((977, 996, 1854, 1873),),
        (
            WeightedComposition("city_tiger_roar_west_hinterland_pine_floor_grouse", 1),
            WeightedComposition("city_tiger_roar_west_hinterland_dam_builder", 1),
            WeightedComposition("city_tiger_roar_west_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_ancestor_shrine_hinterland",
        "northwest_highland_forest",
        ((734, 753, 1579, 1598),),
        (
            WeightedComposition("town_ancestor_shrine_hinterland_pine_floor_grouse", 1),
            WeightedComposition("town_ancestor_shrine_hinterland_dam_builder", 1),
            WeightedComposition("town_ancestor_shrine_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_east_ford_camp_hinterland",
        "northwest_highland_forest",
        ((1133, 1152, 1370, 1389),),
        (
            WeightedComposition("town_east_ford_camp_hinterland_pine_floor_grouse", 1),
            WeightedComposition("town_east_ford_camp_hinterland_dam_builder", 1),
            WeightedComposition("town_east_ford_camp_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_falcon_hinterland",
        "northwest_highland_forest",
        ((1098, 1117, 1439, 1458),),
        (
            WeightedComposition("town_falcon_hinterland_pine_floor_grouse", 1),
            WeightedComposition("town_falcon_hinterland_dam_builder", 1),
            WeightedComposition("town_falcon_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_frost_wind_hinterland",
        "northwest_highland_forest",
        ((217, 236, 1797, 1816),),
        (
            WeightedComposition("town_frost_wind_hinterland_pine_floor_grouse", 1),
            WeightedComposition("town_frost_wind_hinterland_dam_builder", 1),
            WeightedComposition("town_frost_wind_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_grizzly_hinterland",
        "northwest_highland_forest",
        ((901, 920, 1473, 1492),),
        (
            WeightedComposition("town_grizzly_hinterland_pine_floor_grouse", 1),
            WeightedComposition("town_grizzly_hinterland_dam_builder", 1),
            WeightedComposition("town_grizzly_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_pine_ferry_hinterland",
        "northwest_highland_forest",
        ((1065, 1084, 1712, 1731),),
        (
            WeightedComposition("town_pine_ferry_hinterland_pine_floor_grouse", 1),
            WeightedComposition("town_pine_ferry_hinterland_dam_builder", 1),
            WeightedComposition("town_pine_ferry_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_shaman_cave_hinterland",
        "northwest_highland_forest",
        ((1173, 1192, 1800, 1819),),
        (
            WeightedComposition("town_shaman_cave_hinterland_pine_floor_grouse", 1),
            WeightedComposition("town_shaman_cave_hinterland_dam_builder", 1),
            WeightedComposition("town_shaman_cave_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_stag_ferry_hinterland",
        "northwest_highland_forest",
        ((374, 393, 1752, 1771),),
        (
            WeightedComposition("town_stag_ferry_hinterland_pine_floor_grouse", 1),
            WeightedComposition("town_stag_ferry_hinterland_dam_builder", 1),
            WeightedComposition("town_stag_ferry_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "town_west_ford_camp_hinterland",
        "northwest_highland_forest",
        ((433, 452, 1352, 1371),),
        (
            WeightedComposition("town_west_ford_camp_hinterland_pine_floor_grouse", 1),
            WeightedComposition("town_west_ford_camp_hinterland_dam_builder", 1),
            WeightedComposition("town_west_ford_camp_hinterland_vein_digger", 1),
        ),
        2,
        4,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "far_west_wild",
        "northwest_highland_forest",
        ((150, 179, 1295, 1324),),
        (
            WeightedComposition("far_west_wild_trapline_raider", 1),
            WeightedComposition("far_west_wild_wood_stalker", 1),
            WeightedComposition("far_west_wild_pine_floor_grouse", 1),
            WeightedComposition("far_west_wild_vein_digger", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "howl_ridge_wild",
        "northwest_highland_forest",
        ((630, 659, 1895, 1924),),
        (
            WeightedComposition("howl_ridge_wild_trapline_raider", 1),
            WeightedComposition("howl_ridge_wild_wood_stalker", 1),
            WeightedComposition("howl_ridge_wild_pine_floor_grouse", 1),
            WeightedComposition("howl_ridge_wild_vein_digger", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "pine_ferry_west_wild",
        "northwest_highland_forest",
        ((885, 914, 1670, 1699),),
        (
            WeightedComposition("pine_ferry_west_wild_trapline_raider", 1),
            WeightedComposition("pine_ferry_west_wild_wood_stalker", 1),
            WeightedComposition("pine_ferry_west_wild_pine_floor_grouse", 1),
            WeightedComposition("pine_ferry_west_wild_vein_digger", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "valhalla_north_wild",
        "northwest_highland_forest",
        ((780, 809, 1880, 1909),),
        (
            WeightedComposition("valhalla_north_wild_trapline_raider", 1),
            WeightedComposition("valhalla_north_wild_wood_stalker", 1),
            WeightedComposition("valhalla_north_wild_pine_floor_grouse", 1),
            WeightedComposition("valhalla_north_wild_vein_digger", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "valhalla_west_wild",
        "northwest_highland_forest",
        ((540, 569, 1670, 1699),),
        (
            WeightedComposition("valhalla_west_wild_trapline_raider", 1),
            WeightedComposition("valhalla_west_wild_wood_stalker", 1),
            WeightedComposition("valhalla_west_wild_pine_floor_grouse", 1),
            WeightedComposition("valhalla_west_wild_vein_digger", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
# Eastern plains (eastern-plains-deep-placement): deep-wild zones.
    EcologyZone(
        "black_soil_north_wild",
        "eastern_plains",
        ((1660, 1689, 1605, 1634),),
        (
            WeightedComposition("black_soil_north_wild_plain_runner", 1),
            WeightedComposition("black_soil_north_wild_sluice_wader", 1),
            WeightedComposition("black_soil_north_wild_road_ball_roller", 1),
            WeightedComposition("black_soil_north_wild_grain_pecker", 1),
            WeightedComposition("black_soil_north_wild_burrow_maker", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "crystal_north_wild",
        "eastern_plains",
        ((2005, 2034, 1890, 1919),),
        (
            WeightedComposition("crystal_north_wild_plain_runner", 1),
            WeightedComposition("crystal_north_wild_sluice_wader", 1),
            WeightedComposition("crystal_north_wild_road_ball_roller", 1),
            WeightedComposition("crystal_north_wild_grain_pecker", 1),
            WeightedComposition("crystal_north_wild_burrow_maker", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "east_pasture_east_wild",
        "eastern_plains",
        ((2500, 2529, 900, 929),),
        (
            WeightedComposition("east_pasture_east_wild_plain_runner", 1),
            WeightedComposition("east_pasture_east_wild_sluice_wader", 1),
            WeightedComposition("east_pasture_east_wild_road_ball_roller", 1),
            WeightedComposition("east_pasture_east_wild_grain_pecker", 1),
            WeightedComposition("east_pasture_east_wild_burrow_maker", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "north_wood_west_wild",
        "eastern_plains",
        ((1540, 1569, 1875, 1904),),
        (
            WeightedComposition("north_wood_west_wild_plain_runner", 1),
            WeightedComposition("north_wood_west_wild_sluice_wader", 1),
            WeightedComposition("north_wood_west_wild_road_ball_roller", 1),
            WeightedComposition("north_wood_west_wild_grain_pecker", 1),
            WeightedComposition("north_wood_west_wild_burrow_maker", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
    EcologyZone(
        "starglow_east_wild",
        "eastern_plains",
        ((2290, 2319, 1170, 1199),),
        (
            WeightedComposition("starglow_east_wild_plain_runner", 1),
            WeightedComposition("starglow_east_wild_sluice_wader", 1),
            WeightedComposition("starglow_east_wild_road_ball_roller", 1),
            WeightedComposition("starglow_east_wild_grain_pecker", 1),
            WeightedComposition("starglow_east_wild_burrow_maker", 1),
        ),
        1,
        2,
        3,
        3600,
        600,
        3,
    ),
)

# No settlement needs a larger maintained surroundings yet, so the policy
# registry ships empty: every inhabited settlement already receives the generic
# minimum one-cell buffer from the geometry rule.
_SETTLEMENT_BIRTH_POLICY_DECLARATIONS: tuple[SettlementBirthPolicy, ...] = ()

_MONSTER_SITE_ROWS: dict[str, MonsterSite] = build_monster_site_registry(
    _SITE_DECLARATIONS
)
_ENCOUNTER_COMPOSITION_ROWS: dict[str, EncounterComposition] = (
    build_encounter_composition_registry(_ENCOUNTER_COMPOSITION_DECLARATIONS)
)
_ECOLOGY_ZONE_ROWS: dict[str, EcologyZone] = build_ecology_zone_registry(
    _ECOLOGY_ZONE_DECLARATIONS
)
_SETTLEMENT_BIRTH_POLICY_ROWS: dict[str, SettlementBirthPolicy] = (
    build_settlement_birth_policy_registry(_SETTLEMENT_BIRTH_POLICY_DECLARATIONS)
)

# Shipped content must be valid the moment the module loads (titles.py
# precedent): validation runs here, before either registry is published, so an
# authored typo cannot produce a partially valid registry.
validate_monster_placement_registry(
    _MONSTER_SITE_ROWS,
    compositions=_ENCOUNTER_COMPOSITION_ROWS,
)
validate_ecology_registries(
    _ECOLOGY_ZONE_ROWS, _ENCOUNTER_COMPOSITION_ROWS, _SETTLEMENT_BIRTH_POLICY_ROWS
)

# The published registries are read-only proxies: every consumer reads through
# `.get` / `values()` / `[key]` / `in`, and no subsystem may mutate lore data
# in place.
MONSTER_SITE_REGISTRY: MappingProxyType = MappingProxyType(_MONSTER_SITE_ROWS)
ENCOUNTER_COMPOSITION_REGISTRY: MappingProxyType = MappingProxyType(
    _ENCOUNTER_COMPOSITION_ROWS
)
ECOLOGY_ZONE_REGISTRY: MappingProxyType = MappingProxyType(_ECOLOGY_ZONE_ROWS)
SETTLEMENT_BIRTH_POLICY_REGISTRY: MappingProxyType = MappingProxyType(
    _SETTLEMENT_BIRTH_POLICY_ROWS
)
