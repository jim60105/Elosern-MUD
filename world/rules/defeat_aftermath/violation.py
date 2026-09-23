"""The violation hook registry and the violation sequence.

Holds the ``_VIOLATION_HOOK`` registry point, the attempt-loop building
blocks (victim pool, draws, deltas, counters, clock advances, EventLog
entries), and the registered sequence body itself.

Part of the :mod:`world.rules.defeat_aftermath` package split; the package
re-exports the historical public surface.
"""
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from django.conf import settings

from world.observability import log_info, log_warn
from world.rules.action import (
    _attribute_snapshot,
    _restore_attribute,
    _stored_trait_value,
)
from world.rules.clock import (
    AdvanceSource,
    _ADVANCE_ENTITY_SURFACES,
    _restore_advance_registry,
    _restore_clock_tick,
    _snapshot_clock_tick,
    build_advance_snapshot_registry,
)
from world.rules.defeat_aftermath.contracts import (
    ViolationDeltas,
    ViolationHookContext,
    ViolationOutcome,
)
from world.rules.defeat_aftermath.rulebook import DEFEAT_AFTERMATH_RULEBOOK
from world.rules.event_log import EventEntry
from world.rules.player_messages import defeat_aftermath_template
from world.rules.pleasure import apply_pleasure_gain
from world.rules.sexual_act_effects import mutator_name_for
from world.rules.sexual_resist import resist_verdict
from world.rules.state_derived_roll import derived_roll


_VIOLATION_HOOK: Callable[..., None] | None = None


def register_violation_hook(hook: Callable[..., None]) -> None:
    """Register the violation-sequence body contributed by an adult change.

    A single registration point: a second distinct registration fails loudly
    instead of silently replacing an adult phase; re-registering the
    identical callable is accepted so idempotent boot registration stays
    possible.
    """
    global _VIOLATION_HOOK
    if not callable(hook):
        raise ValueError("the defeat violation hook must be callable")
    if _VIOLATION_HOOK is not None and _VIOLATION_HOOK is not hook:
        raise RuntimeError("the defeat violation hook is already registered")
    _VIOLATION_HOOK = hook


def _call_violation_hook(
    context: ViolationHookContext,
) -> dict[str, ViolationOutcome]:
    """Run the guarded violation hook point (design D-C4).

    Pure guard: with ``DEFEAT_ADULT_SCENES`` off the hook is never called and
    the core-only settlement is the entire behavior; with the flag on but no
    adult body registered the call is a no-op. The flag is read exactly once,
    at hook entry (no mid-sequence toggle semantics, DA4 delta requirement).
    """
    if not settings.DEFEAT_ADULT_SCENES:
        return {}
    if _VIOLATION_HOOK is None:
        return {}
    outcomes = _VIOLATION_HOOK(context)
    return outcomes if outcomes is not None else {}


def _violation_scope(actor: Any) -> list[Any]:
    """The attempt clock advance's entity scope: deliberately empty.

    The attempts spend world time as fiction over the atomic settlement —
    the downed body does not heal, decay, or climax-settle inside its own
    violation. The shipped settlement stages are accumulator-based, so
    every body (the victim included) is caught up unchanged at its next
    in-scope advance (the recovery phase's allies scope, or any later
    advance); boundary stages and world event sources still run, so
    deadlines and restocks cross exactly like any other clock window. An
    entity-scoped advance would regenerate the victim past the recovery
    wake target pinned by defeat-aftermath-recovery and mutate companions
    and violators the change declares untouched (rubber-duck plan review
    finding 2).
    """
    del actor
    return []


def _snapshot_sexual_surfaces(entity: Any) -> Callable[[], None]:
    """Snapshot every durable sexual surface one entity may expose (DA4).

    The clock's advance registry restores what each advance itself touched;
    the violation's deltas are applied between advances, so their surfaces
    are captured here and restored by the caller's undo on any failure —
    the transaction restores the database rows, the idmapper cache needs
    this explicit restore (design D-C5 discipline).
    """
    snapshots = tuple(
        (name, category, _attribute_snapshot(entity, name, category))
        for name, category in _ADVANCE_ENTITY_SURFACES
    )

    def _restore() -> None:
        for name, category, snapshot in snapshots:
            _restore_attribute(entity, name, snapshot, category=category)
        # Drop the materialized ``sexual`` handler so the next access re-mounts
        # from the restored attributes — the same cache invalidation
        # ``_restore_entity_state`` and the clock's advance restore perform
        # (the idmapper-cached handler would otherwise outlive the rollback).
        entity.__dict__.pop("sexual", None)

    return _restore


