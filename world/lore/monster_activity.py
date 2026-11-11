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
