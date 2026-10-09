"""Triggerable simulated-battle guild examinations (guild-economy D-7).

``start_guild_exam`` is the sole examination trigger; ``requested_by`` is audit
metadata, never authority. The opponent is the branch-qualified persistent
adventurer (persistent-guild-exam-lifecycle): the start validates the local
counter, host qualification/presence/service state, exact next rank, the true
cumulative merit threshold and absence of active combat/exam, then issues the
exam kit, activates the restriction and schedule hold, restores both sides to
full HP/MP/SP and opens a ``guild_exam`` combat session as one all-or-nothing
operation. The exam is a simulated lethal battle; every terminal outcome
restores the host's normal outfit/effects and both sides' full pools, and
never deletes the host. Settlement is idempotent by exam ID and promotes
exactly one rank on PASS.
"""

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from django.db import transaction

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer
from typeclasses.npcs import NPC
from world.observability import log_info, log_warn
from world.rules.equipment import normalized_equipment
from world.rules.exam_schedule_holds import (
    begin_exam_schedule_hold,
    read_exam_schedule_hold,
    release_exam_schedule_hold,
    restore_exam_schedule_hold_surfaces,
    snapshot_exam_schedule_hold_surfaces,
)
from world.rules.guild import parse_guild_registration
from world.rules.guild_config import get_catalog
from world.rules import guild_exam_restrictions
from world.rules.guild_exam_restrictions import (
    RestrictionError,
    activate_exam_restriction,
    preflight_exam_restriction,
)
from world.rules.human_guild_hosts import GuildHostIntegrityError, qualified_host
from world.rules.npc_schedules import interaction_reason
from world.rules.service_gate import REASON_REMOTE, service_available
from world.rules.surfaces import (
    attribute_snapshot,
    read_counter_trait,
    restore_traits,
    snapshot_traits,
)
from world.skills.restrictions import exam_restriction


class GuildExamError(ValueError):
    """An examination operation violates the deterministic exam contract."""


# Exam-pass observers (title-system change G nomination trigger seam):
# registered by the composition-root service at server start, called once
# after a PASS settlement's transaction block completes. Observers must defer
# their side effects through ``transaction.on_commit`` (an outer transaction
# may still own the commit) and a raising observer is isolated and logged —
# settlement semantics never change because of an observer.
_EXAM_PASS_OBSERVERS: list[Callable[[Any, str], None]] = []


def register_exam_pass_observer(observer: Callable[[Any, str], None]) -> None:
    """Idempotently install one exam-pass observer."""
    if observer not in _EXAM_PASS_OBSERVERS:
        _EXAM_PASS_OBSERVERS.append(observer)


def _notify_exam_pass(actor: Any, target_rank: str) -> None:
    for observer in tuple(_EXAM_PASS_OBSERVERS):
        try:
            observer(actor, target_rank)
        except Exception as error:  # noqa: BLE001 - isolation is the contract
            log_warn(
                "exam_pass_observer_failed",
                exc=error,
                context={"observer": getattr(observer, "__qualname__", str(observer))},
            )


class ExamReason(StrEnum):
    NOT_A_PLAYER = "not_a_player"
    NO_EXAMINER = "no_examiner"
    REMOTE_EXAMINER = "remote_examiner"
    # Co-located but the shared anchoring gate refused (off-anchor place
    # examiner or malformed stored binding); the line is the gate's message.
    SERVICE_UNAVAILABLE = "service_unavailable"
    UNREGISTERED = "unregistered"
    WRONG_BRANCH = "wrong_branch"
    NOT_NEXT_RANK = "not_next_rank"
    BELOW_THRESHOLD = "below_threshold"
    ACTIVE_COMBAT = "active_combat"
    DUPLICATE_ACTIVE = "duplicate_active"
    UNKNOWN_PROFILE = "unknown_profile"
    MALFORMED_RECORD = "malformed_record"
    UNQUALIFIED_EXAMINER = "unqualified_examiner"
    PARTICIPANT_NAME_COLLISION = "participant_name_collision"
    EXAMINER_ENGAGED = "examiner_engaged"
    ALREADY_SETTLED = "already_settled"
    NOT_SETTLABLE = "not_settlable"
    UNKNOWN_EXAM = "unknown_exam"
    # Present qualified host whose schedule state blocks guild service.
    EXAMINER_BUSY = "examiner_busy"
    # The local counter's own schedule state blocks guild service.
    SCHEDULE_BLOCKED = "schedule_blocked"
    # Absent host whose next planned attendance cannot be confirmed; the
    # service-window reader's named reason rides ``args[1]``.
    ATTENDANCE_UNKNOWN = "attendance_unknown"


