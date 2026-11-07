"""Stable physical-edge identity, discovery, quoting, and player history.

One movement owner for the last completed physical edge. A wilderness cell is
named by its registered map and integer coordinates, never by the pooled
``TerrainRoom`` object that happens to render it; a persistent authored room is
named by its durable dbref. The same read-only discovery prices an edge through
the canonical execution arithmetic (``resolve_traversal_cost``), so later
escape and retreat code never grows a second legality calculator.

The public surface is deliberately small:

``location_ref``
    A stable locator for an entity's logical position.
``legal_edges``
    The adjacent edges execution would currently consider from ``source``.
``quote_edge``
    The canonical ``TraversalResolution`` for one edge, optionally priced from
    detached projected physiology.
``read_previous_edge`` / ``record_completed_edge`` / ``invalidate_previous_edge``
    The persisted history contract (``db.previous_traversal``).

Discovery and quoting never create rooms, advance the clock, tick gauges or
write attributes. Routing-only weights are never used here.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import json
import re
from typing import Any, Mapping, Sequence

from world.maps.wilderness_provider import WILDERNESS_NAME
from world.observability import log_info, log_warn
from world.rules.presentation_events import on_publication_commit
from world.rules.travel_cost import (
    TraversalResolution,
    TraversalStatus,
    resolve_traversal_cost,
)

#: The persisted attribute owning one body's last completed physical edge.
PREVIOUS_TRAVERSAL_ATTRIBUTE = "previous_traversal"

#: Stable tag discriminating the two locator shapes.
KIND_WILDERNESS = "wilderness"
KIND_ROOM = "room"

_DIRECTION_ROUTE = re.compile(r"^direction:(n|ne|e|se|s|sw|w|nw)$")
_EXIT_ROUTE = re.compile(r"^exit:([1-9][0-9]*)$")


class MovementEdgeError(ValueError):
    """A locator, edge, or history record violates the stable contract."""


class LocationRefError(MovementEdgeError):
    """An entity's position cannot be represented as a stable locator."""


class MovementHistoryError(MovementEdgeError):
    """A stored previous-traversal record is malformed or inconsistent."""


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True, slots=True)
class LocationRef:
    """One stable physical location: a wilderness cell or an authored room.

    The representation is a tagged value, never a live room reference. Use
    :meth:`wilderness` / :meth:`room`; the strict JSON shape is produced by
    :func:`encode_location_ref`.
    """

    kind: str
    map: str | None = None
    x: int | None = None
    y: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.kind == KIND_WILDERNESS:
            if not isinstance(self.map, str) or not self.map:
                raise MovementEdgeError("a wilderness locator needs a map name")
            if not _is_int(self.x) or not _is_int(self.y):
                raise MovementEdgeError("wilderness coordinates must be integers")
            if self.x < 0 or self.y < 0:
                raise MovementEdgeError("wilderness coordinates must be non-negative")
            if self.id is not None:
                raise MovementEdgeError("a wilderness locator carries no room id")
            return
        if self.kind == KIND_ROOM:
            if not _is_int(self.id) or self.id <= 0:
                raise MovementEdgeError("a room locator needs a positive integer id")
            if self.map is not None or self.x is not None or self.y is not None:
                raise MovementEdgeError("a room locator carries no map or coordinates")
            return
        raise MovementEdgeError(f"unknown locator kind {self.kind!r}")

    @classmethod
    def wilderness(cls, map_name: str, x: int, y: int) -> "LocationRef":
        return cls(kind=KIND_WILDERNESS, map=map_name, x=x, y=y)

    @classmethod
    def room(cls, dbref: int) -> "LocationRef":
        return cls(kind=KIND_ROOM, id=dbref)


@dataclass(frozen=True, slots=True)
class PhysicalEdge:
    """One traversable physical edge in stable locator terms.

    ``route`` is ``direction:<normalized direction>`` for a departure whose
    source is a wilderness cell and ``exit:<positive dbref>`` for an authored
    Exit. A gate remains its actual registered crossing: adjacency never
    invents a wall entrance.
    """

    source: LocationRef
    destination: LocationRef
    route: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, LocationRef) or not isinstance(
            self.destination, LocationRef
        ):
            raise MovementEdgeError("an edge connects two LocationRef values")
        if not isinstance(self.route, str):
            raise MovementEdgeError("an edge route must be a string")
        direction = _DIRECTION_ROUTE.fullmatch(self.route)
        exit_match = _EXIT_ROUTE.fullmatch(self.route)
        if direction is not None:
            if self.source.kind != KIND_WILDERNESS:
                raise MovementEdgeError(
                    "a direction route belongs to a wilderness source"
                )
            return
        if exit_match is not None:
            if self.source.kind != KIND_ROOM:
                raise MovementEdgeError("an exit route belongs to a room source")
            return
        raise MovementEdgeError(f"unknown edge route {self.route!r}")