def _derived_resist_roll(
    session_id: str,
    violator: Any,
    victim_key: str,
    attempt_index: int,
    rolls: list[int],
) -> Callable[[], int]:
    """Build the state-derived d100 source for one resist contest (D-V4).

    The wrapper records every consumed value so the EventLog reports exactly
    the roll the contest used, and nothing when ``resist_verdict``'s shipped
    auto-comply branches return before the dice (finding 3).
    """
    violator_key = str(violator.pk)

    def _roll() -> int:
        value = derived_roll(
            session_id, violator_key, victim_key, attempt_index, "resist"
        )
        rolls.append(value)
        return value

    return _roll


def _apply_violation_deltas(
    victim: Any, aggressor: Any, deltas: ViolationDeltas
) -> None:
    """Apply one attempt's declared pleasure points through the shipped path."""
    if deltas.victim_pleasure:
        apply_pleasure_gain(victim, deltas.victim_pleasure)
    if deltas.aggressor_pleasure:
        apply_pleasure_gain(aggressor, deltas.aggressor_pleasure)


def _victim_climax_onset(
    victim: Any, aggressor: Any, deltas: ViolationDeltas
) -> bool:
    """Apply the deltas and report one climax onset.

    An onset is the victim's climax phase pushed into ``進行中`` by this very
    attempt — the digest's climax count and one ``climax: true`` flag on the
    attempt's ``violation_act`` entry, keeping outcome and EventLog counts
    equal by construction.
    """
    was_in_progress = victim.sexual.climax_phase.level == "進行中"
    _apply_violation_deltas(victim, aggressor, deltas)
    return not was_in_progress and victim.sexual.climax_phase.level == "進行中"


def _credit_violation_counters(
    victim: Any, violator: Any, counters: tuple[str, ...]
) -> None:
    """Credit every declared counter on BOTH bodies (DA3 shared convention)."""
    for name in counters:
        mutator = mutator_name_for(name)
        getattr(victim.sexual, mutator)()
        getattr(violator.sexual, mutator)()


def _advance_attempt_clock(
    clock: Any,
    seconds: int,
    scope: list[Any],
    restores: list[Callable[[], None]],
) -> None:
    """Advance the world clock by one attempt's declared duration (DA4).

    Same discipline as the recovery phase: the advance registry and the
    clock tick are snapshotted so the caller's failure boundary can restore
    both the database (through the transaction) and the idmapper cache.
    """
    registry = build_advance_snapshot_registry(
        clock, seconds, AdvanceSource.DEFEAT_AFTERMATH, scope
    )
    tick_snapshot = _snapshot_clock_tick(clock)
    clock.advance(seconds, AdvanceSource.DEFEAT_AFTERMATH, scope)

    def _restore(
        clock=clock, registry=registry, tick=tick_snapshot, scope=tuple(scope)
    ) -> None:
        _restore_clock_tick(clock, tick)
        _restore_advance_registry(registry, scope)

    restores.append(_restore)


def _violation_attempt_entry(
    violator: Any,
    victim: Any,
    attempt_index: int,
    verdict: Any,
    rolls: list[int],
    *,
    player_victim: bool,
) -> EventEntry:
    """One ``violation_attempt`` entry: the contest exactly as it ran.

    ``actor`` is the violator, ``target`` the selected victim; the template
    follows the victim so the offline prose names whoever the attempt
    actually targeted (the player-facing lines stay byte-identical).
    """
    return EventEntry(
        kind="violation_attempt",
        actor=str(violator.key),
        target=str(victim.key),
        data={
            "attempt": attempt_index,
            "roll": rolls[-1] if rolls else None,
            "auto_comply": bool(verdict.auto_comply),
            "actor_score": verdict.actor_score,
            "resister_score": verdict.resister_score,
        },
        text_template=defeat_aftermath_template(
            "violation_attempt" if player_victim else "violation_attempt_companion"
        ),
    )


def _violation_resisted_entry(
    violator: Any, victim: Any, attempt_index: int, *, player_victim: bool
) -> EventEntry:
    """One ``violation_resisted`` entry: the contest outcome went to the prey."""
    return EventEntry(
        kind="violation_resisted",
        actor=str(violator.key),
        target=str(victim.key),
        data={"attempt": attempt_index},
        text_template=defeat_aftermath_template(
            "violation_resisted" if player_victim else "violation_resisted_companion"
        ),
    )


