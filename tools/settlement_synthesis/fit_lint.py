"""The terrain-fit lint: authored street graphs checked against their terrain.

Every check runs in world metres, so a settlement's local frame is resolved
through its location cell and its unique anchor node once. The rules are
deliberately coarse: the wilderness raster is 1 km cells, so water is only
known per cell and a water-edge role is allowed a generous 600 m rather than an
exact shoreline. Ford cells never count as water.

The lint reads documents and writes nothing. It never edits a direction, a
coordinate or an identifier: a finding names the object and leaves the decision
to the author.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from elosern_map_core.authoring import gate_approach_cell

from tools.settlement_synthesis.geometry import (
    Cell,
    OCTANT_VECTORS,
    OPPOSITE,
    bearing,
    cell_of,
    octant_distance,
    point_to_cell_distance,
    world_position,
)
from tools.settlement_synthesis.terrain_view import GridTerrain

#: Identifier tokens that claim a role on the water's edge.
WATER_EDGE_WORDS = frozenset(
    {
        "quay",
        "wharf",
        "dock",
        "docks",
        "pier",
        "landing",
        "riverbank",
        "waterfront",
    }
)

#: Identifier tokens that make a road a legal water crossing.
CROSSING_WORDS = frozenset({"bridge", "ford", "ferry"})


def words(node_id: str) -> frozenset[str]:
    """The whole underscore-separated tokens of one identifier."""

    return frozenset(node_id.split("_"))


@dataclass(frozen=True)
class FitFinding:
    """One terrain-fit result for one map object."""

    code: str
    severity: str  # "error" | "warning"
    map_id: str
    object_id: str  # node id, "source>destination" for a road, "gate:<return_direction>"
    message: str


@dataclass(frozen=True)
class LintConfig:
    """The lint's two tolerances, both in world metres."""

    water_edge_max_m: int = 600
    sample_step_m: int = 50


def _road_polyline(
    document: Any, road: Any, location_cell: Cell, anchor: tuple[int, int]
) -> list[tuple[int, int]]:
    points = [document.nodes[road.source].coordinate]
    points.extend((bend.x_m, bend.y_m) for bend in road.bends)
    points.append(document.nodes[road.destination].coordinate)
    return [world_position(location_cell, anchor, point) for point in points]


def _crosses_water(
    polyline: list[tuple[int, int]], terrain: GridTerrain, step_m: int
) -> bool:
    """Whether any sampled point of a world-metre polyline lands in water."""

    for start, end in zip(polyline, polyline[1:]):
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        steps = max(1, math.ceil(length / step_m))
        for index in range(steps + 1):
            fraction = index / steps
            point = (
                start[0] + (end[0] - start[0]) * fraction,
                start[1] + (end[1] - start[1]) * fraction,
            )
            if terrain.is_water(cell_of(point)):
                return True
    return False


