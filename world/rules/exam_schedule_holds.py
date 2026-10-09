"""Persisted examiner schedule holds, independently usable by exam lifecycle.

The lifecycle supplies globally unique exam IDs and restores the host before
release. It must snapshot these surfaces before an enclosing transaction and
restore them after its rollback; nested savepoints cannot restore outer caches.
Mutation calls belong to the serialized deterministic game loop, like clock
settlement. Concurrent worker/web-thread calls are outside this API contract.
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from typing import Any

from django.db import transaction

from typeclasses.npcs import NPC
from world.observability import log_info
from world.rules.clock import (
    ScheduledEvent,
    SurfaceSnapshot,
    _restore_advance_registry,
    read_world_clock,
)
from world.rules.surfaces import attribute_snapshot

HOLD_ATTRIBUTE = "exam_schedule_hold"


class ExamScheduleHoldError(ValueError):
    """The hold cannot be safely mutated or released."""


@dataclass(frozen=True)
class ExamScheduleHold:
    schema_version: int
    host_id: int
    exam_id: str
    start_tick: int
    held_through_tick: int
    consumed_through: tuple[int, int] | None = None
    released: bool = False


@dataclass(frozen=True)
class ExamScheduleHoldRead:
    """Known absence has ``hold=None``; indeterminate reads carry a reason."""

    known: bool
    hold: ExamScheduleHold | None = None
    reason: str | None = None


def _tick(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _host(npc: Any) -> None:
    if not isinstance(npc, NPC) or not _tick(npc.pk) or npc.pk == 0:
        raise ExamScheduleHoldError("hold requires a persistent NPC")


def read_exam_schedule_hold(npc: Any) -> ExamScheduleHoldRead:
    """Read without writes; corrupt/foreign records fail closed for readers."""
    try:
        _host(npc)
        raw = npc.attributes.get(HOLD_ATTRIBUTE)
        if raw is None and not npc.attributes.has(HOLD_ATTRIBUTE):
            return ExamScheduleHoldRead(True)
        fields = set(ExamScheduleHold.__dataclass_fields__)
        if not isinstance(raw, Mapping) or set(raw) != fields:
            return ExamScheduleHoldRead(False, reason="exam_hold_invalid_shape")
        raw = dict(raw)
        if (
            type(raw["schema_version"]) is not int or raw["schema_version"] != 1
            or type(raw["host_id"]) is not int or raw["host_id"] != npc.pk
            or not isinstance(raw["exam_id"], str) or not raw["exam_id"].strip()
            or not _tick(raw["start_tick"]) or not _tick(raw["held_through_tick"])
            or raw["held_through_tick"] < raw["start_tick"]
            or type(raw["released"]) is not bool
        ):
            return ExamScheduleHoldRead(False, reason="exam_hold_invalid_identity_or_timing")
        consumed = raw["consumed_through"]
        if consumed is not None:
            if (
                not raw["released"]
                or not isinstance(consumed, (list, tuple)) or len(consumed) != 2
                or not all(_tick(value) for value in consumed)
                or not raw["start_tick"] <= consumed[0] <= raw["held_through_tick"]
            ):
                return ExamScheduleHoldRead(False, reason="exam_hold_invalid_consumed_through")
            raw["consumed_through"] = tuple(consumed)
        return ExamScheduleHoldRead(True, ExamScheduleHold(**raw))
    except Exception:
        # observability: ignore R2: read-only total availability seam exposes a named indeterminate result
        return ExamScheduleHoldRead(False, reason="exam_hold_unreadable")


def snapshot_exam_schedule_hold_surfaces(npc: Any) -> dict[int, SurfaceSnapshot]:
    """Snapshot hold, schedule state and location for an outer lifecycle write."""
    _host(npc)
    location = npc.location
    return {id(npc): SurfaceSnapshot(
        attributes={
            (key, None): attribute_snapshot(npc, key)
            for key in (HOLD_ATTRIBUTE, "schedule_state")
        },
        location=(True, int(location.pk)) if location is not None else (False, 0),
    )}


def restore_exam_schedule_hold_surfaces(
    npc: Any, snapshot: dict[int, SurfaceSnapshot]
) -> None:
    """Restore after database rollback, including room contents caches."""
    _restore_advance_registry(snapshot, (npc,))


def _write(npc: Any, hold: ExamScheduleHold, event: str) -> None:
    npc.attributes.add(HOLD_ATTRIBUTE, asdict(hold))
    context = {
        "host_id": hold.host_id, "exam_id": hold.exam_id,
        "start_tick": hold.start_tick, "tick": hold.held_through_tick,
        "consumed_through": hold.consumed_through,
    }
    transaction.on_commit(lambda: log_info(event, context=context))


def _known(npc: Any) -> ExamScheduleHold | None:
    _host(npc)
    result = read_exam_schedule_hold(npc)
    if not result.known:
        raise ExamScheduleHoldError(result.reason)
    return result.hold


def _world_tick() -> int:
    clock = read_world_clock()
    if clock is None:
        raise ExamScheduleHoldError("world clock is unavailable")
    return clock.tick


def begin_exam_schedule_hold(npc: Any, exam_id: str, start_tick: int) -> ExamScheduleHold:
    """Begin at the current persisted tick; repeat only the same active begin.

    Only the latest completed ID is retained. Callers must never reuse IDs.
    """
    prior = _known(npc)
    if not isinstance(exam_id, str) or not exam_id.strip() or not _tick(start_tick):
        raise ExamScheduleHoldError("invalid examination identity or start tick")
    if prior is not None and not prior.released:
        if prior.exam_id == exam_id and prior.start_tick == start_tick:
            return prior
        raise ExamScheduleHoldError("host is owned by another examination")
    if prior is not None and prior.exam_id == exam_id:
        raise ExamScheduleHoldError("completed examination identity cannot be reused")
    if start_tick != _world_tick():
        raise ExamScheduleHoldError("hold must begin at the current world tick")
    hold = ExamScheduleHold(1, int(npc.pk), exam_id, start_tick, start_tick)
    snapshot = snapshot_exam_schedule_hold_surfaces(npc)
    try:
        with transaction.atomic():
            _write(npc, hold, "exam_schedule_hold_started")
    except Exception:
        restore_exam_schedule_hold_surfaces(npc, snapshot)
        raise
    return hold


def consult_exam_schedule_hold(
    npc: Any, end_tick: int
) -> tuple[bool, tuple[int, int] | None]:
    """Return deferral and consumed cursor; marker failure aborts the advance."""
    result = read_exam_schedule_hold(npc)
    if not result.known:
        return True, None
    hold = result.hold
    if hold is None:
        return False, None
    if hold.released:
        return False, hold.consumed_through
    if end_tick > hold.held_through_tick:
        _write(npc, replace(hold, held_through_tick=end_tick), "exam_schedule_hold_extended")
    return True, hold.consumed_through


def release_exam_schedule_hold(
    npc: Any, exam_id: str, through_tick: int
) -> list[ScheduledEvent]:
    """Replay through elapsed time once, without advancing the world clock.

    A failed traversal is consumed just like an ordinary schedule skip.
    Corrupt schedule storage leaves the active hold intact for explicit repair.
    """
    from world.rules.npc_schedules import (
        _settle_occurrence, _skip_diagnostic, due_occurrences, parse_stored_schedule,
    )
    from world.rules.service_gate import schedule_silenced

    hold = _known(npc)
    if hold is None or hold.exam_id != exam_id:
        raise ExamScheduleHoldError("examination does not own this host hold")
    if not _tick(through_tick) or not hold.held_through_tick <= through_tick <= _world_tick():
        raise ExamScheduleHoldError("release must cover the hold within elapsed world time")
    if hold.released:
        return []
    silenced = schedule_silenced(npc)
    parsed = parse_stored_schedule(npc)
    if parsed is None and npc.db.schedule is not None:
        raise ExamScheduleHoldError("host schedule is indeterminate")
    occurrences = due_occurrences(parsed, hold.start_tick, through_tick) if parsed else []
    snapshot = snapshot_exam_schedule_hold_surfaces(npc)
    events: list[ScheduledEvent] = []
    try:
        with transaction.atomic():
            consumed = hold.consumed_through
            for due_tick, index, entry in occurrences:
                if consumed is not None and (due_tick, index) <= consumed:
                    continue
                if not silenced:
                    # Retain the ordinary source's per-entry exception isolation.
                    try:
                        events.extend(_settle_occurrence(npc, parsed, due_tick, index, entry))
                    except Exception as exc:  # observability: ignore R2: shared bounded skip diagnostic
                        _skip_diagnostic(npc, due_tick, index, f"unexpected failure: {exc}")
                consumed = (due_tick, index)
            _write(npc, replace(
                hold, held_through_tick=through_tick,
                consumed_through=consumed, released=True,
            ), "exam_schedule_hold_released")
    except Exception:
        restore_exam_schedule_hold_surfaces(npc, snapshot)
        raise
    return events
