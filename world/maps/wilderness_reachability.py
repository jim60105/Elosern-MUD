"""Exact walkable-component index of the wilderness (map-districts validation).

Movement between wilderness cells follows ``wilderness_neighbor``: a diagonal
step needs both orthogonal cells walkable, so 8-direction reachability equals
4-connectivity of :func:`world.maps.wilderness_provider.is_valid_wilderness_cell`
cells. The index stores every row as runs of consecutive valid cells and joins
runs of adjacent rows that share a column (union-find). Only the cells that can
be invalid inside the mainland (the summit ridge span, rasterized waterways and
anchor footprints) are tested per row, so building the index is bounded work
over about 2,700 rows instead of a scan of every land cell.

The index is a pure derivation of one explicit geography snapshot and the live
wilderness entry registry; it reads no database, clock or random source. It is
cached per (snapshot, entry-registry) pair, so a second world or a reload never
reuses another world's components.
"""

from __future__ import annotations

import math

from elosern_map_core import terrain as core_terrain
from elosern_map_core.terrain import TerrainDefinition

from world.lore import wilderness_entry as _wilderness_entry_module

_INDEX_CACHE: dict[tuple[str, tuple[tuple[str, object], ...]], "WalkableComponents"] = {}


class WalkableComponents:
    """Connected components of valid wilderness cells, stored as row runs.

    ``terrain`` is the explicit snapshot this index was derived from; it owns
    the frame, mainland, ridge, water and anchor-footprint rules, and no
    module-level constant is consulted here.
    """

    def __init__(
        self, terrain: TerrainDefinition, footprints: frozenset[tuple[int, int]]
    ) -> None:
        self.terrain = terrain
        self._footprints = footprints
        candidates: dict[int, set[int]] = {}
        for x, y in core_terrain.rasterize_routes(terrain.waterway_routes):
            candidates.setdefault(y, set()).add(x)
        for x, y in footprints:
            candidates.setdefault(y, set()).add(x)
        self._runs: list[tuple[int, int, int]] = []
        self._parent: list[int] = []
        self._row_runs: dict[int, list[int]] = {}
        previous: list[int] = []
        for y in range(terrain.max_y + 1):
            low, high = core_terrain.ridge_span(terrain, y)
            row_candidates = candidates.get(y, set()) | set(range(low, high + 1))
            current: list[int] = []
            for west, east in mainland_row_intervals(terrain, y):
                blocked = sorted(
                    x
                    for x in row_candidates
                    if west <= x <= east
                    and not core_terrain.is_valid_wilderness_cell(
                        terrain, self._footprints, (x, y)
                    )
                )
                start = west
                for x in [*blocked, east + 1]:
                    if x > start:
                        current.append(self._add_run(y, start, x - 1))
                    start = x + 1
            self._row_runs[y] = current
            for run in current:
                _, run_low, run_high = self._runs[run]
                for other in previous:
                    _, other_low, other_high = self._runs[other]
                    if run_low <= other_high and other_low <= run_high:
                        self._union(run, other)
            previous = current

    @property
    def footprints(self) -> frozenset[tuple[int, int]]:
        """The anchor footprint cells this index was built from."""

        return self._footprints

    def _add_run(self, y: int, low: int, high: int) -> int:
        self._runs.append((y, low, high))
        self._parent.append(len(self._parent))
        return len(self._runs) - 1

    def _find(self, run: int) -> int:
        while self._parent[run] != run:
            self._parent[run] = self._parent[self._parent[run]]
            run = self._parent[run]
        return run

    def _union(self, first: int, second: int) -> None:
        self._parent[self._find(first)] = self._find(second)

    def component(self, cell: tuple[int, int]) -> int | None:
        """The component id of a valid cell, or ``None`` for an invalid one."""
        x, y = cell
        for run in self._row_runs.get(y, ()):
            _, low, high = self._runs[run]
            if low <= x <= high:
                return self._find(run)
        return None


def mainland_row_intervals(terrain: TerrainDefinition, y: int) -> list[tuple[int, int]]:
    """Inclusive X intervals of land cells in row ``y``.

    The even-odd crossings of the row's centre line give the candidate ends;
    each end is then corrected against :func:`is_land_cell` (the single land
    rule), so a floating-point edge case can only move an end onto the rule's
    own answer, never disagree with it.
    """
    north = y + 0.5
    vertices = terrain.mainland_boundary_km
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
        high = min(math.floor(east - 0.5), terrain.max_x)
        while low <= high and not core_terrain.is_land_cell(terrain, (low, y)):
            low += 1
        while low > 0 and core_terrain.is_land_cell(terrain, (low - 1, y)):
            low -= 1
        while high >= low and not core_terrain.is_land_cell(terrain, (high, y)):
            high -= 1
        while high < terrain.max_x and core_terrain.is_land_cell(terrain, (high + 1, y)):
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


def walkable_components(snapshot=None) -> WalkableComponents:
    """The component index for one geography snapshot and the live entry registry."""

    from world.maps.geography import current

    geography = snapshot if snapshot is not None else current()
    terrain = geography.terrain
    registry = _wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY
    key = (geography.identity, tuple(registry.items()))
    cached = _INDEX_CACHE.get(key)
    if cached is None:
        footprints = frozenset(
            cell for entry in registry.values() for cell in entry.footprint_cells
        )
        cached = WalkableComponents(terrain, footprints)
        _INDEX_CACHE.clear()
        _INDEX_CACHE[key] = cached
    return cached


__all__ = [
    "WalkableComponents",
    "mainland_row_intervals",
    "walkable_components",
]
