"""Distance-bearing travel cost: terrain speed, geometry and one upward round.

``world-map-scale`` design §10: a movement command traverses one authored edge
between named locations. Duration is the edge's physical geometry (Euclidean
straight length or the full authored meter polyline) divided by the slowest
eligible source-present traveller's sustainable speed for the edge's terrain,
rounded upward once for the whole committed traversal. This module is the single
calculation authority:

- the terrain speed table and the wilderness region→terrain table live in
  ``rulebook/movement.yaml`` (authored integer meters per hour, never seconds);
- settlement edge lengths come from ``world.maps.sparse_graph``'s physical node
  positions, wilderness distances from the provider's declared cell span, and
  gate approaches from the settlement anchor transform plus authored approach
  cells (``world.maps.wilderness_destination``);
- the per-member sustainable speed is the terrain speed scaled by the member's
  exact outgoing fatigue scale (``world.rules.fatigue``). A wholly absent
  mental-reserve state is a not-yet-initialized body and travels at its base
  speed; a corrupt state or a posture that forbids travel refuses the
  traversal at preflight instead of being priced as healthy.

Only ``seconds`` is an authority. ``clock.yaml``'s ``command_defaults`` remain
the explicit durations for non-distance connectors (a Limbo bridge, an
instance-room doorway, a plain room pair); a distance-bearing outdoor lineage
either resolves here or is refused before any write. ``wilderness_move`` is
retained as the distinct wilderness flight-waiver context key only and is never
a seconds authority.

The preflight boundary is the :func:`preflight_movement_cost` context manager:
every exit lineage resolves one immutable :class:`TraversalCost` before
relocation and ``charge_movement`` consumes exactly that record through
:func:`consume_preflight_resolution` without changing its public signature.
Direct ``charge_movement`` calls outside an exit fall back to a live resolution
from the caller's source location and the traverser's current location.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from math import ceil, hypot
from pathlib import Path
from typing import Any

import yaml

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.maps import map_data
from world.maps.wilderness_provider import (
    WILDERNESS_KM_PER_CELL,
    WILDERNESS_NAME,
    region_for_coordinates,
)
from world.observability import log_warn
from world.rules.fatigue import (
    POSTURE_ATTRIBUTE,
    RESERVE_ATTRIBUTE,
    FatigueStateError,
    SleepPosture,
    outgoing_foot_speed_scale,
    read_fatigue_state,
    read_optional_fatigue_state,
)

RULEBOOK_PATH = Path(__file__).parent / "rulebook" / "movement.yaml"

TRAVEL_YAML = yaml.safe_load(RULEBOOK_PATH.read_text(encoding="utf-8"))

#: Terrain contexts every distance-bearing edge resolves to. Settlement roads
#: and good wilderness road share the design's 1.25 m/s calibration.
TERRAIN_SPEEDS: Mapping[str, int] = dict(TRAVEL_YAML["terrain_meters_per_hour"])
WILDERNESS_TERRAIN: Mapping[str, str] = dict(TRAVEL_YAML["wilderness_terrain"])


class TravelRulebookError(ValueError):
    """The movement rulebook violates the terrain/speed contract."""


class MovementPreflightRefused(ValueError):
    """A preflight found an ineligible traveller or an unpriceable outdoor edge."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class TraversalStatus(StrEnum):
    """How one movement call classifies against the distance-bearing contract."""

    #: A physical outdoor edge resolved to an exact duration.
    RESOLVED = "resolved"
    #: An explicit non-distance connector: its authored clock default applies.
    NON_DISTANCE = "non_distance"
    #: An outdoor lineage whose authored geometry could not be resolved.
    UNRESOLVED = "unresolved"


SLEEPING_PARTY_MESSAGE = "同行成員正在沉睡，無法移動。"


def refuse_sleeping_party(members: Sequence[Any]) -> None:
    """Refuse any travel whose source-present party includes a forced sleeper.

    The intended source-present follow scope is the same set the charge and
    the follow step use, so an awake possessed member can neither carry nor
    teleport a sleeping body. The refusal happens at preflight, before cost
    resolution, waiver, relocation, time or location changes.
    """
    for member in members:
        state = read_optional_fatigue_state(member)
        if state is not None and state.posture is SleepPosture.FORCED:
            raise MovementPreflightRefused("party_sleeping", SLEEPING_PARTY_MESSAGE)


