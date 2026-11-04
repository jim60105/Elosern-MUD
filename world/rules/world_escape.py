"""Pure world escape planning: a mapped flee needs a real committed route.

Combat resolution owns the agility contest; this module owns the physical half.
It projects the fleeing member's unpaid combat physiology through the action's
occurrence, quotes every adjacent legal edge through the canonical movement
resolver, chooses one deterministically from the engagement's own execution
scope, and returns the immutable plan the map owner commits.

Nothing here writes: ``plan_individual_escape`` and
``project_monster_combat_state`` are read-only. ``settle_monster_combat_through``
pays exactly the unpaid combat prefix through the sole fatigue writer and
advances the map-owned cursor in the same call, so departure can seed the
journey from a committed state without a second settlement.

``plan_party_retreat`` is the player party's counterpart. It projects the whole
present team's unpaid combat prefix plus the retreat attempt round from the
durable settled-round cursor and the recorded posture evidence, prices only the
actually self-moving members through ``movement_edges.quote_edge``, and treats
knocked-out companions as carried bodies: they are part of the plan's member
list but never a traveller, a speed term or a sleep refusal. Remote companions
are outside the plan entirely. Ordinary blocked/unaffordable neighbours yield
``None``; corrupt physiology or history raises by name.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from typing import Any

from world.rules.fatigue import (
    FatigueActivity,
    FatigueInterval,
    FatigueStateError,
    IntervalCompletion,
    SleepPosture,
    predict_interval,
    read_optional_fatigue_state,
    settle_fatigue_intervals,
)
from world.rules.movement_edges import (
    LocationRef,
    MovementEdgeError,
    PhysicalEdge,
    legal_edges,
    location_ref,
    quote_edge,
)
from world.rules.travel_cost import (
    MovementPreflightRefused,
    TraversalResolution,
    TraversalStatus,
    flight_waives_wilderness_charge,
    plan_traversal,
)
from world.rules.travel_plan import TravellerState

#: The two named physiology refusals a mapped flee must report, never skip.
_PHYSIOLOGY_REFUSALS = frozenset({"fatigue_state_partial", "fatigue_state_invalid"})

#: The step kind the flee action's own round-time contribution uses.
ESCAPE_CONTEXT_KEY = "escape_context"


class WorldEscapeError(ValueError):
    """A mapped escape cannot be planned or settled (named, never silent)."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True, slots=True)
class AbstractEscapeContext:
    """An explicitly abstract battlefield: flee changes eligibility only.

    Standalone combat, manual campaigns and staged simulations construct this
    context themselves. It never claims a world relocation and never resolves
    an edge, a room or a coordinate.
    """


@dataclass(frozen=True, slots=True)
class WorldEscapeContext:
    """The world context of one mapped flee at its action occurrence."""

    session_id: str
    occurred_tick: int
    source: LocationRef
    operation_id: str


@dataclass(frozen=True, slots=True)
class EscapePlan:
    """One immutable, replayable mapped escape.

    ``expected_fingerprint`` binds the selected group state and the member's
    physiology; the map owner revalidates it before any write and replays an
    existing operation receipt without another mutation.
    """

    individual_id: int
    group_id: str
    session_id: str
    operation_id: str
    occurred_tick: int
    expected_group_sequence: int
    expected_fingerprint: str
    edge: PhysicalEdge
    state_after_combat: TravellerState
    traversal: TraversalResolution
    committed_plan: dict[str, Any]


def _combat_activity(activity: str) -> FatigueActivity:
    return (
        FatigueActivity.SLEEP
        if activity == "sleep"
        else FatigueActivity.AWAKE_COMBAT
    )


def _posture_activity(posture: SleepPosture | None) -> FatigueActivity:
    return FatigueActivity.SLEEP if posture is not SleepPosture.AWAKE else FatigueActivity.AWAKE_COMBAT


def _combat_member_time(wilderness: Any, individual_id: int) -> tuple[str, Any] | None:
    """The (group id, member time) owning one member, or ``None``."""
    from world.maps import monster_activity

    try:
        state = monster_activity.read_monster_activity(wilderness)
    except monster_activity.MonsterActivityError:
        return None
    for group in state.groups.values():
        if individual_id in group.member_ids:
            return group.group_id, group.member_time[str(individual_id)]
    return None


