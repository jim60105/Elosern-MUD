"""Terminal settlement: one-time time settlement, clearing, and recovery.

The accumulated round time settles exactly once at a terminal outcome through
``settle_session``; ``restore_active_session`` reconstructs a valid persisted
session (or terminates it diagnostically) at startup (fix-combat-
settlement-recovery D1/D2, guild-economy D-6).
"""

import time
from collections.abc import Mapping
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

from evennia.objects.models import ObjectDB

from world.observability import log_info, log_warn
from world.rules.action import _stored_trait_value
from world.rules.clock import get_world_clock, settle_combat_result
from world.rules.combat import COMBAT_YAML, Battlefield
from world.rules.combat_session.battlefield import reconstruct_battlefield
from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.overwhelm import classify_overwhelm
from world.rules.combat_session.lifecycle import _persist, clear_session
from world.rules.combat_session.records import CombatSessionRecord, read_session
from world.rules.skip_safety import register_active_battlefield

_ROUND_SECONDS = int(COMBAT_YAML["round"]["seconds"])


def _team_living(
    battlefield: Battlefield,
    team: str,
    record: CombatSessionRecord,
) -> bool:
    """Return whether a team has any living, present, active member.

    The persisted ``knocked_out_ids`` (exam knockouts and the previous round's
    markings) and the battlefield's in-round ``knocked_out`` set (marked at
    damage-commit time) both count, so a knocked-out member is never "living"
    through either source (party-combat D-2).
    """
    knocked = set(record.knocked_out_ids) | {
        int(entity.pk)
        for key, entity in battlefield.roster.items()
        if key in battlefield.knocked_out and key in battlefield.roster
    }
    return any(
        key in battlefield.roster
        and key not in battlefield.fled
        and battlefield.roster[key].pk not in knocked
        and _stored_trait_value(battlefield.roster[key].traits.hp) > 0
        for key in battlefield.teams[team]
    )


def _terminal_outcome(
    actor: Any,
    battlefield: Battlefield,
    record: CombatSessionRecord,
) -> str | None:
    """Return the deterministic terminal outcome, or ``None`` to continue.

    Player-centric (party-combat D-4): the session ends on the player's flee,
    knockout, or death even when companions stand; only the foes team decides
    victory. A knocked-out companion is battlefield state, never a terminal
    condition.
    """
    player_team = battlefield.team_of(str(actor.key))
    foe_team = next(team for team in battlefield.teams if team != player_team)
    if str(actor.key) in battlefield.fled:
        return "fled"
    player_key = str(actor.key)
    player_defeated = (
        _stored_trait_value(actor.traits.hp) <= 0
        or player_key in battlefield.knocked_out
        or int(actor.pk) in record.knocked_out_ids
    )
    if player_defeated:
        return "defeat" if record.mode == "hostile" else "exam_failed"
    if not _team_living(battlefield, foe_team, record):
        return "victory" if record.mode == "hostile" else "exam_passed"
    if record.rounds_elapsed >= _round_cap():
        return "cap"
    return None


def _round_cap() -> int:
    return int(COMBAT_YAML.get("max_rounds", 100))


def _continue_or_settle(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield,
    logs,
    *,
    notification_count: int = 0,
    opening: str = "round",
) -> dict[str, Any]:
    outcome = _terminal_outcome(actor, battlefield, record)
    if outcome is None:
        return {
            "outcome": "round",
            "rounds_elapsed": record.rounds_elapsed,
            "logs": tuple(logs),
            "overwhelming_team": classify_overwhelm(battlefield),
        }
    # nested_round: this settlement runs inside _submit_request's round
    # transaction, so the aftermath arms its undo for that transaction's
    # own failure boundary.
    return settle_session(
        actor, record, battlefield, outcome, logs, nested_round=True, opening=opening
    )