def encode_location_ref(ref: LocationRef) -> dict[str, Any]:
    """Return the exact tagged mapping for one locator."""
    if not isinstance(ref, LocationRef):
        raise MovementEdgeError("expected a LocationRef")
    if ref.kind == KIND_WILDERNESS:
        return {"kind": KIND_WILDERNESS, "map": ref.map, "x": ref.x, "y": ref.y}
    return {"kind": KIND_ROOM, "id": ref.id}


def decode_location_ref(data: Any) -> LocationRef:
    """Parse one exact tagged locator mapping; reject every other shape."""
    if not isinstance(data, Mapping):
        raise MovementEdgeError("a locator must be a mapping")
    keys = set(data)
    kind = data.get("kind")
    if kind == KIND_WILDERNESS:
        if keys != {"kind", "map", "x", "y"}:
            raise MovementEdgeError("a wilderness locator has exactly four keys")
        return LocationRef.wilderness(data["map"], data["x"], data["y"])
    if kind == KIND_ROOM:
        if keys != {"kind", "id"}:
            raise MovementEdgeError("a room locator has exactly two keys")
        return LocationRef.room(data["id"])
    raise MovementEdgeError(f"unknown locator kind {kind!r}")


def encode_physical_edge(edge: PhysicalEdge) -> dict[str, Any]:
    """Return the exact JSON shape of one physical edge."""
    if not isinstance(edge, PhysicalEdge):
        raise MovementEdgeError("expected a PhysicalEdge")
    return {
        "source": encode_location_ref(edge.source),
        "destination": encode_location_ref(edge.destination),
        "route": edge.route,
    }


def decode_physical_edge(data: Any) -> PhysicalEdge:
    """Parse one exact physical-edge mapping; reject every other shape."""
    if not isinstance(data, Mapping):
        raise MovementEdgeError("an edge must be a mapping")
    if set(data) != {"source", "destination", "route"}:
        raise MovementEdgeError("an edge has exactly source, destination and route")
    return PhysicalEdge(
        source=decode_location_ref(data["source"]),
        destination=decode_location_ref(data["destination"]),
        route=data["route"],
    )


# ---------------------------------------------------------------------------
# Locator adapters


class _WildernessCell:
    """A locator-backed terrain cell ``resolve_traversal_cost`` can price.

    This is a read-only adapter, not an Evennia room: it never creates or
    mutates a pooled ``TerrainRoom``. ``movement_layer`` is the marker
    ``travel_cost`` reads to classify an unmaterialized wilderness endpoint.
    """

    __slots__ = ("coordinates", "movement_layer")

    def __init__(self, coordinates: tuple[int, int]) -> None:
        self.coordinates = coordinates
        self.movement_layer = KIND_WILDERNESS


def _coordinate_pair(value: Any) -> tuple[int, int] | None:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or not _is_int(value[0])
        or not _is_int(value[1])
    ):
        return None
    return (value[0], value[1])


def _registered_coordinates(entity: Any) -> tuple[int, int] | None:
    """A pooled body's live wilderness registration, without materializing."""
    try:
        ndb = getattr(entity, "ndb", None)
        script = getattr(ndb, "wilderness", None)
        itemcoordinates = getattr(script, "itemcoordinates", None)
        if isinstance(itemcoordinates, Mapping):
            return _coordinate_pair(itemcoordinates.get(entity))
    except Exception:  # observability: ignore R2: an absent registration is the documented "no stable locator" outcome
        return None
    return None


def _is_room_object(entity: Any) -> bool:
    from typeclasses.rooms import GridRoom, Room, TerrainRoom

    return isinstance(entity, (GridRoom, Room, TerrainRoom))