def _validate_rulebook() -> None:
    if not isinstance(TERRAIN_SPEEDS, Mapping) or not TERRAIN_SPEEDS:
        raise TravelRulebookError("movement.yaml: terrain_meters_per_hour must be a mapping")
    for terrain, speed in TERRAIN_SPEEDS.items():
        if not isinstance(terrain, str) or not terrain:
            raise TravelRulebookError("movement.yaml: terrain names must be non-empty strings")
        if isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0:
            raise TravelRulebookError(
                f"movement.yaml: terrain {terrain!r} speed must be a positive integer"
            )
    if not isinstance(WILDERNESS_TERRAIN, Mapping) or not WILDERNESS_TERRAIN:
        raise TravelRulebookError("movement.yaml: wilderness_terrain must be a mapping")
    for region, terrain in WILDERNESS_TERRAIN.items():
        if terrain not in TERRAIN_SPEEDS:
            raise TravelRulebookError(
                f"movement.yaml: wilderness region {region!r} names unknown terrain {terrain!r}"
            )
    # The live region model is the key source: a new region without a declared
    # terrain would otherwise silently fall back to a default speed.
    from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY

    missing = sorted(set(WILDERNESS_REGION_REGISTRY) - set(WILDERNESS_TERRAIN))
    if missing:
        raise TravelRulebookError(
            f"movement.yaml: wilderness regions without a terrain row: {missing}"
        )


_validate_rulebook()


@dataclass(frozen=True, slots=True)
class TraversalCost:
    """One immutable preflight record: geometry, terrain, travellers and time."""

    distance_m: float
    terrain: str
    seconds: int
    members: tuple[Any, ...]


@dataclass(frozen=True, slots=True)
class TraversalResolution:
    """The classification of one movement call plus its preflight record."""

    status: TraversalStatus
    cost: TraversalCost | None
    members: tuple[Any, ...] = ()
    traverser_id: int | None = None
    cost_key: str | None = None
    source_location_id: int | None = None


#: The active preflight stack. Movement is synchronous, so a context variable
#: is enough; a nested traversal (a hook starting another move) gets its own
#: innermost record and the outer record is restored on exit.
_ACTIVE_RESOLUTIONS: ContextVar[tuple[TraversalResolution, ...]] = ContextVar(
    "movement_preflight_resolutions", default=()
)


def terrain_speed_m_per_hour(terrain: str) -> int:
    """Return the authored integer meters-per-hour speed for ``terrain``."""

    try:
        return TERRAIN_SPEEDS[terrain]
    except KeyError as error:
        raise TravelRulebookError(f"unknown travel terrain {terrain!r}") from error


def traversal_seconds(
    leg_lengths_m: Iterable[float], speed_m_per_hour: Fraction | int
) -> int:
    """Return one committed traversal's duration, rounded upward exactly once.

    Each polyline leg is measured in meters and divided by the party's exact
    speed; the legs are summed as exact fractions before the single ceiling, so
    two 0.4-second legs commit 1 second, never 2. Per-meter rounding is
    therefore impossible by construction.
    """

    speed = Fraction(speed_m_per_hour)
    if speed <= 0:
        raise TravelRulebookError("travel speed must be positive")
    total = sum(
        (Fraction(length) * 3600 / speed for length in leg_lengths_m),
        Fraction(0),
    )
    return ceil(total)


