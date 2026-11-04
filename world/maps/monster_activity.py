"""Durable map-owned monster groups, journeys and operation receipts.

This is the sole writer of ``wilderness.db.monster_activity``. The record owns
the actual group membership an individual belongs to, the one journey it may be
taking, the per-member physiology cursors that say which interval already
belongs to whom, and the operation receipts that make a replay of one
already-committed operation a no-op.

Nothing here decides ordinary activity: a group is either idle at its position
or in its one journey. Construction owners create the initial groups, the
resolver's escape path begins a journey, and the merged population lifecycle
settles journeys at their chronological boundaries.

The persisted shapes are strict. Every codec rejects an unknown or missing key,
a boolean where a tick is expected, or a fraction that is not canonical, and a
missing or malformed record in an already provisioned world refuses by the
named ``monster_activity_state_invalid`` reason instead of being reset.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from math import gcd
from typing import Any, Iterable, Mapping, Sequence

from django.db import transaction

from world.observability import log_info, log_warn
from world.rules.clock import ScheduledEvent, SurfaceSnapshot
from world.rules.movement_edges import (
    LocationRef,
    MovementEdgeError,
    PhysicalEdge,
    decode_location_ref,
    decode_physical_edge,
    encode_location_ref,
    encode_physical_edge,
    legal_edges,
    quote_edge,
)
from world.rules.travel_cost import (
    MovementPreflightRefused,
    TraversalStatus,
)

#: The wilderness Attribute this owner writes and reads.
MONSTER_ACTIVITY_ATTRIBUTE = "monster_activity"

#: The named refusal for a missing or malformed owner record.
STATE_INVALID = "monster_activity_state_invalid"

#: Owner kinds a group may declare.
OWNER_KINDS = ("zone", "site", "quest", "explicit")

#: The three member-time modes. Exactly one mode owns a member's interval.
MODE_IDLE = "idle"
MODE_COMBAT = "combat"
MODE_JOURNEY = "journey"
MEMBER_MODES = (MODE_IDLE, MODE_COMBAT, MODE_JOURNEY)

#: The closed combat-posture activity vocabulary of a recorded combat interval.
ACTIVITY_AWAKE_COMBAT = "awake_combat"
ACTIVITY_SLEEP = "sleep"
COMBAT_ACTIVITIES = (ACTIVITY_AWAKE_COMBAT, ACTIVITY_SLEEP)

#: The staged-construction binding. GM, quest and staged-exam construction
#: owners create their group with this explicit stationary binding and this
#: positive decision interval; no authored ecology declaration is inferred.
STAGED_STATIONARY_ACTIVITY = "stationary"
STAGED_DECISION_INTERVAL = 120

#: The positive fallback interval of a group whose explicitly recorded binding
#: has no published declaration in this tree. The binding itself is never
#: changed or inferred from member rows; the fallback only keeps a decision
#: loop from ever becoming zero-time. Activity scheduling refuses an unknown
#: published binding rather than moving it.
DEFAULT_DECISION_INTERVAL = 60

#: The departure receipt kind this owner writes.
RECEIPT_DEPARTURE = "departure"

#: The one draw purpose an ordinary activity decision consumes.
DECISION_PURPOSE = "activity"

#: The outcome reason of a committed departure (or a stay chosen by the saved
#: selection). Every other stay reason names why no lawful group route exists.
DECISION_DEPART = "depart"
DECISION_STAY = "stay"
STAY_STATIONARY = "stationary"
STAY_IN_JOURNEY = "in_journey"
STAY_UNPUBLISHED_BINDING = "unpublished_binding"
STAY_NO_LIVING_MEMBERS = "no_living_members"
STAY_MEMBER_ENGAGED = "member_engaged"
STAY_MEMBER_DISPLACED = "member_displaced"
STAY_MEMBER_SETTLED_AHEAD = "member_settled_ahead"
STAY_NO_LEGAL_ROUTE = "no_legal_route"
STAY_MEMBER_SLEEPING = "member_sleeping"
STAY_MEMBER_UNAFFORDABLE = "member_unaffordable"
STAY_MEMBER_BLOCKED = "member_blocked"
STAY_OUTSIDE_BOUNDS_WAITING = "outside_bounds_waiting"

#: The bounded number of posture segments one idle interval may commit.
_MAX_POSTURE_SEGMENTS = 64

_STATE_FIELDS = frozenset(
    {"groups", "journeys", "receipts", "room_protection", "settled_through_tick"}
)
_GROUP_FIELDS = frozenset(
    {
        "member_ids",
        "home_owner",
        "activity_key",
        "home",
        "position",
        "journey_id",
        "next_decision_tick",
        "sequence",
        "seed",
        "member_time",
    }
)
_MEMBER_TIME_FIELDS = frozenset(
    {"settled_through_tick", "mode", "session_id", "combat_intervals"}
)
_COMBAT_INTERVAL_FIELDS = frozenset({"start_tick", "end_tick", "activity"})
_JOURNEY_FIELDS = frozenset(
    {
        "group_id",
        "member_ids",
        "source",
        "destination",
        "depart_tick",
        "arrival_tick",
        "settled_through_tick",
        "retry_tick",
        "edge",
        "plan",
    }
)
_PLAN_FIELDS = frozenset(
    {"seconds", "distance_m", "terrain_legs", "segments", "members"}
)
_PLAN_LEG_FIELDS = frozenset({"distance_m", "terrain"})
_PLAN_SEGMENT_FIELDS = frozenset({"seconds", "distance_m", "speed_m_per_hour"})
_PLAN_MEMBER_FIELDS = frozenset(
    {"individual_id", "reserve_units", "posture", "activity", "waived"}
)
_RECEIPT_FIELDS = frozenset(
    {
        "operation_id",
        "kind",
        "group_id",
        "journey_id",
        "individual_id",
        "occurred_tick",
    }
)
_ROOM_PROTECTION_FIELDS = frozenset(
    {"session_id", "location", "start_tick", "end_tick"}
)


class MonsterActivityError(ValueError):
    """An owner record, operation or boundary violates the durable contract."""

    def __init__(self, reason: str, detail: str = "") -> None:
        message = reason if not detail else f"{reason}: {detail}"
        super().__init__(message)
        self.reason = reason
        self.detail = detail


class MonsterActivityStateInvalid(MonsterActivityError):
    """The durable owner record is missing, malformed or inconsistent."""


class MonsterActivityOperationInvalid(MonsterActivityError):
    """One requested owner operation is not lawful in the current state."""


def _invalid(detail: str) -> MonsterActivityStateInvalid:
    return MonsterActivityStateInvalid(STATE_INVALID, detail)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_int(value: Any, what: str, minimum: int = 0) -> int:
    if not _is_int(value) or value < minimum:
        raise _invalid(f"{what} must be an integer >= {minimum}, got {value!r}")
    return value


def _require_name(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise _invalid(f"{what} must be a nonempty string, got {value!r}")
    return value


def _require_keys(value: Any, fields: frozenset[str], what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise _invalid(f"{what} must have exactly the keys {sorted(fields)}")
    return value


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


# ---------------------------------------------------------------------------
# Fractions


def encode_fraction(value: Fraction) -> list[int]:
    """The canonical ``[numerator, denominator]`` pair of one exact fraction.

    A negative or zero denominator, or a non-reduced pair, is never produced
    here: the value is normalized once at the single serialization point.
    """
    if not isinstance(value, Fraction):
        raise TypeError(f"expected a Fraction, got {value!r}")
    if value < 0:
        raise ValueError("a persisted fraction must not be negative")
    numerator, denominator = value.numerator, value.denominator
    if denominator <= 0:
        raise ValueError("a persisted fraction needs a positive denominator")
    return [numerator, denominator]


def decode_fraction(value: Any, what: str) -> Fraction:
    """Parse one canonical fraction pair; every other shape is malformed."""
    if (
        not _is_sequence(value)
        or len(value) != 2
        or not _is_int(value[0])
        or not _is_int(value[1])
    ):
        raise _invalid(f"{what} must be one integer [numerator, denominator] pair")
    numerator, denominator = value[0], value[1]
    if numerator < 0 or denominator <= 0:
        raise _invalid(f"{what} must be nonnegative over a positive denominator")
    if gcd(numerator, denominator) != 1 and numerator != 0:
        raise _invalid(f"{what} must be in canonical reduced form")
    return Fraction(numerator, denominator)


# ---------------------------------------------------------------------------
# Record types


@dataclass(frozen=True, slots=True)
class CombatInterval:
    """One already-completed combat posture interval of one member."""

    start_tick: int
    end_tick: int
    activity: str


@dataclass(frozen=True, slots=True)
class MemberTime:
    """One member's physiology ownership cursor and pending combat evidence.

    ``settled_through_tick`` is the last settled instant; the member's live
    physiology is exactly the state at that cursor. ``combat_intervals`` hold
    the recorded completed posture intervals that are still unpaid, in order,
    starting at the cursor.
    """

    settled_through_tick: int
    mode: str
    session_id: str | None
    combat_intervals: tuple[CombatInterval, ...] = ()


@dataclass(frozen=True, slots=True)
class MonsterGroup:
    """One durable movement group and its per-member cursors."""

    group_id: str
    member_ids: tuple[int, ...]
    home_owner: tuple[str, str]
    activity_key: str
    home: LocationRef
    position: LocationRef | None
    journey_id: str | None
    next_decision_tick: int
    sequence: int
    seed: int
    member_time: Mapping[str, MemberTime] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PlanLeg:
    distance_m: Fraction
    terrain: str


@dataclass(frozen=True, slots=True)
class PlanSegment:
    seconds: Fraction
    distance_m: Fraction
    speed_m_per_hour: Fraction


@dataclass(frozen=True, slots=True)
class PlanMember:
    """One journey member's committed departure state and waiver."""

    individual_id: int
    reserve_units: int | None
    posture: str | None
    activity: str
    waived: bool


@dataclass(frozen=True, slots=True)
class JourneyPlan:
    """The exact committed traversal plan of one journey."""

    seconds: int
    distance_m: Fraction
    terrain_legs: tuple[PlanLeg, ...]
    segments: tuple[PlanSegment, ...]
    members: tuple[PlanMember, ...]


@dataclass(frozen=True, slots=True)
class MonsterJourney:
    """One durable passage from a source locator to a destination locator."""

    journey_id: str
    group_id: str
    member_ids: tuple[int, ...]
    source: LocationRef
    destination: LocationRef
    depart_tick: int
    arrival_tick: int
    settled_through_tick: int
    retry_tick: int | None
    edge: PhysicalEdge
    plan: JourneyPlan


@dataclass(frozen=True, slots=True)
class ActivityReceipt:
    """One committed owner operation's replay evidence."""

    operation_id: str
    kind: str
    group_id: str
    journey_id: str | None
    individual_id: int | None
    occurred_tick: int


@dataclass(frozen=True, slots=True)
class ActivityDecision:
    """One scheduled ordinary group decision.

    ``edge`` is ``None`` for a committed stay (the saved selection or a
    lawful refusal); otherwise it names the one route the whole group takes.
    ``expected_sequence`` binds the plan to the group state it was read from,
    so a stale decision can never displace a newer one.
    """

    group_id: str
    tick: int
    expected_sequence: int
    edge: PhysicalEdge | None
    reason: str


@dataclass(frozen=True, slots=True)
class RoomProtection:
    """One persistent authored room's protected interval."""

    session_id: str
    location: LocationRef
    start_tick: int
    end_tick: int | None


@dataclass(frozen=True, slots=True)
class MonsterActivityState:
    """The complete durable owner record of one wilderness world."""

    groups: Mapping[str, MonsterGroup]
    journeys: Mapping[str, MonsterJourney]
    receipts: Mapping[str, ActivityReceipt]
    room_protection: tuple[RoomProtection, ...]
    settled_through_tick: int


# ---------------------------------------------------------------------------
# Codecs


def _fraction_to_value(value: Fraction) -> list[int]:
    return encode_fraction(value)


def _plan_leg_to_dict(leg: PlanLeg) -> dict[str, Any]:
    return {"distance_m": _fraction_to_value(leg.distance_m), "terrain": leg.terrain}


def _plan_segment_to_dict(segment: PlanSegment) -> dict[str, Any]:
    return {
        "seconds": _fraction_to_value(segment.seconds),
        "distance_m": _fraction_to_value(segment.distance_m),
        "speed_m_per_hour": _fraction_to_value(segment.speed_m_per_hour),
    }


def _plan_member_to_dict(member: PlanMember) -> dict[str, Any]:
    return {
        "individual_id": member.individual_id,
        "reserve_units": member.reserve_units,
        "posture": member.posture,
        "activity": member.activity,
        "waived": member.waived,
    }


def plan_to_dict(plan: JourneyPlan) -> dict[str, Any]:
    """The exact persisted journey plan mapping."""
    if not isinstance(plan, JourneyPlan):
        raise TypeError(f"expected a JourneyPlan, got {plan!r}")
    return {
        "seconds": plan.seconds,
        "distance_m": _fraction_to_value(plan.distance_m),
        "terrain_legs": [_plan_leg_to_dict(leg) for leg in plan.terrain_legs],
        "segments": [_plan_segment_to_dict(s) for s in plan.segments],
        "members": [_plan_member_to_dict(m) for m in plan.members],
    }


