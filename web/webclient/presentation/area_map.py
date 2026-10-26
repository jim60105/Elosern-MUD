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
- wilderness: the 15 x 15 cell window centred on the player, clipped to legal
  ground, with true gateway replacement on the eight neighbour steps and the
  current district name.

For every graph layer, known = visited ∪ adjacent(visited); a road is emitted
only when both ends are known and at least one is visited. Move actions are
only the current room's traversable exits, resolved through the same helpers
as the minimap. The presenter reads canonical room, map, knowledge and quest
data and never mutates anything. The exact wire schema lives in
:mod:`web.webclient.presentation.map_panels`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
import math
from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.local_map.builder import _exit_ref, _traversable
from web.webclient.presentation.local_map.gateways import (
    _gateway_far_side_label,
    _grid_gateway_at,
    _wild_region_label,
    _wilderness_gateway_at,
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
    MAP_MAX_TITLE,
    WILDERNESS_MAP_ID,
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
    from world.lore.anchors import ANCHOR_REGISTRY
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

    for entry in WILDERNESS_ENTRY_REGISTRY.values():
        if any(gate.z_map_key == z for gate in entry.gates):
            anchor = ANCHOR_REGISTRY.get(entry.anchor_key)
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
    from world.lore.map_districts import MAP_DISTRICT_REGISTRY
    from world.maps.district_partition import district_at

    key = district_at(cell)
    district = MAP_DISTRICT_REGISTRY.get(key) if key is not None else None
    if district is None:
        return _wild_region_label(*cell)
    return district.district_name_zh


def _wilderness_area(actor: Any, location: Any, visit_ids: set[str]) -> dict[str, Any]:
    from typeclasses.rooms import GridRoom
    from world.maps import wilderness_provider
    from world.maps.wilderness_destination import (
        DIRECTION_DELTAS,
        is_provider_valid_coordinates,
        normalize_wilderness_direction,
        resolve_wilderness_destination,
    )
    from world.rules.map_knowledge import decode_node
    from web.webclient.presentation.local_map.validate import WILD_DIRECTIONS

    coordinates = location.coordinates
    if coordinates is None:
        raise PanelUnavailableError
    cx, cy = int(coordinates[0]), int(coordinates[1])
    if not (0 <= cx <= wilderness_provider.WILDERNESS_MAX_X and 0 <= cy <= wilderness_provider.WILDERNESS_MAX_Y):
        raise PanelUnavailableError
    name = wilderness_provider.WILDERNESS_NAME
    km = wilderness_provider.WILDERNESS_KM_PER_CELL
    current_id = encode_wild(name, cx, cy)

    def centre(value: int) -> float | int:
        scaled = (value + 0.5) * km
        return int(scaled) if float(scaled).is_integer() else scaled

    # The window, keyed by cell so a gateway step can replace its cell.
    cells: dict[tuple[int, int], dict[str, Any]] = {}
    for y in range(cy - _HALF_WINDOW, cy + _HALF_WINDOW + 1):
        for x in range(cx - _HALF_WINDOW, cx + _HALF_WINDOW + 1):
            if (x, y) != (cx, cy) and not is_provider_valid_coordinates((x, y)):
                continue
            node_id = encode_wild(name, x, y)
            gateway = _wilderness_gateway_at(x, y)
            label = (
                _gateway_far_side_label("wilderness", (x, y), gateway[2])
                if gateway is not None
                else _wild_region_label(x, y)
            )
            visited = node_id == current_id or node_id in visit_ids
            cells[(x, y)] = {
                "id": node_id,
                "label": label,
                "x": centre(x),
                "y": centre(y),
                "visibility": "current" if node_id == current_id else ("visited" if visited else "seen"),
                "visited": visited,
                "gateway": None,
                "action": None,
            }

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
            # True gateway replacement: the step's cell IS the gate room.
            decoded = decode_node(destination)
            grid_gateway = _grid_gateway_at(decoded["x"], decoded["y"], decoded["z_map_key"])
            if grid_gateway is None:
                # Not representable as a gateway node: offer nothing rather
                # than an unlabelled cross-map node.
                continue
            room = GridRoom.objects.filter_xyz(
                xyz=(decoded["x"], decoded["y"], decoded["z_map_key"])
            ).first()
            cells[cell] = {
                "id": destination,
                "label": room.key if room is not None else _grid_room_label(
                    (decoded["x"], decoded["y"]), decoded["z_map_key"]
                ),
                "x": centre(cell[0]),
                "y": centre(cell[1]),
                "visibility": "visited" if destination in visit_ids else "seen",
                "visited": destination in visit_ids,
                "gateway": {
                    "leads_to": _gateway_far_side_label("wilderness", grid_gateway[0], grid_gateway[2])
                },
                "action": action,
            }
        else:
            node = cells.get(cell)
            if node is None or node["id"] != destination:
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
    return {
        "layer": "wilderness",
        "map_id": WILDERNESS_MAP_ID,
        "current_node": current_id,
        "title": _wild_region_label(cx, cy)[:MAP_MAX_TITLE],
        "nodes": nodes,
        "edges": edges,
        "district_name": _district_name((cx, cy))[:MAP_MAX_TITLE],
        "cell_km": km,
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
    try:
        visits = parse_knowledge(actor)
    except KnowledgeError as error:  # observability: ignore R2: unreadable knowledge degrades to the declared-unavailable panel
        raise PanelUnavailableError from error
    visit_ids = {visit.node_id for visit in visits}

    from typeclasses.rooms import GridRoom, InstanceRoom, Room, TerrainRoom

    try:
        if isinstance(location, GridRoom):
            body = _grid_area(actor, location, visit_ids)
        elif isinstance(location, TerrainRoom):
            body = _wilderness_area(actor, location, visit_ids)
        elif isinstance(location, InstanceRoom):
            body = _room_graph_area(actor, location, visit_ids, is_instance=True)
        elif isinstance(location, Room):
            body = _room_graph_area(actor, location, visit_ids, is_instance=False)
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
        payload["district_name"] = body["district_name"]
        payload["cell_km"] = body["cell_km"]
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
    "fog_of_war",
]
