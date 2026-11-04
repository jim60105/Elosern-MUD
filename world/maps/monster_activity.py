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
    for key, member_id in _member_index(groups).items():
        if key in groups:
            raise _invalid(f"member {member_id} belongs to more than one group")
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
    if group.journey_id is not None:
        raise MonsterActivityOperationInvalid(
            "monster_activity_group_in_journey", f"group {group_id!r} is already travelling"
        )
    if individual_id not in group.member_ids:
        raise MonsterActivityOperationInvalid(
            "monster_activity_member_unknown",
            f"member {individual_id} does not belong to group {group_id!r}",
        )
    if group.sequence != expected_sequence:
        raise MonsterActivityOperationInvalid(
            "monster_activity_sequence_stale",
            f"group {group_id!r} sequence is {group.sequence}, expected {expected_sequence}",
        )
    if group.position != source:
        raise MonsterActivityOperationInvalid(
            "monster_activity_source_moved",
            f"group {group_id!r} no longer stands at {source}",
        )
    if edge.source != source or edge.destination != destination:
        raise MonsterActivityOperationInvalid(
            "monster_activity_edge_mismatch", "the edge endpoints differ from the selected route"
        )
    if plan.seconds < 0:
        raise MonsterActivityOperationInvalid("the committed plan duration is invalid")
    if {member.individual_id for member in plan.members} != {individual_id}:
        raise MonsterActivityOperationInvalid(
            "monster_activity_plan_members", "the plan must name exactly the departing member"
        )
    from evennia.objects.models import ObjectDB

    from world.maps import regional_population

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
    remaining = tuple(
        member_id for member_id in group.member_ids if member_id != individual_id
    )
    new_group_id = group_id if not remaining else f"{group_id}~{individual_id}"
    if not remaining:
        groups = dict(state.groups)
        groups.pop(group_id, None)
    else:
        groups = dict(state.groups)
    member_time_map = dict(group.member_time)
    member_time_map.pop(str(individual_id), None)
    if remaining:
        groups[group_id] = _replace_group(
            group,
            member_ids=remaining,
            sequence=group.sequence + 1,
            member_time=member_time_map,
        )
    arriving_member_time = {str(individual_id): member_time}
    journey_id = f"journey:{operation_id}"
    arrival_tick = depart_tick + plan.seconds
    new_group = MonsterGroup(
        group_id=new_group_id,
        member_ids=(individual_id,),
        home_owner=group.home_owner,
        activity_key=group.activity_key,
        home=group.home,
        position=None,
        journey_id=journey_id,
        next_decision_tick=arrival_tick + _activity_interval(group.activity_key),
        sequence=0,
        seed=group.seed,
        member_time=arriving_member_time,
    )
    groups[new_group_id] = new_group
    journey = MonsterJourney(
        journey_id=journey_id,
        group_id=new_group_id,
        member_ids=(individual_id,),
        source=source,
        destination=destination,
        depart_tick=depart_tick,
        arrival_tick=arrival_tick,
        settled_through_tick=depart_tick,
        retry_tick=None,
        edge=edge,
        plan=plan,
    )
    journeys = dict(state.journeys)
    journeys[journey_id] = journey
    receipts = dict(state.receipts)
    receipts[operation_id] = ActivityReceipt(
        operation_id,
        RECEIPT_DEPARTURE,
        new_group_id,
        journey_id,
        individual_id,
        depart_tick,
    )

    before = regional_population.presence_of(
        wilderness,
        individual,
        alive=True,
        cell=(source.x, source.y) if source.kind == "wilderness" else None,
    )
    if source.kind == "wilderness":
        coordinates = dict(wilderness.db.itemcoordinates)
        coordinates.pop(individual, None)
        wilderness.db.itemcoordinates = coordinates
        room = _source_room(wilderness, (source.x, source.y))
        if room is not None:
            room.contents_cache.init()
    individual.location = None
    after = regional_population.presence_of(wilderness, individual, alive=True)
    regional_population.record_population_transition(
        wilderness,
        regional_population.PopulationTransition(
            source_id=operation_id,
            individual_id=individual_id,
            occurred_tick=depart_tick,
            before=before,
            after=after,
        ),
    )
    _write_state(
        wilderness,
        _copy_state(state, groups=groups, journeys=journeys, receipts=receipts),
    )
    context = {
        "operation": operation_id,
        "group": new_group_id,
        "individual": individual_id,
        "source": encode_location_ref(source),
        "destination": encode_location_ref(destination),
        "journey": journey_id,
        "tick": depart_tick,
    }
    transaction.on_commit(lambda context=context: log_info("monster_departed", context=context))
    transaction.on_commit(
        lambda context=context: log_info("monster_escape_resolved", context=context)
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

    The prior idle prefix is closed at ``tick`` (this change owns no idle
    writer; the journey/activity slice settles the elapsed posture there), and
    the member's owner becomes exactly this session. A member already owned by
    the same session is unchanged.
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


def _settle_interval(
    entity: Any,
    *,
    seconds: int,
    activity: Any,
    context: Mapping[str, Any],
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
        )
    except Exception as error:  # observability: R1 reported below; corrupt physiology refuses the whole boundary
        log_warn(
            "monster_activity_physiology_failed",
            exc=error,
            context={**dict(context), "individual": getattr(entity, "pk", None)},
        )
        raise


def _journey_physiology(
    individual: Any, *, seconds: int, context: Mapping[str, Any]
) -> None:
    from world.rules.fatigue import FatigueActivity

    _settle_interval(
        individual,
        seconds=seconds,
        activity=FatigueActivity.FOOT_TRAVEL,
        context=context,
    )


def _waiting_physiology(
    individual: Any, *, seconds: int, context: Mapping[str, Any]
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
        individual, seconds=seconds, activity=activity, context=context
    )


def _destination_blocked(wilderness: Any, destination: LocationRef, tick: int) -> bool:
    from world.maps import regional_population

    if destination.kind == "wilderness":
        cell = (destination.x, destination.y)
        return cell in regional_population.protected_cells(wilderness, at_tick=tick)
    return room_protected(wilderness, destination, tick)


def _arrive(
    wilderness: Any,
    journey: MonsterJourney,
    individual: Any,
    *,
    tick: int,
    state: MonsterActivityState,
    log_events: list[ScheduledEvent],
) -> None:
    from world.maps import regional_population
    from world.rules.movement_edges import room_for_ref

    destination = journey.destination
    group = state.groups[journey.group_id]
    member_time = group.member_time[str(journey.member_ids[0])]
    before = regional_population.presence_of(wilderness, individual, alive=True)
    if destination.kind == "wilderness":
        cell = (destination.x, destination.y)
        if not wilderness.is_valid_coordinates(cell):
            raise _invalid(f"journey {journey.journey_id!r} names an invalid destination cell")
        coordinates = dict(wilderness.db.itemcoordinates)
        coordinates[individual] = cell
        wilderness.db.itemcoordinates = coordinates
        room = (wilderness.db.rooms or {}).get(cell)
        if room is not None:
            room.contents_cache.add(individual)
            individual.location = room
        else:
            individual.location = None
        after = regional_population.presence_of(
            wilderness, individual, alive=True, cell=cell
        )
    else:
        room = room_for_ref(destination)
        if room is None:
            raise _invalid(f"journey {journey.journey_id!r} names a vanished authored room")
        individual.location = room
        room.contents_cache.add(individual)
        after = regional_population.presence_of(wilderness, individual, alive=True)
    regional_population.record_population_transition(
        wilderness,
        regional_population.PopulationTransition(
            source_id=f"arrival:{journey.journey_id}",
            individual_id=journey.member_ids[0],
            occurred_tick=tick,
            before=before,
            after=after,
        ),
    )
    member_time_map = {
        key: member_time if key == str(journey.member_ids[0]) else value
        for key, value in group.member_time.items()
    }
    member_time_map[str(journey.member_ids[0])] = MemberTime(
        max(journey.settled_through_tick, journey.arrival_tick),
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
    context = {
        "journey": journey.journey_id,
        "group": journey.group_id,
        "individual": journey.member_ids[0],
        "source": encode_location_ref(journey.source),
        "destination": encode_location_ref(destination),
        "tick": tick,
    }
    transaction.on_commit(lambda context=context: log_info("monster_arrived", context=context))
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
        individual_id = journey.member_ids[0]
        individual = ObjectDB.objects.filter(id=individual_id).first()
        if individual is None:
            raise _invalid(f"journey {journey_id!r} names a missing individual")
        group = state.groups[journey.group_id]
        if _destination_blocked(wilderness, journey.destination, tick):
            interval = _activity_interval(group.activity_key)
            travelled = min(tick, journey.arrival_tick) - min(
                journey.settled_through_tick, journey.arrival_tick
            )
            _journey_physiology(
                individual,
                seconds=max(0, travelled),
                context={"stage": "monster_journey", "journey": journey_id},
            )
            waiting = max(
                0, tick - max(journey.settled_through_tick, journey.arrival_tick)
            )
            _waiting_physiology(
                individual,
                seconds=waiting,
                context={"stage": "monster_journey_wait", "journey": journey_id},
            )
            journeys = dict(state.journeys)
            journeys[journey_id] = MonsterJourney(
                journey_id,
                journey.group_id,
                journey.member_ids,
                journey.source,
                journey.destination,
                journey.depart_tick,
                journey.arrival_tick,
                max(journey.settled_through_tick, tick),
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
                "individual": individual_id,
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
        travelled = min(tick, journey.arrival_tick) - min(
            journey.settled_through_tick, journey.arrival_tick
        )
        _journey_physiology(
            individual,
            seconds=max(0, travelled),
            context={"stage": "monster_journey", "journey": journey_id},
        )
        journey = MonsterJourney(
            journey_id,
            journey.group_id,
            journey.member_ids,
            journey.source,
            journey.destination,
            journey.depart_tick,
            journey.arrival_tick,
            max(journey.settled_through_tick, tick),
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
            individual,
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
    """The earliest due arrival or retry strictly after ``after`` up to ``end``."""
    if wilderness is None or not activity_provisioned(wilderness):
        return None
    state = read_monster_activity(wilderness)
    candidates: list[int] = []
    for journey in state.journeys.values():
        due = journey.retry_tick if journey.retry_tick is not None else journey.arrival_tick
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


def _db_safe_attribute_snapshot(obj: Any, key: str) -> tuple[bool, Any]:
    from evennia.utils import dbserialize

    exists = obj.attributes.has(key)
    value = (
        dbserialize.from_pickle(dbserialize.to_pickle(obj.attributes.get(key)))
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
                (key, category): _db_safe_attribute_snapshot(individual, key)
                for key, category in FATIGUE_ATTRIBUTE_SURFACES
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
    regional_population.restore_population_surfaces(snapshot)


__all__ = [
    "ACTIVITY_AWAKE_COMBAT",
    "ACTIVITY_SLEEP",
    "COMBAT_ACTIVITIES",
    "DEFAULT_DECISION_INTERVAL",
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
    "activity_provisioned",
    "begin_monster_journey",
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
    "settle_monster_activity_at",
    "snapshot_activity_surfaces",
    "snapshot_departure_surfaces",
    "snapshot_monster_activity_surfaces",
    "state_from_dict",
    "state_to_dict",
    "update_member_time",
]
