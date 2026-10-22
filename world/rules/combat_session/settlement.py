"""Terminal settlement: one-time time settlement, clearing, and recovery.

The accumulated round time settles exactly once at a terminal outcome through
``settle_session``; ``restore_active_session`` reconstructs a valid persisted
session (or terminates it diagnostically) at startup (fix-combat-
settlement-recovery D1/D2, guild-economy D-6).
"""

import time
from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import Any

from evennia.objects.models import ObjectDB

from world.observability import log_info, log_warn
from world.rules.action import _stored_trait_value
from world.rules.clock import get_world_clock, settle_combat_result
from world.rules.combat import COMBAT_YAML, Battlefield
from world.rules.combat_session.battlefield import reconstruct_battlefield
from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.combat_session.writer import serialized_combat_write
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


def terminal_posture_segments(
    record: CombatSessionRecord,
    actor_id: int,
) -> tuple[tuple[bool, int], ...]:
    """Return ``(asleep, seconds)`` intervals over the completed combat time.

    The engagement posture (``initial_sleep_ids``) and every explicit
    completed-round boundary transition (``sleep_transitions``) are replayed
    chronologically at the authored six-second round length, so a member
    awakened part way through the fight never receives the whole interval as
    sleep. A zero-length tail keeps a transition observed at the final
    boundary, so it still determines the terminal posture.
    """
    transitions = sorted(
        (transition.round_index, transition.asleep)
        for transition in record.sleep_transitions
        if transition.actor_id == actor_id
    )
    asleep = actor_id in record.initial_sleep_ids
    segments: list[tuple[bool, int]] = []
    cursor = 0
    for round_index, next_asleep in transitions:
        segments.append((asleep, (round_index - cursor) * _ROUND_SECONDS))
        cursor = round_index
        asleep = next_asleep
    segments.append((asleep, (record.rounds_elapsed - cursor) * _ROUND_SECONDS))
    return tuple(segments)


def _defeated_participant_ids(
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
) -> set[int]:
    """The participants whose defeat is already established at settlement."""
    defeated = set(record.knocked_out_ids)
    if battlefield is not None:
        for key, entity in battlefield.roster.items():
            if key in getattr(battlefield, "knocked_out", ()):
                pk = getattr(entity, "pk", None)
                if isinstance(pk, int) and not isinstance(pk, bool):
                    defeated.add(pk)
    return defeated


