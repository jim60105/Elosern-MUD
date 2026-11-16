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
provisioning and the lifecycle pass. The writer guards read it; no owner
decision does.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterator

from world.lore import monster_activity as lore_activity
from world.lore import monster_placement as lore_placement
from world.maps import regional_population
from world.maps.published import SourceMemo
from world.rules.sight import MAX_GROUND_SIGHT_RADIUS
from world.rules.surfaces import store_attribute

#: The unit of every room, and of every cell no authored rectangle covers.
RESIDUAL_UNIT = "~residual"

#: How far one player observes a settlement unit: the maximum ground sight a
#: rulebook policy can derive, so the answer can never be too narrow.
OBSERVATION_RADIUS = MAX_GROUND_SIGHT_RADIUS

#: The wilderness Attribute recording each unit's settled-through tick.
POPULATION_UNIT_CURSORS_ATTRIBUTE = "population_unit_cursors"

#: The named refusal of a scoped pass that would write outside its scope.
POPULATION_SCOPE_VIOLATION = "population_scope_violation"

#: The named refusal of a catch-up that would settle inside another transaction.
POPULATION_CATCH_UP_NESTED = "population_catch_up_nested"

#: The named refusal of a write into a unit behind the world tick.
POPULATION_UNIT_NOT_CURRENT = "population_unit_not_current"

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


#: Units of one resolved movable area, pinned to the unit index and the
#: published geography that classify its cells.
_AREA_UNITS = SourceMemo()


def _area_units(index: UnitIndex, area: Any) -> frozenset[str]:
    """Every unit one resolved movable area touches.

    A movable area holds hundreds of cells and every group names one, so
    resolving each cell again on every group scan made one scan cost seconds of
    reactor time. The activity owner answers one shared immutable tuple per
    resolved area, so the answer is kept by that tuple's identity; the memo
    holds the tuple itself, which rules out a recycled identity. Any other
    sequence is resolved without the memo.
    """
    from world.maps.geography import current as current_geography
    from world.rules.movement_edges import decode_location_ref

    def resolve() -> tuple[Any, frozenset[str]]:
        found: set[str] = set()
        for locator in area:
            unit = unit_of_location(index, decode_location_ref(locator))
            if unit is not None:
                found.add(unit)
        return area, frozenset(found)

    if type(area) is not tuple:
        return resolve()[1]
    return _AREA_UNITS.resolve((index, current_geography()), id(area), resolve)[1]


def group_units(index: UnitIndex, group: Any, journey: Any | None) -> frozenset[str]:
    """Every unit one group touches: home, position, journey, area and owner."""
    from world.maps import monster_activity

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
    # A group whose own decision cannot move it contributes no area unit: the
    # owner answers a lawful scheduled stay for every one of those bindings, so
    # it can never reach a cell outside the units its own record names.
    area = monster_activity.movable_area(group)
    if area:
        units |= _area_units(index, area)
    kind, key = group.home_owner
    if kind == "zone":
        unit = index.unit_of_zone.get(key)
        if unit is not None:
            units.add(unit)
    elif kind == "site":
        units.add(site_unit(index, key))
    return frozenset(units)


#: Every group's units for one activity record, pinned to the unit index, the
#: published geography and the record itself. The record is immutable and every
#: write replaces it, so its identity proves the answer current.
_GROUP_UNITS = SourceMemo()
_GROUP_UNITS_KEY = "group-units"


def group_units_map(index: UnitIndex, state: Any) -> Mapping[str, frozenset[str]]:
    """Every group's units, computed once per unchanged settlement record.

    Public because the scoped pass needs the same answers twice -- once for the
    closure and once for the groups it may settle -- and the cost note on
    :func:`unit_closure` forbids computing them twice.
    """
    from world.maps.geography import current as current_geography

    return _GROUP_UNITS.resolve(
        (index, current_geography(), state),
        _GROUP_UNITS_KEY,
        lambda: MappingProxyType(
            {
                group_id: group_units(
                    index, group, state.journeys.get(group.journey_id)
                )
                for group_id, group in state.groups.items()
            }
        ),
    )


