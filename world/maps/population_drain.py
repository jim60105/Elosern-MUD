"""The bounded background drain of the monster-population backlog.

A clock advance settles only the units a player observes, so an unobserved unit
falls behind the world tick and would pay its whole debt in one synchronous
step when a player first comes near. This module pays that debt off the action
path: one drain run performs a bounded number of steps, each selecting the
closed set of units with the lowest settled-through tick and settling it
forward by at most one bounded slice of game time, in its own short transaction
with full rollback.

Any partition of the same elapsed interval gives the same per-unit result, so
materialising the debt in slices changes no outcome. The drain never moves the
world tick and admits no field contact; it materialises game time that already
elapsed through player actions.

``PopulationDrainScript`` is the thin periodic caller: it holds no logic of its
own beyond the enable switch and the recent-input gate, and reads its interval
from settings at creation. The reactor is single-threaded and every clock
advance is synchronous, so a repeat can never interleave with a pass; a drain
is never called from inside one either.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from django.conf import settings
from django.db import transaction

from evennia import DefaultScript

from world.maps import population_lifecycle, population_units, regional_population
from world.observability import log_error, log_info
from world.rules import player_input
from world.rules.clock import held_advance_registry, restore_advance_registry

#: How many failed sets one run tolerates before it yields to the reactor.
MAX_FAILED_SETS_PER_RUN = 3


def _require_slice(slice_seconds: object) -> int:
    """One positive game-second slice; every other value is an argument error."""
    if (
        isinstance(slice_seconds, bool)
        or not isinstance(slice_seconds, int)
        or slice_seconds <= 0
    ):
        raise ValueError(
            f"slice_seconds must be a positive integer, got {slice_seconds!r}"
        )
    return slice_seconds


def _require_steps(max_steps: object) -> int:
    """One positive settlement-step count; every other value is an argument error."""
    if (
        isinstance(max_steps, bool)
        or not isinstance(max_steps, int)
        or max_steps <= 0
    ):
        raise ValueError(
            f"max_steps must be a positive integer, got {max_steps!r}"
        )
    return max_steps


def _units_still_lagging(
    pending: Iterable[tuple[int, frozenset[str]]],
    cursors: population_units.UnitCursors,
    advanced: Mapping[str, int],
    units: frozenset[str],
    target: int,
    now: int,
) -> int:
    """How many units lag once this step settled ``units`` to ``target``.

    A settlement never lowers a cursor, so a unit stands at the largest of its
    recorded cursor, the tick an earlier step of this run advanced it to, and
    ``target`` when this step settled it. A linked set may lawfully hold an
    already-current unit; it is counted only while its own cursor is behind
    ``now``, which is what the event reports.
    """
    remaining = 0
    for _, closed in pending:
        for unit_id in closed:
            after = population_units.unit_cursor(cursors, unit_id)
            earlier = advanced.get(unit_id)
            if earlier is not None and earlier > after:
                after = earlier
            if unit_id in units and target > after:
                after = target
            if after < now:
                remaining += 1
    return remaining


def drain_population_backlog(slice_seconds: int, max_steps: int = 1) -> int:
    """Settle lagging closed sets forward, one slice per step.

    Performs at most ``max_steps`` settlement steps and returns how many
    settled. Each step selects the set with the lowest cursor (ties: the
    smallest unit identifier) among the sets this run has not failed on, using
    the cursors this run has already advanced.

    A world with no wilderness, no population seed or no cursor record settles
    nothing and returns ``0``. A set whose settlement fails keeps its complete
    prior durable and live state, emits one error event, and is not tried again
    in the same run; after three failed sets the run stops, so one bad set
    cannot starve the others. A world fault is reported the same way with no
    unit: the periodic caller must survive a malformed record.
    """
    slice_seconds = _require_slice(slice_seconds)
    max_steps = _require_steps(max_steps)
    try:
        wilderness = regional_population.live_wilderness()
        if wilderness is None or not regional_population.population_provisioned(
            wilderness
        ):
            return 0
        if not wilderness.attributes.has(
            population_units.POPULATION_UNIT_CURSORS_ATTRIBUTE
        ):
            return 0
        now = regional_population.current_population_tick()
        cursors = population_units.read_unit_cursors(wilderness)
        pending = population_units.lagging_sets(wilderness, now)
    except Exception as error:
        # A world-level fault (an unreadable or malformed record) has no unit
        # to name; the periodic caller answers the same event with units=0.
        log_error(
            "population_backlog_drain_failed",
            exc=error,
            context={"units": 0, "tick_from": 0, "tick_to": 0},
        )
        return 0
    candidates = [[cursor, units] for cursor, units in pending]
    advanced: dict[str, int] = {}
    settled = failed = 0
    while candidates and settled < max_steps and failed < MAX_FAILED_SETS_PER_RUN:
        position = min(
            range(len(candidates)),
            key=lambda item: (candidates[item][0], min(candidates[item][1])),
        )
        start, units = candidates[position]
        target = min(now, start + slice_seconds)
        registry = None
        try:
            scope = population_units.build_scope(wilderness, units)
            registry = population_lifecycle.snapshot_population_lifecycle_surfaces(
                start, target, scope=scope
            )
            remaining = _units_still_lagging(
                pending, cursors, advanced, units, target, now
            )
            event = {
                "units": len(units),
                "tick_from": start,
                "tick_to": target,
                "remaining": remaining,
            }
            with held_advance_registry(), transaction.atomic():
                population_lifecycle.settle_population_scope(
                    wilderness, units, target, contact=False
                )
                transaction.on_commit(
                    lambda context=event: log_info(
                        "population_backlog_drained", context=context
                    )
                )
        except Exception as error:
            # The atomic block has rolled back before this handler runs; the
            # registry restores the in-memory surfaces the pass advanced.
            if registry is not None:
                restore_advance_registry(registry, (wilderness,))
            log_error(
                "population_backlog_drain_failed",
                exc=error,
                context={
                    "units": len(units),
                    "tick_from": start,
                    "tick_to": target,
                },
            )
            del candidates[position]
            failed += 1
            continue
        settled += 1
        for unit_id in units:
            advanced[unit_id] = target
        if target >= now:
            del candidates[position]
        else:
            candidates[position][0] = target
    return settled


class PopulationDrainScript(DefaultScript):
    """Periodically settles the most lagging population sets, one slice each.

    A repeat inside the idle window since the last player input returns before
    reading any population record.
    """

    def at_script_creation(self) -> None:
        self.key = "population_drain"
        self.interval = settings.POPULATION_DRAIN_INTERVAL_SECONDS
        self.start_delay = True
        self.repeats = 0
        self.persistent = True

    def at_repeat(self) -> None:
        if not settings.POPULATION_DRAIN_ENABLED:
            return
        idle = player_input.seconds_since_player_input()
        if idle is not None and idle < settings.POPULATION_DRAIN_IDLE_SECONDS:
            return
        drain_population_backlog(
            settings.POPULATION_DRAIN_SLICE_SECONDS,
            settings.POPULATION_DRAIN_STEPS_PER_RUN,
        )


__all__ = [
    "MAX_FAILED_SETS_PER_RUN",
    "PopulationDrainScript",
    "drain_population_backlog",
]