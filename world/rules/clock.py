"""Player-driven deterministic world time and settlement ordering."""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import floor, gcd
from pathlib import Path
from typing import Any

import yaml
from django.db import transaction
from evennia import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.search import search_script

from world.observability import log_info, log_warn
from world.rules.buffs import BUFF_DEFINITIONS, tick_buffs
from world.rules.fatigue import (
    FATIGUE_ATTRIBUTE_SURFACES,
    FatigueActivity,
    FatigueInterval,
    IntervalCompletion,
    SleepPosture,
    predict_interval,
    project_fatigue_status,
    read_optional_fatigue_state,
    settle_fatigue_intervals,
    sleep_blocks_actions,
    write_fatigue_state,
)
from world.rules.quantum import SETTLEMENT_QUANTUM_SECONDS
from world.rules.progression import grant_study_practice_xp
from world.rules.pleasure import saintess_trickle_step
from world.rules.sexual_state import (
    DECAY_CONFIG,
    PLEASURE_CONFIG,
    climax_settlement_action,
    decay_tick,
    reset_daily_counters,
)
from world.rules.sexual_transitions import apply_event
from world.rules.sleep_receipt import (
    MODE_RECOVERY,
    SLEEP_RECEIPT_SURFACES,
    STATE_COMPLETED,
    STATE_INTERRUPTED,
    STATE_SLEEPING,
    SleepReceipt,
    SleepReceiptError,
    full_recovery_seconds,
    next_sleep_offset,
    read_sleep_receipt,
    recovery_target_tick,
    write_sleep_receipt,
)
from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort
from world.rules.traits import GAUGE_KEYS
from world.rules.unlock_notices import PRACTICE_UNLOCK_EVENT, UnlockNotice


CLOCK_YAML = yaml.safe_load(
    (Path(__file__).parent / "rulebook" / "clock.yaml").read_text(encoding="utf-8")
)
_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]

# A single advance may cover at most one full game day: this keeps ``wait
# until``'s worst case (a day-long wait) legal while bounding the per-day
# boundary loop at one crossing per call.
MAX_ADVANCE_SECONDS = _DAY_SECONDS


def _validate_settlement_intervals(buff_definitions, decay_config) -> int:
    """Validate every settlement interval, returning their greatest common divisor."""
    intervals = [
        definition.tick_interval
        for definition in buff_definitions.values()
        if definition.tick_interval is not None
    ] + [config["interval_seconds"] for config in decay_config.values()]
    if any(not isinstance(interval, int) or interval <= 0 for interval in intervals):
        raise ValueError(f"invalid settlement interval: {intervals!r}")
    return gcd(*intervals)


_DERIVED_QUANTUM = _validate_settlement_intervals(BUFF_DEFINITIONS, DECAY_CONFIG)
if _DERIVED_QUANTUM != SETTLEMENT_QUANTUM_SECONDS:
    raise ValueError(
        f"derived settlement quantum {_DERIVED_QUANTUM} does not match canonical SETTLEMENT_QUANTUM_SECONDS {SETTLEMENT_QUANTUM_SECONDS}"
    )
_STAGE_ORDER = (
    "gauge_regen",
    "buff_ticks",
    "sexual_decay",
    "practice_settlement",
    "daily_resets",
    "caravan_arrivals",
    "shop_hours",
    "quest_deadlines",
    "npc_schedules",
    "correspondence_delivery",
    "instance_reclamation",
    "monster_site_lifecycle",
)


@dataclass
class SurfaceSnapshot:
    """One object's durable pre-advance state, captured by a pure read.

    ``attributes`` maps ``(key, category)`` to ``(existed, deepcopy(value))``
    exactly as the shared ``attribute_snapshot`` helper returns. ``location``
    is ``(existed, pre-advance db_location pk)`` when the declaring source may
    move the object: the location is stored as a plain primary key, never a
    live object, because a room deleted inside the rolled-back transaction has
    ``pk = None`` on its stale instance and restoring ``db_location`` from that
    instance would orphan the moved occupant.
    """

    attributes: dict[tuple[str, str | None], tuple[bool, Any]]
    location: tuple[bool, int] | None = None


@dataclass(frozen=True)
class EventSourceRegistration:
    """One registered boundary-stage source plus its advance-surface contract.

    ``surfaces`` is ``None`` for a read-only seam (or a test/synthetic
    source): ``advance()`` performs no snapshot or restore for it.
    """

    settle: Callable[[int, int], list["ScheduledEvent"]]
    surfaces: Callable[[int, int], Mapping[int, SurfaceSnapshot]] | None = None
    next_boundary: Callable[[int, int], int | None] | None = None


_EVENT_SOURCES: dict[str, EventSourceRegistration] = {}


class DaypartError(ValueError):
    """Raised when a named clock daypart is unknown."""


class ClockAdvanceBoundError(ValueError):
    """Raised when an advance would exceed ``MAX_ADVANCE_SECONDS``."""


class AdvanceSource(StrEnum):
    """The action category that supplied elapsed game seconds."""

    COMMAND = "command"
    GM = "gm"
    COMBAT = "combat"
    SKIP = "skip"
    DEFEAT_AFTERMATH = "defeat_aftermath"


@dataclass(frozen=True)
class WorldDateTime:
    """Calendar fields derived entirely from one game-time tick."""

    year: int
    season_index: int
    day_in_season: int
    hour: int
    minute: int
    second: int

    @classmethod
    def from_tick(cls, tick: int) -> "WorldDateTime":
        if tick < 0:
            raise ValueError("tick must be non-negative")
        total_days, remaining = divmod(tick, _DAY_SECONDS)
        days_per_year = CLOCK_YAML["days_per_season"] * CLOCK_YAML["seasons_per_year"]
        year, day_of_year = divmod(total_days, days_per_year)
        season_index, day_index = divmod(day_of_year, CLOCK_YAML["days_per_season"])
        hour, remaining = divmod(remaining, CLOCK_YAML["seconds_per_hour"])
        minute, second = divmod(remaining, 60)
        return cls(year, season_index, day_index + 1, hour, minute, second)

    @property
    def season_name(self) -> str:
        return CLOCK_YAML["season_names"][self.season_index]


