"""Site context: where a settlement sits relative to water, relief and peers.

The analysis is a pure function of one location, one terrain window and the
location roster. It answers the questions a street graph must respect: which
river or sea is near and in which direction, where the water flows, where the
usable crossings and harbour sites are, which way is uphill, and where the
neighbouring national settlements and the settlement's own capital lie.

Every bearing is one of the eight compass points, and every distance is in
wilderness cells: the search radius is a Chebyshev box, the distances are
Euclidean over cell indices.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from tools.settlement_synthesis.budget import NATIONAL_KINDS
from tools.settlement_synthesis.geometry import Cell, bearing
from tools.settlement_synthesis.terrain_view import GridTerrain


@dataclass(frozen=True)
class SettlementRef:
    """One location as a site analysis needs it: identity, kind and lore join."""

    location_id: str
    kind: str
    nation: str | None
    population: int | None
    cell: Cell


@dataclass(frozen=True)
class WaterContact:
    """One waterway or the sea within the search radius."""

    kind: str  # "river" | "sea"
    name: str | None  # waterway id; None for sea
    distance_cells: float  # Euclidean, location cell -> nearest_cell
    bearing: str  # bearing of the centroid of that body's cells within the radius
    nearest_cell: Cell  # min by (distance, y, x)
    downstream: str | None  # river: bearing(end - start) of the nearest segment


@dataclass(frozen=True)
class PointFeature:
    """One named terrain point at a known distance and bearing."""

    feature_id: str
    cell: Cell
    distance_cells: float
    bearing: str | None


@dataclass(frozen=True)
class SiteContext:
    """Everything one site analysis derives about one location."""

    location_id: str
    kind: str
    nation: str | None
    population: int | None
    cell: Cell
    rivers: tuple[WaterContact, ...]  # sorted by (distance_cells, name)
    sea: WaterContact | None
    fords: tuple[PointFeature, ...]  # feature_id = waterway id
    harbours: tuple[PointFeature, ...]  # feature_id = harbour id
    uphill: str | None
    relief: int
    neighbours: tuple[PointFeature, ...]  # feature_id = location id
    capital_bearing: str | None


def _within(cell: Cell, centre: Cell, radius: int) -> bool:
    return max(abs(cell[0] - centre[0]), abs(cell[1] - centre[1])) <= radius


def _distance(a: Cell, b: Cell) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _centroid(cells: Sequence[Cell]) -> tuple[float, float]:
    return (
        sum(cell[0] for cell in cells) / len(cells),
        sum(cell[1] for cell in cells) / len(cells),
    )


def _nearest_cell(cells: Sequence[Cell], centre: Cell) -> Cell:
    """The closest cell, ties broken south-first then west-first."""

    return min(cells, key=lambda cell: (_distance(cell, centre), cell[1], cell[0]))


def _centroid_bearing(cells: Sequence[Cell], centre: Cell) -> str:
    """The bearing of a body's centroid, falling back to its nearest cell.

    A body that surrounds the location has its centroid on the location, where
    there is no bearing; the nearest cell still names a direction.
    """

    centroid = _centroid(cells)
    direction = bearing(centroid[0] - centre[0], centroid[1] - centre[1])
    if direction is not None:
        return direction
    nearest = _nearest_cell(cells, centre)
    fallback = bearing(nearest[0] - centre[0], nearest[1] - centre[1])
    return fallback if fallback is not None else "e"


def _segment_distance(point: Cell, start: Cell, end: Cell) -> float:
    """Euclidean distance from a cell point to one route segment."""

    delta_x, delta_y = end[0] - start[0], end[1] - start[1]
    if delta_x == 0 and delta_y == 0:
        return _distance(point, start)
    offset_x, offset_y = point[0] - start[0], point[1] - start[1]
    projection = (offset_x * delta_x + offset_y * delta_y) / (
        delta_x * delta_x + delta_y * delta_y
    )
    projection = max(0.0, min(1.0, projection))
    closest = (start[0] + projection * delta_x, start[1] + projection * delta_y)
    return math.hypot(point[0] - closest[0], point[1] - closest[1])


def _downstream_bearing(
    route: Sequence[Cell], nearest: Cell
) -> str | None:
    """The direction of the route segment closest to one cell.

    Routes run source-to-mouth, so the segment's own direction is downstream.
    Ties go to the earliest segment.
    """

    if len(route) < 2:
        return None
    index = min(
        range(len(route) - 1),
        key=lambda position: (
            _segment_distance(nearest, route[position], route[position + 1]),
            position,
        ),
    )
    start, end = route[index], route[index + 1]
    return bearing(end[0] - start[0], end[1] - start[1])


def _window_cells(terrain: GridTerrain) -> list[Cell]:
    min_x, min_y, max_x, max_y = terrain.window
    return [
        (x, y)
        for y in range(min_y, max_y + 1)
        for x in range(min_x, max_x + 1)
    ]


def analyse_site(
    location: SettlementRef,
    terrain: GridTerrain,
    roster: Sequence[SettlementRef],
    *,
    radius: int = 8,
    relief_radius: int = 3,
    harbour_radius: int = 15,
    neighbour_count: int = 4,
) -> SiteContext:
    """Derive one settlement's site context from explicit inputs."""

    centre = location.cell

    rivers: list[WaterContact] = []
    for name in sorted(terrain.waterway_cells):
        cells = [
            cell
            for cell in terrain.waterway_cells[name]
            if _within(cell, centre, radius)
        ]
        if not cells:
            continue
        nearest = _nearest_cell(cells, centre)
        rivers.append(
            WaterContact(
                kind="river",
                name=name,
                distance_cells=_distance(nearest, centre),
                bearing=_centroid_bearing(cells, centre),
                nearest_cell=nearest,
                downstream=_downstream_bearing(
                    terrain.waterway_routes.get(name, ()), nearest
                ),
            )
        )
    rivers.sort(key=lambda contact: (contact.distance_cells, contact.name or ""))

    sea: WaterContact | None = None
    sea_cells = [
        cell
        for cell in _window_cells(terrain)
        if terrain.is_sea(cell) and _within(cell, centre, radius)
    ]
    if sea_cells:
        nearest = _nearest_cell(sea_cells, centre)
        sea = WaterContact(
            kind="sea",
            name=None,
            distance_cells=_distance(nearest, centre),
            bearing=_centroid_bearing(sea_cells, centre),
            nearest_cell=nearest,
            downstream=None,
        )

    fords: list[PointFeature] = []
    for name in sorted(terrain.waterway_fords):
        for cell in terrain.waterway_fords[name]:
            if not _within(cell, centre, radius):
                continue
            fords.append(
                PointFeature(
                    feature_id=name,
                    cell=cell,
                    distance_cells=_distance(cell, centre),
                    bearing=bearing(cell[0] - centre[0], cell[1] - centre[1]),
                )
            )
    fords.sort(
        key=lambda feature: (
            feature.distance_cells,
            feature.feature_id,
            feature.cell,
        )
    )

    harbours: list[PointFeature] = []
    for harbour_id in sorted(terrain.harbours):
        cell = terrain.harbours[harbour_id]
        if not _within(cell, centre, harbour_radius):
            continue
        harbours.append(
            PointFeature(
                feature_id=harbour_id,
                cell=cell,
                distance_cells=_distance(cell, centre),
                bearing=bearing(cell[0] - centre[0], cell[1] - centre[1]),
            )
        )
    harbours.sort(key=lambda feature: (feature.distance_cells, feature.feature_id))

    relief_cells = [
        cell
        for cell in _window_cells(terrain)
        if _within(cell, centre, relief_radius) and terrain.walkable(cell)
    ]
    relief_cells.append(centre)
    bands = [terrain.band(cell) for cell in relief_cells]
    relief = max(bands) - min(bands)
    base_band = terrain.band(centre)
    gradient_x = sum(
        (terrain.band(cell) - base_band) * (cell[0] - centre[0])
        for cell in relief_cells
    )
    gradient_y = sum(
        (terrain.band(cell) - base_band) * (cell[1] - centre[1])
        for cell in relief_cells
    )
    uphill = bearing(gradient_x, gradient_y) if relief >= 1 else None

    neighbours = [
        PointFeature(
            feature_id=ref.location_id,
            cell=ref.cell,
            distance_cells=_distance(ref.cell, centre),
            bearing=bearing(ref.cell[0] - centre[0], ref.cell[1] - centre[1]),
        )
        for ref in roster
        if ref.location_id != location.location_id and ref.kind in NATIONAL_KINDS
    ]
    neighbours.sort(key=lambda feature: (feature.distance_cells, feature.feature_id))
    neighbours = neighbours[:neighbour_count]

    capital_bearing: str | None = None
    if location.kind != "capital" and location.nation is not None:
        capitals = sorted(
            (
                ref
                for ref in roster
                if ref.kind == "capital" and ref.nation == location.nation
            ),
            key=lambda ref: ref.location_id,
        )
        if capitals:
            capital_bearing = bearing(
                capitals[0].cell[0] - centre[0], capitals[0].cell[1] - centre[1]
            )

    return SiteContext(
        location_id=location.location_id,
        kind=location.kind,
        nation=location.nation,
        population=location.population,
        cell=centre,
        rivers=tuple(rivers),
        sea=sea,
        fords=tuple(fords),
        harbours=tuple(harbours),
        uphill=uphill,
        relief=relief,
        neighbours=tuple(neighbours),
        capital_bearing=capital_bearing,
    )
