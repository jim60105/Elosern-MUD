"""Shared pure node-ID encoder for location nodes.

``node_id_for_location`` is the single canonical derivation of the node ID of
an actor's current location, used by both the ``explore.move`` adapter's
``stale_location`` compare and the move affordance builder so a move card's
``current_node`` is byte-identical to what the adapter re-derives. The module
is pure: it never touches a Session, an actor, or persistent state, and
imports Evennia typeclasses only inside the function body.
"""

from typing import Any

from world.rules.map_knowledge import encode_grid, encode_room, encode_wild


def node_id_for_location(location: Any) -> str | None:
    """Return the canonical node ID of a location, or ``None`` when absent.

    Grid rooms encode through ``encode_grid``, terrain rooms through
    ``encode_wild``, and every other room through ``encode_room``; a missing
    location or unreadable coordinates yield ``None``.
    """
    if location is None:
        return None
    from typeclasses.rooms import GridRoom, TerrainRoom
    from world.maps.wilderness_provider import WILDERNESS_NAME

    if isinstance(location, GridRoom):
        try:
            x, y, z = location.xyz
        except Exception:
            return None
        return encode_grid(str(z), x, y)
    if isinstance(location, TerrainRoom):
        coordinates = location.coordinates
        if coordinates is None:
            return None
        return encode_wild(WILDERNESS_NAME, coordinates[0], coordinates[1])
    return encode_room(int(location.pk))


__all__ = ["node_id_for_location"]
