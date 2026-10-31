"""Read-only ``travel.plan`` routing and sequential settlement prediction.

``travel.plan`` answers one bounded question: from the actor's current
wilderness cell, which revealed passable cells would the party actually reach,
in what order, how long each admitted step charges, and where would a chosen
pace or the fall of night stop the walk? It writes nothing and never ticks the
clock.

The planner is split in two:

- :func:`read_travel_snapshot` performs every world read once (the revealed
  window, the source-present travellers' validated reserve/posture, the
  charge-waiver fact and the current tick) and returns an immutable
  :class:`TravelSnapshot`.
- :func:`plan_travel` is a pure function of that snapshot, the destination,
  the pace and ``stop_at_night``. It never reads or writes a real entity.

Routing is A* with a zero (admissible) heuristic, i.e. Dijkstra, over the
revealed cells of the inclusive current±20 window clipped to the frame. Eight
directions are offered through the canonical
:func:`world.maps.wilderness_destination.wilderness_neighbor`, so a diagonal
step requires both crossed orthogonal cells to be passable; the planner adds
the reveal requirement to the destination and to both crossed orthogonals. A
registered gateway direction is never an ordinary wilderness route -- execution
diverts it into its grid room before the ordinary step -- so those directions
are excluded. Candidate edges are priced by
:func:`world.rules.travel_cost.wilderness_step_weight` with the snapshot's
reserves frozen; stable neighbour order plus the ``(cost, steps, y, x)`` heap
key make the selected route deterministic.

Sequential replay then re-runs the canonical
:func:`world.rules.travel_cost.wilderness_step_cost` preflight for each edge
with the *predicted* member states carried forward. A step is admitted only
when that canonical preflight admits it; the charge is the canonical rounded
duration unless the traverser's flight effect waives it (then it is zero and
neither the calendar nor any reserve moves). Fatigue is advanced by the pure
:func:`world.rules.fatigue.predict_interval` over the charged seconds, never by
local arithmetic. The whole route is never rounded as one interval: each step
carries its own rounded seconds and the total sums them.

The stop semantics are the approved design's: cautious stops after the first
step that reaches light fatigue, standard after moderate, forced has no
voluntary threshold; ``stop_at_night`` stops after the first positive charged
interval containing a night entry, decided on absolute calendar boundaries.
Travellers already at or beyond the pace threshold stop after the first legal
step. Admitted preview steps continue past a voluntary stop, but never past a
refused edge or a forced-sleep step. Simultaneous stops resolve in the order
``member_asleep``, ``preflight_refused``, ``pace_threshold``, ``nightfall``,
``destination_reached``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import heapq
from typing import Any

from world.rules import sight
from world.rules.clock import CLOCK_YAML, WorldDateTime, read_world_clock
from world.rules.fatigue import (
    POSTURE_ATTRIBUTE,
    RESERVE_ATTRIBUTE,
    FatigueActivity,
    FatigueStage,
    FatigueState,
    FatigueStateError,
    IntervalCompletion,
    SleepPosture,
    fatigue_stage,
    predict_interval,
    read_optional_fatigue_state,
)
from world.rules.map_knowledge import revealed_in_bounds
from world.rules.travel_cost import (
    MovementPreflightRefused,
    flight_waives_wilderness_charge,
    source_present_members,
    wilderness_step_cost,
    wilderness_step_weight,
)

#: The inclusive half-width of the query window around the origin (`current±20`).
PLAN_WINDOW_RADIUS = 20

#: One plan never proposes more admitted steps than this.
MAX_PLAN_STEPS = 60

PACES: tuple[str, ...] = ("cautious", "standard", "forced")

#: The voluntary fatigue threshold each pace stops at; forced has none.
PACE_STOP_STAGES: dict[str, FatigueStage] = {
    "cautious": FatigueStage.LIGHT,
    "standard": FatigueStage.MODERATE,
}

#: Stable result stop reasons, in the design's simultaneous-stop priority order.
STOP_REASONS: tuple[str, ...] = (
    "member_asleep",
    "preflight_refused",
    "pace_threshold",
    "nightfall",
    "destination_reached",
)

#: The five stable domain error codes (design §7.2). Nothing else leaves here.
PLAN_OUTSIDE_WINDOW = "plan_destination_outside_window"
PLAN_UNREVEALED = "plan_destination_unrevealed"
PLAN_UNREACHABLE = "plan_unreachable"
PLAN_TOO_LONG = "plan_too_long"
PLAN_PARTY_CANNOT_TRAVEL = "plan_party_cannot_travel"

#: Stable direction order for neighbour generation.
DIRECTION_ORDER: tuple[str, ...] = ("n", "ne", "e", "se", "s", "sw", "w", "nw")

_STAGE_RANK: dict[FatigueStage, int] = {
    FatigueStage.NORMAL: 0,
    FatigueStage.LIGHT: 1,
    FatigueStage.MODERATE: 2,
    FatigueStage.SEVERE: 3,
    FatigueStage.SLEEPING: 4,
    FatigueStage.FORCED_SLEEP: 5,
}

_ASLEEP_STAGES = frozenset({FatigueStage.SLEEPING, FatigueStage.FORCED_SLEEP})

_SECONDS_PER_HOUR = int(CLOCK_YAML["seconds_per_hour"])


class TravelPlanRefused(Exception):
    """One ``travel.plan`` domain refusal carrying its stable code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class TravellerState:
    """One traveller's validated state, detached from any live entity.

    ``reserve_units`` and ``posture`` are both ``None`` for a body whose
    physiology was never constructed (the canonical not-yet-initialized
    baseline that travels at base speed). A half-written or malformed state is
    never represented here: the snapshot read refuses it exactly as movement
    preflight does.

    ``member_id`` is the source entity's dbref when the state came from a live
    snapshot. It exists only so a caller can correlate a predicted state with
    its body; the planner never reads it and it never reaches result data.
    """

    reserve_units: int | None
    posture: SleepPosture | None
    member_id: int | None = None

    @classmethod
    def from_state(
        cls, state: FatigueState | None, *, member_id: int | None = None
    ) -> "TravellerState":
        if state is None:
            return cls(reserve_units=None, posture=None, member_id=member_id)
        return cls(
            reserve_units=state.reserve_units,
            posture=state.posture,
            member_id=member_id,
        )

    def detached(self) -> "_DetachedTraveller":
        """A stand-in the canonical cost helpers can read as this state."""

        return _DetachedTraveller(_DetachedAttributes(self))

    def advance(self, seconds: int) -> "TravellerState":
        """This state after ``seconds`` of foot travel (pure prediction)."""

        if self.reserve_units is None or self.posture is None:
            return self
        prediction = predict_interval(
            FatigueState(reserve_units=self.reserve_units, posture=self.posture),
            FatigueActivity.FOOT_TRAVEL,
            seconds,
            completion=IntervalCompletion.INDIVISIBLE,
        )
        return TravellerState.from_state(
            prediction.end, member_id=self.member_id
        )

    def stage(self) -> FatigueStage | None:
        """The instantaneous canonical stage, or ``None`` without physiology."""

        if self.reserve_units is None or self.posture is None:
            return None
        return fatigue_stage(
            FatigueState(reserve_units=self.reserve_units, posture=self.posture)
        )


