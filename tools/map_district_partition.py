"""Offline map-district partition generator (map-district-partition).

Computes which map district owns every land cell of the continent and the
smoothed district outlines, then writes them as frozen, version-controlled
data (``world/maps/data/district_partition.json``). The runtime only decodes
that file through ``world.maps.district_partition``; it never imports this
module or recomputes anything (world-map drawer design §4.2).

Regenerate after any registry or geography change::

    uv run --locked python -m tools.map_district_partition

``--check`` regenerates in memory and exits non-zero when the committed file
differs byte for byte.

Algorithm (compute-map-district-partition design):

1. ``region`` districts take every land cell of their terrain region first,
   even across nominal nations.
2. The remaining walkable land is the Voronoi domain. A legal one-kilometre
   step joins two domain cells of the same nominal nation; a diagonal step
   also needs both orthogonal cells in the domain and of that nation (no
   corner cutting). Sea, ridge, river, footprint and region cells are blocked
   sides; a national border is closed even at a pass or ford.
3. Each 5 km tile (540 by 540 over the 2700 km frame) splits its domain cells
   into fragments: the tile-local components under legal steps. Fragments are
   the coarse vertices. Two fragments of adjacent tiles are joined when a
   legal one-kilometre step crosses between them, at cost 1 for a cardinal
   tile step and sqrt(2) for a diagonal (corner) tile step; travel inside a
   fragment is free.
4. A multi-source Dijkstra from every Voronoi landmark assigns each fragment
   to the nearest district; equal distances go to the smaller district key,
   then the smaller fragment (tile row-major, then first cell row-major).
   Distances are exact ``a + b*sqrt(2)`` integer pairs. A grid landmark is
   injected as zero-distance sources at the same-nation domain fragments of
   its routed gateway approach cells, and its containing footprint's land is
   assigned to it explicitly. Any unseeded legal component is an error that
   names its coordinates; a barrier is never crossed to fill it.
5. Remaining land (ridge, river, unseeded footprint) is display ownership
   only: the nearest propagated or claimed same-nation non-region cell by
   squared centre distance, then district key, then cell (row-major). It
   never feeds propagation. Sea has no owner.

The output stores 5 km tile ownership as row runs plus exact 1 km exception
runs for tiles whose land cells have more than one owner, and district
outlines traced from the exact 1 km ownership. Outline pieces are shared
between neighbours and smoothed once, so smoothing creates no gap or overlap;
pieces along a national border keep their exact lattice geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import os
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import ndimage

#: Bump when the algorithm or the encoding changes; it is part of the
#: fingerprint, so a stale committed file is detected.
ALGORITHM_VERSION = 1
#: One-kilometre cells per side of a coarse raster tile (5 km tiles).
TILE_CELLS = 5
#: Metres per one-kilometre cell; outline coordinates are metres.
CELL_M = 1000
#: Douglas-Peucker tolerance for smoothed (non-national) outline pieces.
OUTLINE_TOLERANCE_M = 500
#: Coarse tile value whose land cells have several owners (see exceptions).
MIXED = -1
#: Farthest Chebyshev radius searched for a display owner.
DISPLAY_SEARCH_RADIUS = 64

DATA_PATH = Path(__file__).resolve().parents[1] / "world" / "maps" / "data" / "district_partition.json"

_SQRT2 = math.sqrt(2.0)
_DISTRICT_KINDS = ("voronoi", "region")

Cell = tuple[int, int]


class PartitionError(ValueError):
    """The inputs cannot be partitioned; ``problems`` names every fault."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("map district partition failed:\n" + "\n".join(self.problems))


@dataclass(frozen=True)
class DistrictSeed:
    """One district as the partition sees it.

    ``landmark_cell`` is the one-kilometre cell holding the landmark.
    ``approaches`` is ``None`` for a wilderness landmark; for a grid landmark
    it lists the gateway approach cells whose gate routes to the landmark
    through the settlement's sparse graph. ``footprint`` is the footprint of
    the anchor entry containing the landmark cell (empty otherwise).
    """

    key: str
    kind: str
    landmark_cell: Cell
    region_key: str | None = None
    approaches: tuple[Cell, ...] | None = None
    footprint: frozenset[Cell] = frozenset()


@dataclass(frozen=True, eq=False)
class PartitionInput:
    """Rasters indexed ``[y, x]`` (row = north coordinate) plus districts.

    ``nation`` and ``region`` hold ``index + 1`` into their name tables and 0
    where unset; every land cell needs both.
    """

    size: int
    land: np.ndarray
    walkable: np.ndarray
    nation: np.ndarray
    nation_names: tuple[str, ...]
    region: np.ndarray
    region_names: tuple[str, ...]
    districts: tuple[DistrictSeed, ...]
    tile: int = TILE_CELLS


