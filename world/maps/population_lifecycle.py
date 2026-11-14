"""Merged chronological population lifecycle coordinator.

The regional population owner (``world.maps.regional_population``) owns the
durable zone state, the presence timeline and the deterministic wave commit;
the site owner (``world.maps.monster_sites``) owns each authored site's
lifecycle. Neither decides *when* a boundary happens: this coordinator is the
one place that merges the interval-start site initialization, the pending
presence transitions, the site clear/recover boundaries and the regional
recovery due times into a single chronological queue inside the existing
player-driven clock stage.

Ordering contract at every selected boundary tick:

1. Establish or cancel each zone's recovery episode from the projected counts.
2. Settle the site owner's clear/create/recover decisions in stable site-key
   order, so same-tick explicit site births precede ordinary regional births.
3. Recompute and settle each due regional recovery in zone-key order.
4. Consume the applied facts and record progress.

An interval is stopped at ``end_tick``, and a repeated interval never reapplies
a settled boundary because consumed transitions and passed protection intervals
are retired by the owner. The pure boundary query shares this planning and
consumes no sequence, draw or durable state, so an interruptible skip can stop
before the earliest relevant boundary.

Registration installs this coordinator under the existing
``monster_site_lifecycle`` stage kind, replacing the former site-only interval
callback. There is no second whole-interval regional stage; production zone
initialization remains an explicit owner operation.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import nullcontext
from typing import Any

from django.db import transaction

from world.maps import (
    monster_activity,
    monster_sites,
    population_units,
    regional_population,
)
from world.observability import log_info
from world.observability.tally import maintenance_tally, suspended_maintenance_tally
from world.rules.clock import (
    ScheduledEvent,
    SurfaceSnapshot,
    advance_registry_held,
    held_advance_registry,
    register_event_source,
    restore_advance_registry,
)
from world.rules.surfaces import (
    deferred_attribute_stores,
    flushed_attribute_stores,
    outer_rollback_owner,
    suspended_outer_rollback,
)

#: The existing stage kind this coordinator installs itself under.
STAGE_KIND = monster_sites.SITE_STAGE_KIND


def _wilderness() -> Any | None:
    return regional_population.live_wilderness()


def _zone_keys(wilderness: Any) -> tuple[str, ...]:
    """Every initialized zone, in deterministic key order."""
    return regional_population.initialized_zone_keys(wilderness)


def _note_boundary(
    wilderness: Any,
    zone_keys: tuple[str, ...],
    tick: int,
    *,
    noted: tuple[Any, ...] | None = None,
) -> tuple[Any, ...]:
    """Note this boundary unless ``noted`` proves the measure cannot differ.

    The same presence and the same tick always yield the same episode answer,
    and measuring the whole population is the costly part of a quiet boundary.
    """
    current = regional_population.presence_fingerprint(wilderness)
    if current != noted:
        regional_population.note_population_boundaries(
            wilderness, zone_keys, tick=tick
        )
    return current


def _settle_population_at(
    wilderness: Any,
    tick: int,
    *,
    contact_tick: int | None = None,
    scope: Any | None = None,
    first_tick: bool = False,
    cursors: Any | None = None,
) -> list[ScheduledEvent]:
    """Apply every category of boundary at one already selected tick.

    ``contact_tick`` names the advance's accepted endpoint. Authored contact is
    admitted only there (never at an interior tick whose physiology was
    already settled to a later endpoint) and always after the same tick's
    lawful arrivals and births but before its idle departures.

    ``scope`` settles that scope's groups, journeys, zones and sites only. A unit
    that has already passed this tick gets no zone note, no recovery and no site
    step here; its groups are still visited and skip themselves through their own
    cursors. ``first_tick`` marks the pass's interval start, which a whole-world
    pass always settles: a unit whose cursor is that start has not settled it
    yet, so its zone and site steps run there too.

    The authored field contact is a whole-world write (it contacts whoever stands
    near the present party) and stays with the whole-world pass; a scoped pass
    never runs it.
    """
    step = None if scope is None else scope.behind(tick, inclusive=first_tick)
    zone_keys = _zone_keys(wilderness) if step is None else step.zone_keys
    # 1. Lawful completed arrivals and protected-arrival retries first, so a
    # present arrival consumes the headroom it actually occupies at this tick.
    events = list(
        monster_activity.settle_monster_activity_at(wilderness, tick, scope=scope)
    )
    noted = _note_boundary(wilderness, zone_keys, tick)
    # 2. Explicit site births, then 3. ordinary regional births.
    events.extend(monster_sites.settle_monster_sites_at(tick, scope=step))
    # Same-tick explicit site births restore local density: cancel or refresh
    # each episode from the post-site counts before any regional wave is
    # considered, so a restored episode never survives into a later due time.
    noted = _note_boundary(wilderness, zone_keys, tick, noted=noted)
    for zone_key in regional_population.due_recovery_zone_keys(
        wilderness, tick=tick, scope=step
    ):
        events.extend(
            regional_population.settle_recovery_due(
                wilderness, zone_key, tick=tick
            )
        )
    # 4. Authored field contact at the accepted endpoint: completed lawful
    # arrivals and site/regional births precede it, and it precedes idle
    # departures so a wandering departure can never avoid the encounter it
    # belongs to. The source persists the session only; the owning rules
    # action drains the predecessor continuation after the advance returned.
    if contact_tick is not None and scope is None and int(tick) == int(contact_tick):
        from world.rules.field_contact import settle_population_contact_at

        # A failed contact restores its participants before the failure reaches
        # the caller. The block may change liveness, ownership markers and
        # physiology, so no read of the pass's earlier facts may answer across
        # it. It suspends the pass's rollback owner: work it recovers from must
        # roll back to its own savepoint, because the pass is not going to.
        regional_population.forget_living_presence()
        with (
            flushed_attribute_stores(),
            monster_activity.unbatched_state_writes(),
            suspended_maintenance_tally(),
            suspended_outer_rollback(),
        ):
            events.extend(
                settle_population_contact_at(wilderness, tick, int(contact_tick))
            )
        regional_population.forget_living_presence()
    # 5. Idle departures last: a contact cannot be avoided by iterating a
    # wandering departure before the encounter it belongs to.
    events.extend(
        monster_activity.settle_group_decisions_at(wilderness, tick, scope=scope)
    )
    # A zero-duration committed departure arrives at this same tick. It is
    # settled here rather than scheduling an unreachable same-tick boundary;
    # the owner advances no clock and no second scheduler exists.
    events.extend(
        monster_activity.settle_monster_activity_at(wilderness, tick, scope=scope)
    )
    # A departure can itself open a recovery deficit at this tick. Establish or
    # cancel each episode from the post-departure counts without another birth.
    _note_boundary(wilderness, zone_keys, tick, noted=noted)
    regional_population.settle_timeline_through(
        wilderness,
        tick,
        retain=monster_sites.retained_loss_ids(wilderness, scope=step),
        scope=step,
        cursors=cursors,
    )
    return events


def _next_population_boundary(
    wilderness: Any, tick: int, end_tick: int, scope: Any | None = None
) -> int | None:
    """The earliest merged boundary strictly after ``tick`` up to ``end_tick``.

    ``scope`` keeps only the boundaries that scope's units can act on: a
    transition one of its units concerns, a protection interval over one of its
    cells, a site of one of its units, or a zone of one of its units that has not
    already passed the candidate tick.
    """
    index = None if scope is None else population_units.current_unit_index()
    timeline = regional_population.read_population_timeline(wilderness)
    candidates = [
        transition.occurred_tick
        for transition in timeline.transitions
        if tick < transition.occurred_tick <= end_tick
        and (
            scope is None
            or population_units.concerned_units(index, transition) & scope.units
        )
    ]
    # The interval endpoint keeps a site of a unit that is ahead of ``tick``
    # inside the query: that unit still owes every step after its own cursor, and
    # its site boundary is the only tick at which the pass can reach it.
    site_boundary = monster_sites.next_site_boundary(
        tick,
        end_tick,
        scope=None if scope is None else scope.behind(end_tick + 1),
    )
    if site_boundary is not None:
        candidates.append(site_boundary)
    journey_boundary = monster_activity.next_monster_activity_boundary(
        wilderness, tick, end_tick, scope=scope
    )
    if journey_boundary is not None:
        candidates.append(journey_boundary)
    # A birth route deferred by encounter protection retries on the first
    # unprotected tick, so protection end is a real merged boundary.
    for protection in timeline.protection:
        if protection.end_tick is None:
            continue
        resumed = protection.end_tick + 1
        if tick < resumed <= end_tick and (
            scope is None or scope.covers_cell((protection.cell.x, protection.cell.y))
        ):
            candidates.append(resumed)
    for state in regional_population.zone_states(wilderness).values():
        due = state.recovery_due_tick
        if (
            due is not None
            and tick < due <= end_tick
            and (scope is None or scope.zone_in_step(state.zone_key, due))
        ):
            candidates.append(due)
    return min(candidates) if candidates else None


def _run_pass(
    wilderness: Any,
    scope: Any | None,
    start_tick: int,
    end_tick: int,
    *,
    contact: bool,
    cursors: Any | None = None,
) -> list[ScheduledEvent]:
    """Run one settlement pass over ``[start_tick, end_tick]`` for ``scope``.

    ``scope=None`` is the whole-world pass. A scoped pass settles only that
    scope's groups, journeys, zones and sites and advances only its units'
    cursors; every other unit's records and individuals are left untouched.
    The whole body runs marked as a settlement pass, so a catch-up entry point
    reached from inside it never starts a nested catch-up.
    """
    with population_units.running_pass():
        # A world without a usable per-unit record must refuse before any
        # settlement work, not after it: a direct caller outside a clock advance
        # owns its own commit, so a tail-only check would leave settled state
        # behind a raised advance. The record is read once per pass -- the scoped
        # entry point hands over the one `build_scope` already read -- and handed
        # to every boundary, because it cannot change before the pass advances
        # it.
        if cursors is None:
            cursors = population_units.read_unit_cursors(wilderness)
        contact_tick = end_tick if contact else None
        events: list[ScheduledEvent] = []
        tick = start_tick
        with maintenance_tally() as counts:
            with (
                outer_rollback_owner() if advance_registry_held() else nullcontext(),
                (
                    deferred_attribute_stores()
                    if advance_registry_held()
                    else nullcontext()
                ),
                monster_activity.batched_state_writes(wilderness),
                regional_population.reused_living_presence(),
                population_units.scoped(scope),
            ):
                while tick <= end_tick:
                    events.extend(
                        _settle_population_at(
                            wilderness,
                            tick,
                            contact_tick=contact_tick,
                            scope=scope,
                            first_tick=tick == start_tick,
                            cursors=cursors,
                        )
                    )
                    following = _next_population_boundary(
                        wilderness, tick, end_tick, scope
                    )
                    if following is None or following <= tick:
                        break
                    tick = following
                # Progress is the interval endpoint whether or not a boundary fell
                # there: equal elapsed time must leave equal settlement progress and
                # equal protection retirement.
                monster_activity.settle_idle_physiology(
                    wilderness, end_tick, scope=scope
                )
                regional_population.settle_timeline_through(
                    wilderness,
                    end_tick,
                    retain=monster_sites.retained_loss_ids(wilderness, scope=scope),
                    scope=scope,
                    cursors=cursors,
                )
                monster_activity.retire_room_protection(
                    wilderness, end_tick, scope=scope
                )
                monster_activity.retire_settled_decision_receipts(
                    wilderness, end_tick, scope=scope
                )
                # The pass endpoint is the scope's progress: a whole-world pass
                # raises every unit, a scoped pass only its own.
                population_units.advance_unit_cursors(
                    wilderness, None if scope is None else scope.units, end_tick
                )
            if counts:
                context = {
                    "tick_from": int(start_tick),
                    "tick_to": int(end_tick),
                    **dict(sorted(counts.items())),
                }
                transaction.on_commit(
                    lambda context=context: log_info(
                        "population_maintenance_settled", context=context
                    )
                )
        return events


def settle_population_lifecycle(
    start_tick: int, end_tick: int
) -> list[ScheduledEvent]:
    """Settle every population boundary in ``[start_tick, end_tick]`` in order.

    A world with no wilderness script or no explicitly initialized population
    seed has no population lifecycle to run and settles nothing. This is the
    whole-world pass, and it remains the clock stage.
    """
    wilderness = _wilderness()
    if wilderness is None or not regional_population.population_provisioned(wilderness):
        return []
    return _run_pass(wilderness, None, start_tick, end_tick, contact=True)


def settle_population_scope(
    wilderness: Any, seeds: Iterable[str], end_tick: int, *, contact: bool = False
) -> list[ScheduledEvent]:
    """Settle the closed set of units around ``seeds`` from its cursor to ``end_tick``.

    The set is the closure of the seeded units over every group that touches two,
    so one settlement never reads state another unit owns. The pass starts at the
    set's lowest cursor and advances only its units' cursors. A pass over an
    interval that ended before the set's cursor does nothing; an interval that
    starts and ends at it settles that tick, exactly like a whole-world pass.

    The authored field contact is a whole-world write (it contacts whoever
    stands near the present party), so a scoped pass refuses it by name rather
    than accepting a flag it cannot honour. One interval must not leave a
    contact boundary unsettled behind an advanced cursor.
    """
    if wilderness is None or not regional_population.population_provisioned(wilderness):
        return []
    if contact:
        raise ValueError(
            "a scoped settlement pass cannot run the authored field contact"
        )
    cursors = population_units.read_unit_cursors(wilderness)
    scope = population_units.build_scope(wilderness, seeds, cursors=cursors)
    if not scope.units:
        return []
    start_tick = population_units.scope_start_tick(wilderness, scope)
    if end_tick < start_tick:
        return []
    return _run_pass(
        wilderness,
        scope,
        start_tick,
        end_tick,
        contact=False,
        cursors=cursors,
    )


def ensure_population_current(wilderness: Any, seeds: Iterable[str]) -> bool:
    """Catch the closed set around ``seeds`` up to the current tick.

    Returns ``True`` when it settled anything. A world with no wilderness or no
    population, a catch-up reached from inside a settlement pass, an empty seed
    set and a set that is already current all settle nothing and return
    ``False``.

    The set is settled in its own transaction with the same rollback strength
    as a clock advance: the pre-catch-up surface registry is built first and
    restores every surface the pass writes when anything fails.
    """
    if wilderness is None or not regional_population.population_provisioned(
        wilderness
    ):
        return False
    if population_units.pass_running():
        return False
    # One cursor read answers the common case: a world whose whole record has
    # settled through ``now`` has no unit left to settle, so the closed set is
    # never resolved (the second read a clock advance's merge point relies on).
    cursors = population_units.read_unit_cursors(wilderness)
    now = regional_population.current_population_tick()
    if population_units.all_units_current(cursors, now):
        return False
    scope = population_units.build_scope(wilderness, seeds, cursors=cursors)
    if not scope.units:
        return False
    start = population_units.scope_start_tick(wilderness, scope)
    if start >= now:
        return False
    if _refuse_nested_catch_up():
        from django.db import transaction as _transaction

        connection = _transaction.get_connection()
        if connection.in_atomic_block:
            raise population_units.PopulationCatchUpNested(
                f"{population_units.POPULATION_CATCH_UP_NESTED}: a catch-up that "
                f"would settle {sorted(scope.units)} from {start} to {now} was "
                "reached inside an enclosing transaction"
            )
    # Nothing writes between the scope build above and the pass's own scope
    # build, so both derive the same closed set and the same start tick.
    registry = snapshot_population_lifecycle_surfaces(start, now)
    try:
        with held_advance_registry(), transaction.atomic():
            settle_population_scope(wilderness, scope.units, now, contact=False)
            transaction.on_commit(
                lambda: log_info(
                    "population_caught_up",
                    context={
                        "units": len(scope.units),
                        "tick_from": start,
                        "tick_to": now,
                    },
                )
            )
    except Exception:
        restore_advance_registry(registry, (wilderness,))
        raise
    return True


def _refuse_nested_catch_up() -> bool:
    """Whether a writing catch-up refuses an enclosing transaction.

    Fail closed in production. The test harness wraps every case in one outer
    atomic block that no game owner opened, so the test settings disable the
    refusal and the refusal's own test re-enables it explicitly.
    """
    from django.conf import settings

    return bool(getattr(settings, "POPULATION_CATCH_UP_REFUSES_NESTED", True))


def ensure_locations_current(locations: Iterable[Any]) -> bool:
    """Catch up every unit within the observation radius of ``locations``."""
    wilderness = regional_population.live_wilderness()
    if wilderness is None or not regional_population.population_provisioned(
        wilderness
    ):
        return False
    if population_units.pass_running():
        return False
    index = population_units.current_unit_index()
    map_name = getattr(wilderness, "db_key", None)
    seeds: set[str] = set()
    for location in locations:
        if location.kind != "room" and location.map != map_name:
            continue
        seeds |= population_units.units_around(index, location)
    return ensure_population_current(wilderness, seeds)


def ensure_observed_population_current() -> bool:
    """Catch up every unit a player observes, or a running action announced."""
    wilderness = regional_population.live_wilderness()
    if wilderness is None or not regional_population.population_provisioned(
        wilderness
    ):
        return False
    if population_units.pass_running():
        return False
    return ensure_population_current(
        wilderness, population_units.observed_units(wilderness)
    )


def next_population_lifecycle_boundary(
    start_tick: int, end_tick: int
) -> int | None:
    """The next interactive authored contact without executing any writer.

    The public query is deliberately narrower than :func:`_next_population_boundary`:
    it answers only ticks at which a present scope party would really be
    contacted, using the read-only chronological projection
    (:mod:`world.maps.population_forecast`) that shares this coordinator's
    planners. Distant arrivals, births, recoveries and idle decisions stay
    internal maintenance: the committed settlement still runs every one of
    them, but an interruptible skip is not returned to the player for them.
    """
    from world.maps.population_forecast import (
        capture_activity_snapshot,
        project_activity_window,
    )
    from world.rules.field_contact import forecast_observers

    wilderness = _wilderness()
    if wilderness is None or not regional_population.population_provisioned(wilderness):
        return None
    observers = forecast_observers()
    if not observers:
        return None
    snapshot = capture_activity_snapshot(start_tick=int(start_tick))
    forecast = project_activity_window(
        snapshot,
        start_tick=int(start_tick),
        end_tick=int(end_tick),
        observers=observers,
        wilderness=getattr(wilderness, "db_key", None),
    )
    return forecast.first_tick


def snapshot_population_lifecycle_surfaces(
    start_tick: int, end_tick: int
) -> dict[int, SurfaceSnapshot]:
    """The combined advance-surface contract of both merged owners."""
    merged: dict[int, SurfaceSnapshot] = {}
    for registry in (
        monster_sites.snapshot_monster_site_surfaces(start_tick, end_tick),
        regional_population.snapshot_regional_population_surfaces(
            start_tick, end_tick
        ),
        monster_activity.snapshot_monster_activity_surfaces(start_tick, end_tick),
    ):
        for object_id, surface in registry.items():
            existing = merged.get(object_id)
            if existing is None:
                merged[object_id] = surface
                continue
            existing.attributes.update(surface.attributes)
            if surface.location is not None:
                existing.location = surface.location
    return merged


def register_regional_population() -> None:
    """Install the merged coordinator as the live lifecycle stage (idempotent)."""
    register_event_source(
        STAGE_KIND,
        settle_population_lifecycle,
        snapshot_population_lifecycle_surfaces,
        next_boundary=next_population_lifecycle_boundary,
    )


__all__ = [
    "STAGE_KIND",
    "ensure_locations_current",
    "ensure_observed_population_current",
    "ensure_population_current",
    "next_population_lifecycle_boundary",
    "register_regional_population",
    "settle_population_lifecycle",
    "settle_population_scope",
    "snapshot_population_lifecycle_surfaces",
]
