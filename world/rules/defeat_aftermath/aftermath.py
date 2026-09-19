"""The defeat-aftermath writer: phases, departure, undo.

The deterministic core writer runs inside ``settle_session``'s
``transaction.atomic()``; see the package docstring for the full
rollback and departure contracts.

Part of the :mod:`world.rules.defeat_aftermath` package split; the package
re-exports the historical public surface.
"""
import math
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from world.observability import log_error, log_info, log_warn
from world.rules.action import (
    _attribute_snapshot,
    _restore_attribute,
    _stored_trait_value,
)
from world.rules.buffs import apply_buff
from world.rules.clock import (
    AdvanceSource,
    _restore_advance_registry,
    _restore_clock_tick,
    _snapshot_clock_tick,
    build_advance_snapshot_registry,
)
from world.rules.defeat_aftermath.contracts import (
    DefeatAftermathResult,
    DigestOutcome,
    ViolationHookContext,
    WakeObservation,
)
from world.rules.defeat_aftermath.digest import _run_digest_phase
from world.rules.defeat_aftermath.rulebook import DEFEAT_AFTERMATH_RULEBOOK
from world.rules.defeat_aftermath.violation import _call_violation_hook
from world.rules.event_log import EventEntry, EventLog
from world.rules.player_messages import defeat_aftermath_template


_PENDING_OUTER_UNDOS: list[Callable[[], None]] = []


def register_pending_undo(undo: Callable[[], None]) -> None:
    """Arm the aftermath undo for a later outer-transaction rollback.

    A defeat settled inside a nested round transaction (the ordinary
    submission path) can still be rolled back by the enclosing transaction
    AFTER ``settle_session`` returned, and Django has no rollback hook. The
    round wrapper drains and runs the armed undo on its failure boundary and
    discards it on success; ``undo`` is idempotent.
    """
    _PENDING_OUTER_UNDOS.append(undo)


def drain_pending_undos() -> list[Callable[[], None]]:
    """Return and clear every armed undo (run them, or discard on commit)."""
    pending = list(_PENDING_OUTER_UNDOS)
    _PENDING_OUTER_UNDOS.clear()
    return pending


def solve_recovery_seconds(
    current: float,
    carried: float,
    rate: float,
    scale: float,
    target: int,
    cap: int,
) -> tuple[int, bool]:
    """Solve the minimum whole seconds of scaled regen to reach ``target``.

    Pure settlement math over the stored gauge-regen model (D-R1/D-R2): the
    virtual scaled model is ``floor(current + carried + rate * scale * t)``,
    the exact float arithmetic ``_settle_gauge_regen`` uses. Returns
    ``(seconds, capped)``. ``t = 0`` when the stored state is already at or
    above the target. A non-positive scaled rate, or a solve whose minimum
    ``t`` exceeds ``cap`` (the closed form normalizes against the float
    model first), returns ``(cap, True)`` — the caller settles at the HP the
    capped virtual model produces and reports loudly (D-R3).
    """
    headroom = target - (current + carried)
    if headroom <= 0:
        return 0, False
    scaled_rate = rate * scale
    if scaled_rate <= 0:
        return cap, True
    seconds = min(max(math.ceil(headroom / scaled_rate), 0), cap)
    # Normalize the closed form against the clock's exact float model: the
    # guards move at most one step for floating-point boundary error.
    while seconds < cap and math.floor(current + carried + scaled_rate * seconds) < target:
        seconds += 1
    while seconds > 0 and math.floor(current + carried + scaled_rate * (seconds - 1)) >= target:
        seconds -= 1
    reached = math.floor(current + carried + scaled_rate * seconds) >= target
    return seconds, not reached