@dataclass(frozen=True, eq=False)
class Partition:
    """The computed ownership.

    ``owner`` holds ``index + 1`` into ``keys`` (0 = no owner). ``primary``
    marks cells owned by region reservation, propagation or an explicit
    footprint claim; land outside it is display ownership. ``fragment`` holds
    each domain cell's fragment id (-1 elsewhere) and ``sources`` the source
    fragments of every Voronoi district.
    """

    keys: tuple[str, ...]
    owner: np.ndarray
    primary: np.ndarray
    domain: np.ndarray
    fragment: np.ndarray
    sources: dict[str, tuple[int, ...]] = field(default_factory=dict)

    def owner_at(self, cell: Cell) -> str | None:
        code = int(self.owner[cell[1], cell[0]])
        return self.keys[code - 1] if code else None


# --------------------------------------------------------------------------
# Partition


def _check_input(inp: PartitionInput) -> list[str]:
    problems = []
    if inp.size % inp.tile:
        problems.append(f"frame size {inp.size} is not a multiple of the {inp.tile}-cell tile")
    for name in ("land", "walkable", "nation", "region"):
        if getattr(inp, name).shape != (inp.size, inp.size):
            problems.append(f"{name} raster is not {inp.size} by {inp.size}")
    if problems:
        return problems
    if np.any(inp.walkable & ~inp.land):
        problems.append("a walkable cell lies outside land")
    if len(inp.nation_names) > 255 or len(inp.region_names) > 255:
        problems.append("more than 255 nations or regions do not fit the uint8 rasters")
    if np.any(inp.land & (inp.nation == 0)):
        problems.append("a land cell has no nominal nation")
    if np.any(inp.land & (inp.region == 0)):
        problems.append("a land cell has no terrain region")
    keys = [district.key for district in inp.districts]
    for key in sorted({key for key in keys if keys.count(key) > 1}):
        problems.append(f"{key}: duplicate district key")
    for district in inp.districts:
        if district.kind not in _DISTRICT_KINDS:
            problems.append(f"{district.key}: kind {district.kind!r} is not voronoi or region")
        x, y = district.landmark_cell
        if not (0 <= x < inp.size and 0 <= y < inp.size) or not inp.land[y, x]:
            problems.append(f"{district.key}: landmark cell {district.landmark_cell} is not land")
    return problems


def _label_fragments(domain_nation: np.ndarray, size: int, tile: int) -> np.ndarray:
    """Fragment ids per cell (-1 outside the domain), deterministically numbered.

    Tiles are stacked so a plane-only 4-neighbour structure labels every tile
    on its own; legal 8-direction steps under the corner rule connect exactly
    the 4-connected same-nation cells. Ids follow tile row-major order, then
    the fragment's first cell in row-major order.
    """
    count = size // tile
    stacked = domain_nation.reshape(count, tile, count, tile).transpose(0, 2, 1, 3)
    stacked = stacked.reshape(count * count, tile, tile)
    structure = np.zeros((3, 3, 3), dtype=bool)
    structure[1] = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
    labels = np.zeros(stacked.shape, dtype=np.int64)
    offset = 0
    for code in np.unique(stacked[stacked > 0]):
        labelled, found = ndimage.label(stacked == code, structure=structure)
        labels[labelled > 0] = labelled[labelled > 0] + offset
        offset += found
    flat = labels.ravel()
    present, first = np.unique(flat, return_index=True)
    order = np.argsort(first[present > 0], kind="stable")
    renumber = np.full(offset + 1, -1, dtype=np.int64)
    renumber[present[present > 0][order]] = np.arange(order.size)
    renumbered = renumber[labels]
    return renumbered.reshape(count, count, tile, tile).transpose(0, 2, 1, 3).reshape(size, size)


