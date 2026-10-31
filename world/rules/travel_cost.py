"""Distance-bearing travel cost: terrain speed, geometry and one upward round.

``world-map-scale`` design §10: a movement command traverses one authored edge
between named locations. Duration is the edge's physical geometry (Euclidean
straight length or the full authored meter polyline) divided by the slowest
eligible source-present traveller's sustainable speed for the edge's terrain,
rounded upward once for the whole committed traversal. This module is the single
calculation authority:

- the terrain speed table and the wilderness region→terrain table live in
  ``rulebook/movement.yaml`` (authored integer meters per hour, never seconds);
- settlement edge lengths come from ``elosern_map_core.sparse``'s physical node
  positions, wilderness distances from the provider's declared cell span, and
  gate approaches from the settlement anchor transform plus authored approach
  cells (``world.maps.wilderness_destination``);
- the per-member sustainable speed is the terrain speed scaled by the member's
  exact outgoing fatigue scale (``world.rules.fatigue``). A wholly absent
  mental-reserve state is a not-yet-initialized body and travels at its base
  speed; a corrupt state or a posture that forbids travel refuses the
  traversal at preflight instead of being priced as healthy.

The duration is integrated, not sampled once: :func:`plan_traversal` walks the
ordered ``(distance, terrain)`` legs and recomputes the slowest sustainable
speed at every member fatigue threshold and every terrain boundary, applying a
changed speed only to the remaining distance. Segment durations stay exact
fractions and the whole traversal rounds upward exactly once, which is the
same whole-second interval the clock's fatigue settlement commits. A member
predicted to exhaust mental reserve strictly before the destination refuses
the departure with ``pre_destination_depletion``; reaching exactly zero at
arrival is accepted and the external forced-sleep latch applies there.
Processing is per authored boundary, never per meter or per second.

Only ``seconds`` is an authority. ``clock.yaml``'s ``command_defaults`` remain
the explicit durations for non-distance connectors (a Limbo bridge, an
instance-room doorway, a plain room pair); a distance-bearing outdoor lineage
either resolves here or is refused before any write. ``wilderness_move`` is
retained as the distinct wilderness flight-waiver context key only and is never
a seconds authority. An explicit connector's authored duration is admission
checked against the same pre-destination depletion rule.

The preflight boundary is the :func:`preflight_movement_cost` context manager:
every exit lineage resolves one immutable :class:`TraversalCost` before
relocation and ``charge_movement`` consumes exactly that record through
:func:`consume_preflight_resolution` without changing its public signature.
Direct ``charge_movement`` calls outside an exit fall back to a live resolution
from the caller's source location and the traverser's current location.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
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
from world.maps.wilderness_provider import WILDERNESS_NAME, region_for_coordinates
from world.observability import log_warn
from world.rules.fatigue import (
    POSTURE_ATTRIBUTE,
    RESERVE_ATTRIBUTE,
    BoundaryKind,
    FatigueActivity,
    FatigueState,
    FatigueStateError,
    SleepPosture,
    get_policy,
    next_fatigue_boundary,
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

#: One refusal message for every pre-destination mental exhaustion.
DEPLETION_MESSAGE = "隊伍成員的精力不足以支撐這趟旅行。"


def refuse_sleeping_party(members: Sequence[Any]) -> None:
    """Refuse any travel whose source-present party includes a sleeper.

    Every sleep posture -- voluntary and forced alike -- makes the party
    stationary, so a full reserve is never evidence of being awake. The
    intended source-present follow scope is the same set the charge and the
    follow step use (the traverser plus the effective, co-located companions,
    including the owner's own body while a companion is possessed), so an
    awake possessed member can neither carry nor teleport a sleeping body and
    a remote sleeper grants nothing. The refusal happens at preflight, before
    cost resolution, skill waiver, relocation, destination creation, time or
    location changes. A malformed state still fails closed through the
    validating read rather than being treated as awake.
    """
    for member in members:
        state = read_optional_fatigue_state(member)
        if state is not None and state.posture is not SleepPosture.AWAKE:
            raise MovementPreflightRefused("party_sleeping", SLEEPING_PARTY_MESSAGE)


def refuse_pre_destination_depletion(seconds: int, members: Sequence[Any]) -> None:
    """Refuse a fixed-duration traversal a present member cannot survive.

    Non-distance connectors keep their authored ``clock.yaml`` duration, so
    their integrated duration is that constant. Exactly zero at arrival is
    accepted (the external forced sleep then applies at the destination);
    anything that exhausts strictly before arrival refuses here, before the
    exit relocates, charges time, or records knowledge.
    """
    if seconds <= 0:
        return
    rate = abs(int(get_policy().rates[FatigueActivity.FOOT_TRAVEL]))
    for member in members:
        state = _fatigue_state(member)
        if state is None:
            continue
        if Fraction(state.reserve_units, rate) < seconds:
            raise MovementPreflightRefused(
                "pre_destination_depletion", DEPLETION_MESSAGE
            )


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


_validate_rulebook()


def validate_wilderness_region_coverage(region_keys) -> None:
    """Reject a published region set this rulebook cannot price.

    The map-owned region vocabulary is loaded from the continent source, so the
    coverage join runs when that geography is published
    (``world.maps.geography``), not at this module's import.
    """

    missing = sorted(set(region_keys) - set(WILDERNESS_TERRAIN))
    if missing:
        raise TravelRulebookError(
            f"movement.yaml: wilderness regions without a terrain row: {missing}"
        )


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


def _fatigue_state(member: Any) -> FatigueState | None:
    """Return one present member's validated fatigue state, or refuse.

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
        return None
    try:
        has_reserve = attributes.has(RESERVE_ATTRIBUTE)
        has_posture = attributes.has(POSTURE_ATTRIBUTE)
    except Exception as error:  # observability: ignore R2: an unreadable attribute store is corrupt physiology, refused below as such; no state is written
        raise MovementPreflightRefused(
            "fatigue_state_invalid",
            f"{member!r} has an unreadable mental-reserve state: {error}",
        ) from error
    if not has_reserve and not has_posture:
        return None
    if not (has_reserve and has_posture):
        raise MovementPreflightRefused(
            "fatigue_state_partial",
            f"{member!r} has only one half of its mental-reserve state",
        )
    try:
        return read_fatigue_state(member)
    except FatigueStateError as error:
        raise MovementPreflightRefused(
            "fatigue_state_invalid",
            f"{member!r} has an unreadable mental-reserve state: {error}",
        ) from error


def _state_speed_m_per_hour(state: FatigueState | None, terrain: str) -> Fraction:
    """One predicted member state's sustainable speed on ``terrain``.

    A ``None`` state is the wholly-absent construction baseline and travels at
    the base terrain speed for the whole traversal (it never transitions). A
    stored state uses the external fatigue owner's outgoing scale, so a segment
    that begins exactly on a band floor already travels at the lower band.
    """

    speed = Fraction(terrain_speed_m_per_hour(terrain))
    if state is None:
        return speed
    try:
        return speed * outgoing_foot_speed_scale(state)
    except FatigueStateError as error:
        raise MovementPreflightRefused(
            "travel_forbidden",
            f"a member may not travel: {error}",
        ) from error


def member_speed_m_per_hour(member: Any, terrain: str) -> Fraction:
    """Return one member's sustainable speed on ``terrain`` (exact fraction)."""

    return _state_speed_m_per_hour(_fatigue_state(member), terrain)


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


@dataclass(frozen=True, slots=True)
class TraversalSegment:
    """One constant-speed piece of an integrated traversal.

    ``seconds`` and ``distance_m`` are exact fractions: the pieces are summed
    before the traversal's single upward rounding, so a subsecond boundary is
    never rounded per segment.
    """

    seconds: Fraction
    distance_m: Fraction
    speed_m_per_hour: Fraction


@dataclass(frozen=True, slots=True)
class TraversalPlan:
    """One integrated traversal: constant-speed segments plus its commitment."""

    distance_m: Fraction
    segments: tuple[TraversalSegment, ...]
    seconds: int
    members: tuple[Any, ...]


def _predicted_state(reserve_units: int, elapsed: Fraction) -> FatigueState:
    """The predicted state of one body after exact fractional ``elapsed``.

    Foot-travel consumption is exactly linear in elapsed time, so every
    segment start (including the start of a later terrain leg) is derived from
    the member's initial reserve and the traversal's exact elapsed time rather
    than from a per-segment state that flooring would drift. The stored state
    is integral: the reserve is truncated and the residual fraction still
    belongs to the same band, while a fully consumed reserve is the forced
    latch.
    """

    rate = Fraction(get_policy().rates[FatigueActivity.FOOT_TRAVEL])
    exact = Fraction(reserve_units) + rate * elapsed
    if exact <= 0:
        return FatigueState(
            reserve_units=0, posture=SleepPosture.FORCED
        )
    return FatigueState(reserve_units=int(exact), posture=SleepPosture.AWAKE)


def plan_traversal(
    legs: Sequence[tuple[float, str]], members: Sequence[Any]
) -> TraversalPlan:
    """Integrate one traversal across ordered ``(distance_m, terrain)`` legs.

    Every member's state is read once, so the actual initial posture is what
    admission judges: any initial sleeper refuses the departure with the
    stable sleeping-party reason before a distance is integrated, and neither
    a full reserve nor a waiver can reconstruct an awake traveller. Only then
    is the party speed recomputed at each member threshold and each terrain
    boundary, and only the remaining distance uses a changed speed. Segments
    are keyed by those authored boundaries, never by meter or second. The
    exact segment durations are summed before the traversal's single upward
    rounding, so prediction and the whole-second fatigue settlement agree on
    the committed duration. A member predicted to exhaust strictly before the
    final destination refuses the departure; reaching exactly zero at arrival
    is accepted and the external forced sleep applies there.
    """

    if not members:
        raise MovementPreflightRefused(
            "no_travellers", "a distance-bearing traversal needs at least one traveller"
        )
    initial_states = tuple(_fatigue_state(member) for member in members)
    if any(
        state is not None and state.posture is not SleepPosture.AWAKE
        for state in initial_states
    ):
        # Posture is carried through prediction, never inferred from reserve:
        # a voluntary sleeper at full reserve is still stationary.
        raise MovementPreflightRefused("party_sleeping", SLEEPING_PARTY_MESSAGE)
    initial_reserves = tuple(
        None if state is None else state.reserve_units for state in initial_states
    )
    rate = Fraction(get_policy().rates[FatigueActivity.FOOT_TRAVEL])
    total_distance = Fraction(0)
    elapsed = Fraction(0)
    segments: list[TraversalSegment] = []
    for distance_m, terrain in legs:
        if distance_m < 0:
            raise TravelRulebookError("travel distance must not be negative")
        remaining = Fraction(distance_m)
        total_distance += remaining
        while remaining > 0:
            states = tuple(
                None if reserve is None else _predicted_state(reserve, elapsed)
                for reserve in initial_reserves
            )
            if any(
                state is not None and state.posture is SleepPosture.FORCED
                for state in states
            ):
                # A member exhausted on an earlier leg: the destination is
                # still ahead, so this departure can never complete.
                raise MovementPreflightRefused(
                    "pre_destination_depletion", DEPLETION_MESSAGE
                )
            speeds = [_state_speed_m_per_hour(state, terrain) for state in states]
            speed = min(speeds)
            if speed <= 0:
                raise TravelRulebookError("travel speed must be positive")
            metres_per_second = speed / 3600
            # Each boundary offset is measured against the exact fractional
            # reserve (not its truncated state), so a carried fraction from an
            # earlier leg is never dropped.
            boundaries: list[tuple[Fraction, BoundaryKind]] = []
            for reserve, state in zip(initial_reserves, states):
                if reserve is None or state is None:
                    continue
                boundary = next_fatigue_boundary(
                    state, FatigueActivity.FOOT_TRAVEL
                )
                if boundary is None:
                    continue
                exact_reserve = Fraction(reserve) + rate * elapsed
                boundaries.append(
                    (
                        (exact_reserve - boundary.reserve_units) / -rate,
                        boundary.kind,
                    )
                )
            boundary_seconds = (
                min(offset for offset, _ in boundaries) if boundaries else None
            )
            if boundary_seconds is None:
                segments.append(
                    TraversalSegment(
                        seconds=remaining / metres_per_second,
                        distance_m=remaining,
                        speed_m_per_hour=speed,
                    )
                )
                elapsed += remaining / metres_per_second
                break
            coverable = metres_per_second * boundary_seconds
            if remaining <= coverable:
                # The remaining distance fits before the next boundary (the
                # exact-zero-at-arrival case lands here and is accepted).
                segments.append(
                    TraversalSegment(
                        seconds=remaining / metres_per_second,
                        distance_m=remaining,
                        speed_m_per_hour=speed,
                    )
                )
                elapsed += remaining / metres_per_second
                break
            if boundary_seconds <= 0 or any(
                kind is BoundaryKind.DEPLETION and offset == boundary_seconds
                for offset, kind in boundaries
            ):
                # A member reaches zero (or already is) before this leg -- and
                # therefore before the destination -- completes.
                raise MovementPreflightRefused(
                    "pre_destination_depletion", DEPLETION_MESSAGE
                )
            segments.append(
                TraversalSegment(
                    seconds=boundary_seconds,
                    distance_m=coverable,
                    speed_m_per_hour=speed,
                )
            )
            remaining -= coverable
            elapsed += boundary_seconds
    return TraversalPlan(
        distance_m=total_distance,
        segments=tuple(segments),
        seconds=ceil(elapsed),
        members=tuple(members),
    )


def distance_traversal_cost(
    distance_m: float, terrain: str, members: Sequence[Any]
) -> TraversalCost:
    """The shared calculation: geometry + terrain + integrated party speed."""

    plan = plan_traversal(((distance_m, terrain),), members)
    return TraversalCost(
        distance_m=float(distance_m),
        terrain=terrain,
        seconds=plan.seconds,
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

    from world.maps import wilderness_provider

    return int(wilderness_provider.WILDERNESS_KM_PER_CELL) * 1000


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


def wilderness_step_weight(
    source_xy: tuple[int, int],
    destination_xy: tuple[int, int],
    members: Sequence[Any],
    *,
    cell_size_m: int | None = None,
) -> int:
    """One read-only routing weight for a wilderness step.

    This is the travel planner's candidate-edge price and nothing else. It is
    the canonical :func:`wilderness_step_cost` duration whenever that preflight
    admits the step; when the initial-state preflight refuses it (a member
    depletes strictly before the step's end), it degrades to the pure
    distance/terrain duration at the initial frozen party speed, so a bounded
    search can still compare edge lengths. It never authorizes execution: the
    planner's sequential replay re-runs the canonical preflight before any step
    is admitted or charged.
    """

    try:
        return wilderness_step_cost(
            source_xy, destination_xy, members, cell_size_m=cell_size_m
        ).seconds
    except MovementPreflightRefused:  # observability: ignore R2: the refused edge is replaced by its documented routing-only distance/terrain weight; the sequential replay reports any real refusal to the caller
        terrain = wilderness_terrain(source_xy, destination_xy)
        distance = Fraction(
            wilderness_distance_m(source_xy, destination_xy, cell_size_m=cell_size_m)
        )
        speed = party_speed_m_per_hour(members, terrain)
        return ceil(distance / (speed / 3600))


def flight_waives_wilderness_charge(traversing_object: Any, cost_key: str) -> bool:
    """Whether the flight effect waives this traversal's wilderness charge.

    The single canonical decision used by execution
    (``world.rules.movement.charge_movement``) and read-only planning: only an
    owned, currently allowed ``flight`` effect on the actual traverser waives
    the ``wilderness_move`` charge. ``flash_step`` explicitly does not waive
    it; that skill only satisfies flight-required exit admission. Admission
    (sleeping and depletion preflight) is the caller's earlier responsibility,
    so this predicate never authorizes a traversal on its own.
    """

    if cost_key != "wilderness_move":
        return False
    skills = getattr(traversing_object, "skills", None)
    owned = getattr(skills, "owned_keys", None)
    if not callable(owned) or "flight" not in owned():
        return False
    from world.skills.restrictions import skill_effect_allowed

    return skill_effect_allowed(traversing_object, "flight")


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
    from elosern_map_core.references import ReferenceError
    from world.maps.static_references import settlement_node_xyz

    for entry in wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY.values():
        if ANCHOR_PLACEMENT_REGISTRY.get(entry.anchor_key) is None:
            continue
        for gate in entry.gates:
            if gate.destination.map_id != map_id:
                continue
            try:
                position = settlement_node_xyz(
                    gate.destination,
                    source=f"wilderness gate {entry.anchor_key}",
                )
            except ReferenceError:  # observability: ignore R2: a patched-in gate on an absent map is simply not this connector
                continue
            if position != (grid_xy[0], grid_xy[1], map_id):
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
    # An explicit connector's authored duration is still a traversal a member
    # must survive: refuse departure before any write exactly as a physical
    # edge does, with the same exact-zero-at-arrival allowance.
    from world.rules.clock import CLOCK_YAML

    authored_seconds = CLOCK_YAML.get("command_defaults", {}).get(cost_key)
    if isinstance(authored_seconds, int):
        refuse_pre_destination_depletion(authored_seconds, members)
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


def active_traversal_members(
    traversing_object: Any, source_location: Any
) -> tuple[Any, ...] | None:
    """The innermost preflight traveller tuple for this traversal, if any.

    The settlement snapshot reuses exactly the scope the preflight priced and
    the charge will settle, so a post-relocation rollback restores the same
    travellers it may have written. It falls back to an independent scope
    resolution only for a direct call outside an exit lineage.
    """

    traverser_id = getattr(traversing_object, "id", None)
    source_id = getattr(source_location, "id", None)
    for resolution in reversed(_ACTIVE_RESOLUTIONS.get()):
        if (
            resolution.traverser_id == traverser_id
            and resolution.source_location_id == source_id
        ):
            return resolution.members
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

    from world.rules.party import travel_scope

    return travel_scope(
        traversing_object, source_location, wilderness_source_coordinates
    )


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
    "DEPLETION_MESSAGE",
    "MovementPreflightRefused",
    "TRAVEL_YAML",
    "TERRAIN_SPEEDS",
    "TraversalCost",
    "TraversalPlan",
    "TraversalResolution",
    "TraversalSegment",
    "TraversalStatus",
    "TravelRulebookError",
    "WILDERNESS_TERRAIN",
    "active_traversal_members",
    "consume_preflight_resolution",
    "distance_traversal_cost",
    "gate_approach_cost",
    "log_traversal_refusal",
    "member_speed_m_per_hour",
    "party_speed_m_per_hour",
    "plan_traversal",
    "preflight_movement_cost",
    "refuse_pre_destination_depletion",
    "refuse_sleeping_party",
    "resolve_traversal_cost",
    "settlement_edge_cost",
    "source_present_members",
    "terrain_speed_m_per_hour",
    "wilderness_cell_size_m",
    "wilderness_distance_m",
    "wilderness_step_cost",
    "wilderness_terrain",
]
