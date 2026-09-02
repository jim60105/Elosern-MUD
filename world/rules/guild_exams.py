"""Triggerable simulated-battle guild examinations (guild-economy D-7).

``start_guild_exam`` is the sole examination trigger; ``requested_by`` is audit
metadata, never authority. It validates registration, exact next rank, the true
cumulative merit threshold, and absence of active combat/exam, then spawns a
temporary adult NPC opponent, restores both sides to full HP/MP/SP, and opens a
``guild_exam`` combat session as one all-or-nothing operation. The exam is a
simulated lethal battle: combat follows ordinary lethal semantics, and both
sides are restored to full HP/MP/SP again after settlement, win or lose
(exam-simulated-battle-redesign D1-D3). Settlement is idempotent by exam ID
and promotes exactly one rank on PASS.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from evennia.utils.create import create_object

from world.observability import log_warn
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer
from typeclasses.npcs import NPC, ensure_npc_adult_identity
from world.rules.guild import parse_guild_registration
from world.rules.guild_config import get_catalog
from world.rules.surfaces import (
    attribute_snapshot,
    read_counter_trait,
    restore_traits,
    snapshot_traits,
)


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
    UNREGISTERED = "unregistered"
    WRONG_BRANCH = "wrong_branch"
    NOT_NEXT_RANK = "not_next_rank"
    BELOW_THRESHOLD = "below_threshold"
    ACTIVE_COMBAT = "active_combat"
    DUPLICATE_ACTIVE = "duplicate_active"
    UNKNOWN_PROFILE = "unknown_profile"
    MALFORMED_RECORD = "malformed_record"
    ALREADY_SETTLED = "already_settled"
    NOT_SETTLABLE = "not_settlable"
    UNKNOWN_EXAM = "unknown_exam"


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


def _profile_for(target_rank: str):
    profile = get_catalog().exam_profiles.get(target_rank)
    if profile is None:
        raise GuildExamError(ExamReason.UNKNOWN_PROFILE, target_rank)
    return profile


def _spawn_opponent(actor: Any, target_rank: str) -> NPC:
    profile = _profile_for(target_rank)
    opponent = create_object(NPC, key=f"guild-examiner-{target_rank}")
    try:
        opponent.race = "human"
        opponent._apply_trait_config(
            __import__(
                "world.rules.traits", fromlist=["_trait_config"]
            )._trait_config(
                {
                    "hp": profile.hp,
                    "mp": profile.mp,
                    "sp": profile.sp,
                    "atk_phys": profile.atk_phys,
                    "agility": profile.agility,
                    "defense": profile.defense,
                    "magic_power": profile.magic_power,
                    "guild_merit": 0,
                },
            )
        )
        opponent.db.skills = {"active": list(profile.skills), "passive": []}
        ensure_npc_adult_identity(opponent)
        opponent.location = actor.location
        # Suffix the pk so a participant whose display name equals the bare
        # ``guild-examiner-<rank>`` pattern can never collide in a battlefield
        # roster keyed by display key.
        opponent.key = f"guild-examiner-{target_rank}-{opponent.pk}"
        opponent.save()
    except Exception:
        try:
            opponent.delete()
        except Exception as error:
            log_warn(
                "exam_opponent_delete_failed",
                exc=error,
                context={"stage": "spawn_opponent", "obj": str(opponent)},
            )
        raise
    return opponent


def start_guild_exam(
    actor: Any,
    examiner: Any,
    target_rank: str,
    *,
    requested_by: str = "command",
) -> GuildExamRecord:
    """Start one simulated-battle guild examination as the sole trigger (D-7).

    ``requested_by`` is audit metadata only; every gate (co-location,
    component/branch, registration, exact next rank, true merit threshold,
    no active combat/exam) is revalidated here regardless of its value. The
    candidate and the spawned opponent are restored to full HP/MP/SP inside
    the all-or-nothing start, so a failed start restores nothing.
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
    if not hasattr(examiner, "components") or not examiner.components.has(GuildExaminer.name):
        raise GuildExamError(ExamReason.NO_EXAMINER)
    if actor.location is None or examiner.location != actor.location:
        raise GuildExamError(ExamReason.REMOTE_EXAMINER)
    examiner_component = examiner.components.get(GuildExaminer.get_component_slot())
    branch_key = examiner_component.branch_key
    registration = parse_guild_registration(actor)
    if registration["branch_key"] != branch_key:
        raise GuildExamError(ExamReason.WRONG_BRANCH)

    actor_rank = actor.guild_rank
    from world.lore.guild import GUILD_RANK_REGISTRY

    if actor_rank not in GUILD_RANK_REGISTRY:
        raise GuildExamError(ExamReason.MALFORMED_RECORD, "actor has no valid rank")
    expected_next = GUILD_RANK_REGISTRY[actor_rank].key
    next_order = _rank_order(actor_rank) + 1
    if _rank_order(target_rank) != next_order:
        raise GuildExamError(ExamReason.NOT_NEXT_RANK)
    threshold = get_catalog().merit_thresholds[target_rank]
    if read_counter_trait(actor, "guild_merit") < threshold:
        raise GuildExamError(ExamReason.BELOW_THRESHOLD)

    records = _read_exams(actor)
    if _find_active_exam(records) is not None:
        raise GuildExamError(ExamReason.DUPLICATE_ACTIVE)
    passed_target = next(
        (record for record in records if record.target_rank == target_rank and record.state is ExamState.PASSED),
        None,
    )
    if passed_target is not None:
        raise GuildExamError(ExamReason.ALREADY_SETTLED)

    attempt = _attempt_number(records, target_rank)
    exam_id = f"{actor.pk}:{target_rank}:{attempt}"

    from world.rules.combat_session import CombatSessionRecord, to_storage

    record_snapshot = attribute_snapshot(actor, "guild_exams")
    session_snapshot = attribute_snapshot(actor, "active_combat")
    rank_snapshot = attribute_snapshot(actor, "guild_rank")
    examiner_relations = attribute_snapshot(examiner, "relations_data")
    # The pre-restore writes trait surfaces; restore them on rollback so the
    # in-process gauge values never serve the restored values a rejected
    # start rolled back in the database (idmapper is not transaction-aware).
    traits_snapshot = snapshot_traits(actor)
    opponent = None
    try:
        from django.db import transaction

        with transaction.atomic():
            # Spawn inside the transaction so every failure path rolls the
            # opponent back; no orphan can survive a rejected start.
            opponent = _spawn_opponent(actor, target_rank)
            # Simulated battle: both sides enter at full HP/MP/SP regardless
            # of their state before the exam (exam-simulated-battle-redesign
            # D2); a failed start rolls this restoration back with everything
            # else.
            from world.rules.traits import restore_gauges_to_full

            restore_gauges_to_full(actor)
            restore_gauges_to_full(opponent)
            session = CombatSessionRecord(
                session_id=f"guild_exam:{actor.pk}:{exam_id}",
                mode="guild_exam",
                room_id=int(actor.location.pk),
                player_ids=(int(actor.pk),),
                enemy_ids=(int(opponent.pk),),
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
                opponent_id=int(opponent.pk),
                session_id=session.session_id,
                state=ExamState.ACTIVE,
                terminal_reason=None,
            )
            _write_exams(actor, [*records, exam_record])
            actor.db.active_combat = to_storage(session)
            from world.rules.combat_session import reconstruct_battlefield
            from world.rules.skip_safety import register_active_battlefield

            battlefield = reconstruct_battlefield(actor, session)
            register_active_battlefield(battlefield)
            from world.rules.affinity import AffinitySource, apply_affinity_change

            apply_affinity_change(examiner, actor, AffinitySource.GUILD, 1)
    except Exception:
        from world.rules.skip_safety import unregister_participants

        if opponent is not None:
            unregister_participants((int(actor.pk), int(opponent.pk)))
        from world.rules.surfaces import restore_attribute_best_effort

        restore_attribute_best_effort(actor, "guild_exams", record_snapshot)
        restore_attribute_best_effort(actor, "active_combat", session_snapshot)
        restore_attribute_best_effort(actor, "guild_rank", rank_snapshot)
        restore_attribute_best_effort(examiner, "relations_data", examiner_relations)
        restore_traits(actor, traits_snapshot)
        if opponent is not None:
            try:
                opponent.delete()
            except Exception as error:
                log_warn(
                    "exam_opponent_delete_failed",
                    exc=error,
                    context={"stage": "start_exam_compensation", "obj": str(opponent)},
                )
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
    cumulative merit unchanged. The temporary opponent is deleted by the
    caller after the settlement transaction commits (so a rolled-back
    settlement keeps it alive for exactly one retry); this function only
    writes the exam terminal state.
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