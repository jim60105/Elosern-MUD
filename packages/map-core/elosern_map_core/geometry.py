"""Explicit-input metric geometry shared by the map layers.

Units
-----
Wilderness cells are logical areas of one kilometre per axis. A cell's
representative centre in absolute metres is
``E = 1000 * X + 500`` and ``N = 1000 * Y + 500`` (:func:`cell_center_m`);
the half-cell offset is :data:`CELL_CENTER_OFFSET_M`.

Settlement positions are integer metres east/north in the settlement's local
frame. The cross-layer transform is
``world_m = anchor_cell_center_m + local_m - local_anchor_m``
(:func:`local_to_world_m`): the authored local anchor point is the settlement
position that sits on the wilderness anchor cell's centre. A settlement's
``z`` remains a logical layer key and is never physical elevation, so the
transform returns horizontal metres only.

Polygon helpers take the mainland boundary as an explicit closed-ring vertex
tuple in absolute kilometres; boundary points count as land.

Every function is pure and deterministic: no game, database, clock or random
input, and no cache outside the arguments it is given.
"""

from __future__ import annotations

from typing import Iterable

#: Logical size of one wilderness cell per axis, in metres.
METRES_PER_WILDERNESS_CELL = 1000
#: A cell's representative centre is offset this many metres into the cell.
CELL_CENTER_OFFSET_M = 500

Point = tuple[int, int]


def _require_int_pair(value: object, label: str) -> tuple[int, int]:
    """Return ``value`` as an integer pair, or raise ``ValueError``."""

    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or isinstance(value[0], bool)
        or isinstance(value[1], bool)
        or not isinstance(value[0], int)
        or not isinstance(value[1], int)
    ):
        raise ValueError(f"{label} must be an integer (east, north) pair")
    return value


def cell_center_m(cell: tuple[int, int]) -> tuple[int, int]:
    """Absolute ``(east, north)`` metres of a wilderness cell's centre.

    A cell is an area; this point is only its representative centre.
    """

    x, y = _require_int_pair(cell, "wilderness cell")
    return (METRES_PER_WILDERNESS_CELL * x + CELL_CENTER_OFFSET_M,
            METRES_PER_WILDERNESS_CELL * y + CELL_CENTER_OFFSET_M)


def local_to_world_m(
    anchor_cell: tuple[int, int],
    local_anchor_m: tuple[int, int],
    local_position_m: tuple[int, int],
) -> tuple[int, int]:
    """Absolute ``(east, north)`` metres of a settlement-local metre position.

    ``world = cell_center_m(anchor_cell) + local_position_m - local_anchor_m``.
    ``anchor_cell`` is the wilderness cell whose centre the settlement's local
    anchor point occupies; every argument is an explicit authored value.
    """

    center_east, center_north = cell_center_m(anchor_cell)
    anchor_east, anchor_north = _require_int_pair(local_anchor_m, "local anchor")
    local_east, local_north = _require_int_pair(local_position_m, "local position")
    return (
        center_east + local_east - anchor_east,
        center_north + local_north - anchor_north,
    )


def is_within_frame(frame_cells: int, cell: tuple[int, int]) -> bool:
    """Whether ``cell`` is inside a ``frame_cells`` square frame."""

    if not isinstance(frame_cells, int) or isinstance(frame_cells, bool) or frame_cells <= 0:
        raise ValueError("frame_cells must be a positive integer")
    x, y = _require_int_pair(cell, "cell")
    return 0 <= x < frame_cells and 0 <= y < frame_cells


def _ring(boundary: Iterable[Point]) -> tuple[Point, ...]:
    vertices = tuple(_require_int_pair(point, "boundary vertex") for point in boundary)
    if len(vertices) < 3:
        raise ValueError("a boundary needs at least three vertices")
    return vertices


def polygon_area_km2(boundary: Iterable[Point]) -> float:
    """Shoelace area of a closed boundary ring, square kilometres."""

    vertices = _ring(boundary)
    doubled = sum(
        vertices[index][0] * vertices[(index + 1) % len(vertices)][1]
        - vertices[(index + 1) % len(vertices)][0] * vertices[index][1]
        for index in range(len(vertices))
    )
    return abs(doubled) / 2


def _on_boundary(vertices: tuple[Point, ...], east_km: float, north_km: float) -> bool:
    for index, (start_east, start_north) in enumerate(vertices):
        end_east, end_north = vertices[(index + 1) % len(vertices)]
        cross = (end_east - start_east) * (north_km - start_north) - (
            end_north - start_north
        ) * (east_km - start_east)
        if cross != 0:
            continue
        if (
            min(start_east, end_east) <= east_km <= max(start_east, end_east)
            and min(start_north, end_north) <= north_km <= max(start_north, end_north)
        ):
            return True
    return False


def is_on_mainland(
    boundary: Iterable[Point], east_km: float, north_km: float
) -> bool:
    """Whether an absolute ``(east, north)`` kilometre point is on land.

    ``boundary`` is the closed mainland ring; boundary points count as land.
    """

    vertices = _ring(boundary)
    if _on_boundary(vertices, east_km, north_km):
        return True
    inside = False
    for index, (start_east, start_north) in enumerate(vertices):
        end_east, end_north = vertices[(index + 1) % len(vertices)]
        if (start_north > north_km) == (end_north > north_km):
            continue
        crossing_east = (end_east - start_east) * (north_km - start_north) / (
            end_north - start_north
        ) + start_east
        if east_km < crossing_east:
            inside = not inside
    return inside