def _project_intervals(state: Any, member_time: Any, *, through_tick: int) -> Any:
    """Fold the unpaid combat prefix onto ``state`` without writing."""
    if state is None:
        return None
    current = state
    pending: list[tuple[FatigueActivity, int]] = []
    last_end = member_time.settled_through_tick
    for interval in member_time.combat_intervals:
        pending.append((_combat_activity(interval.activity), interval.end_tick - interval.start_tick))
        last_end = interval.end_tick
    remaining = through_tick - last_end
    if remaining > 0:
        pending.append((_posture_activity(current.posture), remaining))
    for activity, seconds in pending:
        if seconds <= 0:
            continue
        current = predict_interval(
            current, activity, seconds, completion=IntervalCompletion.INDIVISIBLE
        ).end
    return current


def project_monster_combat_state(individual: Any, *, through_tick: int) -> TravellerState:
    """The member's physiology after its unpaid combat prefix (pure read)."""
    from world.maps import regional_population

    wilderness = regional_population.live_wilderness()
    state = read_optional_fatigue_state(individual)
    if state is None:
        return TravellerState(None, None, getattr(individual, "pk", None))
    if wilderness is None:
        return TravellerState.from_state(state, member_id=getattr(individual, "pk", None))
    ownership = _combat_member_time(wilderness, int(individual.pk))
    if ownership is None:
        return TravellerState.from_state(state, member_id=int(individual.pk))
    _group_id, member_time = ownership
    if member_time.mode != "combat":
        return TravellerState.from_state(state, member_id=int(individual.pk))
    projected = _project_intervals(state, member_time, through_tick=int(through_tick))
    return TravellerState.from_state(projected, member_id=int(individual.pk))


def settle_monster_combat_through(
    individual: Any, *, through_tick: int, operation_id: str
) -> TravellerState:
    """Pay exactly the member's unpaid combat prefix and advance its cursor.

    The write is idempotent: a cursor already at or beyond ``through_tick``
    pays nothing. The sole fatigue writer settles every segment; the map-owned
    member cursor then owns the interval as ``idle``, so no later generic
    settlement can repeat it. Departure immediately rewrites the mode to
    ``journey`` in the same resolver transaction.
    """
    from world.maps import monster_activity, regional_population

    wilderness = regional_population.live_wilderness()
    state = read_optional_fatigue_state(individual)
    if state is None:
        return TravellerState(None, None, getattr(individual, "pk", None))
    if wilderness is None:
        return TravellerState.from_state(state, member_id=int(individual.pk))
    ownership = _combat_member_time(wilderness, int(individual.pk))
    if ownership is None:
        return TravellerState.from_state(state, member_id=int(individual.pk))
    group_id, member_time = ownership
    if member_time.mode != "combat":
        return TravellerState.from_state(state, member_id=int(individual.pk))
    if member_time.settled_through_tick >= int(through_tick):
        return TravellerState.from_state(state, member_id=int(individual.pk))
    current = state
    for interval in member_time.combat_intervals:
        settlement = settle_fatigue_intervals(
            (
                FatigueInterval(
                    individual,
                    _combat_activity(interval.activity),
                    interval.end_tick - interval.start_tick,
                    current,
                    IntervalCompletion.INDIVISIBLE,
                ),
            ),
            context={
                "stage": "monster_combat",
                "session": member_time.session_id,
                "operation": operation_id,
            },
        )
        current = settlement.commits[0].end
    last_end = (
        member_time.combat_intervals[-1].end_tick
        if member_time.combat_intervals
        else member_time.settled_through_tick
    )
    remaining = int(through_tick) - last_end
    if remaining > 0:
        settlement = settle_fatigue_intervals(
            (
                FatigueInterval(
                    individual,
                    _posture_activity(current.posture),
                    remaining,
                    current,
                    IntervalCompletion.INDIVISIBLE,
                ),
            ),
            context={
                "stage": "monster_combat",
                "session": member_time.session_id,
                "operation": operation_id,
            },
        )
        current = settlement.commits[0].end
    # Gauge regeneration for the combat prefix belongs to this owner too: the
    # member is released to idle at ``through_tick``, after which the generic
    # clock stage deliberately skips it. Paid only after every fatigue
    # segment succeeded, and never for a dead body.
    gauge = getattr(getattr(individual, "traits", None), "hp", None)
    if gauge is not None and float(getattr(gauge, "current", 0)) > 0:
        elapsed = int(through_tick) - member_time.settled_through_tick
        if elapsed > 0:
            from world.rules.clock import settle_gauge_regeneration

            settle_gauge_regeneration((individual,), elapsed)
    monster_activity.update_member_time(
        wilderness,
        group_id=group_id,
        individual_id=int(individual.pk),
        member_time=monster_activity.MemberTime(
            int(through_tick), monster_activity.MODE_IDLE, None, ()
        ),
    )
    return TravellerState.from_state(current, member_id=int(individual.pk))