def _coarse_edges(cls: np.ndarray, fragment: np.ndarray, tile: int) -> list[list[tuple[int, int, int]]]:
    """Adjacency ``[(neighbour, cardinal steps, diagonal steps)]`` per fragment."""
    size = cls.shape[0]
    pairs: list[np.ndarray] = []

    def add(first_frag, second_frag, legal, diagonal):
        u = first_frag[legal]
        v = second_frag[legal]
        kind = np.full(u.shape, diagonal, dtype=np.int64)
        pairs.append(np.stack([u, v, kind], axis=1))
        pairs.append(np.stack([v, u, kind], axis=1))

    # Cardinal one-kilometre steps across a vertical / horizontal tile edge.
    xs = np.arange(tile - 1, size - 1, tile)
    left, right = cls[:, xs], cls[:, xs + 1]
    add(fragment[:, xs], fragment[:, xs + 1], (left > 0) & (left == right), 0)
    ys = np.arange(tile - 1, size - 1, tile)
    below, above = cls[ys, :], cls[ys + 1, :]
    add(fragment[ys, :], fragment[ys + 1, :], (below > 0) & (below == above), 0)
    # Diagonal one-kilometre steps across a tile corner: legal only when all
    # four cells around the corner share one nation inside the domain.
    grid_y, grid_x = np.meshgrid(ys, xs, indexing="ij")
    sw = cls[grid_y, grid_x]
    se = cls[grid_y, grid_x + 1]
    nw = cls[grid_y + 1, grid_x]
    ne = cls[grid_y + 1, grid_x + 1]
    open_corner = (sw > 0) & (sw == se) & (sw == nw) & (sw == ne)
    add(fragment[grid_y, grid_x], fragment[grid_y + 1, grid_x + 1], open_corner, 1)
    add(fragment[grid_y, grid_x + 1], fragment[grid_y + 1, grid_x], open_corner, 1)

    total = int(fragment.max()) + 1
    adjacency: list[list[tuple[int, int, int]]] = [[] for _ in range(total)]
    if not pairs:
        return adjacency
    edges = np.unique(np.concatenate(pairs), axis=0)
    for u, v, diagonal in edges.tolist():
        adjacency[u].append((v, 1 - diagonal, diagonal))
    return adjacency


def _dijkstra(
    adjacency: list[list[tuple[int, int, int]]],
    sources: dict[int, tuple[int, ...]],
) -> list[int]:
    """Owner rank (-1 unreached) of every fragment.

    ``sources`` maps a district rank to its zero-distance fragments. Labels
    are ordered by exact distance (integer pair ``a + b*sqrt(2)``, compared
    through the float key: distinct pairs never tie in the reals and their
    gap far exceeds rounding), then by rank, then by fragment id.
    """
    owner = [-1] * len(adjacency)
    best: list[tuple[float, int] | None] = [None] * len(adjacency)
    heap: list[tuple[float, int, int, int, int]] = []
    for rank in sorted(sources):
        for fragment in sources[rank]:
            if best[fragment] is None or (0.0, rank) < best[fragment]:
                best[fragment] = (0.0, rank)
                heapq.heappush(heap, (0.0, rank, fragment, 0, 0))
    while heap:
        _, rank, fragment, cardinal, diagonal = heapq.heappop(heap)
        if owner[fragment] != -1:
            continue
        owner[fragment] = rank
        for neighbour, step_cardinal, step_diagonal in adjacency[fragment]:
            if owner[neighbour] != -1:
                continue
            a, b = cardinal + step_cardinal, diagonal + step_diagonal
            label = (a + b * _SQRT2, rank)
            if best[neighbour] is None or label < best[neighbour]:
                best[neighbour] = label
                heapq.heappush(heap, (label[0], rank, neighbour, a, b))
    return owner