class _DetachedAttributes:
    """The attribute-store surface ``wilderness_step_cost`` reads."""

    __slots__ = ("_state",)

    def __init__(self, state: TravellerState) -> None:
        self._state = state

    def has(self, key: str) -> bool:
        if key == RESERVE_ATTRIBUTE:
            return self._state.reserve_units is not None
        if key == POSTURE_ATTRIBUTE:
            return self._state.posture is not None
        return False

    def get(self, key: str, default: Any = None) -> Any:
        if key == RESERVE_ATTRIBUTE and self._state.reserve_units is not None:
            return self._state.reserve_units
        if key == POSTURE_ATTRIBUTE and self._state.posture is not None:
            return self._state.posture
        return default


class _DetachedTraveller:
    """One predicted traveller the canonical cost helpers can price."""

    __slots__ = ("attributes",)

    def __init__(self, attributes: _DetachedAttributes) -> None:
        self.attributes = attributes


@dataclass(frozen=True, slots=True)
class TravelSnapshot:
    """The immutable query snapshot one plan is answered from."""

    origin: tuple[int, int]
    bounds: tuple[int, int, int, int]
    revealed: frozenset[tuple[int, int]]
    travellers: tuple[TravellerState, ...]
    charge_waived: bool
    tick: int

    def detached_travellers(self) -> tuple[_DetachedTraveller, ...]:
        return tuple(traveller.detached() for traveller in self.travellers)