def _commitment(candidates: tuple[PhysicalEdge, ...], seed_hex: str) -> PhysicalEdge:
    """Pick one candidate deterministically inside the engagement's scope."""
    digest = hashlib.sha256(seed_hex.encode("utf-8")).digest()
    index = int.from_bytes(digest[:8], "big") % len(candidates)
    return candidates[index]


def build_journey_plan(
    actors: Any,
    traversal: TraversalResolution,
    states: Any,
) -> dict[str, Any]:
    """Build the persisted plan from the canonical traversal calculator.

    ``actors`` and ``states`` are parallel sequences: one live body and its
    detached physiology per committed traveller. The whole group is priced by
    the same integrated calculator execution uses, so a cohesive departure
    travels at the slowest actual member rather than an averaged speed.
    """
    from world.maps import monster_activity

    actors = tuple(actors)
    states = tuple(states)
    if not actors or len(actors) != len(states):
        raise ValueError("a journey plan needs one state per actor")
    waived = bool(traversal.cost_key) and flight_waives_wilderness_charge(
        actors[0], traversal.cost_key
    )
    if traversal.status is TraversalStatus.RESOLVED and traversal.cost is not None:
        legs = ((traversal.cost.distance_m, traversal.cost.terrain),)
        integrated = plan_traversal(legs, tuple(state.detached() for state in states))
        seconds = int(traversal.cost.seconds)
        plan = monster_activity.JourneyPlan(
            seconds=seconds,
            distance_m=integrated.distance_m,
            terrain_legs=(
                monster_activity.PlanLeg(integrated.distance_m, traversal.cost.terrain),
            ),
            segments=tuple(
                monster_activity.PlanSegment(
                    segment.seconds, segment.distance_m, segment.speed_m_per_hour
                )
                for segment in integrated.segments
            ),
            members=(),
        )
    else:
        # An authored non-distance connector has no physical distance; its
        # committed duration is the one authored clock default execution uses.
        from world.rules.clock import CLOCK_YAML

        authored = CLOCK_YAML.get("command_defaults", {}).get(
            traversal.cost_key or "", 0
        )
        seconds = int(authored) if isinstance(authored, int) else 0
        plan = monster_activity.JourneyPlan(
            seconds=seconds,
            distance_m=Fraction(0),
            terrain_legs=(),
            segments=(),
            members=(),
        )
    members = []
    for actor, state in zip(actors, states):
        activity = (
            monster_activity.ACTIVITY_SLEEP
            if state.posture is not None and state.posture is not SleepPosture.AWAKE
            else monster_activity.ACTIVITY_AWAKE_COMBAT
        )
        members.append(
            monster_activity.PlanMember(
                individual_id=int(actor.pk),
                reserve_units=state.reserve_units,
                posture=None if state.posture is None else str(state.posture),
                activity=activity,
                waived=waived,
            )
        )
    plan = monster_activity.JourneyPlan(
        seconds=plan.seconds,
        distance_m=plan.distance_m,
        terrain_legs=plan.terrain_legs,
        segments=plan.segments,
        members=tuple(members),
    )
    return monster_activity.plan_to_dict(plan)


def _journey_plan(
    actor: Any,
    traversal: TraversalResolution,
    state: TravellerState,
) -> dict[str, Any]:
    """The single-member escape plan (the shared builder's one-traveller form)."""
    return build_journey_plan((actor,), traversal, (state,))


