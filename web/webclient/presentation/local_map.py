"""Exact schema-version-1 ``local_map`` panel and presenter (map-knowledge-minimap).

The presenter serializes a read-only local minimap from canonical room, map,
and knowledge data. It is registered beside ``status`` and ``context_actions``
in the production registry and never mutates knowledge, traits, clock, or
location.

The payload shape and the exact shared bounds (design D10a) are mirrored by the
client validator in ``web/static/webclient/js/elosern/protocol.js`` and guarded
by a dual-direction parity test.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.map_knowledge import (
    KnowledgeError,
    NodeVisit,
    decode_node,
    encode_grid,
    encode_room,
    encode_wild,
    parse_knowledge,
)

LOCAL_MAP_SCHEMA_VERSION = 1

# Exact shared bounds (design D10a) -- must stay equal in the JS validator.
MAX_NODES = 64
MAX_EDGES = 128
MAX_LEGEND = 16
MAX_STRING_CODE_POINTS = 256
MAX_TITLE_CODE_POINTS = 128
MAX_NODE_ID_CHARS = 128
MAX_EXIT_REF_CHARS = 64
COORD_MIN = -1024
COORD_MAX = 1024

VISIBILITIES = ("current", "visible_unvisited", "visible_visited", "remembered")
LAYERS = ("grid", "wilderness", "instance", "interior")
ACTION_KINDS = ("move",)

# Grid visual-range option bounds (sample-city-altoria).
MAX_GRID_VISUAL_RANGE = 8
GRID_MODES = ("nodes", "scan")

# The eight wilderness cardinal directions (wilderness-map-provider).
WILD_DIRECTIONS = ("n", "ne", "e", "se", "s", "sw", "w", "nw")

# Stable localized legend labels explaining the visibility states.
LEGEND_LABELS = (
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
    "曾經到過、但不在附近的遠方位置",
)


class LocalMapError(ProtocolValidationError):
    """The available local_map payload violates its exact bounded schema."""


def _require_node_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) > MAX_NODE_ID_CHARS:
        raise ProtocolValidationError(f"{field} exceeds the maximum node-ID length")
    decode_node(value)
    return value


def _require_exit_ref(value: Any, field: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_EXIT_REF_CHARS:
        raise ProtocolValidationError(
            f"{field} must be 1..{MAX_EXIT_REF_CHARS} ASCII characters"
        )
    if not value.isascii():
        raise ProtocolValidationError(f"{field} must be ASCII")
    return value


def _require_coord(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolValidationError(f"{field} must be an integer")
    if not COORD_MIN <= value <= COORD_MAX:
        raise ProtocolValidationError(f"{field} must be within {COORD_MIN}..{COORD_MAX}")
    return value


def _validate_action(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_exact_fields(value, "action", {"kind", "exit_ref", "destination"}, {})
    if value["kind"] not in ACTION_KINDS:
        raise ProtocolValidationError("action kind is not a stable value")
    _require_exit_ref(value["exit_ref"], "action.exit_ref")
    _require_node_id(value["destination"], "action.destination")
    return {
        "kind": value["kind"],
        "exit_ref": value["exit_ref"],
        "destination": value["destination"],
    }


def _validate_node(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "node",
        {"id", "label", "x", "y", "visibility", "current", "anchor", "landmark", "action"},
        {},
    )
    node_id = _require_node_id(value["id"], "node.id")
    label = _require_str(value, "label", maximum=MAX_STRING_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("node.label must be non-empty")
    x = _require_coord(value["x"], "node.x")
    y = _require_coord(value["y"], "node.y")
    visibility = value["visibility"]
    if visibility not in VISIBILITIES:
        raise ProtocolValidationError("node.visibility is not a stable value")
    current = _require_bool(value, "current")
    anchor = _require_bool(value, "anchor")
    landmark = _require_bool(value, "landmark")
    action = _validate_action(value["action"])
    if visibility == "current" and not current:
        raise ProtocolValidationError("the current node must carry current=True")
    if current and visibility != "current":
        raise ProtocolValidationError("a non-current node must not carry current=True")
    return {
        "id": node_id,
        "label": label,
        "x": x,
        "y": y,
        "visibility": visibility,
        "current": current,
        "anchor": anchor,
        "landmark": landmark,
        "action": action,
    }


def _validate_edge(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "edge",
        {"source", "destination", "label", "known", "traversable"},
        {},
    )
    source = _require_node_id(value["source"], "edge.source")
    destination = _require_node_id(value["destination"], "edge.destination")
    label = _require_str(value, "label", maximum=MAX_STRING_CODE_POINTS)
    known = _require_bool(value, "known")
    traversable = _require_bool(value, "traversable")
    if source == destination:
        raise ProtocolValidationError("an edge must connect two distinct nodes")
    return {
        "source": source,
        "destination": destination,
        "label": label,
        "known": known,
        "traversable": traversable,
    }


def validate_local_map(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``local_map`` payload.

    Returns a normalized payload or raises :class:`LocalMapError`. The common
    unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "local_map panel",
        {"schema_version", "available", "layer", "current_node", "title", "nodes", "edges", "legend"},
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != LOCAL_MAP_SCHEMA_VERSION:
        raise LocalMapError("unsupported local_map schema_version")
    if not _require_bool(payload, "available"):
        raise LocalMapError("available must be true for the local_map form")
    layer = payload["layer"]
    if layer not in LAYERS:
        raise LocalMapError("layer is not a stable value")
    current_node = _require_node_id(payload["current_node"], "current_node")
    decoded = decode_node(current_node)
    if layer == "grid" and decoded["prefix"] != "grid":
        raise LocalMapError("a grid-layer payload must have a grid current node")
    if layer == "wilderness" and decoded["prefix"] != "wild":
        raise LocalMapError("a wilderness-layer payload must have a wild current node")
    if layer in ("instance", "interior") and decoded["prefix"] != "room":
        raise LocalMapError(
            "an instance/interior payload must have a room current node"
        )
    title = _require_str(payload, "title", maximum=MAX_TITLE_CODE_POINTS)
    if not title.strip():
        raise LocalMapError("title must be non-empty")

    nodes = payload["nodes"]
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES:
        raise LocalMapError(f"nodes must be a list of 1..{MAX_NODES} entries")
    node_views = [_validate_node(item) for item in nodes]
    if not any(node_view["current"] for node_view in node_views):
        raise LocalMapError("the payload must mark exactly one current node")
    if len([node_view for node_view in node_views if node_view["current"]]) != 1:
        raise LocalMapError("the payload must mark exactly one current node")
    if not any(node_view["id"] == current_node for node_view in node_views):
        raise LocalMapError("current_node must be present in nodes")
    node_ids = [node_view["id"] for node_view in node_views]
    if len(set(node_ids)) != len(node_ids):
        raise LocalMapError("node ids must be unique")

    edges = payload["edges"]
    if not isinstance(edges, list) or len(edges) > MAX_EDGES:
        raise LocalMapError(f"edges must be a list of at most {MAX_EDGES} entries")
    edge_views = [_validate_edge(item) for item in edges]
    node_id_set = set(node_ids)
    for edge_view in edge_views:
        if edge_view["source"] not in node_id_set:
            raise LocalMapError("edge.source must reference a presented node")
        if edge_view["destination"] not in node_id_set:
            raise LocalMapError("edge.destination must reference a presented node")

    legend = payload["legend"]
    if not isinstance(legend, list) or len(legend) > MAX_LEGEND:
        raise LocalMapError(f"legend must be a list of at most {MAX_LEGEND} entries")
    legend_views = []
    for entry in legend:
        text = _require_str({"legend": entry}, "legend", maximum=MAX_STRING_CODE_POINTS)
        if not text.strip():
            raise LocalMapError("legend entries must be non-empty")
        legend_views.append(text)

    result = {
        "schema_version": LOCAL_MAP_SCHEMA_VERSION,
        "available": True,
        "layer": layer,
        "current_node": current_node,
        "title": title,
        "nodes": node_views,
        "edges": edge_views,
        "legend": legend_views,
    }
    # Envelope guarantee (design D10a): a conforming payload must serialize
    # within the OOB envelope limit. The per-field bounds are ceilings, not a
    # guarantee that any combination of them fits, so the validator enforces
    # the serialized size directly -- a payload that would exceed the envelope
    # fails closed rather than being emitted.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise LocalMapError("local_map payload exceeds the OOB envelope limit")
    return result


# ---------------------------------------------------------------------------
# Layer adapters: read canonical map/knowledge data, never rendered ANSI.
# ---------------------------------------------------------------------------


def _visited_map(visits: list[NodeVisit]) -> dict[str, NodeVisit]:
    return {visit.node_id: visit for visit in visits}


def _known_node_id(node_id: str, visited: dict[str, NodeVisit]) -> bool:
    return node_id in visited


class _GraphBuilder:
    """Accumulates bounded nodes/edges and the exact payload node dicts."""

    def __init__(self, visited: dict[str, NodeVisit]) -> None:
        self.visited = visited
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self._by_id: dict[str, dict[str, Any]] = {}

    def add_node(
        self,
        node_id: str,
        label: str,
        x: int,
        y: int,
        *,
        visibility: str,
        current: bool = False,
        anchor: bool = False,
        landmark: bool = False,
        action: dict[str, Any] | None = None,
    ) -> None:
        existing = self._by_id.get(node_id)
        if existing is not None:
            # A later exit-derived descriptor may enrich a node first added as
            # an origin/return with a travel action; never downgrade a node
            # that already carries one.
            if existing["action"] is None and action is not None:
                existing["action"] = action
            return
        node = {
            "id": node_id,
            "label": label,
            "x": x,
            "y": y,
            "visibility": visibility,
            "current": current,
            "anchor": anchor,
            "landmark": landmark,
            "action": action,
        }
        self.nodes.append(node)
        self._by_id[node_id] = node

    def add_edge(self, source: str, destination: str, label: str, traversable: bool) -> None:
        known = _known_node_id(destination, self.visited)
        self.edges.append(
            {
                "source": source,
                "destination": destination,
                "label": label,
                "known": known,
                "traversable": traversable,
            }
        )

    def remembered(self, cap: int) -> list[dict[str, Any]]:
        """Return the bounded remembered nodes, most-recent ``last_seen`` first."""
        candidates = [
            visit
            for visit in self.visited.values()
            if visit.node_id not in self._by_id and visit.node_id.startswith(("grid:", "wild:", "room:"))
        ]
        candidates.sort(key=lambda visit: (-visit.last_seen_tick, visit.node_id))
        return candidates[:cap]


def _exit_ref(exit_obj: Any) -> str:
    """An opaque, stable ASCII identifier for a real exit (its dbref)."""
    return str(int(exit_obj.id))


def _traversable(exit_obj: Any, actor: Any) -> bool:
    try:
        return bool(exit_obj.access(actor, "traverse"))
    except Exception:
        return False


def _grid_layer(actor: Any, visits: list[NodeVisit], builder: _GraphBuilder) -> str:
    """Build the grid/anchor layer from the live XYMap node/link model (D6)."""
    from typeclasses.rooms import AnchorRoom, GridRoom

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
    in_range = _grid_nodes_in_range(xymap, current_node, visual_range, map_mode)
    known_visited_ids = {
        node_id
        for node_id in visited
        if node_id.startswith("grid:") and _grid_node_in_map(xymap, node_id)
    }

    # Current node first, then in-range nodes, then bounded remembered.
    current_id = encode_grid(str(z), x, y)
    anchor_coord = None
    for node in sorted(xymap.node_index_map.values(), key=lambda n: (n.Y, n.X)):
        if node.node_index == current_node.node_index:
            anchor_coord = (node.X, node.Y)
            break
    if anchor_coord is None:
        raise PanelUnavailableError

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
            _grid_node_label(xymap, node, (node.X, node.Y), z),
            node.X,
            node.Y,
            visibility=visibility,
            anchor=is_anchor,
            landmark=is_anchor,
            action=action,
        )
        builder.add_edge(current_id, node_id, _grid_direction_label(current_node, node), action is not None)

    # Remembered grid nodes (outside visual range), bounded.
    for visit in builder.remembered(MAX_NODES - len(builder.nodes)):
        if not visit.node_id.startswith("grid:"):
            continue
        if visit.node_id == current_id:
            continue
        decoded = decode_node(visit.node_id)
        builder.add_node(
            visit.node_id,
            _grid_coord_label(xymap, (decoded["x"], decoded["y"]), decoded["z_map_key"]),
            decoded["x"],
            decoded["y"],
            visibility="remembered",
            anchor=_grid_coord_is_anchor(xymap, (decoded["x"], decoded["y"])),
            landmark=False,
            action=None,
        )

    return "grid"


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


def _grid_node_label(xymap, node, coord: tuple[int, int], z: str) -> str:
    from typeclasses.rooms import GridRoom

    room = GridRoom.objects.filter_xyz(xyz=(coord[0], coord[1], z)).first()
    return room.key if room is not None else f"({coord[0]},{coord[1]})"


def _grid_coord_label(xymap, coord: tuple[int, int], z: str) -> str:
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


def _wilderness_layer(actor: Any, visits: list[NodeVisit], builder: _GraphBuilder) -> str:
    """Build the wilderness layer from provider bounds and terrain labels (D7).

    Every traversable adjacent node carries the exact ``move`` descriptor with
    the canonical destination resolved through
    ``resolve_wilderness_destination`` (fix-wilderness-web-navigation) -- the
    contrib's self-loop exits never name the real arrival node, and the
    registered gateway south exit actually returns to the grid. The edge is
    only ``traversable`` when the node carries a move action, matching the
    grid layer.
    """
    from typeclasses.rooms import TerrainRoom
    from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
    from world.maps.wilderness_destination import (
        normalize_wilderness_direction,
        resolve_wilderness_destination,
    )
    from world.maps.wilderness_provider import (
        WILDERNESS_MAX_X,
        WILDERNESS_MAX_Y,
        WILDERNESS_NAME,
        region_for_coordinates,
    )

    location = actor.location
    if not isinstance(location, TerrainRoom):
        raise PanelUnavailableError
    coordinates = location.coordinates
    if coordinates is None:
        raise PanelUnavailableError
    x, y = coordinates
    if not (0 <= x <= WILDERNESS_MAX_X and 0 <= y <= WILDERNESS_MAX_Y):
        raise PanelUnavailableError
    visited = _visited_map(visits)
    current_id = encode_wild(WILDERNESS_NAME, x, y)

    builder.add_node(
        current_id,
        WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)].display_name_zh,
        x,
        y,
        visibility="current",
        current=True,
        anchor=False,
        landmark=False,
        action=None,
    )

    # Direction -> real exit object (the contrib keys the eight exits
    # "north".."northwest"). Only exits whose own key is a canonical
    # wilderness direction map; an unrelated exit (e.g. one aliased "s")
    # must never hijack a direction's move descriptor.
    exits_by_direction: dict[str, Any] = {}
    for exit_obj in location.exits:
        direction = normalize_wilderness_direction(exit_obj.key)
        if direction is not None:
            exits_by_direction.setdefault(direction, exit_obj)

    # Eight legal adjacent cells are visible (visited or unvisited).
    for direction in WILD_DIRECTIONS:
        neighbor = _wild_neighbor(x, y, direction)
        if neighbor is None:
            continue
        nx, ny = neighbor
        node_id = encode_wild(WILDERNESS_NAME, nx, ny)
        visibility = (
            "visible_visited"
            if _known_node_id(node_id, visited)
            else "visible_unvisited"
        )
        destination = resolve_wilderness_destination(location, direction)
        exit_obj = exits_by_direction.get(direction)
        action = None
        if (
            destination is not None
            and exit_obj is not None
            and _traversable(exit_obj, actor)
        ):
            action = {
                "kind": "move",
                "exit_ref": _exit_ref(exit_obj),
                "destination": destination,
            }
        builder.add_node(
            node_id,
            WILDERNESS_REGION_REGISTRY[region_for_coordinates(nx, ny)].display_name_zh,
            nx,
            ny,
            visibility=visibility,
            anchor=False,
            landmark=False,
            action=action,
        )
        builder.add_edge(current_id, node_id, direction, action is not None)

    # Remembered wild cells outside adjacency, bounded by most-recent last_seen.
    for visit in builder.remembered(MAX_NODES - len(builder.nodes)):
        if not visit.node_id.startswith("wild:"):
            continue
        decoded = decode_node(visit.node_id)
        if abs(decoded["x"] - x) > 1 or abs(decoded["y"] - y) > 1:
            builder.add_node(
                visit.node_id,
                WILDERNESS_REGION_REGISTRY[
                    region_for_coordinates(decoded["x"], decoded["y"])
                ].display_name_zh,
                decoded["x"],
                decoded["y"],
                visibility="remembered",
                anchor=False,
                landmark=False,
                action=None,
            )

    return "wilderness"


def _wild_neighbor(x: int, y: int, direction: str) -> tuple[int, int] | None:
    from world.maps.wilderness_provider import WILDERNESS_MAX_X, WILDERNESS_MAX_Y

    deltas = {
        "n": (0, 1),
        "ne": (1, 1),
        "e": (1, 0),
        "se": (1, -1),
        "s": (0, -1),
        "sw": (-1, -1),
        "w": (-1, 0),
        "nw": (-1, 1),
    }
    dx, dy = deltas[direction]
    nx, ny = x + dx, y + dy
    if not (0 <= nx <= WILDERNESS_MAX_X and 0 <= ny <= WILDERNESS_MAX_Y):
        return None
    return (nx, ny)


def _interior_graph(actor: Any, visits: list[NodeVisit], builder: _GraphBuilder, is_instance: bool) -> str:
    """Build the coordinate-free instance/interior graph from real Exits (D8)."""
    from typeclasses.rooms import InstanceRoom, Room

    location = actor.location
    if is_instance and not isinstance(location, InstanceRoom):
        raise PanelUnavailableError
    if not is_instance and not isinstance(location, Room):
        raise PanelUnavailableError
    visited = _visited_map(visits)
    current_id = encode_room(int(location.id))

    builder.add_node(
        current_id,
        location.key,
        0,
        0,
        visibility="current",
        current=True,
        anchor=False,
        landmark=False,
        action=None,
    )

    # Origin/return node for an instance.
    if is_instance:
        origin = location.origin_room
        if origin is not None and getattr(origin, "id", None):
            origin_id = encode_room(int(origin.id))
            builder.add_node(
                origin_id,
                origin.key,
                0,
                1,
                visibility=(
                    "visible_visited"
                    if _known_node_id(origin_id, visited)
                    else "visible_unvisited"
                ),
                anchor=False,
                landmark=False,
                action=None,
            )
            builder.add_edge(current_id, origin_id, "回程", True)

    # One-hop exits: visited adjacent rooms keep their names; unvisited
    # destinations are labelled 未探索 with the room name withheld.
    index = 1
    for exit_obj in sorted(location.exits, key=lambda e: (e.key or "")):
        destination = exit_obj.destination
        if destination is None or not getattr(destination, "id", None):
            continue
        dest_id = encode_room(int(destination.id))
        if dest_id == current_id:
            continue
        known = _known_node_id(dest_id, visited)
        if not known:
            label = "未探索"
        else:
            label = destination.key
        builder.add_node(
            dest_id,
            label,
            index,
            0,
            visibility="visible_visited" if known else "visible_unvisited",
            anchor=False,
            landmark=False,
            action=(
                {
                    "kind": "move",
                    "exit_ref": _exit_ref(exit_obj),
                    "destination": dest_id,
                }
                if _traversable(exit_obj, actor)
                else None
            ),
        )
        builder.add_edge(current_id, dest_id, exit_obj.key or "", True)
        index += 1

    # Remembered room nodes outside the current graph, bounded. A room node
    # whose object no longer resolves is treated as unavailable and omitted
    # (D4); the next reclamation prunes it idempotently.
    for visit in builder.remembered(MAX_NODES - len(builder.nodes)):
        if not visit.node_id.startswith("room:"):
            continue
        if visit.node_id == current_id or visit.node_id in {
            node["id"] for node in builder.nodes
        }:
            continue
        decoded = decode_node(visit.node_id)
        room = _room_by_id(decoded["dbref"])
        if room is None:
            continue
        builder.add_node(
            visit.node_id,
            room.key,
            index,
            0,
            visibility="remembered",
            anchor=False,
            landmark=False,
            action=None,
        )
        index += 1

    return "instance" if is_instance else "interior"


def _room_by_id(dbref: int):
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(id=dbref).first()


def local_map_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``local_map`` panel for the authenticated puppet."""
    actor = context.actor
    location = getattr(actor, "location", None)
    if location is None:
        raise PanelUnavailableError
    try:
        visits = parse_knowledge(actor)
    except KnowledgeError:
        raise PanelUnavailableError

    from typeclasses.rooms import GridRoom, InstanceRoom, TerrainRoom

    builder = _GraphBuilder(_visited_map(visits))
    if isinstance(location, GridRoom):
        layer = _grid_layer(actor, visits, builder)
        title = f"{location.key}街道圖"
    elif isinstance(location, TerrainRoom):
        layer = _wilderness_layer(actor, visits, builder)
        title = "荒野地圖"
    elif isinstance(location, InstanceRoom):
        layer = _interior_graph(actor, visits, builder, is_instance=True)
        title = f"{location.key}空間平面圖"
    else:
        layer = _interior_graph(actor, visits, builder, is_instance=False)
        title = f"{location.key}平面圖"

    if not any(node["current"] for node in builder.nodes):
        raise PanelUnavailableError

    payload = {
        "schema_version": LOCAL_MAP_SCHEMA_VERSION,
        "available": True,
        "layer": layer,
        "current_node": next(node["id"] for node in builder.nodes if node["current"]),
        "title": title,
        "nodes": builder.nodes,
        "edges": builder.edges,
        "legend": list(LEGEND_LABELS),
    }
    return validate_local_map(payload)