@dataclass(frozen=True, slots=True)
class PlanStep:
    """One admitted step: its arrival cell, charged seconds and worst stage."""

    cell: tuple[int, int]
    seconds: int
    fatigue_stage: FatigueStage


@dataclass(frozen=True, slots=True)
class TravelPlan:
    """The exact ``travel.plan`` success value (indexes zero-based, nullable)."""

    origin: tuple[int, int]
    destination: tuple[int, int]
    steps: tuple[PlanStep, ...]
    total_seconds: int
    nightfall_index: int | None
    stop_index: int | None
    stop_reason: str | None

    def as_data(self) -> dict[str, Any]:
        """The exact bounded result data object (the protocol's data slot)."""

        return {
            "origin": {"x": self.origin[0], "y": self.origin[1]},
            "destination": {"x": self.destination[0], "y": self.destination[1]},
            "steps": [
                {
                    "cell": {"x": step.cell[0], "y": step.cell[1]},
                    "seconds": step.seconds,
                    "fatigue_stage": step.fatigue_stage.value,
                }
                for step in self.steps
            ],
            "total_seconds": self.total_seconds,
            "nightfall_index": self.nightfall_index,
            "stop_index": self.stop_index,
            "stop_reason": self.stop_reason,
        }


# -- snapshot reads ---------------------------------------------------------
def read_travel_snapshot(actor: Any) -> TravelSnapshot:
    """Read one ``travel.plan`` snapshot from the actor's current wilderness room.

    Every read is a pure projection: the revealed window uses the map-knowledge
    owner, the traveller tuple is the canonical source-present follow scope, and
    the tick comes from the non-creating clock accessor. A traveller with
    half-written or malformed physiology is refused exactly as movement
    preflight refuses it (``plan_party_cannot_travel``). The builder assumes the
    caller already established wilderness exploration mode.
    """

    from typeclasses.rooms import TerrainRoom
    from world.maps import wilderness_provider
    from world.rules.map_knowledge import KnowledgeError

    location = getattr(actor, "location", None)
    coordinates = getattr(location, "coordinates", None)
    if not isinstance(location, TerrainRoom) or not isinstance(coordinates, tuple):
        raise ValueError("travel.plan requires a wilderness TerrainRoom")
    if len(coordinates) != 2 or any(
        isinstance(value, bool) or not isinstance(value, int) for value in coordinates
    ):
        raise ValueError("travel.plan requires integer wilderness coordinates")
    origin = (coordinates[0], coordinates[1])
    max_x = wilderness_provider.WILDERNESS_MAX_X
    max_y = wilderness_provider.WILDERNESS_MAX_Y
    bounds = (
        max(0, origin[0] - PLAN_WINDOW_RADIUS),
        max(0, origin[1] - PLAN_WINDOW_RADIUS),
        min(max_x, origin[0] + PLAN_WINDOW_RADIUS),
        min(max_y, origin[1] + PLAN_WINDOW_RADIUS),
    )
    try:
        revealed = revealed_in_bounds(actor, bounds)
    except KnowledgeError:  # observability: ignore R2: the owner already degrades an unreadable record to "nothing revealed"; the query answers with the same projection
        revealed = frozenset()

    states: list[TravellerState] = []
    for member in source_present_members(actor, location, origin):
        try:
            state = read_optional_fatigue_state(member)
        except FatigueStateError as error:
            # Canonical movement preflight refuses a malformed physiology, so
            # the query reports the same refusal instead of an internal error.
            raise TravelPlanRefused(PLAN_PARTY_CANNOT_TRAVEL) from error
        states.append(
            TravellerState.from_state(state, member_id=getattr(member, "pk", None))
        )

    clock = read_world_clock()
    return TravelSnapshot(
        origin=origin,
        bounds=bounds,
        revealed=frozenset(revealed),
        travellers=tuple(states),
        charge_waived=flight_waives_wilderness_charge(actor, "wilderness_move"),
        tick=0 if clock is None else int(clock.tick),
    )


