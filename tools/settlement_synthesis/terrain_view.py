"""A windowed, read-only view of the wilderness terrain for fit checks.

The adapter (``workspace.WorkspaceView.terrain_window``) fills one of these for
the cells a check can reach. Everything a check asks is answered from this
value alone, so a synthetic window substitutes for the whole continent.

A window boundary is not a coastline: a cell outside the window is neither land
nor sea, and is not walkable. That is what makes a gate approach outside the
frame a real error rather than a silently empty neighbourhood.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from tools.settlement_synthesis.geometry import Cell


@dataclass(frozen=True)
class GridTerrain:
    """The terrain facts inside one inclusive window, in wilderness cells."""

    window: tuple[int, int, int, int]  # min_x, min_y, max_x, max_y (inclusive)
    land: frozenset[Cell]  # mainland cells inside the window
    inland_water: frozenset[Cell]  # waterway raster minus fords
    impassable: frozenset[Cell]  # land, not water, not walkable (ridge walls)
    waterway_routes: Mapping[str, tuple[Cell, ...]]  # source -> mouth vertices
    waterway_cells: Mapping[str, frozenset[Cell]]  # raster cells, fords excluded
    waterway_fords: Mapping[str, tuple[Cell, ...]]
    bands: Mapping[Cell, int]  # elevation band 0..15; missing = 0
    harbours: Mapping[str, Cell]

    def contains(self, cell: Cell) -> bool:
        """Whether the cell lies inside the window."""

        min_x, min_y, max_x, max_y = self.window
        return min_x <= cell[0] <= max_x and min_y <= cell[1] <= max_y

    def is_sea(self, cell: Cell) -> bool:
        """Whether the cell is inside the window and not mainland."""

        return self.contains(cell) and cell not in self.land

    def is_water(self, cell: Cell) -> bool:
        """Whether the cell is sea or inland water. Fords are never water."""

        return self.is_sea(cell) or cell in self.inland_water

    def walkable(self, cell: Cell) -> bool:
        """Whether a traveller can stand on the cell."""

        return (
            self.contains(cell)
            and cell in self.land
            and cell not in self.inland_water
            and cell not in self.impassable
        )

    def band(self, cell: Cell) -> int:
        """The cell's elevation band; a cell without a tile reads as 0."""

        return self.bands.get(cell, 0)
