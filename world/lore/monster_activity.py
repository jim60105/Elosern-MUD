"""Authored monster field-activity registries (monster-activity-authoring).

Explicit, immutable declarations of where an authored monster group may move
and under which aggression condition it admits an encounter. Activity is
separate from birth geometry and from the combat behaviour profile: nothing
here spawns, moves, schedules or mutates game state, and no species name or
prose is ever interpreted as executable policy.

The module owns three frozen row types, their keyed registries, construction
validation, and one pure geometry predicate. A placement composition or site
names exactly one activity key; the site's own declaration overrides the
composition binding only for that site's movement declaration. See
``world.lore.monster_placement`` for the bindings and
``docs/development/monster-field-behaviour.md`` for the authored review.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from .registry_refs import ref

#: The closed activity-policy vocabulary. ``stationary`` never departs,
#: ``solitary_roaming`` binds a composition whose every legal outcome is one
#: individual, and ``cohesive_group`` moves one complete group together.
MONSTER_ACTIVITY_POLICIES: tuple[str, ...] = (
    "stationary",
    "solitary_roaming",
    "cohesive_group",
)

#: The closed aggression-condition vocabulary. A hostile condition is never
#: inferred from a species name or ecology prose.
AGGRESSION_KINDS: tuple[str, ...] = ("passive", "contact", "defended_area")

#: The clock dayparts an authored condition may name. Read from the canonical
#: clock rulebook data file: importing ``world.rules.clock`` would load the
#: Evennia settlement stack, and this registry layer is pure.
CLOCK_RULEBOOK_PATH = (
    Path(__file__).resolve().parents[1] / "rules" / "rulebook" / "clock.yaml"
)


def _clock_dayparts() -> tuple[str, ...]:
    """The authored clock daypart keys, in their rulebook order."""
    document = yaml.safe_load(CLOCK_RULEBOOK_PATH.read_text(encoding="utf-8"))
    dayparts = document.get("dayparts") if isinstance(document, Mapping) else None
    if not isinstance(dayparts, Mapping) or not dayparts:
        raise ValueError(
            f"clock rulebook {CLOCK_RULEBOOK_PATH} declares no dayparts mapping"
        )
    names: list[str] = []
    for key in dayparts:
        if not isinstance(key, str) or not key:
            raise ValueError(
                f"clock rulebook daypart key must be a nonempty string, got {key!r}"
            )
        names.append(key)
    return tuple(names)


#: The canonical clock daypart vocabulary, in rulebook order.
CLOCK_DAYPARTS: tuple[str, ...] = _clock_dayparts()


class MonsterActivityRegistryError(ValueError):
    """An activity declaration or binding violates the authored-data contract."""


@dataclass(frozen=True, slots=True)
class ActivityArea:
    """One bounded activity extent.

    Exactly one geometry form is authored. The region-intersection form names
    a wilderness region and inclusive ``(x_min, x_max, y_min, y_max)`` cell
    rectangles; the home-distance form names a nonnegative Chebyshev radius
    around the group's current home cell (zero contains that cell only, and a
    room home contains that room only). Settlement birth buffers never
    participate in activity geometry.
    """

    key: str
    region_key: str | None = field(
        default=None,
        metadata=ref("wilderness_regions", inverse="activity_areas", nullable=True),
    )
    rectangles: tuple[tuple[int, int, int, int], ...] = ()
    home_radius: int | None = None


@dataclass(frozen=True, slots=True)
class AggressionCondition:
    """One authored aggression trigger; ``dayparts`` empty means all times."""

    kind: str
    area_key: str | None = field(
        default=None,
        metadata=ref("activity_areas", inverse="defended_by", nullable=True),
    )
    dayparts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MonsterActivity:
    """One complete activity declaration and its aggression condition."""

    key: str
    policy: str
    area_key: str = field(
        metadata=ref("activity_areas", inverse="activities")
    )
    decision_interval: int
    aggression: AggressionCondition


def _require_int(value: object, what: str, minimum: int) -> None:
    """Reject a non-integer (bools included) or out-of-range authored value."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise MonsterActivityRegistryError(
            f"{what} must be an integer literal, got {value!r}"
        )
    if value < minimum:
        raise MonsterActivityRegistryError(
            f"{what} must be at least {minimum}, got {value!r}"
        )


def _require_nonempty_str(value: object, what: str) -> None:
    if not isinstance(value, str) or not value:
        raise MonsterActivityRegistryError(f"{what} must be a nonempty string")


def _check_rectangles(
    rectangles: object, what: str, regions: frozenset[str] | None, region_key: str
) -> None:
    """Reject geometry that is not inclusive integer rectangles."""
    if not isinstance(rectangles, tuple) or not rectangles:
        raise MonsterActivityRegistryError(f"{what} declares no bounded geometry")
    for rectangle in rectangles:
        if not isinstance(rectangle, tuple) or len(rectangle) != 4:
            raise MonsterActivityRegistryError(
                f"{what} geometry must be (x_min, x_max, y_min, y_max) "
                f"rectangles, got {rectangle!r}"
            )
        if any(
            isinstance(bound, bool) or not isinstance(bound, int)
            for bound in rectangle
        ):
            raise MonsterActivityRegistryError(
                f"{what} geometry bounds must be integer cells, got {rectangle!r}"
            )
        x_min, x_max, y_min, y_max = rectangle
        if x_min > x_max or y_min > y_max:
            raise MonsterActivityRegistryError(
                f"{what} geometry {rectangle!r} has inverted inclusive bounds"
            )
    if regions is not None and region_key not in regions:
        raise MonsterActivityRegistryError(
            f"{what} names unknown wilderness region {region_key!r}"
        )


def _check_area(
    area: object, what: str, regions: frozenset[str] | None = None
) -> None:
    """Reject an area that does not author exactly one legal geometry form."""
    if not isinstance(area, ActivityArea):
        raise MonsterActivityRegistryError(
            f"{what} must be an ActivityArea, got {area!r}"
        )
    _require_nonempty_str(area.key, f"{what} key")
    has_region = area.region_key is not None
    has_radius = area.home_radius is not None
    if has_region == has_radius:
        raise MonsterActivityRegistryError(
            f"{what} must author exactly one geometry form: region-intersection "
            "or home-distance"
        )
    if has_region:
        _require_nonempty_str(area.region_key, f"{what} region key")
        if area.home_radius is not None:
            raise MonsterActivityRegistryError(
                f"{what} region geometry forbids a home radius"
            )
        _check_rectangles(area.rectangles, what, regions, area.region_key)
        return
    if area.rectangles:
        raise MonsterActivityRegistryError(
            f"{what} home-distance geometry forbids region rectangles"
        )
    _require_int(area.home_radius, f"{what} home radius", 0)


def _check_condition(
    condition: object,
    what: str,
    area_keys: Mapping[str, ActivityArea],
    dayparts: frozenset[str],
) -> None:
    """Reject an aggression condition with a closed-vocabulary defect."""
    if not isinstance(condition, AggressionCondition):
        raise MonsterActivityRegistryError(
            f"{what} must be an AggressionCondition, got {condition!r}"
        )
    if condition.kind not in AGGRESSION_KINDS:
        raise MonsterActivityRegistryError(
            f"{what} declares unknown aggression kind {condition.kind!r}"
        )
    area_key = condition.area_key
    if condition.kind == "defended_area":
        _require_nonempty_str(area_key, f"{what} defended-area key")
        if area_key not in area_keys:
            raise MonsterActivityRegistryError(
                f"{what} references unknown activity area {area_key!r}"
            )
    elif area_key is not None:
        raise MonsterActivityRegistryError(
            f"{what} kind {condition.kind!r} forbids a defended-area key"
        )
    if not isinstance(condition.dayparts, tuple):
        raise MonsterActivityRegistryError(
            f"{what} dayparts must be a tuple, got {condition.dayparts!r}"
        )
    seen: set[str] = set()
    for daypart in condition.dayparts:
        if not isinstance(daypart, str) or not daypart:
            raise MonsterActivityRegistryError(
                f"{what} daypart must be a nonempty string, got {daypart!r}"
            )
        if daypart in seen:
            raise MonsterActivityRegistryError(
                f"{what} repeats daypart {daypart!r}"
            )
        seen.add(daypart)
        if daypart not in dayparts:
            raise MonsterActivityRegistryError(
                f"{what} names unknown daypart {daypart!r}"
            )


def _check_activity(
    activity: object,
    what: str,
    area_keys: Mapping[str, ActivityArea],
    dayparts: frozenset[str],
) -> None:
    """Reject one activity with an unknown policy, area or timing defect."""
    if not isinstance(activity, MonsterActivity):
        raise MonsterActivityRegistryError(
            f"{what} must be a MonsterActivity, got {activity!r}"
        )
    _require_nonempty_str(activity.key, f"{what} key")
    if activity.policy not in MONSTER_ACTIVITY_POLICIES:
        raise MonsterActivityRegistryError(
            f"{what} declares unknown activity policy {activity.policy!r}"
        )
    _require_nonempty_str(activity.area_key, f"{what} area key")
    if activity.area_key not in area_keys:
        raise MonsterActivityRegistryError(
            f"{what} references unknown activity area {activity.area_key!r}"
        )
    _require_int(activity.decision_interval, f"{what} decision interval", 1)
    _check_condition(
        activity.aggression, f"{what} aggression", area_keys, dayparts
    )


def _build_keyed_registry(
    declarations: Iterable[Any],
    key_of,
    what: str,
) -> dict[str, Any]:
    """Merge declared rows into a keyed registry, rejecting duplicate keys."""
    registry: dict[str, Any] = {}
    for entry in declarations:
        key = key_of(entry)
        if key in registry:
            raise MonsterActivityRegistryError(
                f"{what} key {key!r} is declared more than once"
            )
        registry[key] = entry
    return registry


def build_activity_area_registry(
    declarations: Iterable[ActivityArea],
) -> dict[str, ActivityArea]:
    """Merge declared activity areas into the keyed registry."""
    return _build_keyed_registry(
        declarations, lambda entry: entry.key, "activity area"
    )


def build_monster_activity_registry(
    declarations: Iterable[MonsterActivity],
) -> dict[str, MonsterActivity]:
    """Merge declared activities into the keyed registry."""
    return _build_keyed_registry(
        declarations, lambda entry: entry.key, "monster activity"
    )


def validate_activity_registries(
    areas: Mapping[str, ActivityArea],
    activities: Mapping[str, MonsterActivity],
    *,
    region_face: Iterable[str] | None = None,
    daypart_face: Iterable[str] | None = None,
) -> None:
    """Raise unless every authored activity declaration is complete and legal.

    Pure and DB-free. The region and daypart vocabularies default to the
    candidate-independent authored values and are injectable so behavior tests
    can exercise invented keys. Candidate-world geometry is a separate check
    (:func:`activity_area_problems`) because it needs the candidate terrain.
    """
    regions = None if region_face is None else frozenset(region_face)
    dayparts = frozenset(CLOCK_DAYPARTS if daypart_face is None else daypart_face)

    for mapping_key, area in areas.items():
        what = f"activity area {mapping_key!r}"
        if mapping_key != area.key:
            raise MonsterActivityRegistryError(
                f"{what} declares key {area.key!r}; an area is keyed by its own key"
            )
        _check_area(area, what, regions)

    for mapping_key, activity in activities.items():
        what = f"monster activity {mapping_key!r}"
        if mapping_key != activity.key:
            raise MonsterActivityRegistryError(
                f"{what} declares key {activity.key!r}; an activity is keyed by "
                "its own key"
            )
        _check_activity(activity, what, areas, dayparts)


@dataclass(frozen=True, slots=True)
class MovementUnit:
    """One movement group a placement creates: its binding and member slots."""

    activity_key: str
    member_indices: tuple[int, ...]


def movement_units(
    row_counts: Sequence[tuple[str, int]],
    row_bindings: Sequence[str],
    *,
    activities: Mapping[str, MonsterActivity] | None = None,
) -> tuple[MovementUnit, ...]:
    """The movement groups one complete placement forms under its binding.

    ``row_counts`` is the sampled ``(variant_key, count)`` composition in
    member order and ``row_bindings`` is the activity key each row resolves,
    parallel to it. Member slots are the flattened construction order -- row
    zero's individuals first, then row one's -- and slot numbers start at zero,
    so a writer must construct its individuals in exactly this order.

    Every slot of a ``cohesive_group`` binding sharing one key joins the same
    unit; each ``solitary_roaming`` or ``stationary`` slot is a unit of its
    own. A binding that permits several members therefore disperses instead of
    rejecting the placement. Units come back ordered by their smallest member
    slot. A zero-count row contributes no slot but is still validated.
    """
    counts = tuple(row_counts)
    bindings = tuple(row_bindings)
    if len(counts) != len(bindings):
        raise MonsterActivityRegistryError(
            f"movement units need one binding per row, got {len(counts)} rows "
            f"and {len(bindings)} bindings"
        )
    registry = MONSTER_ACTIVITY_REGISTRY if activities is None else activities
    units: list[MovementUnit] = []
    cohesive_positions: dict[str, int] = {}
    slot = 0
    for (_variant_key, count), binding in zip(counts, bindings):
        if isinstance(count, bool) or not isinstance(count, int):
            raise MonsterActivityRegistryError(
                f"movement unit row count must be an integer literal, got {count!r}"
            )
        if count < 0:
            raise MonsterActivityRegistryError(
                f"movement unit row count must be at least 0, got {count!r}"
            )
        if not isinstance(binding, str) or not binding:
            raise MonsterActivityRegistryError(
                f"movement unit binding must be a nonempty string, got {binding!r}"
            )
        activity = registry.get(binding)
        if activity is None:
            raise MonsterActivityRegistryError(
                f"movement unit binding {binding!r} names no monster activity"
            )
        for _ in range(count):
            if activity.policy == "cohesive_group":
                position = cohesive_positions.get(binding)
                if position is None:
                    cohesive_positions[binding] = len(units)
                    units.append(MovementUnit(binding, (slot,)))
                else:
                    units[position] = MovementUnit(
                        binding, (*units[position].member_indices, slot)
                    )
            else:
                units.append(MovementUnit(binding, (slot,)))
            slot += 1
    return tuple(sorted(units, key=lambda unit: unit.member_indices[0]))


def _candidate_terrain(candidate_world: Any):
    """The candidate geography's terrain definition, or a clear rejection."""
    terrain = getattr(candidate_world, "terrain", None)
    regions = getattr(candidate_world, "regions", None)
    if terrain is None or not isinstance(regions, Mapping):
        raise MonsterActivityRegistryError(
            "activity geometry requires a candidate geography with terrain and "
            "regions"
        )
    return terrain, regions


def _wilderness_cell_is_legal(terrain: Any, x: int, y: int) -> bool:
    from elosern_map_core.terrain import is_land_cell, is_within_frame

    if not is_within_frame(terrain.frame_cells, (x, y)):
        return False
    return is_land_cell(terrain, (x, y))


def activity_area_problems(
    area: ActivityArea, candidate_world: Any
) -> list[str]:
    """Every candidate-world defect of one area, in deterministic order.

    Region-intersection geometry is checked against this candidate's own
    regions and frame, so a republished terrain cannot validate against stale
    previously published cells. Home-distance geometry has no candidate check
    here: its home is supplied by the bound composition or site at resolution
    time, and the site's own cell is validated by the placement publication.
    """
    what = f"activity area {area.key!r}"
    try:
        terrain, regions = _candidate_terrain(candidate_world)
    except MonsterActivityRegistryError as error:
        return [str(error)]
    if area.region_key is None:
        return []
    problems: list[str] = []
    if area.region_key not in regions:
        problems.append(
            f"{what} names unknown candidate region {area.region_key!r}"
        )
    from elosern_map_core.terrain import (
        is_land_cell,
        is_within_frame,
        region_for_coordinates,
    )

    frame = terrain.frame_cells
    legal = False
    for x_min, x_max, y_min, y_max in area.rectangles:
        for x, y in ((x_min, y_min), (x_max, y_max)):
            if not is_within_frame(frame, (x, y)):
                problems.append(
                    f"{what} geometry {(x_min, x_max, y_min, y_max)!r} lies "
                    "outside the candidate frame"
                )
                break
        else:
            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    if not is_land_cell(terrain, (x, y)):
                        continue
                    if region_for_coordinates(terrain, x, y) != area.region_key:
                        continue
                    legal = True
    if not legal and not problems:
        problems.append(
            f"{what} geometry intersects no legal cell of region "
            f"{area.region_key!r}"
        )
    return problems