def plan_from_dict(value: Any) -> JourneyPlan:
    """Parse one exact persisted journey plan mapping."""
    data = _require_keys(value, _PLAN_FIELDS, "journey plan")
    seconds = _require_int(data["seconds"], "plan seconds")
    distance = decode_fraction(data["distance_m"], "plan distance_m")
    legs_raw = data["terrain_legs"]
    segments_raw = data["segments"]
    members_raw = data["members"]
    if not (_is_sequence(legs_raw) and _is_sequence(segments_raw) and _is_sequence(members_raw)):
        raise _invalid("journey plan legs, segments and members must be lists")
    legs: list[PlanLeg] = []
    for leg in legs_raw:
        leg_data = _require_keys(leg, _PLAN_LEG_FIELDS, "plan leg")
        legs.append(
            PlanLeg(
                decode_fraction(leg_data["distance_m"], "plan leg distance_m"),
                _require_name(leg_data["terrain"], "plan leg terrain"),
            )
        )
    segments: list[PlanSegment] = []
    for segment in segments_raw:
        segment_data = _require_keys(segment, _PLAN_SEGMENT_FIELDS, "plan segment")
        speed = decode_fraction(
            segment_data["speed_m_per_hour"], "plan segment speed_m_per_hour"
        )
        if speed <= 0:
            raise _invalid("a plan segment speed must be positive")
        segments.append(
            PlanSegment(
                decode_fraction(segment_data["seconds"], "plan segment seconds"),
                decode_fraction(segment_data["distance_m"], "plan segment distance_m"),
                speed,
            )
        )
    members: list[PlanMember] = []
    seen: set[int] = set()
    for member in members_raw:
        member_data = _require_keys(member, _PLAN_MEMBER_FIELDS, "plan member")
        individual_id = _require_int(
            member_data["individual_id"], "plan member individual_id", 1
        )
        if individual_id in seen:
            raise _invalid("a plan member appears twice")
        seen.add(individual_id)
        reserve = member_data["reserve_units"]
        posture = member_data["posture"]
        if (reserve is None) != (posture is None):
            raise _invalid("a plan member's optional physiology halves must be null together")
        if reserve is not None:
            reserve = _require_int(reserve, "plan member reserve_units")
            posture = _require_name(posture, "plan member posture")
        activity = member_data["activity"]
        if activity not in COMBAT_ACTIVITIES:
            raise _invalid(f"unknown plan member activity {activity!r}")
        waived = member_data["waived"]
        if not isinstance(waived, bool):
            raise _invalid("plan member waived must be a boolean")
        members.append(PlanMember(individual_id, reserve, posture, activity, waived))
    return JourneyPlan(seconds, distance, tuple(legs), tuple(segments), tuple(members))


def _member_time_to_dict(member_time: MemberTime) -> dict[str, Any]:
    return {
        "settled_through_tick": member_time.settled_through_tick,
        "mode": member_time.mode,
        "session_id": member_time.session_id,
        "combat_intervals": [
            {
                "start_tick": interval.start_tick,
                "end_tick": interval.end_tick,
                "activity": interval.activity,
            }
            for interval in member_time.combat_intervals
        ],
    }


def _member_time_from_dict(
    value: Any, *, cursor_floor: int, what: str
) -> MemberTime:
    data = _require_keys(value, _MEMBER_TIME_FIELDS, what)
    settled = _require_int(data["settled_through_tick"], f"{what} settled_through_tick")
    if settled < cursor_floor:
        raise _invalid(f"{what} settled_through_tick regresses below the group cursor")
    mode = data["mode"]
    if mode not in MEMBER_MODES:
        raise _invalid(f"{what} has unknown mode {mode!r}")
    session_id = data["session_id"]
    if session_id is not None:
        _require_name(session_id, f"{what} session_id")
    intervals_raw = data["combat_intervals"]
    if not _is_sequence(intervals_raw):
        raise _invalid(f"{what} combat_intervals must be a list")
    intervals: list[CombatInterval] = []
    expected_start = settled
    for interval in intervals_raw:
        interval_data = _require_keys(interval, _COMBAT_INTERVAL_FIELDS, f"{what} interval")
        start = _require_int(interval_data["start_tick"], f"{what} interval start")
        end = _require_int(interval_data["end_tick"], f"{what} interval end")
        if start != expected_start or end < start:
            raise _invalid(f"{what} combat intervals must be ordered, disjoint and start at the cursor")
        activity = interval_data["activity"]
        if activity not in COMBAT_ACTIVITIES:
            raise _invalid(f"{what} interval has unknown activity {activity!r}")
        intervals.append(CombatInterval(start, end, activity))
        expected_start = end
    return MemberTime(settled, mode, session_id, tuple(intervals))


def group_to_dict(group: MonsterGroup) -> dict[str, Any]:
    """The exact persisted group mapping."""
    if not isinstance(group, MonsterGroup):
        raise TypeError(f"expected a MonsterGroup, got {group!r}")
    return {
        "member_ids": list(group.member_ids),
        "home_owner": {"kind": group.home_owner[0], "key": group.home_owner[1]},
        "activity_key": group.activity_key,
        "home": encode_location_ref(group.home),
        "position": None if group.position is None else encode_location_ref(group.position),
        "journey_id": group.journey_id,
        "next_decision_tick": group.next_decision_tick,
        "sequence": group.sequence,
        "seed": group.seed,
        "member_time": {
            key: _member_time_to_dict(value) for key, value in group.member_time.items()
        },
    }


def group_from_dict(group_id: str, value: Any) -> MonsterGroup:
    """Parse one exact persisted group mapping."""
    what = f"group {group_id!r}"
    data = _require_keys(value, _GROUP_FIELDS, what)
    member_ids_raw = data["member_ids"]
    if not _is_sequence(member_ids_raw) or not member_ids_raw:
        raise _invalid(f"{what} must list its members")
    member_ids = tuple(
        _require_int(member_id, f"{what} member_id", 1) for member_id in member_ids_raw
    )
    if len(set(member_ids)) != len(member_ids):
        raise _invalid(f"{what} lists one member twice")
    owner = _require_keys(data["home_owner"], frozenset({"kind", "key"}), f"{what} home_owner")
    kind = owner["kind"]
    if kind not in OWNER_KINDS:
        raise _invalid(f"{what} has unknown owner kind {kind!r}")
    key = _require_name(owner["key"], f"{what} home_owner key")
    activity_key = _require_name(data["activity_key"], f"{what} activity_key")
    home = decode_location_ref(data["home"])
    position_raw = data["position"]
    position = None if position_raw is None else decode_location_ref(position_raw)
    journey_id = data["journey_id"]
    if journey_id is not None:
        _require_name(journey_id, f"{what} journey_id")
    if (position is None) == (journey_id is None):
        raise _invalid(f"{what} is either idle at a position or in one journey")
    next_decision_tick = _require_int(
        data["next_decision_tick"], f"{what} next_decision_tick"
    )
    sequence = _require_int(data["sequence"], f"{what} sequence")
    seed = data["seed"]
    if not _is_int(seed):
        raise _invalid(f"{what} seed must be an integer")
    member_time_raw = data["member_time"]
    if not isinstance(member_time_raw, Mapping):
        raise _invalid(f"{what} member_time must be a mapping")
    if set(member_time_raw) != {str(member_id) for member_id in member_ids}:
        raise _invalid(f"{what} member_time keys must be exactly its member IDs")
    member_time = {
        key: _member_time_from_dict(
            value,
            cursor_floor=0,
            what=f"{what} member_time[{key!r}]",
        )
        for key, value in member_time_raw.items()
    }
    return MonsterGroup(
        group_id=group_id,
        member_ids=member_ids,
        home_owner=(kind, key),
        activity_key=activity_key,
        home=home,
        position=position,
        journey_id=journey_id,
        next_decision_tick=next_decision_tick,
        sequence=sequence,
        seed=seed,
        member_time=member_time,
    )


def journey_to_dict(journey: MonsterJourney) -> dict[str, Any]:
    """The exact persisted journey mapping."""
    if not isinstance(journey, MonsterJourney):
        raise TypeError(f"expected a MonsterJourney, got {journey!r}")
    return {
        "group_id": journey.group_id,
        "member_ids": list(journey.member_ids),
        "source": encode_location_ref(journey.source),
        "destination": encode_location_ref(journey.destination),
        "depart_tick": journey.depart_tick,
        "arrival_tick": journey.arrival_tick,
        "settled_through_tick": journey.settled_through_tick,
        "retry_tick": journey.retry_tick,
        "edge": encode_physical_edge(journey.edge),
        "plan": plan_to_dict(journey.plan),
    }


def journey_from_dict(journey_id: str, value: Any) -> MonsterJourney:
    """Parse one exact persisted journey mapping."""
    what = f"journey {journey_id!r}"
    data = _require_keys(value, _JOURNEY_FIELDS, what)
    group_id = _require_name(data["group_id"], f"{what} group_id")
    member_ids_raw = data["member_ids"]
    if not _is_sequence(member_ids_raw) or not member_ids_raw:
        raise _invalid(f"{what} must list its members")
    member_ids = tuple(
        _require_int(member_id, f"{what} member_id", 1) for member_id in member_ids_raw
    )
    if len(set(member_ids)) != len(member_ids):
        raise _invalid(f"{what} lists one member twice")
    source = decode_location_ref(data["source"])
    destination = decode_location_ref(data["destination"])
    depart_tick = _require_int(data["depart_tick"], f"{what} depart_tick")
    arrival_tick = _require_int(data["arrival_tick"], f"{what} arrival_tick")
    if arrival_tick < depart_tick:
        raise _invalid(f"{what} arrives before it departs")
    settled = _require_int(data["settled_through_tick"], f"{what} settled_through_tick")
    if settled < depart_tick:
        raise _invalid(f"{what} settled_through_tick precedes departure")
    retry_raw = data["retry_tick"]
    retry_tick = None if retry_raw is None else _require_int(retry_raw, f"{what} retry_tick")
    edge = decode_physical_edge(data["edge"])
    if edge.source != source or edge.destination != destination:
        raise _invalid(f"{what} edge endpoints must match its source and destination")
    plan = plan_from_dict(data["plan"])
    if plan.seconds != arrival_tick - depart_tick:
        raise _invalid(f"{what} plan seconds must equal its committed duration")
    if {member.individual_id for member in plan.members} != set(member_ids):
        raise _invalid(f"{what} plan members must be exactly its members")
    return MonsterJourney(
        journey_id,
        group_id,
        member_ids,
        source,
        destination,
        depart_tick,
        arrival_tick,
        settled,
        retry_tick,
        edge,
        plan,
    )


def _receipt_to_dict(receipt: ActivityReceipt) -> dict[str, Any]:
    return {
        "operation_id": receipt.operation_id,
        "kind": receipt.kind,
        "group_id": receipt.group_id,
        "journey_id": receipt.journey_id,
        "individual_id": receipt.individual_id,
        "occurred_tick": receipt.occurred_tick,
    }


def _receipt_from_dict(key: str, value: Any) -> ActivityReceipt:
    data = _require_keys(value, _RECEIPT_FIELDS, f"receipt {key!r}")
    operation_id = _require_name(data["operation_id"], "receipt operation_id")
    if operation_id != key:
        raise _invalid("a receipt's key must equal its operation id")
    kind = _require_name(data["kind"], "receipt kind")
    group_id = _require_name(data["group_id"], "receipt group_id")
    journey_id = data["journey_id"]
    if journey_id is not None:
        _require_name(journey_id, "receipt journey_id")
    individual_raw = data["individual_id"]
    individual_id = (
        None
        if individual_raw is None
        else _require_int(individual_raw, "receipt individual_id", 1)
    )
    occurred_tick = _require_int(data["occurred_tick"], "receipt occurred_tick")
    return ActivityReceipt(
        operation_id, kind, group_id, journey_id, individual_id, occurred_tick
    )


def _room_protection_to_dict(protection: RoomProtection) -> dict[str, Any]:
    return {
        "session_id": protection.session_id,
        "location": encode_location_ref(protection.location),
        "start_tick": protection.start_tick,
        "end_tick": protection.end_tick,
    }


def _room_protection_from_dict(value: Any, index: int) -> RoomProtection:
    data = _require_keys(
        value, _ROOM_PROTECTION_FIELDS, f"room_protection[{index}]"
    )
    session_id = _require_name(data["session_id"], "room protection session_id")
    location = decode_location_ref(data["location"])
    if location.kind != "room":
        raise _invalid("room protection names a persistent authored room")
    start_tick = _require_int(data["start_tick"], "room protection start_tick")
    end_raw = data["end_tick"]
    end_tick = (
        None
        if end_raw is None
        else _require_int(end_raw, "room protection end_tick", start_tick)
    )
    return RoomProtection(session_id, location, start_tick, end_tick)