def _ref_for_location(location: Any) -> LocationRef | None:
    """The stable locator of one room object, or ``None`` when unrepresentable."""
    from typeclasses.rooms import GridRoom, Room, TerrainRoom

    if isinstance(location, TerrainRoom):
        coordinates = _coordinate_pair(getattr(location, "coordinates", None))
        if coordinates is None:
            return None
        return LocationRef.wilderness(WILDERNESS_NAME, *coordinates)
    if isinstance(location, (GridRoom, Room)):
        # A pooled TerrainRoom is excluded above; every other Room family is a
        # persistent authored interior or grid node. Instance rooms are
        # ephemeral, so they are deliberately absent from this predicate.
        room_id = getattr(location, "id", None)
        if not _is_int(room_id) or room_id <= 0:
            return None
        return LocationRef.room(room_id)
    return None


def location_ref(entity: Any) -> LocationRef:
    """Return the stable locator of ``entity``'s logical position.

    Accepts a room object directly or any body whose ``location`` (or live
    wilderness registration) names the position. Raises
    :class:`LocationRefError` when no stable locator exists.
    """
    if _is_room_object(entity):
        ref = _ref_for_location(entity)
        if ref is not None:
            return ref
        raise LocationRefError(f"{entity!r} has no stable locator")
    location = getattr(entity, "location", None)
    if location is not None:
        ref = _ref_for_location(location)
        if ref is not None:
            return ref
        raise LocationRefError(f"{entity!r} stands in an unrepresentable location")
    coordinates = _registered_coordinates(entity)
    if coordinates is not None:
        return LocationRef.wilderness(WILDERNESS_NAME, *coordinates)
    raise LocationRefError(f"{entity!r} has no stable position")


def _current_ref_or_none(entity: Any) -> LocationRef | None:
    try:
        return location_ref(entity)
    except (LocationRefError, MovementEdgeError):  # observability: ignore R2: an unrepresentable position is the documented "no usable history" outcome, not a failure
        return None


def _load_authored_room(dbref: int) -> Any | None:
    from evennia.objects.models import ObjectDB
    from typeclasses.rooms import GridRoom, Room, TerrainRoom

    room = ObjectDB.objects.filter(id=int(dbref)).first()
    if room is None or isinstance(room, TerrainRoom):
        return None
    if not isinstance(room, (GridRoom, Room)):
        return None
    return room


def room_for_ref(ref: LocationRef) -> Any | None:
    """Resolve a room locator to its live persistent authored room, if any."""
    if not isinstance(ref, LocationRef) or ref.kind != KIND_ROOM:
        return None
    return _load_authored_room(ref.id)


def _load_exit(dbref: int) -> Any | None:
    from evennia.objects.models import ObjectDB
    from typeclasses.exits import MovementCostMixin

    exit_obj = ObjectDB.objects.filter(id=int(dbref)).first()
    if exit_obj is None or not isinstance(exit_obj, MovementCostMixin):
        return None
    return exit_obj


def _authored_room_ref(room: Any) -> LocationRef | None:
    from typeclasses.rooms import GridRoom, Room, TerrainRoom

    if isinstance(room, TerrainRoom) or not isinstance(room, (GridRoom, Room)):
        return None
    room_id = getattr(room, "id", None)
    if not _is_int(room_id) or room_id <= 0:
        return None
    return LocationRef.room(room_id)


def _gate_landing(exit_obj: Any) -> tuple[int, int] | None:
    """The registered wilderness landing cell of a ``WildernessGateExit``."""
    from world.lore import wilderness_entry as wilderness_entry_module

    entry = wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY.get(
        getattr(getattr(exit_obj, "db", None), "anchor_key", None)
    )
    if entry is None:
        return None
    gate = entry.gate_for(getattr(getattr(exit_obj, "db", None), "gate_direction", None))
    if gate is None:
        return None
    return _coordinate_pair(entry.approach_cell(gate))


def _arrival_refused(actor: Any, destination: Any) -> bool:
    """Whether the destination's read-only receive policy refuses ``actor``.

    Most rooms accept every arrival. ``LimboRoom`` owns the one authored
    hard-gate policy, exposed as a pure predicate so discovery can consult it
    without sending messages or writing its refusal marker.
    """
    from typeclasses.rooms import LimboRoom

    if isinstance(destination, LimboRoom):
        return bool(destination.refuses_arrival(actor))
    return False


def _materialized_room(source: LocationRef) -> Any | None:
    """The wilderness room currently materialized at ``source``, if any."""
    from evennia.utils.search import search_script

    script = search_script(WILDERNESS_NAME)
    if not script:
        return None
    return (script[0].db.rooms or {}).get((source.x, source.y))


