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

from world.maps import monster_sites, regional_population
from world.rules.clock import ScheduledEvent, SurfaceSnapshot, register_event_source

#: The existing stage kind this coordinator installs itself under.
STAGE_KIND = monster_sites.SITE_STAGE_KIND


def _wilderness() -> Any | None:
    return regional_population.live_wilderness()


def _zone_keys(wilderness: Any) -> tuple[str, ...]:
    """Every initialized zone, in deterministic key order."""
    return regional_population.initialized_zone_keys(wilderness)


def _settle_population_at(wilderness: Any, tick: int) -> list[ScheduledEvent]:
    """Apply every category of boundary at one already selected tick."""
    zone_keys = _zone_keys(wilderness)
    for zone_key in zone_keys:
        regional_population.note_population_boundary(
            wilderness, zone_key, tick=tick
        )
    events = list(monster_sites.settle_monster_sites_at(tick))
    for zone_key in zone_keys:
        events.extend(
            regional_population.settle_recovery_due(
                wilderness, zone_key, tick=tick
            )
        )
    regional_population.settle_timeline_through(wilderness, tick)
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
    while tick <= end_tick:
        events.extend(_settle_population_at(wilderness, tick))
        following = _next_population_boundary(wilderness, tick, end_tick)
        if following is None or following <= tick:
            break
        tick = following
    return events


def next_population_lifecycle_boundary(
    start_tick: int, end_tick: int
) -> int | None:
    """The next population boundary without executing any writer (pure read)."""
    wilderness = _wilderness()
    if wilderness is None or not regional_population.population_provisioned(wilderness):
        return None
    return _next_population_boundary(wilderness, start_tick, end_tick)


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
