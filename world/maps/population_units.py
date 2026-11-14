"""Settlement units: the independently settleable parts of one population.

A clock advance settles the whole monster population, so the cost of one player
action grows with the world. Settlement may be limited to the units one action
touches only when the parts of the world never read each other's state.

A settlement unit is one connected component of the authored geometry: a
region-bound activity area and a zone (or another area) share a unit exactly
when their rectangles overlap inside one region, or when a zone's or a site's
births can be bound to that area. A room, and a cell covered by neither, belong
to the residual unit.

Nothing here decides anything. The index is a pure function of the published
registries, and the per-unit cursor record is written only by fresh
provisioning and the lifecycle pass; no owner decision reads it yet.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from world.lore import monster_activity as lore_activity
from world.lore import monster_placement as lore_placement
from world.maps import regional_population
from world.maps.published import SourceMemo
from world.rules.surfaces import store_attribute

#: The unit of every room, and of every cell no authored rectangle covers.
RESIDUAL_UNIT = "~residual"

#: The wilderness Attribute recording each unit's settled-through tick.
POPULATION_UNIT_CURSORS_ATTRIBUTE = "population_unit_cursors"

_ZONE = "zone"
_AREA = "area"

#: The exact fields one stored cursor record carries.
_CURSOR_FIELDS = frozenset({"default", "units"})


def _overlaps(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> bool:
    """Whether two inclusive rectangles share at least one cell."""
    return (
        first[0] <= second[1]
        and second[0] <= first[1]
        and first[2] <= second[3]
        and second[2] <= first[3]
    )


def _contains(rectangle: tuple[int, int, int, int], cell: tuple[int, int]) -> bool:
    """Whether one inclusive rectangle contains one cell."""
    x, y = cell
    return (
        rectangle[0] <= x <= rectangle[1]
        and rectangle[2] <= y <= rectangle[3]
    )


class _Components:
    """Union-find over ``(kind, key)`` nodes."""

    __slots__ = ("_parent",)

    def __init__(self) -> None:
        self._parent: dict[tuple[str, str], tuple[str, str]] = {}

    def find(self, node: tuple[str, str]) -> tuple[str, str]:
        parent = self._parent
        parent.setdefault(node, node)
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != root:
            parent[node], node = root, parent[node]
        return root

    def union(self, first: tuple[str, str], second: tuple[str, str]) -> None:
        left = self.find(first)
        right = self.find(second)
        if left != right:
            self._parent[left] = right


@dataclass(frozen=True, slots=True)
class UnitIndex:
    """One immutable division of the authored geometry into settlement units."""

    unit_of_zone: Mapping[str, str]
    unit_of_area: Mapping[str, str]
    #: Region key -> ``(rectangle, unit id)``, sorted by ``(unit id, rectangle)``.
    rectangles: Mapping[str, tuple[tuple[tuple[int, int, int, int], str], ...]]

    def unit_of_cell(self, region_key: str | None, cell: tuple[int, int]) -> str:
        """The unit of one wilderness cell, or the residual unit.

        Rectangle overlap inside one region puts every rectangle that covers a
        given cell into one unit by construction, so the sorted scan order can
        never change the answer.
        """
        if region_key is None:
            return RESIDUAL_UNIT
        for rectangle, unit_id in self.rectangles.get(region_key, ()):
            if _contains(rectangle, cell):
                return unit_id
        return RESIDUAL_UNIT


def build_unit_index(
    zones: Mapping[str, Any],
    areas: Mapping[str, Any],
    bound_areas: Mapping[str, frozenset[str]],
    area_links: Iterable[frozenset[str]] = (),
) -> UnitIndex:
    """Resolve authored zones and region-bound areas into settlement units.

    Two nodes share a unit when their rectangles overlap inside one region, when
    a zone's births can be bound to the area (``bound_areas``), or when one site
    outside every zone binds both areas to each other (``area_links``). The unit
    identifier is the smallest zone key in the component, or the smallest area
    key when the component holds no zone.
    """
    components = _Components()
    nodes: list[tuple[str, str]] = []
    by_region: dict[str, list[tuple[tuple[int, int, int, int], tuple[str, str]]]] = {}
    for zone_key in sorted(zones):
        zone = zones[zone_key]
        node = (_ZONE, zone_key)
        components.find(node)
        nodes.append(node)
        for rectangle in zone.rectangles:
            by_region.setdefault(zone.region_key, []).append((rectangle, node))
    for area_key in sorted(areas):
        area = areas[area_key]
        if area.region_key is None:
            continue
        node = (_AREA, area_key)
        components.find(node)
        nodes.append(node)
        for rectangle in area.rectangles:
            by_region.setdefault(area.region_key, []).append((rectangle, node))
    for entries in by_region.values():
        for index, (rectangle, node) in enumerate(entries):
            for other, other_node in entries[index + 1 :]:
                if node != other_node and _overlaps(rectangle, other):
                    components.union(node, other_node)
    for zone_key in sorted(bound_areas):
        if zone_key not in zones:
            continue
        for area_key in sorted(bound_areas[zone_key]):
            area = areas.get(area_key)
            if area is None or area.region_key is None:
                continue
            components.union((_ZONE, zone_key), (_AREA, area_key))
    for group in area_links:
        linked = sorted(
            area_key
            for area_key in group
            if areas.get(area_key) is not None
            and areas[area_key].region_key is not None
        )
        for area_key in linked[1:]:
            components.union((_AREA, linked[0]), (_AREA, area_key))

    members: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for node in nodes:
        members.setdefault(components.find(node), []).append(node)
    unit_of_node: dict[tuple[str, str], str] = {}
    for group in members.values():
        zone_keys = sorted(key for kind, key in group if kind == _ZONE)
        area_keys = sorted(key for kind, key in group if kind == _AREA)
        unit_id = (
            f"{_ZONE}:{zone_keys[0]}"
            if zone_keys
            else f"{_AREA}:{area_keys[0]}"
        )
        for node in group:
            unit_of_node[node] = unit_id

    rectangles: dict[str, tuple[tuple[tuple[int, int, int, int], str], ...]] = {}
    for region_key, entries in by_region.items():
        rectangles[region_key] = tuple(
            sorted(
                ((rectangle, unit_of_node[node]) for rectangle, node in entries),
                key=lambda item: (item[1], item[0]),
            )
        )
    return UnitIndex(
        MappingProxyType(
            {zone_key: unit_of_node[(_ZONE, zone_key)] for zone_key in zones}
        ),
        MappingProxyType(
            {
                area_key: unit_of_node[(_AREA, area_key)]
                for area_key in areas
                if areas[area_key].region_key is not None
            }
        ),
        MappingProxyType(rectangles),
    )


def _binding_areas(activity_keys: Iterable[str]) -> set[str]:
    """The region-bound areas one binding sequence names; unknown ones bind none."""
    found: set[str] = set()
    for activity_key in activity_keys:
        activity = lore_activity.MONSTER_ACTIVITY_REGISTRY.get(activity_key)
        if activity is None:
            continue
        area = lore_activity.ACTIVITY_AREA_REGISTRY.get(activity.area_key)
        if area is None or area.region_key is None:
            continue
        found.add(area.key)
    return found


def _composition_areas(composition_key: str) -> set[str]:
    """The region-bound areas one zone pool row can birth a group into."""
    composition = lore_placement.ENCOUNTER_COMPOSITION_REGISTRY.get(
        composition_key
    )
    if composition is None:
        return set()
    return _binding_areas(lore_placement.composition_row_bindings(composition))


def _site_areas(site: Any) -> set[str]:
    """The region-bound areas one site's births can be bound to."""
    composition = lore_placement.ENCOUNTER_COMPOSITION_REGISTRY.get(
        site.composition_key
    )
    if composition is None:
        return set()
    return _binding_areas(
        lore_placement.composition_row_bindings(composition, site=site)
    )


