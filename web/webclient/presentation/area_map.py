"""The on-demand ``area_map`` presenter (world-map drawer design §5.2).

``map.view`` with ``{scope: "area"}`` is the only caller: the panel registers
on demand, so full snapshots, movement and text-command refreshes never run
this presenter (``PresenterSpec.on_demand``; ``coordinator._render_all``).

The panel is a whole-area fog-of-war view of the map the player stands on:

- grid: the settlement's declared sparse graph (never rooms spawned on
  demand), integer metre coordinates, registered gate rooms carry the
  minimap ``gateway`` metadata;
- instance / interior: the coordinate-free room graph of the current family,
  bounded at the family boundary; an exit leaving it is a gateway node and is
  never traversed further;
- wilderness (schema 2, wilderness-area-map-reveal): the 41 x 41 cell window
  centred on the player as run-length-encoded rows that expose terrain only
  for revealed cells, sparse nodes (current, actually visited, and revealed
  cells with a legal step or disclosed location), true gateway replacement on
  the eight neighbour steps, live-sight entities, distant sightings and the
  current district name.

For every graph (non-wilderness) layer, known = visited ∪ adjacent(visited); a road is emitted
only when both ends are known and at least one is visited. Move actions are
only the current room's traversable exits, resolved through the same helpers
as the minimap. The presenter reads canonical room, map, knowledge and quest
data and never mutates anything. The exact wire schema lives in
:mod:`web.webclient.presentation.map_panels`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
import hashlib
import math
from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.local_map.builder import _exit_ref, _traversable
from web.webclient.presentation.local_map.gateways import (
    _gateway_far_side_label,
    _grid_gateway_at,
    _wild_region_label,
)
from web.webclient.presentation.local_map.grid import (
    _grid_exit_action,
    _grid_gate_metadata,
    _grid_room_label,
)
from web.webclient.presentation.map_panels import (
    AREA_FRAME_UNITS,
    AREA_MAP_SCHEMA_VERSION,
    AREA_MAX_BYTES,
    AREA_MAX_EDGES,
    AREA_MAX_NODES,
    AREA_MAX_QUEST_MARKERS,
    AREA_TERRAIN_CLASSES,
    MAP_MAX_LABEL,
    MAP_MAX_TITLE,
    WILDERNESS_MAP_ID,
    WILDERNESS_MAX_ENTITIES,
    WILDERNESS_MAX_NODES,
    WILDERNESS_MAX_SIGHTINGS,
    WILDERNESS_WINDOW,
    validate_area_map,
)
from web.webclient.presentation.protocol import json_byte_size
from web.webclient.presentation.registry import PanelUnavailableError
from world.observability import log_warn
from world.maps.area_identity import (
    AreaGraphOverBound as _OverBound,
    ROOM_GRAPH_MAX_ROOMS,
    room_component as _room_component,
)
from world.rules.map_knowledge import KnowledgeError, encode_grid, encode_room, encode_wild, parse_knowledge

#: Label of a room-graph node the player has not entered (minimap rule: the
#: room name is withheld until a visit).
UNEXPLORED_LABEL = "未探索"

_HALF_WINDOW = WILDERNESS_WINDOW // 2


# ---------------------------------------------------------------------------
# Pure fog of war.
# ---------------------------------------------------------------------------


def fog_of_war(
    adjacency: Mapping[str, Iterable[str]],
    visited: Iterable[str],
    current: str,
    order: Callable[[str], Any] = lambda node_id: node_id,
) -> tuple[list[str], set[str], list[tuple[str, str]]]:
    """Return ``(known_nodes, visited_nodes, edges)`` for one undirected graph.

    ``adjacency`` maps every node of the map to its neighbours; it must already
    be symmetric. ``visited`` is filtered to nodes of this map and always
    includes ``current``. known = visited ∪ adjacent(visited). An edge joins
    two known nodes of which at least one is visited, appears once per
    unordered pair, and is oriented by ``order``. Nodes and edges are sorted
    by ``order`` so the output is deterministic.
    """
    visited_set = {node for node in visited if node in adjacency}
    visited_set.add(current)
    known = set(visited_set)
    for node in visited_set:
        known.update(adjacency.get(node, ()))
    edges: set[tuple[str, str]] = set()
    for node in visited_set:
        for other in adjacency.get(node, ()):
            if other == node or other not in known:
                continue
            pair = (node, other) if order(node) <= order(other) else (other, node)
            edges.add(pair)
    known_sorted = sorted(known, key=order)
    edge_list = sorted(edges, key=lambda pair: (order(pair[0]), order(pair[1])))
    return known_sorted, visited_set, edge_list


def _visibility(node_id: str, current: str, visited: set[str]) -> str:
    if node_id == current:
        return "current"
    return "visited" if node_id in visited else "seen"


def _check_bounds(layer: str, map_id: str, nodes: int, edges: int) -> None:
    if nodes > AREA_MAX_NODES or edges > AREA_MAX_EDGES:
        log_warn(
            "area_map_over_bound",
            context={"layer": layer, "map": map_id, "nodes": nodes, "edges": edges},
        )
        raise _OverBound


def _check_payload_size(layer: str, map_id: str, payload: dict[str, Any]) -> None:
    """Apply the logical byte ceiling before the schema validator sees the body.

    The count checks happen before a payload exists; this second check keeps
    a count-compliant graph with long labels on the same declared over-bound
    path instead of letting ``validate_area_map`` surface a generic internal
    presenter error.
    """
    size = json_byte_size(payload)
    if size > AREA_MAX_BYTES:
        log_warn(
            "area_map_over_bound",
            context={"layer": layer, "map": map_id, "bytes": size},
        )
        raise _OverBound


# ---------------------------------------------------------------------------
# Grid layer.
# ---------------------------------------------------------------------------


def _settlement_title(z: str, location: Any) -> str:
    from world.lore import anchors
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

    for entry in WILDERNESS_ENTRY_REGISTRY.values():
        if any(gate.z_map_key == z for gate in entry.gates):
            anchor = anchors.anchors().get(entry.anchor_key)
            if anchor is not None:
                return f"{anchor.display_name_zh}街道圖"
    return f"{location.key}街道圖"


def _grid_area(actor: Any, location: Any, visit_ids: set[str]) -> dict[str, Any]:
    from world.maps.map_data import settlement_graph

    try:
        x, y, z = location.xyz
    except Exception as error:  # observability: ignore R2: an unplaced grid room has no map; the declared-unavailable panel is the report
        raise PanelUnavailableError from error
    z = str(z)
    graph = settlement_graph(z)
    projection = graph.display_projection() if graph is not None else location.xymap
    if projection is None:
        raise PanelUnavailableError
    try:
        current_node = projection.get_node_from_coord((x, y))
    except Exception as error:  # observability: ignore R2: a room off its own map is reported by the unavailable panel
        raise PanelUnavailableError from error
    if current_node is None:
        raise PanelUnavailableError

    by_id: dict[str, Any] = {}
    adjacency: dict[str, set[str]] = {}
    for node in projection.node_index_map.values():
        node_id = encode_grid(z, node.X, node.Y)
        by_id[node_id] = node
        adjacency.setdefault(node_id, set())
    for node_id, node in by_id.items():
        for end_node in node.links.values():
            other = encode_grid(z, end_node.X, end_node.Y)
            if other == node_id or other not in by_id:
                continue
            adjacency[node_id].add(other)
            adjacency[other].add(node_id)

    current_id = encode_grid(z, current_node.X, current_node.Y)
    order = lambda node_id: (by_id[node_id].Y, by_id[node_id].X)  # noqa: E731
    known, visited, edges = fog_of_war(adjacency, visit_ids, current_id, order)
    _check_bounds("grid", z, len(known), len(edges))

    linked = {encode_grid(z, end.X, end.Y) for end in current_node.links.values()}
    nodes = []
    for node_id in known:
        node = by_id[node_id]
        if graph is not None:
            sparse = graph.node_at((node.X, node.Y))
            label = sparse.key if sparse is not None else _grid_room_label((node.X, node.Y), z)
        else:
            label = _grid_room_label((node.X, node.Y), z)
        action = None
        if node_id in linked and node_id != current_id:
            action = _grid_exit_action(actor, location, (node.X, node.Y), z)
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "x": node.X,
                "y": node.Y,
                "visibility": _visibility(node_id, current_id, visited),
                "gateway": _grid_gate_metadata(node.X, node.Y, z),
                "action": action,
            }
        )
    return {
        "layer": "grid",
        "map_id": z,
        "current_node": current_id,
        "title": _settlement_title(z, location)[:MAP_MAX_TITLE],
        "nodes": nodes,
        "edges": [{"source": a, "destination": b} for a, b in edges],
    }


# ---------------------------------------------------------------------------
# Instance / interior room graphs.
# ---------------------------------------------------------------------------


def _room_graph_area(actor: Any, location: Any, visit_ids: set[str], *, is_instance: bool) -> dict[str, Any]:
    from typeclasses.rooms import InstanceRoom, Room

    family = InstanceRoom if is_instance else Room

    def same_family(room: Any) -> bool:
        return isinstance(room, family)

    rooms, exits = _room_component(location, same_family)
    room_ids = {encode_room(dbref): room for dbref, room in rooms.items()}
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in room_ids}
    # Exits that leave the family: (source room id, exit, destination).
    leaving: list[tuple[str, Any, Any]] = []
    for exit_obj in exits:
        source, destination = exit_obj.location, exit_obj.destination
        if source is None or destination is None or not getattr(destination, "id", None):
            continue
        source_id = encode_room(int(source.id))
        destination_id = encode_room(int(destination.id))
        if source_id == destination_id:
            continue
        if source_id in room_ids and destination_id in room_ids:
            adjacency[source_id].add(destination_id)
            adjacency[destination_id].add(source_id)
        elif source_id in room_ids:
            leaving.append((source_id, exit_obj, destination))

    current_id = encode_room(int(location.id))
    order = lambda node_id: int(node_id.split(":")[1])  # noqa: E731
    known, visited, edges = fog_of_war(adjacency, visit_ids, current_id, order)

    actions: dict[str, dict[str, Any]] = {}
    for exit_obj in sorted(location.exits, key=lambda e: int(e.id)):
        destination = exit_obj.destination
        if destination is None or not getattr(destination, "id", None):
            continue
        destination_id = encode_room(int(destination.id))
        if destination_id == current_id or destination_id in actions:
            continue
        if _traversable(exit_obj, actor):
            actions[destination_id] = {
                "kind": "move",
                "exit_ref": _exit_ref(exit_obj),
                "destination": destination_id,
            }

    nodes = []
    for node_id in known:
        label = room_ids[node_id].key if node_id in visited else UNEXPLORED_LABEL
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "visibility": _visibility(node_id, current_id, visited),
                "gateway": None,
                "action": actions.get(node_id),
            }
        )

    # A visited room's exit out of this family is a gateway reference: one
    # node naming where it leads, never a traversal into the other map.
    presented = {node["id"] for node in nodes}
    edge_pairs = list(edges)
    for source_id, exit_obj, destination in sorted(leaving, key=lambda item: int(item[1].id)):
        if source_id not in visited:
            continue
        gateway_id = encode_room(int(destination.id))
        if gateway_id not in presented:
            presented.add(gateway_id)
            nodes.append(
                {
                    "id": gateway_id,
                    "label": destination.key,
                    "visibility": "seen",
                    "gateway": {"leads_to": destination.key},
                    # The action comes from the current room's own exits, not
                    # from whichever visited room introduced this gateway.
                    # Enrich an existing node below so exit dbref order can
                    # never hide a currently traversable door.
                    "action": actions.get(gateway_id),
                }
            )
        else:
            # A later exit from the current room to a shared gateway must
            # still publish its move action.
            node = next(node for node in nodes if node["id"] == gateway_id)
            node["action"] = actions.get(gateway_id)
        pair = (source_id, gateway_id)
        if pair not in edge_pairs and (gateway_id, source_id) not in edge_pairs:
            edge_pairs.append(pair)

    root = min(rooms)
    map_id = f"{'instance' if is_instance else 'room'}:{root}"
    _check_bounds("instance" if is_instance else "interior", map_id, len(nodes), len(edge_pairs))
    suffix = "空間平面圖" if is_instance else "平面圖"
    return {
        "layer": "instance" if is_instance else "interior",
        "map_id": map_id,
        "current_node": current_id,
        "title": f"{location.key}{suffix}"[:MAP_MAX_TITLE],
        "nodes": nodes,
        "edges": [{"source": a, "destination": b} for a, b in edge_pairs],
        # Internal: every room in this component, known or fogged, lets a
        # commission marker keep its canonical identity without adding the
        # target to ``nodes``.
        "map_node_ids": set(room_ids),
    }


# ---------------------------------------------------------------------------
# Wilderness window.
# ---------------------------------------------------------------------------


def _district_name(cell: tuple[int, int]) -> str:
    from world.lore.map_districts import current
    from world.maps.district_partition import district_at

    key = district_at(cell)
    district = current().districts.get(key) if key is not None else None
    if district is None:
        return _wild_region_label(*cell)
    return district.district_name_zh


def _wilderness_over_bound(**context: Any) -> None:
    log_warn("area_map_over_bound", context={"layer": "wilderness", "map": WILDERNESS_MAP_ID, **context})
    raise _OverBound


def entity_token(observation_key: str) -> str:
    """The stable, non-semantic wire identity of one population observation.

    Raw observation keys embed coordinates, ambient branches or database ids;
    the wire carries only a keyed digest, domain-separated from every other
    use of the server secret. A server without a secret publishes no map
    rather than an unkeyed (reversible) token.
    """
    from django.conf import settings

    secret = getattr(settings, "SECRET_KEY", "") or ""
    if not secret:
        log_warn("area_map_entity_key_missing", context={"layer": "wilderness"})
        raise PanelUnavailableError
    key = hashlib.sha256(b"elosern.area_map.entity.v1:" + secret.encode("utf-8")).digest()
    return hashlib.blake2b(observation_key.encode("utf-8"), digest_size=8, key=key).hexdigest()


class _TerrainOracle:
    """Per-request cached terrain facts of revealed cells (read-only).

    The class order is fixed: sea > settlement footprint > ridge > river
    water > the sight rulebook's terrain row. A hidden anchor's footprint keeps
    its underlying terrain class (its identity needs a visit); every footprint
    stays impassable, exactly as traversal refuses it.
    """

    def __init__(self) -> None:
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.maps import elevation, wilderness_provider
        from world.rules import sight
        from world.rules.wilderness_disclosure import anchor_is_hidden

        self._provider = wilderness_provider
        self._elevation = elevation
        self._sight = sight
        definition = wilderness_provider.terrain_definition()
        self._fords = frozenset(
            tuple(cell) for cells in definition.waterway_fords.values() for cell in cells
        )
        self._footprints: dict[tuple[int, int], bool] = {}
        for anchor_key, entry in WILDERNESS_ENTRY_REGISTRY.items():
            hidden = anchor_is_hidden(anchor_key)
            for cell in entry.footprint_cells:
                self._footprints[tuple(cell)] = hidden
        # Facts are a pure function of the published terrain, elevation and
        # footprint registry; one bounded cache serves repeated windows.
        # The terrain definition and sight policy are compared by identity and
        # kept alive by the cache, so a republished world never reuses a freed
        # object's id.
        owners = (definition, sight.POLICY)
        key = (elevation.current().fingerprint, frozenset(self._footprints.items()))
        cached_owners = _TerrainOracle._cache_definition
        if (
            cached_owners is None
            or any(a is not b for a, b in zip(cached_owners, owners))
            or _TerrainOracle._cache_key != key
        ):
            _TerrainOracle._cache_definition = owners
            _TerrainOracle._cache_key = key
            _TerrainOracle._cache = {}
        self._cache = _TerrainOracle._cache

    def _row(self, x: int, y: int) -> str:
        row = self._sight.sight_terrain_class(self._provider.region_for_coordinates(x, y))
        if row not in AREA_TERRAIN_CLASSES:
            log_warn("area_map_terrain_unclassified", context={"cell": f"{x},{y}", "terrain": row})
            raise PanelUnavailableError
        return row

    _cache_definition: Any = None
    _cache_key: Any = None
    _cache: dict[tuple[int, int], dict[str, Any]] = {}
    _CACHE_CELLS = 65_536

    def facts(self, cell: tuple[int, int]) -> dict[str, Any]:
        cached = self._cache.get(cell)
        if cached is None:
            if len(self._cache) >= self._CACHE_CELLS:
                self._cache.clear()
            cached = self._cache[cell] = self._facts(cell)
        return cached

    def _facts(self, cell: tuple[int, int]) -> dict[str, Any]:
        x, y = cell
        provider = self._provider
        if not provider.is_land_cell(cell):
            terrain = "sea"
        elif cell in self._footprints:
            terrain = self._row(x, y) if self._footprints[cell] else "settlement"
        elif provider.is_closed_ridge_cell(cell):
            terrain = "ridge"
        elif provider.is_inland_water_cell(cell):
            terrain = "water"
        else:
            terrain = self._row(x, y)
        band, tier = self._elevation.cell_elevation(x, y)
        return {
            "kind": "terrain",
            "terrain": terrain,
            "passable": bool(provider.is_valid_wilderness_cell(cell)),
            "band": band,
            "tier": tier,
            # No wilderness road exists in the published geography or the
            # movement pricing (movement.yaml prices regions only).
            "road": False,
            "ford": cell in self._fords,
        }


def encode_rows(
    min_x: int,
    min_y: int,
    facts_at: Callable[[tuple[int, int]], dict[str, Any] | None],
) -> list[list[dict[str, Any]]]:
    """South-to-north rows of merged runs; ``None`` facts are unknown cells."""
    rows: list[list[dict[str, Any]]] = []
    for row in range(WILDERNESS_WINDOW):
        runs: list[dict[str, Any]] = []
        for col in range(WILDERNESS_WINDOW):
            facts = facts_at((min_x + col, min_y + row))
            run = {"kind": "unknown"} if facts is None else dict(facts)
            if runs and {k: v for k, v in runs[-1].items() if k != "length"} == run:
                runs[-1]["length"] += 1
            else:
                runs.append({"length": 1, **run})
        rows.append(runs)
    return rows


def _distant_markers(
    actor: Any, cell: tuple[int, int], calendar: Any, visited: Callable[[str], bool]
) -> tuple[dict[str, Any], ...]:
    """Distant sightings with lighting read by exact landmark membership.

    ``sight.visible_distant_markers`` derives the lit set from the whole
    knowledge record; the window instead asks only for each district
    landmark's own node (one selected chunk each), so a long history never
    decodes every chunk.
    """
    from world.lore.map_districts import current as districts_current, landmark_node_ids
    from world.maps.wilderness_provider import WILDERNESS_KM_PER_CELL
    from world.rules import sight

    registry = districts_current().districts
    lit = frozenset(key for key, node_id in landmark_node_ids(registry).items() if visited(node_id))
    return sight.distant_markers(
        cell,
        calendar,
        sight.published_distant_sources(),
        lit,
        inputs=sight.published_ground_inputs(cell),
        cell_size_km=WILDERNESS_KM_PER_CELL,
        district_names={key: row.landmark_name_zh for key, row in registry.items()},
    )


def _wilderness_area(actor: Any, location: Any) -> dict[str, Any]:
    """The schema-2 wilderness window (wilderness-area-map-reveal).

    Reads only the knowledge chunks the window (plus the reveal reach) needs,
    never the whole record. A cell is published as terrain only when it is
    revealed (permanent reveal, an actual visit, or the current cell);
    everything else is an exact unknown run. Nodes are sparse: the current
    cell, every actually visited cell, and revealed cells that carry a legal
    step or disclosed location metadata.
    """
    from typeclasses.rooms import GridRoom
    from world.maps import wilderness_provider
    from world.maps.wilderness_destination import (
        DIRECTION_DELTAS,
        find_gateway,
        normalize_wilderness_direction,
        resolve_wilderness_destination,
    )
    from world.maps.wilderness_population import population_view
    from world.rules import sight
    from world.rules.clock import get_world_clock
    from world.rules.map_knowledge import decode_node, read_snapshot
    from world.rules.wilderness_disclosure import WildernessDisclosure
    from web.webclient.presentation.local_map.gateways import _registered_gateways
    from web.webclient.presentation.local_map.validate import WILD_DIRECTIONS

    coordinates = location.coordinates
    if coordinates is None:
        raise PanelUnavailableError
    cx, cy = int(coordinates[0]), int(coordinates[1])
    max_x, max_y = wilderness_provider.WILDERNESS_MAX_X, wilderness_provider.WILDERNESS_MAX_Y
    if not (0 <= cx <= max_x and 0 <= cy <= max_y):
        raise PanelUnavailableError
    name = wilderness_provider.WILDERNESS_NAME
    km = wilderness_provider.WILDERNESS_KM_PER_CELL
    current_id = encode_wild(name, cx, cy)
    min_x, min_y = cx - _HALF_WINDOW, cy - _HALF_WINDOW
    bounds = (max(0, min_x), max(0, min_y), min(max_x, cx + _HALF_WINDOW), min(max_y, cy + _HALF_WINDOW))

    def centre(value: int) -> float | int:
        scaled = (value + 0.5) * km
        return int(scaled) if float(scaled).is_integer() else scaled

    # One request-scoped read: the envelope is validated once and only the
    # chunks the window (plus the reveal reach) needs are decoded.
    try:
        snapshot = read_snapshot(actor)
        if snapshot is None:
            raise KnowledgeError("character has no map-knowledge record")
        visits = snapshot.visits_in_bounds(bounds)
    except KnowledgeError as error:  # observability: ignore R2: unreadable knowledge degrades to the declared-unavailable panel, as every area layer does
        raise PanelUnavailableError from error
    visited_cells: set[tuple[int, int]] = set()
    for visit in visits:
        decoded = decode_node(visit.node_id)
        visited_cells.add((decoded["x"], decoded["y"]))
    revealed = set(snapshot.revealed_in_bounds(bounds, obj=str(actor))) | visited_cells | {(cx, cy)}

    gateways = {approach: (grid_gate, anchor) for approach, grid_gate, anchor in _registered_gateways()}
    gate_visits: dict[str, bool] = {}

    def gate_visited(gate_node: str) -> bool:
        if gate_node not in gate_visits:
            try:
                gate_visits[gate_node] = snapshot.has_visited(gate_node)
            except KnowledgeError:  # observability: ignore R2: the window read above already validated the envelope; an unreadable answer discloses nothing
                gate_visits[gate_node] = False
        return gate_visits[gate_node]

    def disclosure_for(gate_node: str) -> WildernessDisclosure:
        visited = frozenset({gate_node}) if gate_visited(gate_node) else frozenset()
        return WildernessDisclosure(frozenset(revealed), visited)

    def wild_label(cell: tuple[int, int]) -> str:
        gateway = gateways.get(cell)
        if gateway is not None:
            (grid_xy, z_map_key), anchor_key = gateway
            gate_node = encode_grid(z_map_key, *grid_xy)
            if disclosure_for(gate_node).gateway_disclosed(anchor_key, gate_node):
                return _gateway_far_side_label("wilderness", cell, anchor_key)
        return _wild_region_label(*cell)

    def wild_node(cell: tuple[int, int], action: dict[str, Any] | None) -> dict[str, Any]:
        node_id = encode_wild(name, *cell)
        visited = cell in visited_cells or node_id == current_id
        return {
            "id": node_id,
            "label": wild_label(cell),
            "x": centre(cell[0]),
            "y": centre(cell[1]),
            "visibility": "current" if node_id == current_id else ("visited" if visited else "seen"),
            "visited": visited,
            "gateway": None,
            "action": action,
        }

    # Sparse nodes keyed by cell: current, visits, then disclosed locations.
    cells: dict[tuple[int, int], dict[str, Any]] = {(cx, cy): wild_node((cx, cy), None)}
    for cell in sorted(visited_cells):
        cells.setdefault(cell, wild_node(cell, None))
    for cell, ((grid_xy, z_map_key), anchor_key) in gateways.items():
        if cell in cells or cell not in revealed:
            continue
        if not (min_x <= cell[0] < min_x + WILDERNESS_WINDOW and min_y <= cell[1] < min_y + WILDERNESS_WINDOW):
            continue
        gate_node = encode_grid(z_map_key, *grid_xy)
        if disclosure_for(gate_node).gateway_disclosed(anchor_key, gate_node):
            cells[cell] = wild_node(cell, None)

    exits_by_direction: dict[str, Any] = {}
    for exit_obj in sorted(location.exits, key=lambda e: int(e.id)):
        direction = normalize_wilderness_direction(exit_obj.key)
        if direction is not None:
            exits_by_direction.setdefault(direction, exit_obj)

    steps: list[str] = []
    for direction in WILD_DIRECTIONS:
        destination = resolve_wilderness_destination(location, direction)
        if destination is None:
            continue
        dx, dy = DIRECTION_DELTAS[direction]
        cell = (cx + dx, cy + dy)
        exit_obj = exits_by_direction.get(direction)
        action = None
        if exit_obj is not None and _traversable(exit_obj, actor):
            action = {"kind": "move", "exit_ref": _exit_ref(exit_obj), "destination": destination}
        if destination.startswith("grid:"):
            # True gateway replacement on a revealed step only: an unrevealed
            # gate cell stays an opaque directional control, and a hidden
            # entry also needs its gate room's visit.
            if cell not in revealed:
                continue
            decoded = decode_node(destination)
            grid_gateway = _grid_gateway_at(decoded["x"], decoded["y"], decoded["z_map_key"])
            if grid_gateway is None:
                continue
            hit = find_gateway((cx, cy), direction)
            anchor_key = hit[0].anchor_key if hit is not None else None
            if not disclosure_for(destination).gateway_disclosed(anchor_key, destination):
                continue
            room = GridRoom.objects.filter_xyz(xyz=(decoded["x"], decoded["y"], decoded["z_map_key"])).first()
            visited = gate_visited(destination)
            cells[cell] = {
                "id": destination,
                "label": room.key if room is not None else _grid_room_label(
                    (decoded["x"], decoded["y"]), decoded["z_map_key"]
                ),
                "x": centre(cell[0]),
                "y": centre(cell[1]),
                "visibility": "visited" if visited else "seen",
                "visited": visited,
                "gateway": {
                    "leads_to": _gateway_far_side_label("wilderness", grid_gateway[0], grid_gateway[2])
                },
                "action": action,
            }
        else:
            if cell not in revealed:
                continue  # an unrevealed step stays an opaque directional control
            node = cells.get(cell)
            if node is None:
                if action is None:
                    continue
                node = cells[cell] = wild_node(cell, None)
            if node["id"] != destination:
                continue
            node["action"] = action
        steps.append(destination)

    nodes = [cells[key] for key in sorted(cells, key=lambda cell: (cell[1], cell[0]))]
    presented = {node["id"] for node in nodes}
    edges = [
        {"source": current_id, "destination": destination}
        for destination in dict.fromkeys(steps)
        if destination in presented and destination != current_id
    ]
    if len(nodes) > WILDERNESS_MAX_NODES or len(edges) > AREA_MAX_EDGES:
        _wilderness_over_bound(nodes=len(nodes), edges=len(edges))

    oracle = _TerrainOracle()

    def facts_at(cell: tuple[int, int]) -> dict[str, Any] | None:
        if cell not in revealed:
            return None
        return oracle.facts(cell)

    rows = encode_rows(min_x, min_y, facts_at)

    try:
        calendar = get_world_clock().calendar
        phase = sight.light_phase(calendar)
        radius = sight.ground_radius_at((cx, cy), calendar)
        sightings = [dict(marker) for marker in _distant_markers(actor, (cx, cy), calendar, gate_visited)]
    except Exception as error:
        log_warn("area_map_sight_failed", exc=error, context={"layer": "wilderness", "cell": f"{cx},{cy}"})
        raise PanelUnavailableError from error
    if len(sightings) > WILDERNESS_MAX_SIGHTINGS:
        _wilderness_over_bound(sightings=len(sightings))

    # Live sight is the current disc; only its revealed cells may carry an
    # entity, so no entity ever stands on an unknown run.
    disc = [
        (cx + dx, cy + dy)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if sight.in_ground_disc((cx, cy), (cx + dx, cy + dy), radius) and (cx + dx, cy + dy) in revealed
    ]
    own = f"object:{actor.pk}"
    entities = []
    for fact in population_view(location.wilderness, disc):
        if fact.observation_key == own:
            continue
        entities.append(
            {
                "id": entity_token(fact.observation_key),
                "cell": {"x": int(fact.cell[0]), "y": int(fact.cell[1])},
                "kind": "hostile" if fact.kind == "monster" else fact.kind,
                "hostile": bool(fact.hostile),
                "label": fact.label[:MAP_MAX_LABEL],
            }
        )
    if len(entities) > WILDERNESS_MAX_ENTITIES:
        _wilderness_over_bound(entities=len(entities))

    return {
        "layer": "wilderness",
        "map_id": WILDERNESS_MAP_ID,
        "current_node": current_id,
        "title": _wild_region_label(cx, cy)[:MAP_MAX_TITLE],
        "nodes": nodes,
        "edges": edges,
        "district_name": _district_name((cx, cy))[:MAP_MAX_TITLE],
        "cell_km": km,
        "window": {"min_x": min_x, "min_y": min_y, "width": WILDERNESS_WINDOW, "height": WILDERNESS_WINDOW},
        "rows": rows,
        "light_phase": phase,
        "ground_radius": radius,
        "entities": entities,
        "sightings": sightings,
    }


# ---------------------------------------------------------------------------
# Quest markers.
# ---------------------------------------------------------------------------


def bearing_and_distance(origin: tuple[int, int], target: tuple[int, int], km_per_cell: float) -> tuple[float, float]:
    """Compass bearing (clockwise from north, y north-positive) and distance.

    Both values are rounded to 0.1; the bearing wraps into ``[0, 360)`` after
    rounding, so 359.96 becomes 0.0.
    """
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    if dx == 0 and dy == 0:
        return 0.0, 0.0
    bearing = round(math.degrees(math.atan2(dx, dy)) % 360.0, 1) % 360.0
    distance = round(math.hypot(dx, dy) * km_per_cell, 1)
    return bearing, distance


def _quest_markers(
    actor: Any,
    layer: str,
    map_id: str,
    presented: set[str],
    map_node_ids: set[str],
) -> list[dict[str, Any]]:
    from web.webclient.presentation.map_quest_destinations import (
        accepted_destinations_with_tracking,
        actor_world_cell,
    )
    from world.maps import wilderness_provider
    from world.quests.definitions import QUEST_DEFINITION_REGISTRY

    destinations, tracked_ids = accepted_destinations_with_tracking(actor)
    origin = actor_world_cell(actor)
    markers: list[tuple[int, int, dict[str, Any]]] = []
    for index, destination in enumerate(destinations):
        definition = QUEST_DEFINITION_REGISTRY.get(destination.definition_key)
        if definition is None:
            continue
        on_map = destination.node_id is not None and (
            (layer == "grid" and destination.map_key == map_id)
            or (layer == "wilderness" and destination.node_id in presented)
            or (layer in ("instance", "interior") and destination.node_id in map_node_ids)
        )
        if on_map:
            target: dict[str, Any] = {"kind": "node", "node_id": destination.node_id}
        elif origin is None or destination.world_cell is None:
            continue  # no known position: never invent a bearing
        else:
            bearing, distance = bearing_and_distance(
                origin, destination.world_cell, wilderness_provider.WILDERNESS_KM_PER_CELL
            )
            target = {"kind": "bearing", "bearing_deg": bearing, "distance_km": distance}
        tracked = destination.quest_id in tracked_ids
        markers.append(
            (
                0 if tracked else 1,
                index,
                {
                    "id": destination.quest_id,
                    "title": definition.display_name[:MAP_MAX_TITLE],
                    "tracked": tracked,
                    "destination": target,
                },
            )
        )
    markers.sort(key=lambda item: (item[0], item[1]))
    return [marker for _, _, marker in markers[:AREA_MAX_QUEST_MARKERS]]


# ---------------------------------------------------------------------------
# Presenter.
# ---------------------------------------------------------------------------


def area_map_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``area_map`` panel for the puppet."""
    actor = context.actor
    location = getattr(actor, "location", None)
    if location is None:
        raise PanelUnavailableError

    from typeclasses.rooms import GridRoom, InstanceRoom, Room, TerrainRoom

    def visit_ids() -> set[str]:
        # Graph layers read the whole (small) visited projection; the
        # wilderness window reads only its own chunks instead.
        try:
            return {visit.node_id for visit in parse_knowledge(actor)}
        except KnowledgeError as error:  # observability: ignore R2: unreadable knowledge degrades to the declared-unavailable panel
            raise PanelUnavailableError from error

    try:
        if isinstance(location, TerrainRoom):
            body = _wilderness_area(actor, location)
        elif isinstance(location, GridRoom):
            body = _grid_area(actor, location, visit_ids())
        elif isinstance(location, InstanceRoom):
            body = _room_graph_area(actor, location, visit_ids(), is_instance=True)
        elif isinstance(location, Room):
            body = _room_graph_area(actor, location, visit_ids(), is_instance=False)
        else:
            raise PanelUnavailableError
    except _OverBound as error:  # observability: ignore R2: the bound violation was logged as area_map_over_bound before raising
        raise PanelUnavailableError from error

    presented = {node["id"] for node in body["nodes"]}
    map_node_ids = body.pop("map_node_ids", set())
    payload = {
        "schema_version": AREA_MAP_SCHEMA_VERSION,
        "available": True,
        "layer": body["layer"],
        "map_id": body["map_id"],
        "frame": {"key": body["map_id"], "unit": AREA_FRAME_UNITS[body["layer"]]},
        "current_node": body["current_node"],
        "title": body["title"],
        "nodes": body["nodes"],
        "edges": body["edges"],
        "quest_markers": _quest_markers(
            actor, body["layer"], body["map_id"], presented, map_node_ids
        ),
    }
    if body["layer"] == "wilderness":
        for key in ("district_name", "cell_km", "window", "rows", "light_phase", "ground_radius", "entities", "sightings"):
            payload[key] = body[key]
    try:
        _check_payload_size(body["layer"], body["map_id"], payload)
    except _OverBound as error:  # observability: ignore R2: the byte violation was logged as area_map_over_bound before raising
        raise PanelUnavailableError from error
    # Validated here as well as in the coordinator: the presenter's own tests
    # exercise the exact schema, and the coordinator still guards every
    # registered map body before it reaches the wire.
    return validate_area_map(payload)


__all__ = [
    "ROOM_GRAPH_MAX_ROOMS",
    "UNEXPLORED_LABEL",
    "area_map_presenter",
    "bearing_and_distance",
    "encode_rows",
    "entity_token",
    "fog_of_war",
]
