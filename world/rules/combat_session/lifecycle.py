"""Session lifecycle: engagement, persistence, and clearing.

``engage``/``engage_group`` create one persistent hostile session and wait for
player input; ``_persist`` writes the record; ``clear_session`` retires the
session, its skip-safety registration, and its ground/positional markers.
"""

from typing import Any

from django.db import transaction

from evennia.objects.models import ObjectDB

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.observability import log_info
from world.rules.action import _stored_trait_value
from world.rules.combat import Battlefield
from world.rules.combat_identity import stable_actor_id
from world.rules.combat_session.observations import discard_session_memory
from world.rules.combat_session.battlefield import reconstruct_battlefield
from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.combat_session.records import (
    CombatSessionRecord,
    read_session_uncached,
    read_session,
    session_id_for,
    to_storage,
)
from world.rules.overwhelm import classify_overwhelm
from world.rules.skip_safety import (
    register_active_battlefield,
    unregister_active_battlefield,
)


from world.rules.combat_session.writer import serialized_combat_write


@serialized_combat_write
def _persist(actor: Any, record: CombatSessionRecord) -> None:
    actor.db.active_combat = to_storage(record)


@serialized_combat_write
def _persist_draft_increment(commander: Any) -> None:
    """Reload the uncached durable record and increment draft_version without dropping latest commands."""
    from dataclasses import replace
    current = read_session_uncached(commander)
    if current is None:
        current = read_session(commander)
    if current is not None:
        updated = replace(current, draft_version=current.draft_version + 1)
        _persist(commander, updated)


def _terminal_session_id(actor: Any, record: CombatSessionRecord | None) -> str | None:
    """The session id still recoverable at terminal cleanup, if any is.

    The durable record carries it while it is still stored, so cleanup reaches
    the recorded AI tuning even on the unparseable-payload path, where no valid
    record was parsed and only the raw storage remains.
    """
    if record is not None:
        return record.session_id
    stored = actor.db.active_combat
    if isinstance(stored, dict):
        candidate = stored.get("session_id")
        if isinstance(candidate, str):
            return candidate
    return None


@serialized_combat_write
def clear_session(
    actor: Any,
    battlefield: Battlefield | None = None,
    record: CombatSessionRecord | None = None,
) -> None:
    """Clear session/context state and skip-safety registration.

    Every persisted participant is unregistered (party-combat D-5): when the
    battlefield cannot be reconstructed, the record's participant dbrefs still
    release surviving companions and monsters from skip safety, and the
    participant scan purges even a deleted participant's stale key, so no
    registration of the session survives settlement.

    The session's recorded in-process AI tuning is dropped here as well, so no
    completed session stays observable and a long-lived process does not
    accumulate one record per session it has ever run.
    """
    from world.rules.skip_safety import unregister_participants

    session_id = _terminal_session_id(actor, record)
    if record is not None:
        # Every lawful clear -- the terminal settlement, an operator deletion
        # of a participant, or startup restoration of a committed receipt --
        # retains the session's exact cell and closed interval before the
        # record disappears. The population owner deduplicates the evidence,
        # and a malformed record never reaches here (it was not parsed).
        from world.rules.combat_session.settlement import (
            _record_terminal_population_protection,
        )

        _record_terminal_population_protection(record)
    actor.db.active_combat = None
    actor.ndb.action_context = None
    if session_id is not None:
        # Terminal cleanup is a commit-only request (monster-ai-observation-
        # lifecycle): the session's observation memory and its recorded tuning
        # are discarded once the outermost transaction commits, so a failed
        # or rolled-back settlement keeps both.
        discard_session_memory(session_id)
    unregister_active_battlefield(actor)
    if battlefield is not None:
        for key in list(battlefield.roster):
            unregister_active_battlefield(battlefield.roster[key])
    if record is not None:
        unregister_participants((*record.player_ids, *record.enemy_ids))

    from django.db import transaction
    from world.rules.buffs import (
        clear_lamb_seals,
        remove_ground_markers,
        remove_positional_markers,
    )

    participants: set[Any] = set()
    if battlefield is not None:
        participants.update(battlefield.roster.values())
    if record is not None:
        for dbref in (*record.player_ids, *record.enemy_ids):
            obj = ObjectDB.objects.filter(id=dbref).first()
            if obj is not None:
                participants.add(obj)
    participants.add(actor)
    for entity in participants:
        removed = remove_ground_markers(entity) + remove_positional_markers(entity)
        seals = clear_lamb_seals(entity)
        if removed or seals:
            boundary = {
                "char": str(entity.pk),
                "count": removed + seals,
                "seals": seals,
                "reason": "session_end",
            }
            transaction.on_commit(
                lambda b=boundary: log_info("combat_marker_swept", context=b)
            )