def _settle_terminal_fatigue(
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
    participants: tuple[Any, ...],
) -> tuple[Any, ...]:
    """Settle every eligible member's mental time once, in round order.

    The eligible scope is the allied party (a player character and its
    effective companions own physiology; a monster's construction baseline is
    not a playable reserve). Each member's recorded posture timeline is
    replayed forward from its engagement posture, because clamping makes the
    order significant, and each segment settles through the sole fatigue
    writer with terminal-combat completion. An awake interval that reaches
    zero latches forced sleep only at the terminal boundary, and natural wake
    is evaluated afterwards from the committed reserve — never inside the
    fight and never for an already defeated body.
    """
    from world.rules.fatigue import (
        FatigueActivity,
        FatigueInterval,
        IntervalCompletion,
        SleepPosture,
        project_fatigue_status,
        read_optional_fatigue_state,
        settle_fatigue_intervals,
        write_fatigue_state,
    )

    allied = {int(pk) for pk in record.player_ids}
    defeated = _defeated_participant_ids(record, battlefield)
    commits: list[Any] = []
    for entity in participants:
        pk = getattr(entity, "pk", None)
        if not isinstance(pk, int) or isinstance(pk, bool) or int(pk) not in allied:
            continue
        if getattr(entity, "_is_deleted", False):
            continue
        state = read_optional_fatigue_state(entity)
        if state is None:
            continue
        has_evidence = int(pk) in record.initial_sleep_ids or any(
            transition.actor_id == int(pk) for transition in record.sleep_transitions
        )
        if has_evidence:
            segments = terminal_posture_segments(record, int(pk))
        else:
            # No engagement evidence: only the live posture is authoritative,
            # and the record still contributes the elapsed combat time.
            segments = (
                (
                    state.posture is not SleepPosture.AWAKE,
                    record.rounds_elapsed * _ROUND_SECONDS,
                ),
            )
        sleeping_posture = (
            state.posture
            if state.posture is not SleepPosture.AWAKE
            else SleepPosture.FORCED
        )
        current = state
        first_asleep = segments[0][0]
        if first_asleep and current.posture is SleepPosture.AWAKE:
            # The recorded engagement posture is the timeline's start; the
            # live posture is only its terminal end. Restoring it here keeps
            # the fatigue writer's compatibility check honest without
            # inventing a reserve change.
            current = write_fatigue_state(
                entity, current.reserve_units, sleeping_posture
            )
        elif not first_asleep and current.posture is not SleepPosture.AWAKE:
            current = write_fatigue_state(
                entity, current.reserve_units, SleepPosture.AWAKE
            )
        for asleep, seconds in segments:
            target = sleeping_posture if asleep else SleepPosture.AWAKE
            if current.posture is not target:
                current = write_fatigue_state(
                    entity, current.reserve_units, target
                )
            if seconds <= 0:
                continue
            activity = (
                FatigueActivity.SLEEP if asleep else FatigueActivity.AWAKE_COMBAT
            )
            settlement = settle_fatigue_intervals(
                (
                    FatigueInterval(
                        entity,
                        activity,
                        seconds,
                        current,
                        IntervalCompletion.TERMINAL_COMBAT,
                    ),
                ),
                context={
                    "stage": "terminal_combat",
                    "session": record.session_id,
                },
            )
            commits.extend(settlement.commits)
            current = settlement.commits[0].end
        if (
            current.posture is SleepPosture.FORCED
            and int(pk) not in defeated
            and _stored_trait_value(entity.traits.hp) > 0
        ):
            # Natural wake is a post-combat fact: commit the whole sleep
            # interval without reinterpretation, then release a forced sleeper
            # that has reached the authored wake threshold. A defeated body
            # never wakes and never becomes an eligible handoff candidate.
            settlement = settle_fatigue_intervals(
                (
                    FatigueInterval(
                        entity,
                        FatigueActivity.SLEEP,
                        0,
                        current,
                        IntervalCompletion.INDIVISIBLE,
                    ),
                ),
                context={
                    "stage": "terminal_combat_wake",
                    "session": record.session_id,
                },
            )
            commits.extend(settlement.commits)
            current = settlement.commits[-1].end
        # A no-op segment (for example sleeping at full reserve) writes no
        # interval, so reconcile the projection once from the final state.
        project_fatigue_status(entity, current)
    return tuple(commits)


def _all_present_allies_forced_asleep(
    actor: Any,
    battlefield: Battlefield,
) -> bool:
    """Whether every present, living allied party participant is forced asleep."""
    from world.rules.fatigue import SleepPosture, read_optional_fatigue_state

    player_team = battlefield.team_of(str(actor.key))
    allies: list[Any] = []
    for key in battlefield.teams[player_team]:
        entity = battlefield.roster.get(key)
        if entity is None or key in battlefield.fled:
            continue
        if _stored_trait_value(entity.traits.hp) <= 0:
            continue
        allies.append(entity)
    if not allies:
        return False
    for entity in allies:
        state = read_optional_fatigue_state(entity)
        if state is None or state.posture is not SleepPosture.FORCED:
            return False
    return True


def settle_forced_sleep_opening(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield,
) -> dict[str, Any] | None:
    """Enter ordinary zero-round terminal settlement for an all-sleep opening.

    Returns ``None`` for every other engagement. The ordinary terminal writer
    supplies hostile defeat or exam FAIL, existing aftermath and diagnostics,
    and the durable settled marker; no combat round, enemy action or spectator
    loop runs. Invalid targets are rejected by engagement validation before
    this seam is reached.
    """
    if not _all_present_allies_forced_asleep(actor, battlefield):
        return None
    outcome = "defeat" if record.mode == "hostile" else "exam_failed"
    return _settle_with_restore(actor, record, battlefield, outcome)