# -- pure plan --------------------------------------------------------------
def plan_travel(
    snapshot: TravelSnapshot,
    destination: tuple[int, int],
    pace: str,
    stop_at_night: bool,
) -> TravelPlan:
    """Plan one bounded revealed-window route and its sequential settlement."""

    if pace not in PACES:
        raise ValueError(f"unknown travel pace {pace!r}")
    x, y = destination
    x0, y0, x1, y1 = snapshot.bounds
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        raise TravelPlanRefused(PLAN_OUTSIDE_WINDOW)
    if (x, y) not in snapshot.revealed:
        raise TravelPlanRefused(PLAN_UNREVEALED)
    if any(
        traveller.posture is not None and traveller.posture is not SleepPosture.AWAKE
        for traveller in snapshot.travellers
    ):
        raise TravelPlanRefused(PLAN_PARTY_CANNOT_TRAVEL)
    if (x, y) == snapshot.origin:
        return TravelPlan(
            origin=snapshot.origin,
            destination=(x, y),
            steps=(),
            total_seconds=0,
            nightfall_index=None,
            stop_index=None,
            stop_reason="destination_reached",
        )

    route = _route(snapshot, (x, y))
    if route is None:
        raise TravelPlanRefused(PLAN_UNREACHABLE)
    if len(route) > MAX_PLAN_STEPS:
        raise TravelPlanRefused(PLAN_TOO_LONG)
    return _replay(snapshot, (x, y), route, pace, stop_at_night)


def _route(
    snapshot: TravelSnapshot, destination: tuple[int, int]
) -> tuple[tuple[int, int], ...] | None:
    """The deterministic duration-weighted cell route, without the origin."""

    from world.maps import wilderness_destination

    frozen = snapshot.detached_travellers()
    revealed = snapshot.revealed
    origin = snapshot.origin
    weights: dict[tuple[tuple[int, int], tuple[int, int]], int] = {}

    def weight(source: tuple[int, int], target: tuple[int, int]) -> int:
        key = (source, target)
        price = weights.get(key)
        if price is None:
            price = wilderness_step_weight(source, target, frozen)
            weights[key] = price
        return price

    def neighbours(cell: tuple[int, int]):
        for direction in DIRECTION_ORDER:
            dx, dy = wilderness_destination.DIRECTION_DELTAS[direction]
            # A registered gateway is not an ordinary wilderness route:
            # execution diverts that direction into its grid room first.
            if wilderness_destination.find_gateway(cell, direction) is not None:
                continue
            target = wilderness_destination.wilderness_neighbor(
                cell[0], cell[1], direction
            )
            if target is None or target not in revealed:
                continue
            if dx and dy and (
                (cell[0] + dx, cell[1]) not in revealed
                or (cell[0], cell[1] + dy) not in revealed
            ):
                continue
            yield target

    best: dict[tuple[int, int], tuple[int, int]] = {origin: (0, 0)}
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    heap: list[tuple[int, int, int, int, tuple[int, int]]] = [
        (0, 0, origin[1], origin[0], origin)
    ]
    while heap:
        cost, steps, _, _, cell = heapq.heappop(heap)
        if best.get(cell) != (cost, steps):
            continue
        if cell == destination:
            break
        for target in neighbours(cell):
            candidate = (cost + weight(cell, target), steps + 1)
            current = best.get(target)
            if current is not None and current <= candidate:
                continue
            best[target] = candidate
            came_from[target] = cell
            heapq.heappush(
                heap, (candidate[0], candidate[1], target[1], target[0], target)
            )
    if destination not in best:
        return None
    path: list[tuple[int, int]] = []
    cell = destination
    while cell != origin:
        path.append(cell)
        cell = came_from[cell]
    path.reverse()
    return tuple(path)