_RECORD_FIELDS = frozenset(
    {
        "exam_id",
        "character_id",
        "target_rank",
        "requested_by",
        "opponent_id",
        "session_id",
        "state",
        "terminal_reason",
    }
)


class ExamState(StrEnum):
    ACTIVE = "active"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True)
class GuildExamRecord:
    """A frozen JSON-safe record of one guild examination attempt."""

    exam_id: str
    character_id: int
    target_rank: str
    requested_by: str
    opponent_id: int
    session_id: str
    state: ExamState
    terminal_reason: str | None


def to_storage(record: GuildExamRecord) -> dict[str, Any]:
    return {
        "exam_id": record.exam_id,
        "character_id": record.character_id,
        "target_rank": record.target_rank,
        "requested_by": record.requested_by,
        "opponent_id": record.opponent_id,
        "session_id": record.session_id,
        "state": record.state.value,
        "terminal_reason": record.terminal_reason,
    }


def from_storage(data: dict[str, Any]) -> GuildExamRecord:
    if not isinstance(data, dict):
        raise GuildExamError(ExamReason.MALFORMED_RECORD)
    unknown = set(data) - _RECORD_FIELDS
    if unknown:
        raise GuildExamError(
            ExamReason.MALFORMED_RECORD, f"unknown fields {sorted(unknown)}"
        )
    missing = _RECORD_FIELDS - set(data)
    if missing:
        raise GuildExamError(
            ExamReason.MALFORMED_RECORD, f"missing fields {sorted(missing)}"
        )
    exam_id = data["exam_id"]
    target_rank = data["target_rank"]
    requested_by = data["requested_by"]
    session_id = data["session_id"]
    if not all(isinstance(v, str) and v for v in (exam_id, target_rank, requested_by, session_id)):
        raise GuildExamError(ExamReason.MALFORMED_RECORD)
    character_id = data["character_id"]
    opponent_id = data["opponent_id"]
    if isinstance(character_id, bool) or not isinstance(character_id, int):
        raise GuildExamError(ExamReason.MALFORMED_RECORD)
    if isinstance(opponent_id, bool) or not isinstance(opponent_id, int):
        raise GuildExamError(ExamReason.MALFORMED_RECORD)
    state_value = data["state"]
    if state_value not in {s.value for s in ExamState}:
        raise GuildExamError(ExamReason.MALFORMED_RECORD)
    terminal_reason = data["terminal_reason"]
    if terminal_reason is not None and not isinstance(terminal_reason, str):
        raise GuildExamError(ExamReason.MALFORMED_RECORD)
    return GuildExamRecord(
        exam_id=exam_id,
        character_id=character_id,
        target_rank=target_rank,
        requested_by=requested_by,
        opponent_id=opponent_id,
        session_id=session_id,
        state=ExamState(state_value),
        terminal_reason=terminal_reason,
    )


def _read_exams(actor: Any) -> list[GuildExamRecord]:
    raw = actor.db.guild_exams
    if raw is None:
        return []
    try:
        raw_list = list(raw)
    except (TypeError, ValueError) as error:
        raise GuildExamError(ExamReason.MALFORMED_RECORD, str(error)) from error
    records = [from_storage(dict(entry)) for entry in raw_list]
    seen: set[str] = set()
    for record in records:
        if record.exam_id in seen:
            raise GuildExamError(ExamReason.MALFORMED_RECORD)
        seen.add(record.exam_id)
    return records


def _write_exams(actor: Any, records: list[GuildExamRecord]) -> None:
    actor.db.guild_exams = [to_storage(record) for record in records]


def _find_active_exam(records: list[GuildExamRecord]) -> GuildExamRecord | None:
    return next(
        (record for record in records if record.state is ExamState.ACTIVE),
        None,
    )