def _recovery_scope(actor: Any, battlefield: Any | None) -> list[Any]:
    """The recovery advance's entity scope: the actor's living allies.

    Mirror of the combat settlement's scope filter restricted to the actor's
    own team: living, non-fled teammates regen for the window exactly like
    any other clock advance (design D-R1), while foes — including a retained
    quest-bound winner and violators already logically departed — are never
    in scope, so the recovery window cannot mutate an opponent's gauges
    (rubber-duck plan review finding 4).
    """
    if battlefield is None:
        return [actor] if _stored_trait_value(actor.traits.hp) > 0 else []
    team = battlefield.team_of(str(actor.key))
    allies = battlefield.teams.get(team, set()) if team is not None else {str(actor.key)}
    return [
        battlefield.roster[key]
        for key in allies
        if key not in battlefield.fled
        and _stored_trait_value(battlefield.roster[key].traits.hp) > 0
    ]



def run_defeat_aftermath(
    actor: Any,
    session: Any,
    battlefield: Any | None,
) -> DefeatAftermathResult:
    """Apply the deterministic defeat aftermath inside the caller's transaction.

    Phase order (tasks 1.2): HP floor + knockout mark -> guarded violation
    hook -> violator departure -> weak debuff -> recovery advance ->
    digest -> EventLog. The caller persists
    the returned session record and clears the session afterwards. Every die
    the writer and its registered violation body use is a pure function of
    durable record state, so a rolled-back retry re-derives the identical
    aftermath (design D-C5, DA4 D-V4). Returns a :class:`DefeatAftermathResult`: the
    knockout-marked session record, the aftermath EventLog the caller
    appends to the settlement result, and an idempotent callable that undoes
    every in-process surface the writer touched. The caller MUST run
    ``undo`` on its own failure boundary before the exception propagates:
    the transaction restores the database rows, but the idmapper cache is
    not transaction-aware, and a failure after this writer returns (the
    marker persist, the session clear) must still leave no half-applied
    aftermath (design D-C5).
    """
    hp_before = _stored_trait_value(actor.traits.hp)
    trait_snapshot = _attribute_snapshot(actor, "traits", "traits")
    buff_snapshot = _attribute_snapshot(actor, "buffs")
    sexual_traits_snapshot = _attribute_snapshot(actor, "sexual_traits", "traits")
    sexual_state_snapshot = {
        key: _attribute_snapshot(actor, key, "sexual_state")
        for key in (
            "virgin",
            "experience_types",
            "climax_turns",
            "pending_climax_extension",
        )
    }
    knocked_out_before = (
        str(actor.key) in battlefield.knocked_out
        if battlefield is not None
        else False
    )
    restores: list[Callable[[], None]] = []
    entries: list[EventEntry] = []
    departed: list[Any] = []
    recovery_seconds = 0
    hp_wake = 1

    def undo() -> None:
        """Undo every in-process aftermath surface; idempotent on re-run."""
        for restore in reversed(restores):
            try:
                restore()
            except Exception as error:
                log_warn(
                    "defeat_aftermath_undo_restore_failed",
                    exc=error,
                    context={"char": str(actor.key)},
                )
        _restore_aftermath_surfaces(
            actor,
            battlefield,
            hp_before,
            trait_snapshot,
            buff_snapshot,
            sexual_traits_snapshot,
            sexual_state_snapshot,
            knocked_out_before,
        )

    try:
        # Phase 1: the nonlethal floor (design D-C1). Unconditional on every
        # hostile defeat: a defeated or surrendered player is never persisted
        # at 0 HP, and the floor is the declared writer-owned write.
        actor.traits.hp.current = 1
        if battlefield is not None:
            battlefield.knocked_out.add(str(actor.key))
        if int(actor.pk) not in session.knocked_out_ids:
            session = replace(
                session,
                knocked_out_ids=(*session.knocked_out_ids, int(actor.pk)),
            )
        entries.append(
            EventEntry(
                kind="defeat_settle",
                actor=str(actor.key),
                target=None,
                data={
                    "wake": DEFEAT_AFTERMATH_RULEBOOK.pg_lines[0],
                    "hp_after": 1,
                },
                text_template=defeat_aftermath_template("defeat_settle"),
            )
        )
        # Phase 2: the guarded violation hook point (design D-C4). No core
        # on-branch; the body is contributed by the adult changes and its
        # entries splice between defeat_settle and violator_depart.
        violation = _call_violation_hook(
            ViolationHookContext(
                actor=actor,
                session=session,
                battlefield=battlefield,
                entries=entries,
                restores=restores,
            )
        )
        # Phase 3: violator departure (design D-C3).
        entries.extend(
            _depart_violators(actor, session, battlefield, restores, departed)
        )
        # Phase 4: the weak debuff (design D-C2).
        apply_buff(actor, DEFEAT_AFTERMATH_RULEBOOK.weak_debuff_buff_key)
        entries.append(
            EventEntry(
                kind="weak_granted",
                actor=str(actor.key),
                target=None,
                data={"buff": DEFEAT_AFTERMATH_RULEBOOK.weak_debuff_buff_key},
                text_template=defeat_aftermath_template("weak_granted"),
            )
        )
        # Phase 5: the recovery advance (defeat-aftermath-recovery D-R1/D-R2).
        # One world-clock advance priced by the virtual scaled-rate solve,
        # then the player's wake value is pinned: clamped down to exactly the
        # target when the real un-scaled advance overshot, or written to the
        # capped virtual-model value when the target was unreachable. Both
        # writes are declared aftermath writes (design D-R2).
        gauge = actor.traits.hp
        target = math.ceil(float(gauge.max) * DEFEAT_AFTERMATH_RULEBOOK.recovery.wake_fraction)
        solve_current = _stored_trait_value(gauge)
        solve_carried = float(getattr(gauge, "regen_remainder", 0.0) or 0.0)
        solve_rate = float(getattr(gauge, "rate", 0) or 0)
        seconds, capped = solve_recovery_seconds(
            solve_current,
            solve_carried,
            solve_rate,
            DEFEAT_AFTERMATH_RULEBOOK.recovery.regen_scale,
            target,
            DEFEAT_AFTERMATH_RULEBOOK.recovery.max_recovery_seconds,
        )
        if seconds > 0:
            # Local import: the test suite patches world.rules.clock's
            # binding, so the clock lookup must resolve at call time.
            from world.rules.clock import get_world_clock

            clock = get_world_clock()
            scope = _recovery_scope(actor, battlefield)
            registry = build_advance_snapshot_registry(
                clock, seconds, AdvanceSource.DEFEAT_AFTERMATH, scope
            )
            tick_snapshot = _snapshot_clock_tick(clock)
            clock.advance(seconds, AdvanceSource.DEFEAT_AFTERMATH, scope)
            def _restore_recovery(
                clock=clock, registry=registry, tick=tick_snapshot, scope=tuple(scope)
            ):
                _restore_clock_tick(clock, tick)
                _restore_advance_registry(registry, scope)
            restores.append(
                _restore_recovery
            )
            wake = _stored_trait_value(gauge)
            if not capped and wake > target:
                gauge.current = target
            elif capped:
                # Settle the stored gauge at the virtual capped state:
                # current AND carried remainder, mirroring
                # ``_settle_gauge_regen``'s storage (final duck finding 1) —
                # keeping the real un-scaled remainder would let a later
                # advance regenerate earlier than the capped model permits.
                continuous = (
                    solve_current
                    + solve_carried
                    + solve_rate * DEFEAT_AFTERMATH_RULEBOOK.recovery.regen_scale * seconds
                )
                maximum = float(gauge.max)
                if continuous >= maximum:
                    gauge.current = round(maximum)
                    gauge.regen_remainder = 0.0
                else:
                    whole = math.floor(continuous)
                    gauge.current = whole
                    gauge.regen_remainder = continuous - whole
            wake = _stored_trait_value(gauge)
            recovery_seconds = seconds
            hp_wake = int(wake)
            entries.append(
                EventEntry(
                    kind="recovery_advance",
                    actor=str(actor.key),
                    target=None,
                    data={"seconds": seconds, "hp_wake": int(wake)},
                    text_template=defeat_aftermath_template("recovery_advance"),
                )
            )
            if capped:
                # observability: ignore R3: the cap hit is a designed bounded outcome (D-R3), not a failure; no exception object exists to chain
                log_error(
                    "defeat_aftermath_recovery_capped",
                    context={
                        "char": str(actor.key),
                        "tick": clock.tick,
                        "target": target,
                        "capped": True,
                    },
                )
        else:
            hp_wake = int(_stored_trait_value(gauge))
        # Phase 6: the digest (defeat-aftermath-digest-narrative D-D6). The
        # body wakes at its settled HP first; the digest then reads what it
        # remembers. Gated on the violation handoff: with no sequence there
        # is nothing to digest and no bystander observing a violation.
        digests: tuple[DigestOutcome, ...] = ()
        wake_observations: tuple[WakeObservation, ...] = ()
        if violation:
            digests, wake_observations = _run_digest_phase(
                actor, session, battlefield, entries, restores, violation
            )
    except Exception:
        undo()
        raise
    _schedule_boundary_event(actor, recovery_seconds, hp_wake)
    return DefeatAftermathResult(
        session=session,
        logs=(
            EventLog(
                actor=str(actor.key),
                skill_key="defeat_aftermath",
                targets=(),
                entries=tuple(entries),
                time_cost_seconds=0,
            ),
        ),
        undo=undo,
        departed=tuple(departed),
        violation=violation,
        digests=digests,
        wake_observations=wake_observations,
    )


