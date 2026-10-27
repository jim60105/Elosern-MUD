"""Canonical wilderness exit-destination resolution (wilderness-anchor-footprint).

The Evennia wilderness contrib builds the eight direction exits as self-loops
(``destination=room``), so ``exit_obj.destination`` can never name the real
arrival node. This module is the one resolver that derives the arrival node
from the current coordinates, direction, and the gateway rules of
``WILDERNESS_ENTRY_REGISTRY``, mirroring ``WildernessReturnExit.at_traverse``
(typeclasses/exits.py): a registered (approach-cell, return-direction) pair
resolves to its gate's ``grid:`` room; a point-shape anchor answers only its
single gate's authored direction; every other provider-valid direction steps
one cell; a provider-invalid neighbor (outside the frame, at sea, on the closed
ridge or a waterway, or on an anchor footprint cell) resolves to ``None``,
matching the stock step refusal.

The gateway lookup (:func:`find_gateway`) and the neighbor-validity rule
(:func:`wilderness_neighbor`) are the single shared helpers the return exit
also uses -- traversal and presentation cannot drift apart (canonical-
wilderness-destination requirement). The resolver never WRITES state; the one
exception its own contract demands is a gateway-hit lookup of the destination
``GridRoom`` (a missing room must resolve to ``None``, fail-closed like the
return exit), so ``resolve_wilderness_destination`` may read the database on a
gateway hit only. The pinning test moves a character through the real exit and
compares predicted and actual arrival nodes.
"""

from math import hypot
from typing import Any

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.wilderness_entry import (
    WILDERNESS_ENTRY_REGISTRY,
    WildernessEntryPoint,
    WildernessGate,
)
from world.maps.map_data import settlement_graph
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    is_valid_wilderness_cell,
)
from world.rules.map_knowledge import encode_grid, encode_wild

# One cell per cardinal direction (short form), matching the contrib's eight
# exits and the local-map layer's WILD_DIRECTIONS geometry.
DIRECTION_DELTAS = {
    "n": (0, 1),
    "ne": (1, 1),
    "e": (1, 0),
    "se": (1, -1),
    "s": (0, -1),
    "sw": (-1, -1),
    "w": (-1, 0),
    "nw": (-1, 1),
}

# The contrib keys its exits "north".."northwest"; long keys normalize to the
# short cardinal forms (which pass through unchanged). Longest keys first so
# "northwest" never normalizes into "nwest".
_DIRECTION_NORMALIZE = {
    "northwest": "nw",
    "northeast": "ne",
    "southwest": "sw",
    "southeast": "se",
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
}


def normalize_wilderness_direction(value: Any) -> str | None:
    """Return the short cardinal form for a wilderness exit key or direction.

    Accepts the contrib exit keys ("north", "southeast") and the short forms
    ("n", "se"), case-insensitively; returns ``None`` for anything else.
    """
    if not isinstance(value, str):
        return None
    lowered = value.lower()
    normalized = _DIRECTION_NORMALIZE.get(lowered, lowered)
    if normalized in DIRECTION_DELTAS:
        return normalized
    return None


def is_provider_valid_coordinates(coordinates: tuple[int, int]) -> bool:
    """Whether the provider accepts ``coordinates``.

    Exactly ``ElosernWildernessMapProvider.is_valid_coordinates``'s rule --
    frame, mainland, passable terrain, and live-registry footprint exclusion --
    so the resolver's adjacency truth is the provider's, not a second opinion.
    """
    return is_valid_wilderness_cell(coordinates)


def wilderness_neighbor(x: int, y: int, direction: str) -> tuple[int, int] | None:
    """Return the provider-valid adjacent cell for one normalized direction.

    The single direction-geometry source shared by the resolver's ordinary
    step, the return exit's stock fallback, and the minimap layers.
    ``direction`` must already be normalized (see
    :func:`normalize_wilderness_direction`); returns ``None`` when the step
    leaves the provider bounds or lands on an anchor footprint cell -- the
    provider refuses both, so the resolver must not offer either.

    A diagonal step additionally forbids corner cutting: either orthogonal
    neighbour being impassable (out of bounds or an anchor footprint cell)
    refuses the diagonal. Traversal, the canonical resolver and the local map
    all read this one rule, so an offered edge is always a traversable one.
    """
    dx, dy = DIRECTION_DELTAS[direction]
    nx, ny = x + dx, y + dy
    if not is_provider_valid_coordinates((nx, ny)):
        return None
    if dx and dy:
        if not is_provider_valid_coordinates((x + dx, y)):
            return None
        if not is_provider_valid_coordinates((x, y + dy)):
            return None
    return (nx, ny)


