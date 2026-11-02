"""Compass bearings and the two coordinate frames the settlement tools share.

Wilderness cells are 1 km squares whose centre sits at ``(1000X + 500,
1000Y + 500)`` metres. A settlement authors integer-metre points in its own
local frame, and the game places that frame on the continent by putting the
anchor node on its location cell's centre. Every value here is a pure function
of its arguments, so a fit check can be reasoned about without a world.
"""

from __future__ import annotations

import math

Cell = tuple[int, int]

#: The eight compass points, counter-clockwise from east.
OCTANTS = ("e", "ne", "n", "nw", "w", "sw", "s", "se")

OPPOSITE = {
    "n": "s",
    "ne": "sw",
    "e": "w",
    "se": "nw",
    "s": "n",
    "sw": "ne",
    "w": "e",
    "nw": "se",
}

OCTANT_VECTORS = {
    "e": (1, 0),
    "ne": (1, 1),
    "n": (0, 1),
    "nw": (-1, 1),
    "w": (-1, 0),
    "sw": (-1, -1),
    "s": (0, -1),
    "se": (1, -1),
}


def bearing(dx: float, dy: float) -> str | None:
    """8-way bearing; dx east, dy north; None for the zero vector."""

    if dx == 0 and dy == 0:
        return None
    index = int(math.floor(math.atan2(dy, dx) / (math.pi / 4) + 0.5)) % 8
    return OCTANTS[index]


def octant_distance(a: str, b: str) -> int:
    """How many octants apart two bearings are, 0..4."""

    i, j = OCTANTS.index(a), OCTANTS.index(b)
    return min(abs(i - j), 8 - abs(i - j))


def world_position(
    location_cell: Cell,
    anchor_m: tuple[int, int],
    local_m: tuple[int, int],
) -> tuple[int, int]:
    """One local metre point placed in continent metres."""

    return (
        1000 * location_cell[0] + 500 + local_m[0] - anchor_m[0],
        1000 * location_cell[1] + 500 + local_m[1] - anchor_m[1],
    )


def cell_of(world_m: tuple[float, float]) -> Cell:
    """The wilderness cell holding one world-metre point."""

    return (int(math.floor(world_m[0] / 1000)), int(math.floor(world_m[1] / 1000)))


def point_to_cell_distance(world_m: tuple[float, float], cell: Cell) -> float:
    """Metres from a point to the nearest point of a 1 km cell square (0 inside)."""

    x0, y0 = 1000 * cell[0], 1000 * cell[1]
    dx = max(x0 - world_m[0], 0.0, world_m[0] - (x0 + 1000))
    dy = max(y0 - world_m[1], 0.0, world_m[1] - (y0 + 1000))
    return math.hypot(dx, dy)