def _fatigue_scale(member: Any) -> Fraction:
    """Return a present member's outgoing foot-speed scale, or refuse.

    Only a wholly absent reserve/posture pair is a body that has never been
    constructed through the physiology initializer, and only that body travels
    at base speed (there is no authored state to read). A half-written pair is
    corrupt state and refuses, exactly like a corrupt value or a
    forced/voluntary sleep posture; neither is ever priced as healthy.
    """

    attributes = getattr(member, "attributes", None)
    if attributes is None or not callable(getattr(attributes, "has", None)):
        # A plain synthetic probe has no attribute store at all: nothing was
        # ever initialized, so it is the wholly-absent baseline.
        return Fraction(1)
    try:
        has_reserve = attributes.has(RESERVE_ATTRIBUTE)
        has_posture = attributes.has(POSTURE_ATTRIBUTE)
    except Exception as error:  # observability: ignore R2: an unreadable attribute store is corrupt physiology, refused below as such; no state is written
        raise MovementPreflightRefused(
            "fatigue_state_invalid",
            f"{member!r} has an unreadable mental-reserve state: {error}",
        ) from error
    if not has_reserve and not has_posture:
        return Fraction(1)
    if not (has_reserve and has_posture):
        raise MovementPreflightRefused(
            "fatigue_state_partial",
            f"{member!r} has only one half of its mental-reserve state",
        )
    try:
        state = read_fatigue_state(member)
    except FatigueStateError as error:
        raise MovementPreflightRefused(
            "fatigue_state_invalid",
            f"{member!r} has an unreadable mental-reserve state: {error}",
        ) from error
    try:
        return outgoing_foot_speed_scale(state)
    except FatigueStateError as error:
        raise MovementPreflightRefused(
            "travel_forbidden",
            f"{member!r} may not travel: {error}",
        ) from error


def member_speed_m_per_hour(member: Any, terrain: str) -> Fraction:
    """Return one member's sustainable speed on ``terrain`` (exact fraction)."""

    return Fraction(terrain_speed_m_per_hour(terrain)) * _fatigue_scale(member)


def party_speed_m_per_hour(members: Sequence[Any], terrain: str) -> Fraction:
    """Return the slowest eligible member's speed (the party's travel speed).

    No headcount penalty and no averaging: five or six healthy members pay
    exactly the solo duration. ``members`` must already be the source-present
    intended travellers, so remote party members never influence the charge.
    """

    if not members:
        raise MovementPreflightRefused(
            "no_travellers", "a distance-bearing traversal needs at least one traveller"
        )
    return min(member_speed_m_per_hour(member, terrain) for member in members)


def distance_traversal_cost(
    distance_m: float, terrain: str, members: Sequence[Any]
) -> TraversalCost:
    """The shared calculation: geometry + terrain + party speed → seconds."""

    if distance_m < 0:
        raise TravelRulebookError("travel distance must not be negative")
    speed = party_speed_m_per_hour(members, terrain)
    return TraversalCost(
        distance_m=float(distance_m),
        terrain=terrain,
        seconds=traversal_seconds([distance_m], speed),
        members=tuple(members),
    )


def _grid_identity(room: Any) -> tuple[str, str] | None:
    """Return ``(map_id, node_id)`` for an authored grid room, or ``None``."""

    node_id = getattr(room, "sparse_node_id", None)
    try:
        xyz = getattr(room, "xyz", None)
    except Exception:  # observability: ignore R2: a room without grid tags has no authored identity; this is a documented non-distance connector, not a failure
        return None
    if not node_id or not xyz or len(xyz) < 3:
        return None
    return (str(xyz[2]), str(node_id))


def _grid_map_id(room: Any) -> str | None:
    """Return the xyzgrid map key of a grid room, or ``None``."""

    try:
        xyz = getattr(room, "xyz", None)
    except Exception:  # observability: ignore R2: a room without grid tags has no declared map, which the caller treats as a non-settlement connector
        return None
    if not xyz or len(xyz) < 3:
        return None
    return str(xyz[2])


def _settlement_edge(source_room: Any, destination_room: Any):
    """The authored directed settlement edge between two grid rooms, if any."""

    source = _grid_identity(source_room)
    destination = _grid_identity(destination_room)
    if source is None or destination is None or source[0] != destination[0]:
        return None
    graph = map_data.settlement_graph(source[0])
    if graph is None:
        return None
    return graph.edge(source[1], destination[1])


def settlement_edge_cost(
    source_room: Any, destination_room: Any, members: Sequence[Any]
) -> TraversalCost | None:
    """Resolve one authored settlement edge to its physical duration."""

    edge = _settlement_edge(source_room, destination_room)
    if edge is None:
        return None
    return distance_traversal_cost(edge.length, "settlement", members)