def _zone_containing(zones: Mapping[str, Any], site: Any) -> str | None:
    """The smallest zone whose region and rectangles contain one site's cell.

    Every zone that matches already shares one unit with the others: their
    rectangles all cover that cell of that region.
    """
    matches = [
        zone_key
        for zone_key in sorted(zones)
        if zones[zone_key].region_key == site.region_key
        and any(
            _contains(rectangle, site.coordinates)
            for rectangle in zones[zone_key].rectangles
        )
    ]
    return matches[0] if matches else None


def zone_bound_areas() -> dict[str, frozenset[str]]:
    """Every zone's births' region-bound areas, read from the live registries."""
    zones = lore_placement.ECOLOGY_ZONE_REGISTRY
    bound: dict[str, set[str]] = {}
    for zone_key in sorted(zones):
        areas: set[str] = set()
        for weighted in zones[zone_key].pool:
            areas |= _composition_areas(weighted.composition_key)
        if areas:
            bound[zone_key] = areas
    for site_key in sorted(lore_placement.MONSTER_SITE_REGISTRY):
        site = lore_placement.MONSTER_SITE_REGISTRY[site_key]
        areas = _site_areas(site)
        if not areas:
            continue
        owner = _zone_containing(zones, site)
        if owner is None:
            continue
        bound.setdefault(owner, set()).update(areas)
    return {zone_key: frozenset(areas) for zone_key, areas in bound.items()}


