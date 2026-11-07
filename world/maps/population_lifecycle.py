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

from typing import Any

from world.maps import monster_activity, monster_sites, regional_population
from world.rules.clock import ScheduledEvent, SurfaceSnapshot, register_event_source

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
    wilderness: Any, tick: int, *, contact_tick: int | None = None
) -> list[ScheduledEvent]:
    """Apply every category of boundary at one already selected tick.

    ``contact_tick`` names the advance's accepted endpoint. Authored contact is
    admitted only there (never at an interior tick whose physiology was
    already settled to a later endpoint) and always after the same tick's
    lawful arrivals and births but before its idle departures.
    """
    zone_keys = _zone_keys(wilderness)
    # 1. Lawful completed arrivals and protected-arrival retries first, so a
    # present arrival consumes the headroom it actually occupies at this tick.
    events = list(monster_activity.settle_monster_activity_at(wilderness, tick))
    noted = _note_boundary(wilderness, zone_keys, tick)
    # 2. Explicit site births, then 3. ordinary regional births.
    events.extend(monster_sites.settle_monster_sites_at(tick))
    # Same-tick explicit site births restore local density: cancel or refresh
    # each episode from the post-site counts before any regional wave is
    # considered, so a restored episode never survives into a later due time.
    noted = _note_boundary(wilderness, zone_keys, tick, noted=noted)
    for zone_key in zone_keys:
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
    if contact_tick is not None and int(tick) == int(contact_tick):
        from world.rules.field_contact import settle_population_contact_at

        # A failed contact restores its participants and the advance goes on.
        with monster_activity.unbatched_state_writes():
            events.extend(
                settle_population_contact_at(wilderness, tick, int(contact_tick))
            )
        regional_population.forget_living_presence()
    # 5. Idle departures last: a contact cannot be avoided by iterating a
    # wandering departure before the encounter it belongs to.
    events.extend(monster_activity.settle_group_decisions_at(wilderness, tick))
    # A zero-duration committed departure arrives at this same tick. It is
    # settled here rather than scheduling an unreachable same-tick boundary;
    # the owner advances no clock and no second scheduler exists.
    events.extend(monster_activity.settle_monster_activity_at(wilderness, tick))
    # A departure can itself open a recovery deficit at this tick. Establish or
    # cancel each episode from the post-departure counts without another birth.
    _note_boundary(wilderness, zone_keys, tick, noted=noted)
    regional_population.settle_timeline_through(
        wilderness, tick, retain=monster_sites.retained_loss_ids(wilderness)
    )
    return events


def _next_population_boundary(
    wilderness: Any, tick: int, end_tick: int
) -> int | None:
    """The earliest merged boundary strictly after ``tick`` up to ``end_tick``."""
    timeline = regional_population.read_population_timeline(wilderness)
    candidates = [
        transition.occurred_tick
        for transition in timeline.transitions
        if tick < transition.occurred_tick <= end_tick
    ]
    site_boundary = monster_sites.next_site_boundary(tick, end_tick)
    if site_boundary is not None:
        candidates.append(site_boundary)
    journey_boundary = monster_activity.next_monster_activity_boundary(
        wilderness, tick, end_tick
    )
    if journey_boundary is not None:
        candidates.append(journey_boundary)
    # A birth route deferred by encounter protection retries on the first
    # unprotected tick, so protection end is a real merged boundary.
    for protection in timeline.protection:
        if protection.end_tick is None:
            continue
        resumed = protection.end_tick + 1
        if tick < resumed <= end_tick:
            candidates.append(resumed)
    for zone_key in _zone_keys(wilderness):
        state = regional_population.zone_state(wilderness, zone_key)
        due = None if state is None else state.recovery_due_tick
        if due is not None and tick < due <= end_tick:
            candidates.append(due)
    return min(candidates) if candidates else None


def settle_population_lifecycle(
    start_tick: int, end_tick: int
) -> list[ScheduledEvent]:
    """Settle every population boundary in ``[start_tick, end_tick]`` in order.

    A world with no wilderness script or no explicitly initialized population
    seed has no population lifecycle to run and settles nothing.
    """
    wilderness = _wilderness()
    if wilderness is None or not regional_population.population_provisioned(wilderness):
        return []
    events: list[ScheduledEvent] = []
    tick = start_tick
    with (
        monster_activity.batched_state_writes(wilderness),
        regional_population.reused_living_presence(),
    ):
        while tick <= end_tick:
            events.extend(
                _settle_population_at(wilderness, tick, contact_tick=end_tick)
            )
            following = _next_population_boundary(wilderness, tick, end_tick)
            if following is None or following <= tick:
                break
            tick = following
        # Progress is the interval endpoint whether or not a boundary fell
        # there: equal elapsed time must leave equal settlement progress and
        # equal protection retirement.
        monster_activity.settle_idle_physiology(wilderness, end_tick)
        regional_population.settle_timeline_through(
            wilderness,
            end_tick,
            retain=monster_sites.retained_loss_ids(wilderness),
        )
        monster_activity.retire_room_protection(wilderness, end_tick)
        monster_activity.retire_settled_decision_receipts(wilderness, end_tick)
    return events


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
    "next_population_lifecycle_boundary",
    "register_regional_population",
    "settle_population_lifecycle",
    "snapshot_population_lifecycle_surfaces",
]