def wilderness_cell_size_m() -> int:
    """The provider's declared wilderness cell span in meters (single authority)."""

    return int(WILDERNESS_KM_PER_CELL) * 1000


def wilderness_distance_m(
    source_xy: tuple[int, int],
    destination_xy: tuple[int, int],
    *,
    cell_size_m: int | None = None,
) -> float:
    """Euclidean wilderness distance in meters (diagonals are not one cell)."""

    span = wilderness_cell_size_m() if cell_size_m is None else int(cell_size_m)
    return hypot(destination_xy[0] - source_xy[0], destination_xy[1] - source_xy[1]) * span


def wilderness_terrain(source_xy: tuple[int, int], destination_xy: tuple[int, int]) -> str:
    """The slower of the two endpoint regions' terrains (symmetric edge cost).

    The deterministic region model supplies one terrain key per cell; an edge
    between a forest cell and an open cell is as slow as its slower end in
    either direction, so identical physical roads charge identical durations.
    """

    source_region = region_for_coordinates(*source_xy)
    destination_region = region_for_coordinates(*destination_xy)
    try:
        source_terrain = WILDERNESS_TERRAIN[source_region]
        destination_terrain = WILDERNESS_TERRAIN[destination_region]
    except KeyError as error:
        raise TravelRulebookError(
            f"wilderness region {error.args[0]!r} has no declared terrain"
        ) from error
    if (
        terrain_speed_m_per_hour(destination_terrain)
        < terrain_speed_m_per_hour(source_terrain)
    ):
        return destination_terrain
    return source_terrain


def wilderness_step_cost(
    source_xy: tuple[int, int],
    destination_xy: tuple[int, int],
    members: Sequence[Any],
    *,
    cell_size_m: int | None = None,
) -> TraversalCost:
    """Resolve one wilderness step from the declared cell span and terrain."""

    return distance_traversal_cost(
        wilderness_distance_m(source_xy, destination_xy, cell_size_m=cell_size_m),
        wilderness_terrain(source_xy, destination_xy),
        members,
    )


def _find_gate(
    grid_room: Any, wilderness_xy: tuple[int, int]
) -> tuple[Any, Any] | None:
    """The registry entry+gate owning one grid room and wilderness approach cell."""

    identity = _grid_identity(grid_room)
    if identity is None:
        return None
    map_id, _ = identity
    try:
        xyz = grid_room.xyz
    except Exception:  # observability: ignore R2: identity already required; a failed second read is a non-gate connector
        return None
    grid_xy = (int(xyz[0]), int(xyz[1]))
    # Read the live registry (tests rebind the module attribute).
    from world.lore import wilderness_entry as wilderness_entry_module

    for entry in wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY.values():
        if ANCHOR_PLACEMENT_REGISTRY.get(entry.anchor_key) is None:
            continue
        for gate in entry.gates:
            if (gate.grid_xy, gate.z_map_key) != (grid_xy, map_id):
                continue
            if entry.approach_cell(gate) == tuple(wilderness_xy):
                return entry, gate
    return None


def gate_approach_cost(
    grid_room: Any,
    wilderness_xy: tuple[int, int],
    members: Sequence[Any],
    *,
    cell_size_m: int | None = None,
) -> TraversalCost | None:
    """Resolve one physical gate-approach segment across the scale boundary.

    The segment runs from the gate room's authored meter position to the
    exterior approach cell's center, both expressed in absolute continent
    meters through the settlement anchor transform (design §5.3). It is one
    segment in either direction, so crossing never adds a full wilderness cell
    plus a second city hop for the same ground.
    """

    from world.maps.wilderness_destination import gate_approach_distance_m

    hit = _find_gate(grid_room, wilderness_xy)
    if hit is None:
        return None
    entry, gate = hit
    distance = gate_approach_distance_m(entry, gate, cell_size_m=cell_size_m)
    if distance is None:
        return None
    return distance_traversal_cost(distance, "settlement", members)


def _is_wilderness_room(room: Any) -> bool:
    from typeclasses.rooms import TerrainRoom

    return isinstance(room, TerrainRoom)