def _home_locator(home: object) -> dict[str, object]:
    """Validate and copy the structural home locator supplied by the caller."""
    if not isinstance(home, Mapping):
        raise MonsterActivityRegistryError(
            f"activity home must be a locator mapping, got {home!r}"
        )
    kind = home.get("kind")
    if kind == "wilderness":
        if set(home) != {"kind", "map", "x", "y"}:
            raise MonsterActivityRegistryError(
                "wilderness home locator must be exactly "
                "{kind, map, x, y}"
            )
        name = home["map"]
        if not isinstance(name, str) or not name:
            raise MonsterActivityRegistryError(
                "wilderness home locator map must be a nonempty string"
            )
        for axis in ("x", "y"):
            value = home[axis]
            if isinstance(value, bool) or not isinstance(value, int):
                raise MonsterActivityRegistryError(
                    f"wilderness home locator {axis} must be an integer cell"
                )
        return {"kind": "wilderness", "map": name, "x": home["x"], "y": home["y"]}
    if kind == "room":
        if set(home) != {"kind", "id"}:
            raise MonsterActivityRegistryError(
                "room home locator must be exactly {kind, id}"
            )
        room_id = home["id"]
        if isinstance(room_id, bool) or not isinstance(room_id, int):
            raise MonsterActivityRegistryError(
                "room home locator id must be an integer"
            )
        return {"kind": "room", "id": room_id}
    raise MonsterActivityRegistryError(
        f"activity home locator kind must be 'wilderness' or 'room', got {kind!r}"
    )


def _locator_sort_key(locator: Mapping[str, object]) -> str:
    return json.dumps(locator, sort_keys=True, separators=(",", ":"))


def resolve_activity_area(
    area: ActivityArea,
    *,
    home: Mapping[str, object],
    candidate_world: Any,
) -> tuple[Mapping[str, object], ...]:
    """Resolve one area's legal cells for ``home`` against the candidate world.

    Pure: it reads only its arguments (and the map-core terrain helpers), never
    the database, never the published runtime, and it creates no room. The
    result is deduplicated and sorted by canonical serialized locator, because
    locator mappings are unhashable. Settlement footprint buffers are not part
    of activity geometry and are never consulted.
    """
    locator = _home_locator(home)
    if area.region_key is not None:
        if locator["kind"] != "wilderness":
            raise MonsterActivityRegistryError(
                "region-intersection activity geometry requires a wilderness home"
            )
        terrain, regions = _candidate_terrain(candidate_world)
        if area.region_key not in regions:
            raise MonsterActivityRegistryError(
                f"activity area {area.key!r} names unknown region "
                f"{area.region_key!r} for this candidate"
            )
        from elosern_map_core.terrain import (
            is_land_cell,
            is_within_frame,
            region_for_coordinates,
        )

        name = locator["map"]
        found: dict[str, Mapping[str, object]] = {}
        for x_min, x_max, y_min, y_max in area.rectangles:
            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    if not is_within_frame(terrain.frame_cells, (x, y)):
                        continue
                    if not is_land_cell(terrain, (x, y)):
                        continue
                    if region_for_coordinates(terrain, x, y) != area.region_key:
                        continue
                    cell_locator = {
                        "kind": "wilderness",
                        "map": name,
                        "x": x,
                        "y": y,
                    }
                    found[_locator_sort_key(cell_locator)] = cell_locator
        return tuple(found[key] for key in sorted(found))

    if locator["kind"] == "room":
        if area.home_radius != 0:
            raise MonsterActivityRegistryError(
                f"activity area {area.key!r} cannot use a room home with a "
                f"nonzero radius ({area.home_radius!r})"
            )
        return (locator,)

    terrain, _regions = _candidate_terrain(candidate_world)
    from elosern_map_core.terrain import is_land_cell, is_within_frame

    name = locator["map"]
    centre_x, centre_y = locator["x"], locator["y"]
    radius = area.home_radius
    found = {}
    for x in range(centre_x - radius, centre_x + radius + 1):
        for y in range(centre_y - radius, centre_y + radius + 1):
            if not is_within_frame(terrain.frame_cells, (x, y)):
                continue
            if not is_land_cell(terrain, (x, y)):
                continue
            cell_locator = {"kind": "wilderness", "map": name, "x": x, "y": y}
            found[_locator_sort_key(cell_locator)] = cell_locator
    return tuple(found[key] for key in sorted(found))


# ---------------------------------------------------------------------------
# Authored content.
#
# Each ecology zone has one region-intersection extent matching its authored
# birth rectangle. The three manual sites keep a region extent for their
# complete composition and a zero-radius home extent for their own stationary
# override. Intervals are game ticks; aggression is explicit, never inferred.
# ---------------------------------------------------------------------------

_ACTIVITY_AREA_DECLARATIONS: tuple[ActivityArea, ...] = (
    ActivityArea(
        "eastern_field_grounds",
        "eastern_plains",
        ((1520, 1539, 520, 539),),
    ),
    ActivityArea(
        "highland_forest_grounds",
        "northwest_highland_forest",
        ((200, 219, 1320, 1339),),
    ),
    ActivityArea(
        "southwest_shore_grounds",
        "southwest_coast",
        ((280, 299, 480, 499),),
    ),
    ActivityArea(
        "western_rockland_grounds",
        "western_hills_valleys",
        ((200, 219, 760, 779),),
    ),
    ActivityArea(
        "ridge_burrow_grounds",
        "western_hills_valleys",
        ((690, 710, 990, 1010),),
    ),
    ActivityArea(
        "cliff_echo_grounds",
        "western_hills_valleys",
        ((750, 770, 1140, 1160),),
    ),
    ActivityArea(
        "tide_mouth_grounds",
        "southeast_coast",
        ((2090, 2110, 290, 310),),
    ),
    ActivityArea("ridge_burrow_nest_home", home_radius=0),
    ActivityArea("cliff_echo_camp_home", home_radius=0),
    ActivityArea("tide_mouth_boss_home", home_radius=0),
    # The three weak species of the content expansion keep one ground per
    # authored habitat. A ground repeats its zone's birth rectangle because the
    # zone model is the single geometry authority; the goblin nest and both rat
    # caches add a small defended sub-area inside their own ground, so ordinary
    # foraging ranges over the whole patch while only the defended area admits
    # an unprompted hostile response.
    ActivityArea(
        "eastern_mudbank_grounds",
        "eastern_plains",
        ((2060, 2079, 820, 839),),
    ),
    ActivityArea(
        "western_mudbank_grounds",
        "western_hills_valleys",
        ((300, 319, 840, 859),),
    ),
    ActivityArea(
        "western_quarry_grounds",
        "western_hills_valleys",
        ((620, 639, 560, 579),),
    ),
    ActivityArea(
        "eastern_cache_grounds",
        "eastern_plains",
        ((1580, 1599, 520, 539),),
    ),
    ActivityArea(
        "western_cache_grounds",
        "western_hills_valleys",
        ((820, 839, 720, 739),),
    ),
    ActivityArea(
        "western_quarry_nest",
        "western_hills_valleys",
        ((627, 632, 567, 572),),
    ),
    ActivityArea(
        "eastern_cache_store",
        "eastern_plains",
        ((1587, 1592, 527, 532),),
    ),
    ActivityArea(
        "western_cache_store",
        "western_hills_valleys",
        ((827, 832, 727, 732),),
    ),
    # The abandoned transfer station's three extents: the whole disused
    # facility, the goblins' defended nest, and the rat's defended cache. The
    # two sub-areas sit strictly inside the grounds, so ordinary foraging
    # covers the facility while only a defended sub-area admits an unprompted
    # hostile response.
    ActivityArea(
        "transfer_station_grounds",
        "western_hills_valleys",
        ((1285, 1295, 985, 995),),
    ),
    ActivityArea(
        "transfer_station_nest",
        "western_hills_valleys",
        ((1286, 1290, 986, 990),),
    ),
    ActivityArea(
        "transfer_station_cache",
        "western_hills_valleys",
        ((1291, 1295, 991, 995),),
    ),
    # The two high-tier boss territories. Each boss roams one bounded remote
    # patch and defends a smaller extent inside it: the crocodile's tidal
    # backwater bay and the boar's dry woodland den. The defended extent sits
    # strictly inside its grounds, so ordinary roaming stays retreat-oriented
    # while an approach into the defended extent admits an unprompted hostile
    # response.
    ActivityArea(
        "reservoir_backwater_grounds",
        "southeast_coast",
        ((2066, 2086, 371, 391),),
    ),
    ActivityArea(
        "reservoir_backwater_bay",
        "southeast_coast",
        ((2071, 2081, 376, 386),),
    ),
    ActivityArea(
        "ember_bristle_grounds",
        "western_hills_valleys",
        ((700, 719, 520, 539),),
    ),
    ActivityArea(
        "ember_bristle_den",
        "western_hills_valleys",
        ((705, 714, 525, 534),),
    ),
# Near-settlement belts (eastern-plains-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    ActivityArea(
        "capital_grandia_east_hinterland_grounds",
        "eastern_plains",
        ((1961, 1980, 1251, 1270),),
    ),
    ActivityArea(
        "capital_grandia_west_hinterland_grounds",
        "eastern_plains",
        ((1930, 1949, 1251, 1270),),
    ),
    ActivityArea(
        "city_imperial_ferry_east_hinterland_grounds",
        "eastern_plains",
        ((1992, 2011, 1115, 1134),),
    ),
    ActivityArea(
        "city_imperial_ferry_west_hinterland_grounds",
        "eastern_plains",
        ((1964, 1983, 1115, 1134),),
    ),
    ActivityArea(
        "city_spice_road_east_hinterland_grounds",
        "eastern_plains",
        ((1981, 2000, 506, 525),),
    ),
    ActivityArea(
        "city_spice_road_west_hinterland_grounds",
        "eastern_plains",
        ((1953, 1972, 506, 525),),
    ),
    ActivityArea(
        "city_starglow_east_hinterland_grounds",
        "eastern_plains",
        ((2036, 2055, 958, 977),),
    ),
    ActivityArea(
        "city_starglow_west_hinterland_grounds",
        "eastern_plains",
        ((2008, 2027, 945, 964),),
    ),
    ActivityArea(
        "city_twin_currents_east_hinterland_grounds",
        "eastern_plains",
        ((2072, 2091, 699, 718),),
    ),
    ActivityArea(
        "city_twin_currents_west_hinterland_grounds",
        "eastern_plains",
        ((2044, 2063, 691, 710),),
    ),
    ActivityArea(
        "city_wheatwave_east_hinterland_grounds",
        "eastern_plains",
        ((2087, 2106, 1512, 1531),),
    ),
    ActivityArea(
        "city_wheatwave_west_hinterland_grounds",
        "eastern_plains",
        ((2059, 2078, 1512, 1531),),
    ),
    ActivityArea(
        "port_dawnlight_hinterland_grounds",
        "eastern_plains",
        ((2452, 2471, 1507, 1526),),
    ),
    ActivityArea(
        "port_tide_wind_hinterland_grounds",
        "eastern_plains",
        ((2559, 2578, 1144, 1163),),
    ),
    ActivityArea(
        "town_black_soil_hinterland_grounds",
        "eastern_plains",
        ((1628, 1647, 1412, 1431),),
    ),
    ActivityArea(
        "town_crystal_hinterland_grounds",
        "eastern_plains",
        ((1876, 1895, 1617, 1636),),
    ),
    ActivityArea(
        "town_east_pasture_hinterland_grounds",
        "eastern_plains",
        ((2305, 2324, 884, 903),),
    ),
    ActivityArea(
        "town_emerald_lake_hinterland_grounds",
        "eastern_plains",
        ((1901, 1920, 890, 909),),
    ),
    ActivityArea(
        "town_maple_foot_hinterland_grounds",
        "eastern_plains",
        ((1649, 1668, 1235, 1254),),
    ),
    ActivityArea(
        "town_north_wood_keep_hinterland_grounds",
        "eastern_plains",
        ((1820, 1839, 1869, 1888),),
    ),
    ActivityArea(
        "town_orange_blossom_hinterland_grounds",
        "eastern_plains",
        ((1810, 1829, 502, 521),),
    ),
    ActivityArea(
        "town_silver_ridge_hinterland_grounds",
        "eastern_plains",
        ((1525, 1544, 745, 764),),
    ),
    ActivityArea(
        "town_steed_plain_hinterland_grounds",
        "eastern_plains",
        ((1692, 1711, 848, 867),),
    ),
    ActivityArea(
        "town_sunken_bell_hinterland_grounds",
        "eastern_plains",
        ((2229, 2248, 1707, 1726),),
    ),
    ActivityArea(
        "town_sunrise_hinterland_grounds",
        "eastern_plains",
        ((2399, 2418, 1448, 1467),),
    ),
    ActivityArea(
        "eastern_road_01_grounds",
        "eastern_plains",
        ((2333, 2352, 676, 695),),
    ),
    ActivityArea(
        "eastern_road_02_grounds",
        "eastern_plains",
        ((1617, 1636, 1040, 1059),),
    ),
    ActivityArea(
        "eastern_road_03_grounds",
        "eastern_plains",
        ((2206, 2225, 532, 551),),
    ),
    ActivityArea(
        "eastern_road_04_grounds",
        "eastern_plains",
        ((2241, 2260, 1445, 1464),),
    ),
    ActivityArea(
        "eastern_road_05_grounds",
        "eastern_plains",
        ((2481, 2500, 1308, 1327),),
    ),
    ActivityArea(
        "eastern_road_06_grounds",
        "eastern_plains",
        ((1790, 1809, 1289, 1308),),
    ),
    ActivityArea(
        "eastern_road_07_grounds",
        "eastern_plains",
        ((2419, 2438, 1035, 1054),),
    ),
    ActivityArea(
        "eastern_road_08_grounds",
        "eastern_plains",
        ((2170, 2189, 987, 1006),),
    ),
    ActivityArea(
        "eastern_road_09_grounds",
        "eastern_plains",
        ((2052, 2071, 1382, 1401),),
    ),
    ActivityArea(
        "eastern_road_10_grounds",
        "eastern_plains",
        ((1655, 1674, 636, 655),),
    ),
    ActivityArea(
        "eastern_road_11_grounds",
        "eastern_plains",
        ((1849, 1868, 1741, 1760),),
    ),
    ActivityArea(
        "eastern_road_12_grounds",
        "eastern_plains",
        ((1750, 1769, 1517, 1536),),
    ),
