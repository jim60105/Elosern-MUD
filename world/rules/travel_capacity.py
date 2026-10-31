"""Read-only wilderness travel status: foot capacity and neighbour quotes.

The leg panel (OpenSpec change wilderness-travel-leg-ui) shows how far the
party can still walk and how long one neighbour step takes, so the browser
never predicts fatigue or eligibility itself. This module answers both from
the canonical owners and writes nothing:

- **Capacity** (:func:`capacity_by_stage`) counts hypothetical orthogonal
  foot steps on the *current* cell's terrain, one declared wilderness cell
  span each (one kilometre at the current geography), until canonical
  preflight would refuse the next step or a traveller falls asleep. Each step
  is priced by :func:`world.rules.travel_cost.plan_traversal` with the
  source-present travellers' predicted states (their canonical slowest
  speed), each traveller then advances through the pure fatigue prediction
  over that step's rounded seconds, exactly as the read-only planner's
  sequential replay does, and the step is counted in the bucket of the worst
  after-step stage. An admitted step that ends in the terminal
  ``forced_sleep`` (the exact-zero arrival) is counted in the ``severe``
  display bucket and ends the prediction; the canonical stage is not altered
  anywhere else. Capacity is a foot estimate: the flight waiver never applies
  to it, no neighbouring terrain, path, reveal or road is inspected, and it
  never promises that a real step is eligible.
- **Neighbour quotes** (:func:`neighbour_quotes`) copy the existing preflight
  physical duration of each committed exploration move row, with the
  canonical flight charge waiver applied. A withheld destination (``null`` in
  the committed row), a disabled row, a gateway into a settlement and any
  unresolved or refused preflight quote ``null``; the move row keeps its own
  enabled/reason, so nothing here is a second admission decision.

:func:`build_travel_status` composes both for the ``status`` panel's
``travel_capacity`` field and returns ``None`` outside wilderness exploration
or when the party has no constructed physiology at all (such a party never
tires, so a count would be invented).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from world.rules.fatigue import FatigueStage, SleepPosture, read_optional_fatigue_state
from world.rules.travel_cost import (
    MovementPreflightRefused,
    TraversalStatus,
    TravelRulebookError,
    flight_waives_wilderness_charge,
    plan_traversal,
    resolve_traversal_cost,
    source_present_members,
    wilderness_cell_size_m,
    wilderness_terrain,
)
from world.rules.travel_plan import (
    _STAGE_RANK,
    PACE_STOP_STAGES,
    TravellerState,
    _worst_stage,
)

#: The display buckets of the capacity gauge, in gauge order.
CAPACITY_BUCKETS: tuple[str, ...] = ("normal", "light", "moderate", "severe")

#: A safety bound on one prediction. A party with any constructed physiology
#: exhausts long before it (a full reserve on the fastest terrain lasts well
#: under a hundred one-kilometre steps); reaching it means the estimate is
#: not a real one and the capacity is reported unavailable instead.
MAX_CAPACITY_STEPS = 120

#: At most this many neighbour quotes are published (the wire bound).
MAX_NEIGHBOUR_QUOTES = 12

_ASLEEP_STAGES = frozenset({FatigueStage.SLEEPING, FatigueStage.FORCED_SLEEP})

_BUCKET_FOR_STAGE: dict[FatigueStage, str] = {
    FatigueStage.NORMAL: "normal",
    FatigueStage.LIGHT: "light",
    FatigueStage.MODERATE: "moderate",
    FatigueStage.SEVERE: "severe",
    # The terminal admitted step: shown in the severe bucket (presentation
    # only; the canonical stage stays forced_sleep).
    FatigueStage.FORCED_SLEEP: "severe",
    FatigueStage.SLEEPING: "severe",
}


@dataclass(frozen=True, slots=True)
class CapacitySnapshot:
    """The detached source-present travellers one estimate is answered from."""

    travellers: tuple[TravellerState, ...]


def read_capacity_snapshot(
    actor: Any, location: Any, origin: tuple[int, int]
) -> CapacitySnapshot:
    """Read the source-present travellers' states without creating any.

    Uses the canonical follow scope and the strict non-creating reader; a
    malformed or half-written physiology raises ``FatigueStateError``.
    """

    states = tuple(
        TravellerState.from_state(
            read_optional_fatigue_state(member), member_id=getattr(member, "pk", None)
        )
        for member in source_present_members(actor, location, origin)
    )
    return CapacitySnapshot(travellers=states)


def capacity_by_stage(
    snapshot: CapacitySnapshot,
    terrain: str,
    *,
    cell_size_m: int | None = None,
) -> dict[str, int] | None:
    """Count admitted hypothetical foot steps by worst after-step stage.

    Returns zero counts when nobody can walk (a sleeper at query start or a
    refused first step) and ``None`` when no traveller has constructed
    physiology, or the estimate does not end within the safety bound.
    """

    counts = {bucket: 0 for bucket in CAPACITY_BUCKETS}
    states = list(snapshot.travellers)
    if not states or all(state.reserve_units is None for state in states):
        return None
    if any(
        state.posture is not None and state.posture is not SleepPosture.AWAKE
        for state in states
    ):
        return counts
    span = wilderness_cell_size_m() if cell_size_m is None else int(cell_size_m)
    for _ in range(MAX_CAPACITY_STEPS):
        try:
            step = plan_traversal(
                ((span, terrain),), tuple(state.detached() for state in states)
            )
        except MovementPreflightRefused:
            return counts
        states = [state.advance(step.seconds) for state in states]
        stage = _worst_stage(states)
        counts[_BUCKET_FOR_STAGE[stage]] += 1
        if stage in _ASLEEP_STAGES:
            return counts
    return None


def pace_state(snapshot: CapacitySnapshot) -> dict[str, bool]:
    """Whether the current worst stage already meets each pace's threshold."""

    worst = _worst_stage(snapshot.travellers)
    return {
        pace: _STAGE_RANK[worst] >= _STAGE_RANK[threshold]
        for pace, threshold in PACE_STOP_STAGES.items()
    }