def _require_engagement_target(actor: Any, target: Any) -> None:
    """Apply ``engage_group()``'s exact per-target gates to one target."""
    if not isinstance(target, Monster):
        raise CombatSessionError(SessionReason.NOT_HOSTILE)
    if actor.location is None or target.location is not actor.location:
        raise CombatSessionError(SessionReason.NOT_PRESENT)
    if _stored_trait_value(target.traits.hp) <= 0:
        raise CombatSessionError(SessionReason.TARGET_DEAD)


def engage(actor: Any, target: Any) -> dict[str, Any]:
    """Create one persistent hostile session for a present living monster.

    The named target is re-validated with ``engage_group()``'s exact gates
    first, so a dead, remote or non-monster anchor is refused without
    substituting a same-labeled bystander. Ordinary engagement then admits
    every living, co-located Monster in persistent-ID order (the whole-cell
    roster), while the `target` only chooses which identity the caller named.
    The signature, return shape, and raised ``CombatSessionError`` reasons
    remain unchanged for existing call sites.

    This is the sole ordinary entry point; explicitly staged callers that
    need a declared participant set use :func:`engage_group` directly.
    """
    if not isinstance(actor, PlayerCharacter):
        raise CombatSessionError(SessionReason.NOT_A_PLAYER)
    if read_session(actor) is not None:
        raise CombatSessionError(SessionReason.ALREADY_IN_COMBAT)
    _require_engagement_target(actor, target)
    # Deferred: ``combat_initiation`` imports this package, so the shared
    # roster helper is resolved at call time to keep the dependency one-way.
    from world.rules.combat_initiation import field_enemy_roster

    return engage_group(actor, field_enemy_roster(actor))


@serialized_combat_write
def engage_group(
    actor: Any,
    targets: Any,
    *,
    opening_first_actor: str | None = None,
) -> dict[str, Any]:
    """Create one persistent hostile session against several present monsters.

    The voluntary authority: every step single-target engagement performed
    before this change is carried here (combat-session-opening-dispatch D-4).
    ``_create_hostile_session`` owns the shared validated body; this wrapper
    preserves the established entry point, immediate registration and the
    automatic continuation of an incapacitated party.
    """
    return _create_hostile_session(
        actor,
        targets,
        authority="voluntary",
        opening_first_actor=opening_first_actor,
    )


def create_hostile_contact_session(
    commander: Any,
    targets: Any,
    *,
    started_tick: int,
) -> dict[str, Any]:
    """Create one authored-contact session at its exact occurrence tick.

    Rules-owner only: ``hostile_contact`` authority is never reachable from a
    client payload. The admission does not run the predecessor continuation
    (a clock source must never advance the clock) and registers skip-safety
    only once the enclosing transaction committed, re-reading the surviving
    engagement so a terminal interval leaves no stale registration.
    """
    return _create_hostile_session(
        commander,
        targets,
        authority="hostile_contact",
        started_tick=int(started_tick),
        settle_continuation=False,
        defer_registration=True,
    )


def _register_surviving_session(commander: Any) -> None:
    """Register the final committed engagement for skip safety, if it survives."""
    record = read_session(commander)
    if record is None or record.settled_tick is not None:
        return
    register_active_battlefield(reconstruct_battlefield(commander, record))


