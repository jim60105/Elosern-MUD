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
from dataclasses import dataclass, field
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

#: Every nation identifier :func:`nominal_nation_for_coordinates` can return,
#: sorted. The classifier owns this vocabulary; a partition snapshot declares it.
NATION_KEYS = ("altoria", "grandia", "valhalla")

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


def _route_centre(points: tuple[Point, ...], y: int) -> int:
    """The interpolated centre X of an authored route at row ``y``.

    Integer half-up interpolation inside each segment (the same rule for
    negative dx), then the nearest endpoint's X continues straight outside the
    route's Y span. Routes are validated strictly Y-increasing with
    ``abs(dx) <= dy``, so one row owns exactly one centre.
    """

    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if y0 <= y <= y1:
            dy = y1 - y0
            if dy == 0:
                return x0
            return x0 + ((x1 - x0) * (y - y0) + dy // 2) // dy
    return points[0][0] if y < points[0][1] else points[-1][0]


def _route_centres(points: tuple[Point, ...]) -> tuple[int, ...]:
    """One immutable centre X per active row of a route, from its first to last."""

    return tuple(
        _route_centre(points, y) for y in range(points[0][1], points[-1][1] + 1)
    )


def _closure(centres: tuple[int, ...], index: int) -> tuple[int, int]:
    """The inclusive wall span closing row ``index`` toward the next active row.

    The terminal active row joins the current centre to itself.
    """

    current = centres[index]
    following = centres[index + 1] if index + 1 < len(centres) else current
    return (min(current, following), max(current, following))


def _merge_spans(spans: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    """Sort spans and merge overlapping or touching ones (never bounding fill)."""

    merged: list[tuple[int, int]] = []
    for low, high in sorted(spans):
        if merged and low <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return tuple(merged)


def _wall_run_polyline(
    closure: tuple[tuple[int, int], ...], indices: range, base_y: int
) -> tuple[Point, ...]:
    """A physical wall run as a polyline of each closed row's span endpoints.

    Physical previews use raster closure spans (the cells that actually block),
    never the authored presentation centre line.
    """

    points: list[Point] = []
    for index in indices:
        low, high = closure[index]
        y = base_y + index
        for x in (low, high):
            point = (x, y)
            if not points or points[-1] != point:
                points.append(point)
    return tuple(points)


@dataclass(frozen=True)
class NationalBorder:
    """One displayed national border line in wilderness cell coordinates.

    ``nation_keys`` is the sorted pair the line separates.
    """

    nation_keys: tuple[str, str]
    points: tuple[Point, ...]


def _validate_ridge_route(
    points: tuple[Point, ...], label: str, frame_cells: int
) -> None:
    """One authored crest route: Y-increasing, shallow, wholly in-frame.

    The frame check runs before any row table is allocated, so a tiny document
    naming an absurd row cannot exhaust memory.
    """

    for previous, current in zip(points, points[1:]):
        if current[1] <= previous[1]:
            raise ValueError(f"{label} rows must strictly increase")
        if abs(current[0] - previous[0]) > current[1] - previous[1]:
            raise ValueError(f"{label} must move at most one column per row")
    for cell in points:
        if not is_within_frame(frame_cells, cell):
            raise ValueError(f"{label} must stay inside the frame")


def _validate_ridge_relations(
    river: tuple[Point, ...],
    stem: tuple[Point, ...],
    branches: Mapping[str, tuple[Point, ...]],
    passes: tuple[tuple[int, int], ...],
) -> None:
    """Semantic route relations shared by the model and candidate diagnostics."""

    source_x = river[0][0]
    if source_x != max(x for x, _ in river):
        raise ValueError("the border river must start at its easternmost vertex")
    centres = _route_centres(stem)
    if any(centre <= source_x for centre in centres):
        raise ValueError(
            "every active ridge stem centre must lie strictly east of the "
            "border river source"
        )
    if not branches:
        return
    crotch_x, crotch_y = stem[-1]
    if any(low <= crotch_y <= high for low, high in passes):
        raise ValueError("the shared ridge crotch cannot be a pass window")
    for name, route in branches.items():
        if route[0] != (crotch_x, crotch_y):
            raise ValueError(
                f"ridge branch {name!r} must start at the stem's last point"
            )
        if route[-1][1] <= crotch_y:
            raise ValueError(f"ridge branch {name!r} must end north of the crotch")
    if branches["west"][-1][0] >= crotch_x:
        raise ValueError("the west ridge branch tip must lie west of the crotch")
    if branches["east"][-1][0] <= crotch_x:
        raise ValueError("the east ridge branch tip must lie east of the crotch")
    west = _route_centres(branches["west"])
    east = _route_centres(branches["east"])
    separated = False
    for index in range(min(len(west), len(east))):
        if west[index] > east[index]:
            raise ValueError("the paired ridge branches cross")
        west_span = _closure(west, index)
        east_span = _closure(east, index)
        if west_span[1] < east_span[0]:
            separated = True
        elif separated:
            raise ValueError("the paired ridge branches rejoin after separating")
    if not separated:
        raise ValueError("the paired ridge branches never separate")


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
    ridge_stem: tuple[Point, ...]
    ridge_passes: tuple[tuple[int, int], ...]
    coastal_y_max: int
    mountain_corridor_half_width: int
    region_flavors: Mapping[str, tuple[str, ...]]
    #: Optional exactly-paired west/east arm routes. Absent means no arms; the
    #: mapping is frozen on construction and never falls back to a formula.
    ridge_branches: Mapping[str, tuple[Point, ...]] = field(default_factory=dict)

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
        for name in ("coastal_y_max", "mountain_corridor_half_width"):
            object.__setattr__(self, name, _int(getattr(self, name), name))

        # -- authored ridge routes -------------------------------------------
        stem = _points(self.ridge_stem, "ridge_stem", minimum_length=2)
        _validate_ridge_route(stem, "ridge_stem", self.frame_cells)
        if stem[0][1] != 0:
            raise ValueError("ridge_stem must begin at row 0")
        branches = self.ridge_branches
        if not isinstance(branches, Mapping):
            raise ValueError("ridge_branches must be a mapping")
        frozen_branches: dict[str, tuple[Point, ...]] = {}
        for name, route in branches.items():
            if name not in ("west", "east"):
                raise ValueError(f"unknown ridge branch {name!r}")
            points = _points(route, f"ridge_branches[{name!r}]", minimum_length=2)
            _validate_ridge_route(
                points, f"ridge_branches[{name!r}]", self.frame_cells
            )
            frozen_branches[name] = points
        if frozen_branches and set(frozen_branches) != {"west", "east"}:
            raise ValueError("ridge_branches needs both a west and an east route")
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
        object.__setattr__(self, "ridge_stem", stem)
        object.__setattr__(self, "ridge_branches", MappingProxyType(frozen_branches))
        object.__setattr__(self, "ridge_passes", tuple(passes))
        _validate_ridge_relations(
            self.waterway_routes[self.border_river_key],
            stem,
            frozen_branches,
            tuple(passes),
        )

        # Precompute immutable per-row tables so point validity never searches
        # a route, builds a raster, scans the frame or allocates a cache.
        stem_centres = _route_centres(stem)
        crotch_y = stem[-1][1]
        arm_centres = {
            name: _route_centres(route) for name, route in frozen_branches.items()
        }
        stem_closure = tuple(
            _closure(stem_centres, index) for index in range(len(stem_centres))
        )
        total_rows = max(
            [len(stem_centres)]
            + [crotch_y + len(table) for table in arm_centres.values()]
        )
        wall_spans: list[tuple[tuple[int, int], ...]] = []
        for y in range(total_rows):
            spans: list[tuple[int, int]] = []
            if y < len(stem_centres) and not any(
                low <= y <= high for low, high in passes
            ):
                spans.append(stem_closure[y])
            for table in arm_centres.values():
                index = y - crotch_y
                if 0 <= index < len(table):
                    spans.append(_closure(table, index))
            wall_spans.append(_merge_spans(spans))
        object.__setattr__(self, "_stem_centres", stem_centres)
        object.__setattr__(self, "_stem_closure", stem_closure)
        object.__setattr__(self, "_arm_centres", MappingProxyType(arm_centres))
        object.__setattr__(self, "_crotch_y", crotch_y)
        object.__setattr__(self, "_wall_spans", tuple(wall_spans))

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
        # The mountain window follows the authored stem's own centre extent,
        # widened by the authored corridor half-width and clipped to the frame.
        min_centre = min(self._stem_centres)
        max_centre = max(self._stem_centres)
        return MappingProxyType(
            {
                "north_deep_forest": (0, max_x, edge_y_min, max_y),
                "central_mountains": (
                    max(0, min_centre - self.mountain_corridor_half_width),
                    min(max_x, max_centre + self.mountain_corridor_half_width),
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
    """The authored stem's X centre at row ``y``.

    Outside the stem's active rows the nearest authored endpoint X continues
    straight, so the region and nominal-nation classifiers stay total over the
    whole bounded frame. This is a derivation from the same authored route,
    never a separate reference axis.
    """

    centres = definition._stem_centres
    if y < 0:
        return centres[0]
    if y >= len(centres):
        return centres[-1]
    return centres[y]


def ridge_crest_center_x(
    definition: TerrainDefinition, crest: str, y: int
) -> int | None:
    """The active centre X of one authored crest (``stem``/``west``/``east``).

    Unknown crest keys raise :class:`ValueError`; a known but absent arm or an
    inactive row returns ``None`` (no formula fallback).
    """

    if crest == "stem":
        centres = definition._stem_centres
        return centres[y] if 0 <= y < len(centres) else None
    if crest in ("west", "east"):
        table = definition._arm_centres.get(crest)
        if table is None:
            return None
        index = y - definition._crotch_y
        return table[index] if 0 <= index < len(table) else None
    raise ValueError(f"unknown ridge crest {crest!r}")


def ridge_span(definition: TerrainDefinition, y: int) -> tuple[int, int] | None:
    """The active stem's inclusive X closure span at row ``y``.

    Spanning every column between this row's centre and the next active row's
    centre keeps the wall 8-connected. ``None`` outside the active stem rows;
    independent of any pass exemption.
    """

    closure = definition._stem_closure
    return closure[y] if 0 <= y < len(closure) else None


def ridge_spans(definition: TerrainDefinition, y: int) -> tuple[tuple[int, int], ...]:
    """Every complete blocked X interval at row ``y``.

    The stem span is omitted in an authored pass row; each arm span is always
    included without pass exemptions. Overlapping or touching spans are merged
    and separated arms are never filled by their outer bounding interval.
    """

    spans = definition._wall_spans
    return spans[y] if 0 <= y < len(spans) else ()


def is_closed_ridge_cell(definition: TerrainDefinition, coordinates: Point) -> bool:
    """Whether ``(x, y)`` is an impassable ridge/cliff cell of any crest."""

    x, y = coordinates
    return any(low <= x <= high for low, high in ridge_spans(definition, y))


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
    """The authored stem route clipped to the inclusive rows ``y_start``..``y_end``.

    Emits the interpolated centre at each clipped boundary plus every authored
    interior vertex in range, deduplicating equal endpoints. An empty tuple
    means the interval does not intersect the active stem. This is the
    presentation line (e.g. a displayed political border), distinct from the
    raster closure spans that physically block; no periodic substitute or arm
    segment is ever produced.
    """

    stem = definition.ridge_stem
    stem_start, stem_end = stem[0][1], stem[-1][1]
    low = max(min(y_start, y_end), stem_start)
    high = min(max(y_start, y_end), stem_end)
    if low > high:
        return ()
    points: list[Point] = [(ridge_center_x(definition, low), low)]
    points.extend((x, y) for x, y in stem if low < y < high)
    points.append((ridge_center_x(definition, high), high))
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


#: The preview's surface classes, in code order.
PREVIEW_SURFACES = ("sea", "land", "water", "ridge")


@dataclass(frozen=True)
class TerrainPreview:
    """A coarse, deterministic preview of the derived terrain of one definition.

    ``samples`` is row-major from the southern row; sample ``(column, row)``
    classifies the cell ``(column * step + step // 2, row * step + step // 2)``
    (clamped to the frame) with the same rule functions the game uses. Each
    value is ``region_index * len(PREVIEW_SURFACES) + surface_index`` where
    ``region_index`` indexes :attr:`regions` and ``surface_index`` indexes
    :data:`PREVIEW_SURFACES`. Every geometric value is in cell indices.
    """

    step: int
    columns: int
    rows: int
    regions: tuple[str, ...]
    samples: tuple[int, ...]
    #: Closed ridge-wall polylines (cell coordinates) between the pass windows.
    ridge_walls: tuple[tuple[Point, ...], ...]
    #: ``(y_min, y_max, centre_cell)`` per authored pass window, in order.
    passes: tuple[tuple[int, int, Point], ...]
    #: Derived national borders; empty with ``borders_reason`` when the
    #: inputs cannot derive them.
    national_borders: tuple[NationalBorder, ...]
    borders_reason: str | None


def _sample_cell(index: int, step: int, maximum: int) -> int:
    return min(index * step + step // 2, maximum)


def _ridge_walls(definition: TerrainDefinition) -> tuple[tuple[Point, ...], ...]:
    walls: list[tuple[Point, ...]] = []
    closure = definition._stem_closure
    start: int | None = None
    for y in range(len(closure)):
        closed = not any(low <= y <= high for low, high in definition.ridge_passes)
        if closed and start is None:
            start = y
        elif not closed and start is not None:
            walls.append(_wall_run_polyline(closure, range(start, y), 0))
            start = None
    if start is not None:
        walls.append(_wall_run_polyline(closure, range(start, len(closure)), 0))
    # Each arm is an additional physical barrier drawn from its closure spans.
    for table in definition._arm_centres.values():
        arm_closure = tuple(_closure(table, index) for index in range(len(table)))
        walls.append(
            _wall_run_polyline(arm_closure, range(len(table)), definition._crotch_y)
        )
    return tuple(walls)


def terrain_preview(definition: TerrainDefinition, *, max_side: int = 90) -> TerrainPreview:
    """Sample the derived terrain on at most ``max_side`` x ``max_side`` cells.

    Pure and bounded: it calls only this module's rules, so the preview of an
    edited definition is exactly what the classifier derives from it.
    """

    if isinstance(max_side, bool) or not isinstance(max_side, int) or max_side < 1:
        raise ValueError("max_side must be a positive integer")
    frame = definition.frame_cells
    step = max(1, math.ceil(frame / max_side))
    count = math.ceil(frame / step)
    regions = tuple(sorted(REGION_KEYS))
    region_index = {key: index for index, key in enumerate(regions)}
    surfaces = len(PREVIEW_SURFACES)
    samples: list[int] = []
    for row in range(count):
        y = _sample_cell(row, step, definition.max_y)
        for column in range(count):
            x = _sample_cell(column, step, definition.max_x)
            if not is_land_cell(definition, (x, y)):
                surface = 0
            elif is_closed_ridge_cell(definition, (x, y)):
                surface = 3
            elif is_inland_water_cell(definition, (x, y)):
                surface = 2
            else:
                surface = 1
            samples.append(region_index[region_for_coordinates(definition, x, y)] * surfaces + surface)
    passes = tuple(
        (low, high, (ridge_center_x(definition, (low + high) // 2), (low + high) // 2))
        for low, high in definition.ridge_passes
    )
    try:
        borders = definition.national_borders
        reason = None
    except ValueError as error:
        borders, reason = (), str(error)
    return TerrainPreview(
        step=step,
        columns=count,
        rows=count,
        regions=regions,
        samples=tuple(samples),
        ridge_walls=_ridge_walls(definition),
        passes=passes,
        national_borders=borders,
        borders_reason=reason,
    )


__all__ = [
    "NATION_KEYS",
    "NationalBorder",
    "PREVIEW_SURFACES",
    "TerrainPreview",
    "REGION_KEYS",
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
    "ridge_crest_center_x",
    "ridge_polyline",
    "ridge_span",
    "ridge_spans",
    "route_row_at",
    "terrain_description",
    "terrain_preview",
]
