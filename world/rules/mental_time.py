"""Pure per-member mental activity and interruptible-boundary composition.

The mental-reserve physiology core owns exact reserve units, activity rates
and the sole writer. This module answers only the pure questions the clock's
party settlement needs: which transient activity one member settles, and how
far an accepted player-driven interval may run before the first interaction
boundary (a forced-sleep entry, a forced sleeper's natural wake, or a
registered interactive event). Nothing here writes state or advances time.

A member with no constructed physiology (a synthetic fixture or a
non-physiological creature) is simply absent from mental settlement; a
half-written or malformed state fails closed through the fatigue reader.
Dead and deleted members are excluded by the caller's present-party scope and
never revived here.
"""

from __future__ import annotations

from fractions import Fraction
from math import ceil
from typing import Any

from world.rules.clock import (
    MentalPlan,
    next_registered_boundary,
)
from world.rules.fatigue import (
    FatigueActivity,
    FatigueState,
    IntervalCompletion,
    SleepPosture,
    get_policy,
    read_optional_fatigue_state,
)


def sample_activity(
    entity: Any, awake_activity: FatigueActivity = FatigueActivity.AWAKE
) -> FatigueActivity:
    """Return the activity a body's stored posture settles over an interval."""
    state = read_optional_fatigue_state(entity)
    if state is None or state.posture is SleepPosture.AWAKE:
        return awake_activity
    return FatigueActivity.SLEEP


def is_forced_sleeper(entity: Any) -> bool:
    """Whether one body's stored posture is the forced-sleep latch."""
    state = read_optional_fatigue_state(entity)
    return state is not None and state.posture is SleepPosture.FORCED


def _offset_seconds(state: FatigueState, activity: FatigueActivity) -> int | None:
    """Whole seconds until the member's next *interactive* fatigue boundary.

    Awake intervals stop only at forced-sleep entry (depletion): ordinary
    stage floors are non-interactive and consume exactly. A forced sleeper
    stops at its natural wake threshold; a voluntary sleeper's target is the
    caller's requested completion, so it declares no earlier boundary.
    """
    policy = get_policy()
    if state.posture is SleepPosture.AWAKE:
        rate = policy.rates[activity]
        if rate >= 0:
            return None
        return ceil(Fraction(state.reserve_units, -rate))
    if state.posture is SleepPosture.FORCED:
        sleep_rate = policy.rates[FatigueActivity.SLEEP]
        if sleep_rate <= 0:
            return None
        gap = max(0, policy.wake_units - state.reserve_units)
        return ceil(Fraction(gap, sleep_rate))
    return None


def next_mental_offset(
    entity: Any, awake_activity: FatigueActivity = FatigueActivity.AWAKE
) -> int | None:
    """Return one member's next interactive mental offset, or ``None``."""
    state = read_optional_fatigue_state(entity)
    if state is None:
        return None
    return _offset_seconds(state, sample_activity(entity, awake_activity))


def next_skip_boundary(
    scope: tuple[Any, ...] | list[Any],
    limit: int,
    *,
    tick: int,
    awake_activity: FatigueActivity = FatigueActivity.AWAKE,
) -> int | None:
    """Return the earliest offset within ``limit`` that must interrupt a skip.

    Combines each member's forced-sleep entry/wake boundary with the earliest
    pure registered interactive-event query. Returns ``None`` when no boundary
    falls inside ``limit``.
    """
    if limit <= 0:
        return None
    offsets = [
        offset
        for entity in scope
        if (offset := next_mental_offset(entity, awake_activity)) is not None
    ]
    registered = next_registered_boundary(tick, tick + limit)
    if registered is not None:
        offsets.append(registered)
    if not offsets:
        return None
    earliest = min(offsets)
    return earliest if earliest <= limit else None


def planned_seconds(
    scope: tuple[Any, ...] | list[Any],
    requested: int,
    *,
    tick: int,
    awake_activity: FatigueActivity = FatigueActivity.AWAKE,
) -> int:
    """Return the accepted elapsed seconds before the first relevant boundary."""
    if requested <= 0:
        return 0
    boundary = next_skip_boundary(
        scope, requested, tick=tick, awake_activity=awake_activity
    )
    return requested if boundary is None else min(requested, boundary)


def plan_for(
    scope: tuple[Any, ...],
    *,
    awake_activity: FatigueActivity = FatigueActivity.AWAKE,
    completion: IntervalCompletion = IntervalCompletion.INTERRUPTIBLE,
) -> MentalPlan:
    """Build the clock's explicit mental context for a present party."""
    return MentalPlan(
        scope=scope,
        activity_for=lambda entity: sample_activity(entity, awake_activity),
        completion=completion,
    )


def indivisible_plan(scope: tuple[Any, ...]) -> MentalPlan:
    """Build the full-duration plan of an indivisible field action or rite."""
    return plan_for(scope, completion=IntervalCompletion.INDIVISIBLE)


__all__ = [
    "is_forced_sleeper",
    "indivisible_plan",
    "next_mental_offset",
    "next_skip_boundary",
    "plan_for",
    "planned_seconds",
    "sample_activity",
]