def plan_individual_escape(
    actor: Any, battlefield: Any, context: WorldEscapeContext
) -> EscapePlan | None:
    """Plan one mapped escape, or ``None`` when no lawful route exists.

    Corrupt state (a half-written fatigue pair, an unreadable owner record)
    raises :class:`WorldEscapeError`; ordinary blocked, locked or unaffordable
    neighbours simply contribute no candidate.
    """
    del battlefield  # the contest is the resolver handler's; this is physical
    if not isinstance(context, WorldEscapeContext):
        raise WorldEscapeError(
            "missing_world_context", "a mapped escape needs a world escape context"
        )
    from world.maps import monster_activity, regional_population

    wilderness = regional_population.live_wilderness()
    if wilderness is None:
        return None
    if not monster_activity.activity_provisioned(wilderness):
        return None
    try:
        state = monster_activity.read_monster_activity(wilderness)
    except monster_activity.MonsterActivityError as error:
        raise WorldEscapeError(error.reason, error.detail) from error
    individual_id = int(actor.pk)
    group = next(
        (
            candidate
            for candidate in state.groups.values()
            if individual_id in candidate.member_ids
        ),
        None,
    )
    if group is None or group.journey_id is not None:
        return None
    if group.position != context.source:
        return None
    if individual_id not in group.member_ids:
        return None
    try:
        projected = project_monster_combat_state(
            actor, through_tick=int(context.occurred_tick)
        )
    except FatigueStateError as error:
        raise WorldEscapeError(error.reason, str(error)) from error
    edges = legal_edges(actor, context.source, (actor,))
    candidates: list[tuple[PhysicalEdge, TraversalResolution]] = []
    for edge in edges:
        try:
            resolution = quote_edge(
                actor, edge, (actor,), states=(projected,)
            )
        except MovementPreflightRefused as error:
            if error.reason in _PHYSIOLOGY_REFUSALS:
                raise WorldEscapeError(error.reason, str(error)) from error
            continue
        if resolution.status is TraversalStatus.UNRESOLVED:
            continue
        if resolution.status is TraversalStatus.RESOLVED and (
            resolution.cost is None or resolution.cost.seconds < 0
        ):
            continue
        candidates.append((edge, resolution))
    if not candidates:
        return None
    ordered = tuple(sorted(candidates, key=lambda item: _edge_key(item[0])))
    seed_hex = (
        f"{context.session_id}:{context.occurred_tick}:{individual_id}:{group.group_id}"
    )
    edge, resolution = _commitment(ordered, seed_hex)
    fingerprint = monster_activity.group_fingerprint(group, actor)
    committed_plan = _journey_plan(actor, resolution, projected)
    return EscapePlan(
        individual_id=individual_id,
        group_id=group.group_id,
        session_id=context.session_id,
        operation_id=context.operation_id,
        occurred_tick=int(context.occurred_tick),
        expected_group_sequence=group.sequence,
        expected_fingerprint=fingerprint,
        edge=edge,
        state_after_combat=projected,
        traversal=resolution,
        committed_plan=committed_plan,
    )


def _edge_key(edge: PhysicalEdge) -> str:
    return f"{edge.route}:{edge.destination.kind}:{edge.destination.id}"


@dataclass(frozen=True, slots=True)
class PartyRetreatPlan:
    """One immutable, replayable whole-party retreat route.

    ``member_ids`` is every present body of the commander's source team (the
    complete physical party, knocked-out companions included).
    ``self_moving_ids`` is the subset that actually walks: alive present members
    that are not knocked out. Only those members price the route and determine
    its speed; ``carried_ids`` are transported without walking, without a
    sleep refusal and without inventing physiology. ``states_after_attempt`` is
    parallel to ``self_moving_ids`` and is the detached physiology the canonical
    movement quote was priced from.
    """

    edge: PhysicalEdge
    member_ids: tuple[int, ...]
    self_moving_ids: tuple[int, ...]
    carried_ids: tuple[int, ...]
    states_after_attempt: tuple[TravellerState, ...]
    traversal: TraversalResolution
    depart_tick: int
    operation_id: str


