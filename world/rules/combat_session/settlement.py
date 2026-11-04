"""Terminal settlement: one-time time settlement, clearing, and recovery.

The accumulated round time settles exactly once at a terminal outcome through
``settle_session``; ``restore_active_session`` reconstructs a valid persisted
session (or terminates it diagnostically) at startup (fix-combat-
settlement-recovery D1/D2, guild-economy D-6).
"""

import time
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import Any

from evennia.objects.models import ObjectDB

from world.observability import log_info, log_warn
from world.rules.action import _stored_trait_value
from world.rules.clock import get_world_clock, settle_combat_result
from world.rules.combat import COMBAT_YAML, Battlefield
from world.rules.combat_identity import stable_actor_id
from world.rules.combat_session.battlefield import (
    get_required_combat_actors,
    reconstruct_battlefield,
)
from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.combat_session.writer import serialized_combat_write
from world.rules.overwhelm import classify_overwhelm
from world.rules.combat_session.lifecycle import _persist, clear_session
from world.rules.combat_session.records import CombatSessionRecord, read_session
from world.rules.presentation_events import publication_group
from world.rules.settlement_alignment import (
    checkpoint_owner,
    publish_combat_terminal,
)
from world.rules.skip_safety import register_active_battlefield

_ROUND_SECONDS = int(COMBAT_YAML["round"]["seconds"])


#: Writer-local reentrancy guard for automatic enemy-only rounds. While one
#: automatic iteration finalizes, the continuation disposition it produces is
#: consumed by the owning loop itself and can never re-enter an outer hook.
_AUTOMATIC_HOSTILE_ROUNDS: ContextVar[bool] = ContextVar(
    "combat_automatic_hostile_rounds", default=False
)


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
    player_id = stable_actor_id(actor)
    player_team = battlefield.team_of(player_id)
    foe_team = next(team for team in battlefield.teams if team != player_team)
    if player_id in battlefield.fled:
        return "fled"
    player_defeated = (
        _stored_trait_value(actor.traits.hp) <= 0
        or player_id in battlefield.knocked_out
        or int(actor.pk) in record.knocked_out_ids
    )
    if player_defeated:
        return "defeat" if record.mode == "hostile" else "exam_failed"
    if not _team_living(battlefield, foe_team, record):
        return "victory" if record.mode == "hostile" else "exam_passed"
    if record.rounds_elapsed >= _round_cap():
        return "cap"
    return None


def settlement_participants(
    actor: Any,
    battlefield: Battlefield | None,
) -> list[Any]:
    """Return the entities whose gauges one combat interval regenerates.

    Every living, non-fled roster member (fix-combat-session-roster-and-
    overwhelm D1): companions and any non-defeated foe still present recover
    for the interval, so a knocked-out companion can rise above the nonlethal
    HP floor and rejoin a later engagement. A member at 0 HP is dead and
    excluded (kill semantics). The actor alone keeps the historical scope only
    when no roster participant is living and the actor is (a solo flee whose
    actor is alive); a dead actor is never passed, so settlement can never
    revive a defeated player.
    """
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
    return participants


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
    return posture_segments(record, actor_id)