def seconds_until_daypart(calendar: WorldDateTime, daypart_name: str) -> int:
    """Return seconds until the next strictly future occurrence of a daypart."""
    try:
        target_hour = CLOCK_YAML["dayparts"][daypart_name]
    except KeyError as error:
        raise DaypartError(f"unknown daypart {daypart_name!r}") from error
    current = calendar.hour * CLOCK_YAML["seconds_per_hour"] + calendar.minute * 60 + calendar.second
    target = target_hour * CLOCK_YAML["seconds_per_hour"]
    remaining = target - current
    return remaining if remaining > 0 else remaining + _DAY_SECONDS


def _daypart_index(tick: int) -> int:
    """The current daypart region of ``tick``, indexed by its sorted start hour.

    ``TimePeriod`` eligibility is a pure function of the daypart region, so a
    committed advance changes it exactly when this index changes. Two advances
    within one region therefore schedule no dialogue refresh, and a crossing
    (including midnight, which is its own start hour) schedules exactly one.
    """
    calendar = WorldDateTime.from_tick(tick)
    seconds_per_hour = CLOCK_YAML["seconds_per_hour"]
    current = calendar.hour * seconds_per_hour + calendar.minute * 60 + calendar.second
    starts = sorted({int(hour) * seconds_per_hour for hour in CLOCK_YAML["dayparts"].values()})
    index = 0
    for position, start in enumerate(starts):
        if current >= start:
            index = position
    return index


@dataclass(frozen=True)
class ScheduledEvent:
    """A serializable event made due by a world-time boundary."""

    kind: str
    due_tick: int
    payload: dict[str, Any]
    #: Whether this event is an interactive registered boundary (the same
    #: sources that declare ``next_boundary`` for ordinary skips). Maintenance
    #: stages stay non-interactive, so an owner-target sleep continuation
    #: consumes across them instead of stopping for housekeeping.
    interactive: bool = False


def _gauge_value(gauge: Any) -> float:
    return float(getattr(gauge, "current", gauge.value))


def _settle_gauge_regen(entities: Iterable[Any], elapsed_seconds: int) -> None:
    for entity in entities:
        mods: dict[str, Any] = {}
        if hasattr(entity, "traits"):
            try:
                from world.rules.combat_modifiers import evaluate_combat_modifiers

                mods = evaluate_combat_modifiers(entity)
            except Exception:  # observability: ignore R2: entity may be a test double without db or complete attributes, treating as unscaled
                pass

        for key in GAUGE_KEYS:
            gauge = getattr(entity.traits, key, None)
            if gauge is None:
                continue
            scale = float(mods.get(f"{key}_regen_scale", 1.0))
            if scale == 0.0:
                continue
            rate = float(getattr(gauge, "rate", 0)) * scale
            maximum = float(gauge.max)
            # Gauge storage is integral (the status read model rejects floats),
            # so each gauge keeps a sub-unit regen remainder. Accruing in
            # float keeps segmented advances (two moves) equal to one advance
            # of the same total duration: floor(lost) + floor(lost) == floor(2*lost)
            # only when the per-advance fraction is carried, never dropped.
            carried = float(getattr(gauge, "regen_remainder", 0.0))
            continuous = _gauge_value(gauge) + carried + rate * elapsed_seconds
            if continuous >= maximum:
                gauge.current = round(maximum)
                gauge.regen_remainder = 0.0
            else:
                whole = floor(continuous)
                gauge.current = whole
                gauge.regen_remainder = continuous - whole


def _has_settlement_work(entity: Any) -> bool:
    buffs = getattr(entity, "buffs", None)
    if buffs is not None and getattr(buffs, "all", None) and buffs.all:
        from world.rules.buffs import _active_buff_instances

        if any(
            buff.remaining_seconds is not None or buff.tick_interval is not None
            for buff in _active_buff_instances(entity)
        ):
            return True
    sexual = getattr(entity, "sexual", None)
    if sexual is None:
        return False
    if sexual.climax_phase.level == "進行中":
        return True
    for field, config in DECAY_CONFIG.items():
        if config.get("only_from") is not None and getattr(
            sexual, field
        ).level != config["only_from"]:
            continue
        trait = getattr(sexual, field)
        level = getattr(trait, "level", None)
        if level is not None:
            if level != config["floor"]:
                return True
        elif trait.value != PLEASURE_CONFIG.floor_for_level(config["floor"]):
            # Counter fields (pleasure) have no level vocabulary; the band
            # table's floor is their resting point.
            return True
    return False


def _settle_buffs_and_decay(
    entities: tuple[Any, ...],
    elapsed_seconds: int,
    start_tick: int = 0,
) -> None:
    from world.narrative.action_adapters import (
        capture_milestone_snapshot,
        record_non_resolver_adult_milestones,
    )
    quanta, remainder = divmod(elapsed_seconds, SETTLEMENT_QUANTUM_SECONDS)
    for quantum_idx in range(min(quanta, CLOCK_YAML["max_settlement_quanta"])):
        if not any(_has_settlement_work(entity) for entity in entities):
            break
        q_tick = start_tick + (quantum_idx + 1) * SETTLEMENT_QUANTUM_SECONDS
        for entity in entities:
            before_ms = capture_milestone_snapshot(entity)
            tick_buffs(entity, SETTLEMENT_QUANTUM_SECONDS)
            decay_tick(entity, SETTLEMENT_QUANTUM_SECONDS)
            action = climax_settlement_action(entity)
            if action == "extend":
                apply_event(entity, "climax_extended")
            elif action == "end":
                apply_event(entity, "climax_ends")
            e_id = getattr(entity, "pk", id(entity))
            record_non_resolver_adult_milestones(
                entity,
                before_ms,
                source_id=f"clock:climax:{q_tick}:{e_id}",
                tick=q_tick,
                location=getattr(entity, "location", None),
            )
    if remainder and any(_has_settlement_work(entity) for entity in entities):
        rem_tick = start_tick + elapsed_seconds
        for entity in entities:
            before_ms = capture_milestone_snapshot(entity)
            tick_buffs(entity, remainder)
            decay_tick(entity, remainder)
            action = climax_settlement_action(entity)
            if action == "extend":
                apply_event(entity, "climax_extended")
            elif action == "end":
                apply_event(entity, "climax_ends")
            e_id = getattr(entity, "pk", id(entity))
            record_non_resolver_adult_milestones(
                entity,
                before_ms,
                source_id=f"clock:climax:{rem_tick}:{e_id}",
                tick=rem_tick,
                location=getattr(entity, "location", None),
            )