def _present_team_bodies(battlefield: Any, commander: Any) -> tuple[Any, ...]:
    """The commander's present, non-fled source team bodies in roster order."""
    from world.rules.combat_identity import stable_actor_id

    team = battlefield.team_of(stable_actor_id(commander))
    if team is None:
        return ()
    bodies = []
    for key in sorted(battlefield.teams.get(team, frozenset())):
        entity = battlefield.roster.get(key)
        if entity is None or key in battlefield.fled:
            continue
        bodies.append(entity)
    return tuple(bodies)


def _stored_hp(entity: Any) -> float:
    try:
        return float(getattr(entity.traits.hp, "current", 0))
    except (AttributeError, TypeError, ValueError):  # observability: ignore R2: a body without a readable gauge is not self-moving; carried planning never fabricates health
        return 0.0


def _project_retreat_state(record: Any, body: Any) -> TravellerState:
    """The member's physiology after its unpaid combat prefix and the attempt.

    The completed unpaid prefix replays the durable recorded posture evidence
    from ``settled_rounds``; the attempt is one live-posture six-second round,
    exactly the interval the confirmed retreat pays. Nothing is written.
    """
    from world.rules.combat import COMBAT_YAML
    from world.rules.combat_session.settlement import posture_segments

    member_id = int(body.pk)
    current = read_optional_fatigue_state(body)
    if current is None:
        return TravellerState(None, None, member_id)
    try:
        segments = posture_segments(
            record,
            member_id,
            from_round=int(record.settled_rounds),
            through_round=int(record.rounds_elapsed),
        )
    except ValueError as error:
        raise WorldEscapeError("combat_prefix_invalid", str(error)) from error
    segments = (*segments, (current.posture is not SleepPosture.AWAKE, int(COMBAT_YAML["round"]["seconds"])))
    sleeping_posture = (
        current.posture if current.posture is not SleepPosture.AWAKE else SleepPosture.FORCED
    )
    first_asleep = segments[0][0]
    from world.rules.fatigue import FatigueState

    if first_asleep and current.posture is SleepPosture.AWAKE:
        current = FatigueState(current.reserve_units, sleeping_posture)
    elif not first_asleep and current.posture is not SleepPosture.AWAKE:
        current = FatigueState(current.reserve_units, SleepPosture.AWAKE)
    for asleep, seconds in segments:
        target = sleeping_posture if asleep else SleepPosture.AWAKE
        if current.posture is not target:
            current = FatigueState(current.reserve_units, target)
        if seconds <= 0:
            continue
        current = predict_interval(
            current,
            FatigueActivity.SLEEP if asleep else FatigueActivity.AWAKE_COMBAT,
            seconds,
            completion=IntervalCompletion.INDIVISIBLE,
        ).end
    return TravellerState.from_state(current, member_id=member_id)


def _preferred_index(
    candidates: tuple[tuple[PhysicalEdge, TraversalResolution], ...],
    preferred: PhysicalEdge | None,
) -> int | None:
    """The preferred route's index inside the legal affordable candidates."""
    if preferred is None:
        return None
    for index, (edge, _resolution) in enumerate(candidates):
        if edge == preferred:
            return index
    return None