def posture_segments(
    record: CombatSessionRecord,
    actor_id: int,
    *,
    from_round: int = 0,
    through_round: int | None = None,
) -> tuple[tuple[bool, int], ...]:
    """Return the recorded posture intervals clipped to a completed-round range.

    ``from_round``/``through_round`` are completed-round ordinals, so the
    returned seconds are the actual awake/sleep durations inside
    ``[from_round, through_round)``. The engagement timeline is replayed from
    round zero because a transition is only meaningful relative to its
    predecessors, but only the requested slice is returned. A zero-length tail
    after the requested range keeps the posture observed at its final boundary
    so a caller can still determine the starting posture.
    """
    through = (
        record.rounds_elapsed if through_round is None else int(through_round)
    )
    start = int(from_round)
    if start < 0 or through < start or through > record.rounds_elapsed:
        raise ValueError(
            "posture segments require 0 <= from_round <= through_round "
            "<= rounds_elapsed"
        )
    transitions = sorted(
        (transition.round_index, transition.asleep)
        for transition in record.sleep_transitions
        if transition.actor_id == actor_id
    )
    asleep = actor_id in record.initial_sleep_ids
    segments: list[tuple[bool, int]] = []

    def emit(flag: bool, begin: int, end: int, *, keep_empty: bool = False) -> None:
        low = max(begin, start)
        high = min(end, through)
        if high > low:
            segments.append((flag, (high - low) * _ROUND_SECONDS))
        elif keep_empty and low == high == through:
            segments.append((flag, 0))

    cursor = 0
    for round_index, next_asleep in transitions:
        emit(asleep, cursor, round_index)
        cursor = round_index
        asleep = next_asleep
    emit(asleep, cursor, record.rounds_elapsed, keep_empty=True)
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

    Only the still-unpaid suffix of the recorded timeline settles here: a
    member whose earlier rounds were already paid by the paid hostile-round
    writer starts at ``record.settled_rounds``, so the terminal call never
    charges an interval twice.
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
            segments = posture_segments(
                record,
                int(pk),
                from_round=record.settled_rounds,
            )
        else:
            # No engagement evidence: only the live posture is authoritative,
            # and the record still contributes the unpaid combat time.
            segments = (
                (
                    state.posture is not SleepPosture.AWAKE,
                    (record.rounds_elapsed - record.settled_rounds)
                    * _ROUND_SECONDS,
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

    player_team = battlefield.team_of(stable_actor_id(actor))
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


def settle_exam_forced_sleep_opening(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield,
) -> dict[str, Any] | None:
    """Enter the examination's zero-round FAIL for an all-sleep opening.

    Only a designated guild examination keeps the zero-round policy: its
    simulated battle has no hostile combat consequence to resolve, so the
    candidate fails immediately through the ordinary examination terminal
    writer. A hostile engagement returns ``None`` here and resolves real
    enemy-only rounds through
    :func:`~world.rules.combat_session.rounds.continue_incapacitated_hostile_rounds`.
    Invalid targets are rejected by engagement validation before this seam is
    reached.
    """
    if record.mode != "guild_exam":
        return None
    if not _all_present_allies_forced_asleep(actor, battlefield):
        return None
    return _settle_with_restore(actor, record, battlefield, "exam_failed")


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
            # The ordinary-round orchestrator (and hostile engagement) reads
            # this disposition after its round savepoint and pays/resolves the
            # enemy-only continuation. An automatic iteration is guarded so it
            # can only ever consume its own disposition in its owning loop.
            "continuation_required": (
                record.mode == "hostile"
                and not _AUTOMATIC_HOSTILE_ROUNDS.get()
                and not get_required_combat_actors(record, battlefield)
            ),
        }
    # nested_round: this settlement runs inside _submit_request's round
    # transaction, so the aftermath arms its undo for that transaction's
    # own failure boundary.
    return settle_session(
        actor, record, battlefield, outcome, logs, nested_round=True, opening=opening
    )


def _record_terminal_population_protection(record: CombatSessionRecord) -> None:
    """Copy one mapped session's exact cell and closed interval before clearing.

    The interval is ``[started_tick, started_tick + rounds * round seconds]``,
    inclusive, so a catch-up that later passes those ticks still refuses to
    birth into the historical battlefield. Nothing is copied for an abstract or
    staged session, and a missing world or a cell naming another wilderness
    records nothing. The population owner deduplicates the evidence, so a
    restart replay is harmless.
    """
    if record.population_cell is None:
        return
    from world.maps import regional_population

    wilderness = regional_population.live_wilderness()
    if wilderness is None:
        return
    if wilderness.db_key != record.population_cell.get("wilderness"):
        return
    cell = regional_population.coordinate_pair(
        (record.population_cell.get("x"), record.population_cell.get("y"))
    )
    if cell is None:
        return
    regional_population.record_population_protection(
        wilderness,
        engagement_id=record.engagement_id or record.session_id,
        cell=cell,
        start_tick=record.started_tick,
        end_tick=record.started_tick + record.rounds_elapsed * _ROUND_SECONDS,
    )


def _record_terminal_room_protection(record: CombatSessionRecord) -> None:
    """Close one authored-room session's protection interval in the owner."""
    if record.population_cell is not None or record.mode != "hostile":
        return
    from world.maps import monster_activity, regional_population
    from world.rules.movement_edges import LocationRef

    wilderness = regional_population.live_wilderness()
    if wilderness is None or not monster_activity.activity_provisioned(wilderness):
        return
    monster_activity.record_room_protection(
        wilderness,
        session_id=record.session_id,
        location=LocationRef.room(int(record.room_id)),
        start_tick=int(record.started_tick),
        end_tick=int(record.started_tick) + int(record.rounds_elapsed) * _ROUND_SECONDS,
    )


def _settle_monster_combat_terminal(
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
) -> None:
    """Pay every still-combat-owned mapped enemy's remaining combat prefix once.

    A fled enemy is skipped: its cursor already belongs to its journey and the
    departure committed exactly its own prefix. A dead or absent enemy owns no
    further physiology. The terminal boundary is the session's committed
    elapsed combat time, not the wall clock.
    """
    if record.mode != "hostile":
        return
    from evennia.objects.models import ObjectDB

    from world.maps import monster_activity, regional_population

    wilderness = regional_population.live_wilderness()
    if wilderness is None or not monster_activity.activity_provisioned(wilderness):
        return
    from world.rules import world_escape

    fled = set(record.fled_ids)
    if battlefield is not None:
        from world.rules.combat_identity import stable_actor_id

        fled.update(
            int(entity.pk)
            for key, entity in battlefield.roster.items()
            if key in battlefield.fled
        )
    terminal_tick = int(record.started_tick) + int(record.rounds_elapsed) * _ROUND_SECONDS
    owned = set(
        monster_activity.combat_owned_member_ids(wilderness, record.session_id)
    )
    for individual_id in record.enemy_ids:
        if int(individual_id) in fled or int(individual_id) not in owned:
            continue
        entity = ObjectDB.objects.filter(id=int(individual_id)).first()
        if entity is None or _stored_trait_value(entity.traits.hp) <= 0:
            continue
        world_escape.settle_monster_combat_through(
            entity,
            through_tick=terminal_tick,
            operation_id=f"{record.engagement_id or record.session_id}:terminal",
        )


def _settle_prefix_segments(
    entity: Any,
    segments: tuple[tuple[bool, int], ...],
    *,
    start_tick: int,
    session_id: str,
) -> None:
    """Pay an already-completed allied prefix from its recorded posture order."""
    from world.rules.fatigue import (
        FatigueActivity,
        FatigueInterval,
        IntervalCompletion,
        SleepPosture,
        read_optional_fatigue_state,
        settle_fatigue_intervals,
        write_fatigue_state,
    )

    current = read_optional_fatigue_state(entity)
    if current is None or not segments:
        return
    sleeping_posture = (
        current.posture
        if current.posture is not SleepPosture.AWAKE
        else SleepPosture.FORCED
    )
    first_asleep = segments[0][0]
    if first_asleep and current.posture is SleepPosture.AWAKE:
        current = write_fatigue_state(entity, current.reserve_units, sleeping_posture)
    elif not first_asleep and current.posture is not SleepPosture.AWAKE:
        current = write_fatigue_state(entity, current.reserve_units, SleepPosture.AWAKE)
    tick = start_tick
    for asleep, seconds in segments:
        target = sleeping_posture if asleep else SleepPosture.AWAKE
        if current.posture is not target:
            current = write_fatigue_state(entity, current.reserve_units, target)
        if seconds > 0:
            settlement = settle_fatigue_intervals(
                (
                    FatigueInterval(
                        entity,
                        (
                            FatigueActivity.SLEEP
                            if asleep
                            else FatigueActivity.AWAKE_COMBAT
                        ),
                        seconds,
                        current,
                        IntervalCompletion.INDIVISIBLE,
                    ),
                ),
                context={"stage": "fled_combat_prefix", "session": session_id},
                in_combat=True,
                start_tick=tick,
            )
            current = settlement.commits[0].end
        tick += seconds


def settle_fled_combat_prefix(
    commander: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
    *,
    through_round: int,
) -> CombatSessionRecord:
    """Pay exactly the old encounter's unpaid allied physiology and clock once.

    Called by the confirmed retreat after the whole party is marked fled, so the
    terminal settlement that follows excludes those departed bodies from gauge
    regeneration while the clock still advances the unpaid prefix plus the
    attempt round exactly once. The durable ``settled_rounds`` cursor is the
    authority: this call pays ``[settled_rounds, through_round)`` and the
    terminal settlement then pays nothing. Only the allied party's mental
    intervals settle here; the enemy cursors keep their own terminal writer.
    """
    first = int(record.settled_rounds)
    through = int(through_round)
    if through <= first:
        return record
    allied = {int(pk) for pk in record.player_ids}
    if battlefield is not None:
        for entity in battlefield.roster.values():
            pk = getattr(entity, "pk", None)
            if not isinstance(pk, int) or isinstance(pk, bool) or int(pk) not in allied:
                continue
            if getattr(entity, "_is_deleted", False):
                continue
            from world.rules.fatigue import SleepPosture, read_optional_fatigue_state

            state = read_optional_fatigue_state(entity)
            if state is None:
                continue
            segments = posture_segments(
                record,
                int(pk),
                from_round=first,
                through_round=int(record.rounds_elapsed),
            )
            # The attempt round has no recorded boundary yet: its one
            # six-second interval is the live posture the confirmation
            # observed.
            segments = (
                *segments,
                (state.posture is not SleepPosture.AWAKE, _ROUND_SECONDS),
            )
            _settle_prefix_segments(
                entity,
                segments,
                start_tick=int(record.started_tick) + first * _ROUND_SECONDS,
                session_id=record.session_id,
            )
    participants = (
        tuple(
            entity
            for key, entity in battlefield.roster.items()
            if key not in battlefield.fled
            and _stored_trait_value(entity.traits.hp) > 0
        )
        if battlefield is not None
        else ()
    )
    seconds = (through - first) * _ROUND_SECONDS
    settle_combat_result(SimpleNamespace(total_seconds=seconds), participants)
    # No persist here: the caller's round finalization writes the durable
    # record (with this cursor) in the same transaction, so the record is never
    # observable in a state the parser refuses.
    return replace(record, settled_rounds=through)


@checkpoint_owner
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

    One committed terminal settlement is one alignment checkpoint
    (webclient-settlement-alignment): the fact is registered after the final
    clear, clock settlement, aftermath, exam restoration and terminal writes,
    inside this transaction's causal publication group, so every watcher
    receives one freshly rendered complete snapshot instead of this
    settlement's delta. A replayed settlement (the durable ``settled_tick``
    gate) and every nonterminal round publish no checkpoint at all.
    """
    from evennia.objects.models import ObjectDB
    from django.db import transaction
    from world.narrative.events import (
        build_encounter_source_id,
        get_committed_award_results,
        record_narrative_event,
        snapshot_location,
    )

    # The terminal fact is keyed by the encounter's own engagement identity.
    # The transport session id is reusable (one token per player, mode and
    # tick), so it can never identify this engagement's outcome: a record
    # without an engagement identity is malformed and settles nothing.
    if not record.engagement_id:
        from world.rules.combat_session.errors import CombatSessionError, SessionReason

        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "the combat session carries no engagement identity",
        )
    engagement_id = record.engagement_id
    encounter_source_id = build_encounter_source_id(
        engagement_id,
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
        # A committed terminal receipt that reloaded before its session cleared
        # still owns its lawful protected interval: retain it idempotently.
        with transaction.atomic():
            _record_terminal_population_protection(record)
            _record_terminal_room_protection(record)
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
                if getattr(entity, "pk", None) == entity_id:
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
            participants = settlement_participants(actor, battlefield)
            # Physiology settles from the recorded round-boundary posture
            # evidence inside this same transaction, once for the accumulated
            # combat seconds. The clock's COMBAT source deliberately does not
            # settle mental time, so this is the sole terminal fatigue write.
            _settle_terminal_fatigue(record, battlefield, tuple(participants))
            # Mapped enemies own their combat prefix through the map cursor:
            # this is the one terminal writer that pays their unpaid rounds,
            # and it runs before the clock's own combat settlement below.
            _settle_monster_combat_terminal(record, battlefield)
            unpaid_rounds = int(record.rounds_elapsed) - int(record.settled_rounds)
            # A confirmed retreat (or any earlier paid prefix) may already own
            # the whole interval; a zero-second clock advance is not a
            # settlement and must not emit another source event.
            events = (
                settle_combat_result(
                    SimpleNamespace(
                        total_seconds=unpaid_rounds * _ROUND_SECONDS
                    ),
                    participants,
                )
                if unpaid_rounds > 0
                else []
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
                record,
                settled_tick=get_world_clock().tick,
                # The terminal call has now paid every recorded round, so the
                # cursor closes at the completed count. A later replay branch
                # pays nothing either way; this keeps the invariant truthful.
                settled_rounds=int(record.rounds_elapsed),
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

            # The encounter's actual location owner is the durable session
            # room. Its readable label is snapshotted here, from that owner,
            # and an already-removed room keeps its durable identity without
            # an invented label.
            session_room = getattr(actor, "location", None)
            if (
                session_room is None
                or int(getattr(session_room, "pk", 0) or 0) != int(record.room_id)
            ):
                session_room = ObjectDB.objects.filter(id=record.room_id).first()
            location_ref = snapshot_location(session_room)
            if not location_ref.known and record.room_id:
                location_ref = snapshot_location(int(record.room_id))

            record_narrative_event(
                source_id=encounter_source_id,
                event_type="combat_encounter",
                content={
                    "encounter_id": engagement_id,
                    "outcome": normalized_outcome,
                    "gameplay_outcome": outcome,
                    "mode": record.mode,
                    "participant_ids": participant_ids,
                    "opponent_ids": opponent_ids,
                    "display_snapshots": display_snapshots,
                    "rounds_elapsed": int(record.rounds_elapsed),
                    "session_id": record.session_id,
                    "location": location_ref.to_content(),
                },
                participants=[str(actor.pk), *participant_ids, *opponent_ids],
                location=location_ref.identity,
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
            # The closed protection lands in the same transaction, before the
            # session clear (and before any later catch-up can observe it).
            _record_terminal_population_protection(settled_record)
            _record_terminal_room_protection(settled_record)
            clear_session(actor, battlefield, record)
            if record.mode == "guild_exam":
                # Simulated battle: restore the candidate and return the
                # persistent host to its normal self (outfit, effects, full
                # pools, schedule hold released) inside the settlement
                # transaction, so restoration commits or rolls back with the
                # exam outcome (persistent-guild-exam-lifecycle).
                _restore_exam_participants(actor, record, battlefield)
            # The committed terminal checkpoint: every terminal write above has
            # landed, so this is the one place the fresh complete alignment is
            # known to be truthful (webclient-settlement-alignment). It joins
            # this transaction's causal publication group, so a nested
            # relocation, aftermath push or clock effect coalesces into the
            # same single final publication.
            publish_combat_terminal(actor, record.player_ids)
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
    from world.maps import monster_activity, regional_population

    wilderness = regional_population.live_wilderness()
    if wilderness is not None and record.exam_id:
        # The staged examination's own opponent record is released with the
        # rest of the exam cleanup; no other group or roster is touched.
        monster_activity.release_group(wilderness, f"exam:{record.exam_id}")
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
    advance_registry: tuple[dict[int, Any], tuple[Any, ...]] | None

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
        if self.advance_registry is not None:
            # A standalone settlement advances the clock through the whole
            # registered stage set (including regional waves). When a later
            # write of the same unit fails, the durable rows roll back but the
            # stages' in-process surfaces do not, so their registry is
            # restored here exactly as the round and confirmed-exit paths do.
            from world.rules.clock import _restore_advance_registry

            registry, scope = self.advance_registry
            _restore_advance_registry(registry, scope)


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
    advance_registry = None
    if record.population_cell is not None:
        from world.rules.clock import (
            AdvanceSource,
            WorldClock,
            build_advance_snapshot_registry,
        )

        scope = () if battlefield is None else tuple(battlefield.roster.values())
        advance_registry = (
            build_advance_snapshot_registry(
                clock if clock is not None else WorldClock(),
                (record.rounds_elapsed - record.settled_rounds)
                * _ROUND_SECONDS,
                AdvanceSource.COMBAT,
                scope,
            ),
            scope,
        )
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
        advance_registry=advance_registry,
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


#: Durable host-release obligation left behind when an examination's malformed
#: session is retired but its persistent host could not be released yet. It
#: names the authoritative identities, never the corrupt payload, so the next
#: recovery can finish the release without any surviving session record.
_EXAM_RELEASE_ATTR = "combat_exam_release_pending"


def _raw_hint(raw: Any, field: str) -> str | None:
    """Return one raw payload text hint, or ``None`` when it states nothing."""
    value = raw.get(field)
    return value if isinstance(value, str) and value else None


def _read_exam_records(actor: Any) -> list[Any] | None:
    """Read the candidate's persisted examination history, or ``None``."""
    from world.rules.guild_exams import GuildExamError, _read_exams

    try:
        return list(_read_exams(actor))
    except GuildExamError as error:
        log_warn(
            "guild_exam_unidentified_history_unreadable",
            exc=error,
            context={"char": str(actor.pk)},
        )
        return None