def state_to_dict(state: MonsterActivityState) -> dict[str, Any]:
    """The exact persisted owner record mapping."""
    if not isinstance(state, MonsterActivityState):
        raise TypeError(f"expected a MonsterActivityState, got {state!r}")
    return {
        "groups": {
            key: group_to_dict(value) for key, value in state.groups.items()
        },
        "journeys": {
            key: journey_to_dict(value) for key, value in state.journeys.items()
        },
        "receipts": {
            key: _receipt_to_dict(value) for key, value in state.receipts.items()
        },
        "room_protection": [
            _room_protection_to_dict(value) for value in state.room_protection
        ],
        "settled_through_tick": state.settled_through_tick,
    }


def state_from_dict(value: Any) -> MonsterActivityState:
    """Parse and cross-check one exact persisted owner record mapping."""
    data = _require_keys(value, _STATE_FIELDS, "monster_activity")
    groups_raw = data["groups"]
    journeys_raw = data["journeys"]
    receipts_raw = data["receipts"]
    if not (
        isinstance(groups_raw, Mapping)
        and isinstance(journeys_raw, Mapping)
        and isinstance(receipts_raw, Mapping)
    ):
        raise _invalid("groups, journeys and receipts must be mappings")
    protection_raw = data["room_protection"]
    if not _is_sequence(protection_raw):
        raise _invalid("room_protection must be a list")
    groups = {
        key: group_from_dict(key, value) for key, value in groups_raw.items()
    }
    for key, group in groups.items():
        if not isinstance(key, str) or not key or group.group_id != key:
            raise _invalid("a group's key must equal its group id")
    journeys = {
        key: journey_from_dict(key, value) for key, value in journeys_raw.items()
    }
    for key, journey in journeys.items():
        if not isinstance(key, str) or not key or journey.journey_id != key:
            raise _invalid("a journey's key must equal its journey id")
        group = groups.get(journey.group_id)
        if group is None:
            raise _invalid(f"journey {key!r} names a missing group")
        if group.journey_id != key:
            raise _invalid(f"group {group.group_id!r} does not name journey {key!r}")
        if set(group.member_ids) != set(journey.member_ids):
            raise _invalid(f"journey {key!r} members differ from its group")
        if group.position is not None:
            raise _invalid(f"group {group.group_id!r} is in a journey but still positioned")
    for group in groups.values():
        if group.journey_id is not None and group.journey_id not in journeys:
            raise _invalid(f"group {group.group_id!r} names a missing journey")
    for group in groups.values():
        for key, member_time in group.member_time.items():
            if member_time.mode == MODE_JOURNEY and group.journey_id is None:
                raise _invalid(
                    f"member {key!r} of group {group.group_id!r} owns a journey it is not in"
                )
            if member_time.mode == MODE_COMBAT and member_time.session_id is None:
                raise _invalid(
                    f"member {key!r} of group {group.group_id!r} is combat-owned without a session"
                )
    seen_members: set[int] = set()
    for group in groups.values():
        for member_id in group.member_ids:
            if member_id in seen_members:
                raise _invalid(f"member {member_id} belongs to more than one group")
            seen_members.add(member_id)
    receipts = {
        key: _receipt_from_dict(key, value) for key, value in receipts_raw.items()
    }
    protection = tuple(
        _room_protection_from_dict(value, index)
        for index, value in enumerate(protection_raw)
    )
    settled = _require_int(data["settled_through_tick"], "settled_through_tick")
    return MonsterActivityState(
        groups, journeys, receipts, protection, settled
    )


def _member_index(groups: Mapping[str, MonsterGroup]) -> dict[str, int]:
    index: dict[str, int] = {}
    for group in groups.values():
        for member_id in group.member_ids:
            index[str(member_id)] = member_id
    return index


# ---------------------------------------------------------------------------
# Durable state access


def _require_wilderness(wilderness: Any) -> Any:
    if wilderness is None:
        raise MonsterActivityOperationInvalid(
            "world_unavailable", "no wilderness world exists"
        )
    return wilderness


def initialize_monster_activity(wilderness: Any, *, tick: int) -> MonsterActivityState:
    """Write the empty owner record once; an existing record is returned."""
    _require_wilderness(wilderness)
    _require_int(tick, "tick")
    if wilderness.attributes.has(MONSTER_ACTIVITY_ATTRIBUTE):
        return read_monster_activity(wilderness)
    state = MonsterActivityState({}, {}, {}, (), tick)
    _write_state(wilderness, state)
    return state


def read_monster_activity(wilderness: Any) -> MonsterActivityState:
    """Read the complete owner record; missing or malformed state refuses."""
    _require_wilderness(wilderness)
    raw = wilderness.attributes.get(MONSTER_ACTIVITY_ATTRIBUTE)
    if raw is None:
        raise _invalid(
            f"{MONSTER_ACTIVITY_ATTRIBUTE!r} is missing from this provisioned world"
        )
    return state_from_dict(raw)


def activity_provisioned(wilderness: Any) -> bool:
    """Whether this world carries the required owner record at all."""
    try:
        return wilderness is not None and wilderness.attributes.has(
            MONSTER_ACTIVITY_ATTRIBUTE
        )
    except Exception:  # observability: ignore R2: an unreadable store is simply not provisioned
        return False


def _write_state(wilderness: Any, state: MonsterActivityState) -> None:
    wilderness.db.monster_activity = state_to_dict(state)


def _copy_state(state: MonsterActivityState, **fields: Any) -> MonsterActivityState:
    return MonsterActivityState(
        fields.get("groups", state.groups),
        fields.get("journeys", state.journeys),
        fields.get("receipts", state.receipts),
        fields.get("room_protection", state.room_protection),
        fields.get("settled_through_tick", state.settled_through_tick),
    )


# ---------------------------------------------------------------------------
# Group construction


def group_id_for(operation_id: str, ordinal: int) -> str:
    """One durable group id derived from the placing operation and ordinal."""
    _require_name(operation_id, "operation_id")
    _require_int(ordinal, "ordinal")
    return f"{operation_id}#{ordinal}"


def _activity_interval(activity_key: str) -> int:
    from world.lore.monster_activity import MONSTER_ACTIVITY_REGISTRY

    declaration = MONSTER_ACTIVITY_REGISTRY.get(activity_key)
    if declaration is not None:
        return declaration.decision_interval
    if activity_key == STAGED_STATIONARY_ACTIVITY:
        return STAGED_DECISION_INTERVAL
    return DEFAULT_DECISION_INTERVAL


def decision_interval(wilderness: Any, group_id: str) -> int:
    """The positive decision interval of one group's committed binding."""
    state = read_monster_activity(wilderness)
    group = state.groups.get(group_id)
    if group is None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_unknown", f"no group {group_id!r}"
        )
    return _activity_interval(group.activity_key)


def create_group(
    wilderness: Any,
    *,
    operation_id: str,
    ordinal: int = 0,
    owner_kind: str,
    owner_key: str,
    activity_key: str,
    home: LocationRef,
    position: LocationRef | None,
    member_ids: Iterable[int],
    seed: int,
    tick: int,
) -> str:
    """Create one initial group for a construction owner; returns its id.

    A construction owner creates groups exactly once per placing operation and
    sampled composition ordinal. An existing group with that id refuses rather
    than being replaced, so no foreign identity or resource is ever absorbed.
    """
    _require_wilderness(wilderness)
    state = read_monster_activity(wilderness)
    if owner_kind not in OWNER_KINDS:
        raise MonsterActivityOperationInvalid(
            "monster_activity_owner_unknown", f"unknown owner kind {owner_kind!r}"
        )
    _require_name(owner_key, "owner_key")
    _require_name(activity_key, "activity_key")
    _require_int(tick, "tick")
    if not _is_int(seed):
        raise MonsterActivityOperationInvalid("seed must be an integer")
    group_id = group_id_for(operation_id, ordinal)
    if group_id in state.groups:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_exists", f"group {group_id!r} already exists"
        )
    members = tuple(int(member_id) for member_id in member_ids)
    if not members or len(set(members)) != len(members):
        raise MonsterActivityOperationInvalid(
            "monster_activity_members_invalid",
            "a group needs distinct member identities",
        )
    if not isinstance(home, LocationRef):
        raise MonsterActivityOperationInvalid("home must be a LocationRef")
    if not isinstance(position, LocationRef):
        raise MonsterActivityOperationInvalid(
            "monster_activity_position_invalid",
            "an initial group must start at its home position",
        )
    member_time = {
        str(member_id): MemberTime(tick, MODE_IDLE, None, ())
        for member_id in members
    }
    group = MonsterGroup(
        group_id=group_id,
        member_ids=members,
        home_owner=(owner_kind, owner_key),
        activity_key=activity_key,
        home=home,
        position=position,
        journey_id=None,
        next_decision_tick=tick + _activity_interval(activity_key),
        sequence=0,
        seed=seed,
        member_time=member_time,
    )
    groups = dict(state.groups)
    groups[group_id] = group
    _write_state(wilderness, _copy_state(state, groups=groups))
    return group_id


def group_of_member(wilderness: Any, individual_id: int) -> MonsterGroup | None:
    """The one group owning ``individual_id``, or ``None``."""
    state = read_monster_activity(wilderness)
    for group in state.groups.values():
        if individual_id in group.member_ids:
            return group
    return None


def release_group(wilderness: Any, group_id: str) -> None:
    """Remove one construction owner's staged group and its receipts.

    Only the owner that created a staged group (a finished examination) calls
    this, and only for a group that is not travelling. The individual rows are
    untouched: this is the activity-record half of an owner cleanup.
    """
    if not activity_provisioned(wilderness):
        return
    state = read_monster_activity(wilderness)
    group = state.groups.get(group_id)
    if group is None:
        return
    if group.journey_id is not None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_in_journey",
            f"group {group_id!r} is travelling and cannot be released",
        )
    groups = dict(state.groups)
    groups.pop(group_id, None)
    receipts = {
        key: value
        for key, value in state.receipts.items()
        if value.group_id != group_id
    }
    _write_state(wilderness, _copy_state(state, groups=groups, receipts=receipts))


def group(wilderness: Any, group_id: str) -> MonsterGroup | None:
    return read_monster_activity(wilderness).groups.get(group_id)


def journey(wilderness: Any, journey_id: str) -> MonsterJourney | None:
    return read_monster_activity(wilderness).journeys.get(journey_id)


def receipt(wilderness: Any, operation_id: str) -> ActivityReceipt | None:
    return read_monster_activity(wilderness).receipts.get(operation_id)


# ---------------------------------------------------------------------------
# Fingerprints