def _living_foes(actor: Any, session: Any, battlefield: Any | None) -> list[Any]:
    """Return the living, non-fled foe-team members of the settled session.

    The battlefield roster is preferred; the degraded recovery path (no
    reconstructible battlefield) resolves the durable record's enemy dbrefs
    instead, discarding missing, fled, or dead objects, so a recovered defeat
    still departs its resolvable population winner (review D4).
    """
    if battlefield is not None:
        player_team = battlefield.team_of(str(actor.key))
        foe_team = next(
            team for team in battlefield.teams if team != player_team
        )
        return [
            entity
            for key in battlefield.teams[foe_team]
            if key in battlefield.roster
            and key not in battlefield.fled
            and _stored_trait_value(battlefield.roster[key].traits.hp) > 0
            for entity in (battlefield.roster[key],)
        ]
    from evennia.objects.models import ObjectDB

    foes: list[Any] = []
    for enemy_id in session.enemy_ids:
        if enemy_id in session.fled_ids:
            continue
        entity = ObjectDB.objects.filter(id=enemy_id).first()
        if entity is None or _stored_trait_value(entity.traits.hp) <= 0:
            continue
        foes.append(entity)
    return foes


def _depart_violators(
    actor: Any,
    session: Any,
    battlefield: Any | None,
    restores: list[Callable[[], None]],
    departed: list[Any],
) -> list[EventEntry]:
    """Depart every living winning violator (design D-C3).

    Quest-bound monsters (pk in the settling player's persisted quest
    records' ``objective_target_ids``) are never removed: quest retention
    outranks the population marker, and removing an extermination target
    would be disguised record loss. Marker-carrying population monsters
    departure through the population service's public primitive; foreign
    monsters stay untouched. One ``violator_depart`` entry is recorded per
    departure; the physical deletion of the departed runs post-commit via
    :func:`finalize_departure`.
    """
    from world.quests.runtime import read_records

    quest_bound = {
        target_id
        for record in read_records(actor)
        for target_id in record.objective_target_ids
    }
    entries: list[EventEntry] = []
    for violator in _living_foes(actor, session, battlefield):
        if int(violator.pk) in quest_bound:
            continue
        if not violator.db.population_key:
            continue
        from world.maps.wilderness_population import depart_population_monster

        wilderness = getattr(
            getattr(violator, "location", None), "wilderness", None
        )
        if wilderness is None:
            log_warn(
                "defeat_aftermath_despawn_without_wilderness",
                context={"monster": str(violator), "char": str(actor.key)},
            )
            continue
        ticket = depart_population_monster(wilderness, violator)
        restores.append(ticket.revert)
        departed.append(ticket)
        entries.append(
            EventEntry(
                kind="violator_depart",
                actor=str(violator.key),
                target=str(actor.key),
                data={"mode": "population"},
                text_template=defeat_aftermath_template("violator_depart"),
            )
        )
    return entries