def cell_center_m(coordinates: tuple[int, int], cell_size_m: int) -> tuple[int, int]:
    """The absolute continent-meter center of one wilderness cell."""

    return (
        coordinates[0] * cell_size_m + cell_size_m // 2,
        coordinates[1] * cell_size_m + cell_size_m // 2,
    )


def _anchor_node(graph):
    """The sparse graph's authored anchor node, or ``None``."""

    for node in graph.nodes.values():
        if node.is_anchor:
            return node
    return None


def settlement_world_position_m(
    entry: WildernessEntryPoint,
    local_position_m: tuple[int, int],
    *,
    cell_size_m: int,
) -> tuple[int, int] | None:
    """Transform one settlement-local meter position into absolute meters.

    ``world_position_m = wilderness_anchor_center_m + local_position_m -
    local_anchor_position_m`` (world-map-scale design §5.3). The local anchor
    is the settlement graph's own anchor node's authored physical position, and
    the wilderness anchor is the center of the entry's anchor cell at the
    declared cell span. ``None`` means the graph or the anchor node is absent.
    """

    placement = ANCHOR_PLACEMENT_REGISTRY.get(entry.anchor_key)
    if placement is None:
        return None
    graph = settlement_graph(placement.zcoord)
    if graph is None:
        return None
    anchor = _anchor_node(graph)
    anchor_cell = entry.anchor_cell
    if anchor is None or anchor_cell is None:
        return None
    world_anchor = cell_center_m(anchor_cell, cell_size_m)
    local_anchor = anchor.physical_coordinate
    return (
        world_anchor[0] + local_position_m[0] - local_anchor[0],
        world_anchor[1] + local_position_m[1] - local_anchor[1],
    )


def gate_approach_distance_m(
    entry: WildernessEntryPoint,
    gate: WildernessGate,
    *,
    cell_size_m: int | None = None,
) -> float | None:
    """The authored physical gate-approach segment length in meters.

    One segment runs from the gate's grid node (its authored meter position,
    anchored through :func:`settlement_world_position_m`) to the exterior
    approach cell's center. Both directions of a crossing measure the same
    segment, so the approach is charged exactly once. ``None`` means the gate
    room has no authored settlement identity or metric position.
    """

    from world.maps.wilderness_provider import WILDERNESS_KM_PER_CELL

    span = (
        int(WILDERNESS_KM_PER_CELL) * 1000 if cell_size_m is None else int(cell_size_m)
    )
    placement = ANCHOR_PLACEMENT_REGISTRY.get(entry.anchor_key)
    if placement is None:
        return None
    graph = settlement_graph(placement.zcoord)
    if graph is None:
        return None
    from world.maps.static_references import settlement_node_xy

    node = graph.node_at(
        settlement_node_xy(gate.destination, source=f"wilderness gate {entry.anchor_key}")
    )
    approach = entry.approach_cell(gate)
    if node is None or approach is None:
        return None
    gate_world = settlement_world_position_m(
        entry, node.physical_coordinate, cell_size_m=span
    )
    if gate_world is None:
        return None
    approach_world = cell_center_m(approach, span)
    return hypot(
        approach_world[0] - gate_world[0], approach_world[1] - gate_world[1]
    )


