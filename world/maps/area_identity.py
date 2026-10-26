"""Authoritative, read-only area and instance identity for one room position.

One committed relocation only needs a *complete* presentation refresh when the
actor crossed an authoritative area or instance boundary. That boundary must be
read from the same facts the map owners and the on-demand ``area_map`` presenter
already treat as identity, never from a display label, a room object, or a bare
coordinate:

- grid: the z map key of the grid room (the settlement map the node belongs to),
  so two rooms that share a display name on different maps are different areas;
- wilderness: the registered wilderness map the terrain room belongs to, so a
  pooled ``TerrainRoom`` reused at another cell — or two distinct terrain room
  objects — stay one continuous area;
- coordinate-free interior: the minimum dbref of the room's connected
  same-family component, the same component walk the area map graph uses;
- instance: that connected component together with its authoritative creation
  root and ``scene_identity``, so entering, leaving or replacing an instance is
  a boundary even when every label and archetype is identical.

Every value is a frozen :class:`~world.rules.presentation_events.AlignmentIdentity`
copied at capture time, so a later mutation of a pooled room can never rewrite
the identity of a movement that already captured it. Anything unreadable or
non-comparable returns ``None``; callers treat that conservatively (a complete
alignment instead of a delta).

This module is read-only. It never mutates canonical state and never calls a map
presenter: the identity of a position must be cheap and independent of whether
anyone opened a map.
"""

from typing import Any, Callable, Iterable

from world.observability import log_warn
from world.rules.presentation_events import AlignmentIdentity

__all__ = [
    "AreaGraphOverBound",
    "ROOM_GRAPH_MAX_ROOMS",
    "is_alignment_boundary",
    "read_alignment_identity",
    "room_component",
]

#: Upper bound on the same-family rooms walked to name a room graph. The walk
#: only fixes the graph's stable identity; the emitted (known) set of the map
#: panel is bounded separately by ``AREA_MAX_NODES``.
ROOM_GRAPH_MAX_ROOMS = 4_096

#: ``__in`` list size per query, well under SQLite's bound-variable limit.
_QUERY_CHUNK = 200


class AreaGraphOverBound(Exception):
    """An area graph exceeds its measured finite bound (never truncated)."""


def _chunks(values: list[Any]) -> Iterable[list[Any]]:
    for start in range(0, len(values), _QUERY_CHUNK):
        yield values[start : start + _QUERY_CHUNK]


def _room_exits(room_ids: list[int]) -> list[Any]:
    """Every exit leaving or entering one of ``room_ids`` (chunked queries)."""
    from django.db.models import Q
    from evennia.objects.models import ObjectDB

    exits: dict[int, Any] = {}
    for chunk in _chunks(room_ids):
        query = ObjectDB.objects.filter(
            Q(db_location__in=chunk) | Q(db_destination__in=chunk),
            db_destination__isnull=False,
        )
        for obj in query:
            if getattr(obj, "destination", None) is not None:
                exits[int(obj.id)] = obj
    return [exits[key] for key in sorted(exits)]


def room_component(
    location: Any, same_family: Callable[[Any], bool]
) -> tuple[dict[int, Any], list[Any]]:
    """The same-family rooms connected to ``location`` and every exit seen.

    Exits count in both directions, so one-way passages still join the graph.
    The walk ends at the family boundary and is bounded by
    ``ROOM_GRAPH_MAX_ROOMS``. This is the single component definition shared by
    the ``area_map`` room graph and the alignment identity reader; neither
    module keeps its own copy.
    """
    rooms: dict[int, Any] = {int(location.id): location}
    frontier = [int(location.id)]
    exits: dict[int, Any] = {}
    while frontier:
        found: list[int] = []
        for exit_obj in _room_exits(frontier):
            exits[int(exit_obj.id)] = exit_obj
            for end in (exit_obj.location, exit_obj.destination):
                if end is None or not getattr(end, "id", None):
                    continue
                end_id = int(end.id)
                if end_id in rooms or not same_family(end):
                    continue
                rooms[end_id] = end
                found.append(end_id)
        if len(rooms) > ROOM_GRAPH_MAX_ROOMS:
            log_warn(
                "area_map_over_bound",
                context={
                    "layer": "room_graph",
                    "room": int(location.id),
                    "rooms": len(rooms),
                },
            )
            raise AreaGraphOverBound
        frontier = found
    return rooms, [exits[key] for key in sorted(exits)]