def _practice_settlement(
    entities: tuple[Any, ...],
    seconds: int,
    source: AdvanceSource,
    due_tick: int,
    eligible: Mapping[int, int] | None = None,
) -> list[ScheduledEvent]:
    """Settle declared-practice bookings in closed form (D7: the real writer).

    SKIP-source only: declared practice is downtime, so a combat advance must
    never settle it (the COMBAT gate in ``_run_stages`` stays permanent, and
    this gate additionally leaves a COMMAND-source advance's booking
    unconsumed for the actor's next SKIP). Exactly once per entity per
    advance: the whole elapsed value collapses to completed whole hours —
    never the quantum loop — and a sub-hour or zero-second SKIP advance
    consumes the booking with zero growth, so a booking can only ever be
    settled by the first successful SKIP advance after it was declared.
    Storage routes exclusively through progression's ``grant_study_practice_xp``
    (whose sole writer is ``award_practice_xp``), so booked awards saturate
    identically to per-use awards at the derived tip cap. An entity without a
    booking — or without a ``db`` at all — is written nothing. Ownership is
    revalidated against current canonical state when the booking settles, so
    a standing booking whose skill was lost while it stood is consumed
    without progression; the award's own saturation is the cap revalidation.

    Returns one ``practice_unlock`` :class:`ScheduledEvent` per skill the
    settled award made usable, carrying the learner and the rendered line.
    The event list is the advance's own return value, so a rolled-back
    advance discards it and no owner can deliver an unlock the commit did not
    keep.
    """
    if source is not AdvanceSource.SKIP or seconds <= 0:
        return []
    events: list[ScheduledEvent] = []
    for entity in entities:
        db = getattr(entity, "db", None)
        if db is None:
            continue
        if eligible is not None:
            if id(entity) not in eligible:
                # A sleeping member's standing booking is preserved for a
                # later eligible awake interval; it is never consumed by
                # time the member spent asleep.
                continue
            hours = eligible[id(entity)] // 3600
        elif sleep_blocks_actions(entity):
            continue
        else:
            hours = seconds // 3600
        booking = getattr(db, "practice_booking", None)
        if booking is None:
            continue
        db.practice_booking = None
        if hours < 1 or not _owns_booking_skill(entity, booking):
            continue
        notices: list[UnlockNotice] = []
        grant_study_practice_xp(entity, booking, hours, unlocks_out=notices)
        events.extend(
            ScheduledEvent(
                PRACTICE_UNLOCK_EVENT,
                due_tick,
                {
                    "learner_id": notice.learner_id,
                    "learner_name": notice.learner_name,
                    "skill_key": notice.skill_key,
                    "line": notice.line,
                },
            )
            for notice in notices
        )
    return events


def _owns_booking_skill(entity: Any, skill_key: str) -> bool:
    """Whether the entity still owns the booked skill at settlement time."""
    skills = getattr(entity, "skills", None)
    owned = getattr(skills, "owned_keys", None)
    return callable(owned) and skill_key in owned()


def register_event_source(
    kind: str,
    source: Callable[[int, int], list[ScheduledEvent]],
    surfaces: Callable[[int, int], Mapping[int, SurfaceSnapshot]] | None = None,
    *,
    next_boundary: Callable[[int, int], int | None] | None = None,
) -> None:
    """Register a boundary-query seam owned by a future subsystem.

    ``surfaces`` is the optional advance-surface contract: a pure, read-only
    callable ``(start_tick, end_tick) -> mapping[id(obj), SurfaceSnapshot]``
    that re-discovers, with the same deterministic queries its settlement
    uses, every object the source may write and snapshots each durable
    surface. A source that writes durable state SHALL ship a contract; a
    source registered with ``surfaces=None`` is a read-only seam (or a test
    seam) and is never snapshotted or restored by ``advance()``.
    """
    _EVENT_SOURCES[kind] = EventSourceRegistration(source, surfaces, next_boundary)


def next_registered_boundary(start_tick: int, end_tick: int) -> int | None:
    """Return the earliest interactive-event offset declared before ``end_tick``.

    A registered source may declare a pure ``next_boundary(start, end)``
    query; it returns the absolute tick of its next interactive fact or
    ``None``. The minimum offset is returned so an interruptible skip can stop
    before the earliest relevant event without executing any writer.
    """
    offsets: list[int] = []
    for registration in _EVENT_SOURCES.values():
        query = registration.next_boundary
        if query is None:
            continue
        due_tick = query(start_tick, end_tick)
        if due_tick is None:
            continue
        offset = int(due_tick) - start_tick
        if 0 < offset <= end_tick - start_tick:
            offsets.append(offset)
    return min(offsets) if offsets else None


def _mental_state_or_none(entity: Any) -> Any:
    """Read one member's fatigue state, or ``None`` when it was never initialized.

    A wholly absent reserve/posture pair is the construction baseline of a
    non-physiological fixture and is skipped. A half-written pair (or any
    malformed value) is corrupt and fails closed through ``read_fatigue_state``.
    """
    return read_optional_fatigue_state(entity)


def _is_dead(entity: Any) -> bool:
    """Whether one member's stored HP is at or below zero (never resurrected)."""
    try:
        hp = entity.traits.hp
        value = getattr(hp, "current", getattr(hp, "value", 0))
        return float(value) <= 0
    except Exception:  # observability: ignore R2: an entity without readable traits is a synthetic non-physiological fixture, not a dead actor; nothing is written for it
        return False


def _same_state(left: Any, right: Any) -> bool:
    return (
        left is not None
        and right is not None
        and left.reserve_units == right.reserve_units
        and left.posture is right.posture
    )


@dataclass(frozen=True)
class MentalPlan:
    """Explicit per-member mental activity and policy for one accepted advance.

    ``scope`` is the present co-located mental party; it is deliberately wider
    than the ordinary resource ``entities`` when a rite or other narrow-scope
    effect settles. ``activity_for`` samples one member's transient activity
    at call time, so a posture committed earlier in the same advance is
    reflected by later segments. ``completion`` is ``INDIVISIBLE`` for a field
    action that must commit its whole duration before any collapse.
    """

    scope: tuple[Any, ...]
    activity_for: Callable[[Any], FatigueActivity]
    completion: IntervalCompletion = IntervalCompletion.INTERRUPTIBLE
    #: Optional caller-owned list receiving the committed fatigue records.
    record: list[Any] | None = None