# Near-settlement belts (western-hills-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    ActivityArea(
        "capital_altoria_east_hinterland_grounds",
        "western_hills_valleys",
        ((867, 886, 1042, 1061),),
    ),
    ActivityArea(
        "capital_altoria_west_hinterland_grounds",
        "western_hills_valleys",
        ((837, 856, 1040, 1059),),
    ),
    ActivityArea(
        "city_border_bridge_east_hinterland_grounds",
        "western_hills_valleys",
        ((823, 842, 1347, 1366),),
    ),
    ActivityArea(
        "city_border_bridge_west_hinterland_grounds",
        "western_hills_valleys",
        ((802, 821, 1341, 1360),),
    ),
    ActivityArea(
        "city_confluence_east_hinterland_grounds",
        "western_hills_valleys",
        ((611, 630, 797, 816),),
    ),
    ActivityArea(
        "city_confluence_west_hinterland_grounds",
        "western_hills_valleys",
        ((582, 601, 804, 823),),
    ),
    ActivityArea(
        "city_east_river_north_hinterland_grounds",
        "western_hills_valleys",
        ((1037, 1056, 1078, 1097),),
    ),
    ActivityArea(
        "city_east_river_south_hinterland_grounds",
        "western_hills_valleys",
        ((1037, 1056, 1050, 1069),),
    ),
    ActivityArea(
        "city_greyrock_east_hinterland_grounds",
        "western_hills_valleys",
        ((335, 354, 984, 1003),),
    ),
    ActivityArea(
        "city_greyrock_west_hinterland_grounds",
        "western_hills_valleys",
        ((307, 326, 984, 1003),),
    ),
    ActivityArea(
        "port_hills_mouth_hinterland_grounds",
        "western_hills_valleys",
        ((160, 179, 821, 840),),
    ),
    ActivityArea(
        "port_west_ore_hinterland_grounds",
        "western_hills_valleys",
        ((207, 226, 684, 703),),
    ),
    ActivityArea(
        "port_westwind_hinterland_grounds",
        "western_hills_valleys",
        ((137, 156, 993, 1012),),
    ),
    ActivityArea(
        "town_east_ferry_hinterland_grounds",
        "western_hills_valleys",
        ((1132, 1151, 1337, 1356),),
    ),
    ActivityArea(
        "town_honey_vale_hinterland_grounds",
        "western_hills_valleys",
        ((1024, 1043, 675, 694),),
    ),
    ActivityArea(
        "town_ruins_gate_hinterland_grounds",
        "western_hills_valleys",
        ((510, 529, 1119, 1138),),
    ),
    ActivityArea(
        "town_scarp_hinterland_grounds",
        "western_hills_valleys",
        ((1283, 1302, 693, 712),),
    ),
    ActivityArea(
        "town_vineyard_hinterland_grounds",
        "western_hills_valleys",
        ((1001, 1020, 1145, 1164),),
    ),
    ActivityArea(
        "town_west_ferry_hinterland_grounds",
        "western_hills_valleys",
        ((431, 450, 1320, 1339),),
    ),
    ActivityArea(
        "western_road_01_grounds",
        "western_hills_valleys",
        ((1025, 1044, 506, 525),),
    ),
    ActivityArea(
        "western_road_02_grounds",
        "western_hills_valleys",
        ((1186, 1205, 858, 877),),
    ),
    ActivityArea(
        "western_road_03_grounds",
        "western_hills_valleys",
        ((464, 483, 541, 560),),
    ),
    ActivityArea(
        "western_road_04_grounds",
        "western_hills_valleys",
        ((674, 693, 1065, 1084),),
    ),
    ActivityArea(
        "western_road_05_grounds",
        "western_hills_valleys",
        ((1151, 1170, 692, 711),),
    ),
    ActivityArea(
        "western_road_06_grounds",
        "western_hills_valleys",
        ((738, 757, 902, 921),),
    ),
    ActivityArea(
        "western_road_07_grounds",
        "western_hills_valleys",
        ((556, 575, 690, 709),),
    ),
    ActivityArea(
        "western_road_08_grounds",
        "western_hills_valleys",
        ((715, 734, 713, 732),),
    ),
    ActivityArea(
        "western_road_09_grounds",
        "western_hills_valleys",
        ((293, 312, 595, 614),),
    ),
    ActivityArea(
        "western_road_10_grounds",
        "western_hills_valleys",
        ((923, 942, 687, 706),),
    ),
# Near-settlement belts (coastal-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    ActivityArea(
        "port_east_bay_hinterland_grounds",
        "southeast_coast",
        ((2385, 2404, 466, 485),),
    ),
    ActivityArea(
        "port_golden_sheaf_hinterland_grounds",
        "southeast_coast",
        ((2061, 2080, 242, 261),),
    ),
    ActivityArea(
        "port_south_cape_hinterland_grounds",
        "southeast_coast",
        ((1704, 1723, 95, 114),),
    ),
    ActivityArea(
        "southeast_road_01_grounds",
        "southeast_coast",
        ((2066, 2085, 348, 367),),
    ),
    ActivityArea(
        "port_fishers_cove_hinterland_grounds",
        "southwest_coast",
        ((415, 434, 157, 176),),
    ),
    ActivityArea(
        "port_south_tide_hinterland_grounds",
        "southwest_coast",
        ((604, 623, 96, 115),),
    ),
    ActivityArea(
        "port_white_sail_hinterland_grounds",
        "southwest_coast",
        ((294, 313, 362, 381),),
    ),
    ActivityArea(
        "southwest_road_01_grounds",
        "southwest_coast",
        ((349, 368, 268, 287),),
    ),
    ActivityArea(
        "southwest_road_02_grounds",
        "southwest_coast",
        ((378, 397, 211, 230),),
    ),
# Near-settlement belts (highland-road-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    ActivityArea(
        "highland_road_01_grounds",
        "northwest_highland_forest",
        ((908, 927, 1827, 1846),),
    ),
    ActivityArea(
        "highland_road_02_grounds",
        "northwest_highland_forest",
        ((540, 559, 1784, 1803),),
    ),
    ActivityArea(
        "highland_road_03_grounds",
        "northwest_highland_forest",
        ((257, 276, 1631, 1650),),
    ),
    ActivityArea(
        "highland_road_04_grounds",
        "northwest_highland_forest",
        ((487, 506, 1537, 1556),),
    ),
    ActivityArea(
        "highland_road_05_grounds",
        "northwest_highland_forest",
        ((800, 819, 1548, 1567),),
    ),
    ActivityArea(
        "highland_road_06_grounds",
        "northwest_highland_forest",
        ((977, 996, 1434, 1453),),
    ),
    ActivityArea(
        "highland_road_07_grounds",
        "northwest_highland_forest",
        ((784, 803, 1769, 1788),),
    ),
    ActivityArea(
        "highland_road_08_grounds",
        "northwest_highland_forest",
        ((620, 639, 1706, 1725),),
    ),
# North deep forest (north-deep-forest-placement): hinterland, approach and deep-wild zone grounds.
    ActivityArea(
        "village_eolas_hinterland_grounds",
        "north_deep_forest",
        ((1414, 1433, 2134, 2153),),
    ),
    ActivityArea(
        "north_wood_forest_edge_grounds",
        "north_deep_forest",
        ((1805, 1824, 1950, 1969),),
    ),
    ActivityArea(
        "tiger_roar_forest_edge_grounds",
        "north_deep_forest",
        ((990, 1009, 1950, 1969),),
    ),
    ActivityArea(
        "dragon_nest_lower_wild_grounds",
        "north_deep_forest",
        ((1830, 1859, 2010, 2039),),
    ),
    ActivityArea(
        "dragon_nest_upper_wild_grounds",
        "north_deep_forest",
        ((1770, 1799, 2085, 2114),),
    ),
    ActivityArea(
        "eternal_night_lower_wild_grounds",
        "north_deep_forest",
        ((965, 994, 2020, 2049),),
    ),
    ActivityArea(
        "eternal_night_upper_wild_grounds",
        "north_deep_forest",
        ((915, 944, 2200, 2229),),
    ),
    ActivityArea(
        "moonvale_outer_wild_grounds",
        "north_deep_forest",
        ((1590, 1619, 2140, 2169),),
    ),
# North deep forest (north-deep-forest-placement): site grounds and defended extents.
    ActivityArea(
        "fairy_ring_nest_grounds",
        "north_deep_forest",
        ((1690, 1710, 1990, 2010),),
    ),
    ActivityArea(
        "fairy_ring_nest_ring",
        "north_deep_forest",
        ((1695, 1705, 1995, 2005),),
    ),
    ActivityArea(
        "quill_den_nest_grounds",
        "north_deep_forest",
        ((1070, 1090, 1980, 2000),),
    ),
    ActivityArea(
        "quill_den_nest_den",
        "north_deep_forest",
        ((1075, 1085, 1985, 1995),),
    ),
    ActivityArea(
        "hollow_roost_camp_grounds",
        "north_deep_forest",
        ((870, 890, 2290, 2310),),
    ),
    ActivityArea(
        "hollow_roost_camp_roost",
        "north_deep_forest",
        ((875, 885, 2295, 2305),),
    ),
    ActivityArea(
        "old_hollow_owl_nest_grounds",
        "north_deep_forest",
        ((1240, 1260, 2090, 2110),),
    ),
    ActivityArea(
        "old_hollow_owl_nest_hollow",
        "north_deep_forest",
        ((1245, 1255, 2095, 2105),),
    ),
    ActivityArea(
        "trail_net_camp_grounds",
        "north_deep_forest",
        ((1830, 1850, 2110, 2130),),
    ),
    ActivityArea(
        "trail_net_camp_web",
        "north_deep_forest",
        ((1835, 1845, 2115, 2125),),
    ),
    ActivityArea(
        "moss_crown_boss_grounds",
        "north_deep_forest",
        ((1290, 1310, 2390, 2410),),
    ),
    ActivityArea(
        "moss_crown_boss_glade",
        "north_deep_forest",
        ((1295, 1305, 2395, 2405),),
    ),
# Central mountains (central-mountains-placement): hinterland, approach and deep-wild zone grounds.
    ActivityArea(
        "village_ciaran_hinterland_grounds",
        "central_mountains",
        ((1370, 1389, 538, 557),),
    ),
    ActivityArea(
        "village_fionnen_hinterland_grounds",
        "central_mountains",
        ((1469, 1488, 1221, 1240),),
    ),
    ActivityArea(
        "fox_fire_pass_approach_grounds",
        "central_mountains",
        ((1329, 1348, 1690, 1709),),
    ),
    ActivityArea(
        "maple_foot_pass_approach_grounds",
        "central_mountains",
        ((1502, 1521, 1246, 1265),),
    ),
    ActivityArea(
        "scarp_pass_approach_grounds",
        "central_mountains",
        ((1309, 1328, 672, 691),),
    ),
    ActivityArea(
        "silver_ridge_pass_approach_grounds",
        "central_mountains",
        ((1471, 1490, 751, 770),),
    ),
    ActivityArea(
        "ciaran_ridge_wild_grounds",
        "central_mountains",
        ((1351, 1380, 235, 264),),
    ),
    ActivityArea(
        "fionnen_ridge_wild_grounds",
        "central_mountains",
        ((1365, 1394, 1005, 1034),),
    ),
    ActivityArea(
        "fox_fire_high_wild_grounds",
        "central_mountains",
        ((1360, 1389, 1545, 1574),),
    ),
    ActivityArea(
        "north_spine_wild_grounds",
        "central_mountains",
        ((1361, 1390, 1805, 1834),),
    ),
    ActivityArea(
        "silver_ridge_high_wild_grounds",
        "central_mountains",
        ((1362, 1391, 745, 774),),
    ),
# Central mountains (central-mountains-placement): site grounds and defended extents.
    ActivityArea(
        "spring_keeper_pool_grounds",
        "central_mountains",
        ((1410, 1430, 410, 430),),
    ),
    ActivityArea(
        "spring_keeper_pool_pool",
        "central_mountains",
        ((1415, 1425, 415, 425),),
    ),
    ActivityArea(
        "vent_crack_den_grounds",
        "central_mountains",
        ((1410, 1430, 1290, 1310),),
    ),
    ActivityArea(
        "vent_crack_den_crack",
        "central_mountains",
        ((1415, 1425, 1295, 1305),),
    ),
    ActivityArea(
        "crag_nest_ledge_grounds",
        "central_mountains",
        ((1386, 1406, 594, 614),),
    ),
    ActivityArea(
        "crag_nest_ledge_ledge",
        "central_mountains",
        ((1391, 1401, 599, 609),),
    ),
    ActivityArea(
        "old_veil_lamp_camp_grounds",
        "central_mountains",
        ((1420, 1440, 890, 910),),
    ),
    ActivityArea(
        "old_veil_lamp_camp_lamp",
        "central_mountains",
        ((1425, 1435, 895, 905),),
    ),
    ActivityArea(
        "rime_coil_boss_grounds",
        "central_mountains",
        ((1396, 1416, 86, 106),),
    ),
    ActivityArea(
        "rime_coil_boss_ravine",
        "central_mountains",
        ((1401, 1411, 91, 101),),
    ),
# Northwest highland forest (northwest-highland-placement): hinterland and deep-wild zone grounds.
    ActivityArea(
        "capital_valhalla_east_hinterland_grounds",
        "northwest_highland_forest",
        ((718, 737, 1680, 1699),),
    ),
    ActivityArea(
        "capital_valhalla_west_hinterland_grounds",
        "northwest_highland_forest",
        ((688, 707, 1680, 1699),),
    ),
    ActivityArea(
        "city_fox_fire_north_hinterland_grounds",
        "northwest_highland_forest",
        ((1283, 1302, 1705, 1724),),
    ),
    ActivityArea(
        "city_fox_fire_south_hinterland_grounds",
        "northwest_highland_forest",
        ((1283, 1302, 1677, 1696),),
    ),
    ActivityArea(
        "city_horn_plain_east_hinterland_grounds",
        "northwest_highland_forest",
        ((396, 415, 1645, 1664),),
    ),
    ActivityArea(
        "city_horn_plain_west_hinterland_grounds",
        "northwest_highland_forest",
        ((368, 387, 1645, 1664),),
    ),
    ActivityArea(
        "city_iron_claw_east_hinterland_grounds",
        "northwest_highland_forest",
        ((1180, 1199, 1589, 1608),),
    ),
    ActivityArea(
        "city_iron_claw_west_hinterland_grounds",
        "northwest_highland_forest",
        ((1152, 1171, 1589, 1608),),
    ),
    ActivityArea(
        "city_moon_howl_east_hinterland_grounds",
        "northwest_highland_forest",
        ((474, 493, 1834, 1853),),
    ),
    ActivityArea(
        "city_moon_howl_west_hinterland_grounds",
        "northwest_highland_forest",
        ((446, 465, 1834, 1853),),
    ),
    ActivityArea(
        "city_mutual_market_north_hinterland_grounds",
        "northwest_highland_forest",
        ((821, 840, 1374, 1393),),
    ),
    ActivityArea(
        "city_mutual_market_west_hinterland_grounds",
        "northwest_highland_forest",
        ((800, 819, 1368, 1387),),
    ),
    ActivityArea(
        "city_shadow_wood_east_hinterland_grounds",
        "northwest_highland_forest",
        ((191, 210, 1567, 1586),),
    ),
    ActivityArea(
        "city_shadow_wood_north_hinterland_grounds",
        "northwest_highland_forest",
        ((185, 204, 1588, 1607),),
    ),
    ActivityArea(
        "city_swift_wind_east_hinterland_grounds",
        "northwest_highland_forest",
        ((605, 624, 1424, 1443),),
    ),
    ActivityArea(
        "city_swift_wind_west_hinterland_grounds",
        "northwest_highland_forest",
        ((577, 596, 1424, 1443),),
    ),
    ActivityArea(
        "city_tiger_roar_east_hinterland_grounds",
        "northwest_highland_forest",
        ((1005, 1024, 1854, 1873),),
    ),
    ActivityArea(
        "city_tiger_roar_west_hinterland_grounds",
        "northwest_highland_forest",
        ((977, 996, 1854, 1873),),
    ),
    ActivityArea(
        "town_ancestor_shrine_hinterland_grounds",
        "northwest_highland_forest",
        ((734, 753, 1579, 1598),),
    ),
    ActivityArea(
        "town_east_ford_camp_hinterland_grounds",
        "northwest_highland_forest",
        ((1133, 1152, 1370, 1389),),
    ),
    ActivityArea(
        "town_falcon_hinterland_grounds",
        "northwest_highland_forest",
        ((1098, 1117, 1439, 1458),),
    ),
    ActivityArea(
        "town_frost_wind_hinterland_grounds",
        "northwest_highland_forest",
        ((217, 236, 1797, 1816),),
    ),
    ActivityArea(
        "town_grizzly_hinterland_grounds",
        "northwest_highland_forest",
        ((901, 920, 1473, 1492),),
    ),
    ActivityArea(
        "town_pine_ferry_hinterland_grounds",
        "northwest_highland_forest",
        ((1065, 1084, 1712, 1731),),
    ),
    ActivityArea(
        "town_shaman_cave_hinterland_grounds",
        "northwest_highland_forest",
        ((1173, 1192, 1800, 1819),),
    ),
    ActivityArea(
        "town_stag_ferry_hinterland_grounds",
        "northwest_highland_forest",
        ((374, 393, 1752, 1771),),
    ),
    ActivityArea(
        "town_west_ford_camp_hinterland_grounds",
        "northwest_highland_forest",
        ((433, 452, 1352, 1371),),
    ),
    ActivityArea(
        "far_west_wild_grounds",
        "northwest_highland_forest",
        ((150, 179, 1295, 1324),),
    ),
    ActivityArea(
        "howl_ridge_wild_grounds",
        "northwest_highland_forest",
        ((630, 659, 1895, 1924),),
    ),
    ActivityArea(
        "pine_ferry_west_wild_grounds",
        "northwest_highland_forest",
        ((885, 914, 1670, 1699),),
    ),
    ActivityArea(
        "valhalla_north_wild_grounds",
        "northwest_highland_forest",
        ((780, 809, 1880, 1909),),
    ),
    ActivityArea(
        "valhalla_west_wild_grounds",
        "northwest_highland_forest",
        ((540, 569, 1670, 1699),),
    ),