def _emit_terminal_sleep_handoff(actor: Any, session_id: str) -> None:
    """Offer sleep-control transfer from committed terminal state, never raises.

    Runs only from ``transaction.on_commit``: the sleep posture, defeat sets
    and aftermath removal are final. The dependent control component owns the
    candidate query and prompt wording, so this seam only asks it for the
    committed offer; a notification failure is reported and never propagates,
    because the settlement has already committed.
    """
    try:
        if not hasattr(actor, "db"):
            return
        from world.rules.time_skip import (
            _handoff_candidates,
            render_handoff_offer_message,
        )

        candidates = _handoff_candidates(actor)
        if not candidates:
            return
        actor.msg(render_handoff_offer_message(candidates))
        log_info(
            "terminal_sleep_handoff",
            context={
                "char": str(getattr(actor, "pk", "?")),
                "session": session_id,
                "candidates": ",".join(
                    str(getattr(candidate, "dbid", "?"))
                    for candidate in candidates
                ),
            },
        )
    except Exception as error:  # observability: ignore R2: a post-commit notification failure must never re-enter settlement compensation
        log_warn(
            "terminal_sleep_handoff_failed",
            exc=error,
            context={
                "char": str(getattr(actor, "pk", "?")),
                "session": session_id,
            },
        )


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