def _settle_unseeded(inp, cls, fragment, adjacency, fragment_owner, owner, claimed) -> list[str]:
    """Settle unreached fragments; return a problem per unseeded component.

    A component whose every surrounding cell (all eight directions) is
    footprint land claimed by one grid landmark is a pocket enclosed by that
    settlement's footprint: nobody can walk into it, so it belongs to the
    footprint's district like the footprint itself. Any other unreached
    component is an unseeded legal component and fails generation.
    """
    unreached = [index for index, rank in enumerate(fragment_owner) if rank == -1]
    if not unreached:
        return []
    seen: set[int] = set()
    problems = []
    ring = np.ones((3, 3), dtype=bool)
    for start in unreached:
        if start in seen:
            continue
        component = [start]
        seen.add(start)
        for current in component:
            for neighbour, _, _ in adjacency[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    component.append(neighbour)
        cells = np.isin(fragment, component)
        border = ndimage.binary_dilation(cells, structure=ring) & ~cells
        codes = set(owner[border].tolist())
        nations = set(inp.nation[cells | border].tolist())
        if bool(np.all(claimed[border])) and len(codes) == 1 and len(nations) == 1:
            rank = codes.pop() - 1
            for index in component:
                fragment_owner[index] = rank
            continue
        ys, xs = np.nonzero(cells)
        y, x = int(ys[0]), int(xs[0])
        nation = inp.nation_names[int(cls[y, x]) - 1]
        problems.append(
            f"unseeded walkable component at cell {(x, y)} in nation {nation!r} "
            f"({int(cells.sum())} cells): add a Voronoi landmark inside it"
        )
    return problems


def _display_owner(inp, owner, candidates, rank_of_code, x, y) -> int:
    """Nearest candidate owner code for display cell ``(x, y)``, or 0."""
    nation = inp.nation[y, x]
    best: tuple[int, int, int, int] | None = None
    radius = 1
    while radius <= DISPLAY_SEARCH_RADIUS and (best is None or radius * radius <= best[0]):
        for dy in range(-radius, radius + 1):
            ny = y + dy
            if not 0 <= ny < inp.size:
                continue
            step = 1 if abs(dy) == radius else 2 * radius
            for dx in range(-radius, radius + 1, step):
                nx = x + dx
                if not 0 <= nx < inp.size or not candidates[ny, nx] or inp.nation[ny, nx] != nation:
                    continue
                code = int(owner[ny, nx])
                label = (dx * dx + dy * dy, rank_of_code[code], ny, nx)
                if best is None or label < best:
                    best = label
        radius += 1
    return 0 if best is None else int(owner[best[2], best[3]])


def compute_partition(inp: PartitionInput) -> Partition:
    """Partition every land cell of ``inp``; raises :class:`PartitionError`."""
    problems = _check_input(inp)
    if problems:
        raise PartitionError(problems)
    size = inp.size
    keys = tuple(sorted(district.key for district in inp.districts))
    code_of = {key: index + 1 for index, key in enumerate(keys)}
    rank_of_code = {code: code - 1 for code in code_of.values()}
    owner = np.zeros((size, size), dtype=np.int16)

    region_owned = np.zeros((size, size), dtype=bool)
    for district in sorted(inp.districts, key=lambda d: d.key):
        if district.kind != "region":
            continue
        if district.region_key not in inp.region_names:
            problems.append(f"{district.key}: region_key {district.region_key!r} is not a region")
            continue
        mask = inp.land & (inp.region == inp.region_names.index(district.region_key) + 1)
        if np.any(region_owned & mask):
            problems.append(f"{district.key}: region {district.region_key!r} is claimed twice")
        owner[mask] = code_of[district.key]
        region_owned |= mask

    domain = inp.land & inp.walkable & ~region_owned
    cls = np.where(domain, inp.nation, 0).astype(np.int16)
    fragment = _label_fragments(cls, size, inp.tile)
    adjacency = _coarse_edges(cls, fragment, inp.tile)

    claimed = np.zeros((size, size), dtype=bool)
    sources: dict[str, tuple[int, ...]] = {}
    landmark_cells = {district.key: district.landmark_cell for district in inp.districts}
    for district in sorted(inp.districts, key=lambda d: d.key):
        if district.kind != "voronoi":
            continue
        lx, ly = district.landmark_cell
        if region_owned[ly, lx]:
            problems.append(f"{district.key}: landmark {district.landmark_cell} lies in region land")
            continue
        if district.approaches is None:
            if not domain[ly, lx]:
                problems.append(
                    f"{district.key}: landmark {district.landmark_cell} is not walkable Voronoi ground"
                )
                continue
            sources[district.key] = (int(fragment[ly, lx]),)
            continue
        # Grid landmark: only same-nation domain approaches inject the seed.
        found = sorted(
            {
                int(fragment[y, x])
                for x, y in district.approaches
                if 0 <= x < size and 0 <= y < size and domain[y, x]
                and inp.nation[y, x] == inp.nation[ly, lx]
            }
        )
        if not found:
            problems.append(
                f"{district.key}: no routed same-nation walkable gateway approach for "
                f"landmark {district.landmark_cell}"
            )
            continue
        sources[district.key] = tuple(found)
        if district.landmark_cell not in district.footprint:
            continue
        footprint_problems = []
        for other, cell in landmark_cells.items():
            if other != district.key and cell in district.footprint:
                footprint_problems.append(f"footprint also holds the landmark of {other!r}")
        cells = sorted(
            (c for c in district.footprint if 0 <= c[0] < size and 0 <= c[1] < size and inp.land[c[1], c[0]]),
            key=lambda c: (c[1], c[0]),
        )
        for x, y in cells:
            if inp.walkable[y, x]:
                footprint_problems.append(f"footprint cell {(x, y)} is walkable")
            elif region_owned[y, x]:
                footprint_problems.append(f"footprint cell {(x, y)} lies in region land")
            elif inp.nation[y, x] != inp.nation[ly, lx]:
                footprint_problems.append(f"footprint cell {(x, y)} crosses a national border")
            elif claimed[y, x]:
                footprint_problems.append(f"footprint cell {(x, y)} is claimed twice")
        if footprint_problems:
            problems.extend(f"{district.key}: {rule}" for rule in footprint_problems)
            continue
        for x, y in cells:
            claimed[y, x] = True
            owner[y, x] = code_of[district.key]
    if problems:
        raise PartitionError(problems)

    fragment_owner = _dijkstra(
        adjacency, {code_of[key] - 1: frags for key, frags in sources.items()}
    )
    problems = _settle_unseeded(
        inp, cls, fragment, adjacency, fragment_owner, owner, claimed
    )
    if problems:
        raise PartitionError(problems)
    codes = np.asarray(fragment_owner, dtype=np.int16) + 1
    in_domain = fragment >= 0
    owner[in_domain] = codes[fragment[in_domain]]

    primary = region_owned | in_domain | claimed
    candidates = in_domain | claimed
    pending_y, pending_x = np.nonzero(inp.land & ~primary)
    display = []
    for y, x in zip(pending_y.tolist(), pending_x.tolist()):
        code = _display_owner(inp, owner, candidates, rank_of_code, x, y)
        if code == 0:
            problems.append(f"land cell {(x, y)} has no same-nation owner within reach")
        display.append((y, x, code))
    for y, x, code in display:
        owner[y, x] = code

    for district in inp.districts:
        x, y = district.landmark_cell
        if int(owner[y, x]) != code_of[district.key]:
            problems.append(f"{district.key}: landmark {district.landmark_cell} is not in its own district")
    if np.any(inp.land & (owner == 0)) and not problems:
        problems.append("a land cell has no owner")
    if np.any(~inp.land & (owner != 0)):
        problems.append("a sea cell has an owner")
    if problems:
        raise PartitionError(problems)
    return Partition(keys, owner, primary, domain, fragment, sources)


# --------------------------------------------------------------------------
# Outlines

_LEFT_TURN = {(1, 0): (0, 1), (0, 1): (-1, 0), (-1, 0): (0, -1), (0, -1): (1, 0)}


def _boundary_edges(owner: np.ndarray, nation_land: np.ndarray):
    """Directed unit edges with the owning district on the left.

    Returns ``{(code, start): [end, ...]}`` plus the undirected edge types
    ``{frozenset(start, end): (low code, high code, national)}``.
    """
    size = owner.shape[0]
    padded = np.zeros((size + 2, size + 2), dtype=owner.dtype)
    padded[1:-1, 1:-1] = owner
    nations = np.zeros((size + 2, size + 2), dtype=nation_land.dtype)
    nations[1:-1, 1:-1] = nation_land
    outgoing: dict[tuple[int, Cell], list[Cell]] = {}
    types: dict[frozenset, tuple[int, int, bool]] = {}

    def record(code, start, end):
        outgoing.setdefault((code, start), []).append(end)

    # Horizontal lattice lines: cell (x, y-1) below, (x, y) above.
    below, above = padded[:-1, 1:-1], padded[1:, 1:-1]
    ys, xs = np.nonzero(below != above)
    n_below, n_above = nations[:-1, 1:-1], nations[1:, 1:-1]
    for y, x in zip(ys.tolist(), xs.tolist()):
        low, high = int(below[y, x]), int(above[y, x])
        national = bool(n_below[y, x] and n_above[y, x] and n_below[y, x] != n_above[y, x])
        start, end = (x, y), (x + 1, y)
        types[frozenset((start, end))] = (min(low, high), max(low, high), national)
        if high:
            record(high, start, end)  # bottom edge of the upper cell: east
        if low:
            record(low, end, start)  # top edge of the lower cell: west
    # Vertical lattice lines: cell (x-1, y) left, (x, y) right.
    left, right = padded[1:-1, :-1], padded[1:-1, 1:]
    ys, xs = np.nonzero(left != right)
    n_left, n_right = nations[1:-1, :-1], nations[1:-1, 1:]
    for y, x in zip(ys.tolist(), xs.tolist()):
        west, east = int(left[y, x]), int(right[y, x])
        national = bool(n_left[y, x] and n_right[y, x] and n_left[y, x] != n_right[y, x])
        start, end = (x, y), (x, y + 1)
        types[frozenset((start, end))] = (min(west, east), max(west, east), national)
        if west:
            record(west, start, end)  # right edge of the western cell: north
        if east:
            record(east, end, start)  # left edge of the eastern cell: south
    return outgoing, types


def _junctions(types) -> set[Cell]:
    """Vertices where the boundary branches or changes type."""
    incident: dict[Cell, list[tuple[int, int, bool]]] = {}
    for edge, kind in types.items():
        for vertex in edge:
            incident.setdefault(vertex, []).append(kind)
    return {
        vertex
        for vertex, kinds in incident.items()
        if len(kinds) != 2 or kinds[0] != kinds[1]
    }


def _trace_rings(code: int, outgoing, starts: list[Cell]) -> list[list[Cell]]:
    """Closed vertex rings of one district (district on the left)."""
    edges = sorted(
        ((start, end) for start in starts for end in outgoing[(code, start)]),
        key=lambda e: (e[0][1], e[0][0], e[1][1], e[1][0]),
    )
    used: set[tuple[Cell, Cell]] = set()
    rings = []
    for first in edges:
        if first in used:
            continue
        ring = [first[0]]
        start, end = first
        used.add(first)
        while True:
            ring.append(end)
            if end == ring[0]:
                break  # closed; a pinch at the start yields a separate ring
            direction = (end[0] - start[0], end[1] - start[1])
            options = [e for e in outgoing.get((code, end), ()) if (end, e) not in used]
            if not options:
                break
            left = _LEFT_TURN[direction]
            right = (-left[0], -left[1])
            preference = (left, direction, right)
            options.sort(key=lambda e: preference.index((e[0] - end[0], e[1] - end[1])))
            start, end = end, options[0]
            used.add((start, end))
        if ring[-1] != ring[0]:
            raise PartitionError([f"district outline at {ring[0]} does not close"])
        rings.append(ring[:-1])
    return rings


def _canonical(piece: tuple[Cell, ...], closed: bool) -> tuple[tuple[Cell, ...], bool]:
    """``(canonical sequence, reversed?)`` shared by both sides of a piece."""
    backward = tuple(reversed(piece))
    if closed:
        def rotate(seq):
            index = min(range(len(seq) - 1), key=lambda i: (seq[i][1], seq[i][0]))
            body = seq[:-1]
            body = body[index:] + body[:index]
            return body + (body[0],)

        forward_c, backward_c = rotate(piece), rotate(backward)
        return (forward_c, False) if forward_c <= backward_c else (backward_c, True)
    return (piece, False) if piece <= backward else (backward, True)


def _douglas_peucker(points: list[Cell], tolerance: int) -> list[Cell]:
    """Integer Douglas-Peucker keeping both ends (handles a closed loop)."""
    if len(points) < 3:
        return list(points)
    if points[0] == points[-1]:
        x0, y0 = points[0]
        far = max(
            range(1, len(points) - 1),
            key=lambda i: ((points[i][0] - x0) ** 2 + (points[i][1] - y0) ** 2, -i),
        )
        head = _douglas_peucker(points[: far + 1], tolerance)
        return head[:-1] + _douglas_peucker(points[far:], tolerance)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    limit = tolerance * tolerance
    while stack:
        first, last = stack.pop()
        (ax, ay), (bx, by) = points[first], points[last]
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        best, best_index = -1, -1
        for index in range(first + 1, last):
            px, py = points[index]
            # Squared perpendicular distance scaled by the squared segment
            # length, so the comparison stays exact integer arithmetic.
            cross = dx * (py - ay) - dy * (px - ax)
            scaled = cross * cross
            if scaled > limit * length and scaled > best:
                best, best_index = scaled, index
        if best_index != -1:
            keep[best_index] = True
            stack.append((first, best_index))
            stack.append((best_index, last))
    return [point for point, kept in zip(points, keep) if kept]


def _smooth(piece: tuple[Cell, ...], national: bool) -> list[Cell]:
    """Metre geometry of one canonical piece; its two ends stay exact."""
    if national:
        points = [(x * CELL_M, y * CELL_M) for x, y in piece]
        kept = [points[0]]
        for previous, current, following in zip(points, points[1:], points[2:]):
            if (current[0] - previous[0]) * (following[1] - current[1]) != (
                current[1] - previous[1]
            ) * (following[0] - current[0]):
                kept.append(current)
        kept.append(points[-1])
        return kept
    half = CELL_M // 2
    points = [(piece[0][0] * CELL_M, piece[0][1] * CELL_M)]
    points += [((a[0] + b[0]) * half, (a[1] + b[1]) * half) for a, b in zip(piece, piece[1:])]
    points.append((piece[-1][0] * CELL_M, piece[-1][1] * CELL_M))
    return _douglas_peucker(points, OUTLINE_TOLERANCE_M)


def compute_outlines(partition: Partition, inp: PartitionInput) -> dict[str, list[list[Cell]]]:
    """Smoothed outline rings (metres) per district key.

    Rings keep the district on their left: outer rings run counter-clockwise
    and holes clockwise in the east/north frame. A piece between two
    junctions is smoothed once and shared, reversed, by its neighbour.
    """
    nation_land = np.where(inp.land, inp.nation, 0)
    outgoing, types = _boundary_edges(partition.owner, nation_land)
    junctions = _junctions(types)
    starts: dict[int, list[Cell]] = {}
    for code, start in outgoing:
        starts.setdefault(code, []).append(start)
    cache: dict[tuple[tuple[Cell, ...], bool], list[Cell]] = {}
    outlines: dict[str, list[list[Cell]]] = {}
    for index, key in enumerate(partition.keys):
        rings = []
        for ring in _trace_rings(index + 1, outgoing, starts.get(index + 1, [])):
            cuts = [i for i, vertex in enumerate(ring) if vertex in junctions]
            if cuts:
                ring = ring[cuts[0] :] + ring[: cuts[0]]
                cuts = [i - cuts[0] for i in cuts]
                bounds = list(zip(cuts, cuts[1:] + [len(ring)]))
                pieces = [
                    tuple(ring[a : b + 1]) if b < len(ring) else tuple(ring[a:] + ring[:1])
                    for a, b in bounds
                ]
            else:
                pieces = [tuple(ring + ring[:1])]
            geometry: list[Cell] = []
            for piece in pieces:
                closed = not cuts
                canonical, flipped = _canonical(piece, closed)
                national = types[frozenset(canonical[:2])][2]
                cache_key = (canonical, closed)
                if cache_key not in cache:
                    cache[cache_key] = _smooth(canonical, national)
                points = cache[cache_key]
                if flipped:
                    points = list(reversed(points))
                geometry.extend(points[:-1])
            rings.append(geometry)
        outlines[key] = rings
    return outlines


# --------------------------------------------------------------------------
# Encoding


def _runs(values: Iterable[int]) -> list[int]:
    """Flat ``[value, count, value, count, ...]`` run-length encoding."""
    runs: list[int] = []
    for value in values:
        if runs and runs[-2] == value:
            runs[-1] += 1
        else:
            runs.extend((int(value), 1))
    return runs


def _raster_digest(inp: PartitionInput) -> str:
    digest = hashlib.sha256()
    for name in ("land", "walkable", "nation", "region"):
        raster = np.ascontiguousarray(getattr(inp, name)).astype("<u1")
        digest.update(name.encode())
        digest.update(raster.tobytes())
    digest.update(json.dumps([inp.nation_names, inp.region_names]).encode())
    return digest.hexdigest()


def fingerprint(inp: PartitionInput) -> str:
    """SHA-256 of the algorithm version, frame, districts and input rasters."""
    canonical = {
        "algorithm": ALGORITHM_VERSION,
        "frame_cells": inp.size,
        "tile_cells": inp.tile,
        "tolerance_m": OUTLINE_TOLERANCE_M,
        "districts": [
            {
                "key": d.key,
                "kind": d.kind,
                "region_key": d.region_key,
                "landmark_cell": list(d.landmark_cell),
                "approaches": None if d.approaches is None else sorted(map(list, d.approaches)),
                "footprint": sorted(map(list, d.footprint)),
            }
            for d in sorted(inp.districts, key=lambda d: d.key)
        ],
        "rasters": _raster_digest(inp),
    }
    text = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def encode(partition: Partition, inp: PartitionInput) -> dict:
    """The frozen document (plain JSON types, integers only)."""
    tile, count = inp.tile, inp.size // inp.tile
    owner = partition.owner.astype(np.int32)
    big = np.int32(1 << 20)
    low = np.where(inp.land, owner, big).reshape(count, tile, count, tile).min(axis=(1, 3))
    high = np.where(inp.land, owner, -1).reshape(count, tile, count, tile).max(axis=(1, 3))
    coarse = np.where(high < 0, 0, np.where(low == high, low, MIXED))
    exceptions = []
    for ty, tx in zip(*np.nonzero(coarse == MIXED)):
        block = owner[ty * tile : (ty + 1) * tile, tx * tile : (tx + 1) * tile]
        exceptions.append([int(tx), int(ty), *_runs(block.ravel().tolist())])
    outlines = compute_outlines(partition, inp)
    return {
        "version": ALGORITHM_VERSION,
        "fingerprint": fingerprint(inp),
        "frame_cells": inp.size,
        "tile_cells": tile,
        "districts": list(partition.keys),
        "coarse": [_runs(row) for row in coarse.tolist()],
        "exceptions": exceptions,
        "outlines": {
            key: [[value for point in ring for value in point] for ring in rings]
            for key, rings in outlines.items()
        },
    }


def serialize(document: dict) -> str:
    """Deterministic, line-oriented JSON text (one row or ring per line)."""

    def compact(value) -> str:
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)

    def listing(items: list[str], indent: str) -> str:
        if not items:
            return "[]"
        return "[\n" + ",\n".join(indent + "  " + item for item in items) + "\n" + indent + "]"

    lines = ["{"]
    scalars = ("version", "fingerprint", "frame_cells", "tile_cells", "districts")
    for key in scalars:
        lines.append(f"  {compact(key)}: {compact(document[key])},")
    lines.append(f'  "coarse": {listing([compact(r) for r in document["coarse"]], "  ")},')
    lines.append(f'  "exceptions": {listing([compact(r) for r in document["exceptions"]], "  ")},')
    outline_items = [
        f"{compact(key)}: {listing([compact(r) for r in document['outlines'][key]], '    ')}"
        for key in sorted(document["outlines"])
    ]
    if outline_items:
        body = ",\n".join("    " + item for item in outline_items)
        lines.append('  "outlines": {\n' + body + "\n  }")
    else:
        lines.append('  "outlines": {}')
    lines.append("}")
    return "\n".join(lines) + "\n"