def warm_group_units() -> None:
    """Resolve every group's units once so no later scan pays the first cost.

    A world with no provisioned population has nothing to scan. The answers are
    kept by :func:`_area_units`; nothing is written.
    """
    from world.maps import monster_activity

    wilderness = regional_population.live_wilderness()
    if wilderness is None or not regional_population.population_provisioned(
        wilderness
    ):
        return
    group_units_map(
        current_unit_index(), monster_activity.read_monster_activity(wilderness)
    )


def _closure_over(
    units_of: Mapping[str, frozenset[str]], seeds: Iterable[str]
) -> frozenset[str]:
    """The least fixed point of the closure rule over already computed units."""
    closure = set(seeds)
    group_ids = sorted(units_of)
    changed = True
    while changed:
        changed = False
        for group_id in group_ids:
            units = units_of[group_id]
            if not units or not closure.intersection(units):
                continue
            added = units - closure
            if added:
                closure.update(added)
                changed = True
    return frozenset(closure)


def unit_closure(
    index: UnitIndex, state: Any, seeds: Iterable[str]
) -> frozenset[str]:
    """Every unit reachable from ``seeds`` through groups that touch two.

    Each group's units are computed exactly once, before the fixed point starts,
    so the iterations only intersect sets. The answer never depends on the
    visit order, because the closure is the least fixed point of the rule. A
    scope build must not compute the same answers a second time: use
    :func:`group_units_map` and derive both the closure and the settled groups
    from it.
    """
    return _closure_over(group_units_map(index, state), seeds)


def all_units(index: UnitIndex) -> tuple[str, ...]:
    """Every settlement unit of one index, plus the residual unit, sorted."""
    return tuple(
        sorted(
            {RESIDUAL_UNIT}
            | set(index.unit_of_zone.values())
            | set(index.unit_of_area.values())
        )
    )


def closed_sets(
    index: UnitIndex, state: Any, seeds: Iterable[str]
) -> tuple[frozenset[str], ...]:
    """The distinct closed sets the given seeds resolve to, in unit order.

    Every seed resolves through the same closure rule a scoped pass applies, so
    distinct answers are disjoint and together they partition the units a
    whole-world pass would settle. The group units are computed once and every
    seed's closure derives from them, so resolving the whole index costs one
    group scan, not one per seed.
    """
    units_of = group_units_map(index, state)
    sets = {_closure_over(units_of, (seed,)) for seed in seeds}
    return tuple(sorted(sets, key=lambda units: min(units)))


def lagging_sets(
    wilderness: Any, now: int
) -> tuple[tuple[int, frozenset[str]], ...]:
    """Every closed set behind ``now``, as ``(cursor, units)`` sorted pairs.

    The cursor of a set is its lowest unit cursor: a set with unequal cursors
    is lawful and is settled from its lowest cursor. A record whose every unit
    of the index has settled through ``now`` answers with no set after one
    cursor read, without decoding the activity record.
    """
    from world.maps import monster_activity

    index = current_unit_index()
    units = all_units(index)
    cursors = read_unit_cursors(wilderness)
    if all(unit_cursor(cursors, unit_id) >= now for unit_id in units):
        return ()
    state = monster_activity.read_monster_activity(wilderness)
    pending: list[tuple[int, frozenset[str]]] = []
    for closed in closed_sets(index, state, units):
        cursor = min(unit_cursor(cursors, unit_id) for unit_id in closed)
        if cursor < now:
            pending.append((cursor, closed))
    return tuple(sorted(pending, key=lambda item: (item[0], min(item[1]))))


class PopulationScopeViolation(regional_population.RegionalPopulationError):
    """A scoped pass would write outside the units it may settle."""


class PopulationCatchUpNested(regional_population.RegionalPopulationError):
    """A catch-up that would settle units was reached inside another transaction.

    Its write would be a savepoint of that transaction: a later rollback of the
    enclosing block reverts the durable rows while every live cache keeps the
    settled values. Entry points call the catch-up before their own transaction,
    so reaching this refusal means a caller is nested and must be fixed.
    """