def settle_session(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
    outcome: str,
    logs=(),
    *,
    notification_count: int = 0,
    nested_round: bool = False,
    opening: str = "round",
) -> dict[str, Any]:
    """Settle accumulated round time once and clear session state (D-6).

    The whole terminal settlement is one durable transaction (fix-combat-
    settlement-recovery D2): the exam outcome (guild-exam mode), the combat
    clock advance, the durable ``settled_tick`` marker, the session clear,
    and the simulated-battle gauge restoration commit or roll back together.
    A crash mid-settlement therefore never loses exam time, never double-
    counts hostile time, never leaves a half-settled session, and never
    strands a defeated exam candidate; the marker additionally lets a
    restart skip re-settlement for any durable record already marked
    settled. The session clear is the last step inside the transaction
    (followed by the exam gauge restoration), so a failure of any earlier
    step leaves the durable session intact for exactly one retry. The
    persistent exam host is restored inside the same transaction and is
    never deleted.
    """
    from django.db import transaction

    exam_result = None
    started = time.monotonic()
    aftermath = None
    try:
        with transaction.atomic():
            if record.mode == "guild_exam":
                from world.rules.guild_exams import (
                    ExamReason,
                    GuildExamError,
                    settle_exam_outcome,
                )

                try:
                    exam_result = settle_exam_outcome(
                        actor, record, battlefield, outcome
                    )
                except GuildExamError as error:
                    # A missing or unreadable exam history cannot be settled,
                    # but it must never strand the persistent host: the
                    # session still clears and the host is restored below.
                    # Both reasons are raised before any exam write.
                    if error.args[0] not in (
                        ExamReason.UNKNOWN_EXAM,
                        ExamReason.MALFORMED_RECORD,
                    ):
                        raise
                    log_warn(
                        "guild_exam_settlement_record_unavailable",
                        exc=error,
                        context={"char": str(actor.pk), "session": record.session_id},
                    )
            # Settlement regenerates every living, non-fled roster member
            # (fix-combat-session-roster-and-overwhelm D1): companions and any
            # non-defeated foe still present recover for the accumulated combat
            # seconds, so a knocked-out companion can rise above the nonlethal
            # HP floor and rejoin a later engagement. A member at 0 HP is dead
            # and excluded (kill semantics). The actor alone keeps the historical
            # scope only when the actor is still living (recovery fallback with a
            # live actor, or a solo flee whose actor is alive); a dead actor is
            # never passed, so settlement can never revive a defeated player.
            participants = (
                [
                    entity
                    for key, entity in battlefield.roster.items()
                    if key not in battlefield.fled
                    and _stored_trait_value(entity.traits.hp) > 0
                ]
                if battlefield is not None
                else []
            )
            if not participants and _stored_trait_value(actor.traits.hp) > 0:
                participants = [actor]
            events = settle_combat_result(
                SimpleNamespace(
                    total_seconds=record.rounds_elapsed * _ROUND_SECONDS
                ),
                participants,
            )
            aftermath_logs: tuple = ()
            if record.mode == "hostile" and outcome == "defeat":
                from world.rules.defeat_aftermath import (
                    finalize_departure,
                    register_pending_undo,
                    run_defeat_aftermath,
                )

                aftermath = run_defeat_aftermath(actor, record, battlefield)
                record = aftermath.session
                aftermath_logs = aftermath.logs
                # The physical departure deletes only after the OUTERMOST
                # durable commit: a settlement reached inside a round's
                # transaction is a savepoint, and a rolled-back round must
                # leave the winner alive (D-C3 two-phase departure).
                transaction.on_commit(
                    lambda actor=actor, tickets=aftermath.departed: (
                        finalize_departure(actor, tickets)
                    )
                )
                if nested_round:
                    # Django has no rollback hook: arm the undo so the
                    # enclosing round transaction can restore the aftermath
                    # surfaces when it rolls back after this settlement
                    # returned.
                    register_pending_undo(aftermath.undo)
            # Record the world tick at which the settlement committed; a
            # non-None value marks the session as settled for any later
            # reader. Victory also consumes any martyr stamp (design §5.8):
            # the marked fight ended in the clergy's favour, so the stamp is
            # spent and a later defeat in another session can never fire it.
            settled_record = replace(
                record, settled_tick=get_world_clock().tick
            )
            # Record durable narrative event for covered protection encounters inside this same atomic unit
            from world.narrative.projector import select_and_record_protection_event
            select_and_record_protection_event(
                actor=actor,
                record=record,
                battlefield=battlefield,
                outcome=outcome,
                opening=opening,
                rounds_elapsed=record.rounds_elapsed,
                settled_tick=int(settled_record.settled_tick or 0),
            )
            if outcome == "victory" and settled_record.martyr_key is not None:
                settled_record = replace(
                    settled_record, martyr_key=None
                )
            _persist(actor, settled_record)
            clear_session(actor, battlefield, record)
            if record.mode == "guild_exam":
                # Simulated battle: restore the candidate and return the
                # persistent host to its normal self (outfit, effects, full
                # pools, schedule hold released) inside the settlement
                # transaction, so restoration commits or rolls back with the
                # exam outcome (persistent-guild-exam-lifecycle).
                _restore_exam_participants(actor, record, battlefield)
            # Boundary event fires only on the OUTERMOST durable commit: a
            # settlement reached inside a round's transaction is a savepoint, and
            # a rolled-back attempt must emit nothing (spec scenario).
            settled_ms = int((time.monotonic() - started) * 1000)
            # Context snapshotted at the boundary; callback carries only
            # primitives (see the round-boundary note above).
            boundary = {
                "char": str(actor.pk),
                "outcome": outcome,
                "ms": settled_ms,
                "notifications": notification_count,
            }
            transaction.on_commit(
                lambda boundary=boundary: log_info(
                    "settlement_done", context=boundary
                )
            )
    except Exception:
        # Any exception escaping the transaction — a body failure or the
        # context manager's own commit/exit failure — must undo the
        # idmapper-cached aftermath surfaces before propagating (D-C5); the
        # undo is idempotent.
        if aftermath is not None:
            from world.rules.defeat_aftermath import drain_pending_undos

            aftermath.undo()
            drain_pending_undos()
        raise
    return {
        "outcome": outcome,
        "rounds_elapsed": record.rounds_elapsed,
        "logs": (*logs, *aftermath_logs),
        "events": tuple(events),
        "exam": exam_result,
    }