def read_alignment_identity(actor: Any) -> AlignmentIdentity | None:
    """The committed alignment identity of ``actor``'s location, or ``None``.

    ``None`` means "no comparable identity": the actor has no location, the
    position is not a known room layer, or an authoritative fact could not be
    read. Callers must then align completely rather than guess.
    """
    location = getattr(actor, "location", None)
    if location is None:
        return None
    try:
        return _location_identity(location)
    except Exception as error:  # observability: R2 reported below; an unreadable position becomes the conservative alignment choice at the caller
        log_warn(
            "alignment_identity_unavailable",
            context={"room": str(getattr(location, "pk", "?"))},
            exc=error,
        )
        return None


def _location_identity(location: Any) -> AlignmentIdentity | None:
    """Build the identity of one room object (never of a display label)."""
    from typeclasses.rooms import GridRoom, InstanceRoom, Room, TerrainRoom

    if isinstance(location, GridRoom):
        # Only the map key is area identity; coordinates inside one map are not.
        try:
            _x, _y, z = location.xyz
        except Exception:  # observability: ignore R2: an unplaced grid room has no map key, and the caller's conservative alignment is the reported outcome
            return None
        if not isinstance(z, str) or not z:
            return None
        return AlignmentIdentity(layer="grid", area_key=z)
    if isinstance(location, TerrainRoom):
        # The registered wilderness map is the whole continuous area: a pooled
        # room reused at another cell, and two distinct terrain rooms of the
        # same map, are the same identity. Never invent the default map name:
        # a room without a wilderness script is untrustworthy.
        wilderness = location.wilderness
        name = getattr(wilderness, "key", None)
        if not isinstance(name, str) or not name:
            return None
        return AlignmentIdentity(layer="wilderness", area_key=name)
    if isinstance(location, InstanceRoom):
        return _instance_identity(location, InstanceRoom)
    if isinstance(location, Room):
        rooms, _exits = room_component(location, lambda room: isinstance(room, Room))
        return AlignmentIdentity(layer="interior", area_key=f"room:{min(rooms)}")
    return None


def _instance_identity(location: Any, family: type) -> AlignmentIdentity | None:
    """The identity of one instance component, or ``None`` when untrustworthy.

    Connectivity alone is not instance membership: two separately spawned
    instances are distinct contexts even if a passage joins them. The
    authoritative creation fact is the spawn ``origin_room`` every room of one
    instance shares, so a component that mixes origins (or misses one) has no
    comparable identity and aligns conservatively.
    """
    rooms, _exits = room_component(location, lambda room: isinstance(room, family))
    root_id = min(rooms)
    root = rooms[root_id]
    origin = getattr(root, "db", None)
    origin_pk = getattr(getattr(origin, "origin_room", None), "pk", None)
    if origin_pk is None:
        return None
    for room_id, room in rooms.items():
        member_origin = getattr(
            getattr(getattr(room, "db", None), "origin_room", None), "pk", None
        )
        if member_origin != origin_pk:
            return None
    token = getattr(root, "scene_identity", None)
    if not isinstance(token, str) or not token:
        return None
    return AlignmentIdentity(
        layer="instance",
        area_key=f"instance:{root_id}",
        instance_key=(int(root_id), token),
    )


def is_alignment_boundary(
    source: AlignmentIdentity | None, destination: AlignmentIdentity | None
) -> bool:
    """Whether one committed transition needs a complete alignment.

    A comparable pair is a boundary exactly when the authoritative identities
    differ; an unreadable or non-comparable side is conservative and aligns.
    """
    if source is None or destination is None:
        return True
    return source != destination
