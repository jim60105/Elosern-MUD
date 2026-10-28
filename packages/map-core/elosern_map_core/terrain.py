"""Deterministic wilderness terrain rules over an explicit terrain definition.

The wilderness is a square frame of one-kilometre cells. A
:class:`TerrainDefinition` carries every authored input the rules read: the
frame size, the mainland boundary ring, the meandering northern forest edge, the
inland waterway routes and fords, the bending central ridge with its pass
windows, the coastal band limit, the mountain corridor width, and the terrain
flavour variants per region key. Nothing here reads a game registry, a database,
a clock or a random source.

Ownership of derived values and caches
--------------------------------------
Every derived table (:attr:`TerrainDefinition.forest_edge_rows`,
``border_river_rows``, the rasterized waterway cell set, the region search boxes
and the derived national borders) belongs to the definition instance that
produced it. Two definitions never share a table, so classifying world B can
never reuse a world-A value, and the live anchor-footprint set stays a caller
input (:func:`is_valid_wilderness_cell`) rather than hidden module state.

Units: cells are logical one-kilometre areas; the land test samples a cell's
centre (``x + 0.5``, ``y + 0.5``) against the kilometre boundary ring. Region
keys, the compass-free ridge geometry and terrain flavour text are authored
vocabulary supplied by the definition.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import Iterable, Mapping

from .geometry import Point, is_on_mainland, is_within_frame

#: The seven terrain region keys a classification can return.
REGION_KEYS = frozenset(
    {
        "north_deep_forest",
        "central_mountains",
        "eastern_plains",
        "southeast_coast",
        "southwest_coast",
        "northwest_highland_forest",
        "western_hills_valleys",
    }
)

#: The ridge bend walks this many phases, so its centre moves by at most two
#: steps either side of ``ridge_base_x``. The phase count is part of the
#: algorithm, not a per-world setting: every derivation that needs the ridge's
#: horizontal extent uses the same constant.
RIDGE_BEND_PHASES = 5

#: Multipliers of the closed-form flavour selector (``(x, y)`` alone).
TERRAIN_FLAVOR_MULTIPLIER_X = 92821
TERRAIN_FLAVOR_MULTIPLIER_Y = 68917


def _int(value: object, label: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    return value


def _point(value: object, label: str) -> Point:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or isinstance(value[0], bool)
        or isinstance(value[1], bool)
        or not isinstance(value[0], int)
        or not isinstance(value[1], int)
    ):
        raise ValueError(f"{label} must be an integer (x, y) pair")
    return value


def _points(values: Iterable[object], label: str, *, minimum_length: int = 1) -> tuple[Point, ...]:
    points = tuple(_point(value, label) for value in values)
    if len(points) < minimum_length:
        raise ValueError(f"{label} needs at least {minimum_length} point(s)")
    return points


def _routes(
    routes: Mapping[str, Iterable[object]], label: str
) -> Mapping[str, tuple[Point, ...]]:
    if not isinstance(routes, Mapping) or not routes:
        raise ValueError(f"{label} must be a non-empty mapping")
    frozen: dict[str, tuple[Point, ...]] = {}
    for key, points in routes.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{label} keys must be non-empty strings")
        frozen[key] = _points(points, f"{label}[{key!r}]", minimum_length=2)
    return MappingProxyType(frozen)


def _fords(fords: Mapping[str, Iterable[object]], label: str) -> Mapping[str, tuple[Point, ...]]:
    if not isinstance(fords, Mapping):
        raise ValueError(f"{label} must be a mapping")
    frozen: dict[str, tuple[Point, ...]] = {}
    for key, cells in fords.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{label} keys must be non-empty strings")
        frozen[key] = _points(cells, f"{label}[{key!r}]", minimum_length=0)
    return MappingProxyType(frozen)


def _strictly_monotone(points: tuple[Point, ...], *, increasing: bool, label: str) -> None:
    steps = [
        following[0] - current[0] for current, following in zip(points, points[1:])
    ]
    if not all(step > 0 if increasing else step < 0 for step in steps):
        direction = "increasing" if increasing else "decreasing"
        raise ValueError(f"{label} columns must be strictly {direction}")


def _column_table(points: tuple[Point, ...], frame_cells: int) -> tuple[int, ...]:
    return tuple(route_row_at(points, x) for x in range(frame_cells))


def route_row_at(points: tuple[Point, ...], x: int) -> int:
    """The row an x-monotone, shallow route occupies in column ``x``.

    Uses the rasterizer's own integer arithmetic, so for a route whose segments
    all satisfy ``|dx| >= |dy|`` the result is the exact rasterized cell of that
    column. Outside the route's X span the nearest end vertex's row continues
    straight (the derived extension that closes a line against the ridge or the
    frame edge).
    """

    for start, end in zip(points, points[1:]):
        x0, y0 = start
        x1, y1 = end
        if min(x0, x1) <= x <= max(x0, x1):
            steps = abs(x1 - x0)
            if steps == 0:
                return y0
            index = abs(x - x0)
            return y0 + (y1 - y0) * index // steps
    west, east = sorted((points[0], points[-1]))
    return west[1] if x < west[0] else east[1]


def rasterize_segment(start: Point, end: Point) -> set[Point]:
    """Every integer cell on the straight segment between two cell points.

    Deterministic integer interpolation (no floats, no library): the walk takes
    one step per axis major, so the rasterized waterway is continuous.
    """

    x0, y0 = start
    x1, y1 = end
    steps = max(abs(x1 - x0), abs(y1 - y0))
    if steps == 0:
        return {(x0, y0)}
    return {
        (x0 + (x1 - x0) * index // steps, y0 + (y1 - y0) * index // steps)
        for index in range(steps + 1)
    }


def rasterize_routes(routes: Mapping[str, tuple[Point, ...]]) -> frozenset[Point]:
    """Every cell covered by the given polyline routes."""

    cells: set[Point] = set()
    for points in routes.values():
        for start, end in zip(points, points[1:]):
            cells |= rasterize_segment(start, end)
    return frozenset(cells)


@dataclass(frozen=True)
class NationalBorder:
    """One displayed national border line in wilderness cell coordinates.

    ``nation_keys`` is the sorted pair the line separates.
    """

    nation_keys: tuple[str, str]
    points: tuple[Point, ...]


@dataclass(frozen=True)
class TerrainDefinition:
    """Every authored input the deterministic terrain rules read.

    Construction validates the inputs and freezes them: mapping fields are
    copied into read-only views and point sequences into tuples, so mutating the
    caller's containers afterwards cannot change a classification. The forest
    edge must be X-increasing and the border river X-decreasing, which is what
    makes their per-column row tables single-valued.
    """

    frame_cells: int
    mainland_boundary_km: tuple[Point, ...]
    forest_edge: tuple[Point, ...]
    waterway_routes: Mapping[str, tuple[Point, ...]]
    waterway_fords: Mapping[str, tuple[Point, ...]]
    border_river_key: str
    ridge_base_x: int
    ridge_period: int
    ridge_step: int
    ridge_min_x: int
    ridge_max_x: int
    ridge_north_limit: int
    ridge_passes: tuple[tuple[int, int], ...]
    coastal_y_max: int
    mountain_corridor_half_width: int
    region_flavors: Mapping[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "frame_cells", _int(self.frame_cells, "frame_cells", minimum=1)
        )
        boundary = tuple(self.mainland_boundary_km)
        if len(boundary) < 3:
            raise ValueError("mainland_boundary_km needs at least three vertices")
        object.__setattr__(
            self,
            "mainland_boundary_km",
            tuple(_point(vertex, "boundary vertex") for vertex in boundary),
        )
        edge = _points(self.forest_edge, "forest_edge", minimum_length=2)
        _strictly_monotone(edge, increasing=True, label="forest_edge")
        object.__setattr__(self, "forest_edge", edge)
        object.__setattr__(
            self, "waterway_routes", _routes(self.waterway_routes, "waterway_routes")
        )
        object.__setattr__(
            self, "waterway_fords", _fords(self.waterway_fords, "waterway_fords")
        )
        if not isinstance(self.border_river_key, str) or not self.border_river_key:
            raise ValueError("border_river_key must be a non-empty string")
        if self.border_river_key not in self.waterway_routes:
            raise ValueError(
                f"waterway_routes has no border river {self.border_river_key!r}"
            )
        _strictly_monotone(
            self.waterway_routes[self.border_river_key],
            increasing=False,
            label=f"waterway_routes[{self.border_river_key!r}]",
        )
        for name in (
            "ridge_base_x",
            "ridge_period",
            "ridge_step",
            "ridge_min_x",
            "ridge_max_x",
            "ridge_north_limit",
            "coastal_y_max",
            "mountain_corridor_half_width",
        ):
            object.__setattr__(self, name, _int(getattr(self, name), name))
        if self.ridge_period < 1 or self.ridge_step < 1:
            raise ValueError("ridge_period and ridge_step must be positive")
        if self.ridge_min_x > self.ridge_max_x:
            raise ValueError("ridge_min_x must not exceed ridge_max_x")
        # Each window is re-built as a tuple: a caller-supplied list must not
        # stay reachable, or a later mutation would silently open or close the
        # ridge wall of an already constructed definition.
        passes: list[tuple[int, int]] = []
        for window in self.ridge_passes:
            if not isinstance(window, (tuple, list)) or len(window) != 2:
                raise ValueError(f"ridge pass window {window!r} must be two rows")
            low, high = window
            _int(low, "ridge pass low")
            _int(high, "ridge pass high")
            if low > high:
                raise ValueError(f"ridge pass window {window!r} is inverted")
            passes.append((low, high))
        object.__setattr__(self, "ridge_passes", tuple(passes))

        flavors = self.region_flavors
        if not isinstance(flavors, Mapping):
            raise ValueError("region_flavors must be a mapping")
        missing = REGION_KEYS - set(flavors)
        if missing:
            raise ValueError(
                f"region_flavors is missing region keys {sorted(missing)}"
            )
        frozen_flavors: dict[str, tuple[str, ...]] = {}
        for key, variants in flavors.items():
            if not isinstance(key, str) or not key:
                raise ValueError("region_flavors keys must be non-empty strings")
            normalized = tuple(variants)
            if not normalized or not all(isinstance(text, str) for text in normalized):
                raise ValueError(f"region_flavors[{key!r}] needs strings")
            frozen_flavors[key] = normalized
        object.__setattr__(self, "region_flavors", MappingProxyType(frozen_flavors))

        waterway_cells = rasterize_routes(self.waterway_routes) - frozenset(
            cell for fords in self.waterway_fords.values() for cell in fords
        )
        object.__setattr__(self, "_waterway_cells", waterway_cells)
        object.__setattr__(
            self, "_forest_edge_rows", _column_table(edge, self.frame_cells)
        )
        object.__setattr__(
            self,
            "_border_river_rows",
            _column_table(self.waterway_routes[self.border_river_key], self.frame_cells),
        )

    # -- derived tables ---------------------------------------------------
    @property
    def waterway_cells(self) -> frozenset[Point]:
        """Rasterized inland water cells, fords excluded."""

        return self._waterway_cells

    @cached_property
    def region_search_boxes(self) -> Mapping[str, tuple[int, int, int, int]]:
        """Authored enumeration windows ``(x_min, x_max, y_min, y_max)``.

        They are a superset of each region's cells (the classifier still
        decides membership) so sparse-index consumers enumerate only the
        relevant band instead of the whole frame.
        """

        max_x = self.frame_cells - 1
        max_y = self.frame_cells - 1
        edge_y_min = min(y for _, y in self.forest_edge)
        edge_y_max = max(y for _, y in self.forest_edge)
        river_y_min = min(y for _, y in self.waterway_routes[self.border_river_key])
        river_y_max = max(y for _, y in self.waterway_routes[self.border_river_key])
        bend_extent = (RIDGE_BEND_PHASES // 2) * self.ridge_step
        return MappingProxyType(
            {
                "north_deep_forest": (0, max_x, edge_y_min, max_y),
                "central_mountains": (
                    self.ridge_base_x - bend_extent - self.mountain_corridor_half_width,
                    self.ridge_base_x + bend_extent + self.mountain_corridor_half_width,
                    0,
                    edge_y_max - 1,
                ),
                "eastern_plains": (0, max_x, self.coastal_y_max + 1, edge_y_max - 1),
                "southeast_coast": (0, max_x, 0, self.coastal_y_max),
                "southwest_coast": (0, max_x, 0, self.coastal_y_max),
                "northwest_highland_forest": (
                    0,
                    max_x,
                    river_y_min + 1,
                    edge_y_max - 1,
                ),
                "western_hills_valleys": (0, max_x, self.coastal_y_max + 1, river_y_max),
            }
        )

    @cached_property
    def national_borders(self) -> tuple[NationalBorder, ...]:
        """The displayed national borders derived from the ridge and the river."""

        river = self.waterway_routes[self.border_river_key]
        source_x, junction_y = river[0]
        junction = (ridge_center_x(self, junction_y), junction_y)
        river_line = tuple(reversed(river)) + (
            (junction,) if junction[0] != source_x else ()
        )
        ridge_start = next(
            (
                y
                for y in range(self.frame_cells)
                if is_land_cell(self, (ridge_center_x(self, y), y))
            ),
            None,
        )
        if ridge_start is None:
            raise ValueError("the ridge centre line never crosses land in this frame")
        ridge_end = junction_y
        while (ridge_end + 1) < forest_edge_row(self, ridge_center_x(self, ridge_end + 1)):
            ridge_end += 1
        return (
            NationalBorder(("altoria", "valhalla"), river_line),
            NationalBorder(
                ("altoria", "grandia"), ridge_polyline(self, ridge_start, junction_y)
            ),
            NationalBorder(
                ("grandia", "valhalla"), ridge_polyline(self, junction_y, ridge_end)
            ),
        )

    # -- lookups ----------------------------------------------------------
    def _clamped_column(self, x: int) -> int:
        return min(max(x, 0), self.frame_cells - 1)

    @property
    def max_x(self) -> int:
        return self.frame_cells - 1

    @property
    def max_y(self) -> int:
        return self.frame_cells - 1


def forest_edge_row(definition: TerrainDefinition, x: int) -> int:
    """The northern deep forest's first row in column ``x``."""

    return definition._forest_edge_rows[definition._clamped_column(x)]