def group_fingerprint(group: MonsterGroup, individual: Any) -> str:
    """The canonical SHA-256 of one selected group and member physiology.

    The digest covers the exact group record (members, cursors, source,
    sequence) and the selected member's current reserve/posture. A commit
    revalidates it before any write, so a physically changed body or group can
    never be carried into a journey by a stale plan.
    """
    import hashlib
    import json

    from world.rules.fatigue import read_optional_fatigue_state

    state = read_optional_fatigue_state(individual)
    payload = {
        "group": group_to_dict(group),
        "member": [
            getattr(individual, "pk", None),
            None if state is None else state.reserve_units,
            None if state is None else str(state.posture),
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# ---------------------------------------------------------------------------
# Ordinary activity decisions


def _alive(body: Any) -> bool:
    try:
        return float(getattr(body.traits.hp, "current", 0)) > 0
    except (AttributeError, TypeError, ValueError):  # observability: ignore R2: a body without a readable gauge is simply not self-moving; it is never silently moved
        return False


def _active_participant_ids() -> frozenset[int]:
    """Non-fled participants of every persisted active hostile session."""
    from world.maps import regional_population

    return regional_population.active_combat_participant_ids()


def _member_bodies(group: MonsterGroup) -> tuple[Any, ...]:
    """Every living member row of one group, in member-id order."""
    from evennia.objects.models import ObjectDB

    bodies: list[Any] = []
    for member_id in group.member_ids:
        body = ObjectDB.objects.filter(id=int(member_id)).first()
        if body is not None and _alive(body):
            bodies.append(body)
    return tuple(bodies)


def _declaration(activity_key: str) -> Any | None:
    """The published ordinary-activity declaration, or ``None``."""
    from world.lore.monster_activity import MONSTER_ACTIVITY_REGISTRY

    return MONSTER_ACTIVITY_REGISTRY.get(activity_key)


def _group_area(group: MonsterGroup) -> tuple[Mapping[str, object], ...]:
    """The bounded legal cells of one group's committed activity binding."""
    from world.lore.monster_activity import (
        ACTIVITY_AREA_REGISTRY,
        resolve_activity_area,
    )
    from world.maps.geography import current as current_geography

    declaration = _declaration(group.activity_key)
    if declaration is None:
        raise _invalid(
            f"group {group.group_id!r} names no published activity binding"
        )
    area = ACTIVITY_AREA_REGISTRY.get(declaration.area_key)
    if area is None:
        raise _invalid(
            f"activity {declaration.key!r} names a missing activity area"
        )
    return tuple(
        resolve_activity_area(
            area,
            home=encode_location_ref(group.home),
            candidate_world=current_geography(),
        )
    )


def _locator_key(locator: Mapping[str, object]) -> str:
    import json

    return json.dumps(dict(locator), sort_keys=True, separators=(",", ":"))


def _body_at_position(wilderness: Any, body: Any, position: LocationRef) -> bool:
    from world.maps import regional_population

    if position.kind == "wilderness":
        cell = regional_population.actual_cell(wilderness, body)
        return cell == (position.x, position.y)
    return getattr(getattr(body, "location", None), "pk", None) == position.id


def _edge_key(edge: PhysicalEdge) -> str:
    return _locator_key(encode_physical_edge(edge))


def _legal_group_edges(
    group: MonsterGroup, bodies: tuple[Any, ...]
) -> tuple[PhysicalEdge, ...]:
    """Edges every living member currently discovers, in canonical order."""
    per_member: list[dict[str, PhysicalEdge]] = []
    for body in bodies:
        try:
            edges = legal_edges(body, group.position, (body,))
        except MovementEdgeError:  # observability: ignore R2: an unrepresentable position contributes no lawful edge and keeps the group in place
            edges = ()
        per_member.append({_edge_key(edge): edge for edge in edges})
    if not per_member:
        return ()
    common = set(per_member[0])
    for discovered in per_member[1:]:
        common &= set(discovered)
    return tuple(per_member[0][key] for key in sorted(common))


def _project_idle_state(
    body: Any, member_time: MemberTime, *, through_tick: int
) -> Any:
    """The member's posture after its unpaid idle prefix (pure projection).

    Uses exactly the interruptible segmentation the owner's committed idle
    settlement uses, so a read-only plan prices the same state a commit will
    settle without writing. A wholly absent physiology state stays absent.
    """
    from world.rules.fatigue import (
        FatigueActivity,
        IntervalCompletion,
        SleepPosture,
        predict_interval,
        read_optional_fatigue_state,
    )

    state = read_optional_fatigue_state(body)
    if state is None:
        return None
    remaining = int(through_tick) - member_time.settled_through_tick
    for _ in range(_MAX_POSTURE_SEGMENTS):
        if remaining <= 0:
            return state
        activity = (
            FatigueActivity.SLEEP
            if state.posture is not SleepPosture.AWAKE
            else FatigueActivity.AWAKE
        )
        prediction = predict_interval(
            state, activity, remaining, completion=IntervalCompletion.INTERRUPTIBLE
        )
        step = prediction.applicable_seconds
        if step <= 0:
            advanced = predict_interval(
                state, activity, 0, completion=IntervalCompletion.INTERRUPTIBLE
            ).end
            if advanced == state:
                raise MonsterActivityOperationInvalid(
                    "monster_activity_physiology_no_progress",
                    f"member {getattr(body, 'pk', '?')} cannot advance its posture",
                )
            state = advanced
            continue
        state = predict_interval(
            state, activity, step, completion=IntervalCompletion.INTERRUPTIBLE
        ).end
        remaining -= step
    raise MonsterActivityOperationInvalid(
        "monster_activity_physiology_segments",
        "an idle interval exceeded its bounded posture segmentation",
    )


def _projected_member_states(
    group: MonsterGroup, bodies: tuple[Any, ...], *, tick: int
) -> tuple[Any, ...]:
    """Detached physiology for every member at the decision occurrence."""
    from world.rules.fatigue import read_optional_fatigue_state
    from world.rules.travel_plan import TravellerState

    states: list[Any] = []
    for body in bodies:
        member_time = group.member_time[str(body.pk)]
        if member_time.mode == MODE_IDLE and member_time.settled_through_tick < tick:
            state = _project_idle_state(body, member_time, through_tick=tick)
        else:
            state = read_optional_fatigue_state(body)
        states.append(TravellerState.from_state(state, member_id=int(body.pk)))
    return tuple(states)


def _bounded_candidates(
    wilderness: Any,
    group: MonsterGroup,
    bodies: tuple[Any, ...],
    *,
    tick: int,
    area_keys: frozenset[str],
) -> tuple[PhysicalEdge, ...]:
    """Every lawful, unprotected edge landing inside the activity area."""
    candidates: list[PhysicalEdge] = []
    for edge in _legal_group_edges(group, bodies):
        if _locator_key(encode_location_ref(edge.destination)) not in area_keys:
            continue
        if _destination_blocked(wilderness, edge.destination, tick):
            continue
        candidates.append(edge)
    return tuple(candidates)


def _resolved_area_keys(group: MonsterGroup) -> frozenset[str] | None:
    """The canonical inside-area locator keys, or ``None`` when unresolvable."""
    from world.lore.monster_activity import MonsterActivityRegistryError

    try:
        return frozenset(
            _locator_key(locator) for locator in _group_area(group)
        )
    except (MonsterActivityRegistryError, MovementEdgeError):  # observability: ignore R2: an authored area the published candidate cannot resolve is a lawful scheduled stay; the publisher rejects it before production use
        return None


def _price_candidates(
    bodies: tuple[Any, ...],
    states: tuple[Any, ...],
    candidates: tuple[PhysicalEdge, ...],
) -> tuple[tuple[PhysicalEdge, ...], set[str]]:
    """The canonically priced group routes plus the refusal reasons seen."""
    priced: list[PhysicalEdge] = []
    refusals: set[str] = set()
    for edge in candidates:
        try:
            resolution = quote_edge(bodies[0], edge, bodies, states=states)
        except MovementPreflightRefused as error:  # observability: ignore R2: an ordinary sleeping/depleted refusal selects a stay, not an operational failure
            refusals.add(error.reason)
            continue
        if resolution.status is TraversalStatus.UNRESOLVED:
            refusals.add(STAY_MEMBER_BLOCKED)
            continue
        if (
            resolution.status is TraversalStatus.RESOLVED
            and (resolution.cost is None or resolution.cost.seconds < 0)
        ):
            refusals.add(STAY_MEMBER_BLOCKED)
            continue
        priced.append(edge)
    return tuple(priced), refusals


def _stay_reason(
    candidates: tuple[PhysicalEdge, ...], refusals: set[str]
) -> str:
    if not candidates:
        return STAY_NO_LEGAL_ROUTE
    if "party_sleeping" in refusals:
        return STAY_MEMBER_SLEEPING
    if "pre_destination_depletion" in refusals:
        return STAY_MEMBER_UNAFFORDABLE
    return STAY_MEMBER_BLOCKED


def plan_group_decision(
    wilderness: Any, group_id: str, *, tick: int
) -> ActivityDecision:
    """Plan one saved ordinary decision without writing anything.

    The saved seed, group identity, sequence and tick select deterministically
    through the population owner's single sampling discipline. Staying is a
    scheduled candidate; a lawful departure is the one route the whole living
    group can physically take inside its authored bounds.
    """
    _require_wilderness(wilderness)
    _require_int(tick, "tick")
    state = read_monster_activity(wilderness)
    group = state.groups.get(group_id)
    if group is None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_unknown", f"no group {group_id!r}"
        )
    if group.journey_id is not None:
        return ActivityDecision(
            group_id, tick, group.sequence, None, STAY_IN_JOURNEY
        )
    declaration = _declaration(group.activity_key)
    if declaration is None:
        reason = (
            STAY_STATIONARY
            if group.activity_key == STAGED_STATIONARY_ACTIVITY
            else STAY_UNPUBLISHED_BINDING
        )
        return ActivityDecision(group_id, tick, group.sequence, None, reason)
    if declaration.policy == "stationary":
        return ActivityDecision(
            group_id, tick, group.sequence, None, STAY_STATIONARY
        )
    bodies = _member_bodies(group)
    if not bodies:
        return ActivityDecision(
            group_id, tick, group.sequence, None, STAY_NO_LIVING_MEMBERS
        )
    active_participants = _active_participant_ids()
    for body in bodies:
        member_time = group.member_time[str(body.pk)]
        if (
            member_time.mode == MODE_COMBAT
            or int(body.pk) in active_participants
        ):
            return ActivityDecision(
                group_id, tick, group.sequence, None, STAY_MEMBER_ENGAGED
            )
        if member_time.settled_through_tick > tick:
            return ActivityDecision(
                group_id, tick, group.sequence, None, STAY_MEMBER_SETTLED_AHEAD
            )
        if not _body_at_position(wilderness, body, group.position):
            return ActivityDecision(
                group_id, tick, group.sequence, None, STAY_MEMBER_DISPLACED
            )
    area_keys = _resolved_area_keys(group)
    if area_keys is None:
        return ActivityDecision(
            group_id, tick, group.sequence, None, STAY_UNPUBLISHED_BINDING
        )
    outside = _locator_key(encode_location_ref(group.position)) not in area_keys
    candidates = _bounded_candidates(
        wilderness, group, bodies, tick=tick, area_keys=area_keys
    )
    states = _projected_member_states(group, bodies, tick=tick)
    priced, refusals = _price_candidates(bodies, states, candidates)
    if not priced:
        reason = (
            STAY_OUTSIDE_BOUNDS_WAITING
            if outside
            else _stay_reason(candidates, refusals)
        )
        return ActivityDecision(group_id, tick, group.sequence, None, reason)
    choices: tuple[PhysicalEdge | None, ...] = (
        priced if outside else (None, *priced)
    )
    from world.maps import regional_population

    index = regional_population.draw_index(
        seed=group.seed,
        stream_key=group.group_id,
        sequence=group.sequence,
        tick=tick,
        ordinal=0,
        purpose=DECISION_PURPOSE,
        upper=len(choices),
    )
    chosen = choices[index]
    return ActivityDecision(
        group_id,
        tick,
        group.sequence,
        chosen,
        DECISION_DEPART if chosen is not None else DECISION_STAY,
    )


def commit_group_decision(wilderness: Any, plan: ActivityDecision) -> None:
    """Commit one planned stay or whole-group departure atomically.

    The plan is revalidated against the committed group before any write:
    sequence, idle position, living membership, per-member access and the
    canonical execution price must all still hold. A departure moves every
    living member in one group journey, never a subset; a stay advances the
    sequence exactly once and schedules the next positive decision.
    """
    if not isinstance(plan, ActivityDecision):
        raise TypeError(f"expected an ActivityDecision, got {plan!r}")
    _require_wilderness(wilderness)
    _require_int(plan.tick, "tick")
    operation_id = f"activity:{plan.group_id}:{plan.tick}"
    state = read_monster_activity(wilderness)
    existing = state.receipts.get(operation_id)
    if existing is not None:
        if existing.journey_id is None:
            raise MonsterActivityOperationInvalid(
                "monster_activity_receipt_conflict",
                f"operation {operation_id!r} is not a departure receipt",
            )
        return
    group = state.groups.get(plan.group_id)
    if group is None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_unknown", f"no group {plan.group_id!r}"
        )
    if group.journey_id is not None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_in_journey",
            f"group {plan.group_id!r} is already travelling",
        )
    if plan.tick < group.next_decision_tick:
        raise MonsterActivityOperationInvalid(
            "monster_activity_decision_early",
            f"group {plan.group_id!r} is not due until {group.next_decision_tick}",
        )
    if plan.edge is None:
        _commit_stay(wilderness, group, plan)
        return
    _commit_departure(wilderness, group, plan, operation_id=operation_id)


def _decision_interval(group: MonsterGroup) -> int:
    return _activity_interval(group.activity_key)


def _emit_decided(plan: ActivityDecision) -> None:
    context = {
        "group": plan.group_id,
        "sequence": plan.expected_sequence,
        "tick": plan.tick,
        "reason": plan.reason,
    }
    transaction.on_commit(
        lambda context=context: log_info("monster_activity_decided", context=context)
    )


def _commit_stay(wilderness: Any, group: MonsterGroup, plan: ActivityDecision) -> None:
    del group  # the group is re-read inside the owning transaction
    snapshot = snapshot_departure_surfaces(wilderness)
    try:
        with transaction.atomic():
            settle_group_idle(wilderness, plan.group_id, tick=plan.tick)
            state = read_monster_activity(wilderness)
            current = state.groups.get(plan.group_id)
            if current is None or current.journey_id is not None:
                raise MonsterActivityOperationInvalid(
                    "monster_activity_sequence_stale",
                    f"group {plan.group_id!r} changed before its stay committed",
                )
            if current.sequence != plan.expected_sequence:
                raise MonsterActivityOperationInvalid(
                    "monster_activity_sequence_stale",
                    f"group {plan.group_id!r} sequence changed before its stay",
                )
            groups = dict(state.groups)
            groups[plan.group_id] = _replace_group(
                current,
                sequence=current.sequence + 1,
                next_decision_tick=int(plan.tick) + _decision_interval(current),
            )
            _write_state(
                wilderness,
                _copy_state(
                    state,
                    groups=groups,
                    settled_through_tick=max(state.settled_through_tick, plan.tick),
                ),
            )
            _emit_decided(plan)
    except Exception:
        restore_activity_surfaces(snapshot, wilderness=wilderness)
        raise