@serialized_combat_write
def _create_hostile_session(
    actor: Any,
    targets: Any,
    *,
    authority: str,
    opening_first_actor: str | None = None,
    started_tick: int | None = None,
    settle_continuation: bool = True,
    defer_registration: bool = False,
) -> dict[str, Any]:
    """Create one persistent hostile session against several present monsters.

    Carries every step single-target engagement performed before this change
    (combat-session-opening-dispatch D-4): the PlayerCharacter check, the
    no-active-session check, the per-target living-hostile-``Monster``-in-room
    checks in their established order and reasons, ``combat_companions()``
    collection, record construction with one dbref per supplied target in
    deterministic (sorted-pk) order, battlefield reconstruction, persistence,
    skip-safety registration, and dialogue clearing. Any single invalid
    target rejects the whole group before anything is persisted or
    registered, and a repeated target dbref is rejected as
    ``DUPLICATE_PARTICIPANT``. The informational ``classify_overwhelm``
    verdict is computed once over the complete multi-enemy roster and is
    never consulted for dispatch here (single-shot-resolution): engagement
    runs no action before the player chooses one.

    ``opening_first_actor`` is the encounter's explicit opening-order policy
    (``player-combat-session``): the stable individual identity that acts
    first in the first complete round, persisted with the session so it
    survives the waiting seed and is consumed exactly once. ``engage()`` and
    every ordinary engagement pass nothing, so ordinary entry order never
    changes initiative.

    ``authority`` is the closed ``voluntary``/``hostile_contact`` vocabulary.
    Only the rules owner of field contact may request hostile authority; the
    only voluntary sleep-action gate on initiation is
    ``authorize_member(..., PURPOSE_ACT)`` in ``combat_initiation``'s opening
    path, which hostile contact deliberately never traverses. Party ownership
    and battlefield eligibility are retained unchanged, and a sleeping body
    gains no action authority. ``started_tick`` is the exact occurrence the
    caller observed (never a later persisted clock read); ``settle_continuation``
    and ``defer_registration`` exist for the source/owner split.
    """
    if authority not in ("voluntary", "hostile_contact"):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            f"unknown admission authority {authority!r}",
        )
    if not isinstance(actor, PlayerCharacter):
        raise CombatSessionError(SessionReason.NOT_A_PLAYER)
    if read_session(actor) is not None:
        raise CombatSessionError(SessionReason.ALREADY_IN_COMBAT)
    if isinstance(targets, (str, bytes)) or not hasattr(targets, "__iter__"):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "engage_group requires a sequence of targets",
        )
    targets = list(targets)
    if not targets:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "engage_group requires at least one target",
        )
    seen_pks: set[Any] = set()
    for target in targets:
        pk = getattr(target, "pk", None)
        if pk is not None and pk in seen_pks:
            raise CombatSessionError(
                SessionReason.DUPLICATE_PARTICIPANT,
                f"target dbref {pk} is supplied more than once",
            )
        seen_pks.add(pk)
    for target in targets:
        _require_engagement_target(actor, target)

    from world.rules.fatigue import sleep_blocks_actions
    from world.rules.party import combat_companions

    companion_entities = combat_companions(actor)
    companions = [int(companion.pk) for companion in companion_entities]
    # Every admission input is checked by stable identity before the encounter
    # counter or any session surface is written: the same entity supplied
    # twice (as a target, a companion, or the actor) rejects atomically.
    participant_identities = [
        stable_actor_id(actor),
        *(stable_actor_id(companion) for companion in companion_entities),
        *(stable_actor_id(target) for target in targets),
    ]
    if len(participant_identities) != len(set(participant_identities)):
        raise CombatSessionError(
            SessionReason.DUPLICATE_PARTICIPANT,
            "a participant identity is supplied more than once",
        )
    # A sleeping body still joins the roster: sleep is a live posture that
    # excludes its own commands, never a knockout or an absence. The initial
    # posture is recorded as terminal-accounting evidence only; the live
    # posture stays the eligibility authority.
    initial_sleep_ids = tuple(
        sorted(
            int(entity.pk)
            for entity in (actor, *companion_entities, *targets)
            if sleep_blocks_actions(entity)
        )
    )
    counter = int(getattr(actor.db, "combat_encounter_seq", 0) or 0) + 1
    sequence_before = (actor.attributes.has("combat_encounter_seq"),
                       actor.attributes.get("combat_encounter_seq"))
    actor.db.combat_encounter_seq = counter
    if started_tick is None:
        from world.rules.clock import get_world_clock

        occurrence_tick = int(get_world_clock().tick)
        session_id = session_id_for(actor, "hostile")
    else:
        from world.rules.combat_session.records import format_session_id

        occurrence_tick = int(started_tick)
        session_id = format_session_id(actor, "hostile", occurrence_tick)
    from world.maps.regional_population import mapped_population_cell

    record = CombatSessionRecord(
        session_id=session_id,
        engagement_id=f"{session_id}:{counter}",
        mode="hostile",
        room_id=int(actor.location.pk),
        player_ids=(int(actor.pk), *companions),
        enemy_ids=tuple(sorted(int(target.pk) for target in targets)),
        fled_ids=(),
        knocked_out_ids=(),
        rounds_elapsed=0,
        exam_id=None,
        opening_first_actor=opening_first_actor,
        initial_sleep_ids=initial_sleep_ids,
        # The engagement's own game-time occurrence and real battlefield cell:
        # a later-round defeat is placed from these, never from the pre-combat
        # tick, and the cell stays protected independently of room reuse.
        started_tick=occurrence_tick,
        population_cell=mapped_population_cell(actor),
    )
    battlefield = reconstruct_battlefield(actor, record)
    from world.maps import monster_activity, regional_population
    from world.rules.combat_session.snapshot import (
        _restore_round_clock,
        _restore_round_touched,
        _snapshot_party_surfaces,
        _snapshot_round_clock,
        _snapshot_round_touched,
    )
    from world.rules.progression import (
        restore_practice_dedupe,
        snapshot_practice_dedupe,
    )

    wilderness = regional_population.live_wilderness()
    activity_before = (
        monster_activity.snapshot_activity_surfaces(wilderness)
        if wilderness is not None
        and monster_activity.activity_provisioned(wilderness)
        else None
    )
    # Admission plus the automatic enemy-only continuation form one durable
    # unit: a canonical engagement whose whole present allied party is already
    # asleep (or otherwise action-forbidden) pays its real rounds now instead
    # of entering a fabricated zero-round defeat, and a failure anywhere in
    # that unit restores every clock-source, physiology, activity and session
    # surface.
    from world.rules.combat_session.settlement import _round_cap

    clock_before = _snapshot_round_clock(
        record, battlefield, horizon_rounds=_round_cap()
    )
    touched, extra = _snapshot_round_touched(actor, battlefield, record)
    party_before, members_before, relations_before = _snapshot_party_surfaces(
        actor, battlefield
    )
    dedupe_before = snapshot_practice_dedupe()
    item_journals: list[Any] = []
    continuation: dict[str, Any] | None = None
    try:
        with transaction.atomic():
            _persist(actor, record)
            _own_mapped_combat_time(record)
            if settle_continuation:
                from world.rules.combat_session.rounds import (
                    continue_incapacitated_hostile_rounds,
                )

                continuation = continue_incapacitated_hostile_rounds(
                    actor, journals=item_journals
                )
    except Exception:
        # Admission may already have paid an idle prefix or opened room
        # protection, and the continuation may have paid real rounds; the
        # database rolled back, so restore every process-memory surface it
        # left behind before the failure escapes.
        for journal in item_journals:
            journal.restore()
        if activity_before is not None:
            monster_activity.restore_activity_surfaces(
                activity_before, wilderness=wilderness
            )
        _restore_round_clock(clock_before)
        _restore_round_touched(
            actor,
            touched,
            extra,
            party_before,
            members_before,
            relations_before,
        )
        restore_practice_dedupe(dedupe_before)
        # The encounter counter is an in-process idmapper surface like the
        # session itself: a rolled-back admission never consumes an encounter
        # sequence number.
        if sequence_before[0]:
            actor.attributes.add(
                "combat_encounter_seq", sequence_before[1]
            )
        else:
            actor.attributes.remove("combat_encounter_seq")
        raise
    final = read_session(actor)
    if final is not None:
        # A terminal continuation has already cleared the session and its
        # registrations; only a surviving active session is registered. A
        # deferred registration waits for the enclosing commit and re-reads
        # the surviving engagement, so an interval that ended before the
        # commit (or a later rollback) leaves no stale battlefield behind.
        if defer_registration:
            transaction.on_commit(
                lambda commander=actor: _register_surviving_session(commander)
            )
        else:
            register_active_battlefield(battlefield)
    # Hostility ends a conversation (webclient-align-07): the session is
    # retired in the same deterministic-core path that persisted the session,
    # so no snapshot can ever render dialogue mode over a live combat session.
    from world.rules.dialogue import clear_dialogue_session

    clear_dialogue_session(actor)
    return {
        "record": final if final is not None else record,
        "overwhelming_team": classify_overwhelm(battlefield),
        # Internal slot: the entry adapters render the automatic rounds' logs
        # and select the terminal or interactive message from its outcome.
        "continuation": continuation,
    }


def _own_mapped_combat_time(record: CombatSessionRecord) -> None:
    """Claim the session's mapped enemies' combat interval at admission.

    Only a real hostile session over a provisioned world with a map-owned
    group participates; a staged or abstract session owns no member cursor.
    The authored-room protection
    interval of a room-based session is opened here and closed by the terminal
    settlement, through the activity owner's own record.
    """
    if record.mode != "hostile":
        return
    from world.maps import monster_activity, regional_population

    wilderness = regional_population.live_wilderness()
    if wilderness is None or not monster_activity.activity_provisioned(wilderness):
        return
    for individual_id in record.enemy_ids:
        monster_activity.begin_member_combat(
            wilderness,
            individual_id=int(individual_id),
            session_id=record.session_id,
            tick=int(record.started_tick),
        )
    if record.population_cell is None:
        from world.rules.movement_edges import LocationRef

        monster_activity.record_room_protection(
            wilderness,
            session_id=record.session_id,
            location=LocationRef.room(int(record.room_id)),
            start_tick=int(record.started_tick),
            end_tick=None,
        )