_RECEIPT_UNUSABLE = object()


def _voluntary_sleep_offsets(
    plan: MentalPlan | None, start_tick: int
) -> dict[int, int]:
    """Capture each sleeper's own boundary from pre-regeneration state.

    The advance regenerates gauges for its full window before mental
    settlement, so a recovery boundary read afterwards would see the action's
    own regeneration and wake a gauge-limited sleeper at the start. This pure
    read runs before any resource write and is the single boundary used by
    both indivisible subdivision and practice accounting.
    """
    if plan is None:
        return {}
    offsets: dict[int, int] = {}
    for entity in plan.scope:
        if getattr(entity, "_is_deleted", False) or _is_dead(entity):
            continue
        state = _mental_state_or_none(entity)
        if state is None or state.posture is not SleepPosture.VOLUNTARY:
            continue
        receipt = _receipt_state(entity, "boundary_capture")
        if receipt is _RECEIPT_UNUSABLE or receipt is None or not receipt.sleeping:
            continue
        offset = next_sleep_offset(entity, receipt, start_tick)
        if offset is not None:
            offsets[id(entity)] = offset
    return offsets


def _receipt_state(entity: Any, stage: str) -> Any:
    """Read one receipt for settlement; a corrupt record fails closed locally."""
    try:
        return read_sleep_receipt(entity)
    except SleepReceiptError as error:
        log_warn(
            "sleep_receipt_unusable",
            context={
                "char": str(getattr(entity, "pk", "?")),
                "reason": error.code,
                "stage": stage,
            },
        )
        return _RECEIPT_UNUSABLE


def _schedule_voluntary_wake(entity: Any, receipt: SleepReceipt, revision: int) -> None:
    """Emit one post-commit wake notification for a committed voluntary wake."""
    from typeclasses.characters import PlayerCharacter

    if not isinstance(entity, PlayerCharacter):
        return
    from world.rules.fatigue import _notify_wake_transition_observers

    occurrence_id = (
        f"wake:voluntary:{getattr(entity, 'pk', '')}:{receipt.sleep_id}:{revision}"
    )
    transaction.on_commit(
        lambda ent=entity, oid=occurrence_id: _notify_wake_transition_observers(
            ent, occurrence_id=oid, in_combat=False
        )
    )


def _reconcile_sleep_receipt(entity: Any, end_tick: int) -> bool:
    """Advance one body's receipt to ``end_tick`` and complete a due wake.

    The reconciliation runs inside the owning clock transaction and never
    changes possession, control or death state. A due voluntary target wakes
    the body once and completes the receipt; a body already awake without
    reaching its target is recorded as interrupted, never as completed sleep.
    """
    if getattr(entity, "_is_deleted", False):
        return False
    state = _mental_state_or_none(entity)
    if state is None or _is_dead(entity):
        return False
    receipt = _receipt_state(entity, "sleep_reconcile")
    if receipt is _RECEIPT_UNUSABLE or receipt is None:
        return False
    if not receipt.sleeping:
        return False
    target = recovery_target_tick(entity, receipt, end_tick)
    due = target <= end_tick
    woke = False
    new_state = receipt.state
    partial = receipt.partial
    if due and state.posture is SleepPosture.VOLUNTARY:
        write_fatigue_state(entity, state.reserve_units, SleepPosture.AWAKE)
        project_fatigue_status(entity)
        woke = True
        new_state = STATE_COMPLETED
        if receipt.mode == MODE_RECOVERY:
            partial = full_recovery_seconds(entity) > 0
    elif due:
        new_state = STATE_COMPLETED
    elif state.posture is SleepPosture.AWAKE:
        new_state = STATE_INTERRUPTED
    if (
        target == receipt.target_tick
        and new_state == receipt.state
        and end_tick <= receipt.settled_through_tick
    ):
        return False
    updated = receipt.with_progress(
        settled_through_tick=end_tick,
        target_tick=target,
        state=new_state,
        partial=partial,
    )
    write_sleep_receipt(entity, updated)
    if woke:
        _schedule_voluntary_wake(entity, updated, updated.revision)
    return woke


def _settle_interruptible_member(
    entity: Any,
    plan: MentalPlan,
    seconds: int,
    start_tick: int,
    commits: list[Any],
) -> None:
    """Commit one member's interactively segmented interval."""
    state = _mental_state_or_none(entity)
    remaining = seconds
    cursor = start_tick
    for _ in range(16):
        activity = plan.activity_for(entity)
        prediction = predict_interval(
            state, activity, remaining, completion=IntervalCompletion.INTERRUPTIBLE
        )
        step = prediction.applicable_seconds
        settlement = settle_fatigue_intervals(
            (
                FatigueInterval(
                    entity,
                    activity,
                    step,
                    state,
                    IntervalCompletion.INTERRUPTIBLE,
                ),
            ),
            context={"stage": "mental_settlement"},
            start_tick=cursor,
        )
        commit = settlement.commits[0]
        commits.append(commit)
        state = commit.end
        cursor += step
        remaining -= step
        if remaining <= 0:
            break
        if step == 0 and _same_state(commit.end, commit.start):
            raise RuntimeError(
                "mental settlement made no progress at a zero-second boundary"
            )
    else:
        raise RuntimeError("mental settlement exceeded its internal segment bound")