# Northwest highland forest (northwest-highland-placement): site grounds and defended extents.
    ActivityArea(
        "lek_master_lek_grounds",
        "northwest_highland_forest",
        ((1040, 1060, 1510, 1530),),
    ),
    ActivityArea(
        "lek_master_lek_lek",
        "northwest_highland_forest",
        ((1045, 1055, 1515, 1525),),
    ),
    ActivityArea(
        "old_dam_keeper_dam_grounds",
        "northwest_highland_forest",
        ((310, 330, 1690, 1710),),
    ),
    ActivityArea(
        "old_dam_keeper_dam_pond",
        "northwest_highland_forest",
        ((315, 325, 1695, 1705),),
    ),
    ActivityArea(
        "deep_seam_mole_den_grounds",
        "northwest_highland_forest",
        ((1230, 1250, 1550, 1570),),
    ),
    ActivityArea(
        "deep_seam_mole_den_chamber",
        "northwest_highland_forest",
        ((1235, 1245, 1555, 1565),),
    ),
    ActivityArea(
        "winter_den_glutton_den_grounds",
        "northwest_highland_forest",
        ((272, 292, 1892, 1912),),
    ),
    ActivityArea(
        "winter_den_glutton_den_cache",
        "northwest_highland_forest",
        ((277, 287, 1897, 1907),),
    ),
    ActivityArea(
        "golden_plume_boss_grounds",
        "northwest_highland_forest",
        ((280, 300, 1430, 1450),),
    ),
    ActivityArea(
        "golden_plume_boss_cliff",
        "northwest_highland_forest",
        ((285, 295, 1435, 1445),),
    ),
# Eastern plains (eastern-plains-deep-placement): deep-wild zone grounds.
    ActivityArea(
        "black_soil_north_wild_grounds",
        "eastern_plains",
        ((1660, 1689, 1605, 1634),),
    ),
    ActivityArea(
        "crystal_north_wild_grounds",
        "eastern_plains",
        ((2005, 2034, 1890, 1919),),
    ),
    ActivityArea(
        "east_pasture_east_wild_grounds",
        "eastern_plains",
        ((2500, 2529, 900, 929),),
    ),
    ActivityArea(
        "north_wood_west_wild_grounds",
        "eastern_plains",
        ((1540, 1569, 1875, 1904),),
    ),
    ActivityArea(
        "starglow_east_wild_grounds",
        "eastern_plains",
        ((2290, 2319, 1170, 1199),),
    ),
# Eastern plains (eastern-plains-deep-placement): site grounds and defended extents.
    ActivityArea(
        "flock_leader_camp_grounds",
        "eastern_plains",
        ((1690, 1710, 1090, 1110),),
    ),
    ActivityArea(
        "flock_leader_camp_stubble",
        "eastern_plains",
        ((1695, 1705, 1095, 1105),),
    ),
    ActivityArea(
        "nest_guard_nest_grounds",
        "eastern_plains",
        ((2190, 2210, 1190, 1210),),
    ),
    ActivityArea(
        "nest_guard_nest_warren",
        "eastern_plains",
        ((2195, 2205, 1195, 1205),),
    ),
    ActivityArea(
        "heap_brood_keeper_heap_grounds",
        "eastern_plains",
        ((2140, 2160, 790, 810),),
    ),
    ActivityArea(
        "heap_brood_keeper_heap_brood_heap",
        "eastern_plains",
        ((2145, 2155, 795, 805),),
    ),
    ActivityArea(
        "herd_stallion_camp_grounds",
        "eastern_plains",
        ((2390, 2410, 740, 760),),
    ),
    ActivityArea(
        "herd_stallion_camp_pasture",
        "eastern_plains",
        ((2395, 2405, 745, 755),),
    ),
    ActivityArea(
        "heronry_elder_nest_grounds",
        "eastern_plains",
        ((1740, 1760, 1690, 1710),),
    ),
    ActivityArea(
        "heronry_elder_nest_heronry",
        "eastern_plains",
        ((1745, 1755, 1695, 1705),),
    ),
    ActivityArea(
        "white_reed_boss_grounds",
        "eastern_plains",
        ((2140, 2160, 1820, 1840),),
    ),
    ActivityArea(
        "white_reed_boss_reed_bay",
        "eastern_plains",
        ((2145, 2155, 1825, 1835),),
    ),
# South-east coast (southeast-coast-placement): road-corridor and deep-wild zone grounds.
    ActivityArea(
        "southeast_road_02_grounds",
        "southeast_coast",
        ((2060, 2079, 477, 496),),
    ),
    ActivityArea(
        "southeast_road_03_grounds",
        "southeast_coast",
        ((2059, 2078, 307, 326),),
    ),
    ActivityArea(
        "east_bay_west_wild_grounds",
        "southeast_coast",
        ((2220, 2249, 380, 409),),
    ),
    ActivityArea(
        "golden_sheaf_northeast_wild_grounds",
        "southeast_coast",
        ((2130, 2159, 330, 359),),
    ),
    ActivityArea(
        "golden_sheaf_southwest_wild_grounds",
        "southeast_coast",
        ((1870, 1899, 120, 149),),
    ),
    ActivityArea(
        "golden_sheaf_west_wild_grounds",
        "southeast_coast",
        ((1960, 1989, 150, 179),),
    ),
    ActivityArea(
        "south_cape_east_wild_grounds",
        "southeast_coast",
        ((1780, 1809, 80, 109),),
    ),
# South-east coast (southeast-coast-placement): site grounds and defended extents.
    ActivityArea(
        "reef_warden_reef_grounds",
        "southeast_coast",
        ((1812, 1832, 88, 108),),
    ),
    ActivityArea(
        "reef_warden_reef_reef",
        "southeast_coast",
        ((1817, 1827, 93, 103),),
    ),
    ActivityArea(
        "bay_warden_bay_grounds",
        "southeast_coast",
        ((2252, 2272, 394, 414),),
    ),
    ActivityArea(
        "bay_warden_bay_backwater",
        "southeast_coast",
        ((2257, 2267, 399, 409),),
    ),
    ActivityArea(
        "turret_keeper_flat_grounds",
        "southeast_coast",
        ((2112, 2132, 292, 312),),
    ),
    ActivityArea(
        "turret_keeper_flat_turrets",
        "southeast_coast",
        ((2117, 2127, 297, 307),),
    ),
    ActivityArea(
        "stack_colony_elder_rocks_grounds",
        "southeast_coast",
        ((1952, 1972, 128, 148),),
    ),
    ActivityArea(
        "stack_colony_elder_rocks_colony",
        "southeast_coast",
        ((1957, 1967, 133, 143),),
    ),
    ActivityArea(
        "haulout_bull_sandbar_grounds",
        "southeast_coast",
        ((2274, 2294, 396, 416),),
    ),
    ActivityArea(
        "haulout_bull_sandbar_haulout",
        "southeast_coast",
        ((2279, 2289, 401, 411),),
    ),
# South-west coast (southwest-coast-placement): hinterland, road-corridor and deep-wild zone grounds.
    ActivityArea(
        "city_salt_ferry_east_hinterland_grounds",
        "southwest_coast",
        ((409, 428, 477, 496),),
    ),
    ActivityArea(
        "city_salt_ferry_west_hinterland_grounds",
        "southwest_coast",
        ((388, 407, 477, 496),),
    ),
    ActivityArea(
        "city_salt_road_east_hinterland_grounds",
        "southwest_coast",
        ((1024, 1043, 337, 356),),
    ),
    ActivityArea(
        "city_salt_road_west_hinterland_grounds",
        "southwest_coast",
        ((997, 1016, 359, 378),),
    ),
    ActivityArea(
        "town_olive_ferry_hinterland_grounds",
        "southwest_coast",
        ((704, 723, 232, 251),),
    ),
    ActivityArea(
        "southwest_road_03_grounds",
        "southwest_coast",
        ((1188, 1207, 416, 435),),
    ),
    ActivityArea(
        "southwest_road_04_grounds",
        "southwest_coast",
        ((549, 568, 337, 356),),
    ),
    ActivityArea(
        "southwest_road_05_grounds",
        "southwest_coast",
        ((850, 869, 287, 306),),
    ),
    ActivityArea(
        "southwest_road_06_grounds",
        "southwest_coast",
        ((612, 631, 258, 277),),
    ),
    ActivityArea(
        "southwest_road_07_grounds",
        "southwest_coast",
        ((498, 517, 235, 254),),
    ),
    ActivityArea(
        "salt_road_southeast_wild_grounds",
        "southwest_coast",
        ((1110, 1139, 110, 139),),
    ),
    ActivityArea(
        "salt_road_southwest_wild_grounds",
        "southwest_coast",
        ((930, 959, 120, 149),),
    ),
    ActivityArea(
        "south_tide_east_wild_grounds",
        "southwest_coast",
        ((720, 749, 100, 129),),
    ),
    ActivityArea(
        "southwest_east_cape_wild_grounds",
        "southwest_coast",
        ((1270, 1299, 90, 119),),
    ),
    ActivityArea(
        "white_sail_north_wild_grounds",
        "southwest_coast",
        ((280, 309, 440, 469),),
    ),
# South-west coast (southwest-coast-placement): site grounds and defended extents.
    ActivityArea(
        "salt_mound_soldier_mound_grounds",
        "southwest_coast",
        ((840, 860, 310, 330),),
    ),
    ActivityArea(
        "salt_mound_soldier_mound_crust",
        "southwest_coast",
        ((845, 855, 315, 325),),
    ),
    ActivityArea(
        "tide_pool_elder_pool_grounds",
        "southwest_coast",
        ((522, 542, 94, 114),),
    ),
    ActivityArea(
        "tide_pool_elder_pool_deep_pool",
        "southwest_coast",
        ((527, 537, 99, 109),),
    ),
    ActivityArea(
        "seawall_den_holder_den_grounds",
        "southwest_coast",
        ((280, 300, 398, 418),),
    ),
    ActivityArea(
        "seawall_den_holder_den_burrow",
        "southwest_coast",
        ((285, 295, 403, 413),),
    ),
    ActivityArea(
        "salt_dike_holder_dike_grounds",
        "southwest_coast",
        ((458, 478, 88, 108),),
    ),
    ActivityArea(
        "salt_dike_holder_dike_warm_dike",
        "southwest_coast",
        ((463, 473, 93, 103),),
    ),
    ActivityArea(
        "reef_warden_cove_grounds",
        "southwest_coast",
        ((258, 278, 480, 500),),
    ),
    ActivityArea(
        "reef_warden_cove_reef",
        "southwest_coast",
        ((263, 273, 485, 495),),
    ),
    ActivityArea(
        "sunken_anchor_boss_grounds",
        "southwest_coast",
        ((804, 824, 96, 116),),
    ),
    ActivityArea(
        "sunken_anchor_boss_wreck",
        "southwest_coast",
        ((809, 819, 101, 111),),
    ),
)