class PopulationUnitNotCurrent(regional_population.RegionalPopulationError):
    """A population write touches a settlement unit behind the world tick.

    The unit's history stops at its cursor, so a presence fact, protection or
    group written today would describe a state the unit never settled. The
    error names the first offending unit in sorted order and both ticks; the
    fix is a catch-up at the entry point that reached the writer, never a
    weakened guard.
    """


@dataclass(frozen=True, slots=True)
class PopulationScope:
    """The closed set of settlement units one scoped pass may settle."""

    units: frozenset[str]
    group_ids: frozenset[str]
    #: The initialized zones of the scope, sorted; ``behind`` narrows them.
    zone_keys: tuple[str, ...]
    site_keys: frozenset[str]
    #: Unit id -> the cursor the unit reported when the scope was built.
    start_ticks: Mapping[str, int]
    #: Zone key -> its unit, and site key -> its unit, resolved once.
    zone_units: Mapping[str, str]
    site_units: Mapping[str, str]

    def behind(self, tick: int, *, inclusive: bool = False) -> "PopulationScope":
        """This scope's zones and sites of the units that have not passed ``tick``.

        A unit whose cursor is ``tick`` has already committed that tick's zone
        note and site step, so both are skipped there. The pass's own first tick
        is the one exception (``inclusive``): a whole-world pass always settles
        its interval start, and a unit whose cursor is that start has not
        committed it yet. Every zone and site step is a no-op when it runs again
        on a tick whose work is already committed, which is what makes skipping
        a passed tick and re-running an inclusive one equally safe.
        """
        if inclusive:
            active = {
                unit for unit, start in self.start_ticks.items() if start <= tick
            }
        else:
            active = {
                unit for unit, start in self.start_ticks.items() if start < tick
            }
        return PopulationScope(
            self.units,
            self.group_ids,
            tuple(
                key for key in self.zone_keys if self.zone_units.get(key) in active
            ),
            frozenset(
                key for key in self.site_keys if self.site_units.get(key) in active
            ),
            self.start_ticks,
            self.zone_units,
            self.site_units,
        )

    def zone_in_step(self, zone_key: str, tick: int, *, inclusive: bool = False) -> bool:
        """Whether this scope's pass notes one zone at ``tick``."""
        unit = self.zone_units.get(zone_key)
        if unit is None:
            return False
        start = self.start_ticks.get(unit)
        return start is not None and (start <= tick if inclusive else start < tick)

    def covers(self, location: Any | None) -> bool:
        """Whether one locator lies inside the scope; no locator is covered."""
        if location is None:
            return True
        return unit_of_location(current_unit_index(), location) in self.units

    def covers_cell(self, cell: tuple[int, int]) -> bool:
        """Whether one wilderness cell lies inside the scope."""
        index = current_unit_index()
        return index.unit_of_cell(
            regional_population.cell_region(cell), cell
        ) in self.units


def build_scope(
    wilderness: Any, seeds: Iterable[str], *, cursors: UnitCursors | None = None
) -> PopulationScope:
    """The closed set of units reached from ``seeds`` and everything inside it.

    One activity-record read, one group-units computation and -- unless the
    caller already read it -- one cursor read for the whole pass; the answer is
    kept for the pass in :func:`scoped`. The per-unit record is read first, so a
    missing or malformed one refuses before any settlement work. A seed that
    names no unit of the authored geometry is dropped rather than recorded: a
    settlement must never persist a cursor for a unit the world does not have.
    """
    from world.maps import monster_activity
    from world.maps import monster_sites

    record = read_unit_cursors(wilderness) if cursors is None else cursors
    index = current_unit_index()
    state = monster_activity.read_monster_activity(wilderness)
    units_of = group_units_map(index, state)
    known = (
        set(index.unit_of_zone.values())
        | set(index.unit_of_area.values())
        | {RESIDUAL_UNIT}
    )
    units = _closure_over(units_of, [seed for seed in seeds if seed in known])
    zone_keys = tuple(
        key
        for key in regional_population.initialized_zone_keys(wilderness)
        if index.unit_of_zone.get(key) in units
    )
    # The owner's own binding decides which sites the pass settles, so the scope
    # names its sites from that one registry.
    site_keys = tuple(
        key
        for key in monster_sites.MONSTER_SITE_REGISTRY
        if site_unit(index, key) in units
    )
    return PopulationScope(
        units,
        frozenset(
            group_id
            for group_id, group_set in units_of.items()
            if group_set and group_set <= units
        ),
        zone_keys,
        frozenset(site_keys),
        MappingProxyType({unit: unit_cursor(record, unit) for unit in units}),
        MappingProxyType(
            {key: index.unit_of_zone[key] for key in zone_keys if key in index.unit_of_zone}
        ),
        MappingProxyType({key: site_unit(index, key) for key in site_keys}),
    )