def _unidentified_exam_record(actor: Any, raw: Any) -> tuple[Any | None, bool]:
    """Resolve the authoritative examination a malformed session belonged to.

    Returns ``(record, resolved)``. The candidate's own persisted history is
    the authority; the corrupt payload's ``exam_id``/``session_id`` only choose
    between ACTIVE examinations. A hinted ACTIVE record wins, then the single
    ACTIVE record the duplicate rule permits. Anything else leaves
    ``resolved`` false: the caller must not clear the payload on ambiguity,
    because an ACTIVE examination may still own a host.
    """
    from world.rules.guild_exams import ExamState

    records = _read_exam_records(actor)
    if records is None:
        return None, True
    active = [record for record in records if record.state is ExamState.ACTIVE]
    if not active:
        return None, True
    exam_hint = _raw_hint(raw, "exam_id")
    session_hint = _raw_hint(raw, "session_id")
    named = [
        record
        for record in active
        if (exam_hint is not None and record.exam_id == exam_hint)
        or (session_hint is not None and record.session_id == session_hint)
    ]
    if len(named) == 1:
        return named[0], True
    if len(active) == 1:
        return active[0], True
    log_warn(
        "guild_exam_unidentified_ambiguous",
        context={"char": str(actor.pk), "candidates": len(active)},
    )
    return None, False


