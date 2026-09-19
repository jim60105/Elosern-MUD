"""The wilderness layer adapter (design D7).

Builds the eight-neighbour wilderness payload from provider bounds, terrain
labels, and the resolver-truth node identity: a step resolving to a registered
gateway IS the resolved grid node, and in-view gate approach cells are named
for their far side.
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
    _wilderness_gateway_at,
)
from web.webclient.presentation.local_map.grid import _grid_room_label
from web.webclient.presentation.local_map.validate import (
    MAX_NODES,
    MAX_REMEMBERED_GATEWAYS,
    WILD_DIRECTIONS,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.map_knowledge import (
    KnowledgeError,
    NodeVisit,
    decode_node,
    encode_wild,
)


def _wilderness_layer(actor: Any, visits: list[NodeVisit], builder: _GraphBuilder) -> str:
    """Build the wilderness layer from provider bounds and terrain labels (D7).

    Every traversable adjacent node carries the exact ``move`` descriptor with
    the canonical destination resolved through
    ``resolve_wilderness_destination`` (fix-wilderness-web-navigation) -- the
    contrib's self-loop exits never name the real arrival node, and the
    registered gateway south exit actually returns to the grid. The edge is
    only ``traversable`` when the node carries a move action, matching the
    grid layer.

    Node identity follows resolution (fix-wilderness-map-adjacency-truth D1):
    when a step resolves to a ``grid:`` node -- the registered gateway -- the
    node IS that grid node (id, room label, visited knowledge), positioned at
    the renderer-local adjacent cell so the lattice keeps its clean 3x3
    neighbourhood. A resolved grid destination that cannot be decoded (the
    map was rescinded) fails closed.
    """
    from typeclasses.rooms import AnchorRoom, GridRoom, TerrainRoom
    from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
    from world.maps.wilderness_destination import (
        normalize_wilderness_direction,
        DIRECTION_DELTAS,
        wilderness_neighbor,
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
        neighbor = wilderness_neighbor(x, y, direction)
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
        if destination is not None and destination.startswith("grid:"):
            # Registered gateway: the node is the resolved grid room itself.
            try:
                decoded = decode_node(destination)
            except KnowledgeError:
                raise PanelUnavailableError
            room = GridRoom.objects.filter_xyz(
                xyz=(decoded["x"], decoded["y"], decoded["z_map_key"])
            ).first()
            if room is None:
                label, is_anchor = destination, False
            else:
                label = room.key
                is_anchor = isinstance(room, AnchorRoom)
            # Renderer-local geometry keeps the 3x3 lattice. The gateway's
            # adjacent cell may be provider-invalid without being an edge:
            # an approach cell's gate direction faces an anchor-footprint
            # cell (wilderness-anchor-footprint), and provider edges refuse
            # a step too. The node is a grid identity, never a wild cell,
            # and footprint/edge cells can never host a drawn wild node --
            # the geometric adjacent cell is therefore always free.
            if neighbor is not None:
                nx, ny = neighbor
            else:
                dx, dy = DIRECTION_DELTAS[direction]
                nx, ny = x + dx, y + dy
            builder.add_node(
                destination,
                label,
                nx,
                ny,
                visibility=(
                    "visible_visited"
                    if _known_node_id(destination, visited)
                    else "visible_unvisited"
                ),
                anchor=is_anchor,
                landmark=is_anchor,
                action=action,
            )
            builder.add_edge(current_id, destination, direction, action is not None)
            continue
        if neighbor is None:
            continue
        nx, ny = neighbor
        node_id = encode_wild(WILDERNESS_NAME, nx, ny)
        visibility = (
            "visible_visited"
            if _known_node_id(node_id, visited)
            else "visible_unvisited"
        )
        # FLAGGED/STRIKEABLE (design D8a, ADDED requirement "The map surfaces
        # state a place name only where it adds information"): an in-view
        # neighbour that is itself a registered gate's approach cell is named
        # for the place its traversal reaches, not the region it stands on --
        # closing the same one-name-repeated-nine-times defect inside the
        # drawn field of view that the remembered-gateway rule closes outside
        # it. Nothing else about the node (id, action, edge, visibility)
        # changes.
        neighbor_gateway = _wilderness_gateway_at(nx, ny)
        if neighbor_gateway is not None:
            _, _, neighbor_anchor_key = neighbor_gateway
            label = _gateway_far_side_label("wilderness", (nx, ny), neighbor_anchor_key)
        else:
            label = WILDERNESS_REGION_REGISTRY[region_for_coordinates(nx, ny)].display_name_zh
        builder.add_node(
            node_id,
            label,
            nx,
            ny,
            visibility=visibility,
            anchor=False,
            landmark=False,
            action=action,
        )
        builder.add_edge(current_id, node_id, direction, action is not None)

    # Remembered wilderness-layer gateways: a map boundary stood on, not
    # visited ground (design D1-D6). Same filter-then-bound ordering as the
    # grid layer -- the gateway filter runs over every ordered visited
    # candidate before the result is truncated to the remembered ceiling.
    gateway_candidates: list[tuple[str, int, int, str, str]] = []
    for visit in builder.remembered(len(builder.visited)):
        if not visit.node_id.startswith("wild:"):
            continue
        decoded = decode_node(visit.node_id)
        if abs(decoded["x"] - x) <= 1 and abs(decoded["y"] - y) <= 1:
            continue  # still inside the drawn field of view
        gateway = _wilderness_gateway_at(decoded["x"], decoded["y"])
        if gateway is None:
            continue
        _, (grid_xy, z_map_key), anchor_key = gateway
        far_label = _gateway_far_side_label("wilderness", (decoded["x"], decoded["y"]), anchor_key)
        boundary_name = _grid_room_label(grid_xy, z_map_key)
        gateway_candidates.append((visit.node_id, decoded["x"], decoded["y"], far_label, boundary_name))

    remembered_budget = min(MAX_REMEMBERED_GATEWAYS, MAX_NODES - len(builder.nodes))
    gateway_candidates = gateway_candidates[:remembered_budget]

    # Distinctness (design D5): one anchor can register more than one gate
    # (capital_altoria already has two), so the far-side name alone is not
    # unique on this layer either -- the same collision-then-qualify rule the
    # grid layer applies, mirrored here with the grid-side room as the
    # boundary qualifier. Counted over the final, bounded set only.
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

    return "wilderness"