def generate(inp: PartitionInput) -> str:
    """Partition, encode and serialize ``inp`` (the complete artifact text)."""
    return serialize(encode(compute_partition(inp), inp))


# --------------------------------------------------------------------------
# Production inputs (needs a configured Django/Evennia environment)


def _production_districts(size: int) -> tuple[DistrictSeed, ...]:
    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.anchors import LOCAL_FRAME_ANCHOR_REGISTRY, world_position_m
    from world.lore import map_districts, wilderness_entry
    from world.maps.map_data import settlement_graph
    from world.rules.map_knowledge import decode_node

    entries = wilderness_entry.WILDERNESS_ENTRY_REGISTRY
    seeds = []
    for district in map_districts.MAP_DISTRICT_REGISTRY.values():
        parts = decode_node(district.landmark_node)
        if parts["prefix"] == "wild":
            seeds.append(
                DistrictSeed(
                    district.key, district.kind, (parts["x"], parts["y"]), district.region_key
                )
            )
            continue
        map_key, xy = parts["z_map_key"], (parts["x"], parts["y"])
        graph = settlement_graph(map_key)
        node = graph.node_at(xy) if graph is not None else None
        anchor_key = next(
            (
                placement.anchor_key
                for placement in ANCHOR_PLACEMENT_REGISTRY.values()
                if placement.zcoord == map_key and placement.anchor_key in LOCAL_FRAME_ANCHOR_REGISTRY
            ),
            None,
        )
        if node is None or anchor_key is None:
            raise PartitionError([f"{district.key}: grid landmark {district.landmark_node} does not resolve"])
        cell = map_districts.cell_of_position(world_position_m(anchor_key, node.physical_coordinate))
        approaches = []
        footprint: frozenset[Cell] = frozenset()
        for entry in entries.values():
            if cell in entry.footprint_cells:
                footprint = entry.footprint_cells
            for gate in entry.gates:
                gate_node = graph.node_at(gate.grid_xy) if gate.z_map_key == map_key else None
                approach = entry.approach_cell(gate)
                if gate_node is None or approach is None:
                    continue
                if graph.route(gate_node.node_id, node.node_id) is not None:
                    approaches.append(approach)
        seeds.append(
            DistrictSeed(
                district.key,
                district.kind,
                cell,
                district.region_key,
                tuple(sorted(set(approaches))),
                footprint,
            )
        )
    return tuple(seeds)


