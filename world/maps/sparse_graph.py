"""Sparse authored settlement graphs and their deterministic route adapter.

A settlement is declared as stable identity nodes (``SparseNode``) at integer
coordinates plus explicit roads (``SparseRoad``) between them. Route finding
walks only those declared nodes and roads: memory and work scale with the graph,
never with the coordinate span, so meter-scale coordinates never allocate a
meter-sized lattice (world-map-scale design §11).

The module is pure Python: no Django or Evennia imports, so lore/quest modules
may read the declarations without touching the database. The map layer
(``world.maps.bootstrap``) owns the persistent ``XYZRoom``/``XYZExit``
convergence built on top of these declarations.

Stable identity is the synchronizer's matching authority. A node's identity is
its authored ``node_id``; its coordinate is a mutable binding. A road's identity
is its ordered endpoint pair. Coordinates are never used as runtime aliases:
they are only the deterministic one-time convergence input for rooms that were
spawned before identity binding existed (design decision: "stable authored node
keys are added as the synchronizer's matching authority").
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import hypot
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

# Compass short keys, matching the xyzgrid contrib's own MAPSCAN vocabulary so
# spawned exit keys stay the answers players and tests already search for.
_COMPASS_BY_DELTA = {
    (0, 1): "n",
    (1, 1): "ne",
    (1, 0): "e",
    (1, -1): "se",
    (0, -1): "s",
    (-1, -1): "sw",
    (-1, 0): "w",
    (-1, 1): "nw",
}

# The default spawn key/aliases per compass direction (xyzgrid's
# ``MapNode.direction_spawn_defaults``). Kept here so route planning can name
# the exit a step traverses without importing the contrib.
_EXIT_SPAWN_DEFAULTS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "n": ("north", "n"),
        "ne": ("northeast", "ne", "north-east"),
        "e": ("east", "e"),
        "se": ("southeast", "se", "south-east"),
        "s": ("south", "s"),
        "sw": ("southwest", "sw", "south-west"),
        "w": ("west", "w"),
        "nw": ("northwest", "nw", "north-west"),
        "d": ("down", "d", "do"),
        "u": ("up", "u"),
    }
)


def exit_spawn_names(direction: str) -> tuple[str, ...]:
    """Return the authored ``(key, alias, ...)`` spawn surface for a direction."""

    return _EXIT_SPAWN_DEFAULTS[direction]


class SparseGraphError(ValueError):
    """An authored sparse graph is malformed or binds conflicting identities."""


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def compass_direction(dx: int, dy: int) -> str:
    """Return the compass short key for a non-zero integer delta.

    The sign of each axis selects the direction; a diagonal that is not a
    perfect 45-degree step still names its quadrant, exactly as the xyzgrid
    parser does for its visual links.
    """

    if not _is_int(dx) or not _is_int(dy):
        raise SparseGraphError("road deltas must be integers")
    if dx == 0 and dy == 0:
        raise SparseGraphError("a road segment cannot have zero length")
    sx = 0 if dx == 0 else (1 if dx > 0 else -1)
    sy = 0 if dy == 0 else (1 if dy > 0 else -1)
    return _COMPASS_BY_DELTA[(sx, sy)]


@dataclass(frozen=True, slots=True)
class SparseNode:
    """One authored location with a stable identity and a mutable coordinate.

    ``prototype`` is the room prototype mapping applied by the synchronizer
    (``prototype_parent``, ``key``, ``desc`` and any Attribute keys). A node
    prototype must be a mapping; the synchronizer resolves its typeclass.
    """

    node_id: str
    x: int
    y: int
    prototype: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(self.node_id, str) or not self.node_id:
            raise SparseGraphError("node_id must be a non-empty string")
        if not _is_int(self.x) or not _is_int(self.y):
            raise SparseGraphError(f"node {self.node_id!r} coordinate must be an integer pair")
        if not isinstance(self.prototype, Mapping) or not self.prototype:
            raise SparseGraphError(f"node {self.node_id!r} needs a room prototype mapping")

    @property
    def coordinate(self) -> tuple[int, int]:
        return (self.x, self.y)

    @property
    def key(self) -> str:
        """The authored display key, never the identity."""

        return str(self.prototype.get("key", self.node_id))

    @property
    def is_anchor(self) -> bool:
        return self.prototype.get("prototype_parent") == "anchor_room" or bool(
            self.prototype.get("anchor_key")
        )


@dataclass(frozen=True, slots=True)
class SparseRoad:
    """One explicit road between two authored nodes.

    ``bend_points`` are intermediate meter-space points; the road's physical
    length is the full polyline length (straight when no bend is authored).
    The direction is the compass of the first segment, which is the exit a
    traveller takes out of the source node.
    """

    road_id: str
    source_id: str
    destination_id: str
    bend_points: tuple[tuple[int, int], ...] = ()
    direction_hint: str | None = None
    prototype: Mapping[str, Any] = MappingProxyType({})

    def __post_init__(self) -> None:
        if not isinstance(self.road_id, str) or not self.road_id:
            raise SparseGraphError("road_id must be a non-empty string")
        for label, value in (
            ("source_id", self.source_id),
            ("destination_id", self.destination_id),
        ):
            if not isinstance(value, str) or not value:
                raise SparseGraphError(f"road {self.road_id!r} {label} must be a non-empty string")
        if self.source_id == self.destination_id:
            raise SparseGraphError(f"road {self.road_id!r} cannot be a self-loop")
        if not isinstance(self.bend_points, tuple):
            raise SparseGraphError(f"road {self.road_id!r} bend_points must be a tuple")
        for point in self.bend_points:
            if (
                not isinstance(point, tuple)
                or len(point) != 2
                or not _is_int(point[0])
                or not _is_int(point[1])
            ):
                raise SparseGraphError(
                    f"road {self.road_id!r} bend point {point!r} must be an integer pair"
                )
        if not isinstance(self.prototype, Mapping):
            raise SparseGraphError(f"road {self.road_id!r} prototype must be a mapping")
        if self.direction_hint is not None and self.direction_hint not in _EXIT_SPAWN_DEFAULTS:
            raise SparseGraphError(
                f"road {self.road_id!r} direction_hint {self.direction_hint!r} is unknown"
            )

    @property
    def identity(self) -> tuple[str, str]:
        return (self.source_id, self.destination_id)


@dataclass(frozen=True, slots=True)
class SparseEdge:
    """A road resolved against its endpoint nodes for routing and spawning."""

    road: SparseRoad
    source: SparseNode
    destination: SparseNode
    direction: str
    length: float


@dataclass(frozen=True, slots=True)
class RouteStep:
    """One traversable step of a sparse route."""

    direction: str
    exit_key: str
    source: SparseNode
    destination: SparseNode
    road: SparseRoad
    length: float


def _polyline(
    source: SparseNode, road: SparseRoad, destination: SparseNode
) -> tuple[tuple[int, int], ...]:
    return (
        source.coordinate,
        *road.bend_points,
        destination.coordinate,
    )


def _polyline_length(points: Sequence[tuple[int, int]]) -> float:
    return sum(
        hypot(end[0] - start[0], end[1] - start[1])
        for start, end in zip(points, points[1:])
    )


class SparseSettlementGraph:
    """A validated settlement graph: nodes, explicit roads and route planning.

    Construction is the validation boundary: every identity, coordinate,
    endpoint, road and direction conflict raises :class:`SparseGraphError`
    before a caller can persist or cache anything. The synchronizer relies on
    that guarantee for its "refuse before mutation" contract.
    """

    def __init__(
        self,
        map_id: str,
        nodes: Iterable[SparseNode],
        roads: Iterable[SparseRoad],
        *,
        options: Mapping[str, Any] | None = None,
        exit_prototype: Mapping[str, Any] | None = None,
    ) -> None:
        if not isinstance(map_id, str) or not map_id:
            raise SparseGraphError("map_id must be a non-empty string")
        node_list = tuple(nodes)
        road_list = tuple(roads)

        by_id: dict[str, SparseNode] = {}
        by_coord: dict[tuple[int, int], SparseNode] = {}
        for node in node_list:
            if not isinstance(node, SparseNode):
                raise SparseGraphError(f"map {map_id!r} received a non-node entry {node!r}")
            if node.node_id in by_id:
                raise SparseGraphError(
                    f"map {map_id!r} declares node identity {node.node_id!r} twice"
                )
            if node.coordinate in by_coord:
                other = by_coord[node.coordinate]
                raise SparseGraphError(
                    f"map {map_id!r} binds identities {other.node_id!r} and "
                    f"{node.node_id!r} to the same coordinate {node.coordinate}"
                )
            by_id[node.node_id] = node
            by_coord[node.coordinate] = node

        if not node_list:
            raise SparseGraphError(f"map {map_id!r} declares no nodes")

        self.map_id = map_id
        self.nodes: Mapping[str, SparseNode] = MappingProxyType(by_id)
        self.roads: tuple[SparseRoad, ...] = road_list
        self.options: Mapping[str, Any] = MappingProxyType(dict(options or {}))
        self.exit_prototype: Mapping[str, Any] = MappingProxyType(dict(exit_prototype or {}))

        road_ids: set[str] = set()
        pairs: set[tuple[str, str]] = set()
        directions: set[tuple[str, str]] = set()
        edges: list[SparseEdge] = []
        adjacency: dict[str, list[tuple[SparseEdge, str]]] = {node_id: [] for node_id in by_id}
        for road in road_list:
            if not isinstance(road, SparseRoad):
                raise SparseGraphError(f"map {map_id!r} received a non-road entry {road!r}")
            if road.road_id in road_ids:
                raise SparseGraphError(f"map {map_id!r} declares road {road.road_id!r} twice")
            road_ids.add(road.road_id)
            source = by_id.get(road.source_id)
            destination = by_id.get(road.destination_id)
            if source is None or destination is None:
                missing = road.source_id if source is None else road.destination_id
                raise SparseGraphError(
                    f"road {road.road_id!r} names unknown node identity {missing!r}"
                )
            if road.identity in pairs:
                raise SparseGraphError(
                    f"map {map_id!r} binds road {road.identity} twice"
                )
            pairs.add(road.identity)
            points = _polyline(source, road, destination)
            direction = road.direction_hint or compass_direction(
                points[1][0] - points[0][0], points[1][1] - points[0][1]
            )
            if (source.node_id, direction) in directions:
                raise SparseGraphError(
                    f"map {map_id!r} has two exits from {source.node_id!r} "
                    f"in direction {direction!r}"
                )
            directions.add((source.node_id, direction))
            edge = SparseEdge(
                road=road,
                source=source,
                destination=destination,
                direction=direction,
                length=_polyline_length(points),
            )
            edges.append(edge)
            adjacency[source.node_id].append((edge, destination.node_id))

        for node_edges in adjacency.values():
            node_edges.sort(key=lambda item: (item[0].road.road_id, item[1]))
        self.edges: tuple[SparseEdge, ...] = tuple(edges)
        self.adjacency: Mapping[str, tuple[tuple[SparseEdge, str], ...]] = MappingProxyType(
            {node_id: tuple(node_edges) for node_id, node_edges in adjacency.items()}
        )
        self._by_coord = MappingProxyType(by_coord)

    # -- lookups ---------------------------------------------------------
    def node(self, node_id: str) -> SparseNode | None:
        return self.nodes.get(node_id)

    def node_at(self, coordinate: tuple[int, int]) -> SparseNode | None:
        return self._by_coord.get(tuple(coordinate))  # type: ignore[arg-type]

    @property
    def max_x(self) -> int:
        return max(node.x for node in self.nodes.values())

    @property
    def max_y(self) -> int:
        return max(node.y for node in self.nodes.values())

    # -- routing ---------------------------------------------------------
    def route(self, source_id: str, destination_id: str) -> tuple[SparseEdge, ...] | None:
        """Return the shortest road sequence between two authored identities.

        Dijkstra over the declared adjacency only: the working set is bounded
        by the graph's own nodes/roads, never by coordinate span. Ties break by
        node identity so the result is deterministic.
        """

        if source_id not in self.nodes or destination_id not in self.nodes:
            return None
        if source_id == destination_id:
            return ()

        distances: dict[str, float] = {source_id: 0.0}
        previous: dict[str, SparseEdge] = {}
        heap: list[tuple[float, str]] = [(0.0, source_id)]
        settled: set[str] = set()
        while heap:
            distance, node_id = heappop(heap)
            if node_id in settled:
                continue
            settled.add(node_id)
            if node_id == destination_id:
                break
            for edge, neighbor_id in self.adjacency[node_id]:
                candidate = distance + edge.length
                known = distances.get(neighbor_id)
                if known is None or candidate < known - 1e-12:
                    distances[neighbor_id] = candidate
                    previous[neighbor_id] = edge
                    heappush(heap, (candidate, neighbor_id))
        if destination_id not in previous:
            return None

        path: list[SparseEdge] = []
        cursor = destination_id
        while cursor != source_id:
            edge = previous[cursor]
            path.append(edge)
            cursor = edge.source.node_id
        path.reverse()
        return tuple(path)

    def plan(self, source_id: str, destination_id: str) -> tuple[RouteStep, ...]:
        """Return the shortest traversable route as exit-named steps."""

        edges = self.route(source_id, destination_id)
        if edges is None:
            return ()
        return tuple(
            RouteStep(
                direction=edge.direction,
                exit_key=_EXIT_SPAWN_DEFAULTS[edge.direction][0],
                source=edge.source,
                destination=edge.destination,
                road=edge.road,
                length=edge.length,
            )
            for edge in edges
        )

    def plan_between_coordinates(
        self, start_xy: tuple[int, int], end_xy: tuple[int, int]
    ) -> tuple[RouteStep, ...]:
        """Plan between two coordinate bindings, or return no route."""

        start = self.node_at(start_xy)
        end = self.node_at(end_xy)
        if start is None or end is None:
            return ()
        return self.plan(start.node_id, end.node_id)

    @property
    def max_route_length(self) -> float:  # pragma: no cover - diagnostic helper
        return sum(edge.length for edge in self.edges)


def build_sparse_graph(
    *,
    map_id: str,
    prototypes: Mapping[tuple[int, int], Mapping[str, Any]],
    node_ids: Mapping[tuple[int, int], str],
    roads: Iterable[tuple[str, str] | SparseRoad],
    options: Mapping[str, Any] | None = None,
    exit_prototype: Mapping[str, Any] | None = None,
) -> SparseSettlementGraph:
    """Assemble a validated graph from coordinate-keyed authored declarations.

    ``node_ids`` is the authored identity table (coordinate → stable slug) and
    must describe exactly the prototype coordinates: a missing or extra entry is
    a graph error, so identity and room data cannot drift apart silently.
    """

    prototype_coords = {
        key
        for key in prototypes
        if isinstance(key, tuple) and len(key) == 2 and all(_is_int(value) for value in key)
    }
    identity_coords = set(node_ids)
    if prototype_coords != identity_coords:
        missing = sorted(identity_coords - prototype_coords)
        extra = sorted(prototype_coords - identity_coords)
        raise SparseGraphError(
            f"map {map_id!r} identity table and prototypes disagree "
            f"(identities without prototypes: {missing}; prototypes without identities: {extra})"
        )
    nodes = [
        SparseNode(
            node_id=node_ids[coordinate],
            x=coordinate[0],
            y=coordinate[1],
            prototype=dict(prototypes[coordinate]),
        )
        for coordinate in sorted(node_ids, key=lambda cell: (cell[1], cell[0]))
    ]
    road_objects: list[SparseRoad] = []
    for entry in roads:
        if isinstance(entry, SparseRoad):
            road_objects.append(entry)
        else:
            source_id, destination_id = entry
            road_objects.append(
                SparseRoad(
                    road_id=f"{source_id}>{destination_id}",
                    source_id=source_id,
                    destination_id=destination_id,
                )
            )
    return SparseSettlementGraph(
        map_id,
        nodes,
        road_objects,
        options=options,
        exit_prototype=exit_prototype,
    )


def graph_from_xymap(xymap) -> SparseSettlementGraph | None:
    """Adapt a live contrib ``XYMap`` for maps without a sparse declaration.

    Synthetic test maps and builder-authored maps still arrive as parsed ASCII.
    This transient adapter gives route planning the same sparse graph contract
    without persisting or caching a second authority. Identity is the map's
    node index, which is only valid for the lifetime of the loaded map.
    """

    if xymap is None or not getattr(xymap, "node_index_map", None):
        return None
    prototypes = getattr(xymap, "prototypes", None) or {}
    nodes = []
    for node in sorted(xymap.node_index_map.values(), key=lambda item: item.node_index):
        prototype = prototypes.get((node.X, node.Y))
        if not prototype:
            prototype = {"key": getattr(node, "key", str(node.node_index))}
        nodes.append(
            SparseNode(
                node_id=str(node.node_index),
                x=node.X,
                y=node.Y,
                prototype=dict(prototype),
            )
        )
    roads = []
    seen = set()
    for node in xymap.node_index_map.values():
        for direction, neighbor in node.links.items():
            pair = (node.node_index, neighbor.node_index)
            if pair in seen:
                continue
            seen.add(pair)
            roads.append(
                SparseRoad(
                    road_id=f"{node.node_index}>{neighbor.node_index}",
                    source_id=str(node.node_index),
                    destination_id=str(neighbor.node_index),
                    direction_hint=direction,
                )
            )
    try:
        return SparseSettlementGraph(
            str(xymap.Z),
            nodes,
            roads,
            options=getattr(xymap, "options", None),
            exit_prototype=prototypes.get(("*", "*", "*"), {}),
        )
    except SparseGraphError:
        return None