def _settle_indivisible_member(
    entity: Any,
    plan: MentalPlan,
    seconds: int,
    start_tick: int,
    receipt: Any,
    commits: list[Any],
    voluntary_deadline: int | None = None,
) -> None:
    """Commit one member's indivisible interval, splitting only physiology.

    A pre-existing voluntary accepted deadline inside the action subdivides the
    body's own physiology: it sleeps up to the deadline, wakes there, then
    consumes the remaining action time at the ordinary awake rate. The action's
    effects, cost, full duration and atomicity are unchanged.
    """
    state = _mental_state_or_none(entity)
    if voluntary_deadline is None and (
        isinstance(receipt, SleepReceipt)
        and receipt.sleeping
        and state.posture is SleepPosture.VOLUNTARY
    ):
        voluntary_deadline = next_sleep_offset(entity, receipt, start_tick)
    if voluntary_deadline is None or voluntary_deadline >= seconds:
        settlement = settle_fatigue_intervals(
            (
                FatigueInterval(
                    entity,
                    plan.activity_for(entity),
                    seconds,
                    state,
                    plan.completion,
                ),
            ),
            context={"stage": "mental_settlement"},
            start_tick=start_tick,
        )
        commits.extend(settlement.commits)
        return
    sleeping_seconds = max(0, min(seconds, voluntary_deadline))
    if sleeping_seconds > 0:
        settlement = settle_fatigue_intervals(
            (
                FatigueInterval(
                    entity,
                    plan.activity_for(entity),
                    sleeping_seconds,
                    state,
                    IntervalCompletion.INDIVISIBLE,
                ),
            ),
            context={"stage": "mental_settlement"},
            start_tick=start_tick,
        )
        commits.extend(settlement.commits)
    _reconcile_sleep_receipt(entity, start_tick + sleeping_seconds)
    remaining = seconds - sleeping_seconds
    if remaining <= 0:
        return
    awake_state = _mental_state_or_none(entity)
    if awake_state is None:
        return
    # The awake remainder keeps the action's indivisible completion policy: a
    # collapse inside it latches at completion and never earns recovery before
    # the paid action ends.
    settlement = settle_fatigue_intervals(
        (
            FatigueInterval(
                entity,
                plan.activity_for(entity),
                remaining,
                awake_state,
                plan.completion,
            ),
        ),
        context={"stage": "mental_settlement"},
        start_tick=start_tick + sleeping_seconds,
    )
    commits.extend(settlement.commits)


def _settle_mental(
    seconds: int,
    plan: MentalPlan | None,
    start_tick: int = 0,
    sleep_offsets: dict[int, int] | None = None,
) -> list[Any]:
    """Settle one present party's mental intervals inside the clock transaction.

    An ``INTERRUPTIBLE`` plan is segmented only across ordinary fatigue-stage
    thresholds (never across an interaction boundary: the caller already
    truncated the accepted interval). Each segment is committed through the
    sole fatigue writer, so exact reserve consumption and every exclusive
    projection survive one long advance. An ``INDIVISIBLE`` plan commits its
    full duration once, subdividing only the body's physiology at a
    pre-existing voluntary accepted deadline.

    Every living in-scope sleeper's own receipt cursor is reconciled at the
    interval end, including bodies this advance did not explicitly continue.
    A voluntary body whose receipt is missing or corrupt is left completely
    un-settled: no refill, no invented wake and no repair.
    """
    if plan is None:
        return []
    commits: list[Any] = []
    for entity in plan.scope:
        if getattr(entity, "_is_deleted", False):
            continue
        state = _mental_state_or_none(entity)
        if state is None or _is_dead(entity):
            continue
        receipt = _receipt_state(entity, "mental_settlement")
        if state.posture is SleepPosture.VOLUNTARY:
            if receipt is _RECEIPT_UNUSABLE or receipt is None:
                continue
        elif receipt is _RECEIPT_UNUSABLE:
            receipt = None
        if plan.completion is not IntervalCompletion.INTERRUPTIBLE:
            _settle_indivisible_member(
                entity,
                plan,
                seconds,
                start_tick,
                receipt,
                commits,
                (sleep_offsets or {}).get(id(entity)),
            )
        else:
            _settle_interruptible_member(entity, plan, seconds, start_tick, commits)
        _reconcile_sleep_receipt(entity, start_tick + seconds)
    if plan.record is not None:
        plan.record.extend(commits)
    return commits


def _awake_practice_seconds(
    plan: MentalPlan | None,
    seconds: int,
    start_tick: int,
    sleep_offsets: dict[int, int] | None = None,
) -> dict[int, int] | None:
    """The actual awake seconds each member may settle study over.

    A body that starts asleep earns no practice for the sleeping portion; a
    pre-existing voluntary deadline leaves its awake remainder eligible. A
    body whose receipt is missing or corrupt earns no study time and keeps its
    standing booking.
    """
    if plan is None:
        return None
    eligible: dict[int, int] = {}
    for entity in plan.scope:
        if getattr(entity, "_is_deleted", False) or _is_dead(entity):
            continue
        state = _mental_state_or_none(entity)
        if state is None:
            eligible[id(entity)] = seconds
            continue
        if plan.activity_for(entity) is not FatigueActivity.SLEEP:
            eligible[id(entity)] = seconds
            continue
        if state.posture is SleepPosture.VOLUNTARY:
            offset = (sleep_offsets or {}).get(id(entity))
            if offset is None:
                continue
            awake_seconds = max(0, seconds - offset)
            if awake_seconds > 0:
                eligible[id(entity)] = awake_seconds
    return eligible


def _settle_boundary_stages(start_tick: int, end_tick: int, entities: tuple[Any, ...]) -> list[ScheduledEvent]:
    events: list[ScheduledEvent] = []
    start_day, end_day = start_tick // _DAY_SECONDS, end_tick // _DAY_SECONDS
    for day in range(start_day + 1, end_day + 1):
        for entity in entities:
            if getattr(entity, "sexual", None) is not None:
                reset_daily_counters(entity)
        events.append(ScheduledEvent("daily_reset", day * _DAY_SECONDS, {}))
    for kind in _STAGE_ORDER[5:]:
        registration = _EVENT_SOURCES.get(kind)
        if registration is not None:
            interactive = registration.next_boundary is not None
            for event in registration.settle(start_tick, end_tick):
                events.append(
                    ScheduledEvent(
                        event.kind,
                        event.due_tick,
                        event.payload,
                        interactive=interactive or event.interactive,
                    )
                )
    return events