def plan_party_retreat(
    commander: Any,
    record: Any,
    battlefield: Any,
    *,
    operation_id: str,
    preferred: PhysicalEdge | None,
) -> PartyRetreatPlan | None:
    """Plan one confirmed whole-party retreat, or ``None`` when no route exists.

    The plan is read-only and exact: it projects every present member's unpaid
    combat prefix plus the attempt round, prices the full route for every
    actually self-moving member through the canonical ``quote_edge`` calculator
    (so fatigue speed changes, exact-zero arrival and authorized waivers are
    execution arithmetic), and lets a broken path be an ordinary gameplay
    failure. A malformed fatigue pair, an unreadable history record or broken
    authored geometry raises :class:`WorldEscapeError` instead.

    ``preferred`` is the server-captured reverse of the party's last completed
    edge; when it is still legal and affordable it is taken, otherwise the
    deterministic operation-scoped commitment among every other lawful
    affordable neighbour decides. No safe/monster-free preference is applied.
    """
    if battlefield is None:
        return None
    from world.rules.combat_identity import stable_actor_id
    from world.rules.player_control import is_player_driven

    if not is_player_driven(commander):
        return None
    try:
        source = location_ref(commander)
    except MovementEdgeError as error:
        raise WorldEscapeError("location_unavailable", str(error)) from error
    bodies = _present_team_bodies(battlefield, commander)
    if not bodies:
        return None
    knocked = set(int(pk) for pk in record.knocked_out_ids)
    for key, entity in battlefield.roster.items():
        if key in battlefield.knocked_out:
            pk = getattr(entity, "pk", None)
            if isinstance(pk, int) and not isinstance(pk, bool):
                knocked.add(pk)
    self_moving = tuple(
        body
        for body in bodies
        if int(body.pk) not in knocked and _stored_hp(body) > 0
    )
    carried = tuple(body for body in bodies if body not in self_moving)
    if not self_moving:
        return None
    try:
        projected = tuple(_project_retreat_state(record, body) for body in self_moving)
    except FatigueStateError as error:
        raise WorldEscapeError(error.reason, str(error)) from error
    if any(
        state.posture is not None and state.posture is not SleepPosture.AWAKE
        for state in projected
    ):
        # A non-knocked-out sleeper keeps the ordinary sleep movement
        # restriction; the whole route is an ordinary unaffordable failure.
        return None
    try:
        edges = legal_edges(commander, source, self_moving)
    except MovementEdgeError as error:
        raise WorldEscapeError("movement_edge_invalid", str(error)) from error
    candidates: list[tuple[PhysicalEdge, TraversalResolution]] = []
    for edge in edges:
        try:
            resolution = quote_edge(
                commander, edge, self_moving, states=projected
            )
        except MovementPreflightRefused as error:
            if error.reason in _PHYSIOLOGY_REFUSALS:
                raise WorldEscapeError(error.reason, str(error)) from error
            continue
        except MovementEdgeError as error:
            raise WorldEscapeError("movement_edge_invalid", str(error)) from error
        if resolution.status is TraversalStatus.UNRESOLVED:
            continue
        if resolution.status is TraversalStatus.RESOLVED and (
            resolution.cost is None or resolution.cost.seconds < 0
        ):
            continue
        candidates.append((edge, resolution))
    if not candidates:
        return None
    ordered = tuple(sorted(candidates, key=lambda item: _edge_key(item[0])))
    index = _preferred_index(ordered, preferred)
    if index is None:
        seed = (
            f"{operation_id}:{stable_actor_id(commander)}:"
            f"{record.session_id}:{int(record.rounds_elapsed)}"
        )
        index = int.from_bytes(
            hashlib.sha256(seed.encode("utf-8")).digest()[:8], "big"
        ) % len(ordered)
    edge, resolution = ordered[index]
    clock = None
    try:
        from world.rules.clock import read_world_clock

        clock = read_world_clock()
    except Exception:  # observability: ignore R2: the departure tick is telemetry; a missing clock degrades to the session's own elapsed boundary
        clock = None
    if clock is not None:
        depart_tick = int(clock.tick) + (
            int(record.rounds_elapsed) + 1 - int(record.settled_rounds)
        ) * 6
    else:
        depart_tick = int(record.started_tick) + (
            int(record.rounds_elapsed) + 1
        ) * 6
    return PartyRetreatPlan(
        edge=edge,
        member_ids=tuple(sorted(int(body.pk) for body in bodies)),
        self_moving_ids=tuple(int(body.pk) for body in self_moving),
        carried_ids=tuple(sorted(int(body.pk) for body in carried)),
        states_after_attempt=projected,
        traversal=resolution,
        depart_tick=depart_tick,
        operation_id=operation_id,
    )


__all__ = [
    "ESCAPE_CONTEXT_KEY",
    "AbstractEscapeContext",
    "EscapePlan",
    "PartyRetreatPlan",
    "WorldEscapeContext",
    "WorldEscapeError",
    "build_journey_plan",
    "plan_individual_escape",
    "plan_party_retreat",
    "project_monster_combat_state",
    "settle_monster_combat_through",
]