def _gateway_from_entry(
    entry: WildernessEntryPoint, coordinates: tuple[int, int], direction: str
) -> WildernessGate | None:
    """The gate ``entry`` advertises at ``coordinates`` in ``direction``.

    Footprint entry: the coordinates must equal one gate's approach cell and
    the direction must equal that gate's ``return_direction``. Point-shape
    entry: the coordinates must equal the anchor cell and the direction must
    equal the single gate's authored ``return_direction`` -- an unrelated
    direction stays an ordinary wilderness step, so a concealed entry never
    hijacks a route.
    """
    if entry.is_point_shape:
        if entry.anchor_cell != coordinates or not entry.gates:
            return None
        gate = entry.gates[0]
        return gate if gate.return_direction == direction else None
    for gate in entry.gates:
        if gate.return_direction == direction and entry.approach_cell(gate) == coordinates:
            return gate
    return None


def find_gateway(
    coordinates: tuple[int, int], direction: str
) -> tuple[WildernessEntryPoint, WildernessGate] | None:
    """The registry entry+gate owning this (coordinates, direction) gateway.

    ``direction`` must already be normalized. This is THE shared gateway-match
    rule: both ``WildernessReturnExit.at_traverse`` and
    :func:`resolve_wilderness_destination` call only this, so traversal and
    presentation agree by construction (the legacy hardcoded
    ``(wilderness_xy, "south")`` pair is gone in any form).
    """
    for entry in WILDERNESS_ENTRY_REGISTRY.values():
        gate = _gateway_from_entry(entry, coordinates, direction)
        if gate is not None:
            return entry, gate
    return None


def grid_room_for_gate(gate: WildernessGate) -> Any:
    """The ``GridRoom`` a gate leads to, or ``None`` when it does not exist.

    Resolved from the gate's authored settlement-node identity against the
    current graph -- not from any exit object's stored anchor (the legacy
    ``_grid_room_for_anchor`` room-hanging assumption is deleted, not
    generalized).
    """
    from typeclasses.rooms import GridRoom
    from world.maps.static_references import settlement_node_xyz

    return GridRoom.objects.filter_xyz(settlement_node_xyz(gate.destination)).first()


def resolve_wilderness_destination(
    room: Any, direction: Any, gateway_rule: Any = None
) -> str | None:
    """Return the canonical arrival node ID for one wilderness step, or ``None``.

    Mirrors ``WildernessReturnExit.at_traverse`` via the shared helpers: a
    registered gateway step resolves to the gate's ``grid:`` node, a provider-
    valid direction resolves to the adjacent ``wild:`` cell, and a refused
    step -- non-terrain room, missing coordinates, unknown direction,
    provider-invalid neighbor, or a gateway whose grid room does not exist --
    resolves to ``None`` exactly where traversal refuses.

    ``gateway_rule`` is a ``WildernessEntryPoint`` from
    ``world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY`` -- the same
    registration the return exit reads (single source). When ``None`` the
    gateway match consults the whole registry; an injected rule applies only
    when IT advertises this (coordinates, direction) pair, exactly like the
    return exit's own lookup -- an injected rule for another entry or cell
    leaves the step ordinary.
    """
    from typeclasses.rooms import TerrainRoom

    if not isinstance(room, TerrainRoom):
        return None
    coordinates = room.coordinates
    if coordinates is None:
        return None
    x, y = coordinates
    normalized = normalize_wilderness_direction(direction)
    if normalized is None:
        return None

    if gateway_rule is None:
        hit = find_gateway(coordinates, normalized)
    else:
        gate = _gateway_from_entry(gateway_rule, coordinates, normalized)
        hit = (gateway_rule, gate) if gate is not None else None
    if hit is not None:
        _, gate = hit
        if grid_room_for_gate(gate) is None:
            # Misconfiguration (destination room missing): the return exit
            # refuses the step, so the edge is unroutable.
            return None
        from world.maps.static_references import settlement_node_xy

        gx, gy = settlement_node_xy(gate.destination)
        return encode_grid(gate.z_map_key, gx, gy)

    neighbor = wilderness_neighbor(x, y, normalized)
    if neighbor is None:
        return None
    nx, ny = neighbor
    return encode_wild(WILDERNESS_NAME, nx, ny)


__all__ = [
    "DIRECTION_DELTAS",
    "find_gateway",
    "grid_room_for_gate",
    "is_provider_valid_coordinates",
    "normalize_wilderness_direction",
    "resolve_wilderness_destination",
    "wilderness_neighbor",
]
