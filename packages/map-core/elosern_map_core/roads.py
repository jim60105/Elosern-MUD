"""Offline wilderness road network generation over an explicit input snapshot.

The generator turns the authored map sources into the frozen road artifact
read by :mod:`elosern_map_core.roads_codec`. It imports NumPy and SciPy, which
live in the ``generation`` extra; nothing on the runtime path imports it.

Algorithm (official-roads design, change ``road-network-generation``):

1. Cost field. Open cells are walkable cells outside the forbidden regions and
   outside non-node point gateways (anchor footprints are already unwalkable).
   A step joins two open cells in eight directions; a diagonal also needs both
   orthogonal cells open. A step costs, in integer milliseconds, its length
   times the slower endpoint's terrain time, a slope factor from the elevation
   band difference and a seeded low-frequency noise factor. The weights are
   symmetric, so ``d(A, B) == d(B, A)``.
2. Terrain distance. ``d(A, B)`` is the cheapest path between any gate
   approach cell of ``A`` and any of ``B``. Two nodes are terrain neighbours
   when their regions in the multi-source nearest-node labelling touch.
3. Topology. A relative neighbourhood graph keeps a pair unless a third node
   is closer to both; detour repair then adds the terrain-neighbour pair with
   the worst network detour while it exceeds the configured limit.
4. Routing. Kept pairs are routed cheapest first; after each road, every step
   whose two ends are road cells costs the configured reuse fraction.
5. Self-check. :func:`verify_roads` re-derives the cost field and checks the
   candidate without reading any router state.

Byte equality is promised within one locked NumPy and SciPy environment:
between equal-cost paths, SciPy's heap order decides.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace

import numpy as np
from scipy import ndimage, sparse
from scipy.sparse.csgraph import dijkstra, shortest_path

from .authoring import (
    _DIRECTION_DELTAS,
    AuthoringWorld,
    gate_approach_cell,
    location_cells_of,
    terrain_definition,
)
from .elevation import DEFAULT_ELEVATION_CONFIG, ELEVATION_BAND_MAX, fractal_noise
from .partition import PartitionError, PartitionInputSnapshot, partition_input
from .roads_codec import encode_road_document, road_source_signature
from .terrain import NATION_KEYS

Cell = tuple[int, int]

#: The authored parameter document a road input requires.
ROAD_PARAMETER_PATH = "content/maps/road_network.yaml"
#: SciPy's marker for "no predecessor" and "no source".
_NONE = -9999
_SQRT2 = math.sqrt(2.0)
#: Undirected step directions; each is emitted in both directions.
_STEPS = ((1, 0), (0, 1), (1, 1), (-1, 1))


class RoadGenerationError(ValueError):
    """The road network cannot be generated; ``problems`` names every fault."""

    def __init__(self, problems: Iterable[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("road network generation failed:\n" + "\n".join(self.problems))


@dataclass(frozen=True)
class RoadNode:
    """One settlement the network joins, keyed by its location."""

    key: str
    approaches: tuple[Cell, ...]


@dataclass(frozen=True, eq=False)
class RoadInput:
    """Rasters indexed ``[y, x]`` plus nodes and parameters.

    ``region`` holds ``index + 1`` into ``region_names`` (0 = sea).
    ``blocked`` are non-node point anchors, which a road must never enter;
    ``point_gateways`` maps every point anchor to the cells its gates step
    into, which no road may step to from the anchor.
    """

    size: int
    walkable: np.ndarray
    region: np.ndarray
    region_names: tuple[str, ...]
    bands: np.ndarray
    region_speeds: Mapping[str, int]
    nodes: tuple[RoadNode, ...]
    blocked: frozenset[Cell]
    point_gateways: Mapping[Cell, frozenset[Cell]]
    forbidden_regions: tuple[str, ...]
    slope_factor_per_band: float
    noise_amplitude: float
    noise_wavelength_cells: float
    noise_seed: int
    detour_limit: float
    reuse_factor: float
    source_signature: str


@dataclass(frozen=True)
class Road:
    """One road: ``first < second``; cells run from first's gate to second's."""

    first: str
    second: str
    cells: tuple[Cell, ...]


# --------------------------------------------------------------------------
# Input assembly


def road_input(
    world: AuthoringWorld,
    bands: np.ndarray,
    region_speeds: Mapping[str, int],
    elevation_fingerprint: str,
) -> RoadInput:
    """Bind one loaded authoring world into an explicit road input."""
    params = world.road_network
    if params is None:
        raise RoadGenerationError(
            [f"{ROAD_PARAMETER_PATH}: the road parameter document is missing"]
        )
    location_cells = location_cells_of(world.locations)
    entries = [
        (settlement, settlement.wilderness_geometry(location_cells[settlement.location_ref]))
        for _, settlement in sorted(world.settlements.items())
        if settlement.wilderness_entry is not None
        and settlement.location_ref in location_cells
    ]
    footprints: set[Cell] = set()
    for _, geometry in entries:
        footprints.update(geometry.footprint_cells)
    region_names = tuple(sorted(world.continent.regions))
    try:
        rasters = partition_input(
            PartitionInputSnapshot(
                terrain=terrain_definition(world.continent),
                nation_names=NATION_KEYS,
                region_names=region_names,
                footprints=frozenset(footprints),
                districts=(),
                source_signature="",
            )
        )
    except PartitionError as error:
        raise RoadGenerationError(error.problems) from error
    size = rasters.size
    node_kinds = set(params.node_kinds)
    nodes: dict[str, RoadNode] = {}
    problems: list[str] = []
    blocked: set[Cell] = set()
    gateways: dict[Cell, frozenset[Cell]] = {}
    for settlement, geometry in entries:
        key = settlement.location_ref
        location = world.locations.locations[key]
        approaches = tuple(
            sorted(
                {
                    cell
                    for gate in geometry.gates
                    if (
                        cell := gate_approach_cell(
                            geometry, gate.return_direction, frame_cells=size
                        )
                    )
                    is not None
                }
            )
        )
        is_node = bool(approaches) and location.kind in node_kinds
        if is_node:
            if key in nodes:
                problems.append(f"node {key}: declared by more than one settlement")
            nodes[key] = RoadNode(key, approaches)
        anchor = geometry.anchor_cell
        if geometry.is_point_shape and anchor is not None:
            if not is_node:
                blocked.add(anchor)
            gateways[anchor] = frozenset(
                (anchor[0] + delta[0], anchor[1] + delta[1])
                for gate in geometry.gates
                if (delta := _DIRECTION_DELTAS.get(gate.return_direction)) is not None
            )
    if problems:
        raise RoadGenerationError(problems)
    return RoadInput(
        size=size,
        walkable=rasters.walkable,
        region=rasters.region,
        region_names=region_names,
        bands=np.asarray(bands).astype(np.int16),
        region_speeds=dict(region_speeds),
        nodes=tuple(nodes[key] for key in sorted(nodes)),
        blocked=frozenset(blocked),
        point_gateways=gateways,
        forbidden_regions=tuple(params.forbidden_regions),
        slope_factor_per_band=params.slope_factor_per_band,
        noise_amplitude=params.noise_amplitude,
        noise_wavelength_cells=params.noise_wavelength_cells,
        noise_seed=params.noise_seed,
        detour_limit=params.detour_limit,
        reuse_factor=params.reuse_factor,
        source_signature=road_source_signature(
            world.fingerprints,
            elevation_fingerprint=elevation_fingerprint,
            region_speeds=region_speeds,
        ),
    )


# --------------------------------------------------------------------------
# Cost field


def _in_frame(inp: RoadInput, cell: Cell) -> bool:
    return 0 <= cell[0] < inp.size and 0 <= cell[1] < inp.size


def _open_mask(inp: RoadInput) -> np.ndarray:
    """Walkable cells outside forbidden regions and non-node point gateways."""
    codes = [
        index + 1
        for index, name in enumerate(inp.region_names)
        if name in set(inp.forbidden_regions)
    ]
    mask = np.asarray(inp.walkable, dtype=bool) & ~np.isin(inp.region, codes)
    for x, y in inp.blocked:
        if 0 <= x < inp.size and 0 <= y < inp.size:
            mask[y, x] = False
    return mask


def _check_input(inp: RoadInput) -> list[str]:
    problems: list[str] = []
    if not inp.source_signature:
        problems.append("the road input carries no source signature")
    for name in ("walkable", "region", "bands"):
        if np.shape(getattr(inp, name)) != (inp.size, inp.size):
            problems.append(f"{name} raster is not {inp.size} by {inp.size}")
    if problems:
        return problems
    if inp.bands.size and (inp.bands.min() < 0 or inp.bands.max() > ELEVATION_BAND_MAX):
        problems.append(f"an elevation band lies outside 0..{ELEVATION_BAND_MAX}")
    if inp.region.size and int(inp.region.max()) > len(inp.region_names):
        problems.append("a region code lies outside the declared region names")
        return problems
    open_cells = _open_mask(inp)
    for code in sorted({int(value) for value in np.unique(inp.region[open_cells])}):
        name = inp.region_names[code - 1] if 0 < code <= len(inp.region_names) else None
        if name is None:
            problems.append(f"an open cell has undeclared region code {code}")
            continue
        speed = inp.region_speeds.get(name)
        if isinstance(speed, bool) or not isinstance(speed, (int, float)) or speed <= 0:
            problems.append(f"region {name}: has no travel speed")
    keys = [node.key for node in inp.nodes]
    for key in sorted({key for key in keys if keys.count(key) > 1}):
        problems.append(f"node {key}: duplicate node key")
    owners: dict[Cell, str] = {}
    for node in inp.nodes:
        if not node.approaches:
            problems.append(f"node {node.key}: has no gate approach")
        for cell in node.approaches:
            if not _in_frame(inp, cell) or not open_cells[cell[1], cell[0]]:
                problems.append(
                    f"node {node.key}: gate approach {cell} is off the cost field"
                )
            other = owners.setdefault(cell, node.key)
            if other != node.key:
                problems.append(
                    f"node {node.key}: gate approach {cell} is shared with {other}"
                )
    return problems


@dataclass(eq=False)
class _CostField:
    index: np.ndarray       # int64 [y, x]: open-cell index or -1
    cells: np.ndarray       # int64 [n, 2]: (x, y) of each open index
    graph: sparse.csr_matrix
    base: np.ndarray        # the unreduced weight of each CSR entry
    rows: np.ndarray        # the source index of each CSR entry


def _cost_field(inp: RoadInput) -> _CostField:
    size = inp.size
    open_cells = _open_mask(inp)
    index = np.full((size, size), -1, dtype=np.int64)
    ys, xs = np.nonzero(open_cells)
    count = len(ys)
    index[ys, xs] = np.arange(count, dtype=np.int64)
    cells = np.stack([xs, ys], axis=1).astype(np.int64)

    seconds = np.zeros(len(inp.region_names) + 1, dtype=np.float64)
    for position, name in enumerate(inp.region_names):
        speed = inp.region_speeds.get(name)
        if speed:
            seconds[position + 1] = 3_600 * 1000 / float(speed)
    seconds_per_cell = seconds[inp.region]
    bands = inp.bands.astype(np.int16)
    if inp.noise_amplitude:
        wavelength = float(inp.noise_wavelength_cells)
        noise = fractal_noise(
            size,
            size,
            replace(
                DEFAULT_ELEVATION_CONFIG,
                seed=int(inp.noise_seed),
                base_wavelength=wavelength,
                warp_wavelength=2 * wavelength,
            ),
        )
    else:
        noise = None

    sources: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    weights: list[np.ndarray] = []
    for dx, dy in _STEPS:
        # Source cell (x, y) and target cell (x + dx, y + dy), both in frame.
        x0, x1 = max(0, -dx), size - max(0, dx)
        y0, y1 = 0, size - dy
        a = (slice(y0, y1), slice(x0, x1))
        b = (slice(y0 + dy, y1 + dy), slice(x0 + dx, x1 + dx))
        legal = open_cells[a] & open_cells[b]
        if dx and dy:
            legal &= open_cells[(slice(y0, y1), slice(x0 + dx, x1 + dx))]
            legal &= open_cells[(slice(y0 + dy, y1 + dy), slice(x0, x1))]
        step = _SQRT2 if dx and dy else 1.0
        factor = (
            1000.0
            * step
            * np.maximum(seconds_per_cell[a], seconds_per_cell[b])
            * (1.0 + inp.slope_factor_per_band * np.abs(bands[a] - bands[b]))
        )
        if noise is not None:
            factor = factor * (1.0 + inp.noise_amplitude * (noise[a] + noise[b]) / 2.0)
        weight = np.maximum(1.0, np.rint(factor))[legal]
        first = index[a][legal]
        second = index[b][legal]
        sources.extend((first, second))
        targets.extend((second, first))
        weights.extend((weight, weight))
    rows = np.concatenate(sources) if sources else np.zeros(0, dtype=np.int64)
    cols = np.concatenate(targets) if targets else np.zeros(0, dtype=np.int64)
    data = np.concatenate(weights) if weights else np.zeros(0, dtype=np.float64)
    graph = sparse.csr_matrix((data, (rows, cols)), shape=(count, count))
    graph.sort_indices()
    entry_rows = np.repeat(np.arange(count, dtype=np.int64), np.diff(graph.indptr))
    return _CostField(index, cells, graph, graph.data.copy(), entry_rows)


# --------------------------------------------------------------------------
# Topology and routing


def _node_indices(field: _CostField, node: RoadNode) -> np.ndarray:
    return np.array([field.index[y, x] for x, y in node.approaches], dtype=np.int64)


def _terrain_distances(field: _CostField, approach: list[np.ndarray]) -> np.ndarray:
    count = len(approach)
    distances = np.full((count, count), np.inf)
    for i, cells in enumerate(approach):
        reach = dijkstra(field.graph, directed=True, indices=cells, min_only=True)
        for j, other in enumerate(approach):
            distances[i, j] = reach[other].min()
    return np.minimum(distances, distances.T)


def _terrain_neighbours(field: _CostField, approach: list[np.ndarray]) -> set[tuple[int, int]]:
    flat = np.concatenate(approach)
    owner_of_source = np.full(field.graph.shape[0], -1, dtype=np.int64)
    for node, cells in enumerate(approach):
        owner_of_source[cells] = node
    _, _, sources = dijkstra(
        field.graph,
        directed=True,
        indices=flat,
        min_only=True,
        return_predecessors=True,
    )
    owner = np.full(field.graph.shape[0], -1, dtype=np.int64)
    reached = sources != _NONE
    owner[reached] = owner_of_source[sources[reached]]
    first = owner[field.rows]
    second = owner[field.graph.indices]
    touching = (first >= 0) & (second >= 0) & (first < second)
    return set(zip(first[touching].tolist(), second[touching].tolist()))


def _relative_neighbourhood(distances: np.ndarray) -> set[tuple[int, int]]:
    count = len(distances)
    kept: set[tuple[int, int]] = set()
    for i in range(count):
        for j in range(i + 1, count):
            dij = distances[i, j]
            if not np.isfinite(dij):
                continue
            if not np.any((distances[i] < dij) & (distances[:, j] < dij)):
                kept.add((i, j))
    return kept


def _repair(
    distances: np.ndarray,
    kept: set[tuple[int, int]],
    neighbours: set[tuple[int, int]],
    limit: float,
) -> set[tuple[int, int]]:
    count = len(distances)
    kept = set(kept)
    while True:
        weights = np.zeros((count, count))
        for i, j in kept:
            weights[i, j] = weights[j, i] = max(distances[i, j], 1.0)
        network = shortest_path(sparse.csr_matrix(weights), directed=False)
        worst: tuple[float, int, int] | None = None
        for i, j in sorted(neighbours - kept):
            direct = distances[i, j]
            if not np.isfinite(direct):
                continue
            through = network[i, j]
            ratio = np.inf if not np.isfinite(through) else through / max(direct, 1.0)
            if ratio > limit and (worst is None or ratio > worst[0]):
                worst = (ratio, i, j)
        if worst is None:
            return kept
        kept.add((worst[1], worst[2]))


def _route(field: _CostField, sources: np.ndarray, targets: np.ndarray) -> tuple[Cell, ...]:
    reach, predecessors, _ = dijkstra(
        field.graph,
        directed=True,
        indices=sources,
        min_only=True,
        return_predecessors=True,
    )
    target = min(
        (int(t) for t in targets),
        key=lambda t: (reach[t], int(field.cells[t, 1]), int(field.cells[t, 0])),
    )
    path = [target]
    while predecessors[path[-1]] != _NONE:
        path.append(int(predecessors[path[-1]]))
    path.reverse()
    return tuple((int(field.cells[i, 0]), int(field.cells[i, 1])) for i in path)


def compute_roads(inp: RoadInput) -> tuple[Road, ...]:
    """The candidate road network, sorted by its settlement pair."""
    problems = _check_input(inp)
    if problems:
        raise RoadGenerationError(problems)
    if not inp.nodes:
        return ()
    field = _cost_field(inp)
    approach = [_node_indices(field, node) for node in inp.nodes]
    distances = _terrain_distances(field, approach)
    kept = _relative_neighbourhood(distances)
    kept = _repair(distances, kept, _terrain_neighbours(field, approach), inp.detour_limit)
    keys = [node.key for node in inp.nodes]
    on_road = np.zeros(field.graph.shape[0], dtype=bool)
    reused = np.maximum(1.0, np.rint(field.base * inp.reuse_factor))
    roads: list[Road] = []
    for i, j in sorted(kept, key=lambda pair: (distances[pair], keys[pair[0]], keys[pair[1]])):
        cells = _route(field, approach[i], approach[j])
        roads.append(Road(keys[i], keys[j], cells))
        for x, y in cells:
            on_road[field.index[y, x]] = True
        both = on_road[field.rows] & on_road[field.graph.indices]
        field.graph.data[both] = reused[both]
    return tuple(sorted(roads, key=lambda road: (road.first, road.second)))


# --------------------------------------------------------------------------
# Self-check


def verify_roads(inp: RoadInput, roads: Sequence[Road]) -> list[str]:
    """Every fault of a candidate network, re-derived from the input alone."""
    problems: list[str] = []
    open_cells = _open_mask(inp)
    labels, _ = ndimage.label(open_cells)
    approaches = {node.key: set(node.approaches) for node in inp.nodes}

    def is_open(cell: Cell) -> bool:
        return _in_frame(inp, cell) and bool(open_cells[cell[1], cell[0]])

    parent = {key: key for key in approaches}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    served: set[str] = set()
    for road in roads:
        name = f"road {road.first}--{road.second}"
        cells = tuple(road.cells)
        served.update((road.first, road.second))
        for cell in cells:
            if not is_open(cell):
                problems.append(f"{name}: cell {cell} is off the cost field")
        for a, b in zip(cells, cells[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            legal = max(abs(dx), abs(dy)) == 1
            if legal and dx and dy:
                legal = is_open((a[0] + dx, a[1])) and is_open((a[0], a[1] + dy))
            if not legal:
                problems.append(f"{name}: illegal step {a} -> {b}")
        if (
            not cells
            or cells[0] not in approaches.get(road.first, ())
            or cells[-1] not in approaches.get(road.second, ())
        ):
            problems.append(f"{name}: does not end at gates of its settlements")
        components = {int(labels[y, x]) for x, y in cells if is_open((x, y))}
        if len(components) > 1:
            problems.append(f"{name}: joins separate networks")
        for a, b in zip(cells, cells[1:]):
            for anchor, other in ((a, b), (b, a)):
                if other in inp.point_gateways.get(anchor, ()):
                    problems.append(
                        f"{name}: leaves point gateway {anchor} in its gate direction"
                    )
        if road.first in parent and road.second in parent:
            parent[find(road.first)] = find(road.second)

    for node in inp.nodes:
        if node.key not in served:
            problems.append(f"node {node.key}: has no road")
    networks: dict[int, list[str]] = {}
    for node in inp.nodes:
        for label in sorted({int(labels[y, x]) for x, y in node.approaches if is_open((x, y))}):
            networks.setdefault(label, []).append(node.key)
    for label, keys in sorted(networks.items()):
        root = find(keys[0])
        apart = [key for key in keys if find(key) != root]
        if apart:
            problems.append(f"network {label}: nodes {', '.join(apart)} are not connected")
    return problems


# --------------------------------------------------------------------------
# Output


def encode_roads(inp: RoadInput, roads: Sequence[Road]) -> str:
    """The canonical artifact text of one network."""
    return encode_road_document(
        frame_cells=inp.size,
        source_signature=inp.source_signature,
        nodes=[node.key for node in inp.nodes],
        roads=[(road.first, road.second, road.cells) for road in roads],
    )


def generate_road_network(inp: RoadInput) -> str:
    """Check, compute, self-check and encode; any problem raises."""
    problems = _check_input(inp)
    if problems:
        raise RoadGenerationError(problems)
    roads = compute_roads(inp)
    problems = verify_roads(inp, roads)
    if problems:
        raise RoadGenerationError(problems)
    return encode_roads(inp, roads)


__all__ = [
    "Cell",
    "ROAD_PARAMETER_PATH",
    "Road",
    "RoadGenerationError",
    "RoadInput",
    "RoadNode",
    "compute_roads",
    "encode_roads",
    "generate_road_network",
    "road_input",
    "verify_roads",
]
