"""Canonical wilderness exit-destination resolution (fix-wilderness-web-navigation).

The Evennia wilderness contrib builds the eight direction exits as self-loops
(``destination=room``), so ``exit_obj.destination`` can never name the real
arrival node. This module is the one resolver that derives the arrival node
from the current coordinates, direction, and gateway rules, mirroring
``WildernessReturnExit.at_traverse`` (typeclasses/exits.py): ordinary
directions step one cell; the registered gateway south exit returns to its
grid room. The minimap and exploration presenters consume it so every surface
advertises the node the player actually reaches.

The resolver is a pure read helper -- it never writes state -- and reads the
same entry registry the return exit reads, so presentation cannot drift from
traversal. Keep it in sync with ``WildernessReturnExit.at_traverse``; the
pinning test moves through the real exit and compares predicted and actual
arrival nodes.
"""

from typing import Any

from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.wilderness_provider import WILDERNESS_MAX_X, WILDERNESS_MAX_Y, WILDERNESS_NAME
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


def wilderness_neighbor(x: int, y: int, direction: str) -> tuple[int, int] | None:
    """Return the provider-bounded adjacent cell for one normalized direction.

    The single direction-geometry source shared by the resolver's ordinary
    step and the minimap layers (fix-wilderness-map-adjacency-truth D3).
    ``direction`` must already be normalized (see
    :func:`normalize_wilderness_direction`); returns ``None`` when the step
    leaves the provider bounds.
    """
    dx, dy = DIRECTION_DELTAS[direction]
    nx, ny = x + dx, y + dy
    if not (0 <= nx <= WILDERNESS_MAX_X and 0 <= ny <= WILDERNESS_MAX_Y):
        return None
    return (nx, ny)


def resolve_wilderness_destination(
    room: Any, direction: Any, gateway_rule: Any = None
) -> str | None:
    """Return the canonical arrival node ID for one wilderness step, or ``None``.

    Mirrors ``WildernessReturnExit.at_traverse`` (typeclasses/exits.py):
    ordinary directions resolve to the adjacent ``wild:`` cell, and the
    registered gateway south exit resolves to the ``grid:`` node of the room
    the gate is attached to. Returns ``None`` exactly where ``at_traverse``
    refuses the step: a non-terrain room, missing coordinates, an unknown
    direction, an out-of-bounds neighbor, or a gateway whose grid gate cannot
    be resolved.

    ``gateway_rule`` is a ``WildernessEntryPoint`` from
    ``world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY`` -- the same
    registration the return exit reads (single source). When ``None`` it is
    resolved by the room's current coordinates; an injected rule only applies
    when its ``wilderness_xy`` matches those coordinates, exactly like the
    return exit's own lookup.
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

    if normalized == "s":
        if gateway_rule is None:
            gateway_rule = next(
                (
                    entry
                    for entry in WILDERNESS_ENTRY_REGISTRY.values()
                    if entry.wilderness_xy == (x, y)
                ),
                None,
            )
        elif gateway_rule.wilderness_xy != (x, y):
            # An injected rule for another coordinate does not apply; the
            # step stays an ordinary wild step, matching at_traverse.
            gateway_rule = None
        if gateway_rule is not None:
            from typeclasses.exits import _grid_room_for_anchor

            grid_room = _grid_room_for_anchor(gateway_rule.anchor_key)
            if grid_room is None:
                # Misconfiguration (gate exit missing or wrong anchor_key):
                # the return exit refuses the step, so the edge is unroutable.
                return None
            try:
                gx, gy, gz = grid_room.xyz
            except Exception:
                return None
            return encode_grid(str(gz), gx, gy)

    neighbor = wilderness_neighbor(x, y, normalized)
    if neighbor is None:
        return None
    nx, ny = neighbor
    return encode_wild(WILDERNESS_NAME, nx, ny)


__all__ = [
    "DIRECTION_DELTAS",
    "normalize_wilderness_direction",
    "resolve_wilderness_destination",
    "wilderness_neighbor",
]