def border_river_row(definition: TerrainDefinition, x: int) -> int:
    """The border river's row in column ``x`` (or its derived extension).

    East of the source the river's source row continues as the watershed line
    to the summit ridge; west of the mouth the mouth row continues to sea.
    """

    return definition._border_river_rows[definition._clamped_column(x)]


def ridge_center_x(definition: TerrainDefinition, y: int) -> int:
    """The summit ridge's X centre at row ``y`` (a deterministic bend)."""

    bend = (y // definition.ridge_period) % RIDGE_BEND_PHASES - (
        RIDGE_BEND_PHASES // 2
    )
    return definition.ridge_base_x + bend * definition.ridge_step


def ridge_span(definition: TerrainDefinition, y: int) -> tuple[int, int]:
    """The ridge's inclusive X span at row ``y``.

    Spanning every column between this row's centre and the next row's centre
    keeps the wall 8-connected, so no diagonal gap can slip through it.
    """

    current = ridge_center_x(definition, y)
    following = ridge_center_x(definition, y + 1)
    return (min(current, following), max(current, following))


def is_closed_ridge_cell(definition: TerrainDefinition, coordinates: Point) -> bool:
    """Whether ``(x, y)`` is an impassable summit-ridge/cliff cell.

    The ridge bends through the central corridor up to its northern limit; the
    authored pass windows are open ground, so land crossings require one of
    them.
    """

    x, y = coordinates
    if not (definition.ridge_min_x <= x <= definition.ridge_max_x):
        return False
    if y >= definition.ridge_north_limit:
        return False
    if any(low <= y <= high for low, high in definition.ridge_passes):
        return False
    low, high = ridge_span(definition, y)
    return low <= x <= high