def _quote(
    actor: Any,
    location: Any,
    origin: tuple[int, int],
    members: Sequence[Any],
    row: Mapping[str, Any],
    waived: bool,
) -> int | None:
    from world.rules.map_knowledge import NodeIDError, decode_node

    destination = row.get("destination")
    if row.get("enabled") is not True or not isinstance(destination, str):
        return None
    try:
        decoded = decode_node(destination)
    except NodeIDError:
        return None
    if decoded.get("prefix") != "wild":
        # A gateway into a settlement is quoted only by its own crossing;
        # resolving its grid room here would read beyond the status scope.
        return None
    try:
        resolution = resolve_traversal_cost(
            actor,
            "wilderness_move",
            source_location=location,
            wilderness_source_coordinates=origin,
            wilderness_destination_coordinates=(decoded["x"], decoded["y"]),
            members=members,
        )
    except (MovementPreflightRefused, TravelRulebookError):  # observability: ignore R2: a refused or unpriceable step has no duration quote; the move row keeps its own enabled/reason
        return None
    if resolution.status is not TraversalStatus.RESOLVED or resolution.cost is None:
        return None
    return 0 if waived else int(resolution.cost.seconds)


def neighbour_quotes(
    actor: Any,
    location: Any,
    origin: tuple[int, int],
    members: Sequence[Any],
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """One ``{exit_ref, seconds}`` quote per committed move row (at most 12)."""

    waived = flight_waives_wilderness_charge(actor, "wilderness_move")
    quotes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        exit_ref = row.get("exit_ref")
        if not isinstance(exit_ref, str) or exit_ref in seen:
            continue
        seen.add(exit_ref)
        quotes.append(
            {
                "exit_ref": exit_ref,
                "seconds": _quote(actor, location, origin, members, row, waived),
            }
        )
        if len(quotes) >= MAX_NEIGHBOUR_QUOTES:
            break
    return quotes


def _wilderness_origin(actor: Any) -> tuple[Any, tuple[int, int]] | None:
    from typeclasses.rooms import TerrainRoom

    location = getattr(actor, "location", None)
    if not isinstance(location, TerrainRoom):
        return None
    coordinates = getattr(location, "coordinates", None)
    if (
        not isinstance(coordinates, tuple)
        or len(coordinates) != 2
        or any(isinstance(value, bool) or not isinstance(value, int) for value in coordinates)
    ):
        return None
    return location, (coordinates[0], coordinates[1])


def build_travel_status(
    actor: Any, rows: Iterable[Mapping[str, Any]] | None = None
) -> dict[str, Any] | None:
    """The exact ``travel_capacity`` status object, or ``None``.

    ``rows`` are the committed exploration move rows of this same
    publication (the presenter passes them so both panels quote one row
    set); without them the exploration presenter's own row builder is read.
    Raises the canonical readers' errors (``FatigueStateError``) for corrupt
    physiology; the presenter degrades that to ``null``.
    """

    from web.webclient.presentation.affordances import in_exploration_mode

    if not in_exploration_mode(actor):
        return None
    resolved = _wilderness_origin(actor)
    if resolved is None:
        return None
    location, origin = resolved
    snapshot = read_capacity_snapshot(actor, location, origin)
    counts = capacity_by_stage(snapshot, wilderness_terrain(origin, origin))
    if counts is None:
        return None
    if rows is None:
        from web.webclient.presentation.exploration import _move_rows

        rows = _move_rows(actor)
    members = source_present_members(actor, location, origin)
    return {
        "capacity": counts,
        "neighbours": neighbour_quotes(actor, location, origin, members, rows),
        "at_pace": pace_state(snapshot),
    }


__all__ = [
    "CAPACITY_BUCKETS",
    "MAX_CAPACITY_STEPS",
    "MAX_NEIGHBOUR_QUOTES",
    "CapacitySnapshot",
    "build_travel_status",
    "capacity_by_stage",
    "neighbour_quotes",
    "pace_state",
    "read_capacity_snapshot",
]