def _commit_departure(
    wilderness: Any,
    group: MonsterGroup,
    plan: ActivityDecision,
    *,
    operation_id: str,
) -> None:
    from world.rules.world_escape import build_journey_plan
    from world.rules.fatigue import read_optional_fatigue_state
    from world.rules.travel_plan import TravellerState

    if plan.edge is None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_decision_invalid", "a departure needs one edge"
        )
    if group.sequence != plan.expected_sequence:
        raise MonsterActivityOperationInvalid(
            "monster_activity_sequence_stale",
            f"group {plan.group_id!r} sequence changed before commit",
        )
    if group.position != plan.edge.source:
        raise MonsterActivityOperationInvalid(
            "monster_activity_source_moved",
            f"group {plan.group_id!r} no longer stands at the selected source",
        )
    declaration = _declaration(group.activity_key)
    if declaration is None or declaration.policy == "stationary":
        raise MonsterActivityOperationInvalid(
            "monster_activity_binding_unpublished",
            f"group {plan.group_id!r} has no movable activity binding",
        )
    bodies = _member_bodies(group)
    if not bodies:
        raise MonsterActivityOperationInvalid(
            "monster_activity_members_invalid",
            f"group {plan.group_id!r} has no living member",
        )
    active_participants = _active_participant_ids()
    for body in bodies:
        member_time = group.member_time[str(body.pk)]
        if (
            member_time.mode == MODE_COMBAT
            or int(body.pk) in active_participants
        ):
            raise MonsterActivityOperationInvalid(
                "monster_activity_member_engaged",
                f"member {body.pk} is combat-owned",
            )
        if member_time.settled_through_tick > plan.tick:
            raise MonsterActivityOperationInvalid(
                "monster_activity_member_settled_ahead",
                f"member {body.pk} already settled past the decision tick",
            )
        if not _body_at_position(wilderness, body, group.position):
            raise MonsterActivityOperationInvalid(
                "monster_activity_member_displaced",
                f"member {body.pk} is not at the group position",
            )
    area_keys = {_locator_key(locator) for locator in _group_area(group)}
    if _locator_key(encode_location_ref(plan.edge.destination)) not in area_keys:
        raise MonsterActivityOperationInvalid(
            "monster_activity_destination_outside",
            "the selected edge leaves the authored activity area",
        )
    if _destination_blocked(wilderness, plan.edge.destination, plan.tick):
        raise MonsterActivityOperationInvalid(
            "monster_activity_destination_protected",
            "the selected destination is protected at the decision tick",
        )
    if plan.edge not in _legal_group_edges(group, bodies):
        raise MonsterActivityOperationInvalid(
            "monster_activity_route_stale",
            "at least one living member can no longer take the selected edge",
        )
    snapshot = snapshot_departure_surfaces(wilderness)
    try:
        with transaction.atomic():
            settle_group_idle(wilderness, plan.group_id, tick=plan.tick)
            state = read_monster_activity(wilderness)
            current = state.groups.get(plan.group_id)
            if current is None or current.journey_id is not None:
                raise MonsterActivityOperationInvalid(
                    "monster_activity_sequence_stale",
                    f"group {plan.group_id!r} changed before its departure",
                )
            if current.sequence != plan.expected_sequence:
                raise MonsterActivityOperationInvalid(
                    "monster_activity_sequence_stale",
                    f"group {plan.group_id!r} sequence changed before its departure",
                )
            if current.position != plan.edge.source:
                raise MonsterActivityOperationInvalid(
                    "monster_activity_source_moved",
                    f"group {plan.group_id!r} no longer stands at the selected source",
                )
            bodies = _member_bodies(current)
            if not bodies:
                raise MonsterActivityOperationInvalid(
                    "monster_activity_members_invalid",
                    f"group {plan.group_id!r} has no living member",
                )
            active_participants = _active_participant_ids()
            for body in bodies:
                if int(body.pk) in active_participants:
                    raise MonsterActivityOperationInvalid(
                        "monster_activity_member_engaged",
                        f"member {body.pk} is an active combat participant",
                    )
                if not _body_at_position(wilderness, body, current.position):
                    raise MonsterActivityOperationInvalid(
                        "monster_activity_member_displaced",
                        f"member {body.pk} is not at the group position",
                    )
            if plan.edge not in _legal_group_edges(current, bodies):
                raise MonsterActivityOperationInvalid(
                    "monster_activity_route_stale",
                    "at least one living member can no longer take the selected edge",
                )
            states = tuple(
                TravellerState.from_state(
                    read_optional_fatigue_state(body), member_id=int(body.pk)
                )
                for body in bodies
            )
            try:
                resolution = quote_edge(
                    bodies[0], plan.edge, bodies, states=states
                )
            except MovementPreflightRefused as error:
                raise MonsterActivityOperationInvalid(
                    "monster_activity_route_refused", str(error)
                ) from error
            if resolution.status is TraversalStatus.UNRESOLVED or (
                resolution.status is TraversalStatus.RESOLVED
                and resolution.cost is None
            ):
                raise MonsterActivityOperationInvalid(
                    "monster_activity_route_unresolved",
                    "the canonical resolver priced no lawful route",
                )
            committed = build_journey_plan(bodies, resolution, states)
            member_times = {
                str(body.pk): MemberTime(plan.tick, MODE_JOURNEY, None, ())
                for body in bodies
            }
            _begin_group_journey(
                wilderness,
                operation_id=operation_id,
                group=current,
                moving_ids=tuple(int(body.pk) for body in bodies),
                expected_sequence=current.sequence,
                source=group.position,
                destination=plan.edge.destination,
                edge=plan.edge,
                plan=plan_from_dict(committed),
                depart_tick=int(plan.tick),
                member_times=member_times,
                carry_sequence_when_whole=True,
                emit_escape=False,
            )
            _emit_decided(plan)
    except Exception:
        restore_activity_surfaces(snapshot, wilderness=wilderness)
        raise


# ---------------------------------------------------------------------------
# Departure and arrival


def _wilderness_name(wilderness: Any) -> str:
    name = getattr(wilderness, "db_key", None)
    if not isinstance(name, str) or not name:
        raise MonsterActivityOperationInvalid(
            "world_unavailable", "the wilderness world has no stable identity"
        )
    return name


def _source_room(wilderness: Any, cell: tuple[int, int]) -> Any | None:
    return (wilderness.db.rooms or {}).get(cell)


def begin_monster_journey(
    wilderness: Any,
    *,
    operation_id: str,
    group_id: str,
    individual_id: int,
    expected_sequence: int,
    expected_fingerprint: str,
    source: LocationRef,
    destination: LocationRef,
    edge: PhysicalEdge,
    plan: JourneyPlan,
    depart_tick: int,
    member_time: MemberTime,
) -> str:
    """Atomically detach one member from its group and begin its journey.

    The caller has already validated and settled the member's combat prefix.
    The member leaves its source presence (coordinate registration and room
    attachment) in the same write, keeps its home/site/quest ownership, and
    becomes the only member of a new group that is in exactly one journey.
    """
    _require_wilderness(wilderness)
    _require_name(operation_id, "operation_id")
    _require_int(depart_tick, "depart_tick")
    state = read_monster_activity(wilderness)
    existing = state.receipts.get(operation_id)
    if existing is not None:
        if existing.journey_id is None:
            raise MonsterActivityOperationInvalid(
                "monster_activity_receipt_conflict",
                f"operation {operation_id!r} does not name a journey",
            )
        return existing.journey_id
    group = state.groups.get(group_id)
    if group is None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_unknown", f"no group {group_id!r}"
        )
    if individual_id not in group.member_ids:
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_unknown",
            f"member {individual_id} does not belong to group {group_id!r}",
        )
    if {member.individual_id for member in plan.members} != {individual_id}:
        raise MonsterActivityOperationInvalid(
            "monster_activity_plan_members", "the plan must name exactly the departing member"
        )
    from evennia.objects.models import ObjectDB

    individual = ObjectDB.objects.filter(id=individual_id).first()
    if individual is None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_missing", f"member {individual_id} no longer exists"
        )
    live_fingerprint = group_fingerprint(group, individual)
    if expected_fingerprint and live_fingerprint != expected_fingerprint:
        raise MonsterActivityOperationInvalid(
            "monster_activity_fingerprint_stale",
            "the selected group state changed before commit",
        )
    if member_time.mode != MODE_JOURNEY:
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_time", "the departing member must own a journey cursor"
        )
    return _begin_group_journey(
        wilderness,
        operation_id=operation_id,
        group=group,
        moving_ids=(individual_id,),
        expected_sequence=expected_sequence,
        source=source,
        destination=destination,
        edge=edge,
        plan=plan,
        depart_tick=depart_tick,
        member_times={str(individual_id): member_time},
        carry_sequence_when_whole=False,
        emit_escape=True,
    )


def _begin_group_journey(
    wilderness: Any,
    *,
    operation_id: str,
    group: MonsterGroup,
    moving_ids: tuple[int, ...],
    expected_sequence: int,
    source: LocationRef,
    destination: LocationRef,
    edge: PhysicalEdge,
    plan: JourneyPlan,
    depart_tick: int,
    member_times: Mapping[str, MemberTime],
    carry_sequence_when_whole: bool,
    emit_escape: bool,
) -> str:
    """Detach exactly ``moving_ids`` from one group into one durable journey.

    Every departed body leaves its source presence and gets its own cursor in
    the same atomic owner write; a residual group (members that are not
    self-moving, such as dead identities) keeps its original id and schedules
    its own next decision. The journey's id is derived from the operation, so
    a committed replay is a no-op.
    """
    from evennia.objects.models import ObjectDB

    from world.maps import regional_population

    _require_wilderness(wilderness)
    _require_name(operation_id, "operation_id")
    _require_int(depart_tick, "depart_tick")
    state = read_monster_activity(wilderness)
    existing = state.receipts.get(operation_id)
    if existing is not None:
        if existing.journey_id is None:
            raise MonsterActivityOperationInvalid(
                "monster_activity_receipt_conflict",
                f"operation {operation_id!r} does not name a journey",
            )
        return existing.journey_id
    if group.group_id not in state.groups:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_unknown", f"no group {group.group_id!r}"
        )
    if group.journey_id is not None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_in_journey",
            f"group {group.group_id!r} is already travelling",
        )
    moving = tuple(int(member_id) for member_id in moving_ids)
    if not moving or len(set(moving)) != len(moving):
        raise MonsterActivityOperationInvalid(
            "monster_activity_members_invalid",
            "a journey needs distinct moving identities",
        )
    if any(member_id not in group.member_ids for member_id in moving):
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_unknown",
            f"a moving member does not belong to group {group.group_id!r}",
        )
    if group.sequence != expected_sequence:
        raise MonsterActivityOperationInvalid(
            "monster_activity_sequence_stale",
            f"group {group.group_id!r} sequence is {group.sequence}, "
            f"expected {expected_sequence}",
        )
    if group.position != source:
        raise MonsterActivityOperationInvalid(
            "monster_activity_source_moved",
            f"group {group.group_id!r} no longer stands at {source}",
        )
    if edge.source != source or edge.destination != destination:
        raise MonsterActivityOperationInvalid(
            "monster_activity_edge_mismatch",
            "the edge endpoints differ from the selected route",
        )
    if plan.seconds < 0:
        raise MonsterActivityOperationInvalid("the committed plan duration is invalid")
    if {member.individual_id for member in plan.members} != set(moving):
        raise MonsterActivityOperationInvalid(
            "monster_activity_plan_members",
            "the plan must name exactly the departing members",
        )
    if set(member_times) != {str(member_id) for member_id in moving}:
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_time",
            "every departing member needs its own journey cursor",
        )
    if any(value.mode != MODE_JOURNEY for value in member_times.values()):
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_time",
            "the departing members must own journey cursors",
        )
    bodies = tuple(
        ObjectDB.objects.filter(id=member_id).first() for member_id in moving
    )
    if any(body is None for body in bodies):
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_missing",
            "a departing member no longer exists",
        )
    residual = tuple(
        member_id for member_id in group.member_ids if member_id not in moving
    )
    groups = dict(state.groups)
    groups.pop(group.group_id, None)
    if residual:
        residual_time = {
            key: value
            for key, value in group.member_time.items()
            if key not in member_times
        }
        groups[group.group_id] = _replace_group(
            group,
            member_ids=residual,
            sequence=group.sequence + 1,
            member_time=residual_time,
            next_decision_tick=depart_tick + _activity_interval(group.activity_key),
        )
        travelling_id = (
            f"{group.group_id}~" + "+".join(str(member_id) for member_id in moving)
        )
    else:
        travelling_id = group.group_id
    journey_id = f"journey:{operation_id}"
    arrival_tick = depart_tick + plan.seconds
    travelling_sequence = (
        group.sequence + 1 if carry_sequence_when_whole and not residual else 0
    )
    groups[travelling_id] = MonsterGroup(
        group_id=travelling_id,
        member_ids=moving,
        home_owner=group.home_owner,
        activity_key=group.activity_key,
        home=group.home,
        position=None,
        journey_id=journey_id,
        next_decision_tick=arrival_tick + _activity_interval(group.activity_key),
        sequence=travelling_sequence,
        seed=group.seed,
        member_time=dict(member_times),
    )
    journeys = dict(state.journeys)
    journeys[journey_id] = MonsterJourney(
        journey_id=journey_id,
        group_id=travelling_id,
        member_ids=moving,
        source=source,
        destination=destination,
        depart_tick=depart_tick,
        arrival_tick=arrival_tick,
        settled_through_tick=depart_tick,
        retry_tick=None,
        edge=edge,
        plan=plan,
    )
    receipts = dict(state.receipts)
    receipts[operation_id] = ActivityReceipt(
        operation_id,
        RECEIPT_DEPARTURE,
        travelling_id,
        journey_id,
        moving[0] if len(moving) == 1 else None,
        depart_tick,
    )
    befores = {
        body.pk: regional_population.presence_of(
            wilderness,
            body,
            alive=True,
            cell=(source.x, source.y) if source.kind == "wilderness" else None,
        )
        for body in bodies
    }
    if source.kind == "wilderness":
        coordinates = dict(wilderness.db.itemcoordinates)
        for body in bodies:
            coordinates.pop(body, None)
        wilderness.db.itemcoordinates = coordinates
    for body in bodies:
        body.location = None
    if source.kind == "wilderness":
        room = _source_room(wilderness, (source.x, source.y))
        if room is not None:
            room.contents_cache.init()
    for body in bodies:
        regional_population.record_population_transition(
            wilderness,
            regional_population.PopulationTransition(
                source_id=operation_id,
                individual_id=int(body.pk),
                occurred_tick=depart_tick,
                before=befores[body.pk],
                after=regional_population.presence_of(wilderness, body, alive=True),
            ),
        )
    _write_state(
        wilderness,
        _copy_state(state, groups=groups, journeys=journeys, receipts=receipts),
    )
    for body in bodies:
        context = {
            "operation": operation_id,
            "group": travelling_id,
            "individual": int(body.pk),
            "source": encode_location_ref(source),
            "destination": encode_location_ref(destination),
            "journey": journey_id,
            "tick": depart_tick,
        }
        transaction.on_commit(
            lambda context=context: log_info("monster_departed", context=context)
        )
        if emit_escape:
            transaction.on_commit(
                lambda context=context: log_info(
                    "monster_escape_resolved", context=context
                )
            )
    return journey_id


