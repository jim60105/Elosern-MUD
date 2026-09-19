"""Terminal settlement: one-time time settlement, clearing, and recovery.

The accumulated round time settles exactly once at a terminal outcome through
``settle_session``; ``restore_active_session`` reconstructs a valid persisted
session (or terminates it diagnostically) at startup (fix-combat-
settlement-recovery D1/D2, guild-economy D-6).
"""

import time
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
        actor, record, battlefield, outcome, logs, nested_round=True
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
    step leaves the durable session intact for exactly one retry. Exam
    opponents are deleted only after the transaction commits: a rolled-back
    settlement must leave the temporary opponent alive for the retry, and
    deleting inside the transaction could strand a stale deleted instance
    in the idmapper cache.
    """
    from django.db import transaction

    exam_result = None
    started = time.monotonic()
    aftermath = None
    try:
        with transaction.atomic():
            if record.mode == "guild_exam":
                from world.rules.guild_exams import settle_exam_outcome

                exam_result = settle_exam_outcome(
                    actor, record, battlefield, outcome
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
            # Record the world tick at which the settlement committed; a non-None
            # value marks the session as settled for any later reader.
            _persist(
                actor,
                replace(record, settled_tick=get_world_clock().tick),
            )
            clear_session(actor, battlefield, record)
            if record.mode == "guild_exam":
                # Simulated battle: restore both sides inside the settlement
                # transaction, so the full-restoration guarantee commits or rolls
                # back with the exam outcome and can never strand a defeated
                # candidate (exam-simulated-battle-redesign D3). Opponent deletion
                # stays post-commit so a rolled-back settlement keeps it alive.
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
    if record.mode == "guild_exam":
        _delete_exam_opponent(actor, record)
    return {
        "outcome": outcome,
        "rounds_elapsed": record.rounds_elapsed,
        "logs": (*logs, *aftermath_logs),
        "events": tuple(events),
        "exam": exam_result,
    }


def _find_exam_opponent(actor: Any, record: CombatSessionRecord) -> Any | None:
    """Return the settled exam's temporary opponent, if it still exists."""
    from world.rules.guild_exams import _read_exams

    exam_record = next(
        (r for r in _read_exams(actor) if r.exam_id == record.exam_id),
        None,
    )
    if exam_record is None:
        return None
    return ObjectDB.objects.filter(id=exam_record.opponent_id).first()


def _restore_exam_participants(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
) -> None:
    """Restore both exam sides' gauges to full inside the settlement.

    Runs as the last step of the settlement transaction, after the session
    clears and before the temporary opponent is deleted post-commit
    (exam-simulated-battle-redesign D3): the candidate and examiner walk away
    from the simulated battle fully healed regardless of outcome, and the
    restoration commits or rolls back with the exam outcome. The battlefield
    roster is preferred when available; a degraded path (or a roster that
    lacks the opponent) falls back to the durable exam record lookup.
    """
    from world.rules.traits import restore_gauges_to_full

    restore_gauges_to_full(actor)
    opponent = None
    if battlefield is not None:
        opponent = next(
            (
                entity
                for key, entity in battlefield.roster.items()
                if int(entity.pk) in record.enemy_ids
            ),
            None,
        )
    if opponent is None:
        opponent = _find_exam_opponent(actor, record)
    if opponent is not None:
        restore_gauges_to_full(opponent)


def _delete_exam_opponent(actor: Any, record: CombatSessionRecord) -> None:
    """Delete the settled exam's temporary opponent, best effort.

    Runs after the settlement transaction committed, so a failed settlement
    keeps the opponent alive for exactly one retry. An already-missing
    opponent (or a delete error) is logged and never raises.
    """
    opponent = _find_exam_opponent(actor, record)
    if opponent is None:
        return
    try:
        opponent.delete()
    except Exception as error:
        log_warn(
            "guild_exam_opponent_delete_failed",
            exc=error,
            context={"char": str(actor.key), "obj": str(opponent), "exam": record.exam_id},
        )


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
    if record.mode == "guild_exam":
        extra["guild_rank"] = _attribute_snapshot(actor, "guild_rank")
        extra["guild_exams"] = _attribute_snapshot(actor, "guild_exams")
        # The settlement transaction restores the exam sides' gauges; when it
        # rolls back, restore the in-process trait surfaces too (the idmapper
        # cache is not transaction-aware), for the actor and the opponent.
        from world.rules.surfaces import snapshot_traits

        trait_snapshots.append((actor, snapshot_traits(actor)))
        opponent = _find_exam_opponent(actor, record)
        if opponent is not None:
            trait_snapshots.append((opponent, snapshot_traits(opponent)))
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