_ACTIVITY_DECLARATIONS: tuple[MonsterActivity, ...] = (
    MonsterActivity(
        "eastern_field_grain_pecker_activity",
        "solitary_roaming",
        "eastern_field_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_field_flock_leader_activity",
        "solitary_roaming",
        "eastern_field_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_field_burrow_maker_activity",
        "solitary_roaming",
        "eastern_field_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_field_nest_guard_activity",
        "solitary_roaming",
        "eastern_field_grounds",
        60,
        AggressionCondition("defended_area", "eastern_field_grounds"),
    ),
    MonsterActivity(
        "eastern_field_grain_and_burrow_activity",
        "cohesive_group",
        "eastern_field_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_wood_stalker_activity",
        "solitary_roaming",
        "highland_forest_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "highland_trail_hunter_activity",
        "solitary_roaming",
        "highland_forest_grounds",
        60,
        AggressionCondition("contact", dayparts=("dawn", "dusk")),
    ),
    MonsterActivity(
        "southwest_shore_walker_activity",
        "solitary_roaming",
        "southwest_shore_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_reef_warden_activity",
        "solitary_roaming",
        "southwest_shore_grounds",
        60,
        AggressionCondition("defended_area", "southwest_shore_grounds"),
    ),
    MonsterActivity(
        "western_rockland_burrow_maker_activity",
        "solitary_roaming",
        "western_rockland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_rockland_nest_guard_activity",
        "solitary_roaming",
        "western_rockland_grounds",
        60,
        AggressionCondition("defended_area", "western_rockland_grounds"),
    ),
    MonsterActivity(
        "western_rockland_cliff_stepper_activity",
        "solitary_roaming",
        "western_rockland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_rockland_pass_warden_activity",
        "solitary_roaming",
        "western_rockland_grounds",
        60,
        AggressionCondition("defended_area", "western_rockland_grounds"),
    ),
    MonsterActivity(
        "western_rockland_burrow_and_cliff_activity",
        "cohesive_group",
        "western_rockland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "ridge_burrow_nest_group_activity",
        "cohesive_group",
        "ridge_burrow_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "cliff_echo_camp_group_activity",
        "cohesive_group",
        "cliff_echo_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "tide_mouth_boss_activity",
        "solitary_roaming",
        "tide_mouth_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "ridge_burrow_nest_stationary",
        "stationary",
        "ridge_burrow_nest_home",
        120,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "cliff_echo_camp_stationary",
        "stationary",
        "cliff_echo_camp_home",
        120,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "tide_mouth_boss_stationary",
        "stationary",
        "tide_mouth_boss_home",
        120,
        AggressionCondition("passive"),
    ),
    # A mud-film slime is passive: approaching footsteps make it retreat, and
    # it answers only after engagement. The goblins and the rats forage as one
    # cohesive group but defend only inside their authored nest or cache, so an
    # ordinary group met away from that cell stays retreat-oriented.
    MonsterActivity(
        "eastern_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_mudbank_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_mudbank_dweller_activity",
        "solitary_roaming",
        "western_mudbank_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_quarry_nest_forager_activity",
        "cohesive_group",
        "western_quarry_grounds",
        90,
        AggressionCondition("defended_area", "western_quarry_nest"),
    ),
    MonsterActivity(
        "eastern_cache_forager_activity",
        "cohesive_group",
        "eastern_cache_grounds",
        90,
        AggressionCondition("defended_area", "eastern_cache_store"),
    ),
    MonsterActivity(
        "western_cache_forager_activity",
        "cohesive_group",
        "western_cache_grounds",
        90,
        AggressionCondition("defended_area", "western_cache_store"),
    ),
    # The abandoned transfer station holds co-located but independent animals:
    # the goblin pair forages as one cohesive group and defends its nest, while
    # the lone rat roams on its own and defends only its cache. Neither binding
    # ever joins the other's members.
    MonsterActivity(
        "transfer_station_nest_activity",
        "cohesive_group",
        "transfer_station_grounds",
        90,
        AggressionCondition("defended_area", "transfer_station_nest"),
    ),
    MonsterActivity(
        "transfer_station_stray_activity",
        "solitary_roaming",
        "transfer_station_grounds",
        60,
        AggressionCondition("defended_area", "transfer_station_cache"),
    ),
    # Both bosses are solitary territorial animals: one individual roams its
    # whole grounds and turns hostile only inside its defended bay or den. The
    # crocodile's utility binding never chooses a voluntary flee, so its fight
    # is decided by the party's own legal retreat; the boar stays legacy and
    # keeps its authored flee threshold.
    MonsterActivity(
        "reservoir_crocodile_territory_activity",
        "solitary_roaming",
        "reservoir_backwater_grounds",
        60,
        AggressionCondition("defended_area", "reservoir_backwater_bay"),
    ),
    MonsterActivity(
        "ember_bristle_territory_activity",
        "solitary_roaming",
        "ember_bristle_grounds",
        60,
        AggressionCondition("defended_area", "ember_bristle_den"),
    ),
# Near-settlement belts (eastern-plains-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    MonsterActivity(
        "capital_grandia_east_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "capital_grandia_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_grandia_east_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "capital_grandia_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_grandia_east_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "capital_grandia_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_grandia_east_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "capital_grandia_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_grandia_west_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "capital_grandia_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_grandia_west_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "capital_grandia_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_grandia_west_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "capital_grandia_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_grandia_west_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "capital_grandia_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_imperial_ferry_east_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "city_imperial_ferry_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_imperial_ferry_east_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_imperial_ferry_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_imperial_ferry_east_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_imperial_ferry_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_imperial_ferry_east_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_imperial_ferry_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_imperial_ferry_west_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "city_imperial_ferry_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_imperial_ferry_west_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_imperial_ferry_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_imperial_ferry_west_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_imperial_ferry_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_imperial_ferry_west_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_imperial_ferry_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_spice_road_east_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "city_spice_road_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_spice_road_east_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_spice_road_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_spice_road_east_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_spice_road_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_spice_road_east_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_spice_road_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_spice_road_west_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "city_spice_road_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_spice_road_west_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_spice_road_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_spice_road_west_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_spice_road_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_spice_road_west_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_spice_road_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_starglow_east_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "city_starglow_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_starglow_east_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_starglow_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_starglow_east_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_starglow_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_starglow_east_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_starglow_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_starglow_west_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "city_starglow_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_starglow_west_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_starglow_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_starglow_west_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_starglow_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_starglow_west_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_starglow_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_twin_currents_east_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "city_twin_currents_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_twin_currents_east_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_twin_currents_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_twin_currents_east_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_twin_currents_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_twin_currents_east_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_twin_currents_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_twin_currents_west_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "city_twin_currents_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_twin_currents_west_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_twin_currents_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_twin_currents_west_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_twin_currents_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_twin_currents_west_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_twin_currents_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_wheatwave_east_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "city_wheatwave_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_wheatwave_east_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_wheatwave_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_wheatwave_east_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_wheatwave_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_wheatwave_east_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_wheatwave_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_wheatwave_west_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "city_wheatwave_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_wheatwave_west_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_wheatwave_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_wheatwave_west_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_wheatwave_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_wheatwave_west_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_wheatwave_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_dawnlight_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "port_dawnlight_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_dawnlight_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "port_dawnlight_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_dawnlight_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "port_dawnlight_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_dawnlight_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "port_dawnlight_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_tide_wind_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "port_tide_wind_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_tide_wind_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "port_tide_wind_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_tide_wind_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "port_tide_wind_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_tide_wind_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "port_tide_wind_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_black_soil_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_black_soil_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_black_soil_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_black_soil_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_black_soil_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_black_soil_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_black_soil_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_black_soil_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_crystal_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_crystal_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_crystal_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_crystal_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_crystal_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_crystal_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_crystal_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_crystal_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_pasture_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_east_pasture_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_pasture_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_east_pasture_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_pasture_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_east_pasture_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_pasture_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_east_pasture_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_emerald_lake_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_emerald_lake_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_emerald_lake_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_emerald_lake_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_emerald_lake_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_emerald_lake_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_emerald_lake_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_emerald_lake_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_maple_foot_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_maple_foot_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_maple_foot_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_maple_foot_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_maple_foot_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_maple_foot_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_maple_foot_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_maple_foot_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_north_wood_keep_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_north_wood_keep_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_north_wood_keep_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_north_wood_keep_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_north_wood_keep_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_north_wood_keep_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_north_wood_keep_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_north_wood_keep_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_orange_blossom_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_orange_blossom_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_orange_blossom_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_orange_blossom_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_orange_blossom_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_orange_blossom_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_orange_blossom_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_orange_blossom_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_silver_ridge_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_silver_ridge_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_silver_ridge_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_silver_ridge_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_silver_ridge_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_silver_ridge_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_silver_ridge_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_silver_ridge_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_steed_plain_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_steed_plain_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_steed_plain_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_steed_plain_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_steed_plain_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_steed_plain_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_steed_plain_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_steed_plain_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_sunken_bell_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_sunken_bell_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_sunken_bell_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_sunken_bell_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_sunken_bell_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_sunken_bell_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_sunken_bell_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_sunken_bell_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_sunrise_hinterland_grain_pecker_activity",
        "solitary_roaming",
        "town_sunrise_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_sunrise_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_sunrise_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_sunrise_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_sunrise_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_sunrise_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_sunrise_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_01_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_01_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_01_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_01_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_01_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_01_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_01_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_01_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_02_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_02_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_02_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_02_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_02_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_02_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_02_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_02_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_03_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_03_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_03_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_03_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_03_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_03_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_03_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_03_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_04_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_04_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_04_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_04_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_04_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_04_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_04_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_04_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_05_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_05_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_05_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_05_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_05_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_05_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_05_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_05_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_06_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_06_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_06_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_06_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_06_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_06_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_06_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_06_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_07_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_07_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_07_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_07_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_07_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_07_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_07_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_07_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_08_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_08_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_08_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_08_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_08_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_08_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_08_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_08_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_09_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_09_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_09_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_09_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_09_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_09_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_09_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_09_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_10_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_10_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_10_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_10_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_10_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_10_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_10_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_10_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_11_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_11_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_11_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_11_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_11_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_11_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_11_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_11_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_12_grain_pecker_activity",
        "solitary_roaming",
        "eastern_road_12_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_12_burrow_maker_activity",
        "solitary_roaming",
        "eastern_road_12_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_12_mudbank_dweller_activity",
        "solitary_roaming",
        "eastern_road_12_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_12_wax_cache_forager_activity",
        "cohesive_group",
        "eastern_road_12_grounds",
        90,
        AggressionCondition("passive"),
    ),
# Near-settlement belts (western-hills-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    MonsterActivity(
        "capital_altoria_east_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "capital_altoria_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_altoria_east_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "capital_altoria_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_altoria_east_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "capital_altoria_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_altoria_east_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "capital_altoria_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_altoria_west_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "capital_altoria_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_altoria_west_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "capital_altoria_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_altoria_west_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "capital_altoria_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_altoria_west_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "capital_altoria_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_border_bridge_east_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_border_bridge_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_border_bridge_east_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_border_bridge_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_border_bridge_east_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_border_bridge_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_border_bridge_east_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "city_border_bridge_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_border_bridge_west_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_border_bridge_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_border_bridge_west_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_border_bridge_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_border_bridge_west_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_border_bridge_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_border_bridge_west_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "city_border_bridge_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_confluence_east_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_confluence_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_confluence_east_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_confluence_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_confluence_east_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_confluence_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_confluence_east_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "city_confluence_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_confluence_west_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_confluence_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_confluence_west_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_confluence_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_confluence_west_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_confluence_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_confluence_west_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "city_confluence_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_east_river_north_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_east_river_north_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_east_river_north_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_east_river_north_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_east_river_north_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_east_river_north_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_east_river_north_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "city_east_river_north_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_east_river_south_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_east_river_south_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_east_river_south_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_east_river_south_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_east_river_south_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_east_river_south_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_east_river_south_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "city_east_river_south_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_greyrock_east_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_greyrock_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_greyrock_east_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_greyrock_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_greyrock_east_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_greyrock_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_greyrock_east_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "city_greyrock_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_greyrock_west_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "city_greyrock_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_greyrock_west_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "city_greyrock_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_greyrock_west_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "city_greyrock_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_greyrock_west_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "city_greyrock_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_hills_mouth_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "port_hills_mouth_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_hills_mouth_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "port_hills_mouth_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_hills_mouth_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "port_hills_mouth_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_hills_mouth_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "port_hills_mouth_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_west_ore_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "port_west_ore_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_west_ore_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "port_west_ore_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_west_ore_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "port_west_ore_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_west_ore_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "port_west_ore_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_westwind_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "port_westwind_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_westwind_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "port_westwind_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_westwind_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "port_westwind_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_westwind_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "port_westwind_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_ferry_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_east_ferry_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_ferry_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_east_ferry_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_ferry_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_east_ferry_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_ferry_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "town_east_ferry_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_honey_vale_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_honey_vale_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_honey_vale_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_honey_vale_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_honey_vale_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_honey_vale_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_honey_vale_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "town_honey_vale_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_ruins_gate_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_ruins_gate_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_ruins_gate_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_ruins_gate_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_ruins_gate_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_ruins_gate_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_ruins_gate_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "town_ruins_gate_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_scarp_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_scarp_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_scarp_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_scarp_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_scarp_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_scarp_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_scarp_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "town_scarp_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_vineyard_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_vineyard_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_vineyard_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_vineyard_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_vineyard_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_vineyard_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_vineyard_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "town_vineyard_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_west_ferry_hinterland_burrow_maker_activity",
        "solitary_roaming",
        "town_west_ferry_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_west_ferry_hinterland_mudbank_dweller_activity",
        "solitary_roaming",
        "town_west_ferry_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_west_ferry_hinterland_wax_cache_forager_activity",
        "cohesive_group",
        "town_west_ferry_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_west_ferry_hinterland_hanging_nest_forager_activity",
        "cohesive_group",
        "town_west_ferry_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_01_cliff_stepper_activity",
        "solitary_roaming",
        "western_road_01_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_01_burrow_maker_activity",
        "solitary_roaming",
        "western_road_01_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_01_hanging_nest_forager_activity",
        "cohesive_group",
        "western_road_01_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_02_cliff_stepper_activity",
        "solitary_roaming",
        "western_road_02_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_02_burrow_maker_activity",
        "solitary_roaming",
        "western_road_02_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_02_hanging_nest_forager_activity",
        "cohesive_group",
        "western_road_02_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_03_burrow_maker_activity",
        "solitary_roaming",
        "western_road_03_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_03_mudbank_dweller_activity",
        "solitary_roaming",
        "western_road_03_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_03_wax_cache_forager_activity",
        "cohesive_group",
        "western_road_03_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_03_hanging_nest_forager_activity",
        "cohesive_group",
        "western_road_03_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_04_cliff_stepper_activity",
        "solitary_roaming",
        "western_road_04_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_04_burrow_maker_activity",
        "solitary_roaming",
        "western_road_04_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_04_hanging_nest_forager_activity",
        "cohesive_group",
        "western_road_04_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_05_cliff_stepper_activity",
        "solitary_roaming",
        "western_road_05_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_05_burrow_maker_activity",
        "solitary_roaming",
        "western_road_05_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_05_hanging_nest_forager_activity",
        "cohesive_group",
        "western_road_05_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_06_cliff_stepper_activity",
        "solitary_roaming",
        "western_road_06_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_06_burrow_maker_activity",
        "solitary_roaming",
        "western_road_06_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_06_hanging_nest_forager_activity",
        "cohesive_group",
        "western_road_06_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_07_cliff_stepper_activity",
        "solitary_roaming",
        "western_road_07_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_07_burrow_maker_activity",
        "solitary_roaming",
        "western_road_07_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_07_hanging_nest_forager_activity",
        "cohesive_group",
        "western_road_07_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_08_cliff_stepper_activity",
        "solitary_roaming",
        "western_road_08_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_08_burrow_maker_activity",
        "solitary_roaming",
        "western_road_08_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_08_hanging_nest_forager_activity",
        "cohesive_group",
        "western_road_08_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_09_cliff_stepper_activity",
        "solitary_roaming",
        "western_road_09_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_09_burrow_maker_activity",
        "solitary_roaming",
        "western_road_09_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_09_hanging_nest_forager_activity",
        "cohesive_group",
        "western_road_09_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_10_cliff_stepper_activity",
        "solitary_roaming",
        "western_road_10_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_10_burrow_maker_activity",
        "solitary_roaming",
        "western_road_10_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "western_road_10_hanging_nest_forager_activity",
        "cohesive_group",
        "western_road_10_grounds",
        90,
        AggressionCondition("passive"),
    ),
# Near-settlement belts (coastal-near-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    MonsterActivity(
        "port_east_bay_hinterland_shore_walker_activity",
        "solitary_roaming",
        "port_east_bay_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_east_bay_hinterland_shore_walker_pair_activity",
        "cohesive_group",
        "port_east_bay_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_east_bay_hinterland_shore_walker_trio_activity",
        "cohesive_group",
        "port_east_bay_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_golden_sheaf_hinterland_shore_walker_activity",
        "solitary_roaming",
        "port_golden_sheaf_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_golden_sheaf_hinterland_shore_walker_pair_activity",
        "cohesive_group",
        "port_golden_sheaf_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_golden_sheaf_hinterland_shore_walker_trio_activity",
        "cohesive_group",
        "port_golden_sheaf_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_south_cape_hinterland_shore_walker_activity",
        "solitary_roaming",
        "port_south_cape_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_south_cape_hinterland_shore_walker_pair_activity",
        "cohesive_group",
        "port_south_cape_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_south_cape_hinterland_shore_walker_trio_activity",
        "cohesive_group",
        "port_south_cape_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southeast_road_01_bank_lurker_activity",
        "solitary_roaming",
        "southeast_road_01_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "southeast_road_01_shore_walker_activity",
        "solitary_roaming",
        "southeast_road_01_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southeast_road_01_shore_walker_pair_activity",
        "cohesive_group",
        "southeast_road_01_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_fishers_cove_hinterland_shore_walker_activity",
        "solitary_roaming",
        "port_fishers_cove_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_fishers_cove_hinterland_shore_walker_pair_activity",
        "cohesive_group",
        "port_fishers_cove_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_fishers_cove_hinterland_shore_walker_trio_activity",
        "cohesive_group",
        "port_fishers_cove_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_south_tide_hinterland_shore_walker_activity",
        "solitary_roaming",
        "port_south_tide_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_south_tide_hinterland_shore_walker_pair_activity",
        "cohesive_group",
        "port_south_tide_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_south_tide_hinterland_shore_walker_trio_activity",
        "cohesive_group",
        "port_south_tide_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_white_sail_hinterland_shore_walker_activity",
        "solitary_roaming",
        "port_white_sail_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_white_sail_hinterland_shore_walker_pair_activity",
        "cohesive_group",
        "port_white_sail_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_white_sail_hinterland_shore_walker_trio_activity",
        "cohesive_group",
        "port_white_sail_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_01_shore_walker_activity",
        "solitary_roaming",
        "southwest_road_01_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_01_shore_walker_pair_activity",
        "cohesive_group",
        "southwest_road_01_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_01_shore_walker_trio_activity",
        "cohesive_group",
        "southwest_road_01_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_02_shore_walker_activity",
        "solitary_roaming",
        "southwest_road_02_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_02_shore_walker_pair_activity",
        "cohesive_group",
        "southwest_road_02_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_02_shore_walker_trio_activity",
        "cohesive_group",
        "southwest_road_02_grounds",
        90,
        AggressionCondition("passive"),
    ),
