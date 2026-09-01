"""Canonical wilderness exit-destination resolution (wilderness-anchor-footprint).

The Evennia wilderness contrib builds the eight direction exits as self-loops
(``destination=room``), so ``exit_obj.destination`` can never name the real
arrival node. This module is the one resolver that derives the arrival node
from the current coordinates, direction, and the gateway rules of
``WILDERNESS_ENTRY_REGISTRY``, mirroring ``WildernessReturnExit.at_traverse``
(typeclasses/exits.py): a registered (approach-cell, return-direction) pair
resolves to its gate's ``grid:`` room; a point-shape anchor answers every
direction with its single gate; every other provider-valid direction steps one
cell; a provider-invalid neighbor (out of the rectangle or an anchor footprint
cell) resolves to ``None``, matching the stock step refusal.

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

from typing import Any

from world.lore.wilderness_entry import (
    WILDERNESS_ENTRY_REGISTRY,
    WildernessEntryPoint,
    WildernessGate,
)
from world.maps.wilderness_provider import (
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
    WILDERNESS_NAME,
    is_footprint_cell,
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


def _in_provider_rect(x: int, y: int) -> bool:
    return 0 <= x <= WILDERNESS_MAX_X and 0 <= y <= WILDERNESS_MAX_Y


def is_provider_valid_coordinates(coordinates: tuple[int, int]) -> bool:
    """Whether the provider accepts ``coordinates`` (rect minus footprints).

    The same boundary rule ``ElosernWildernessMapProvider.is_valid_coordinates``
    applies -- rectangle check plus live-registry footprint exclusion -- so the
    resolver's adjacency truth is the provider's, not a second opinion.
    """
    return _in_provider_rect(*coordinates) and not is_footprint_cell(coordinates)


def wilderness_neighbor(x: int, y: int, direction: str) -> tuple[int, int] | None:
    """Return the provider-valid adjacent cell for one normalized direction.

    The single direction-geometry source shared by the resolver's ordinary
    step, the return exit's stock fallback, and the minimap layers.
    ``direction`` must already be normalized (see
    :func:`normalize_wilderness_direction`); returns ``None`` when the step
    leaves the provider bounds or lands on an anchor footprint cell -- the
    provider refuses both, so the resolver must not offer either.
    """
    dx, dy = DIRECTION_DELTAS[direction]
    nx, ny = x + dx, y + dy
    if not is_provider_valid_coordinates((nx, ny)):
        return None
    return (nx, ny)


def _gateway_from_entry(
    entry: WildernessEntryPoint, coordinates: tuple[int, int], direction: str
) -> WildernessGate | None:
    """The gate ``entry`` advertises at ``coordinates`` in ``direction``.

    Footprint entry: the coordinates must equal one gate's approach cell and
    the direction must equal that gate's ``return_direction``. Point-shape
    entry: the coordinates must equal the anchor cell; ANY direction matches
    the single gate (cave semantics).
    """
    if entry.is_point_shape:
        return entry.gates[0] if entry.anchor_cell == coordinates and entry.gates else None
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

    Resolved from the registry's own ``grid_xy``/``z_map_key`` -- not from any
    exit object's stored anchor (the legacy ``_grid_room_for_anchor`` room-
    hanging assumption is deleted, not generalized).
    """
    from typeclasses.rooms import GridRoom

    x, y = gate.grid_xy
    return GridRoom.objects.filter_xyz((x, y, gate.z_map_key)).first()


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
        gx, gy = gate.grid_xy
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