def _direction_admits(actor: Any, room: Any | None, direction: str) -> bool:
    """Whether the materialized wilderness direction exit admits ``actor``.

    A recycled/unmaterialized cell has no exit object to consult, so topology
    remains the authority there. When the cell is materialized, its real
    ``WildernessReturnExit`` traverse lock is checked read-only.
    """
    from world.maps.wilderness_destination import normalize_wilderness_direction

    normalized = normalize_wilderness_direction(direction)
    if normalized is None:
        return False
    if room is None:
        return True
    for exit_obj in room.exits:
        if normalize_wilderness_direction(getattr(exit_obj, "key", None)) != normalized:
            continue
        try:
            return bool(exit_obj.access(actor, "traverse"))
        except Exception as error:  # observability: R1 reported below; a broken lock refuses the edge
            log_warn(
                "movement_edge_access_failed",
                exc=error,
                context={
                    "exit": getattr(exit_obj, "dbref", None),
                    "direction": normalized,
                },
            )
            return False
    return True


# ---------------------------------------------------------------------------
# Discovery


def resolve_direction_edge(
    source: LocationRef, coordinates: tuple[int, int], direction: str
) -> PhysicalEdge | None:
    """The one legal edge execution takes for ``direction`` at a wilderness cell.

    A registered gateway resolves to its authored grid room; every other
    direction uses the provider-valid neighbouring cell (including the corner
    restriction). Returns ``None`` when execution would refuse the step.
    """
    from world.maps.wilderness_destination import (
        find_gateway,
        grid_room_for_gate,
        normalize_wilderness_direction,
        wilderness_neighbor,
    )

    if source.kind != KIND_WILDERNESS:
        return None
    normalized = normalize_wilderness_direction(direction)
    if normalized is None:
        return None
    cell = _coordinate_pair(coordinates)
    if cell is None:
        return None
    hit = find_gateway(cell, normalized)
    if hit is not None:
        _, gate = hit
        grid_room = grid_room_for_gate(gate)
        if grid_room is None:
            return None
        destination = _authored_room_ref(grid_room)
        if destination is None:
            return None
        return PhysicalEdge(
            source=source,
            destination=destination,
            route=f"direction:{normalized}",
        )
    neighbor = wilderness_neighbor(cell[0], cell[1], normalized)
    if neighbor is None:
        return None
    return PhysicalEdge(
        source=source,
        destination=LocationRef.wilderness(WILDERNESS_NAME, *neighbor),
        route=f"direction:{normalized}",
    )


def resolve_exit_edge(actor: Any, exit_obj: Any) -> PhysicalEdge | None:
    """The one legal edge an authored Exit currently offers, or ``None``.

    Consults the real Exit's traverse access and its current destination; a
    ``WildernessGateExit`` names its registered wilderness cell instead of a
    room destination.
    """
    from typeclasses.exits import (
        MovementCostMixin,
        WildernessGateExit,
        WildernessReturnExit,
    )

    if not isinstance(exit_obj, MovementCostMixin) or isinstance(
        exit_obj, WildernessReturnExit
    ):
        return None
    source = _authored_room_ref(getattr(exit_obj, "location", None))
    if source is None:
        return None
    try:
        admitted = bool(exit_obj.access(actor, "traverse"))
    except Exception as error:  # observability: R1 reported below; a broken access check refuses the edge
        log_warn(
            "movement_edge_access_failed",
            exc=error,
            context={"exit": getattr(exit_obj, "dbref", None)},
        )
        return None
    if not admitted:
        return None
    exit_id = getattr(exit_obj, "id", None)
    if not _is_int(exit_id) or exit_id <= 0:
        return None
    if isinstance(exit_obj, WildernessGateExit):
        landing = _gate_landing(exit_obj)
        if landing is None:
            return None
        return PhysicalEdge(
            source=source,
            destination=LocationRef.wilderness(WILDERNESS_NAME, *landing),
            route=f"exit:{exit_id}",
        )
    destination = _authored_room_ref(getattr(exit_obj, "destination", None))
    if destination is None:
        return None
    if _arrival_refused(actor, exit_obj.destination):
        return None
    return PhysicalEdge(source=source, destination=destination, route=f"exit:{exit_id}")


def _edge_sort_key(edge: PhysicalEdge) -> str:
    return json.dumps(encode_physical_edge(edge), sort_keys=True, separators=(",", ":"))