def scope_start_tick(wilderness: Any, scope: PopulationScope) -> int:
    """The lowest cursor of one scope: the tick its pass starts from.

    Units of one closed set normally share one cursor; they differ only when a
    group linked them after they diverged (an escape into another unit, an
    explicit registration). That state is lawful, and the pass settles it by
    skipping the zone and site steps each unit has already passed.
    """
    if not scope.start_ticks:
        raise ValueError("a settlement scope names no settlement unit")
    return min(scope.start_ticks.values())


def concerned_units(index: UnitIndex, transition: Any) -> frozenset[str]:
    """Every unit one recorded presence transition concerns.

    The units of its before and after positions, of each non-empty home zone, and
    of each non-empty site marker. The site marker is part of the answer even
    though the requirement names positions and home zones: a site's clear
    decision reads its own members' committed loss evidence, so retiring that
    evidence before the site's unit has passed it would lose a fact a decision
    still needs. An empty answer is the residual unit.
    """
    units: set[str] = set()
    for presence in (transition.before, transition.after):
        position = presence.position
        if position is not None:
            cell = (position.x, position.y)
            units.add(
                index.unit_of_cell(regional_population.cell_region(cell), cell)
            )
        if presence.home_zone:
            unit = index.unit_of_zone.get(presence.home_zone)
            if unit is not None:
                units.add(unit)
        if presence.site_key:
            units.add(site_unit(index, presence.site_key))
    return frozenset(units) if units else frozenset({RESIDUAL_UNIT})


def units_around(index: UnitIndex, location: Any | None) -> frozenset[str]:
    """Every settlement unit inside the observation radius of one locator.

    A room, and the absence of a locator, observe only the residual unit. A
    wilderness locator observes the units of every cell of the square window
    ``OBSERVATION_RADIUS`` around it (non-negative coordinates only), so the
    answer is a superset of every derivation of ground sight.
    """
    if location is None or location.kind == "room":
        return frozenset({RESIDUAL_UNIT})
    units = {RESIDUAL_UNIT}
    x, y = location.x, location.y
    for dx in range(-OBSERVATION_RADIUS, OBSERVATION_RADIUS + 1):
        for dy in range(-OBSERVATION_RADIUS, OBSERVATION_RADIUS + 1):
            cell = (x + dx, y + dy)
            if cell[0] < 0 or cell[1] < 0:
                continue
            units.add(index.unit_of_cell(regional_population.cell_region(cell), cell))
    return frozenset(units)


#: The locations a running action announced it is about to enter.
_ANNOUNCED: list[Any] = []


@contextmanager
def announced_observation(locations: Iterable[Any]) -> Iterator[None]:
    """Add ``locations`` to the observed set for the duration of the block.

    Each entry is removed again on every exit path, so a failure inside the
    action cannot leave a later catch-up observing a place nothing announced.
    """
    announced = list(locations)
    target = _ANNOUNCED
    target.extend(announced)
    try:
        yield
    finally:
        for location in reversed(announced):
            for index in range(len(target) - 1, -1, -1):
                if target[index] is location:
                    del target[index]
                    break