def _violation_act_entry(
    violator: Any, victim: Any, attempt_index: int, climax: bool, *, player_victim: bool
) -> EventEntry:
    """One ``violation_act`` entry: the landed attempt and its climax flag."""
    return EventEntry(
        kind="violation_act",
        actor=str(violator.key),
        target=str(victim.key),
        data={"attempt": attempt_index, "climax": climax},
        text_template=defeat_aftermath_template(
            "violation_act" if player_victim else "violation_act_companion"
        ),
    )


def _companion_wake_entry(victim: Any, outcome: ViolationOutcome) -> EventEntry:
    """One ``companion_wake`` entry: the knocked-out companion's observation.

    Observation-only (DA5 D-P4): the companion settles through the core's
    normal survivor path and is not re-floored; the entry reads the outcome
    and carries its counts for the digest phase, mutating nothing.
    """
    return EventEntry(
        kind="companion_wake",
        actor=str(victim.key),
        target=None,
        data={
            "selected": outcome.selected,
            "landed": outcome.landed,
            "resisted": outcome.resisted,
            "climax": outcome.climax_delta,
            "zero_landed": outcome.zero_landed,
        },
        text_template=defeat_aftermath_template("companion_wake"),
    )


def _rewrite_wake_line(entries: list[EventEntry], violated_wake_line: str) -> None:
    """Swap the ``defeat_settle`` wake prose for the violated variant (DA4).

    The replacement copies the entry's data mapping and changes only
    ``wake``, preserving the core contract's remaining fields (finding 7);
    the entry is rebuilt because ``EventEntry`` is frozen.
    """
    for index, entry in enumerate(entries):
        if entry.kind == "defeat_settle":
            entries[index] = replace(
                entry, data={**entry.data, "wake": violated_wake_line}
            )
            return


def _schedule_violation_boundary(
    actor: Any,
    clock: Any,
    attempts: int,
    landed: int,
    resisted: int,
    climaxes: int,
    victims: int,
) -> None:
    """Schedule the violation phase's boundary info event (observability).

    Fires only on the outermost durable commit, like the aftermath's own
    boundary event; the context is snapshotted as primitives so the callback
    carries no live objects. ``victims`` counts the distinct participants
    selected at least once (D-P3's returned outcome set), never the pool
    members no attempt targeted.
    """
    from django.db import transaction

    boundary = {
        "char": str(actor.key),
        "room": str(actor.location.pk) if actor.location is not None else None,
        "tick": clock.tick,
        "attempts": attempts,
        "landed": landed,
        "resisted": resisted,
        "climax": climaxes,
        "victims": victims,
    }
    transaction.on_commit(
        lambda boundary=boundary: log_info(
            "defeat_aftermath_violation", context=boundary
        )
    )


_TARGET_PURPOSE = "target"
# The target draw's victim dimension is a constant marker: the victim is the
# draw's OUTPUT (a participant slot resolved through the pool), never an
# input, so the key space stays (session id, violator, attempt index,
# purpose) exactly as the companion-victims design D-P1 lists it.
_TARGET_POOL_KEY = "pool"


def _violation_pool(
    actor: Any, session: Any, battlefield: Any | None
) -> list[Any]:
    """The violation target pool: the player plus knocked-out companions.

    The pool is every non-fled allied participant (the defeated player plus
    each companion in the knocked-out set; conscious companions are not
    victims). Both resolution paths converge on one canonical order — the
    player first, companions by ascending ``pk`` — so the same durable
    session re-derives identical selection from either a reconstructed
    battlefield or the degraded record-only path. The player is always in
    the pool and always first. One added filter stage (martyrdom vow, design
    §5.8): a valid session martyr stamp collapses the pool to the marked
    non-fled survivor; with no stamp or no eligible martyr the pool is
    returned byte-identically.
    """
    companions: list[Any] = []
    if battlefield is not None:
        player_team = battlefield.team_of(str(actor.key))
        ally_keys = (
            battlefield.teams.get(player_team, set())
            if player_team is not None
            else set()
        )
        for key in ally_keys:
            if key == str(actor.key) or key in battlefield.fled:
                continue
            if key not in battlefield.knocked_out:
                continue
            entity = battlefield.roster.get(key)
            if entity is not None:
                companions.append(entity)
    else:
        from evennia.objects.models import ObjectDB

        for dbref in session.player_ids:
            if dbref == int(actor.pk) or dbref in session.fled_ids:
                continue
            if dbref not in session.knocked_out_ids:
                continue
            entity = ObjectDB.objects.filter(id=dbref).first()
            if entity is not None:
                companions.append(entity)
    companions.sort(key=lambda entity: int(entity.pk))
    pool = [actor, *companions]
    return _martyr_pool_collapse(session, battlefield, pool)