def is_inland_water_cell(definition: TerrainDefinition, coordinates: Point) -> bool:
    """Whether ``(x, y)`` is impassable river water (a ford is not water)."""

    return coordinates in definition.waterway_cells


def is_land_cell(definition: TerrainDefinition, coordinates: Point) -> bool:
    """Whether the cell's centre lies inside the mainland polygon."""

    x, y = coordinates
    return is_on_mainland(definition.mainland_boundary_km, x + 0.5, y + 0.5)


def mainland_row_intervals(definition: TerrainDefinition, y: int) -> list[tuple[int, int]]:
    """Inclusive X intervals of land cells in row ``y``.

    The even-odd crossings of the row's centre line give the candidate ends;
    each end is then corrected against :func:`is_land_cell` (the single land
    rule), so a floating-point edge case can only move an end onto the rule's
    own answer, never disagree with it.
    """
    north = y + 0.5
    vertices = definition.mainland_boundary_km
    crossings: list[float] = []
    for index, (start_east, start_north) in enumerate(vertices):
        end_east, end_north = vertices[(index + 1) % len(vertices)]
        if (start_north > north) == (end_north > north):
            continue
        crossings.append(
            (end_east - start_east) * (north - start_north) / (end_north - start_north)
            + start_east
        )
    crossings.sort()
    intervals: list[tuple[int, int]] = []
    for west, east in zip(crossings[::2], crossings[1::2]):
        low = max(math.ceil(west - 0.5), 0)
        high = min(math.floor(east - 0.5), definition.max_x)
        while low <= high and not is_land_cell(definition, (low, y)):
            low += 1
        while low > 0 and is_land_cell(definition, (low - 1, y)):
            low -= 1
        while high >= low and not is_land_cell(definition, (high, y)):
            high -= 1
        while high < definition.max_x and is_land_cell(definition, (high + 1, y)):
            high += 1
        if low <= high:
            intervals.append((low, high))
    # A corrected end can grow into its neighbour interval; merge so every
    # land cell of the row belongs to exactly one interval.
    merged: list[tuple[int, int]] = []
    for low, high in intervals:
        if merged and low <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return merged