# Near-settlement belts (highland-road-belts): hinterland and road-corridor zones; each zone's grounds repeat its birth rectangle.
    MonsterActivity(
        "highland_road_01_wood_stalker_activity",
        "solitary_roaming",
        "highland_road_01_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "highland_road_02_wood_stalker_activity",
        "solitary_roaming",
        "highland_road_02_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "highland_road_03_wood_stalker_activity",
        "solitary_roaming",
        "highland_road_03_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "highland_road_04_wood_stalker_activity",
        "solitary_roaming",
        "highland_road_04_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "highland_road_05_wood_stalker_activity",
        "solitary_roaming",
        "highland_road_05_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "highland_road_06_wood_stalker_activity",
        "solitary_roaming",
        "highland_road_06_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "highland_road_07_wood_stalker_activity",
        "solitary_roaming",
        "highland_road_07_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "highland_road_08_wood_stalker_activity",
        "solitary_roaming",
        "highland_road_08_grounds",
        60,
        AggressionCondition("contact"),
    ),
# North deep forest (north-deep-forest-placement): hinterland, approach and deep-wild zone activities.
    MonsterActivity(
        "village_eolas_hinterland_rotlog_sprout_activity",
        "cohesive_group",
        "village_eolas_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "village_eolas_hinterland_quill_forager_activity",
        "solitary_roaming",
        "village_eolas_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "village_eolas_hinterland_hollow_roost_flier_activity",
        "cohesive_group",
        "village_eolas_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "north_wood_forest_edge_rotlog_sprout_activity",
        "cohesive_group",
        "north_wood_forest_edge_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "north_wood_forest_edge_quill_forager_activity",
        "solitary_roaming",
        "north_wood_forest_edge_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "north_wood_forest_edge_hollow_roost_flier_activity",
        "cohesive_group",
        "north_wood_forest_edge_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "tiger_roar_forest_edge_rotlog_sprout_activity",
        "cohesive_group",
        "tiger_roar_forest_edge_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "tiger_roar_forest_edge_quill_forager_activity",
        "solitary_roaming",
        "tiger_roar_forest_edge_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "tiger_roar_forest_edge_hollow_roost_flier_activity",
        "cohesive_group",
        "tiger_roar_forest_edge_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "dragon_nest_lower_wild_hush_wing_hunter_activity",
        "solitary_roaming",
        "dragon_nest_lower_wild_grounds",
        60,
        AggressionCondition("contact", dayparts=("dusk", "midnight")),
    ),
    MonsterActivity(
        "dragon_nest_lower_wild_vine_weaver_activity",
        "solitary_roaming",
        "dragon_nest_lower_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "dragon_nest_lower_wild_quill_forager_activity",
        "solitary_roaming",
        "dragon_nest_lower_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "dragon_nest_lower_wild_hollow_roost_flier_activity",
        "cohesive_group",
        "dragon_nest_lower_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "dragon_nest_upper_wild_hush_wing_hunter_activity",
        "solitary_roaming",
        "dragon_nest_upper_wild_grounds",
        60,
        AggressionCondition("contact", dayparts=("dusk", "midnight")),
    ),
    MonsterActivity(
        "dragon_nest_upper_wild_vine_weaver_activity",
        "solitary_roaming",
        "dragon_nest_upper_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "dragon_nest_upper_wild_quill_forager_activity",
        "solitary_roaming",
        "dragon_nest_upper_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "dragon_nest_upper_wild_hollow_roost_flier_activity",
        "cohesive_group",
        "dragon_nest_upper_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eternal_night_lower_wild_hush_wing_hunter_activity",
        "solitary_roaming",
        "eternal_night_lower_wild_grounds",
        60,
        AggressionCondition("contact", dayparts=("dusk", "midnight")),
    ),
    MonsterActivity(
        "eternal_night_lower_wild_vine_weaver_activity",
        "solitary_roaming",
        "eternal_night_lower_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eternal_night_lower_wild_quill_forager_activity",
        "solitary_roaming",
        "eternal_night_lower_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eternal_night_lower_wild_hollow_roost_flier_activity",
        "cohesive_group",
        "eternal_night_lower_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eternal_night_upper_wild_hush_wing_hunter_activity",
        "solitary_roaming",
        "eternal_night_upper_wild_grounds",
        60,
        AggressionCondition("contact", dayparts=("dusk", "midnight")),
    ),
    MonsterActivity(
        "eternal_night_upper_wild_vine_weaver_activity",
        "solitary_roaming",
        "eternal_night_upper_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eternal_night_upper_wild_quill_forager_activity",
        "solitary_roaming",
        "eternal_night_upper_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eternal_night_upper_wild_hollow_roost_flier_activity",
        "cohesive_group",
        "eternal_night_upper_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "moonvale_outer_wild_hush_wing_hunter_activity",
        "solitary_roaming",
        "moonvale_outer_wild_grounds",
        60,
        AggressionCondition("contact", dayparts=("dusk", "midnight")),
    ),
    MonsterActivity(
        "moonvale_outer_wild_vine_weaver_activity",
        "solitary_roaming",
        "moonvale_outer_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "moonvale_outer_wild_quill_forager_activity",
        "solitary_roaming",
        "moonvale_outer_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "moonvale_outer_wild_hollow_roost_flier_activity",
        "cohesive_group",
        "moonvale_outer_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
# North deep forest (north-deep-forest-placement): site activities.
    MonsterActivity(
        "fairy_ring_nest_activity",
        "cohesive_group",
        "fairy_ring_nest_grounds",
        90,
        AggressionCondition("defended_area", "fairy_ring_nest_ring"),
    ),
    MonsterActivity(
        "quill_den_nest_activity",
        "cohesive_group",
        "quill_den_nest_grounds",
        90,
        AggressionCondition("defended_area", "quill_den_nest_den"),
    ),
    MonsterActivity(
        "hollow_roost_camp_activity",
        "cohesive_group",
        "hollow_roost_camp_grounds",
        90,
        AggressionCondition("defended_area", "hollow_roost_camp_roost"),
    ),
    MonsterActivity(
        "old_hollow_owl_nest_activity",
        "solitary_roaming",
        "old_hollow_owl_nest_grounds",
        60,
        AggressionCondition("defended_area", "old_hollow_owl_nest_hollow"),
    ),
    MonsterActivity(
        "trail_net_camp_activity",
        "solitary_roaming",
        "trail_net_camp_grounds",
        60,
        AggressionCondition("defended_area", "trail_net_camp_web"),
    ),
    MonsterActivity(
        "moss_crown_boss_activity",
        "solitary_roaming",
        "moss_crown_boss_grounds",
        60,
        AggressionCondition("defended_area", "moss_crown_boss_glade"),
    ),
# Central mountains (central-mountains-placement): hinterland, approach and deep-wild zone activities.
    MonsterActivity(
        "village_ciaran_hinterland_seep_sipper_activity",
        "cohesive_group",
        "village_ciaran_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "village_ciaran_hinterland_seep_sipper_single_activity",
        "solitary_roaming",
        "village_ciaran_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "village_ciaran_hinterland_ledge_basker_activity",
        "solitary_roaming",
        "village_ciaran_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "village_fionnen_hinterland_seep_sipper_activity",
        "cohesive_group",
        "village_fionnen_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "village_fionnen_hinterland_seep_sipper_single_activity",
        "solitary_roaming",
        "village_fionnen_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "village_fionnen_hinterland_ledge_basker_activity",
        "solitary_roaming",
        "village_fionnen_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "fox_fire_pass_approach_seep_sipper_activity",
        "cohesive_group",
        "fox_fire_pass_approach_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "fox_fire_pass_approach_seep_sipper_single_activity",
        "solitary_roaming",
        "fox_fire_pass_approach_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "fox_fire_pass_approach_ledge_basker_activity",
        "solitary_roaming",
        "fox_fire_pass_approach_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "maple_foot_pass_approach_seep_sipper_activity",
        "cohesive_group",
        "maple_foot_pass_approach_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "maple_foot_pass_approach_seep_sipper_single_activity",
        "solitary_roaming",
        "maple_foot_pass_approach_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "maple_foot_pass_approach_ledge_basker_activity",
        "solitary_roaming",
        "maple_foot_pass_approach_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "scarp_pass_approach_seep_sipper_activity",
        "cohesive_group",
        "scarp_pass_approach_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "scarp_pass_approach_seep_sipper_single_activity",
        "solitary_roaming",
        "scarp_pass_approach_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "scarp_pass_approach_ledge_basker_activity",
        "solitary_roaming",
        "scarp_pass_approach_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "silver_ridge_pass_approach_seep_sipper_activity",
        "cohesive_group",
        "silver_ridge_pass_approach_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "silver_ridge_pass_approach_seep_sipper_single_activity",
        "solitary_roaming",
        "silver_ridge_pass_approach_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "silver_ridge_pass_approach_ledge_basker_activity",
        "solitary_roaming",
        "silver_ridge_pass_approach_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "ciaran_ridge_wild_updraft_glider_activity",
        "solitary_roaming",
        "ciaran_ridge_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "ciaran_ridge_wild_lamp_seeker_activity",
        "solitary_roaming",
        "ciaran_ridge_wild_grounds",
        60,
        AggressionCondition("contact", dayparts=("dusk", "midnight")),
    ),
    MonsterActivity(
        "ciaran_ridge_wild_seep_sipper_activity",
        "cohesive_group",
        "ciaran_ridge_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "ciaran_ridge_wild_ledge_basker_activity",
        "solitary_roaming",
        "ciaran_ridge_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "fionnen_ridge_wild_updraft_glider_activity",
        "solitary_roaming",
        "fionnen_ridge_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "fionnen_ridge_wild_lamp_seeker_activity",
        "solitary_roaming",
        "fionnen_ridge_wild_grounds",
        60,
        AggressionCondition("contact", dayparts=("dusk", "midnight")),
    ),
    MonsterActivity(
        "fionnen_ridge_wild_seep_sipper_activity",
        "cohesive_group",
        "fionnen_ridge_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "fionnen_ridge_wild_ledge_basker_activity",
        "solitary_roaming",
        "fionnen_ridge_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "fox_fire_high_wild_updraft_glider_activity",
        "solitary_roaming",
        "fox_fire_high_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "fox_fire_high_wild_lamp_seeker_activity",
        "solitary_roaming",
        "fox_fire_high_wild_grounds",
        60,
        AggressionCondition("contact", dayparts=("dusk", "midnight")),
    ),
    MonsterActivity(
        "fox_fire_high_wild_seep_sipper_activity",
        "cohesive_group",
        "fox_fire_high_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "fox_fire_high_wild_ledge_basker_activity",
        "solitary_roaming",
        "fox_fire_high_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "north_spine_wild_updraft_glider_activity",
        "solitary_roaming",
        "north_spine_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "north_spine_wild_lamp_seeker_activity",
        "solitary_roaming",
        "north_spine_wild_grounds",
        60,
        AggressionCondition("contact", dayparts=("dusk", "midnight")),
    ),
    MonsterActivity(
        "north_spine_wild_seep_sipper_activity",
        "cohesive_group",
        "north_spine_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "north_spine_wild_ledge_basker_activity",
        "solitary_roaming",
        "north_spine_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "silver_ridge_high_wild_updraft_glider_activity",
        "solitary_roaming",
        "silver_ridge_high_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "silver_ridge_high_wild_lamp_seeker_activity",
        "solitary_roaming",
        "silver_ridge_high_wild_grounds",
        60,
        AggressionCondition("contact", dayparts=("dusk", "midnight")),
    ),
    MonsterActivity(
        "silver_ridge_high_wild_seep_sipper_activity",
        "cohesive_group",
        "silver_ridge_high_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "silver_ridge_high_wild_ledge_basker_activity",
        "solitary_roaming",
        "silver_ridge_high_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
# Central mountains (central-mountains-placement): site activities.
    MonsterActivity(
        "spring_keeper_pool_activity",
        "cohesive_group",
        "spring_keeper_pool_grounds",
        90,
        AggressionCondition("defended_area", "spring_keeper_pool_pool"),
    ),
    MonsterActivity(
        "vent_crack_den_activity",
        "solitary_roaming",
        "vent_crack_den_grounds",
        60,
        AggressionCondition("defended_area", "vent_crack_den_crack"),
    ),
    MonsterActivity(
        "crag_nest_ledge_activity",
        "solitary_roaming",
        "crag_nest_ledge_grounds",
        60,
        AggressionCondition("defended_area", "crag_nest_ledge_ledge"),
    ),
    MonsterActivity(
        "old_veil_lamp_camp_activity",
        "solitary_roaming",
        "old_veil_lamp_camp_grounds",
        60,
        AggressionCondition("defended_area", "old_veil_lamp_camp_lamp"),
    ),
    MonsterActivity(
        "rime_coil_boss_activity",
        "solitary_roaming",
        "rime_coil_boss_grounds",
        60,
        AggressionCondition("defended_area", "rime_coil_boss_ravine"),
    ),
# Northwest highland forest (northwest-highland-placement): hinterland and deep-wild zone activities.
    MonsterActivity(
        "capital_valhalla_east_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "capital_valhalla_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_valhalla_east_hinterland_dam_builder_activity",
        "cohesive_group",
        "capital_valhalla_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_valhalla_east_hinterland_vein_digger_activity",
        "solitary_roaming",
        "capital_valhalla_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_valhalla_west_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "capital_valhalla_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_valhalla_west_hinterland_dam_builder_activity",
        "cohesive_group",
        "capital_valhalla_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_valhalla_west_hinterland_vein_digger_activity",
        "solitary_roaming",
        "capital_valhalla_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_fox_fire_north_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_fox_fire_north_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_fox_fire_north_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_fox_fire_north_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_fox_fire_north_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_fox_fire_north_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_fox_fire_south_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_fox_fire_south_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_fox_fire_south_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_fox_fire_south_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_fox_fire_south_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_fox_fire_south_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_horn_plain_east_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_horn_plain_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_horn_plain_east_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_horn_plain_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_horn_plain_east_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_horn_plain_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_horn_plain_west_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_horn_plain_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_horn_plain_west_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_horn_plain_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_horn_plain_west_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_horn_plain_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_iron_claw_east_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_iron_claw_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_iron_claw_east_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_iron_claw_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_iron_claw_east_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_iron_claw_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_iron_claw_west_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_iron_claw_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_iron_claw_west_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_iron_claw_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_iron_claw_west_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_iron_claw_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_moon_howl_east_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_moon_howl_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_moon_howl_east_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_moon_howl_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_moon_howl_east_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_moon_howl_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_moon_howl_west_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_moon_howl_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_moon_howl_west_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_moon_howl_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_moon_howl_west_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_moon_howl_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_mutual_market_north_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_mutual_market_north_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_mutual_market_north_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_mutual_market_north_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_mutual_market_north_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_mutual_market_north_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_mutual_market_west_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_mutual_market_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_mutual_market_west_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_mutual_market_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_mutual_market_west_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_mutual_market_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_shadow_wood_east_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_shadow_wood_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_shadow_wood_east_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_shadow_wood_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_shadow_wood_east_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_shadow_wood_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_shadow_wood_north_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_shadow_wood_north_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_shadow_wood_north_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_shadow_wood_north_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_shadow_wood_north_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_shadow_wood_north_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_swift_wind_east_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_swift_wind_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_swift_wind_east_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_swift_wind_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_swift_wind_east_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_swift_wind_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_swift_wind_west_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_swift_wind_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_swift_wind_west_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_swift_wind_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_swift_wind_west_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_swift_wind_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_tiger_roar_east_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_tiger_roar_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_tiger_roar_east_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_tiger_roar_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_tiger_roar_east_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_tiger_roar_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_tiger_roar_west_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "city_tiger_roar_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_tiger_roar_west_hinterland_dam_builder_activity",
        "cohesive_group",
        "city_tiger_roar_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_tiger_roar_west_hinterland_vein_digger_activity",
        "solitary_roaming",
        "city_tiger_roar_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_ancestor_shrine_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "town_ancestor_shrine_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_ancestor_shrine_hinterland_dam_builder_activity",
        "cohesive_group",
        "town_ancestor_shrine_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_ancestor_shrine_hinterland_vein_digger_activity",
        "solitary_roaming",
        "town_ancestor_shrine_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_ford_camp_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "town_east_ford_camp_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_ford_camp_hinterland_dam_builder_activity",
        "cohesive_group",
        "town_east_ford_camp_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_ford_camp_hinterland_vein_digger_activity",
        "solitary_roaming",
        "town_east_ford_camp_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_falcon_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "town_falcon_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_falcon_hinterland_dam_builder_activity",
        "cohesive_group",
        "town_falcon_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_falcon_hinterland_vein_digger_activity",
        "solitary_roaming",
        "town_falcon_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_frost_wind_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "town_frost_wind_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_frost_wind_hinterland_dam_builder_activity",
        "cohesive_group",
        "town_frost_wind_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_frost_wind_hinterland_vein_digger_activity",
        "solitary_roaming",
        "town_frost_wind_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_grizzly_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "town_grizzly_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_grizzly_hinterland_dam_builder_activity",
        "cohesive_group",
        "town_grizzly_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_grizzly_hinterland_vein_digger_activity",
        "solitary_roaming",
        "town_grizzly_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_pine_ferry_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "town_pine_ferry_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_pine_ferry_hinterland_dam_builder_activity",
        "cohesive_group",
        "town_pine_ferry_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_pine_ferry_hinterland_vein_digger_activity",
        "solitary_roaming",
        "town_pine_ferry_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_shaman_cave_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "town_shaman_cave_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_shaman_cave_hinterland_dam_builder_activity",
        "cohesive_group",
        "town_shaman_cave_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_shaman_cave_hinterland_vein_digger_activity",
        "solitary_roaming",
        "town_shaman_cave_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_stag_ferry_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "town_stag_ferry_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_stag_ferry_hinterland_dam_builder_activity",
        "cohesive_group",
        "town_stag_ferry_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_stag_ferry_hinterland_vein_digger_activity",
        "solitary_roaming",
        "town_stag_ferry_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_west_ford_camp_hinterland_pine_floor_grouse_activity",
        "cohesive_group",
        "town_west_ford_camp_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_west_ford_camp_hinterland_dam_builder_activity",
        "cohesive_group",
        "town_west_ford_camp_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_west_ford_camp_hinterland_vein_digger_activity",
        "solitary_roaming",
        "town_west_ford_camp_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "far_west_wild_trapline_raider_activity",
        "solitary_roaming",
        "far_west_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "far_west_wild_wood_stalker_activity",
        "solitary_roaming",
        "far_west_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "far_west_wild_pine_floor_grouse_activity",
        "cohesive_group",
        "far_west_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "far_west_wild_vein_digger_activity",
        "solitary_roaming",
        "far_west_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "howl_ridge_wild_trapline_raider_activity",
        "solitary_roaming",
        "howl_ridge_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "howl_ridge_wild_wood_stalker_activity",
        "solitary_roaming",
        "howl_ridge_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "howl_ridge_wild_pine_floor_grouse_activity",
        "cohesive_group",
        "howl_ridge_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "howl_ridge_wild_vein_digger_activity",
        "solitary_roaming",
        "howl_ridge_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "pine_ferry_west_wild_trapline_raider_activity",
        "solitary_roaming",
        "pine_ferry_west_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "pine_ferry_west_wild_wood_stalker_activity",
        "solitary_roaming",
        "pine_ferry_west_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "pine_ferry_west_wild_pine_floor_grouse_activity",
        "cohesive_group",
        "pine_ferry_west_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "pine_ferry_west_wild_vein_digger_activity",
        "solitary_roaming",
        "pine_ferry_west_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "valhalla_north_wild_trapline_raider_activity",
        "solitary_roaming",
        "valhalla_north_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "valhalla_north_wild_wood_stalker_activity",
        "solitary_roaming",
        "valhalla_north_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "valhalla_north_wild_pine_floor_grouse_activity",
        "cohesive_group",
        "valhalla_north_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "valhalla_north_wild_vein_digger_activity",
        "solitary_roaming",
        "valhalla_north_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "valhalla_west_wild_trapline_raider_activity",
        "solitary_roaming",
        "valhalla_west_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "valhalla_west_wild_wood_stalker_activity",
        "solitary_roaming",
        "valhalla_west_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "valhalla_west_wild_pine_floor_grouse_activity",
        "cohesive_group",
        "valhalla_west_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "valhalla_west_wild_vein_digger_activity",
        "solitary_roaming",
        "valhalla_west_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
# Northwest highland forest (northwest-highland-placement): corridor low company activities.
    MonsterActivity(
        "highland_road_01_pine_floor_grouse_activity",
        "cohesive_group",
        "highland_road_01_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_01_vein_digger_activity",
        "solitary_roaming",
        "highland_road_01_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_02_pine_floor_grouse_activity",
        "cohesive_group",
        "highland_road_02_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_02_vein_digger_activity",
        "solitary_roaming",
        "highland_road_02_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_03_pine_floor_grouse_activity",
        "cohesive_group",
        "highland_road_03_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_03_vein_digger_activity",
        "solitary_roaming",
        "highland_road_03_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_04_pine_floor_grouse_activity",
        "cohesive_group",
        "highland_road_04_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_04_vein_digger_activity",
        "solitary_roaming",
        "highland_road_04_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_05_pine_floor_grouse_activity",
        "cohesive_group",
        "highland_road_05_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_05_vein_digger_activity",
        "solitary_roaming",
        "highland_road_05_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_06_pine_floor_grouse_activity",
        "cohesive_group",
        "highland_road_06_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_06_vein_digger_activity",
        "solitary_roaming",
        "highland_road_06_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_07_pine_floor_grouse_activity",
        "cohesive_group",
        "highland_road_07_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_07_vein_digger_activity",
        "solitary_roaming",
        "highland_road_07_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_08_pine_floor_grouse_activity",
        "cohesive_group",
        "highland_road_08_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "highland_road_08_vein_digger_activity",
        "solitary_roaming",
        "highland_road_08_grounds",
        60,
        AggressionCondition("passive"),
    ),
# Northwest highland forest (northwest-highland-placement): site activities.
    MonsterActivity(
        "lek_master_lek_activity",
        "cohesive_group",
        "lek_master_lek_grounds",
        90,
        AggressionCondition("defended_area", "lek_master_lek_lek"),
    ),
    MonsterActivity(
        "old_dam_keeper_dam_activity",
        "cohesive_group",
        "old_dam_keeper_dam_grounds",
        90,
        AggressionCondition("defended_area", "old_dam_keeper_dam_pond"),
    ),
    MonsterActivity(
        "deep_seam_mole_den_activity",
        "solitary_roaming",
        "deep_seam_mole_den_grounds",
        60,
        AggressionCondition("defended_area", "deep_seam_mole_den_chamber"),
    ),
    MonsterActivity(
        "winter_den_glutton_den_activity",
        "solitary_roaming",
        "winter_den_glutton_den_grounds",
        60,
        AggressionCondition("defended_area", "winter_den_glutton_den_cache"),
    ),
    MonsterActivity(
        "golden_plume_boss_activity",
        "solitary_roaming",
        "golden_plume_boss_grounds",
        60,
        AggressionCondition("defended_area", "golden_plume_boss_cliff"),
    ),
# Eastern plains (eastern-plains-deep-placement): deep-wild zone activities.
    MonsterActivity(
        "black_soil_north_wild_plain_runner_activity",
        "cohesive_group",
        "black_soil_north_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "black_soil_north_wild_sluice_wader_activity",
        "solitary_roaming",
        "black_soil_north_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "black_soil_north_wild_road_ball_roller_activity",
        "cohesive_group",
        "black_soil_north_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "black_soil_north_wild_grain_pecker_activity",
        "solitary_roaming",
        "black_soil_north_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "black_soil_north_wild_burrow_maker_activity",
        "solitary_roaming",
        "black_soil_north_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "crystal_north_wild_plain_runner_activity",
        "cohesive_group",
        "crystal_north_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "crystal_north_wild_sluice_wader_activity",
        "solitary_roaming",
        "crystal_north_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "crystal_north_wild_road_ball_roller_activity",
        "cohesive_group",
        "crystal_north_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "crystal_north_wild_grain_pecker_activity",
        "solitary_roaming",
        "crystal_north_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "crystal_north_wild_burrow_maker_activity",
        "solitary_roaming",
        "crystal_north_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "east_pasture_east_wild_plain_runner_activity",
        "cohesive_group",
        "east_pasture_east_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "east_pasture_east_wild_sluice_wader_activity",
        "solitary_roaming",
        "east_pasture_east_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "east_pasture_east_wild_road_ball_roller_activity",
        "cohesive_group",
        "east_pasture_east_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "east_pasture_east_wild_grain_pecker_activity",
        "solitary_roaming",
        "east_pasture_east_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "east_pasture_east_wild_burrow_maker_activity",
        "solitary_roaming",
        "east_pasture_east_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "north_wood_west_wild_plain_runner_activity",
        "cohesive_group",
        "north_wood_west_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "north_wood_west_wild_sluice_wader_activity",
        "solitary_roaming",
        "north_wood_west_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "north_wood_west_wild_road_ball_roller_activity",
        "cohesive_group",
        "north_wood_west_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "north_wood_west_wild_grain_pecker_activity",
        "solitary_roaming",
        "north_wood_west_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "north_wood_west_wild_burrow_maker_activity",
        "solitary_roaming",
        "north_wood_west_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "starglow_east_wild_plain_runner_activity",
        "cohesive_group",
        "starglow_east_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "starglow_east_wild_sluice_wader_activity",
        "solitary_roaming",
        "starglow_east_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "starglow_east_wild_road_ball_roller_activity",
        "cohesive_group",
        "starglow_east_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "starglow_east_wild_grain_pecker_activity",
        "solitary_roaming",
        "starglow_east_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "starglow_east_wild_burrow_maker_activity",
        "solitary_roaming",
        "starglow_east_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
# Eastern plains (eastern-plains-deep-placement): compositions added to the landed hinterland and corridor zones.
    MonsterActivity(
        "capital_grandia_east_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "capital_grandia_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "capital_grandia_west_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "capital_grandia_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_imperial_ferry_east_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "city_imperial_ferry_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_imperial_ferry_west_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "city_imperial_ferry_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_spice_road_east_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "city_spice_road_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_spice_road_west_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "city_spice_road_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_starglow_east_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "city_starglow_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_starglow_west_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "city_starglow_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_twin_currents_east_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "city_twin_currents_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_twin_currents_west_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "city_twin_currents_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_wheatwave_east_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "city_wheatwave_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_wheatwave_west_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "city_wheatwave_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_01_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_01_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_01_plain_runner_activity",
        "cohesive_group",
        "eastern_road_01_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_01_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_01_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_02_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_02_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_02_plain_runner_activity",
        "cohesive_group",
        "eastern_road_02_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_02_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_02_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_03_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_03_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_03_plain_runner_activity",
        "cohesive_group",
        "eastern_road_03_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_03_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_03_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_04_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_04_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_04_plain_runner_activity",
        "cohesive_group",
        "eastern_road_04_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_04_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_04_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_05_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_05_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_05_plain_runner_activity",
        "cohesive_group",
        "eastern_road_05_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_05_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_05_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_06_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_06_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_06_plain_runner_activity",
        "cohesive_group",
        "eastern_road_06_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_06_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_06_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_07_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_07_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_07_plain_runner_activity",
        "cohesive_group",
        "eastern_road_07_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_07_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_07_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_08_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_08_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_08_plain_runner_activity",
        "cohesive_group",
        "eastern_road_08_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_08_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_08_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_09_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_09_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_09_plain_runner_activity",
        "cohesive_group",
        "eastern_road_09_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_09_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_09_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_10_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_10_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_10_plain_runner_activity",
        "cohesive_group",
        "eastern_road_10_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_10_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_10_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_11_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_11_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_11_plain_runner_activity",
        "cohesive_group",
        "eastern_road_11_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_11_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_11_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_12_road_ball_roller_activity",
        "cohesive_group",
        "eastern_road_12_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "eastern_road_12_plain_runner_activity",
        "cohesive_group",
        "eastern_road_12_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "eastern_road_12_sluice_wader_activity",
        "solitary_roaming",
        "eastern_road_12_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "port_dawnlight_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "port_dawnlight_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_tide_wind_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "port_tide_wind_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_black_soil_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_black_soil_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_crystal_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_crystal_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_east_pasture_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_east_pasture_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_emerald_lake_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_emerald_lake_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_maple_foot_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_maple_foot_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_north_wood_keep_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_north_wood_keep_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_orange_blossom_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_orange_blossom_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_silver_ridge_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_silver_ridge_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_steed_plain_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_steed_plain_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_sunken_bell_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_sunken_bell_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_sunrise_hinterland_road_ball_roller_activity",
        "cohesive_group",
        "town_sunrise_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
# Eastern plains (eastern-plains-deep-placement): site activities.
    MonsterActivity(
        "flock_leader_camp_activity",
        "cohesive_group",
        "flock_leader_camp_grounds",
        90,
        AggressionCondition("defended_area", "flock_leader_camp_stubble"),
    ),
    MonsterActivity(
        "nest_guard_nest_activity",
        "cohesive_group",
        "nest_guard_nest_grounds",
        90,
        AggressionCondition("defended_area", "nest_guard_nest_warren"),
    ),
    MonsterActivity(
        "heap_brood_keeper_heap_activity",
        "cohesive_group",
        "heap_brood_keeper_heap_grounds",
        90,
        AggressionCondition("defended_area", "heap_brood_keeper_heap_brood_heap"),
    ),
    MonsterActivity(
        "herd_stallion_camp_activity",
        "cohesive_group",
        "herd_stallion_camp_grounds",
        90,
        AggressionCondition("defended_area", "herd_stallion_camp_pasture"),
    ),
    MonsterActivity(
        "heronry_elder_nest_activity",
        "cohesive_group",
        "heronry_elder_nest_grounds",
        90,
        AggressionCondition("defended_area", "heronry_elder_nest_heronry"),
    ),
    MonsterActivity(
        "white_reed_boss_activity",
        "solitary_roaming",
        "white_reed_boss_grounds",
        60,
        AggressionCondition("defended_area", "white_reed_boss_reed_bay"),
    ),
# South-east coast (southeast-coast-placement): road-corridor and deep-wild zone activities.
    MonsterActivity(
        "southeast_road_02_mast_circler_activity",
        "solitary_roaming",
        "southeast_road_02_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southeast_road_02_mast_circler_pair_activity",
        "cohesive_group",
        "southeast_road_02_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southeast_road_02_mast_circler_flock_activity",
        "cohesive_group",
        "southeast_road_02_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southeast_road_03_mast_circler_activity",
        "solitary_roaming",
        "southeast_road_03_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southeast_road_03_mast_circler_pair_activity",
        "cohesive_group",
        "southeast_road_03_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southeast_road_03_mast_circler_flock_activity",
        "cohesive_group",
        "southeast_road_03_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "east_bay_west_wild_pier_basker_activity",
        "cohesive_group",
        "east_bay_west_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "east_bay_west_wild_bank_lurker_activity",
        "solitary_roaming",
        "east_bay_west_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "east_bay_west_wild_shore_walker_activity",
        "solitary_roaming",
        "east_bay_west_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "east_bay_west_wild_mudflat_skipper_activity",
        "cohesive_group",
        "east_bay_west_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "east_bay_west_wild_mast_circler_activity",
        "cohesive_group",
        "east_bay_west_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "golden_sheaf_northeast_wild_pier_basker_activity",
        "cohesive_group",
        "golden_sheaf_northeast_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "golden_sheaf_northeast_wild_bank_lurker_activity",
        "solitary_roaming",
        "golden_sheaf_northeast_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "golden_sheaf_northeast_wild_shore_walker_activity",
        "solitary_roaming",
        "golden_sheaf_northeast_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "golden_sheaf_northeast_wild_mudflat_skipper_activity",
        "cohesive_group",
        "golden_sheaf_northeast_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "golden_sheaf_northeast_wild_mast_circler_activity",
        "cohesive_group",
        "golden_sheaf_northeast_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "golden_sheaf_southwest_wild_pier_basker_activity",
        "cohesive_group",
        "golden_sheaf_southwest_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "golden_sheaf_southwest_wild_bank_lurker_activity",
        "solitary_roaming",
        "golden_sheaf_southwest_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "golden_sheaf_southwest_wild_shore_walker_activity",
        "solitary_roaming",
        "golden_sheaf_southwest_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "golden_sheaf_southwest_wild_mudflat_skipper_activity",
        "cohesive_group",
        "golden_sheaf_southwest_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "golden_sheaf_southwest_wild_mast_circler_activity",
        "cohesive_group",
        "golden_sheaf_southwest_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "golden_sheaf_west_wild_pier_basker_activity",
        "cohesive_group",
        "golden_sheaf_west_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "golden_sheaf_west_wild_bank_lurker_activity",
        "solitary_roaming",
        "golden_sheaf_west_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "golden_sheaf_west_wild_shore_walker_activity",
        "solitary_roaming",
        "golden_sheaf_west_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "golden_sheaf_west_wild_mudflat_skipper_activity",
        "cohesive_group",
        "golden_sheaf_west_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "golden_sheaf_west_wild_mast_circler_activity",
        "cohesive_group",
        "golden_sheaf_west_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "south_cape_east_wild_pier_basker_activity",
        "cohesive_group",
        "south_cape_east_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "south_cape_east_wild_bank_lurker_activity",
        "solitary_roaming",
        "south_cape_east_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "south_cape_east_wild_shore_walker_activity",
        "solitary_roaming",
        "south_cape_east_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "south_cape_east_wild_mudflat_skipper_activity",
        "cohesive_group",
        "south_cape_east_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "south_cape_east_wild_mast_circler_activity",
        "cohesive_group",
        "south_cape_east_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
# South-east coast (southeast-coast-placement): activities of the compositions added to the landed port hinterland and corridor zones.
    MonsterActivity(
        "port_east_bay_hinterland_mudflat_skipper_activity",
        "cohesive_group",
        "port_east_bay_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_east_bay_hinterland_mast_circler_activity",
        "cohesive_group",
        "port_east_bay_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_golden_sheaf_hinterland_mudflat_skipper_activity",
        "cohesive_group",
        "port_golden_sheaf_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_golden_sheaf_hinterland_mast_circler_activity",
        "cohesive_group",
        "port_golden_sheaf_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_south_cape_hinterland_mudflat_skipper_activity",
        "cohesive_group",
        "port_south_cape_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_south_cape_hinterland_mast_circler_activity",
        "cohesive_group",
        "port_south_cape_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southeast_road_01_mast_circler_activity",
        "cohesive_group",
        "southeast_road_01_grounds",
        90,
        AggressionCondition("passive"),
    ),
# South-east coast (southeast-coast-placement): site activities.
    MonsterActivity(
        "reef_warden_reef_activity",
        "cohesive_group",
        "reef_warden_reef_grounds",
        90,
        AggressionCondition("defended_area", "reef_warden_reef_reef"),
    ),
    MonsterActivity(
        "bay_warden_bay_activity",
        "solitary_roaming",
        "bay_warden_bay_grounds",
        60,
        AggressionCondition("defended_area", "bay_warden_bay_backwater"),
    ),
    MonsterActivity(
        "turret_keeper_flat_activity",
        "cohesive_group",
        "turret_keeper_flat_grounds",
        90,
        AggressionCondition("defended_area", "turret_keeper_flat_turrets"),
    ),
    MonsterActivity(
        "stack_colony_elder_rocks_activity",
        "cohesive_group",
        "stack_colony_elder_rocks_grounds",
        90,
        AggressionCondition("defended_area", "stack_colony_elder_rocks_colony"),
    ),
    MonsterActivity(
        "haulout_bull_sandbar_activity",
        "cohesive_group",
        "haulout_bull_sandbar_grounds",
        90,
        AggressionCondition("defended_area", "haulout_bull_sandbar_haulout"),
    ),
# South-west coast (southwest-coast-placement): hinterland, road-corridor and deep-wild zone activities.
    MonsterActivity(
        "city_salt_ferry_east_hinterland_salt_hauler_activity",
        "solitary_roaming",
        "city_salt_ferry_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_ferry_east_hinterland_salt_hauler_pair_activity",
        "cohesive_group",
        "city_salt_ferry_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_ferry_east_hinterland_salt_hauler_column_activity",
        "cohesive_group",
        "city_salt_ferry_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_ferry_west_hinterland_salt_hauler_activity",
        "solitary_roaming",
        "city_salt_ferry_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_ferry_west_hinterland_salt_hauler_pair_activity",
        "cohesive_group",
        "city_salt_ferry_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_ferry_west_hinterland_salt_hauler_column_activity",
        "cohesive_group",
        "city_salt_ferry_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_road_east_hinterland_salt_hauler_activity",
        "solitary_roaming",
        "city_salt_road_east_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_road_east_hinterland_salt_hauler_pair_activity",
        "cohesive_group",
        "city_salt_road_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_road_east_hinterland_salt_hauler_column_activity",
        "cohesive_group",
        "city_salt_road_east_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_road_west_hinterland_salt_hauler_activity",
        "solitary_roaming",
        "city_salt_road_west_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_road_west_hinterland_salt_hauler_pair_activity",
        "cohesive_group",
        "city_salt_road_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "city_salt_road_west_hinterland_salt_hauler_column_activity",
        "cohesive_group",
        "city_salt_road_west_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_olive_ferry_hinterland_salt_hauler_activity",
        "solitary_roaming",
        "town_olive_ferry_hinterland_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_olive_ferry_hinterland_salt_hauler_pair_activity",
        "cohesive_group",
        "town_olive_ferry_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "town_olive_ferry_hinterland_salt_hauler_column_activity",
        "cohesive_group",
        "town_olive_ferry_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_03_salt_hauler_activity",
        "solitary_roaming",
        "southwest_road_03_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_03_salt_hauler_pair_activity",
        "cohesive_group",
        "southwest_road_03_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_03_salt_hauler_column_activity",
        "cohesive_group",
        "southwest_road_03_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_04_salt_hauler_activity",
        "solitary_roaming",
        "southwest_road_04_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_04_salt_hauler_pair_activity",
        "cohesive_group",
        "southwest_road_04_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_04_salt_hauler_column_activity",
        "cohesive_group",
        "southwest_road_04_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_05_salt_hauler_activity",
        "solitary_roaming",
        "southwest_road_05_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_05_salt_hauler_pair_activity",
        "cohesive_group",
        "southwest_road_05_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_05_salt_hauler_column_activity",
        "cohesive_group",
        "southwest_road_05_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_06_salt_hauler_activity",
        "solitary_roaming",
        "southwest_road_06_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_06_salt_hauler_pair_activity",
        "cohesive_group",
        "southwest_road_06_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_06_salt_hauler_column_activity",
        "cohesive_group",
        "southwest_road_06_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_07_salt_hauler_activity",
        "solitary_roaming",
        "southwest_road_07_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_07_salt_hauler_pair_activity",
        "cohesive_group",
        "southwest_road_07_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_07_salt_hauler_column_activity",
        "cohesive_group",
        "southwest_road_07_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "salt_road_southeast_wild_reef_burrow_striker_activity",
        "solitary_roaming",
        "salt_road_southeast_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "salt_road_southeast_wild_seacliff_basker_activity",
        "cohesive_group",
        "salt_road_southeast_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "salt_road_southeast_wild_shore_walker_activity",
        "solitary_roaming",
        "salt_road_southeast_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "salt_road_southeast_wild_oyster_rack_creeper_activity",
        "cohesive_group",
        "salt_road_southeast_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "salt_road_southeast_wild_salt_hauler_activity",
        "cohesive_group",
        "salt_road_southeast_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "salt_road_southwest_wild_reef_burrow_striker_activity",
        "solitary_roaming",
        "salt_road_southwest_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "salt_road_southwest_wild_seacliff_basker_activity",
        "cohesive_group",
        "salt_road_southwest_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "salt_road_southwest_wild_shore_walker_activity",
        "solitary_roaming",
        "salt_road_southwest_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "salt_road_southwest_wild_oyster_rack_creeper_activity",
        "cohesive_group",
        "salt_road_southwest_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "salt_road_southwest_wild_salt_hauler_activity",
        "cohesive_group",
        "salt_road_southwest_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "south_tide_east_wild_reef_burrow_striker_activity",
        "solitary_roaming",
        "south_tide_east_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "south_tide_east_wild_seacliff_basker_activity",
        "cohesive_group",
        "south_tide_east_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "south_tide_east_wild_shore_walker_activity",
        "solitary_roaming",
        "south_tide_east_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "south_tide_east_wild_oyster_rack_creeper_activity",
        "cohesive_group",
        "south_tide_east_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "south_tide_east_wild_salt_hauler_activity",
        "cohesive_group",
        "south_tide_east_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_east_cape_wild_reef_burrow_striker_activity",
        "solitary_roaming",
        "southwest_east_cape_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "southwest_east_cape_wild_seacliff_basker_activity",
        "cohesive_group",
        "southwest_east_cape_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "southwest_east_cape_wild_shore_walker_activity",
        "solitary_roaming",
        "southwest_east_cape_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_east_cape_wild_oyster_rack_creeper_activity",
        "cohesive_group",
        "southwest_east_cape_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_east_cape_wild_salt_hauler_activity",
        "cohesive_group",
        "southwest_east_cape_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "white_sail_north_wild_reef_burrow_striker_activity",
        "solitary_roaming",
        "white_sail_north_wild_grounds",
        60,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "white_sail_north_wild_seacliff_basker_activity",
        "cohesive_group",
        "white_sail_north_wild_grounds",
        90,
        AggressionCondition("contact"),
    ),
    MonsterActivity(
        "white_sail_north_wild_shore_walker_activity",
        "solitary_roaming",
        "white_sail_north_wild_grounds",
        60,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "white_sail_north_wild_oyster_rack_creeper_activity",
        "cohesive_group",
        "white_sail_north_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "white_sail_north_wild_salt_hauler_activity",
        "cohesive_group",
        "white_sail_north_wild_grounds",
        90,
        AggressionCondition("passive"),
    ),
# South-west coast (southwest-coast-placement): activities of the compositions added to the landed port hinterland and corridor zones.
    MonsterActivity(
        "port_fishers_cove_hinterland_oyster_rack_creeper_activity",
        "cohesive_group",
        "port_fishers_cove_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_fishers_cove_hinterland_salt_hauler_activity",
        "cohesive_group",
        "port_fishers_cove_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_south_tide_hinterland_oyster_rack_creeper_activity",
        "cohesive_group",
        "port_south_tide_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_south_tide_hinterland_salt_hauler_activity",
        "cohesive_group",
        "port_south_tide_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_white_sail_hinterland_oyster_rack_creeper_activity",
        "cohesive_group",
        "port_white_sail_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "port_white_sail_hinterland_salt_hauler_activity",
        "cohesive_group",
        "port_white_sail_hinterland_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_01_salt_hauler_activity",
        "cohesive_group",
        "southwest_road_01_grounds",
        90,
        AggressionCondition("passive"),
    ),
    MonsterActivity(
        "southwest_road_02_salt_hauler_activity",
        "cohesive_group",
        "southwest_road_02_grounds",
        90,
        AggressionCondition("passive"),
    ),
# South-west coast (southwest-coast-placement): site activities.
    MonsterActivity(
        "salt_mound_soldier_mound_activity",
        "cohesive_group",
        "salt_mound_soldier_mound_grounds",
        90,
        AggressionCondition("defended_area", "salt_mound_soldier_mound_crust"),
    ),
    MonsterActivity(
        "tide_pool_elder_pool_activity",
        "cohesive_group",
        "tide_pool_elder_pool_grounds",
        90,
        AggressionCondition("defended_area", "tide_pool_elder_pool_deep_pool"),
    ),
    MonsterActivity(
        "seawall_den_holder_den_activity",
        "solitary_roaming",
        "seawall_den_holder_den_grounds",
        60,
        AggressionCondition("defended_area", "seawall_den_holder_den_burrow"),
    ),
    MonsterActivity(
        "salt_dike_holder_dike_activity",
        "cohesive_group",
        "salt_dike_holder_dike_grounds",
        90,
        AggressionCondition("defended_area", "salt_dike_holder_dike_warm_dike"),
    ),
    MonsterActivity(
        "reef_warden_cove_activity",
        "cohesive_group",
        "reef_warden_cove_grounds",
        90,
        AggressionCondition("defended_area", "reef_warden_cove_reef"),
    ),
    MonsterActivity(
        "sunken_anchor_boss_activity",
        "solitary_roaming",
        "sunken_anchor_boss_grounds",
        60,
        AggressionCondition("defended_area", "sunken_anchor_boss_wreck"),
    ),
)

_ACTIVITY_AREA_ROWS: dict[str, ActivityArea] = build_activity_area_registry(
    _ACTIVITY_AREA_DECLARATIONS
)
_MONSTER_ACTIVITY_ROWS: dict[str, MonsterActivity] = build_monster_activity_registry(
    _ACTIVITY_DECLARATIONS
)

# Shipped declarations must be valid the moment the module loads, so a typo can
# never produce a partially valid registry.
validate_activity_registries(_ACTIVITY_AREA_ROWS, _MONSTER_ACTIVITY_ROWS)

ACTIVITY_AREA_REGISTRY: MappingProxyType = MappingProxyType(_ACTIVITY_AREA_ROWS)
MONSTER_ACTIVITY_REGISTRY: MappingProxyType = MappingProxyType(
    _MONSTER_ACTIVITY_ROWS
)

__all__ = [
    "ACTIVITY_AREA_REGISTRY",
    "AGGRESSION_KINDS",
    "CLOCK_DAYPARTS",
    "MONSTER_ACTIVITY_POLICIES",
    "MONSTER_ACTIVITY_REGISTRY",
    "ActivityArea",
    "AggressionCondition",
    "MovementUnit",
    "MonsterActivity",
    "MonsterActivityRegistryError",
    "activity_area_problems",
    "build_activity_area_registry",
    "build_monster_activity_registry",
    "movement_units",
    "resolve_activity_area",
    "validate_activity_registries",
]