def _run_stages(
    clock: "WorldClock",
    seconds: int,
    source: AdvanceSource,
    entities: tuple[Any, ...],
    mental: MentalPlan | None = None,
) -> list[ScheduledEvent]:
    sleep_offsets = _voluntary_sleep_offsets(mental, clock.tick)
    practice_eligible = _awake_practice_seconds(
        mental, seconds, clock.tick, sleep_offsets
    )
    _settle_gauge_regen(entities, seconds)
    events: list[ScheduledEvent] = []
    if source is not AdvanceSource.COMBAT:
        _settle_mental(seconds, mental, clock.tick, sleep_offsets)
        _settle_buffs_and_decay(entities, seconds, start_tick=clock.tick)
        events.extend(
            _practice_settlement(
                entities, seconds, source, clock.tick + seconds, practice_eligible
            )
        )
        # 聖光涓流 (saintess-vessel D2b): the holder's idle-band pin/oscillation
        # runs exactly once per advance — NOT inside the per-quantum settlement
        # loop, which the pending-work guard would early-exit before (a fully
        # idle holder has no other pending work) and which would draw up to
        # 180 steps in one sleep-length advance. Non-combat sources only,
        # matching the loop's own combat posture, and only when time actually
        # passed (a zero-second advance mutates no world state and must not
        # fluctuate the gauge either). The resulting tick is the post-advance
        # value the caller assigns after this function returns; the direction
        # draw is a stateless hash of it, so a rolled-back and retried
        # advance recomputes the identical draw.
        if seconds > 0:
            resulting_tick = clock.tick + seconds
            for entity in entities:
                saintess_trickle_step(entity, resulting_tick)
    events.extend(_settle_boundary_stages(clock.tick, clock.tick + seconds, entities))
    return events


# Durable attribute surfaces an advance can write on a caller-supplied entity:
# the shared entity-snapshot set (world/rules/action.py) plus the
# sexual-decay accumulators, so a rolled-back advance restores every cache.
_ADVANCE_ENTITY_SURFACES: tuple[tuple[str, str | None], ...] = (
    ("traits", "traits"),
    ("disguised_stats", None),
    ("disguise_placed_by_cast", None),
    ("sexual_traits", "traits"),
    ("virgin", "sexual_state"),
    ("experience_types", "sexual_state"),
    ("climax_turns", "sexual_state"),
    ("pending_climax_extension", "sexual_state"),
    ("buffs", None),
    ("skill_grants", None),
    # Cross-lineage unlocks write db.skills on the booked-practice stage; the
    # advance rollback restores it with every other durability surface so a
    # failed advance undoes the grant its award triggered.
    ("skills", None),
    ("skill_proficiency", None),
    ("skill_practice_day", None),
    ("practice_booking", None),
) + FATIGUE_ATTRIBUTE_SURFACES + SLEEP_RECEIPT_SURFACES + tuple(
    (f"decay_elapsed__{field}", "sexual_state") for field in DECAY_CONFIG
)


def _snapshot_clock_tick(clock: "WorldClock") -> tuple[int, tuple[bool, Any] | None]:
    """Snapshot the in-memory tick and the persisted tick attribute."""
    script = getattr(clock, "_script", None)
    tick_snapshot = (
        attribute_snapshot(script, "tick") if script is not None else None
    )
    return clock.tick, tick_snapshot


def _restore_clock_tick(
    clock: "WorldClock",
    snapshot: tuple[int, tuple[bool, Any] | None],
) -> None:
    """Restore the in-memory and persisted tick after a rolled-back advance."""
    in_memory_tick, tick_snapshot = snapshot
    clock.tick = in_memory_tick
    script = getattr(clock, "_script", None)
    if script is not None and tick_snapshot is not None:
        restore_attribute_best_effort(script, "tick", tick_snapshot)


def validate_advance_sleep_receipts(
    scope: Iterable[Any], mental_scope: Iterable[Any] = ()
) -> None:
    """Reject a corrupt accepted-sleep record before any resource or time write.

    A malformed receipt is an integrity failure: the advance fails closed
    instead of refilling, waking or migrating the body. An absent receipt on a
    voluntary body is a synthetic/legacy state, not a repair request; it is
    handled as "no plan" by settlement and never written here.
    """
    for entity in tuple(scope) + tuple(mental_scope):
        if getattr(entity, "_is_deleted", False):
            continue
        attributes = getattr(entity, "attributes", None)
        if attributes is None or not callable(getattr(attributes, "has", None)):
            continue
        read_sleep_receipt(entity)  # raises SleepReceiptError on a malformed value


def build_advance_snapshot_registry(
    clock: "WorldClock",
    seconds: int,
    source: AdvanceSource,
    entities: Iterable[Any],
    *,
    mental_scope: Iterable[Any] = (),
) -> dict[int, SurfaceSnapshot]:
    """Build the merged pre-advance snapshot registry, keyed by object id.

    Merges, by object identity: (a) the existing caller-entity surfaces
    (``_ADVANCE_ENTITY_SURFACES``, unchanged) for the ordinary resource scope
    and the explicit ``mental_scope`` (the present party, wider than a rite's
    narrow resource scope), then (b) every registered stage kind's
    advance-surface contract in ``_STAGE_ORDER[5:]`` order. A caller-supplied
    entity that a contract also discovers (a player with a due quest, a
    schedule-tagged NPC) is snapshotted once with the union of surfaces. Kinds
    registered without a contract are skipped entirely, so plain advances
    never run contract DB queries; a raising contract fails the advance before
    any write (fail-closed, no partial state). Enclosing outer owners SHALL
    pass their resolved mental scope here so a post-advance failure restores
    mental-only members too.

    This is the outer-owner seam: an outer ``transaction.atomic()`` wrapping
    ``advance()`` (the movement and cast settlement changes) SHALL build this
    registry before its transaction opens and restore it together with the
    clock-tick snapshot after an outer-commit failure, so callback-owned
    surfaces are covered whichever boundary fails.

    ``seconds`` is the whole planned window, which may exceed the one-day
    single-call advance bound when an authored movement edge is that long;
    :meth:`WorldClock.advance_bounded` builds this registry once for the full
    window and then advances it in bounded pieces inside one transaction.
    """
    registry: dict[int, SurfaceSnapshot] = {}

    def _snapshot(entity: Any) -> None:
        if not hasattr(entity, "attributes"):
            return
        registry[id(entity)] = SurfaceSnapshot(
            attributes={
                (key, category): attribute_snapshot(entity, key, category)
                for key, category in _ADVANCE_ENTITY_SURFACES
            }
        )

    for entity in entities:
        _snapshot(entity)
    for entity in mental_scope:
        if id(entity) not in registry:
            _snapshot(entity)
    for kind in _STAGE_ORDER[5:]:
        registration = _EVENT_SOURCES.get(kind)
        if registration is None or registration.surfaces is None:
            continue
        for obj_id, snapshot in registration.surfaces(clock.tick, clock.tick + seconds).items():
            existing = registry.get(obj_id)
            if existing is None:
                registry[obj_id] = snapshot
            else:
                existing.attributes.update(snapshot.attributes)
                if snapshot.location is not None:
                    existing.location = snapshot.location
    return registry