def is_passable_terrain(definition: TerrainDefinition, coordinates: Point) -> bool:
    """Whether the cell is walkable ground (not a ridge wall or water)."""

    return not is_closed_ridge_cell(
        definition, coordinates
    ) and not is_inland_water_cell(definition, coordinates)


def is_walkable_cell(definition: TerrainDefinition, coordinates: Point) -> bool:
    """Whether ``(x, y)`` is in-frame, mainland and passable on foot."""

    return (
        is_within_frame(definition.frame_cells, coordinates)
        and is_land_cell(definition, coordinates)
        and is_passable_terrain(definition, coordinates)
    )


def is_valid_wilderness_cell(
    definition: TerrainDefinition,
    footprint_cells: Iterable[Point],
    coordinates: Point,
) -> bool:
    """In-frame, land-side, passable terrain, and not an anchor footprint cell."""

    return is_walkable_cell(definition, coordinates) and coordinates not in footprint_cells


def region_for_coordinates(definition: TerrainDefinition, x: int, y: int) -> str:
    """Return the terrain region key for ``(x, y)``.

    Pure integer partition over the two coordinates alone. Every cell inside
    the frame (including sea cells) resolves to a registered region. The central
    mountain region follows the authored bending corridor rather than a
    rectangular band.
    """

    if y >= forest_edge_row(definition, x):
        return "north_deep_forest"
    centre = ridge_center_x(definition, y)
    if abs(x - centre) <= definition.mountain_corridor_half_width:
        return "central_mountains"
    if x > centre:  # east of the mountains
        return "southeast_coast" if y <= definition.coastal_y_max else "eastern_plains"
    # x < centre -- west of the mountains; the border river divides the
    # western hills and valleys from the northwest highland forest.
    if y <= definition.coastal_y_max:
        return "southwest_coast"
    if y > border_river_row(definition, x):
        return "northwest_highland_forest"
    return "western_hills_valleys"