def _replace_group(group: MonsterGroup, **fields: Any) -> MonsterGroup:
    return MonsterGroup(
        group_id=fields.get("group_id", group.group_id),
        member_ids=fields.get("member_ids", group.member_ids),
        home_owner=fields.get("home_owner", group.home_owner),
        activity_key=fields.get("activity_key", group.activity_key),
        home=fields.get("home", group.home),
        position=fields.get("position", group.position),
        journey_id=fields.get("journey_id", group.journey_id),
        next_decision_tick=fields.get("next_decision_tick", group.next_decision_tick),
        sequence=fields.get("sequence", group.sequence),
        seed=fields.get("seed", group.seed),
        member_time=fields.get("member_time", group.member_time),
    )


def commit_monster_departure(wilderness: Any, plan: Any) -> str:
    """Atomically commit one planned mapped escape; returns its journey id.

    The plan is revalidated against the committed group before any write: the
    operation receipt makes a replay a no-op, the group sequence, source and
    physiology fingerprint must still match, and only then is the unpaid
    combat prefix settled and the durable journey begun in one transaction.
    """
    from world.rules import world_escape

    _require_wilderness(wilderness)
    state = read_monster_activity(wilderness)
    existing = state.receipts.get(plan.operation_id)
    if existing is not None:
        if existing.journey_id is None:
            raise MonsterActivityOperationInvalid(
                "monster_activity_receipt_conflict",
                f"operation {plan.operation_id!r} is not a departure receipt",
            )
        return existing.journey_id
    group = state.groups.get(plan.group_id)
    if group is None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_unknown", f"no group {plan.group_id!r}"
        )
    if group.sequence != plan.expected_group_sequence:
        raise MonsterActivityOperationInvalid(
            "monster_activity_sequence_stale",
            f"group {plan.group_id!r} sequence changed before commit",
        )
    if group.position != plan.edge.source:
        raise MonsterActivityOperationInvalid(
            "monster_activity_source_moved",
            f"group {plan.group_id!r} no longer stands at the selected source",
        )
    from evennia.objects.models import ObjectDB

    individual = ObjectDB.objects.filter(id=plan.individual_id).first()
    if individual is None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_missing",
            f"member {plan.individual_id} no longer exists",
        )
    if group_fingerprint(group, individual) != plan.expected_fingerprint:
        raise MonsterActivityOperationInvalid(
            "monster_activity_fingerprint_stale",
            "the selected group state changed before commit",
        )
    world_escape.settle_monster_combat_through(
        individual,
        through_tick=plan.occurred_tick,
        operation_id=plan.operation_id,
    )
    member_time = MemberTime(
        plan.occurred_tick, MODE_JOURNEY, plan.session_id, ()
    )
    return begin_monster_journey(
        wilderness,
        operation_id=plan.operation_id,
        group_id=plan.group_id,
        individual_id=plan.individual_id,
        expected_sequence=plan.expected_group_sequence,
        expected_fingerprint=None,
        source=plan.edge.source,
        destination=plan.edge.destination,
        edge=plan.edge,
        plan=plan_from_dict(plan.committed_plan),
        depart_tick=plan.occurred_tick,
        member_time=member_time,
    )


def update_member_time(
    wilderness: Any,
    *,
    group_id: str,
    individual_id: int,
    member_time: MemberTime,
) -> None:
    """Write one member's cursor without changing any other durable field."""
    state = read_monster_activity(wilderness)
    group = state.groups.get(group_id)
    if group is None or individual_id not in group.member_ids:
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_unknown",
            f"member {individual_id} does not belong to group {group_id!r}",
        )
    member_time_map = dict(group.member_time)
    member_time_map[str(individual_id)] = member_time
    groups = dict(state.groups)
    groups[group_id] = _replace_group(group, member_time=member_time_map)
    _write_state(wilderness, _copy_state(state, groups=groups))


def mark_member_combat(
    wilderness: Any, *, group_id: str, individual_id: int, session_id: str, tick: int
) -> None:
    """Mark one member combat-owned from ``tick`` in the same map record."""
    state = read_monster_activity(wilderness)
    group = state.groups.get(group_id)
    if group is None or individual_id not in group.member_ids:
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_unknown",
            f"member {individual_id} does not belong to group {group_id!r}",
        )
    current = group.member_time[str(individual_id)]
    if current.mode == MODE_COMBAT and current.session_id == session_id:
        return
    member_time_map = dict(group.member_time)
    member_time_map[str(individual_id)] = MemberTime(
        max(current.settled_through_tick, tick), MODE_COMBAT, session_id, ()
    )
    groups = dict(state.groups)
    groups[group_id] = _replace_group(group, member_time=member_time_map)
    _write_state(wilderness, _copy_state(state, groups=groups))


def begin_member_combat(
    wilderness: Any, *, individual_id: int, session_id: str, tick: int
) -> bool:
    """Make one member combat-owned at admission; ``False`` when ungrouped.

    The prior idle prefix is paid through the canonical fatigue writer at
    ``tick`` under the member's own posture, then the member's owner becomes
    exactly this session. A member already owned by the same session is
    unchanged.
    """
    if not activity_provisioned(wilderness):
        return False
    state = read_monster_activity(wilderness)
    for group in state.groups.values():
        if individual_id not in group.member_ids:
            continue
        current = group.member_time[str(individual_id)]
        if current.mode == MODE_COMBAT and current.session_id == session_id:
            return True
        from evennia.objects.models import ObjectDB

        individual = ObjectDB.objects.filter(id=int(individual_id)).first()
        if individual is not None and tick > current.settled_through_tick:
            prefix = tick - current.settled_through_tick
            _idle_physiology(
                individual,
                seconds=prefix,
                context={"stage": "monster_idle_admission", "session": session_id},
                start_tick=current.settled_through_tick,
            )
            _settle_gauge(individual, seconds=prefix)
        member_time_map = dict(group.member_time)
        member_time_map[str(individual_id)] = MemberTime(
            max(current.settled_through_tick, tick), MODE_COMBAT, session_id, ()
        )
        groups = dict(state.groups)
        groups[group.group_id] = _replace_group(group, member_time=member_time_map)
        _write_state(wilderness, _copy_state(state, groups=groups))
        return True
    return False


def combat_owned_member_ids(wilderness: Any, session_id: str) -> tuple[int, ...]:
    """Every member currently owned by one combat session, in identity order."""
    if not activity_provisioned(wilderness):
        return ()
    state = read_monster_activity(wilderness)
    owned: list[int] = []
    for group in state.groups.values():
        for member_id in group.member_ids:
            member_time = group.member_time[str(member_id)]
            if member_time.mode == MODE_COMBAT and member_time.session_id == session_id:
                owned.append(member_id)
    return tuple(sorted(owned))


def record_combat_interval(
    wilderness: Any,
    *,
    group_id: str,
    individual_id: int,
    start_tick: int,
    end_tick: int,
    activity: str,
) -> None:
    """Append one completed posture interval to a combat-owned member."""
    if activity not in COMBAT_ACTIVITIES:
        raise MonsterActivityOperationInvalid(
            "monster_activity_activity_invalid", f"unknown activity {activity!r}"
        )
    state = read_monster_activity(wilderness)
    group = state.groups.get(group_id)
    if group is None or individual_id not in group.member_ids:
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_unknown",
            f"member {individual_id} does not belong to group {group_id!r}",
        )
    current = group.member_time[str(individual_id)]
    if current.mode != MODE_COMBAT:
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_time", "the member is not combat-owned"
        )
    last_end = (
        current.combat_intervals[-1].end_tick
        if current.combat_intervals
        else current.settled_through_tick
    )
    if start_tick != last_end or end_tick < start_tick:
        raise MonsterActivityOperationInvalid(
            "monster_activity_interval_invalid",
            "a recorded combat interval must start at the member cursor and not regress",
        )
    member_time_map = dict(group.member_time)
    member_time_map[str(individual_id)] = MemberTime(
        current.settled_through_tick,
        current.mode,
        current.session_id,
        (*current.combat_intervals, CombatInterval(start_tick, end_tick, activity)),
    )
    groups = dict(state.groups)
    groups[group_id] = _replace_group(group, member_time=member_time_map)
    _write_state(wilderness, _copy_state(state, groups=groups))


# ---------------------------------------------------------------------------
# Room protection


def record_room_protection(
    wilderness: Any,
    *,
    session_id: str,
    location: LocationRef,
    start_tick: int,
    end_tick: int | None,
) -> None:
    """Record or close one persistent authored room's protected interval."""
    _require_wilderness(wilderness)
    if not activity_provisioned(wilderness):
        return
    _require_name(session_id, "session_id")
    if not isinstance(location, LocationRef) or location.kind != "room":
        raise MonsterActivityOperationInvalid(
            "monster_activity_room_invalid", "room protection names a persistent room"
        )
    _require_int(start_tick, "start_tick")
    if end_tick is not None:
        _require_int(end_tick, "end_tick", start_tick)
    state = read_monster_activity(wilderness)
    remaining = tuple(
        item
        for item in state.room_protection
        if not (item.session_id == session_id and item.start_tick == start_tick)
    )
    protection = (*remaining, RoomProtection(session_id, location, start_tick, end_tick))
    _write_state(wilderness, _copy_state(state, room_protection=protection))


def room_protected(wilderness: Any, location: LocationRef, tick: int) -> bool:
    """Whether one authored room is protected at ``tick`` (inclusive end)."""
    if not activity_provisioned(wilderness):
        return False
    state = read_monster_activity(wilderness)
    return any(
        item.location == location
        and item.start_tick <= tick
        and (item.end_tick is None or tick <= item.end_tick)
        for item in state.room_protection
    )


# ---------------------------------------------------------------------------
# Chronological settlement


def _settle_gauge(body: Any, *, seconds: int) -> None:
    """Regenerate the member's gauges through the canonical clock writer."""
    if seconds <= 0:
        return
    from world.rules.clock import settle_gauge_regeneration

    settle_gauge_regeneration((body,), int(seconds))


def _settle_posture(
    body: Any, *, start_tick: int, seconds: int, context: Mapping[str, Any]
) -> None:
    """Pay one idle prefix in deterministic posture segments.

    Segmentation happens exactly at the fatigue owner's own boundaries, so an
    arbitrary split of the same elapsed interval commits the identical
    sequence of segments: equal partitions always leave equal physiology.
    """
    from world.rules.fatigue import (
        FatigueActivity,
        FatigueInterval,
        IntervalCompletion,
        SleepPosture,
        predict_interval,
        read_optional_fatigue_state,
        settle_fatigue_intervals,
    )

    state = read_optional_fatigue_state(body)
    if state is None:
        return
    remaining = int(seconds)
    cursor = int(start_tick)
    for _ in range(_MAX_POSTURE_SEGMENTS):
        if remaining <= 0:
            return
        activity = (
            FatigueActivity.SLEEP
            if state.posture is not SleepPosture.AWAKE
            else FatigueActivity.AWAKE
        )
        prediction = predict_interval(
            state, activity, remaining, completion=IntervalCompletion.INTERRUPTIBLE
        )
        step = prediction.applicable_seconds
        if step <= 0:
            advanced = predict_interval(
                state, activity, 0, completion=IntervalCompletion.INTERRUPTIBLE
            ).end
            if advanced == state:
                raise MonsterActivityOperationInvalid(
                    "monster_activity_physiology_no_progress",
                    f"member {getattr(body, 'pk', '?')} cannot advance its posture",
                )
            # An immediate depletion/wake is a real committed transition: pay
            # a zero-second interval through the sole writer so the persisted
            # state matches the projection before the next segment.
            settlement = settle_fatigue_intervals(
                (
                    FatigueInterval(
                        body,
                        activity,
                        0,
                        state,
                        IntervalCompletion.INTERRUPTIBLE,
                    ),
                ),
                context=dict(context),
                start_tick=cursor,
            )
            state = settlement.commits[0].end
            continue
        settlement = settle_fatigue_intervals(
            (
                FatigueInterval(
                    body,
                    activity,
                    step,
                    state,
                    IntervalCompletion.INTERRUPTIBLE,
                ),
            ),
            context=dict(context),
            start_tick=cursor,
        )
        state = settlement.commits[0].end
        cursor += step
        remaining -= step
    raise MonsterActivityOperationInvalid(
        "monster_activity_physiology_segments",
        "an idle interval exceeded its bounded posture segmentation",
    )