def _attempt_number(records: list[GuildExamRecord], target_rank: str) -> int:
    return sum(1 for record in records if record.target_rank == target_rank) + 1


def _rank_order(rank_key: str) -> int:
    from world.lore.guild import GUILD_RANK_REGISTRY

    rank = GUILD_RANK_REGISTRY.get(rank_key)
    if rank is None:
        raise GuildExamError(ExamReason.MALFORMED_RECORD, f"unknown rank {rank_key!r}")
    return rank.order


def _valid_age(value: Any) -> bool:
    return type(value) is int and 0 <= value <= 10000


def _local_exam_counter(actor: Any) -> tuple[Any, Any]:
    """Return the single co-located guild counter carrying examination service.

    The counter (the branch's GuildExaminer component holder) owns the place
    gate and branch identity; the persistent adventurer who fights carries no
    service component of its own.
    """
    from world.rules.guild import GuildServiceError, resolve_local_service_host

    try:
        counter = resolve_local_service_host(actor, GuildExaminer)
    except GuildServiceError as error:
        raise GuildExamError(ExamReason.NO_EXAMINER) from error
    return counter, counter.components.get(GuildExaminer.get_component_slot())


def _counter_branch(actor: Any, counter: Any = None) -> str:
    """Validate the exam counter's shared gate and return its branch key.

    ``counter`` defaults to the single co-located GuildExaminer holder; an
    explicit counter (the NPC speaking an exam intent) is gated identically.
    """
    if counter is None:
        counter, component = _local_exam_counter(actor)
    else:
        component = counter.components.get(GuildExaminer.get_component_slot())
    verdict = service_available(actor, counter, component)
    if not verdict.allowed:
        if verdict.reason == REASON_REMOTE:
            raise GuildExamError(ExamReason.REMOTE_EXAMINER)
        raise GuildExamError(ExamReason.SERVICE_UNAVAILABLE)
    registration = parse_guild_registration(actor)
    if registration is None:
        raise GuildExamError(ExamReason.UNREGISTERED)
    if registration["branch_key"] != component.branch_key:
        raise GuildExamError(ExamReason.WRONG_BRANCH)
    return component.branch_key


def _require_next_rank(actor: Any, target_rank: str) -> None:
    from world.lore.guild import GUILD_RANK_REGISTRY

    actor_rank = actor.guild_rank
    if actor_rank not in GUILD_RANK_REGISTRY:
        raise GuildExamError(ExamReason.MALFORMED_RECORD, "actor has no valid rank")
    if target_rank not in GUILD_RANK_REGISTRY or (
        _rank_order(target_rank) != _rank_order(actor_rank) + 1
    ):
        raise GuildExamError(ExamReason.NOT_NEXT_RANK)


def _is_exam_counter(npc: Any) -> bool:
    components = getattr(npc, "components", None)
    return components is not None and components.has(GuildExaminer.name)


@dataclass(frozen=True)
class ExamRequestTarget:
    """The server-derived authority and opponent of one examination request."""

    counter: Any
    branch_key: str
    host: NPC


def resolve_exam_request_target(
    actor: Any, target_rank: str, *, speaker: Any = None
) -> ExamRequestTarget:
    """Resolve the counter, branch and branch-qualified persistent host.

    Read-only identity selection shared by the request coordinator: the
    branch comes from the exam counter, the person from the qualification
    binding and the object from persistent provenance, never from a
    display-name search or a generic examiner component. ``speaker`` (an NPC
    voicing an exam intent) grants no authority: it must stand beside the
    actor and be either the counter itself or the qualified host. The
    counter's own schedule gate applies; no merit, battle, attendance or
    host-service check happens here.
    """
    if speaker is not None and (
        actor.location is None or getattr(speaker, "location", None) != actor.location
    ):
        raise GuildExamError(ExamReason.REMOTE_EXAMINER)
    if speaker is not None and _is_exam_counter(speaker):
        counter = speaker
    else:
        counter, _ = _local_exam_counter(actor)
    # A busy or resting counter clerk takes no request at all (the same
    # first gate every other guild counter surface applies).
    if interaction_reason(counter, "service_guild") is not None:
        raise GuildExamError(ExamReason.SCHEDULE_BLOCKED)
    branch_key = _counter_branch(actor, counter)
    _require_next_rank(actor, target_rank)
    try:
        host = qualified_host(branch_key, target_rank)
    except GuildHostIntegrityError as error:
        raise GuildExamError(ExamReason.UNQUALIFIED_EXAMINER) from error
    if speaker is not None and speaker is not counter and speaker.pk != host.pk:
        raise GuildExamError(ExamReason.NO_EXAMINER)
    return ExamRequestTarget(counter=counter, branch_key=branch_key, host=host)