@serialized_combat_write
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
    from evennia.objects.models import ObjectDB
    from django.db import transaction
    from world.narrative.events import (
        build_encounter_source_id,
        get_committed_award_results,
        record_narrative_event,
    )

    encounter_source_id = build_encounter_source_id(
        record.engagement_id or record.session_id,
        kind="terminal",
        ordinal=1,
    )
    # The durable ``settled_tick`` marker is the only idempotency gate. The
    # terminal fact itself is written inside this settlement's transaction and
    # ``record_narrative_event`` is already idempotent, so an existing fact can
    # only mean the previous attempt committed in full. A rolled-back attempt
    # must still run the settlement body: the aftermath, the wake state, the
    # session clear and the clock advance all rolled back with it.
    if record.settled_tick is not None:
        from world.narrative.models import NarrativeEvent

        committed_awards = get_committed_award_results(encounter_source_id)
        existing_event = NarrativeEvent.objects.filter(
            source_id=encounter_source_id
        ).first()
        effective_outcome = (
            existing_event.content.get(
                "gameplay_outcome", existing_event.content.get("outcome", outcome)
            )
            if existing_event is not None
            else outcome
        )
        res = {
            "outcome": effective_outcome,
            "rounds_elapsed": record.rounds_elapsed,
            "logs": tuple(logs),
            "events": (),
        }
        if committed_awards is not None:
            res["title_awards"] = [a.to_dict() for a in committed_awards]
        return res

    participant_ids = [str(pid) for pid in record.player_ids]
    opponent_ids = [str(eid) for eid in record.enemy_ids]
    display_snapshots: dict[str, str] = {}
    for entity_id in (*record.player_ids, *record.enemy_ids):
        id_str = str(entity_id)
        name = None
        if battlefield is not None:
            for entity in battlefield.roster.values():
                if getattr(entity, "pk", None) == entity_id or str(getattr(entity, "key", None)) == id_str:
                    name = str(getattr(entity, "name", entity.key))
                    break
        if name is None:
            obj = ObjectDB.objects.filter(id=entity_id).first()
            if obj is not None:
                name = str(getattr(obj, "name", obj.key))
        display_snapshots[id_str] = name if name is not None else id_str

    if outcome in ("fled", "escaped"):
        normalized_outcome = "escape"
    else:
        normalized_outcome = outcome

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
            # Physiology settles from the recorded round-boundary posture
            # evidence inside this same transaction, once for the accumulated
            # combat seconds. The clock's COMBAT source deliberately does not
            # settle mental time, so this is the sole terminal fatigue write.
            _settle_terminal_fatigue(record, battlefield, tuple(participants))
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
            # Record durable narrative event for completed combat encounter
            committed_awards = get_committed_award_results(encounter_source_id)
            title_awards_list = []
            if exam_result and "title_awards" in exam_result:
                title_awards_list.extend(exam_result["title_awards"])
            elif committed_awards:
                title_awards_list.extend(committed_awards)

            record_narrative_event(
                source_id=encounter_source_id,
                event_type="combat_encounter",
                content={
                    "outcome": normalized_outcome,
                    "gameplay_outcome": outcome,
                    "mode": record.mode,
                    "participant_ids": participant_ids,
                    "opponent_ids": opponent_ids,
                    "display_snapshots": display_snapshots,
                    "rounds_elapsed": int(record.rounds_elapsed),
                    "session_id": record.session_id,
                },
                participants=[str(actor.pk), *participant_ids, *opponent_ids],
                location=str(record.room_id or ""),
                tick=int(settled_record.settled_tick or get_world_clock().tick),
                visibility="public",
                salience=1,
                award_results=title_awards_list,
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
            # The sleep-control offer is evaluated only after the outermost
            # commit, from the committed survivor state (aftermath removal and
            # any terminal defeat included); a rolled-back unit emits nothing.
            transaction.on_commit(
                lambda actor=actor, session_id=record.session_id: (
                    _emit_terminal_sleep_handoff(actor, session_id)
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


@dataclass(frozen=True)
class _SettlementRestore:
    """The pre-settlement in-process surfaces one settlement unit reinstates.

    Built before the durable unit starts, so a failure anywhere inside it —
    the settlement body, the unit's own commit, or a later write of the same
    unit (the confirmed exit's operation receipt) — can put every touched
    in-process surface back. The idmapper attribute cache is not
    transaction-aware, so a rolled-back durable write alone would leave
    readers observing post-settlement values (fix-combat-settlement-recovery
    D1/D2). ``clear_session`` clears the action context and the battlefield's
    skip-safety registration in-process as well, so both ride this snapshot.
    """

    actor: Any
    attributes: tuple[tuple[str, tuple[bool, Any]], ...]
    battlefield_buffs: tuple[tuple[Any, tuple[bool, Any]], ...]
    fatigue: tuple[tuple[Any, dict[tuple[str, str | None], tuple[bool, Any]]], ...]
    traits: tuple[tuple[Any, Any], ...]
    exam_host: tuple[Any, Any] | None
    action_context: Any
    battlefield: Battlefield | None
    battlefield_registrations: tuple[tuple[str, Any], ...]
    clock: Any
    clock_tick: tuple[int, tuple[bool, Any] | None] | None

    def restore(self) -> None:
        """Reinstate every snapshotted surface, in the round path's order."""
        from world.rules.action import _restore_attribute
        from world.rules.clock import _restore_clock_tick
        from world.rules.skip_safety import _BATTLEFIELDS

        for key, snapshot in self.attributes:
            _restore_attribute(self.actor, key, snapshot)
        for entity, snapshot in self.battlefield_buffs:
            _restore_attribute(entity, "buffs", snapshot)
        for entity, snapshots in self.fatigue:
            for (key, category), snapshot in snapshots.items():
                _restore_attribute(entity, key, snapshot, category)
        for entity, snapshot in self.traits:
            from world.rules.surfaces import restore_traits

            restore_traits(entity, snapshot)
        if self.exam_host is not None:
            from world.rules.guild_exams import restore_exam_host_surfaces

            host, snapshot = self.exam_host
            restore_exam_host_surfaces(host, snapshot)
        self.actor.ndb.action_context = self.action_context
        if self.battlefield is not None:
            # Registrations are process memory, not durable state: restore the
            # exact pre-settlement entries rather than assuming this battle
            # was registered (a failed all-sleep opening runs before it is).
            for key in (
                str(entity.pk) for entity in self.battlefield.roster.values()
            ):
                _BATTLEFIELDS.pop(key, None)
            _BATTLEFIELDS.update(dict(self.battlefield_registrations))
        if self.clock is not None and self.clock_tick is not None:
            # A later write of the same unit rolls the durable tick back, but
            # the idmapper-cached Script attribute is not transaction-aware.
            _restore_clock_tick(self.clock, self.clock_tick)


def _snapshot_settlement_restore(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
) -> _SettlementRestore:
    """Snapshot every in-process surface a terminal settlement may touch."""
    from world.rules.action import _attribute_snapshot
    from world.rules.clock import _snapshot_clock_tick, read_world_clock
    from world.rules.fatigue import FATIGUE_ATTRIBUTE_SURFACES
    from world.rules.skip_safety import _BATTLEFIELDS

    attributes: list[tuple[str, tuple[bool, Any]]] = [
        ("active_combat", _attribute_snapshot(actor, "active_combat")),
        ("last_combat_receipt", _attribute_snapshot(actor, "last_combat_receipt")),
        ("buffs", _attribute_snapshot(actor, "buffs")),
    ]
    fatigue_entities: list[Any] = [actor]
    if battlefield is not None:
        fatigue_entities.extend(
            entity
            for entity in battlefield.roster.values()
            if entity is not actor
        )
    fatigue_snapshots = tuple(
        (
            entity,
            {
                (key, category): _attribute_snapshot(entity, key, category)
                for key, category in FATIGUE_ATTRIBUTE_SURFACES
            },
        )
        for entity in fatigue_entities
    )
    battlefield_buff_snapshots: list[tuple[Any, tuple[bool, Any]]] = []
    if battlefield is not None:
        for entity in battlefield.roster.values():
            if entity is not actor:
                battlefield_buff_snapshots.append(
                    (entity, _attribute_snapshot(entity, "buffs"))
                )
    trait_snapshots: list[tuple[Any, tuple[bool, Any]]] = []
    exam_host: tuple[Any, Any] | None = None
    if record.mode == "guild_exam":
        attributes.append(("guild_rank", _attribute_snapshot(actor, "guild_rank")))
        attributes.append(("guild_exams", _attribute_snapshot(actor, "guild_exams")))
        attributes.append(("title_collection", _attribute_snapshot(actor, "title_collection")))
        attributes.append(("title_equipped", _attribute_snapshot(actor, "title_equipped")))
        # The settlement transaction restores the exam sides' gauges; when it
        # rolls back, restore the in-process trait surfaces too (the idmapper
        # cache is not transaction-aware), for the actor and the opponent.
        from world.rules.surfaces import snapshot_traits

        trait_snapshots.append((actor, snapshot_traits(actor)))
        host = _find_exam_opponent(actor, record)
        if host is not None:
            from world.rules.guild_exams import snapshot_exam_host_surfaces

            exam_host = (host, snapshot_exam_host_surfaces(host))
    clock = read_world_clock()
    battlefield_registrations: tuple[tuple[str, Any], ...] = ()
    if battlefield is not None:
        battlefield_registrations = tuple(
            (str(entity.pk), _BATTLEFIELDS[str(entity.pk)])
            for entity in battlefield.roster.values()
            if str(entity.pk) in _BATTLEFIELDS
        )
    return _SettlementRestore(
        actor=actor,
        attributes=tuple(attributes),
        battlefield_buffs=tuple(battlefield_buff_snapshots),
        fatigue=fatigue_snapshots,
        traits=tuple(trait_snapshots),
        exam_host=exam_host,
        action_context=actor.ndb.action_context,
        battlefield=battlefield,
        battlefield_registrations=battlefield_registrations,
        clock=clock,
        clock_tick=_snapshot_clock_tick(clock) if clock is not None else None,
    )


def _settle_with_restore(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
    outcome: str,
    logs=(),
    *,
    nested_round: bool = False,
    discard_draft: bool = False,
) -> dict[str, Any]:
    """Settle a session outside a round, restoring surfaces on failure.

    ``settle_session`` runs its own durable transaction; when it fails (for
    example a clock write error during forfeit or startup restoration), the
    database keeps the session but the in-process ``active_combat``/exam
    attributes were already reassigned by the settlement steps. Restoring
    them keeps the retry path consistent without waiting for a reload
    (the idmapper attribute cache is not transaction-aware).

    ``nested_round`` marks the settlement as committing through an enclosing
    durable unit (a confirmed exit), so the aftermath's undo is armed for that
    unit. ``discard_draft`` clears the pending party draft inside the
    settlement's own write, so a confirmed surrender discards selections
    atomically with the outcome it enters and a failed unit keeps them. A
    confirmed exit that spans the settlement plus its own receipt takes the
    wider snapshot itself, so this helper's own bundle covers the settlement
    body exactly as it does for a direct forfeit.
    """
    restore = _snapshot_settlement_restore(actor, record, battlefield)
    if discard_draft:
        record = replace(record, draft_entries={}, confirmed_actors=())
    try:
        return settle_session(
            actor, record, battlefield, outcome, logs, nested_round=nested_round
        )
    except Exception:
        from world.rules.defeat_aftermath import drain_pending_undos

        for undo in drain_pending_undos():
            undo()
        restore.restore()
        raise


@serialized_combat_write
def forfeit(actor: Any) -> dict[str, Any]:
    """Settle accumulated time, record defeat/exam FAIL, and clean up.

    Internal, test-only defeat seam: package code reaches this settlement
    through the confirmed party exit only
    (:func:`world.rules.combat_session.exit.confirm_party_exit`), so no
    player-facing route can perform an unconfirmed forfeit. Never re-export it
    as a public route — that is exactly the bypass
    ``party-combat-confirmed-surrender`` removed.
    """
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


@serialized_combat_write
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