def _flush_deleted_instance(obj: Any) -> None:
    """Force a cached-but-deleted instance out of the idmapper cache.

    ``delete()`` evicts only when ``at_idmapper_flush()`` returns True, which
    ``TypedObject`` overrides to False when the object holds any NAttribute,
    so a deleted instance can survive in the cache with ``pk = None``. The
    next fetch must re-read the rolled-back rows, so the entry is removed by
    identity from the shared instance cache.
    """
    from evennia.objects.models import ObjectDB

    cache = getattr(ObjectDB, "__instance_cache__", None)
    if cache is None:
        return
    for key, instance in list(cache.items()):
        if instance is obj:
            del cache[key]


def _restore_advance_location(obj: Any, target_pk: int) -> None:
    """Re-point one moved object at its pre-advance room after a rollback.

    The target is re-fetched by its snapshot pk: after the rollback the rows
    are back, and a cached-but-deleted target instance is flushed first so the
    fetch returns a fresh live object. The location setter reconciles the
    source and destination rooms' contents caches; the re-fetched room's
    contents cache is then reset so the next read agrees with the database. A
    vanished target is skipped with a bounded diagnostic.
    """
    from evennia.objects.models import ObjectDB

    # A deleted instance that survived eviction stays in the cache under its
    # ORIGINAL pk key (Django nulls ``pk`` only after the collector finishes,
    # so the cached entry can no longer be found by comparing ``pk``); flush
    # it by key so the fetch below re-reads the rolled-back rows.
    cache = getattr(ObjectDB, "__instance_cache__", None)
    if cache is not None:
        stale = cache.get(target_pk)
        if stale is not None and getattr(stale, "_is_deleted", False):
            _flush_deleted_instance(stale)
    target = ObjectDB.objects.filter(id=target_pk).first()
    if target is None:
        log_warn(
            "rollback_restore_failed",
            context={
                "stage": "advance_location",
                "obj": str(obj),
                "key": f"location:#{target_pk}",
                "reason": "room vanished after rollback",
            },
        )
        return
    obj.location = target
    target.contents_cache.clear()


def _restore_registry_attribute(
    obj: Any,
    key: str,
    category: str | None,
    snapshot: tuple[bool, Any],
    *,
    stage: str = "advance_registry_attribute",
) -> None:
    """Restore one registry attribute, degrading to a cache reset on failure.

    Writes the snapshot value directly instead of through the shared
    ``restore_attribute`` deepcopy: a contract surface may embed live database
    objects (the instance contract's ``owned_entities``), which plain
    ``deepcopy`` cannot copy; Evennia's ``attributes.add`` re-encodes through
    ``dbserialize`` and handles them natively. The ``stage`` tag identifies
    the rollback boundary in the failure event's context.
    """
    existed, value = snapshot
    try:
        if existed:
            obj.attributes.add(key, value, category=category)
        else:
            obj.attributes.remove(key, category=category)
    except Exception as error:
        try:
            obj.attributes.reset_cache()
        except Exception:  # observability: ignore R2: cache invalidation is best-effort; the restore failure itself is logged below
            pass
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={
                "stage": stage,
                "obj": str(obj),
                "key": key,
                "category": category,
            },
        )


def _restore_advance_registry(
    registry: dict[int, SurfaceSnapshot],
    entities: Iterable[Any],
) -> None:
    """Restore every registry surface after a rolled-back advance.

    For each registry entry: an object deleted during settlement is skipped
    (its still-cached deleted instance, when NAttributes kept it, is flushed
    so the next fetch re-reads the rolled-back rows); each attribute surface
    is restored; an optional location surface re-fetches the pre-advance room
    by its snapshot pk and assigns it through the location setter. Objects are
    resolved from the caller's own entities first -- a caller-supplied
    instance evicted from the idmapper without deletion (a theoretical
    maintenance path; nothing flushes the cache inside a synchronous
    ``advance()``) is still restored from the caller's reference -- then from
    the object *and script* idmapper caches for contract-discovered objects,
    because a declared surface may live on either model. Caller-scope entities
    finish with the existing trait/sexual cache refresh, and instances the
    rolled-back transaction created are evicted last.
    """
    from evennia.objects.models import ObjectDB
    from evennia.scripts.models import ScriptDB

    objects: dict[int, Any] = {id(obj): obj for obj in entities}
    objects.update(
        {id(obj): obj for obj in ObjectDB.get_all_cached_instances()}
    )
    objects.update(
        {id(obj): obj for obj in ScriptDB.get_all_cached_instances()}
    )
    for obj_id, snapshot in registry.items():
        obj = objects.get(obj_id)
        if obj is None:
            continue
        if getattr(obj, "_is_deleted", False):
            _flush_deleted_instance(obj)
            continue
        for key, category in snapshot.attributes:
            _restore_registry_attribute(
                obj,
                key,
                category,
                snapshot.attributes[(key, category)],
                stage="advance_registry_attribute",
            )
        if snapshot.location is not None:
            existed, target_pk = snapshot.location
            try:
                if existed:
                    _restore_advance_location(obj, target_pk)
                else:
                    obj.location = None
            except Exception as error:
                log_warn(
                    "rollback_restore_failed",
                    exc=error,
                    context={
                        "stage": "advance_location",
                        "obj": str(obj),
                        "key": "location",
                    },
                )
    for entity in entities:
        if not hasattr(entity, "attributes"):
            continue
        _refresh_advance_entity_caches(entity)
    _flush_rolled_back_instances()


def _refresh_advance_entity_caches(entity: Any) -> None:
    """Drop stale in-memory trait/sexual caches so the next read matches the DB."""
    try:
        entity.traits.trait_data = entity.attributes.get(
            "traits", default={}, category="traits"
        )
        entity.traits._cache.clear()
    except Exception as error:
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={"stage": "trait_caches", "obj": str(entity), "key": "traits"},
        )
    try:
        entity.__dict__.pop("sexual", None)
    except Exception as error:
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={"stage": "sexual_cache", "obj": str(entity), "key": "sexual"},
        )