def qualified_exam_host(actor: Any, target_rank: str, *, speaker: Any = None) -> NPC:
    """Return only the qualified persistent host of one examination request."""
    return resolve_exam_request_target(actor, target_rank, speaker=speaker).host


# Host-side surfaces the examination lifecycle writes. The persisted
# normal-state attribute holds the host's own outfit/effects so restoration
# never depends on the candidate's exam record.
NORMAL_STATE_ATTRIBUTE = "guild_exam_normal_state"
_HOST_ATTRIBUTES = (
    "guild_exam_restriction",
    NORMAL_STATE_ATTRIBUTE,
    "equipment",
    "inventory",
    "buffs",
    "relations_data",
)


def snapshot_exam_host_surfaces(host: Any) -> dict[str, Any]:
    """Snapshot every host surface an exam start, round or settlement writes."""
    return {
        "attributes": {key: attribute_snapshot(host, key) for key in _HOST_ATTRIBUTES},
        "traits": snapshot_traits(host),
        "hold": snapshot_exam_schedule_hold_surfaces(host),
    }


def restore_exam_host_surfaces(host: Any, snapshot: dict[str, Any]) -> None:
    """Restore host storage and in-process caches after a rolled-back write."""
    from world.rules.surfaces import restore_attribute_best_effort

    for key, value in snapshot["attributes"].items():
        restore_attribute_best_effort(host, key, value)
    restore_traits(host, snapshot["traits"])
    restore_exam_schedule_hold_surfaces(host, snapshot["hold"])


def _host_engaged(host: Any) -> bool:
    """Whether the host already belongs to an exam or battle (fail closed)."""
    from world.rules.combat import is_battle_over
    from world.rules.skip_safety import _active_battlefield_for

    battlefield = _active_battlefield_for(host)
    if battlefield is not None and not is_battle_over(battlefield) and any(
        entity is host for entity in battlefield.roster.values()
    ):
        return True
    if host.attributes.has(NORMAL_STATE_ATTRIBUTE):
        return True
    try:
        if exam_restriction(host) is not None:
            return True
    except ValueError:  # observability: ignore R2: a malformed restriction fails closed as engaged; the start rejects with a stable reason
        return True
    hold = read_exam_schedule_hold(host)
    return not hold.known or (hold.hold is not None and not hold.hold.released)


def _exam_kit(target_rank: str) -> dict[str, Any]:
    """The exam-owned military pair with an empty accessory loadout."""
    profile = guild_exam_restrictions.PROFILES.get(target_rank)
    if profile is None:
        raise GuildExamError(ExamReason.UNQUALIFIED_EXAMINER, target_rank)
    return {
        "weapon_main": profile.weapon,
        "weapon_off": None,
        "armor": profile.armor,
        "accessories": [],
    }


def _install_exam_kit(host: Any, exam_id: str, start_tick: int, kit: dict[str, Any]) -> None:
    """Persist the normal outfit/effects, then issue and wear the exam kit."""
    from world.rules.equipment import sync_equipment_gauge_limits

    equipment = normalized_equipment(host)
    if equipment is None:
        raise GuildExamError(ExamReason.UNQUALIFIED_EXAMINER, "malformed host equipment")
    inventory = list(host.db.inventory or [])
    host.attributes.add(NORMAL_STATE_ATTRIBUTE, {
        "exam_id": exam_id,
        "start_tick": start_tick,
        "equipment": deepcopy(equipment),
        "inventory": list(inventory),
        "buffs": attribute_snapshot(host, "buffs"),
    })
    issued = list(inventory)
    for key in (kit["weapon_main"], kit["armor"]):
        if key is not None and key not in issued:
            issued.append(key)
    host.db.inventory = issued
    host.db.equipment = deepcopy(kit)
    sync_equipment_gauge_limits(host)