def finalize_departure(actor: Any, tickets: tuple[Any, ...]) -> None:
    """Delete the departed violators after the OUTERMOST transaction committed.

    Scheduled through ``transaction.on_commit`` from inside the settlement
    transaction, so the physical deletion runs only after the durable commit
    and a rolled-back outer round discards it. Best effort with deterministic
    recovery: a failed delete reverts the logical departure (marker and
    bookkeeping restored, the monster stays a normal reconcilable population
    monster) and logs at error level; only a process crash in the post-commit
    window leaves a marker-less live monster — the accepted restart-refresh
    risk the parent design already carries.
    """
    for ticket in tickets:
        try:
            ticket.monster.delete()
        except Exception as error:
            try:
                ticket.revert()
            except Exception as revert_error:
                log_error(
                    "defeat_aftermath_depart_revert_failed",
                    exc=revert_error,
                    context={
                        "char": str(actor.key),
                        "monster": str(ticket.monster),
                    },
                )
            log_error(
                "defeat_aftermath_depart_delete_failed",
                exc=error,
                context={"char": str(actor.key), "monster": str(ticket.monster)},
            )


def _restore_aftermath_surfaces(
    actor: Any,
    battlefield: Any | None,
    hp_before: float,
    trait_snapshot: tuple[bool, Any],
    buff_snapshot: tuple[bool, Any],
    sexual_traits_snapshot: tuple[bool, Any],
    sexual_state_snapshot: dict[str, tuple[bool, Any]],
    knocked_out_before: bool,
) -> None:
    """Undo every in-process surface the writer touched after a rollback.

    The database rows restore through the transaction; the idmapper cache is
    not transaction-aware, so each surface is put back explicitly before the
    exception propagates (design D-C5).
    """
    _restore_attribute(actor, "buffs", buff_snapshot)
    _restore_attribute(actor, "traits", trait_snapshot, category="traits")
    _restore_attribute(actor, "sexual_traits", sexual_traits_snapshot, category="traits")
    for key, snap in sexual_state_snapshot.items():
        _restore_attribute(actor, key, snap, category="sexual_state")
    # The trait handler caches its data dict; rebind it to the restored
    # attribute and drop the per-trait cache (same reset as _restore_entity_state).
    actor.traits.trait_data = actor.attributes.get(
        "traits", default={}, category="traits"
    )
    actor.traits._cache.clear()
    actor.__dict__.pop("sexual", None)
    if battlefield is not None and not knocked_out_before:
        battlefield.knocked_out.discard(str(actor.key))


def _schedule_boundary_event(actor: Any, seconds: int, hp_wake: int) -> None:
    """Schedule the ``defeat_aftermath`` boundary info event (design D-C6).

    Fires only on the outermost durable commit, like ``settlement_done``; the
    context is snapshotted as primitives so the callback carries no live
    objects. The recovery phase widens the context with ``seconds`` and
    ``hp_wake`` (defeat-aftermath-recovery D-R5).
    """
    from django.db import transaction

    from world.rules.clock import get_world_clock

    boundary = {
        "char": str(actor.key),
        "room": str(actor.location.pk) if actor.location is not None else None,
        "tick": get_world_clock().tick,
        "hp_after": _stored_trait_value(actor.traits.hp),
        "seconds": seconds,
        "hp_wake": hp_wake,
    }
    transaction.on_commit(
        lambda boundary=boundary: log_info("defeat_aftermath", context=boundary)
    )