def _settled_group_idle(
    group: MonsterGroup, *, tick: int
) -> MonsterGroup:
    """Return the group with every living idle member paid through ``tick``."""
    from evennia.objects.models import ObjectDB

    member_time = dict(group.member_time)
    changed = False
    for member_id in group.member_ids:
        current = member_time.get(str(member_id))
        if current is None or current.mode != MODE_IDLE:
            continue
        if tick <= current.settled_through_tick:
            continue
        body = ObjectDB.objects.filter(id=int(member_id)).first()
        if body is None or not _alive(body):
            continue
        seconds = tick - current.settled_through_tick
        _settle_posture(
            body,
            start_tick=current.settled_through_tick,
            seconds=seconds,
            context={"stage": "monster_activity_idle", "group": group.group_id},
        )
        _settle_gauge(body, seconds=seconds)
        member_time[str(member_id)] = MemberTime(
            tick, MODE_IDLE, None, ()
        )
        changed = True
    if not changed:
        return group
    return _replace_group(group, member_time=member_time)


def settle_group_idle(wilderness: Any, group_id: str, *, tick: int) -> None:
    """Settle one group's idle physiology through ``tick`` exactly once."""
    _require_wilderness(wilderness)
    _require_int(tick, "tick")
    state = read_monster_activity(wilderness)
    group = state.groups.get(group_id)
    if group is None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_unknown", f"no group {group_id!r}"
        )
    if group.journey_id is not None:
        return
    updated = _settled_group_idle(group, tick=tick)
    if updated is group:
        return
    groups = dict(state.groups)
    groups[group_id] = updated
    _write_state(
        wilderness,
        _copy_state(
            state,
            groups=groups,
            settled_through_tick=max(state.settled_through_tick, tick),
        ),
    )


def settle_idle_physiology(wilderness: Any, tick: int) -> None:
    """Settle every idle group globally through ``tick`` in one owner write.

    Groups in a journey settle their passage and waiting at their own due
    boundaries; combat-owned members are paid by the combat owner. This is the
    one bulk idle pass, so an arbitrary clock-advance partition leaves equal
    resources and cursors.
    """
    if not activity_provisioned(wilderness):
        return
    _require_int(tick, "tick")
    state = read_monster_activity(wilderness)
    groups = dict(state.groups)
    changed = False
    for group_id in sorted(groups):
        group = groups[group_id]
        if group.journey_id is not None:
            continue
        updated = _settled_group_idle(group, tick=tick)
        if updated is not group:
            groups[group_id] = updated
            changed = True
    if not changed:
        return
    _write_state(
        wilderness,
        _copy_state(
            state,
            groups=groups,
            settled_through_tick=max(state.settled_through_tick, tick),
        ),
    )


def settle_group_decisions_at(
    wilderness: Any, tick: int
) -> list[ScheduledEvent]:
    """Plan and commit every due idle group decision at one boundary tick.

    Decisions are observed through the committed logging event, not returned
    as clock boundary events: a distant scheduled stay is internal
    maintenance and must not surface as an interactive boundary.
    """
    _require_wilderness(wilderness)
    _require_int(tick, "tick")
    if not activity_provisioned(wilderness):
        return []
    for group_id in sorted(read_monster_activity(wilderness).groups):
        state = read_monster_activity(wilderness)
        group = state.groups.get(group_id)
        if group is None or group.journey_id is not None:
            continue
        if group.next_decision_tick > tick:
            continue
        settle_group_idle(wilderness, group_id, tick=tick)
        decision = plan_group_decision(wilderness, group_id, tick=tick)
        commit_group_decision(wilderness, decision)
    return []


def activity_member_mode(individual: Any) -> str | None:
    """The activity-record mode owning ``individual``, or ``None``.

    Pure read. A provisioned world whose record cannot be interpreted answers
    ``None`` here so a caller-scoped clock stage simply keeps its ordinary
    semantics; the owner's own settlement still fails closed on that record.
    """
    from world.maps import regional_population

    wilderness = regional_population.live_wilderness()
    if wilderness is None or not activity_provisioned(wilderness):
        return None
    try:
        state = read_monster_activity(wilderness)
    except MonsterActivityError:  # observability: ignore R2: an unreadable owner record is not an activity-owned body here; the owner's own settlement still fails closed
        return None
    pk = int(getattr(individual, "pk", 0) or 0)
    for group in state.groups.values():
        if pk in group.member_ids:
            return group.member_time[str(pk)].mode
    return None


def _settle_interval(
    entity: Any,
    *,
    seconds: int,
    activity: Any,
    context: Mapping[str, Any],
    start_tick: int | None = None,
) -> None:
    """Pay one interval through the sole fatigue writer, or nothing."""
    if seconds <= 0:
        return
    from world.rules.fatigue import (
        FatigueInterval,
        IntervalCompletion,
        read_optional_fatigue_state,
        settle_fatigue_intervals,
    )

    state = read_optional_fatigue_state(entity)
    if state is None:
        return
    try:
        settle_fatigue_intervals(
            (
                FatigueInterval(
                    entity,
                    activity,
                    seconds,
                    state,
                    IntervalCompletion.INDIVISIBLE,
                ),
            ),
            context=dict(context),
            start_tick=start_tick,
        )
    except Exception as error:  # observability: R1 reported below; corrupt physiology refuses the whole boundary
        log_warn(
            "monster_activity_physiology_failed",
            exc=error,
            context={**dict(context), "individual": getattr(entity, "pk", None)},
        )
        raise


def _journey_physiology(
    individual: Any,
    *,
    seconds: int,
    context: Mapping[str, Any],
    start_tick: int | None = None,
) -> None:
    from world.rules.fatigue import FatigueActivity

    _settle_interval(
        individual,
        seconds=seconds,
        activity=FatigueActivity.FOOT_TRAVEL,
        context=context,
        start_tick=start_tick,
    )


def _waiting_physiology(
    individual: Any,
    *,
    seconds: int,
    context: Mapping[str, Any],
    start_tick: int | None = None,
) -> None:
    from world.rules.fatigue import (
        FatigueActivity,
        SleepPosture,
        read_optional_fatigue_state,
    )

    state = read_optional_fatigue_state(individual)
    activity = (
        FatigueActivity.SLEEP
        if state is not None and state.posture is not SleepPosture.AWAKE
        else FatigueActivity.AWAKE
    )
    _settle_interval(
        individual,
        seconds=seconds,
        activity=activity,
        context=context,
        start_tick=start_tick,
    )


def _idle_physiology(
    individual: Any,
    *,
    seconds: int,
    context: Mapping[str, Any],
    start_tick: int | None = None,
) -> None:
    """Pay one ordinary idle interval under the member's actual posture."""
    from world.rules.fatigue import (
        FatigueActivity,
        SleepPosture,
        read_optional_fatigue_state,
    )

    state = read_optional_fatigue_state(individual)
    activity = (
        FatigueActivity.SLEEP
        if state is not None and state.posture is not SleepPosture.AWAKE
        else FatigueActivity.AWAKE
    )
    _settle_interval(
        individual,
        seconds=seconds,
        activity=activity,
        context=context,
        start_tick=start_tick,
    )


def _destination_blocked(wilderness: Any, destination: LocationRef, tick: int) -> bool:
    from world.maps import regional_population

    if destination.kind == "wilderness":
        cell = (destination.x, destination.y)
        return cell in regional_population.protected_cells(wilderness, at_tick=tick)
    return room_protected(wilderness, destination, tick)


def _route_lawful(wilderness: Any, journey: MonsterJourney, individual: Any) -> bool:
    """Whether the committed edge is still a lawful read-only route now.

    The committed price and duration are never repriced: this only re-resolves
    discovery at the source. A vanished authored source room is corrupt route
    state and raises; a now-locked, retargeted or refusing destination is a
    temporary obstruction and contributes a positive retry, exactly like
    encounter protection.
    """
    from world.rules.movement_edges import legal_edges, room_for_ref

    del wilderness
    if journey.source.kind == "room" and room_for_ref(journey.source) is None:
        raise _invalid(
            f"journey {journey.journey_id!r} lost its authored source room"
        )
    if journey.destination.kind == "room" and room_for_ref(
        journey.destination
    ) is None:
        raise _invalid(
            f"journey {journey.journey_id!r} lost its authored destination room"
        )
    edges = legal_edges(individual, journey.source, (individual,))
    return journey.edge in edges


def _arrive(
    wilderness: Any,
    journey: MonsterJourney,
    bodies: tuple[Any, ...],
    *,
    tick: int,
    state: MonsterActivityState,
    log_events: list[ScheduledEvent],
) -> None:
    from world.maps import regional_population
    from world.rules.movement_edges import room_for_ref

    destination = journey.destination
    group = state.groups[journey.group_id]
    befores = {
        body.pk: regional_population.presence_of(wilderness, body)
        for body in bodies
    }
    if destination.kind == "wilderness":
        cell = (destination.x, destination.y)
        if not wilderness.is_valid_coordinates(cell):
            raise _invalid(f"journey {journey.journey_id!r} names an invalid destination cell")
        coordinates = dict(wilderness.db.itemcoordinates)
        for body in bodies:
            if _alive(body):
                coordinates[body] = cell
            else:
                coordinates.pop(body, None)
        wilderness.db.itemcoordinates = coordinates
        room = (wilderness.db.rooms or {}).get(cell)
        if room is not None:
            for body in bodies:
                if _alive(body):
                    body.location = room
                    room.contents_cache.add(body)
                else:
                    body.location = None
        else:
            for body in bodies:
                body.location = None
    else:
        room = room_for_ref(destination)
        if room is None:
            raise _invalid(f"journey {journey.journey_id!r} names a vanished authored room")
        for body in bodies:
            if _alive(body):
                body.location = room
                room.contents_cache.add(body)
            else:
                body.location = None
    for body in bodies:
        regional_population.record_population_transition(
            wilderness,
            regional_population.PopulationTransition(
                source_id=f"arrival:{journey.journey_id}",
                individual_id=int(body.pk),
                occurred_tick=tick,
                before=befores[body.pk],
                after=regional_population.presence_of(
                    wilderness,
                    body,
                ),
            ),
        )
    member_time_map = dict(group.member_time)
    for member_id in journey.member_ids:
        current = member_time_map.get(str(member_id))
        floor = 0 if current is None else current.settled_through_tick
        member_time_map[str(member_id)] = MemberTime(
            max(floor, tick),
            MODE_IDLE,
            None,
            (),
        )
    groups = dict(state.groups)
    groups[journey.group_id] = _replace_group(
        group,
        position=destination,
        journey_id=None,
        member_time=member_time_map,
        next_decision_tick=tick + _activity_interval(group.activity_key),
    )
    journeys = dict(state.journeys)
    journeys.pop(journey.journey_id, None)
    _write_state(wilderness, _copy_state(state, groups=groups, journeys=journeys))
    for member_id in journey.member_ids:
        context = {
            "journey": journey.journey_id,
            "group": journey.group_id,
            "individual": member_id,
            "source": encode_location_ref(journey.source),
            "destination": encode_location_ref(destination),
            "tick": tick,
        }
        transaction.on_commit(
            lambda context=context: log_info("monster_arrived", context=context)
        )
        log_events.append(ScheduledEvent("monster_arrived", tick, dict(context)))