def legal_edges(
    actor: Any, source: LocationRef, members: tuple[Any, ...]
) -> tuple[PhysicalEdge, ...]:
    """Every adjacent edge execution would currently consider from ``source``.

    Wilderness sources enumerate the eight canonical directions through the
    shared gateway/neighbour rule; authored-room sources enumerate the room's
    real exits through their traverse access. ``members`` is part of the
    contract for callers that price candidates next; discovery itself is
    read-only and does not price, create rooms, or write any surface.
    """
    if not isinstance(source, LocationRef):
        raise MovementEdgeError("legal_edges needs a LocationRef source")
    edges: list[PhysicalEdge] = []
    if source.kind == KIND_WILDERNESS:
        from world.rules.travel_plan import DIRECTION_ORDER

        cell = _coordinate_pair((source.x, source.y))
        if cell is None:
            return ()
        room = _materialized_room(source)
        for direction in DIRECTION_ORDER:
            if not _direction_admits(actor, room, direction):
                continue
            edge = resolve_direction_edge(source, cell, direction)
            if edge is not None:
                edges.append(edge)
    else:
        room = _load_authored_room(source.id)
        if room is None:
            return ()
        for exit_obj in room.exits:
            edge = resolve_exit_edge(actor, exit_obj)
            if edge is not None:
                edges.append(edge)
    return tuple(sorted(edges, key=_edge_sort_key))


# ---------------------------------------------------------------------------
# Quoting


def _resolution(
    actor: Any,
    cost_key: str,
    *,
    status: TraversalStatus,
    cost: Any,
    members: Sequence[Any],
    source: LocationRef,
) -> TraversalResolution:
    return TraversalResolution(
        status=status,
        cost=cost,
        members=tuple(members),
        traverser_id=getattr(actor, "id", None),
        cost_key=cost_key,
        source_location_id=_room_id(source),
    )


def _room_id(source: LocationRef) -> int | None:
    return source.id if source.kind == KIND_ROOM else None


def _exit_key(route: str) -> int:
    match = _EXIT_ROUTE.fullmatch(route)
    if match is None:
        raise MovementEdgeError(f"not an exit route: {route!r}")
    return int(match.group(1))


def _direction_quote(
    actor: Any, edge: PhysicalEdge, travellers: Sequence[Any]
) -> TraversalResolution:
    from world.maps.wilderness_destination import normalize_wilderness_direction

    match = _DIRECTION_ROUTE.fullmatch(edge.route)
    if match is None:
        return _resolution(
            actor, "wilderness_move", status=TraversalStatus.UNRESOLVED,
            cost=None, members=travellers, source=edge.source,
        )
    direction = match.group(1)
    if edge.source.kind != KIND_WILDERNESS:
        return _resolution(
            actor, "wilderness_move", status=TraversalStatus.UNRESOLVED,
            cost=None, members=travellers, source=edge.source,
        )
    if not _direction_admits(actor, _materialized_room(edge.source), direction):
        return _resolution(
            actor, "wilderness_move", status=TraversalStatus.UNRESOLVED,
            cost=None, members=travellers, source=edge.source,
        )
    cell = _coordinate_pair((edge.source.x, edge.source.y))
    if cell is None:
        return _resolution(
            actor, "wilderness_move", status=TraversalStatus.UNRESOLVED,
            cost=None, members=travellers, source=edge.source,
        )
    current = resolve_direction_edge(edge.source, cell, direction)
    if current is None or current.destination != edge.destination:
        return _resolution(
            actor, "wilderness_move", status=TraversalStatus.UNRESOLVED,
            cost=None, members=travellers, source=edge.source,
        )
    source_cell = _WildernessCell(cell)
    if edge.destination.kind == KIND_WILDERNESS:
        destination = _WildernessCell((edge.destination.x, edge.destination.y))
        return resolve_traversal_cost(
            actor,
            "wilderness_move",
            source_location=source_cell,
            destination=destination,
            wilderness_source_coordinates=cell,
            wilderness_destination_coordinates=(edge.destination.x, edge.destination.y),
            members=travellers,
        )
    grid_room = _load_authored_room(edge.destination.id)
    if grid_room is None:
        return _resolution(
            actor, "wilderness_move", status=TraversalStatus.UNRESOLVED,
            cost=None, members=travellers, source=edge.source,
        )
    return resolve_traversal_cost(
        actor,
        "wilderness_move",
        source_location=source_cell,
        destination=grid_room,
        members=travellers,
    )