def restore_exam_host(host: Any, exam_id: str) -> None:
    """Return a persistent host to its normal self after one examination.

    Removes only this exam's restriction, restores the persisted normal
    outfit/effects, refills full normal pools, then releases this exam's
    schedule hold through elapsed time. Foreign or unreadable exam state is
    left untouched and reported; the host is never deleted.
    """
    from world.rules.clock import read_world_clock
    from world.rules.equipment import sync_equipment_gauge_limits
    from world.rules.guild_exam_restrictions import remove_exam_restriction
    from world.rules.surfaces import restore_attribute
    from world.rules.traits import restore_gauges_to_full

    try:
        restriction = exam_restriction(host)
    except ValueError:
        restriction = None
        log_warn("guild_exam_host_restriction_unreadable", context={"exam": exam_id, "host": host.pk})
    normal = host.attributes.get(NORMAL_STATE_ATTRIBUTE)
    owns_normal = isinstance(normal, Mapping) and normal.get("exam_id") == exam_id
    foreign = (restriction is not None and restriction["exam_id"] != exam_id) or (
        normal is not None and not owns_normal
    )
    if foreign:
        # Another examination owns this host now: a replayed or late
        # settlement must not lift, re-outfit or heal it.
        log_warn(
            "guild_exam_host_state_foreign",
            context={
                "exam": exam_id, "host": host.pk,
                "owner": restriction["exam_id"] if restriction is not None else None,
            },
        )
        return
    if restriction is not None:
        remove_exam_restriction(host, exam_id)
    if owns_normal:
        host.db.equipment = deepcopy(dict(normal["equipment"]))
        host.db.inventory = list(normal["inventory"])
        restore_attribute(host, "buffs", tuple(normal["buffs"]))
        host.attributes.remove(NORMAL_STATE_ATTRIBUTE)
    sync_equipment_gauge_limits(host)
    restore_gauges_to_full(host)
    hold = read_exam_schedule_hold(host)
    if not hold.known:
        log_warn(
            "guild_exam_host_hold_unreadable",
            context={"exam": exam_id, "host": host.pk, "reason": hold.reason},
        )
    elif hold.hold is not None and hold.hold.exam_id == exam_id and not hold.hold.released:
        clock = read_world_clock()
        if clock is None:
            raise GuildExamError(ExamReason.SERVICE_UNAVAILABLE, "world clock is unavailable")
        release_exam_schedule_hold(host, exam_id, max(clock.tick, hold.hold.held_through_tick))
    transaction.on_commit(lambda context={"exam": exam_id, "host": host.pk}: log_info(
        "guild_exam_host_restored", context=context
    ))