def _session_id_for_member(session: Any, dbref: int) -> str | None:
    """Rebuild the durable session id one participant holds in this session.

    A session id has the shape ``<mode>:<caster pk>:<tick>``; the record's own
    id names the player's session, and every party participant's id in the
    SAME engagement differs only in the pk slot. Rebuilding from the record is
    a pure function of durable record state — never a live clock read — so a
    rolled-back retry re-derives the identical pool, and a stamp from another
    session (different caster pk or tick) can never match a member.
    """
    parts = session.session_id.split(":")
    if len(parts) != 3:
        return None
    mode, _caster_pk, tick = parts
    return f"{mode}:{dbref}:{tick}"


def _martyr_pool_collapse(
    session: Any, battlefield: Any | None, pool: list[Any]
) -> list[Any]:
    """One added filter stage: a valid martyr stamp collapses the pool.

    Edge rules (church design §5.8): the marker died before the wipe (0 HP)
    or fled → no eligible martyr → the normal pool; multiple markers → the
    first by canonical order (the pool's own order: player first, then
    ascending pk); a session-id mismatch (stale stamp) can never fire because
    member ids are rebuilt from THIS session's id. Zero target rolls come
    from the existing single-member short-circuit in the draw selector.
    """
    stamps = session.martyr_key
    if not stamps:
        return pool
    for member in pool:
        member_id = _session_id_for_member(session, int(member.pk))
        if member_id is None or member_id not in stamps:
            continue
        if (
            str(member.key) in getattr(battlefield, "fled", ())
            or int(member.pk) in session.fled_ids
        ):
            # The marker fled: not an eligible survivor, match the next one.
            continue
        if _stored_trait_value(member.traits.hp) <= 0:
            # The marker died before the wipe: never a survivor (kill
            # semantics), so the pool falls through to the next candidate.
            continue
        return [member]
    return pool


def _select_violation_victim(
    pool: list[Any], session_id: str, violator: Any, attempt_index: int
) -> Any:
    """One attempt's victim: a pure derived draw over the pool (D-P1).

    A solo pool short-circuits to the player without touching the dice —
    the pinned player-only baseline stays byte-identical and an
    auto-complying victim still consumes no roll. Otherwise the state-
    derived helper keys on (session id, violator, attempt index,
    purpose="target") and the draw resolves a participant slot, so a
    rolled-back retry re-derives the identical victim. Fled companions are
    filtered out of the pool before the draw and can never be selected.
    """
    if len(pool) == 1:
        return pool[0]
    draw = derived_roll(
        session_id,
        str(violator.pk),
        _TARGET_POOL_KEY,
        attempt_index,
        _TARGET_PURPOSE,
    )
    return pool[draw % len(pool)]