def settle_monster_activity_at(wilderness: Any, tick: int) -> list[ScheduledEvent]:
    """Settle every due journey arrival or protected-arrival retry at ``tick``.

    Journeys settle in stable journey-id order. An arrival pays only the newly
    elapsed passage through the canonical physiology writer. When the
    destination is protected, the same journey stays between its endpoints,
    settles ordinary waiting posture, and retries at one positive decision
    interval later without repricing the passage. A retry that finds the
    destination lawful arrives in the same pass.
    """
    _require_wilderness(wilderness)
    _require_int(tick, "tick")
    if not activity_provisioned(wilderness):
        return []
    from evennia.objects.models import ObjectDB

    state = read_monster_activity(wilderness)
    events: list[ScheduledEvent] = []
    for journey_id in sorted(state.journeys):
        journey = state.journeys[journey_id]
        due = journey.retry_tick if journey.retry_tick is not None else journey.arrival_tick
        if due != tick:
            continue
        bodies = tuple(
            ObjectDB.objects.filter(id=int(member_id)).first()
            for member_id in journey.member_ids
        )
        if any(body is None for body in bodies):
            raise _invalid(f"journey {journey_id!r} names a missing individual")
        group = state.groups[journey.group_id]
        # Pay exactly the newly elapsed passage and ordinary waiting at every
        # due boundary, whether this boundary arrives or defers. A successful
        # retry therefore never loses the wait that preceded it.
        for body in bodies:
            member_time = group.member_time[str(body.pk)]
            cursor = member_time.settled_through_tick
            if _alive(body):
                travelled = min(tick, journey.arrival_tick) - min(
                    cursor, journey.arrival_tick
                )
                _journey_physiology(
                    body,
                    seconds=max(0, travelled),
                    context={"stage": "monster_journey", "journey": journey_id},
                    start_tick=cursor,
                )
                waiting = max(0, tick - max(cursor, journey.arrival_tick))
                _waiting_physiology(
                    body,
                    seconds=waiting,
                    context={"stage": "monster_journey_wait", "journey": journey_id},
                    start_tick=max(cursor, journey.arrival_tick),
                )
                _settle_gauge(body, seconds=max(0, tick - cursor))
            group = _replace_group(
                group,
                member_time={
                    **group.member_time,
                    str(body.pk): MemberTime(
                        max(cursor, tick),
                        MODE_JOURNEY,
                        member_time.session_id,
                        (),
                    ),
                },
            )
            state = _copy_state(
                state, groups={**state.groups, journey.group_id: group}
            )
        settled = max(journey.settled_through_tick, tick)
        blocked = _destination_blocked(
            wilderness, journey.destination, tick
        ) or any(
            _alive(body) and not _route_lawful(wilderness, journey, body)
            for body in bodies
        )
        if blocked:
            interval = _activity_interval(group.activity_key)
            journeys = dict(state.journeys)
            journeys[journey_id] = MonsterJourney(
                journey_id,
                journey.group_id,
                journey.member_ids,
                journey.source,
                journey.destination,
                journey.depart_tick,
                journey.arrival_tick,
                settled,
                tick + interval,
                journey.edge,
                journey.plan,
            )
            state = _copy_state(
                state,
                journeys=journeys,
                groups=_retry_group(state.groups, journey, tick + interval),
            )
            _write_state(wilderness, state)
            context = {
                "journey": journey_id,
                "individual": (
                    int(bodies[0].pk)
                    if len(bodies) == 1
                    else tuple(int(body.pk) for body in bodies)
                ),
                "destination": encode_location_ref(journey.destination),
                "tick": tick,
                "retry_tick": tick + interval,
            }
            transaction.on_commit(
                lambda context=context: log_info(
                    "monster_arrival_deferred", context=context
                )
            )
            events.append(
                ScheduledEvent("monster_arrival_deferred", tick, dict(context))
            )
            continue
        journey = MonsterJourney(
            journey_id,
            journey.group_id,
            journey.member_ids,
            journey.source,
            journey.destination,
            journey.depart_tick,
            journey.arrival_tick,
            settled,
            None,
            journey.edge,
            journey.plan,
        )
        state = _copy_state(
            state,
            journeys={**state.journeys, journey_id: journey},
        )
        _arrive(
            wilderness,
            journey,
            bodies,
            tick=tick,
            state=state,
            log_events=events,
        )
        state = read_monster_activity(wilderness)
    if state.settled_through_tick < tick:
        _write_state(wilderness, _copy_state(state, settled_through_tick=tick))
    return events


def _retry_group(
    groups: Mapping[str, MonsterGroup], journey: MonsterJourney, retry_tick: int
) -> dict[str, MonsterGroup]:
    result = dict(groups)
    group = groups.get(journey.group_id)
    if group is not None:
        result[journey.group_id] = _replace_group(group, next_decision_tick=retry_tick)
    return result


def next_monster_activity_boundary(
    wilderness: Any, after: int, end: int
) -> int | None:
    """The earliest due journey or idle-decision boundary after ``after``."""
    if wilderness is None or not activity_provisioned(wilderness):
        return None
    state = read_monster_activity(wilderness)
    candidates: list[int] = []
    for journey in state.journeys.values():
        due = journey.retry_tick if journey.retry_tick is not None else journey.arrival_tick
        if after < due <= end:
            candidates.append(due)
    for group in state.groups.values():
        if group.journey_id is not None:
            continue
        due = group.next_decision_tick
        if after < due <= end:
            candidates.append(due)
    return min(candidates) if candidates else None


def retire_room_protection(wilderness: Any, tick: int) -> None:
    """Consume closed room protection once chronological progress passes it."""
    if not activity_provisioned(wilderness):
        return
    state = read_monster_activity(wilderness)
    remaining = tuple(
        item
        for item in state.room_protection
        if item.end_tick is None or item.end_tick >= tick
    )
    if len(remaining) != len(state.room_protection):
        _write_state(wilderness, _copy_state(state, room_protection=remaining))


# ---------------------------------------------------------------------------
# Surfaces for a caller-owned rollback


def _db_safe_attribute_snapshot(
    obj: Any, key: str, category: str | None = None
) -> tuple[bool, Any]:
    from evennia.utils import dbserialize

    exists = obj.attributes.has(key, category=category)
    value = (
        dbserialize.from_pickle(
            dbserialize.to_pickle(obj.attributes.get(key, category=category))
        )
        if exists
        else None
    )
    return exists, value


def _tracked_individual_ids(state: MonsterActivityState) -> tuple[int, ...]:
    members: set[int] = set()
    for group in state.groups.values():
        members.update(group.member_ids)
    for journey in state.journeys.values():
        members.update(journey.member_ids)
    return tuple(sorted(members))


def snapshot_monster_activity_surfaces(
    start_tick: int, end_tick: int
) -> dict[int, SurfaceSnapshot]:
    """The clock advance-surface contract of this owner (pure read)."""
    from world.maps import regional_population

    wilderness = regional_population.live_wilderness()
    if wilderness is None or not regional_population.population_provisioned(wilderness):
        return {}
    return snapshot_activity_surfaces(wilderness)


def snapshot_activity_surfaces(wilderness: Any) -> dict[int, SurfaceSnapshot]:
    """Snapshot every durable and live surface one activity write may touch."""
    from evennia.objects.models import ObjectDB

    from world.rules.fatigue import FATIGUE_ATTRIBUTE_SURFACES
    from world.rules.sleep_receipt import SLEEP_RECEIPT_SURFACES

    surfaces: dict[int, SurfaceSnapshot] = {
        id(wilderness): SurfaceSnapshot(
            attributes={
                (MONSTER_ACTIVITY_ATTRIBUTE, None): _db_safe_attribute_snapshot(
                    wilderness, MONSTER_ACTIVITY_ATTRIBUTE
                ),
            }
        )
    }
    try:
        state = read_monster_activity(wilderness)
    except MonsterActivityError:  # observability: ignore R2: a malformed record still snapshots its own attribute; the write refuses before any member is read
        return surfaces
    for individual_id in _tracked_individual_ids(state):
        individual = ObjectDB.objects.filter(id=individual_id).first()
        if individual is None:
            continue
        location = getattr(individual, "location", None)
        surfaces[id(individual)] = SurfaceSnapshot(
            attributes={
                (key, category): _db_safe_attribute_snapshot(
                    individual, key, category
                )
                for key, category in (
                    # Gauge regeneration is settled by this owner for its
                    # bodies, so the durable trait store belongs to the same
                    # rollback contract as fatigue and receipts.
                    ("traits", "traits"),
                    *FATIGUE_ATTRIBUTE_SURFACES,
                    *SLEEP_RECEIPT_SURFACES,
                )
            },
            location=(location is not None, getattr(location, "pk", None)),
        )
    return surfaces


def snapshot_departure_surfaces(wilderness: Any) -> dict[int, SurfaceSnapshot]:
    """The departure effect's snapshot, including coordinates and timeline."""
    from world.maps import regional_population as owner

    surfaces = snapshot_activity_surfaces(wilderness)
    surfaces[id(wilderness)] = SurfaceSnapshot(
        attributes={
            **surfaces[id(wilderness)].attributes,
            (owner.POPULATION_TIMELINE_ATTRIBUTE, None): _db_safe_attribute_snapshot(
                wilderness, owner.POPULATION_TIMELINE_ATTRIBUTE
            ),
            (owner.ITEMCOORDINATES_ATTRIBUTE, None): _db_safe_attribute_snapshot(
                wilderness, owner.ITEMCOORDINATES_ATTRIBUTE
            ),
        }
    )
    return surfaces


def restore_activity_surfaces(
    snapshot: Mapping[int, SurfaceSnapshot], *, wilderness: Any | None = None
) -> None:
    """Restore durability and live caches after a rolled-back activity write."""
    from evennia.objects.models import ObjectDB
    from evennia.scripts.models import ScriptDB

    from world.maps import regional_population

    candidates = {
        id(instance): instance
        for instance in (
            *ObjectDB.get_all_cached_instances(),
            *ScriptDB.get_all_cached_instances(),
        )
    }
    if wilderness is not None:
        candidates[id(wilderness)] = wilderness
    for object_id, surface in snapshot.items():
        obj = candidates.get(object_id)
        if obj is None or getattr(obj, "_is_deleted", False):
            continue
        for (key, category), value in surface.attributes.items():
            regional_population._restore_attribute(obj, key, category, value)
        if surface.location is not None:
            existed, target_pk = surface.location
            try:
                target = (
                    ObjectDB.objects.filter(id=target_pk).first()
                    if existed and target_pk is not None
                    else None
                )
                obj.location = target
                if target is not None:
                    target.contents_cache.clear()
            except Exception as error:  # observability: ignore R2: the warn below is this facade event
                log_warn(
                    "rollback_restore_failed",
                    exc=error,
                    context={"stage": "monster_activity_location", "obj": str(obj)},
                )
    from world.rules.clock import _refresh_advance_entity_caches

    for object_id in snapshot:
        obj = candidates.get(object_id)
        if obj is None or getattr(obj, "_is_deleted", False):
            continue
        if hasattr(obj, "attributes"):
            try:
                obj.attributes.reset_cache()
            except Exception as error:  # observability: ignore R2: the warn below reports the failed cache refresh
                log_warn(
                    "rollback_restore_failed",
                    exc=error,
                    context={
                        "stage": "monster_activity_attribute_cache",
                        "obj": str(obj),
                    },
                )
            _refresh_advance_entity_caches(obj)
    regional_population.restore_population_surfaces(snapshot)


__all__ = [
    "ACTIVITY_AWAKE_COMBAT",
    "ACTIVITY_SLEEP",
    "COMBAT_ACTIVITIES",
    "DECISION_DEPART",
    "DECISION_PURPOSE",
    "DECISION_STAY",
    "DEFAULT_DECISION_INTERVAL",
    "STAY_IN_JOURNEY",
    "STAY_MEMBER_BLOCKED",
    "STAY_MEMBER_DISPLACED",
    "STAY_MEMBER_ENGAGED",
    "STAY_MEMBER_SETTLED_AHEAD",
    "STAY_MEMBER_SLEEPING",
    "STAY_MEMBER_UNAFFORDABLE",
    "STAY_NO_LEGAL_ROUTE",
    "STAY_NO_LIVING_MEMBERS",
    "STAY_OUTSIDE_BOUNDS_WAITING",
    "STAY_STATIONARY",
    "STAY_UNPUBLISHED_BINDING",
    "ActivityDecision",
    "ActivityReceipt",
    "CombatInterval",
    "JourneyPlan",
    "MemberTime",
    "MonsterActivityError",
    "MonsterActivityOperationInvalid",
    "MonsterActivityState",
    "MonsterActivityStateInvalid",
    "MonsterGroup",
    "MonsterJourney",
    "MONSTER_ACTIVITY_ATTRIBUTE",
    "MODE_COMBAT",
    "MODE_IDLE",
    "MODE_JOURNEY",
    "OWNER_KINDS",
    "PlanLeg",
    "PlanMember",
    "PlanSegment",
    "RECEIPT_DEPARTURE",
    "RoomProtection",
    "STAGED_DECISION_INTERVAL",
    "STAGED_STATIONARY_ACTIVITY",
    "STATE_INVALID",
    "activity_member_mode",
    "activity_provisioned",
    "begin_monster_journey",
    "commit_group_decision",
    "create_group",
    "decision_interval",
    "decode_fraction",
    "encode_fraction",
    "group",
    "group_fingerprint",
    "group_id_for",
    "group_of_member",
    "group_from_dict",
    "group_to_dict",
    "initialize_monster_activity",
    "journey",
    "journey_from_dict",
    "journey_to_dict",
    "mark_member_combat",
    "next_monster_activity_boundary",
    "plan_group_decision",
    "plan_from_dict",
    "plan_to_dict",
    "read_monster_activity",
    "receipt",
    "record_combat_interval",
    "record_room_protection",
    "release_group",
    "restore_activity_surfaces",
    "retire_room_protection",
    "room_protected",
    "settle_group_decisions_at",
    "settle_group_idle",
    "settle_idle_physiology",
    "settle_monster_activity_at",
    "snapshot_activity_surfaces",
    "snapshot_departure_surfaces",
    "snapshot_monster_activity_surfaces",
    "state_from_dict",
    "state_to_dict",
    "update_member_time",
]