def start_guild_exam(
    actor: Any,
    examiner: Any,
    target_rank: str,
    *,
    requested_by: str = "command",
    counter: Any = None,
) -> GuildExamRecord:
    """Start one simulated-battle guild examination as the sole trigger (D-7).

    ``examiner`` is the branch-qualified persistent adventurer who fights;
    ``requested_by`` is audit metadata only. Every gate (local counter and its
    anchoring, branch, host qualification and co-location, host service
    state, participant identity, exact next rank, true merit threshold, no
    active combat/exam on either side, wearable kit and usable lineage) is
    revalidated here before any write. ``counter`` is an already-resolved
    exam counter (the NPC voicing an exam intent); it is gated exactly like
    the single co-located counter resolved by default. The kit, restriction,
    schedule hold, full pools, exam record, session and +1 affinity then
    commit together.
    """
    if not isinstance(actor, PlayerCharacter):
        raise GuildExamError(ExamReason.NOT_A_PLAYER)
    from world.rules.combat_session import is_in_active_session

    if is_in_active_session(actor):
        raise GuildExamError(ExamReason.ACTIVE_COMBAT)
    if parse_guild_registration(actor) is None:
        raise GuildExamError(ExamReason.UNREGISTERED)
    if not isinstance(examiner, NPC):
        raise GuildExamError(ExamReason.NO_EXAMINER)
    # The counter's shared availability gate refuses remote, off-anchor and
    # malformed bindings before any eligibility check or write.
    if counter is not None and not _is_exam_counter(counter):
        raise GuildExamError(ExamReason.NO_EXAMINER)
    branch_key = _counter_branch(actor, counter)
    if actor.location is None or examiner.location != actor.location:
        raise GuildExamError(ExamReason.REMOTE_EXAMINER)

    _require_next_rank(actor, target_rank)

    try:
        host = qualified_host(branch_key, target_rank)
    except GuildHostIntegrityError as error:
        raise GuildExamError(ExamReason.UNQUALIFIED_EXAMINER) from error
    if host.pk != examiner.pk:
        raise GuildExamError(ExamReason.UNQUALIFIED_EXAMINER)
    if interaction_reason(host, "service_guild") is not None:
        raise GuildExamError(ExamReason.EXAMINER_BUSY)
    # Battlefield rosters key participants by display key; a same-keyed
    # candidate is rejected rather than renaming the persistent host.
    if str(actor.key) == str(host.key):
        raise GuildExamError(ExamReason.PARTICIPANT_NAME_COLLISION)
    if is_in_active_session(host) or _host_engaged(host):
        raise GuildExamError(ExamReason.EXAMINER_ENGAGED)
    if not all(_valid_age(host.attributes.get(key)) for key in ("age", "apparent_age")):
        raise GuildExamError(ExamReason.UNQUALIFIED_EXAMINER, "invalid canonical age")

    threshold = get_catalog().merit_thresholds[target_rank]
    if read_counter_trait(actor, "guild_merit") < threshold:
        raise GuildExamError(ExamReason.BELOW_THRESHOLD)
    records = _read_exams(actor)
    if _find_active_exam(records) is not None:
        raise GuildExamError(ExamReason.DUPLICATE_ACTIVE)
    if any(r.target_rank == target_rank and r.state is ExamState.PASSED for r in records):
        raise GuildExamError(ExamReason.ALREADY_SETTLED)

    kit = _exam_kit(target_rank)
    try:
        preflight_exam_restriction(host, target_rank, equipment=kit)
    except RestrictionError as error:
        raise GuildExamError(ExamReason.UNQUALIFIED_EXAMINER, str(error)) from error
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    if clock is None:
        raise GuildExamError(ExamReason.SERVICE_UNAVAILABLE, "world clock is unavailable")
    start_tick = clock.tick
    exam_id = f"{actor.pk}:{target_rank}:{_attempt_number(records, target_rank)}"

    from world.rules.combat_session import CombatSessionRecord, to_storage

    actor_snapshots = {
        key: attribute_snapshot(actor, key)
        for key in ("guild_exams", "active_combat", "guild_rank")
    }
    actor_traits_snapshot = snapshot_traits(actor)
    host_snapshot = snapshot_exam_host_surfaces(host)
    try:
        with transaction.atomic():
            _install_exam_kit(host, exam_id, start_tick, kit)
            activate_exam_restriction(host, exam_id, target_rank)
            begin_exam_schedule_hold(host, exam_id, start_tick)
            from world.rules.traits import restore_gauges_to_full

            # Simulated battle: both sides enter at full applicable pools.
            restore_gauges_to_full(actor)
            restore_gauges_to_full(host)
            session = CombatSessionRecord(
                session_id=f"guild_exam:{actor.pk}:{exam_id}",
                mode="guild_exam",
                room_id=int(actor.location.pk),
                player_ids=(int(actor.pk),),
                enemy_ids=(int(host.pk),),
                fled_ids=(),
                knocked_out_ids=(),
                rounds_elapsed=0,
                exam_id=exam_id,
            )
            exam_record = GuildExamRecord(
                exam_id=exam_id,
                character_id=int(actor.pk),
                target_rank=target_rank,
                requested_by=requested_by,
                opponent_id=int(host.pk),
                session_id=session.session_id,
                state=ExamState.ACTIVE,
                terminal_reason=None,
            )
            _write_exams(actor, [*records, exam_record])
            actor.db.active_combat = to_storage(session)
            from world.rules.combat_session import reconstruct_battlefield
            from world.rules.skip_safety import register_active_battlefield

            register_active_battlefield(reconstruct_battlefield(actor, session))
            from world.rules.affinity import AffinitySource, apply_affinity_change

            apply_affinity_change(host, actor, AffinitySource.GUILD, 1)
            transaction.on_commit(lambda context={
                "exam": exam_id, "host": host.pk, "char": actor.pk,
                "target": target_rank, "branch": branch_key, "tick": start_tick,
                "session": session.session_id,
            }: log_info("guild_exam_started", context=context))
    except Exception:
        from world.rules.skip_safety import unregister_participants
        from world.rules.surfaces import restore_attribute_best_effort

        unregister_participants((int(actor.pk), int(host.pk)))
        for key, snapshot in actor_snapshots.items():
            restore_attribute_best_effort(actor, key, snapshot)
        restore_traits(actor, actor_traits_snapshot)
        restore_exam_host_surfaces(host, host_snapshot)
        raise
    return exam_record