def _exit_quote(
    actor: Any, edge: PhysicalEdge, travellers: Sequence[Any]
) -> TraversalResolution:
    from typeclasses.exits import WildernessGateExit

    cost_key = "move"
    exit_obj = _load_exit(_exit_key(edge.route))
    if exit_obj is None:
        return _resolution(
            actor, cost_key, status=TraversalStatus.UNRESOLVED,
            cost=None, members=travellers, source=edge.source,
        )
    try:
        admitted = bool(exit_obj.access(actor, "traverse"))
    except Exception as error:  # observability: R1 reported below; a broken access check refuses the edge
        log_warn(
            "movement_edge_access_failed",
            exc=error,
            context={"exit": getattr(exit_obj, "dbref", None)},
        )
        admitted = False
    source_room = _load_authored_room(edge.source.id)
    if (
        not admitted
        or source_room is None
        or getattr(exit_obj, "location", None) is not source_room
    ):
        return _resolution(
            actor, cost_key, status=TraversalStatus.UNRESOLVED,
            cost=None, members=travellers, source=edge.source,
        )
    cost_key = (
        "wilderness_move"
        if isinstance(exit_obj, WildernessGateExit)
        else getattr(exit_obj, "movement_cost_key", cost_key)
    )
    if isinstance(exit_obj, WildernessGateExit):
        landing = _gate_landing(exit_obj)
        if landing is None or edge.destination.kind != KIND_WILDERNESS:
            return _resolution(
                actor, cost_key, status=TraversalStatus.UNRESOLVED,
                cost=None, members=travellers, source=edge.source,
            )
        if (edge.destination.x, edge.destination.y) != landing:
            return _resolution(
                actor, cost_key, status=TraversalStatus.UNRESOLVED,
                cost=None, members=travellers, source=edge.source,
            )
        return resolve_traversal_cost(
            actor,
            cost_key,
            source_location=source_room,
            wilderness_destination_coordinates=landing,
            members=travellers,
        )
    destination_room = _load_authored_room(
        edge.destination.id if edge.destination.kind == KIND_ROOM else 0
    )
    if destination_room is None or getattr(exit_obj, "destination", None) is not destination_room:
        return _resolution(
            actor, cost_key, status=TraversalStatus.UNRESOLVED,
            cost=None, members=travellers, source=edge.source,
        )
    if _arrival_refused(actor, destination_room):
        return _resolution(
            actor, cost_key, status=TraversalStatus.UNRESOLVED,
            cost=None, members=travellers, source=edge.source,
        )
    return resolve_traversal_cost(
        actor,
        cost_key,
        source_location=source_room,
        destination=destination_room,
        members=travellers,
    )


def quote_edge(
    actor: Any,
    edge: PhysicalEdge,
    members: tuple[Any, ...],
    *,
    states: Sequence[Any] | None = None,
) -> TraversalResolution:
    """Price one edge with the canonical execution arithmetic.

    ``states`` (``TravellerState`` values) prices projected physiology instead
    of the live bodies; each state implements ``detached()``. The call is
    read-only: no room is created, no clock ticks, no attribute is written. A
    stale edge (a changed destination, a locked exit, a vanished room) is
    ``UNRESOLVED``; a legitimate refusal (sleeping party, pre-destination
    depletion) raises ``MovementPreflightRefused`` exactly as execution does.
    """
    if not isinstance(edge, PhysicalEdge):
        raise MovementEdgeError("quote_edge needs a PhysicalEdge")
    travellers: tuple[Any, ...]
    if states is not None:
        travellers = tuple(state.detached() for state in states)
    else:
        travellers = tuple(members)
    # A named topology or physiology error propagates; only ordinary blocked
    # edges are represented as ``UNRESOLVED``. Never disguise corrupt state or
    # broken authored geometry as an unpriceable candidate.
    if edge.route.startswith("direction:"):
        resolution = _direction_quote(actor, edge, travellers)
    else:
        resolution = _exit_quote(actor, edge, travellers)
    if resolution.cost is None or resolution.cost_key is None:
        return resolution
    from world.rules.travel_cost import flight_waives_wilderness_charge

    # Quote the canonical committed duration: an authorized flight waiver is
    # the same zero the clock charge applies, never a positive physical price.
    if flight_waives_wilderness_charge(actor, resolution.cost_key):
        return replace(resolution, cost=replace(resolution.cost, seconds=0))
    return resolution