def _flush_rolled_back_instances() -> None:
    """Evict cached instances whose rows the rolled-back advance removed.

    Evennia's idmapper is not transaction-aware, and a stage that *creates*
    objects (monster-site-placement's settlement) has no pre-advance snapshot
    to restore: the row is gone with the transaction while the instance stays
    cached, and a later row that reuses that primary key would be served as the
    stale object. This runs only on the failure path, where the number of
    cached objects is small, and flushes exactly the entries the database no
    longer backs.
    """
    from evennia.objects.models import ObjectDB

    cache = getattr(ObjectDB, "__instance_cache__", None)
    if cache is None:
        return
    for key, instance in list(cache.items()):
        if key is None or getattr(instance, "_is_deleted", False):
            continue
        if not ObjectDB.objects.filter(pk=key).exists():
            instance.flush_from_cache(force=True)


@dataclass
class WorldClock:
    """The sole mutable driver of elapsed game time."""

    tick: int = 0

    @property
    def calendar(self) -> WorldDateTime:
        return WorldDateTime.from_tick(self.tick)

    def advance(
        self,
        seconds: int,
        source: AdvanceSource,
        entities: Iterable[Any],
        *,
        mental: MentalPlan | None = None,
    ) -> list[ScheduledEvent]:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        if seconds > MAX_ADVANCE_SECONDS:
            raise ClockAdvanceBoundError(
                f"advance of {seconds}s exceeds the {MAX_ADVANCE_SECONDS}s bound"
            )
        scope = tuple(entities)
        mental_scope = mental.scope if mental is not None else ()
        validate_advance_sleep_receipts(scope, mental_scope)
        registry = build_advance_snapshot_registry(
            self, seconds, source, scope, mental_scope=mental_scope
        )
        tick_snapshot = _snapshot_clock_tick(self)
        tick_from = self.tick
        try:
            with transaction.atomic():
                events = _run_stages(self, seconds, source, scope, mental=mental)
                self.tick += seconds
                persist = getattr(self, "_persist", None)
                if persist is not None:
                    persist(self.tick)
                # Boundary event fires only on the OUTERMOST durable commit:
                # advance() runs nested inside item/combat transactions, so a
                # savepoint exit alone must not leave a clock_advance line
                # behind a rollback (on_commit callbacks are discarded then).
                tick_to = self.tick
                # World-time is a dialogue eligibility source independent of
                # the action's entity scope: an idle owner in another room may
                # depend on the new daypart. Only a committed daypart crossing
                # schedules anything, and the discovery plus projection run in
                # the commit callback from the final tick.
                if (
                    seconds > 0
                    and _daypart_index(tick_from) != _daypart_index(tick_to)
                ):
                    from world.rules.dialogue_availability import (
                        queue_dialogue_refresh,
                        session_bearing_dialogue_owners,
                    )

                    queue_dialogue_refresh(
                        session_bearing_dialogue_owners(), cause="world_time"
                    )
                transaction.on_commit(
                    lambda: log_info(
                        "clock_advance",
                        context={
                            "tick_from": tick_from,
                            "tick_to": tick_to,
                            "scope": len(scope),
                        },
                    )
                )
        except Exception:
            _restore_clock_tick(self, tick_snapshot)
            _restore_advance_registry(registry, scope)
            raise
        return events

    def advance_bounded(
        self,
        seconds: int,
        source: AdvanceSource,
        entities: Iterable[Any],
        *,
        mental: MentalPlan | None = None,
    ) -> list[ScheduledEvent]:
        """Advance any duration inside the one-call bound, as one window.

        A duration at or below :data:`MAX_ADVANCE_SECONDS` is exactly
        ``advance()``. A longer committed duration — a multi-day authored
        movement edge — is split into bounded internal advances that all stay
        inside one transaction, while the pre-advance snapshot registry and the
        clock-tick snapshot are built once for the **full** window. A failure
        in any piece restores that whole window, so callers never observe a
        partially advanced traversal, and the committed duration is never
        clipped to a daily cap.
        """

        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        if seconds <= MAX_ADVANCE_SECONDS:
            return self.advance(seconds, source, entities, mental=mental)
        scope = tuple(entities)
        mental_scope = mental.scope if mental is not None else ()
        validate_advance_sleep_receipts(scope, mental_scope)
        registry = build_advance_snapshot_registry(
            self, seconds, source, scope, mental_scope=mental_scope
        )
        tick_snapshot = _snapshot_clock_tick(self)
        events: list[ScheduledEvent] = []
        try:
            with transaction.atomic():
                remaining = seconds
                while remaining > 0:
                    step = min(remaining, MAX_ADVANCE_SECONDS)
                    events.extend(
                        self.advance(step, source, scope, mental=mental)
                    )
                    remaining -= step
        except Exception:
            _restore_clock_tick(self, tick_snapshot)
            _restore_advance_registry(registry, scope)
            raise
        return events


class WorldClockScript(DefaultScript):
    """Persistent attribute storage for the player-driven world tick."""

    def at_script_creation(self) -> None:
        self.db.tick = 0


def get_world_clock() -> WorldClock:
    """Find or create the non-repeating persisted clock singleton."""
    matches = search_script("world_clock")
    script = matches[0] if matches else create_script(
        WorldClockScript, key="world_clock", persistent=True, interval=0, repeats=0
    )
    clock = WorldClock(int(script.db.tick or 0))
    clock._script = script
    clock._persist = lambda tick: setattr(script.db, "tick", tick)
    return clock


def read_world_clock() -> WorldClock | None:
    """Return the existing world-clock singleton or ``None`` without creating.

    Presentation reads only through this accessor; it never calls
    ``get_world_clock``, which would create the Script. A missing singleton is
    reported as absence so presentation can fail safely.
    """
    matches = search_script("world_clock")
    if not matches:
        return None
    script = matches[0]
    clock = WorldClock(int(script.db.tick or 0))
    clock._script = script
    clock._persist = lambda tick: setattr(script.db, "tick", tick)
    return clock


def settle_combat_result(result: Any, entities: Iterable[Any]) -> list[ScheduledEvent]:
    """Settle a reported combat duration through the combat source gate."""
    return get_world_clock().advance(result.total_seconds, AdvanceSource.COMBAT, entities)