def _find_exam_opponent(actor: Any, record: CombatSessionRecord) -> Any | None:
    """Return the session's persistent exam host by its recorded dbref.

    Reads the parsed session record, never the candidate's exam history, so
    a malformed history cannot hide the host from restoration.
    """
    if record.mode != "guild_exam" or len(record.enemy_ids) != 1:
        return None
    return ObjectDB.objects.filter(id=record.enemy_ids[0]).first()


def _restore_exam_participants(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
) -> None:
    """Restore the candidate's full pools and the host's normal self.

    Runs as the last step of the settlement transaction, after the session
    clears (exam-simulated-battle-redesign D3, persistent-guild-exam-
    lifecycle): the candidate walks away fully healed regardless of outcome,
    and the persistent host loses this exam's restriction/kit, regains its
    normal outfit/effects and full normal pools, and has its schedule hold
    released, all committing or rolling back with the exam outcome.
    """
    from world.rules.guild_exams import restore_exam_host
    from world.rules.traits import restore_gauges_to_full

    restore_gauges_to_full(actor)
    host = _find_exam_opponent(actor, record)
    if host is None:
        log_warn(
            "guild_exam_host_missing",
            context={"char": str(actor.pk), "session": record.session_id, "exam": record.exam_id},
        )
        return
    restore_exam_host(host, record.exam_id)


def _settle_with_restore(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
    outcome: str,
    logs=(),
) -> dict[str, Any]:
    """Settle a session outside a round, restoring actor surfaces on failure.

    ``settle_session`` runs its own durable transaction; when it fails (for
    example a clock write error during forfeit or startup restoration), the
    database keeps the session but the in-process ``active_combat``/exam
    attributes were already reassigned by the settlement steps. Restoring
    them keeps the retry path consistent without waiting for a reload
    (the idmapper attribute cache is not transaction-aware).
    """
    from world.rules.action import _attribute_snapshot, _restore_attribute

    extra: dict[str, tuple[bool, Any]] = {
        "active_combat": _attribute_snapshot(actor, "active_combat"),
        "buffs": _attribute_snapshot(actor, "buffs"),
    }
    battlefield_buff_snapshots: list[tuple[Any, tuple[bool, Any]]] = []
    if battlefield is not None:
        for entity in battlefield.roster.values():
            if entity is not actor:
                battlefield_buff_snapshots.append(
                    (entity, _attribute_snapshot(entity, "buffs"))
                )
    trait_snapshots: list[tuple[Any, tuple[bool, Any]]] = []
    host = None
    host_snapshot = None
    if record.mode == "guild_exam":
        extra["guild_rank"] = _attribute_snapshot(actor, "guild_rank")
        extra["guild_exams"] = _attribute_snapshot(actor, "guild_exams")
        # The settlement transaction restores the exam sides' gauges; when it
        # rolls back, restore the in-process trait surfaces too (the idmapper
        # cache is not transaction-aware), for the actor and the opponent.
        from world.rules.surfaces import snapshot_traits

        trait_snapshots.append((actor, snapshot_traits(actor)))
        host = _find_exam_opponent(actor, record)
        if host is not None:
            from world.rules.guild_exams import snapshot_exam_host_surfaces

            host_snapshot = snapshot_exam_host_surfaces(host)
    try:
        return settle_session(actor, record, battlefield, outcome, logs)
    except Exception:
        for key, snapshot in extra.items():
            _restore_attribute(actor, key, snapshot)
        for entity, snapshot in battlefield_buff_snapshots:
            _restore_attribute(entity, "buffs", snapshot)
        for entity, snapshot in trait_snapshots:
            from world.rules.surfaces import restore_traits

            restore_traits(entity, snapshot)
        if host_snapshot is not None:
            from world.rules.guild_exams import restore_exam_host_surfaces

            restore_exam_host_surfaces(host, host_snapshot)
        raise


