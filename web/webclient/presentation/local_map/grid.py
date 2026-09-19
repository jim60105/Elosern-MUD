"""The grid/anchor layer adapter and its XYMap geometry helpers (design D6).

Reads the live XYMap node/link model -- never the rendered ANSI -- and lays
down the bounded grid payload: current node, in-range nodes with real exit
edges, registered gate nodes claiming capacity first, and bounded remembered
gateways.
"""

from typing import Any

from web.webclient.presentation.local_map.builder import (
    _exit_ref,
    _GraphBuilder,
    _known_node_id,
    _traversable,
    _visited_map,
)
from web.webclient.presentation.local_map.gateways import (
    _gateway_far_side_label,
    _grid_gateway_at,
    _wild_region_label,
)
from web.webclient.presentation.local_map.validate import (
    COORD_MAX,
    COORD_MIN,
    GRID_MODES,
    MAX_GRID_VISUAL_RANGE,
    MAX_NODES,
    MAX_REMEMBERED_GATEWAYS,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.map_knowledge import (
    KnowledgeError,
    NodeVisit,
    decode_node,
    encode_grid,
    encode_wild,
)


def _grid_layer(actor: Any, visits: list[NodeVisit], builder: _GraphBuilder) -> str:
    """Build the grid/anchor layer from the live XYMap node/link model (D6)."""
    from typeclasses.rooms import AnchorRoom, GridRoom
    from world.maps.wilderness_destination import DIRECTION_DELTAS

    location = actor.location
    if not isinstance(location, GridRoom):
        raise PanelUnavailableError
    try:
        x, y, z = location.xyz
    except Exception:
        raise PanelUnavailableError
    xymap = location.xymap
    if xymap is None:
        raise PanelUnavailableError
    options = getattr(xymap, "options", None) or {}
    map_mode = options.get("map_mode")
    visual_range = options.get("map_visual_range")
    if map_mode not in GRID_MODES:
        raise PanelUnavailableError
    if (
        isinstance(visual_range, bool)
        or not isinstance(visual_range, int)
        or not 1 <= visual_range <= MAX_GRID_VISUAL_RANGE
    ):
        raise PanelUnavailableError

    try:
        current_node = xymap.get_node_from_coord((x, y))
    except Exception:
        raise PanelUnavailableError
    if current_node is None:
        raise PanelUnavailableError

    visited = _visited_map(visits)

    # Registered gate exits claim their capacity BEFORE the ordinary visible
    # set is laid down (design D2): the gate is never the node that breaks the
    # bound and never silently dropped. Distinct gate targets beyond the
    # representable budget fail closed.
    gate_candidates = _grid_gate_candidates(location)
    if len(gate_candidates) > MAX_NODES - 1:
        raise PanelUnavailableError
    in_range = _trim_visible(
        _grid_nodes_in_range(xymap, current_node, visual_range, map_mode),
        current_node,
        MAX_NODES - len(gate_candidates),
    )

    # Current node first, then in-range nodes, then gates, then bounded
    # remembered (the remembered loop self-limits against the running count).
    current_id = encode_grid(str(z), x, y)

    builder.add_node(
        current_id,
        location.key,
        x,
        y,
        visibility="current",
        current=True,
        anchor=isinstance(location, AnchorRoom),
        landmark=isinstance(location, AnchorRoom),
        action=None,
    )

    # In-range neighbor nodes with real exit edges.
    for node in in_range:
        if node.node_index == current_node.node_index:
            continue
        node_id = encode_grid(str(z), node.X, node.Y)
        if node_id == current_id:
            continue
        is_anchor = _grid_coord_is_anchor(xymap, (node.X, node.Y))
        visibility = (
            "visible_visited"
            if _known_node_id(node_id, visited)
            else "visible_unvisited"
        )
        action = _grid_exit_action(actor, location, (node.X, node.Y), z)
        builder.add_node(
            node_id,
            _grid_room_label((node.X, node.Y), z),
            node.X,
            node.Y,
            visibility=visibility,
            anchor=is_anchor,
            landmark=is_anchor,
            action=action,
        )
        builder.add_edge(current_id, node_id, _grid_direction_label(current_node, node), action is not None)

    # Registered wilderness gates: the grid side of the gateway pair renders
    # the gate's own approach cell's wild node (design D2). Geometry is the
    # renderer-local slot named by the registry face carried on the candidate
    # (never a parse of the exit's key/aliases -- every gate exit is keyed
    # 荒野); an occupied slot probes outward deterministically instead of
    # dropping the gate.
    for gate_id, (landing_cell, gate, direction) in gate_candidates.items():
        dx, dy = DIRECTION_DELTAS[direction]
        slot_x, slot_y = _free_slot(builder, x + dx, y + dy)
        action = (
            {"kind": "move", "exit_ref": _exit_ref(gate), "destination": gate_id}
            if _traversable(gate, actor)
            else None
        )
        builder.add_node(
            gate_id,
            _wild_region_label(*landing_cell),
            slot_x,
            slot_y,
            visibility=(
                "visible_visited"
                if _known_node_id(gate_id, visited)
                else "visible_unvisited"
            ),
            anchor=False,
            landmark=False,
            action=action,
        )
        builder.add_edge(current_id, gate_id, direction, action is not None)

    # Remembered grid-layer gateways: a map boundary stood on, not visited
    # ground (design D1-D6). The gateway filter runs over EVERY ordered
    # visited candidate -- not pre-truncated to the remaining node budget,
    # which would let enough recent non-gateway visits silently crowd an
    # older gateway out of the candidate list before the filter ever saw it
    # -- and only the FILTERED result is then bounded.
    gateway_candidates: list[tuple[str, int, int, str, str]] = []
    for visit in builder.remembered(len(builder.visited)):
        if not visit.node_id.startswith("grid:") or visit.node_id == current_id:
            continue
        decoded = decode_node(visit.node_id)
        if decoded["z_map_key"] != z:
            # A different grid map's coordinate space: omitted, never
            # plotted at a fabricated or cross-space position (design D3).
            continue
        gateway = _grid_gateway_at(decoded["x"], decoded["y"], decoded["z_map_key"])
        if gateway is None:
            # A visited grid room that is not a registered gate room (an
            # AnchorRoom plaza is an in-map landmark, not a way out; design D2).
            continue
        approach_cell, _, anchor_key = gateway
        far_label = _gateway_far_side_label("grid", approach_cell, anchor_key)
        boundary_name = _grid_room_label((decoded["x"], decoded["y"]), decoded["z_map_key"])
        gateway_candidates.append((visit.node_id, decoded["x"], decoded["y"], far_label, boundary_name))

    remembered_budget = min(MAX_REMEMBERED_GATEWAYS, MAX_NODES - len(builder.nodes))
    gateway_candidates = gateway_candidates[:remembered_budget]

    # Distinctness (design D5): two gates of one city can open onto the same
    # far-side region, so a repeated label is qualified with its own
    # boundary node's name. Counted over the final, bounded set only, so a
    # collision that was truncated away never forces an unneeded qualifier.
    label_counts: dict[str, int] = {}
    for _, _, _, far_label, _ in gateway_candidates:
        label_counts[far_label] = label_counts.get(far_label, 0) + 1
    for node_id, gx, gy, far_label, boundary_name in gateway_candidates:
        label = f"{far_label}（{boundary_name}）" if label_counts[far_label] > 1 else far_label
        builder.add_node(
            node_id,
            label,
            gx,
            gy,
            visibility="remembered",
            anchor=False,
            landmark=True,
            action=None,
        )

    return "grid"


def _grid_gate_candidates(location) -> dict[str, tuple[Any, Any, str]]:
    """Registered gate exits at ``location``, deduped by canonical wild id.

    Returns ``{wild_id: (landing_cell, gate_exit, face)}`` in deterministic
    dbid order (lowest dbid wins a duplicate registration of the same entry).
    An unregistered or missing ``db.anchor_key`` is not a gate; a registered
    entry whose coordinate cannot encode fails closed -- the presenter never
    emits an identity it cannot name.

    The gate's wilderness-side identity is its landing cell: the approach cell
    of the gate named by the exit's ``db.gate_direction`` (wilderness-anchor-
    footprint -- what the exit renders is where traversing it actually puts
    you). A row whose ``db.gate_direction`` is missing or names no gate of the
    entry is a misconfiguration the traversal itself refuses
    (``WildernessGateExit.at_traverse`` fails closed on the same lookup), so
    the presenter refuses to advertise it too -- the panel never offers an
    action that cannot be taken.

    ``face`` is the renderer direction the gate's node draws toward: the
    registry gate face (``OPPOSITE_DIRECTION[return_direction]``, the outward
    direction from the city -- exactly the direction of the exit provisioning
    placed on the gate room). It is derived from the registry, never from the
    exit's key/aliases, which cannot distinguish two gates whose exits share
    the key 荒野 (wilderness-anchor-footprint-local-map D2).
    """
    from typeclasses.exits import WildernessGateExit
    from world.lore.wilderness_entry import OPPOSITE_DIRECTION, WILDERNESS_ENTRY_REGISTRY
    from world.maps.wilderness_provider import WILDERNESS_NAME

    candidates: dict[str, tuple[Any, Any, str]] = {}
    gates = [e for e in location.exits if isinstance(e, WildernessGateExit)]
    for exit_obj in sorted(gates, key=lambda e: int(e.id)):
        try:
            entry = WILDERNESS_ENTRY_REGISTRY.get(exit_obj.db.anchor_key)
        except Exception:
            continue
        if entry is None:
            continue
        gate = entry.gate_for(exit_obj.db.gate_direction) if exit_obj.db.gate_direction else None
        landing_cell = entry.approach_cell(gate) if gate is not None else None
        face = OPPOSITE_DIRECTION.get(gate.return_direction) if gate is not None else None
        if landing_cell is None or face is None:
            # Same lookup, same refusal as the traversal: not a gate identity.
            continue
        try:
            gate_id = encode_wild(WILDERNESS_NAME, *landing_cell)
        except Exception:
            raise PanelUnavailableError
        candidates.setdefault(gate_id, (landing_cell, exit_obj, face))
    return candidates


def _trim_visible(nodes: list, current_node, cap: int) -> list:
    """Cap the visible set, dropping the farthest nodes first (design D2).

    Deterministic drop order: descending Chebyshev distance from the current
    node, then descending Y, then descending X. The current node is never
    dropped.
    """
    if len(nodes) <= cap:
        return nodes
    cx, cy = current_node.X, current_node.Y
    droppable = sorted(
        (node for node in nodes if node.node_index != current_node.node_index),
        key=lambda node: (max(abs(node.X - cx), abs(node.Y - cy)), node.Y, node.X),
    )
    excess = len(nodes) - cap
    kept = {current_node.node_index} | {
        node.node_index for node in droppable[: max(len(droppable) - excess, 0)]
    }
    return [node for node in nodes if node.node_index in kept]


def _free_slot(builder: _GraphBuilder, x: int, y: int) -> tuple[int, int]:
    """Return ``(x, y)`` or the nearest free renderer-local slot (design D2).

    Deterministic probe order: ring sweep by ``(|dx| + |dy|)``, then ``dy``,
    then ``dx``, staying within the payload coordinate bounds. A free slot
    always exists -- the payload caps at 64 nodes while the COORD window
    offers far more slots -- but the sweep stays bounded and fails closed.
    """
    occupied = {(node["x"], node["y"]) for node in builder.nodes}
    if (
        (x, y) not in occupied
        and COORD_MIN <= x <= COORD_MAX
        and COORD_MIN <= y <= COORD_MAX
    ):
        return (x, y)
    for radius in range(1, MAX_NODES + 1):
        for _distance, dy, dx in sorted(
            (abs(dx) + abs(dy), dy, dx)
            for dx in range(-radius, radius + 1)
            for dy in range(-radius, radius + 1)
            if abs(dx) + abs(dy) == radius
        ):
            slot = (x + dx, y + dy)
            if (
                COORD_MIN <= slot[0] <= COORD_MAX
                and COORD_MIN <= slot[1] <= COORD_MAX
                and slot not in occupied
            ):
                return slot
    raise PanelUnavailableError


def _grid_nodes_in_range(xymap, current_node, visual_range: int, map_mode: str) -> list:
    """Return the linked nodes within the configured visual range (D6)."""
    seen: dict[int, Any] = {}
    if map_mode == "scan":
        # scan: rectangular cut-out around the current node on the XY grid.
        cx, cy = current_node.X, current_node.Y
        for node in xymap.node_index_map.values():
            if abs(node.X - cx) <= visual_range and abs(node.Y - cy) <= visual_range:
                seen[node.node_index] = node
        return list(seen.values())
    # nodes: depth-first over linked nodes up to `visual_range` hops.
    frontier = [current_node]
    seen = {current_node.node_index: current_node}
    for _ in range(visual_range):
        next_frontier: list[Any] = []
        for node in frontier:
            for end_node in node.links.values():
                if end_node.node_index not in seen:
                    seen[end_node.node_index] = end_node
                    next_frontier.append(end_node)
        frontier = next_frontier
    return list(seen.values())


def _grid_node_in_map(xymap, node_id: str) -> bool:
    try:
        decoded = decode_node(node_id)
    except KnowledgeError:
        return False
    if decoded["z_map_key"] != xymap.Z:
        return False
    try:
        return xymap.get_node_from_coord((decoded["x"], decoded["y"])) is not None
    except Exception:
        return False


def _grid_coord_is_anchor(xymap, coord: tuple[int, int]) -> bool:
    try:
        node = xymap.get_node_from_coord(coord)
    except Exception:
        return False
    return node is not None and getattr(node, "interrupt_path", False) or (
        node is not None and node.symbol == "@"
    )


def _grid_room_label(coord: tuple[int, int], z: str) -> str:
    """The room key at one grid coordinate, or a coordinate fallback."""
    from typeclasses.rooms import GridRoom

    room = GridRoom.objects.filter_xyz(xyz=(coord[0], coord[1], z)).first()
    return room.key if room is not None else f"({coord[0]},{coord[1]})"


def _grid_direction_label(current_node, end_node) -> str:
    for direction, linked in current_node.links.items():
        if linked.node_index == end_node.node_index:
            return direction
    return ""


def _grid_exit_action(actor: Any, room, coord: tuple[int, int], z: str) -> dict[str, Any] | None:
    """Return the move descriptor for a real, traversable exit to ``coord``.

    Traversability is checked against the actual actor (not the room), so a
    lock that names the player, their permissions, or their attributes yields
    the correct movement descriptor for that player.
    """
    from typeclasses.rooms import GridRoom

    destination = GridRoom.objects.filter_xyz(xyz=(coord[0], coord[1], z)).first()
    if destination is None:
        return None
    for exit_obj in room.exits:
        if exit_obj.destination is destination:
            if not _traversable(exit_obj, actor):
                return None
            return {
                "kind": "move",
                "exit_ref": _exit_ref(exit_obj),
                "destination": encode_grid(str(z), coord[0], coord[1]),
            }
    return None