def _is_grid_room(room: Any) -> bool:
    from typeclasses.rooms import GridRoom

    return isinstance(room, GridRoom)


def _wilderness_coordinates(room: Any) -> tuple[int, int] | None:
    coordinates = getattr(room, "coordinates", None)
    if (
        not isinstance(coordinates, tuple)
        or len(coordinates) != 2
        or any(isinstance(value, bool) or not isinstance(value, int) for value in coordinates)
    ):
        return None
    return (coordinates[0], coordinates[1])


def resolve_traversal_cost(
    traversing_object: Any,
    cost_key: str,
    *,
    source_location: Any,
    destination: Any | None = None,
    grid_location: Any | None = None,
    wilderness_source_coordinates: tuple[int, int] | None = None,
    wilderness_destination_coordinates: tuple[int, int] | None = None,
    members: Sequence[Any],
) -> TraversalResolution:
    """Classify and resolve one movement call before any relocation.

    ``destination`` may be ``None`` when the caller only knows the intended
    wilderness landing cell (the gate line resolves the approach from authored
    geometry, not from a room that does not exist yet). Both grid sides of a
    gate crossing are supported, so entry and return charge the same segment.

    ``grid_location`` names the grid room a gate exit is mounted in when the
    caller's traversal source is not that room (a direct ``at_traverse`` call
    on an exit object); it defaults to ``source_location``.
    """
    refuse_sleeping_party(members)

    source_is_wild = _is_wilderness_room(source_location)
    destination_is_wild = _is_wilderness_room(destination)
    destination_is_grid = _is_grid_room(destination)
    grid_source = source_location if grid_location is None else grid_location

    def resolution(status: TraversalStatus, cost: TraversalCost | None) -> TraversalResolution:
        return TraversalResolution(
            status=status,
            cost=cost,
            members=tuple(members),
            traverser_id=getattr(traversing_object, "id", None),
            cost_key=cost_key,
            source_location_id=getattr(source_location, "id", None),
        )

    wilderness_origin = (
        wilderness_source_coordinates
        if wilderness_source_coordinates is not None
        else (_wilderness_coordinates(source_location) if source_is_wild else None)
    )

    if source_is_wild:
        if destination_is_grid:
            grid_room = destination
            approach = wilderness_origin
        elif destination_is_wild or wilderness_destination_coordinates is not None:
            grid_room = None
            approach = wilderness_origin
        else:
            approach = None
            grid_room = None
        if grid_room is not None and approach is not None:
            cost = gate_approach_cost(grid_room, approach, members)
            return resolution(
                TraversalStatus.RESOLVED if cost is not None else TraversalStatus.UNRESOLVED,
                cost,
            )
        target = (
            wilderness_destination_coordinates
            if wilderness_destination_coordinates is not None
            else _wilderness_coordinates(destination)
        )
        if approach is not None and target is not None:
            return resolution(
                TraversalStatus.RESOLVED,
                wilderness_step_cost(approach, target, members),
            )
        return resolution(TraversalStatus.UNRESOLVED, None)

    if wilderness_destination_coordinates is not None or destination_is_wild:
        approach = (
            wilderness_destination_coordinates
            if wilderness_destination_coordinates is not None
            else _wilderness_coordinates(destination)
        )
        if _is_grid_room(grid_source) and approach is not None:
            cost = gate_approach_cost(grid_source, approach, members)
            return resolution(
                TraversalStatus.RESOLVED if cost is not None else TraversalStatus.UNRESOLVED,
                cost,
            )
        return resolution(TraversalStatus.UNRESOLVED, None)

    if _is_grid_room(grid_source) and _is_grid_room(destination):
        source_identity = _grid_identity(grid_source)
        destination_identity = _grid_identity(destination)
        source_map = _grid_map_id(grid_source)
        destination_map = _grid_map_id(destination)
        authored_surface = (
            source_map is not None
            and source_map == destination_map
            and map_data.settlement_graph(source_map) is not None
        )
        if authored_surface:
            # A declared settlement map is a distance-bearing outdoor surface:
            # both endpoints must carry their authored identity and the
            # directed road must exist. Anything less is broken geometry, not
            # an invented connector, so it refuses before writes.
            if source_identity is None or destination_identity is None:
                return resolution(TraversalStatus.UNRESOLVED, None)
            cost = settlement_edge_cost(grid_source, destination, members)
            return resolution(
                TraversalStatus.RESOLVED
                if cost is not None
                else TraversalStatus.UNRESOLVED,
                cost,
            )
        # Grid rooms outside every declared settlement map are explicit
        # non-distance connectors (instance interiors, builder-room doorways).
    return resolution(TraversalStatus.NON_DISTANCE, None)