def nominal_nation_for_coordinates(definition: TerrainDefinition, x: int, y: int) -> str:
    """Return the one nation that nominally claims ``(x, y)``.

    East of the summit ridge is ``grandia`` (the ridge's centre line continues
    north of its own limit through the deep forest); west of it, the border
    river divides ``altoria`` (the river row and south) from ``valhalla``
    (north). Region keys stay terrain: the mountain and deep-forest regions span
    several claims. Pure integer arithmetic.
    """

    if x > ridge_center_x(definition, y):
        return "grandia"
    if y <= border_river_row(definition, x):
        return "altoria"
    return "valhalla"


def ridge_polyline(
    definition: TerrainDefinition, y_start: int, y_end: int
) -> tuple[Point, ...]:
    """The ridge centre line from ``y_start`` to ``y_end`` (inclusive rows)."""

    points = [(ridge_center_x(definition, y_start), y_start)]
    for y in range(y_start, y_end):
        here, following = ridge_center_x(definition, y), ridge_center_x(
            definition, y + 1
        )
        if here != following:
            points.extend(((here, y), (following, y + 1)))
    points.append((ridge_center_x(definition, y_end), y_end))
    deduplicated: list[Point] = []
    for point in points:
        if not deduplicated or deduplicated[-1] != point:
            deduplicated.append(point)
    return tuple(deduplicated)


def terrain_description(definition: TerrainDefinition, x: int, y: int) -> str:
    """Return one deterministic flavour variant for the region at ``(x, y)``.

    Pure closed-form integer arithmetic on the two coordinates alone -- no RNG,
    no LLM, no DB read. The multipliers are deliberately large odd numbers
    purely to spread adjacent coordinates across variants.
    """

    variants = definition.region_flavors[region_for_coordinates(definition, x, y)]
    index = (
        x * TERRAIN_FLAVOR_MULTIPLIER_X + y * TERRAIN_FLAVOR_MULTIPLIER_Y
    ) % len(variants)
    return variants[index]


__all__ = [
    "NationalBorder",
    "REGION_KEYS",
    "RIDGE_BEND_PHASES",
    "TerrainDefinition",
    "border_river_row",
    "forest_edge_row",
    "is_closed_ridge_cell",
    "is_inland_water_cell",
    "is_land_cell",
    "is_passable_terrain",
    "is_valid_wilderness_cell",
    "is_walkable_cell",
    "nominal_nation_for_coordinates",
    "rasterize_routes",
    "rasterize_segment",
    "region_for_coordinates",
    "ridge_center_x",
    "ridge_polyline",
    "ridge_span",
    "route_row_at",
    "terrain_description",
]