def production_input() -> PartitionInput:
    """Rasterize the live terrain model and district registry."""
    from world.lore import wilderness_entry
    from world.lore.nations import NATION_REGISTRY
    from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
    from world.maps import wilderness_provider as provider
    from world.maps.wilderness_reachability import _mainland_row_intervals

    size = provider.WILDERNESS_MAX_X + 1
    nation_names = tuple(sorted(NATION_REGISTRY))
    region_names = tuple(sorted(WILDERNESS_REGION_REGISTRY))
    nation_code = {name: index + 1 for index, name in enumerate(nation_names)}
    region_code = {name: index + 1 for index, name in enumerate(region_names)}
    land = np.zeros((size, size), dtype=bool)
    walkable = np.zeros((size, size), dtype=bool)
    nation = np.zeros((size, size), dtype=np.uint8)
    region = np.zeros((size, size), dtype=np.uint8)
    passable = provider.is_passable_terrain
    nation_of = provider.nominal_nation_for_coordinates
    region_of = provider.region_for_coordinates
    for y in range(size):
        for west, east in _mainland_row_intervals(y):
            xs = range(west, east + 1)
            land[y, west : east + 1] = True
            walkable[y, west : east + 1] = [passable((x, y)) for x in xs]
            nation[y, west : east + 1] = [nation_code[nation_of(x, y)] for x in xs]
            region[y, west : east + 1] = [region_code[region_of(x, y)] for x in xs]
    for entry in wilderness_entry.WILDERNESS_ENTRY_REGISTRY.values():
        for x, y in entry.footprint_cells:
            walkable[y, x] = False
    return PartitionInput(
        size=size,
        land=land,
        walkable=walkable,
        nation=nation,
        nation_names=nation_names,
        region=region,
        region_names=region_names,
        districts=_production_districts(size),
    )


def _bootstrap() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django

    django.setup()
    import evennia

    evennia._init()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the frozen map-district partition.")
    parser.add_argument("--check", action="store_true", help="fail when the committed file is stale")
    parser.add_argument("--output", type=Path, default=DATA_PATH)
    args = parser.parse_args(argv)
    _bootstrap()
    text = generate(production_input())
    current = args.output.read_text(encoding="utf-8") if args.output.exists() else None
    if args.check:
        if current != text:
            print(f"{args.output} is stale; run: uv run --locked python -m tools.map_district_partition")
            return 1
        print(f"{args.output} is up to date")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output} ({len(text.encode())} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