def site_area_links() -> tuple[frozenset[str], ...]:
    """Areas that one site outside every zone binds to each other."""
    zones = lore_placement.ECOLOGY_ZONE_REGISTRY
    links: list[frozenset[str]] = []
    for site_key in sorted(lore_placement.MONSTER_SITE_REGISTRY):
        site = lore_placement.MONSTER_SITE_REGISTRY[site_key]
        areas = _site_areas(site)
        if len(areas) < 2 or _zone_containing(zones, site) is not None:
            continue
        links.append(frozenset(areas))
    return tuple(links)


#: The index of the currently published registries, pinned to their identity so
#: a swapped registry (a test or a republication) gets a fresh index.
_UNIT_INDEX = SourceMemo()
_UNIT_INDEX_KEY = "settlement-units"


def current_unit_index() -> UnitIndex:
    """The settlement-unit index of the currently published registries."""
    zones = lore_placement.ECOLOGY_ZONE_REGISTRY
    areas = lore_activity.ACTIVITY_AREA_REGISTRY
    activities = lore_activity.MONSTER_ACTIVITY_REGISTRY
    compositions = lore_placement.ENCOUNTER_COMPOSITION_REGISTRY
    sites = lore_placement.MONSTER_SITE_REGISTRY
    return _UNIT_INDEX.resolve(
        (zones, areas, activities, compositions, sites),
        _UNIT_INDEX_KEY,
        lambda: build_unit_index(
            zones, areas, zone_bound_areas(), site_area_links()
        ),
    )


def unit_of_location(index: UnitIndex, location: Any | None) -> str | None:
    """The unit of one locator: none for ``None``, residual for a room."""
    if location is None:
        return None
    if location.kind == "room":
        return RESIDUAL_UNIT
    cell = (location.x, location.y)
    return index.unit_of_cell(regional_population.cell_region(cell), cell)


def site_unit(index: UnitIndex, site_key: str) -> str:
    """The unit of one authored site's cell; an unknown key is residual."""
    site = lore_placement.MONSTER_SITE_REGISTRY.get(site_key)
    if site is None:
        return RESIDUAL_UNIT
    cell = site.coordinates
    return index.unit_of_cell(regional_population.cell_region(cell), cell)


def group_units(index: UnitIndex, group: Any, journey: Any | None) -> frozenset[str]:
    """Every unit one group touches: home, position, journey, area and owner."""
    from world.maps import monster_activity
    from world.rules.movement_edges import decode_location_ref

    units: set[str] = set()
    for location in (group.home, group.position):
        unit = unit_of_location(index, location)
        if unit is not None:
            units.add(unit)
    if journey is not None:
        for location in (journey.source, journey.destination):
            unit = unit_of_location(index, location)
            if unit is not None:
                units.add(unit)
    for locator in monster_activity.group_area(group):
        unit = unit_of_location(index, decode_location_ref(locator))
        if unit is not None:
            units.add(unit)
    kind, key = group.home_owner
    if kind == "zone":
        unit = index.unit_of_zone.get(key)
        if unit is not None:
            units.add(unit)
    elif kind == "site":
        units.add(site_unit(index, key))
    return frozenset(units)


def unit_closure(
    index: UnitIndex, state: Any, seeds: Iterable[str]
) -> frozenset[str]:
    """Every unit reachable from ``seeds`` through groups that touch two.

    Each group is visited in sorted identifier order; the answer does not depend
    on the order, because the closure is the least fixed point of the rule.
    """
    closure = set(seeds)
    groups = [state.groups[group_id] for group_id in sorted(state.groups)]
    changed = True
    while changed:
        changed = False
        for group in groups:
            units = group_units(
                index, group, state.journeys.get(group.journey_id)
            )
            if not closure.intersection(units):
                continue
            added = units - closure
            if added:
                closure.update(added)
                changed = True
    return frozenset(closure)


@dataclass(frozen=True, slots=True)
class UnitCursors:
    """One settled-through tick per unit, plus the unlisted default."""

    default: int
    units: Mapping[str, int]


def unit_cursor(cursors: UnitCursors, unit_id: str) -> int:
    """The settled-through tick of one settlement unit."""
    return cursors.units.get(unit_id, cursors.default)