def forfeit(actor: Any) -> dict[str, Any]:
    """Settle accumulated time, record defeat/exam FAIL, and clean up."""
    record = read_session(actor)
    if record is None:
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    battlefield = None
    try:
        battlefield = reconstruct_battlefield(actor, record)
    except CombatSessionError:  # observability: ignore R2: forfeit deliberately settles without a battlefield when participants are unreconstructable
        battlefield = None
    outcome = "defeat" if record.mode == "hostile" else "exam_failed"
    return _settle_with_restore(actor, record, battlefield, outcome)


def restore_active_session(actor: Any) -> None:
    """Reconstruct a valid persisted session or terminate it diagnostically.

    The strict parse runs inside the recovery boundary: a record that cannot
    be parsed at all (for example ``{"not": "a valid record"}``) is cleared
    with a diagnostic and never settled, because its untrusted fields must
    not drive a time settlement or participant effects. Missing, deleted,
    moved, duplicated, or malformed participants of a well-formed record
    close the session deterministically: hostile sessions settle as defeat,
    examinations as FAIL, leaving no orphan opponent and no blocked player.
    A record that already carries a durable ``settled_tick`` marker is never
    settled again: its time already committed, so restoration only clears the
    leftover session state (fix-combat-settlement-recovery D2). Unrelated
    restoration or settlement failures propagate with the durable record
    intact for retry.
    """
    try:
        record = read_session(actor)
    except CombatSessionError as error:
        # Unparseable payload: clear without settlement. The actor's own
        # skip-safety registration is the only key gating the actor's skips,
        # and untrusted ids must never drive participant cleanup.
        log_warn(
            "combat_session_unparseable_cleared",
            exc=error,
            context={"char": str(actor.key)},
        )
        clear_session(actor, None, None)
        return
    if record is None:
        return
    if record.settled_tick is not None:
        log_warn(
            "combat_session_already_settled",
            context={
                "session": record.session_id,
                "settled_tick": record.settled_tick,
            },
        )
        clear_session(actor, None, record)
        return
    if record.mode == "guild_exam" and not _exam_session_coherent(actor, record):
        # Persisted exam identity, host restriction or schedule hold disagree:
        # close the simulation once as FAIL and restore the persistent host
        # from its own persisted normal state; deletion is never a repair.
        log_warn(
            "combat_session_terminated_invalid",
            context={"char": str(actor.key), "session": record.session_id, "mode": "guild_exam"},
        )
        _settle_with_restore(actor, record, None, "exam_failed")
        return
    try:
        battlefield = reconstruct_battlefield(actor, record)
    except CombatSessionError as error:
        log_warn(
            "combat_session_terminated_invalid",
            exc=error,
            context={"char": str(actor.key), "session": record.session_id},
        )
        _settle_with_restore(
            actor,
            record,
            None,
            "defeat" if record.mode == "hostile" else "exam_failed",
        )
        return
    outcome = _terminal_outcome(actor, battlefield, record)
    if outcome is not None:
        _settle_with_restore(actor, record, battlefield, outcome)
        return
    register_active_battlefield(battlefield)


def _exam_session_coherent(actor: Any, record: CombatSessionRecord) -> bool:
    """Whether a reloaded exam session may resume with its persistent host.

    Coherent means the candidate's ACTIVE exam record, the session, the host
    restriction, the host's persisted normal state and its active schedule
    hold all name the same exam and host, and the participant keys stay
    distinct. Any unreadable piece reads as incoherent (fail closed).
    """
    from world.rules.exam_schedule_holds import read_exam_schedule_hold
    from world.rules.guild_exams import (
        NORMAL_STATE_ATTRIBUTE,
        ExamState,
        GuildExamError,
        _read_exams,
    )
    from world.skills.restrictions import exam_restriction

    host = _find_exam_opponent(actor, record)
    if host is None or str(host.key) == str(actor.key):
        return False
    try:
        exam = next((r for r in _read_exams(actor) if r.exam_id == record.exam_id), None)
        restriction = exam_restriction(host)
    except (GuildExamError, ValueError):  # observability: ignore R2: an unreadable exam record or restriction is incoherent; the caller logs and settles FAIL
        return False
    if exam is None or exam.state is not ExamState.ACTIVE or exam.opponent_id != host.pk:
        return False
    if restriction is None or restriction["exam_id"] != record.exam_id:
        return False
    normal = host.attributes.get(NORMAL_STATE_ATTRIBUTE)
    if not isinstance(normal, Mapping) or normal.get("exam_id") != record.exam_id:
        return False
    hold = read_exam_schedule_hold(host)
    return (
        hold.known
        and hold.hold is not None
        and hold.hold.exam_id == record.exam_id
        and not hold.hold.released
    )