def _release_exam_host(actor: Any, exam_id: str, host_id: int) -> bool:
    """Release one examination's persistent host; report whether it completed."""
    from evennia.objects.models import ObjectDB
    from django.db import transaction

    from world.rules.guild_exams import restore_exam_host
    from world.rules.traits import restore_gauges_to_full

    host = ObjectDB.objects.filter(id=host_id).first()
    if host is None:
        log_warn(
            "guild_exam_unidentified_host_missing",
            context={"char": str(actor.pk), "exam": exam_id, "host": host_id},
        )
        return True
    try:
        with transaction.atomic():
            restore_exam_host(host, exam_id)
            restore_gauges_to_full(actor)
            # The session clear cannot release a roster it cannot reconstruct,
            # and the corrupt payload's roster is never trusted: only this
            # examination's own candidate and host are unregistered.
            from world.rules.skip_safety import (
                unregister_active_battlefield,
                unregister_participants,
            )

            unregister_active_battlefield(host)
            unregister_active_battlefield(actor)
            unregister_participants((host_id, int(actor.pk)))
    except Exception as error:
        log_warn(
            "guild_exam_unidentified_host_release_failed",
            exc=error,
            context={
                "char": str(actor.pk),
                "exam": exam_id,
                "host": host_id,
                "retry": _EXAM_RELEASE_ATTR,
            },
        )
        return False
    return True