def _malformed(detail: str) -> regional_population.MalformedPopulationState:
    return regional_population.MalformedPopulationState(
        f"{regional_population.MALFORMED_STATE}: {detail}"
    )


def _require_tick(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _malformed(f"{what} must be a non-negative integer, got {value!r}")
    return value


def _cursors_from_raw(raw: object) -> UnitCursors:
    """Validate one stored cursor record; every other shape refuses by name."""
    if not isinstance(raw, Mapping):
        raise _malformed(
            f"{POPULATION_UNIT_CURSORS_ATTRIBUTE!r} is missing or not a mapping"
        )
    if set(raw) != _CURSOR_FIELDS:
        raise _malformed(
            f"{POPULATION_UNIT_CURSORS_ATTRIBUTE!r} must carry exactly "
            f"{sorted(_CURSOR_FIELDS)}"
        )
    default = _require_tick(raw["default"], "default")
    raw_units = raw["units"]
    if not isinstance(raw_units, Mapping):
        raise _malformed(
            f"{POPULATION_UNIT_CURSORS_ATTRIBUTE!r}.units must be a mapping"
        )
    units: dict[str, int] = {}
    for unit_id, value in raw_units.items():
        if not isinstance(unit_id, str) or not unit_id:
            raise _malformed(
                f"unit identifier {unit_id!r} is not a nonempty string"
            )
        units[unit_id] = _require_tick(value, f"unit {unit_id!r}")
    return UnitCursors(default, MappingProxyType(units))


def _cursors_to_raw(cursors: UnitCursors) -> dict[str, object]:
    """The canonical stored form: sorted unit identifiers, no extra keys."""
    return {
        "default": cursors.default,
        "units": {
            unit_id: cursors.units[unit_id] for unit_id in sorted(cursors.units)
        },
    }


def read_unit_cursors(wilderness: Any) -> UnitCursors:
    """Read the per-unit settlement record; a missing or bad one refuses."""
    return _cursors_from_raw(
        wilderness.attributes.get(POPULATION_UNIT_CURSORS_ATTRIBUTE)
    )


def write_unit_cursors(wilderness: Any, cursors: UnitCursors) -> None:
    """Store the whole record once, through the shared attribute writer."""
    store_attribute(
        wilderness, POPULATION_UNIT_CURSORS_ATTRIBUTE, _cursors_to_raw(cursors)
    )


def initialize_unit_cursors(wilderness: Any, *, tick: int) -> None:
    """Write the fresh-provisioning record once; an existing one is kept."""
    if wilderness.attributes.has(POPULATION_UNIT_CURSORS_ATTRIBUTE):
        return
    write_unit_cursors(wilderness, UnitCursors(int(tick), MappingProxyType({})))


def _require_argument_tick(tick: object) -> int:
    if isinstance(tick, bool) or not isinstance(tick, int) or tick < 0:
        raise ValueError(f"tick must be a non-negative integer, got {tick!r}")
    return tick


def advance_unit_cursors(
    wilderness: Any, unit_ids: Iterable[str] | None, tick: int
) -> None:
    """Raise the listed units, or every unit, to ``tick``; never lower one.

    ``None`` records a whole-world pass: the default rises to ``tick`` and every
    listed unit rises with it, so no unit reports a tick below the default it is
    accounted against. Explicit unit ids raise only those units and leave the
    default alone. A record that cannot change is not rewritten.
    """
    target = _require_argument_tick(tick)
    cursors = read_unit_cursors(wilderness)
    if unit_ids is None:
        default = max(cursors.default, target)
        units = {
            unit_id: max(value, default)
            for unit_id, value in cursors.units.items()
        }
    else:
        default = cursors.default
        units = dict(cursors.units)
        for unit_id in unit_ids:
            if not isinstance(unit_id, str) or not unit_id:
                raise ValueError(
                    "a settlement unit identifier must be a nonempty string, "
                    f"got {unit_id!r}"
                )
            if target > units.get(unit_id, default):
                units[unit_id] = target
    if default == cursors.default and units == dict(cursors.units):
        return
    write_unit_cursors(wilderness, UnitCursors(default, units))


__all__ = [
    "POPULATION_UNIT_CURSORS_ATTRIBUTE",
    "RESIDUAL_UNIT",
    "UnitCursors",
    "UnitIndex",
    "advance_unit_cursors",
    "build_unit_index",
    "current_unit_index",
    "group_units",
    "initialize_unit_cursors",
    "read_unit_cursors",
    "site_area_links",
    "site_unit",
    "unit_closure",
    "unit_cursor",
    "unit_of_location",
    "write_unit_cursors",
    "zone_bound_areas",
]