def run_violation_sequence(
    context: ViolationHookContext,
) -> dict[str, ViolationOutcome]:
    """The registered body of the core's guarded hook (DA4 D-V6, DA5 D-P1).

    Runs between the core's ``defeat_settle`` and ``violator_depart`` phases:
    victory arousal -> archetype threshold gate -> the attempt loop (one
    state-derived victim draw and one state-derived resist contest per
    attempt through the shipped pure ``resist_verdict``, declared deltas
    through the shipped pleasure path onto the selected victim's own
    records, symmetric counter credits, one ``defeat_aftermath``-source
    world-clock advance per attempt, first successful resistance ends that
    violator's pursuit) -> the violated wake line when attempts landed on
    the player and one observation-only wake line per selected companion
    victim. A sequence in which zero attempts landed is the PG variant.
    Every die is a pure function of durable record state (D-V4, D-P1), so a
    rolled-back retry re-derives the identical sequence; the sequence
    persists only its state writes, counter credits, EventLog entries, and
    the clock advances themselves.
    """
    actor = context.actor
    session = context.session
    battlefield = context.battlefield
    entries = context.entries
    restores = context.restores
    rulebook = DEFEAT_AFTERMATH_RULEBOOK.violation
    from world.rules.defeat_aftermath.aftermath import _living_foes

    candidates = sorted(
        _living_foes(actor, session, battlefield),
        key=lambda violator: int(violator.pk),
    )
    if not candidates:
        return {}
    pool = _violation_pool(actor, session, battlefield)
    from world.rules.clock import get_world_clock

    clock = get_world_clock()
    scope = _violation_scope(actor)

    # Undo layering: every pool member's sexual surfaces are snapshotted
    # before any write (any companion may be selected); each row-carrying
    # violator joins right before its victory arousal. Reversed-order undo
    # then unwinds the advances before the deltas, converging on the
    # pre-sequence state.
    restores.append(_snapshot_sexual_surfaces(actor))
    for victim in pool[1:]:
        restores.append(_snapshot_sexual_surfaces(victim))
    # Per-participant tallies (D-P3): participant key -> [selected, landed,
    # resisted, climaxes]. Only participants targeted at least once appear.
    tallies: dict[str, list[int]] = {}
    for violator in candidates:
        row = rulebook.rows.get(str(violator.key))
        if row is None:
            # observability: ignore R3: a missing archetype row is the designed PG degradation (design §5), not an error; no exception object exists to chain
            log_warn(
                "defeat_aftermath_violation_archetype_missing",
                context={
                    "archetype": str(violator.key),
                    "tick": clock.tick,
                    "char": str(actor.key),
                },
            )
            continue
        restores.append(_snapshot_sexual_surfaces(violator))
        # Victory arousal (parent design §3.1 step 2): the delta lands on top
        # of whatever the fight raised, clamped by the pleasure gauge.
        apply_pleasure_gain(violator, row.victory_pleasure_delta)
        if violator.sexual.arousal < row.threshold_ordinal:
            continue
        for attempt_index in range(row.attempt_cap):
            victim = _select_violation_victim(
                pool, session.session_id, violator, attempt_index
            )
            tally = tallies.setdefault(str(victim.key), [0, 0, 0, 0])
            tally[0] += 1
            rolls: list[int] = []
            verdict = resist_verdict(
                violator,
                victim,
                rng=_derived_resist_roll(
                    session.session_id, violator, str(victim.pk), attempt_index, rolls
                ),
            )
            player_victim = victim is actor
            entries.append(
                _violation_attempt_entry(
                    violator,
                    victim,
                    attempt_index,
                    verdict,
                    rolls,
                    player_victim=player_victim,
                )
            )
            if verdict.resisted:
                tally[2] += 1
                _apply_violation_deltas(victim, violator, row.resisted)
                entries.append(
                    _violation_resisted_entry(
                        violator,
                        victim,
                        attempt_index,
                        player_victim=player_victim,
                    )
                )
                _advance_attempt_clock(
                    clock, row.attempt_duration_seconds, scope, restores
                )
                # D-V5: the first successful resistance cancels this
                # violator's remaining attempts; the shrunk deltas and the
                # spent duration of the resisted attempt are its last.
                break
            tally[1] += 1
            climax = _victim_climax_onset(victim, violator, row.landed)
            tally[3] += int(climax)
            _credit_violation_counters(victim, violator, row.credited_counters)
            entries.append(
                _violation_act_entry(
                    violator,
                    victim,
                    attempt_index,
                    climax,
                    player_victim=player_victim,
                )
            )
            _advance_attempt_clock(
                clock, row.attempt_duration_seconds, scope, restores
            )
    outcomes = {
        key: ViolationOutcome(
            participant=key,
            selected=tally[0],
            landed=tally[1],
            resisted=tally[2],
            climax_delta=tally[3],
            zero_landed=tally[1] == 0,
        )
        for key, tally in tallies.items()
    }
    # The player's wake prose keys on the player's own landed attempts: a
    # sequence that only landed on companions leaves the PG wake line.
    player_outcome = outcomes.get(str(actor.key))
    if player_outcome is not None and not player_outcome.zero_landed:
        _rewrite_wake_line(entries, rulebook.violated_wake_line)
    for victim in pool[1:]:
        outcome = outcomes.get(str(victim.key))
        if outcome is not None:
            entries.append(_companion_wake_entry(victim, outcome))
    if not outcomes:
        return {}
    _schedule_violation_boundary(
        actor,
        clock,
        sum(outcome.selected for outcome in outcomes.values()),
        sum(outcome.landed for outcome in outcomes.values()),
        sum(outcome.resisted for outcome in outcomes.values()),
        sum(outcome.climax_delta for outcome in outcomes.values()),
        len(outcomes),
    )
    return outcomes