def lint_settlement(
    document: Any,
    location_cell: Cell,
    terrain: GridTerrain,
    config: LintConfig = LintConfig(),
) -> tuple[FitFinding, ...]:
    """Every terrain-fit finding for one settlement map, errors first."""

    map_id = document.identity
    anchor = document.local_anchor_m
    if anchor is None:
        return (
            FitFinding(
                code="fit_missing_anchor",
                severity="error",
                map_id=map_id,
                object_id=map_id,
                message=(
                    "the map has no unique anchor_room node, so its local frame "
                    "cannot be placed on the continent"
                ),
            ),
        )

    geometry = document.wilderness_geometry(location_cell)
    footprint = frozenset() if geometry is None else geometry.footprint_cells
    multi_cell = bool(footprint)

    positions = {
        node_id: world_position(location_cell, anchor, node.coordinate)
        for node_id, node in document.nodes.items()
    }

    min_x, min_y, max_x, max_y = terrain.window
    water_cells = [
        (x, y)
        for y in range(min_y, max_y + 1)
        for x in range(min_x, max_x + 1)
        if terrain.is_water((x, y))
    ]

    findings: list[FitFinding] = []

    for node_id in document.nodes:
        point = positions[node_id]
        cell = cell_of(point)
        if terrain.is_water(cell):
            findings.append(
                FitFinding(
                    code="fit_node_in_water",
                    severity="error",
                    map_id=map_id,
                    object_id=node_id,
                    message=(
                        f"{node_id} stands in water at world {point[0]}, {point[1]} "
                        f"(cell {cell[0]}, {cell[1]})"
                    ),
                )
            )
        if words(node_id) & WATER_EDGE_WORDS:
            nearest = min(
                (point_to_cell_distance(point, water) for water in water_cells),
                default=None,
            )
            if nearest is None:
                findings.append(
                    FitFinding(
                        code="fit_water_role_dry",
                        severity="error",
                        map_id=map_id,
                        object_id=node_id,
                        message=(
                            f"{node_id} claims a water-edge role but no water lies "
                            "in the checked terrain window"
                        ),
                    )
                )
            elif nearest > config.water_edge_max_m:
                findings.append(
                    FitFinding(
                        code="fit_water_role_dry",
                        severity="error",
                        map_id=map_id,
                        object_id=node_id,
                        message=(
                            f"{node_id} claims a water-edge role but the nearest "
                            f"water is {round(nearest)} m away (limit "
                            f"{config.water_edge_max_m} m)"
                        ),
                    )
                )
        if multi_cell and cell not in footprint:
            findings.append(
                FitFinding(
                    code="fit_node_outside_footprint",
                    severity="error",
                    map_id=map_id,
                    object_id=node_id,
                    message=(
                        f"{node_id} stands at cell {cell[0]}, {cell[1]}, outside the "
                        "settlement's footprint cells"
                    ),
                )
            )

    for road in document.roads:
        object_id = f"{road.source}>{road.destination}"
        crossing = bool(
            words(road.source) & CROSSING_WORDS
            or words(road.destination) & CROSSING_WORDS
        )
        polyline = _road_polyline(document, road, location_cell, anchor)
        if not crossing and _crosses_water(polyline, terrain, config.sample_step_m):
            findings.append(
                FitFinding(
                    code="fit_unbridged_crossing",
                    severity="error",
                    map_id=map_id,
                    object_id=object_id,
                    message=(
                        f"{object_id} crosses water with no bridge, ford or ferry "
                        "endpoint"
                    ),
                )
            )

        start = document.nodes[road.source].coordinate
        if road.bends:
            end = (road.bends[0].x_m, road.bends[0].y_m)
        else:
            end = document.nodes[road.destination].coordinate
        delta_x, delta_y = end[0] - start[0], end[1] - start[1]
        if delta_x != 0 or delta_y != 0:
            geometry_bearing = bearing(delta_x, delta_y)
            if (
                geometry_bearing is not None
                and octant_distance(road.direction, geometry_bearing) > 1
            ):
                findings.append(
                    FitFinding(
                        code="fit_direction_drift",
                        severity="warning",
                        map_id=map_id,
                        object_id=object_id,
                        message=(
                            f"{object_id} is authored {road.direction} but its first "
                            f"segment points {geometry_bearing}"
                        ),
                    )
                )

    if geometry is not None and multi_cell:
        for gate in geometry.gates:
            object_id = f"gate:{gate.return_direction}"
            approach = gate_approach_cell(geometry, gate.return_direction)
            if approach is None or not terrain.walkable(approach):
                findings.append(
                    FitFinding(
                        code="fit_gate_approach_blocked",
                        severity="error",
                        map_id=map_id,
                        object_id=object_id,
                        message=(
                            f"{object_id} has no walkable approach cell"
                            if approach is None
                            else (
                                f"{object_id} approaches from cell {approach[0]}, "
                                f"{approach[1]}, which is not walkable"
                            )
                        ),
                    )
                )
            node = document.nodes.get(gate.destination_node)
            outward = OCTANT_VECTORS.get(OPPOSITE.get(gate.return_direction, ""))
            if node is None or outward is None:
                continue
            offset = (node.x_m - anchor[0], node.y_m - anchor[1])
            if offset != (0, 0) and offset[0] * outward[0] + offset[1] * outward[1] < 0:
                findings.append(
                    FitFinding(
                        code="fit_gate_side",
                        severity="warning",
                        map_id=map_id,
                        object_id=object_id,
                        message=(
                            f"{object_id} faces outward {OPPOSITE[gate.return_direction]} "
                            f"but its node {gate.destination_node} lies the other way"
                        ),
                    )
                )

    return tuple(
        sorted(
            findings,
            key=lambda finding: (
                finding.severity == "warning",
                finding.code,
                finding.object_id,
            ),
        )
    )