# ---------------------------------------------------------------------------
# Persisted history


def read_previous_edge(body: Any) -> PhysicalEdge | None:
    """Return ``body``'s last completed edge, or ``None``.

    Absent history is ``None``. A malformed record raises
    :class:`MovementHistoryError` (never silently resets). A record whose
    destination no longer matches the body's current logical position is
    ``None``: it is not a usable retreat from here.
    """
    attributes = getattr(body, "attributes", None)
    if attributes is None or not attributes.has(PREVIOUS_TRAVERSAL_ATTRIBUTE):
        return None
    payload = attributes.get(PREVIOUS_TRAVERSAL_ATTRIBUTE)
    if payload is None:
        raise MovementHistoryError("the retained traversal record is null")
    try:
        edge = decode_physical_edge(payload)
    except MovementEdgeError as error:
        raise MovementHistoryError(str(error)) from error
    current = _current_ref_or_none(body)
    if current is None or current != edge.destination:
        return None
    return edge


def _observer_context(body: Any, **extra: Any) -> dict[str, Any]:
    from world.rules.party_scope import resolve_commander

    try:
        commander = resolve_commander(body)
    except Exception:  # observability: ignore R2: an unbound/possessed body has no commander; the event still names the body
        commander = None
    context: dict[str, Any] = {
        "body": getattr(body, "dbref", None),
        "commander": getattr(commander if commander is not None else body, "dbref", None),
    }
    context.update(extra)
    return context


def record_completed_edge(body: Any, edge: PhysicalEdge) -> None:
    """Persist one completed physical edge on ``body``.

    Only the movement owner calls this, after the whole edge, its costs and
    following all succeeded. The success event is deferred to the surrounding
    transaction's commit, so a rolled-back settlement emits nothing.
    """
    if not isinstance(edge, PhysicalEdge):
        raise MovementEdgeError("record_completed_edge needs a PhysicalEdge")
    attributes = getattr(body, "attributes", None)
    if attributes is None:
        raise MovementEdgeError("a traversing body must expose attributes")
    attributes.add(PREVIOUS_TRAVERSAL_ATTRIBUTE, encode_physical_edge(edge))
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    context = _observer_context(
        body,
        source=edge.source,
        destination=edge.destination,
        route=edge.route,
        tick=None if clock is None else int(clock.tick),
    )
    on_publication_commit(lambda: log_info("movement_edge_completed", context=context))


def invalidate_previous_edge(body: Any) -> None:
    """Forget ``body``'s previous edge; an absent record is a no-op.

    Emits ``movement_history_invalidated`` only when a stored edge was
    actually removed, deferred until the surrounding transaction commits.
    """
    attributes = getattr(body, "attributes", None)
    if attributes is None:
        return
    if not attributes.has(PREVIOUS_TRAVERSAL_ATTRIBUTE):
        return
    removed = None
    try:
        removed = decode_physical_edge(attributes.get(PREVIOUS_TRAVERSAL_ATTRIBUTE))
    except MovementEdgeError:  # observability: ignore R2: the invalidation still removes a malformed record; its provenance is simply unavailable
        removed = None
    attributes.remove(PREVIOUS_TRAVERSAL_ATTRIBUTE)
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    extra: dict[str, Any] = {
        "tick": None if clock is None else int(clock.tick),
    }
    if removed is not None:
        extra.update(
            source=removed.source,
            destination=removed.destination,
            route=removed.route,
        )
    context = _observer_context(body, **extra)
    on_publication_commit(
        lambda: log_info("movement_history_invalidated", context=context)
    )


__all__ = [
    "KIND_ROOM",
    "KIND_WILDERNESS",
    "LocationRef",
    "LocationRefError",
    "MovementEdgeError",
    "MovementHistoryError",
    "PREVIOUS_TRAVERSAL_ATTRIBUTE",
    "PhysicalEdge",
    "decode_location_ref",
    "decode_physical_edge",
    "encode_location_ref",
    "encode_physical_edge",
    "legal_edges",
    "location_ref",
    "quote_edge",
    "read_previous_edge",
    "record_completed_edge",
    "resolve_direction_edge",
    "resolve_exit_edge",
    "room_for_ref",
    "invalidate_previous_edge",
]