def observed_units(wilderness: Any) -> frozenset[str]:
    """Every unit a player observes, or a running action announced it enters.

    A player character in a room observes nothing beyond the residual unit. A
    player position or an announced location on another wilderness map is not
    this world's observation.
    """
    from typeclasses.characters import PlayerCharacter
    from world.rules.movement_edges import (
        LocationRefError,
        MovementEdgeError,
        location_ref,
    )

    index = current_unit_index()
    map_name = getattr(wilderness, "db_key", None)
    units: set[str] = {RESIDUAL_UNIT}
    for player in PlayerCharacter.objects.all_family():
        try:
            location = location_ref(player)
        except (
            LocationRefError,
            MovementEdgeError,
        ):  # observability: ignore R2: an unrepresentable player position adds no unit, and the next command repairs it
            continue
        if location.kind == "room" or location.map != map_name:
            continue
        units |= units_around(index, location)
    for location in tuple(_ANNOUNCED):
        if location.kind == "room" or location.map != map_name:
            continue
        units |= units_around(index, location)
    return frozenset(units)


#: The scope of the settlement pass currently running, if any.
_ACTIVE_SCOPE: PopulationScope | None = None

#: The groups the running scoped pass may settle, including the ones it creates.
_ACTIVE_GROUPS: set[str] | None = None


def active_scope() -> PopulationScope | None:
    """The scope of the settlement pass currently running, or ``None``."""
    return _ACTIVE_SCOPE


def settling_group_ids(scope: PopulationScope | None) -> set[str] | None:
    """The groups ``scope`` may settle now; ``None`` settles every group.

    A group born inside the pass (an explicit site birth or an ordinary wave) is
    inside the scope by construction, because the writer refuses any group whose
    units it may not settle. It is therefore added to the running scope as it is
    created: a scope built before the pass cannot name a group that did not exist
    yet, and a group this pass created must still decide and pay its physiology
    within it.
    """
    if scope is None:
        return None
    live = _ACTIVE_GROUPS
    if live is None:
        return set(scope.group_ids)
    return live


def note_created_group(group_id: str) -> None:
    """Record one group the running scoped pass created; a no-op outside one."""
    groups = _ACTIVE_GROUPS
    if groups is not None:
        groups.add(group_id)


@contextmanager
def scoped(scope: PopulationScope | None) -> Iterator[None]:
    """Run the enclosed work as the settlement pass of ``scope``.

    A nested scope replaces the outer one for the duration of the block and the
    previous scope is restored on every exit path, so a failed pass can never
    leave a scope behind for a later caller.
    """
    global _ACTIVE_SCOPE, _ACTIVE_GROUPS
    previous = _ACTIVE_SCOPE
    previous_groups = _ACTIVE_GROUPS
    _ACTIVE_SCOPE = scope
    _ACTIVE_GROUPS = None if scope is None else set(scope.group_ids)
    try:
        yield
    finally:
        _ACTIVE_SCOPE = previous
        _ACTIVE_GROUPS = previous_groups


#: How many settlement passes are running; a pass never starts a nested catch-up.
_PASS_RUNNING = 0


def pass_running() -> bool:
    """Whether a settlement pass is running now."""
    return _PASS_RUNNING > 0


@contextmanager
def running_pass() -> Iterator[None]:
    """Mark the enclosed work as a settlement pass.

    Counted rather than boolean: an entry point reached from a pass must never
    start a nested catch-up, and a nested pass must not clear the outer one's
    marker when it exits.
    """
    global _PASS_RUNNING
    _PASS_RUNNING += 1
    try:
        yield
    finally:
        _PASS_RUNNING -= 1


def require_in_active_scope(location: Any | None) -> None:
    """Refuse a write to ``location`` that a running scoped pass does not cover."""
    scope = _ACTIVE_SCOPE
    if scope is None or scope.covers(location):
        return
    raise PopulationScopeViolation(
        f"{POPULATION_SCOPE_VIOLATION}: {location!r} lies outside the settled units"
    )


def require_units_in_active_scope(units: Iterable[str]) -> None:
    """Refuse a write touching a unit a running scoped pass does not cover."""
    scope = _ACTIVE_SCOPE
    if scope is None:
        return
    outside = frozenset(units) - scope.units
    if outside:
        raise PopulationScopeViolation(
            f"{POPULATION_SCOPE_VIOLATION}: units {sorted(outside)} lie outside "
            "the settled units"
        )