@contextmanager
def preflight_movement_cost(
    traversing_object: Any,
    cost_key: str,
    *,
    source_location: Any,
    destination: Any | None = None,
    grid_location: Any | None = None,
    wilderness_source_coordinates: tuple[int, int] | None = None,
    wilderness_destination_coordinates: tuple[int, int] | None = None,
    members: Sequence[Any],
) -> Iterator[TraversalResolution]:
    """Preflight one exit movement and expose its record to the charger.

    The immutable record (geometry, terrain, party speed and the source-present
    traveller tuple) is resolved once, before relocation, and pushed onto the
    active stack. ``charge_movement`` consumes it inside the same synchronous
    call, so the post-relocation room state can never change the charge. The
    stack entry is removed on refusal, exception, and normal return.
    """

    resolution = resolve_traversal_cost(
        traversing_object,
        cost_key,
        source_location=source_location,
        destination=destination,
        grid_location=grid_location,
        wilderness_source_coordinates=wilderness_source_coordinates,
        wilderness_destination_coordinates=wilderness_destination_coordinates,
        members=members,
    )
    token = _ACTIVE_RESOLUTIONS.set((*_ACTIVE_RESOLUTIONS.get(), resolution))
    try:
        yield resolution
    finally:
        _ACTIVE_RESOLUTIONS.reset(token)


def consume_preflight_resolution(
    traversing_object: Any, cost_key: str, source_location: Any
) -> TraversalResolution | None:
    """Return the innermost preflight record matching this movement, if any."""

    traverser_id = getattr(traversing_object, "id", None)
    source_id = getattr(source_location, "id", None)
    for resolution in reversed(_ACTIVE_RESOLUTIONS.get()):
        if (
            resolution.traverser_id == traverser_id
            and resolution.cost_key == cost_key
            and resolution.source_location_id == source_id
        ):
            return resolution
    return None


def source_present_members(
    traversing_object: Any,
    source_location: Any,
    wilderness_source_coordinates: tuple[int, int] | None = None,
) -> tuple[Any, ...]:
    """The traverser plus the co-located members the follow step will move.

    The same ``follow_scope`` predicate ``follow_companions`` uses is evaluated
    against the pre-move source, so the speed, the charge entities and the
    followed party can never disagree; remote party members are excluded.
    """

    from world.rules.party import follow_scope

    _, followers = follow_scope(
        traversing_object,
        source_location,
        wilderness_source_coordinates,
        log_unresolved=False,
    )
    return (traversing_object, *followers)


def log_traversal_refusal(source: str, traversing_object: Any, reason: str) -> None:
    """Emit the one structured event a refused movement preflight records."""

    log_warn(
        "movement_preflight_refused",
        context={
            "source": source,
            "traverser": getattr(traversing_object, "dbref", None),
            "reason": reason,
        },
    )


__all__ = [
    "MovementPreflightRefused",
    "TRAVEL_YAML",
    "TERRAIN_SPEEDS",
    "TraversalCost",
    "TraversalResolution",
    "TraversalStatus",
    "TravelRulebookError",
    "WILDERNESS_TERRAIN",
    "consume_preflight_resolution",
    "distance_traversal_cost",
    "gate_approach_cost",
    "log_traversal_refusal",
    "member_speed_m_per_hour",
    "party_speed_m_per_hour",
    "preflight_movement_cost",
    "resolve_traversal_cost",
    "settlement_edge_cost",
    "source_present_members",
    "terrain_speed_m_per_hour",
    "traversal_seconds",
    "wilderness_cell_size_m",
    "wilderness_distance_m",
    "wilderness_step_cost",
    "wilderness_terrain",
]
