"""The bounded background drain of the monster-population backlog.

A clock advance settles only the units a player observes, so an unobserved unit
falls behind the world tick and would pay its whole debt in one synchronous
step when a player first comes near. This module pays that debt off the action
path: one drain run selects the closed set of units with the lowest
settled-through tick and settles it forward by at most one bounded slice of
game time, in its own short transaction with full rollback.

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

from collections.abc import Iterable

from django.conf import settings
from django.db import transaction

from evennia import DefaultScript

from world.maps import population_lifecycle, population_units, regional_population
from world.observability import log_error, log_info
from world.rules import player_input
from world.rules.clock import held_advance_registry, restore_advance_registry

#: How many lagging closed sets one run tries before it yields to the reactor.
MAX_SETS_PER_RUN = 3


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


def _units_still_lagging(
    pending: Iterable[tuple[int, frozenset[str]]],
    cursors: population_units.UnitCursors,
    settled: frozenset[str],
    target: int,
    now: int,
) -> int:
    """How many units lag once this run settled ``settled`` to ``target``.

    A settlement never lowers a cursor, so a settled unit stands at
    ``max(cursor, target)`` afterwards and every other unit keeps its cursor.
    A linked set may lawfully hold an already-current unit; it is counted only
    while its own cursor is behind ``now``, which is what the event reports.
    """
    remaining = 0
    for _, closed in pending:
        for unit_id in closed:
            after = population_units.unit_cursor(cursors, unit_id)
            if unit_id in settled and target > after:
                after = target
            if after < now:
                remaining += 1
    return remaining


def drain_population_backlog(slice_seconds: int) -> bool:
    """Settle the most lagging closed set forward by one slice.

    Returns ``True`` when one set settled. A world with no wilderness, no
    population seed or no cursor record settles nothing and returns ``False``.
    A set whose settlement fails keeps its complete prior durable and live
    state, emits one error event, and the run then tries the next lagging set,
    so one bad set cannot starve the others. A world fault is reported the same
    way with no unit: the periodic caller must survive a malformed record.
    """
    slice_seconds = _require_slice(slice_seconds)
    try:
        wilderness = regional_population.live_wilderness()
        if wilderness is None or not regional_population.population_provisioned(
            wilderness
        ):
            return False
        if not wilderness.attributes.has(
            population_units.POPULATION_UNIT_CURSORS_ATTRIBUTE
        ):
            return False
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
        return False
    for start, units in pending[:MAX_SETS_PER_RUN]:
        target = min(now, start + slice_seconds)
        registry = None
        try:
            scope = population_units.build_scope(wilderness, units)
            registry = population_lifecycle.snapshot_population_lifecycle_surfaces(
                start, target, scope=scope
            )
            remaining = _units_still_lagging(pending, cursors, units, target, now)
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
            continue
        return True
    return False


class PopulationDrainScript(DefaultScript):
    """Periodically settles the most lagging population set by one slice.

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
        drain_population_backlog(settings.POPULATION_DRAIN_SLICE_SECONDS)


__all__ = [
    "MAX_SETS_PER_RUN",
    "PopulationDrainScript",
    "drain_population_backlog",
]