def _replay(
    snapshot: TravelSnapshot,
    destination: tuple[int, int],
    route: Sequence[tuple[int, int]],
    pace: str,
    stop_at_night: bool,
) -> TravelPlan:
    """Re-run the canonical sequential preflight over one selected route."""

    states = list(snapshot.travellers)
    tick = snapshot.tick
    steps: list[PlanStep] = []
    nightfall_index: int | None = None
    refused_at_end = False
    asleep_at_end = False
    previous = snapshot.origin

    for index, cell in enumerate(route):
        try:
            cost = wilderness_step_cost(
                previous, cell, tuple(state.detached() for state in states)
            )
        except MovementPreflightRefused:
            if index == 0:
                raise TravelPlanRefused(PLAN_PARTY_CANNOT_TRAVEL) from None
            refused_at_end = True
            break
        charged = 0 if snapshot.charge_waived else cost.seconds
        if charged > 0:
            entry = _night_entry_offset(tick, charged)
            if entry is not None and nightfall_index is None:
                nightfall_index = index
            tick += charged
            states = [state.advance(charged) for state in states]
        stage = _worst_stage(states)
        steps.append(PlanStep(cell=cell, seconds=charged, fatigue_stage=stage))
        previous = cell
        if stage in _ASLEEP_STAGES:
            asleep_at_end = True
            break

    stop_index, stop_reason = _stop(
        steps,
        arrival=len(steps) == len(route),
        refused_at_end=refused_at_end,
        asleep_at_end=asleep_at_end,
        pace=pace,
        stop_at_night=stop_at_night,
        nightfall_index=nightfall_index,
    )
    total_seconds = sum(step.seconds for step in steps[: stop_index + 1])
    return TravelPlan(
        origin=snapshot.origin,
        destination=destination,
        steps=tuple(steps),
        total_seconds=total_seconds,
        nightfall_index=nightfall_index,
        stop_index=stop_index,
        stop_reason=stop_reason,
    )


def _stop(
    steps: Sequence[PlanStep],
    *,
    arrival: bool,
    refused_at_end: bool,
    asleep_at_end: bool,
    pace: str,
    stop_at_night: bool,
    nightfall_index: int | None,
) -> tuple[int, str]:
    """The first stop index and its stable reason (design priority order)."""

    candidates: list[tuple[int, int, str]] = []
    if asleep_at_end:
        candidates.append((len(steps) - 1, 0, "member_asleep"))
    if refused_at_end:
        # The refused edge is excluded; the stop points at the last admitted step.
        candidates.append((len(steps) - 1, 1, "preflight_refused"))
    threshold = PACE_STOP_STAGES.get(pace)
    if threshold is not None:
        for index, step in enumerate(steps):
            if _STAGE_RANK[step.fatigue_stage] >= _STAGE_RANK[threshold]:
                candidates.append((index, 2, "pace_threshold"))
                break
    if stop_at_night and nightfall_index is not None:
        candidates.append((nightfall_index, 3, "nightfall"))
    if arrival:
        candidates.append((len(steps) - 1, 4, "destination_reached"))
    index, _, reason = min(candidates)
    return index, reason


def _worst_stage(states: Iterable[TravellerState]) -> FatigueStage:
    """The worst canonical after-step stage (``NORMAL`` when all are absent)."""

    worst = FatigueStage.NORMAL
    for state in states:
        stage = state.stage()
        if stage is not None and _STAGE_RANK[stage] > _STAGE_RANK[worst]:
            worst = stage
    return worst


def _night_entry_offset(tick: int, seconds: int) -> int | None:
    """The offset of the first non-night -> night entry inside ``(0, seconds]``.

    The comparison is made at absolute calendar hour boundaries, so a step
    whose start and end phases are both daylight but which crosses a night
    boundary is still an entry, a step that starts in the night never reports
    that same night, and a long interval that leaves the night and re-enters a
    later one reports that later entry.
    """

    if seconds <= 0:
        return None
    current = sight.light_phase(WorldDateTime.from_tick(tick))
    end = tick + seconds
    boundary = (tick // _SECONDS_PER_HOUR + 1) * _SECONDS_PER_HOUR
    while boundary <= end:
        phase = sight.light_phase(WorldDateTime.from_tick(boundary))
        if phase == "night" and current != "night":
            return boundary - tick
        current = phase
        boundary += _SECONDS_PER_HOUR
    return None


__all__ = [
    "DIRECTION_ORDER",
    "MAX_PLAN_STEPS",
    "PACES",
    "PLAN_OUTSIDE_WINDOW",
    "PLAN_PARTY_CANNOT_TRAVEL",
    "PLAN_TOO_LONG",
    "PLAN_UNREACHABLE",
    "PLAN_UNREVEALED",
    "PLAN_WINDOW_RADIUS",
    "STOP_REASONS",
    "PlanStep",
    "TravelPlan",
    "TravelPlanRefused",
    "TravelSnapshot",
    "TravellerState",
    "plan_travel",
    "read_travel_snapshot",
]