def require_cell_in_active_scope(cell: tuple[int, int]) -> None:
    """Refuse a write to ``cell`` that a running scoped pass does not cover."""
    scope = _ACTIVE_SCOPE
    if scope is None or scope.covers_cell(cell):
        return
    raise PopulationScopeViolation(
        f"{POPULATION_SCOPE_VIOLATION}: cell {cell!r} lies outside the settled units"
    )


def require_units_current(wilderness: Any, units: Iterable[str]) -> None:
    """Refuse a write touching a unit behind the current world tick.

    A settlement pass owns the settling it is doing, and a world without the
    population seed records no population state at all, so both answer without
    a read. Otherwise the unit cursor record is read once and the first
    offending unit in sorted order names itself with its cursor and the world
    tick. A missing or malformed record refuses through the owner's own error.

    ``units`` may be a generator: nothing is evaluated once the guard is inert,
    and an answer that names no unit reads no record.
    """
    if pass_running() or not regional_population.population_provisioned(wilderness):
        return
    touched = sorted(set(units))
    if not touched:
        return
    tick = regional_population.current_population_tick()
    cursors = read_unit_cursors(wilderness)
    for unit_id in touched:
        cursor = unit_cursor(cursors, unit_id)
        if cursor < tick:
            raise PopulationUnitNotCurrent(
                f"{POPULATION_UNIT_NOT_CURRENT}: unit {unit_id!r} settled through "
                f"{cursor} is behind the world tick {tick}"
            )


def require_current(wilderness: Any, locations: Iterable[Any | None]) -> None:
    """Refuse a write touching the unit of any non-null locator that is behind.

    The same silence as :func:`require_units_current`: a running pass and an
    unprovisioned world answer before the unit index or the cursor record is
    read. ``locations`` may be a generator for the same reason.
    """
    if pass_running() or not regional_population.population_provisioned(wilderness):
        return
    index = current_unit_index()
    require_units_current(
        wilderness,
        (
            unit
            for location in locations
            if (unit := unit_of_location(index, location)) is not None
        ),
    )


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


def all_units_current(cursors: UnitCursors, tick: int) -> bool:
    """Whether every unit one record names has already settled through ``tick``.

    The unlisted default covers every unit without its own entry, so the whole
    record is current exactly when the default and every listed value have
    reached ``tick``. A caller uses this to answer "nothing to settle" without
    resolving a closed set the settlement would leave untouched.
    """
    if cursors.default < tick:
        return False
    return all(value >= tick for value in cursors.units.values())


__all__ = [
    "OBSERVATION_RADIUS",
    "POPULATION_CATCH_UP_NESTED",
    "POPULATION_UNIT_CURSORS_ATTRIBUTE",
    "POPULATION_SCOPE_VIOLATION",
    "POPULATION_UNIT_NOT_CURRENT",
    "RESIDUAL_UNIT",
    "PopulationCatchUpNested",
    "PopulationScope",
    "PopulationScopeViolation",
    "PopulationUnitNotCurrent",
    "UnitCursors",
    "UnitIndex",
    "active_scope",
    "advance_unit_cursors",
    "all_units",
    "all_units_current",
    "announced_observation",
    "build_scope",
    "build_unit_index",
    "closed_sets",
    "concerned_units",
    "current_unit_index",
    "group_units",
    "group_units_map",
    "initialize_unit_cursors",
    "lagging_sets",
    "note_created_group",
    "observed_units",
    "pass_running",
    "read_unit_cursors",
    "require_current",
    "require_in_active_scope",
    "require_units_current",
    "require_units_in_active_scope",
    "running_pass",
    "scope_start_tick",
    "scoped",
    "settling_group_ids",
    "site_area_links",
    "site_unit",
    "unit_closure",
    "unit_cursor",
    "unit_of_location",
    "units_around",
    "warm_group_units",
    "write_unit_cursors",
    "zone_bound_areas",
]