def _pending_exam_release(actor: Any) -> dict[str, Any] | None:
    """Read the durable host-release obligation, or ``None``."""
    raw = getattr(getattr(actor, "db", None), _EXAM_RELEASE_ATTR, None)
    if not isinstance(raw, Mapping):
        return None
    exam_id = raw.get("exam_id")
    host_id = raw.get("host_id")
    if not isinstance(exam_id, str) or not exam_id:
        return None
    if not isinstance(host_id, int) or isinstance(host_id, bool):
        return None
    return {"exam_id": exam_id, "host_id": host_id}


def _write_pending_exam_release(
    actor: Any, exam_id: str | None, host_id: int | None
) -> None:
    """Record or clear the durable host-release obligation."""
    if exam_id is None or host_id is None:
        actor.db.combat_exam_release_pending = None
        return
    actor.db.combat_exam_release_pending = {
        "exam_id": exam_id,
        "host_id": int(host_id),
    }


def _retry_pending_exam_release(actor: Any) -> None:
    """Finish a host release that a previous recovery could not complete."""
    pending = _pending_exam_release(actor)
    if pending is None:
        return
    if _release_exam_host(actor, pending["exam_id"], pending["host_id"]):
        _write_pending_exam_release(actor, None, None)


def _retire_unidentified_exam(actor: Any) -> bool:
    """Retire an examination whose persisted session lost its identity.

    A persisted guild-examination session without its engagement identity can
    no longer act or settle through the ordinary combat writer, because every
    occurrence that writer commits is keyed by that identity. The candidate's
    examination record and the persistent host's own surfaces are independent
    authoritative state, so the examination is marked FAILED and the host is
    released here. No combat occurrence is fabricated and no replacement
    identity is invented: the corrupt payload is read only to learn which
    examination to retire, never to drive a settlement.

    The examination terminal state and the host release are separate units. A
    release that cannot complete leaves a durable host-release obligation and
    still returns ``True`` -- the session clear must happen, and the obligation
    is what the next recovery retries. ``False`` means ownership is unresolved
    (ambiguous ACTIVE examinations), so the payload is kept rather than erased.
    """
    from django.db import transaction

    raw = getattr(getattr(actor, "db", None), "active_combat", None)
    # A persisted Evennia attribute reads back as a mapping proxy, not a dict.
    if isinstance(raw, Mapping) and raw.get("mode") != "guild_exam":
        return True
    record, resolved = _unidentified_exam_record(
        actor, raw if isinstance(raw, Mapping) else {}
    )
    if not resolved:
        return False
    if record is None:
        return True
    from types import SimpleNamespace

    from world.rules.guild_exams import (
        GuildExamError,
        ExamState,
        settle_exam_outcome,
    )

    exam_id = record.exam_id
    if record.state is ExamState.ACTIVE:
        try:
            with transaction.atomic():
                settle_exam_outcome(
                    actor,
                    SimpleNamespace(mode="guild_exam", exam_id=exam_id),
                    None,
                    "exam_failed",
                )
        except GuildExamError as error:
            # An unreadable examination history cannot be marked; the host is
            # still released below.
            log_warn(
                "guild_exam_unidentified_retirement_unavailable",
                exc=error,
                context={"char": str(actor.pk), "exam": exam_id},
            )
        except Exception as error:
            log_warn(
                "guild_exam_unidentified_retirement_failed",
                exc=error,
                context={"char": str(actor.pk), "exam": exam_id},
            )
            return False
    if not _release_exam_host(actor, exam_id, int(record.opponent_id)):
        # Hand the release to the next recovery as its own durable obligation:
        # the corrupt session must not be kept as the retry handle, because a
        # retained unparseable active_combat blocks every new engagement.
        _write_pending_exam_release(actor, exam_id, int(record.opponent_id))
    return True


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
    # A previous recovery may have retired the session but not yet released
    # its examination host; finish that before anything else.
    _retry_pending_exam_release(actor)
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
        # An unparseable examination still owns its candidate record and its
        # persistent host, both of which are independent authoritative state:
        # retire them here so a session that lost its occurrence identity can
        # never strand the candidate or keep the host examination-owned. Only
        # unresolved ownership keeps the payload; a pending host release is its
        # own durable obligation and never blocks the session clear.
        retired = _retire_unidentified_exam(actor)
        if retired:
            # A cleanup that retires a previously active presentation is a
            # committed combat termination too, but the payload is untrusted:
            # only the acting character's own identity may name a target, and
            # no participant id, outcome or settlement is inferred from it
            # (webclient-settlement-alignment).
            with publication_group():
                clear_session(actor, None, None)
                publish_combat_terminal(actor)
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
    if host is None or stable_actor_id(host) == stable_actor_id(actor):
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
