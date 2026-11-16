"""Resolve a subrace's start room (subrace-start-locations).

The start room is the materialized anchor room of the subrace's start
settlement: start row -> anchor placement -> the placement node's current
coordinate -> the grid room at that coordinate. Every step that does not
resolve raises :class:`StartLocationError`; there is no fallback room.

Imports are function-local so a synthetic registry swap is visible at call
time and a test can patch the single attribute ``resolve_start_room``.
"""

from __future__ import annotations

from typing import Any


class StartLocationError(ValueError):
    """A subrace's start room cannot be resolved."""


def resolve_start_room(subrace_key: str | None) -> Any:
    """Return the materialized anchor room of ``subrace_key``'s start settlement."""

    from elosern_map_core.references import ReferenceError

    from typeclasses.rooms import GridRoom
    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.start_locations import SUBRACE_START_LOCATION_REGISTRY
    from world.maps.static_references import anchor_entrance_xyz

    row = SUBRACE_START_LOCATION_REGISTRY.get(subrace_key) if subrace_key else None
    if row is None:
        raise StartLocationError(f"subrace {subrace_key!r} has no start location")
    placement = ANCHOR_PLACEMENT_REGISTRY.get(row.anchor_key)
    if placement is None:
        raise StartLocationError(
            f"start settlement {row.anchor_key!r} has no map placement"
        )
    try:
        xyz = anchor_entrance_xyz(placement)
    except ReferenceError as error:
        raise StartLocationError(
            f"start settlement {row.anchor_key!r} does not resolve"
        ) from error
    room = GridRoom.objects.filter_xyz(xyz=xyz).first()
    if room is None:
        raise StartLocationError(f"start room of {row.anchor_key!r} is not built")
    return room


__all__ = ["StartLocationError", "resolve_start_room"]