def settle_exam_outcome(
    actor: Any,
    session_record: Any,
    battlefield: Any,
    outcome: str,
) -> dict[str, Any]:
    """Idempotently settle one guild examination by exam ID (D-7).

    Opponent knockout promotes exactly one rank; candidate knockout, flee,
    forfeit, invalid recovery, or round cap records FAIL with rank and
    cumulative merit unchanged. This function only writes the exam terminal
    state; the caller's settlement transaction restores the persistent host
    (``restore_exam_host``) and both sides' pools in the same unit.
    """
    if session_record is None or session_record.mode != "guild_exam":
        raise GuildExamError(ExamReason.NOT_SETTLABLE)
    exam_id = session_record.exam_id
    records = _read_exams(actor)
    record = next((r for r in records if r.exam_id == exam_id), None)
    if record is None:
        raise GuildExamError(ExamReason.UNKNOWN_EXAM)
    if record.state is not ExamState.ACTIVE:
        return {"exam_id": exam_id, "state": record.state.value}

    passed = outcome == "exam_passed"
    new_state = ExamState.PASSED if passed else ExamState.FAILED
    rank_snapshot = attribute_snapshot(actor, "guild_rank")
    exams_snapshot = attribute_snapshot(actor, "guild_exams")
    title_collection_snapshot = attribute_snapshot(actor, "title_collection")
    title_equipped_snapshot = attribute_snapshot(actor, "title_equipped")
    title_notifications: tuple[str, ...] = ()
    try:
        from django.db import transaction

        with transaction.atomic():
            new_record = replace(
                record,
                state=new_state,
                terminal_reason=outcome,
            )
            new_records = [
                new_record if r.exam_id == exam_id else r for r in records
            ]
            _write_exams(actor, new_records)
            if passed:
                actor.guild_rank = _next_rank(actor.guild_rank)
                from world.rules.titles import grant_rank_title

                # D3: the promotion transaction banks the new rank's paired
                # fixed title (auto-equipping the fixed slot only when empty).
                title_notifications = grant_rank_title(actor, actor.guild_rank)
    except Exception:
        from world.rules.surfaces import restore_attribute_best_effort

        restore_attribute_best_effort(actor, "guild_rank", rank_snapshot)
        restore_attribute_best_effort(actor, "guild_exams", exams_snapshot)
        restore_attribute_best_effort(
            actor, "title_collection", title_collection_snapshot
        )
        restore_attribute_best_effort(
            actor, "title_equipped", title_equipped_snapshot
        )
        raise
    if passed:
        # The settlement transaction block succeeded; observers defer their
        # own side effects to ``transaction.on_commit`` because an outer
        # transaction (the caller's session settlement) may still commit.
        _notify_exam_pass(actor, record.target_rank)
    result = {"exam_id": exam_id, "state": new_state.value, "passed": passed}
    if title_notifications:
        result["title_notifications"] = list(title_notifications)
    return result


def _next_rank(current: str) -> str:
    from world.lore.guild import GUILD_RANK_REGISTRY

    order = _rank_order(current) + 1
    for rank in GUILD_RANK_REGISTRY.values():
        if rank.order == order:
            return rank.key
    raise GuildExamError(ExamReason.MALFORMED_RECORD, "no next rank")