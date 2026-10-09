"""Read-only planned service-capable NPC presence intervals (planned-npc-service-windows).

Exposes the single rules-core reader ``read_next_planned_service_interval``:
given a persistent NPC, a destination room or anchor key, and a world tick,
projects the NPC's authoritative schedule occurrences to find the next
[start_tick, end_tick) service-capable presence window at that destination,
or an explicit named unavailable reason.

Guarantees:
- READ-ONLY: Never creates a clock, mutates NPC attributes, tags, locations,
  resources, affinity, or examination records.
- BOUNDED PROJECTION: Searches from actual location and schedule_state through
  the remainder of the current cycle plus exactly one complete future cycle
  (cycle-grid aligned: ``(cycle_idx + 2) * cycle_seconds``).
- INTERVALS: [start_tick, end_tick) are start-inclusive and end-exclusive.
  At ``tick == end_tick``, the window is closed.
- SERVICE BLOCKING: States in ``_BLOCKING_STATES`` (busy, resting) block service.
  A move entry followed at the same tick by busy delays window start until a
  non-blocking state entry opens.
- ACTUAL LOCATION AUTHORITY: If the NPC is absent when an earlier arrival was
  scheduled, that portion cannot provide presence; future arrival or unavailable
  is returned. An arrival due at the exact current tick remains planned until
  actual location confirms it.
- FAIL-CLOSED INDETERMINATE DATA: Missing/malformed schedule, missing clock,
  unresolved destination, active or indeterminate exam hold, and silenced
  schedules yield named unavailable reasons without revealing private routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules import npc_schedules
from world.rules.clock import read_world_clock
from world.rules.exam_schedule_holds import read_exam_schedule_hold
from world.rules.npc_schedules import (
    _BLOCKING_STATES,
    due_occurrences,
    parse_stored_schedule,
)
from world.rules.service_gate import schedule_silenced

# Named failure / unavailability reasons
REASON_INVALID_HOST = "invalid_host"
REASON_MISSING_WORLD_CLOCK = "missing_world_clock"
REASON_INVALID_TICK = "invalid_tick"
REASON_UNRESOLVED_DESTINATION = "unresolved_destination"
REASON_SCHEDULE_SILENCED = "schedule_silenced"
REASON_MISSING_SCHEDULE = "missing_schedule"
REASON_INDETERMINATE_SCHEDULE = "indeterminate_schedule"
REASON_ACTIVE_EXAM_HOLD = "active_exam_hold"
REASON_UNCONFIRMABLE = "unconfirmable"

UNAVAILABLE_REASONS = frozenset({
    REASON_INVALID_HOST,
    REASON_MISSING_WORLD_CLOCK,
    REASON_INVALID_TICK,
    REASON_UNRESOLVED_DESTINATION,
    REASON_SCHEDULE_SILENCED,
    REASON_MISSING_SCHEDULE,
    REASON_INDETERMINATE_SCHEDULE,
    REASON_ACTIVE_EXAM_HOLD,
    REASON_UNCONFIRMABLE,
    # Forwarded hold read reasons
    "exam_hold_invalid_shape",
    "exam_hold_invalid_identity_or_timing",
    "exam_hold_invalid_consumed_through",
    "exam_hold_unreadable",
})


@dataclass(frozen=True)
class PlannedServiceInterval:
    """A planned [start_tick, end_tick) service window."""

    start_tick: int
    end_tick: int


@dataclass(frozen=True)
class PlannedServiceWindowResult:
    """Read result: either a valid interval or a named unavailable reason."""

    interval: PlannedServiceInterval | None = None
    reason: str | None = None

    @property
    def available(self) -> bool:
        return self.interval is not None


def read_next_planned_service_interval(
    npc: Any,
    destination: Any,
    current_tick: int | None = None,
) -> PlannedServiceWindowResult:
    """Read the next planned service-capable interval for ``npc`` at ``destination``.

    Args:
        npc: Persistent NPC instance.
        destination: Room instance or anchor_key string.
        current_tick: Authoritative world tick. If None, read from existing
            world clock (never creating one).

    Returns:
        PlannedServiceWindowResult with interval or a named reason.
    """
    try:
        # 1. Validate NPC
        if not isinstance(npc, NPC) or not isinstance(getattr(npc, "pk", None), int) or npc.pk <= 0:
            return PlannedServiceWindowResult(reason=REASON_INVALID_HOST)

        # 2. Validate current tick
        if current_tick is None:
            clock = read_world_clock()
            if clock is None:
                return PlannedServiceWindowResult(reason=REASON_MISSING_WORLD_CLOCK)
            current_tick = clock.tick
        elif not isinstance(current_tick, int) or isinstance(current_tick, bool) or current_tick < 0:
            return PlannedServiceWindowResult(reason=REASON_INVALID_TICK)

        # 3. Resolve destination room
        dest_room: Any = None
        if isinstance(destination, Room):
            dest_room = destination
        elif isinstance(destination, str) and destination.strip():
            dest_room = npc_schedules._resolve_destination(destination.strip())
        if dest_room is None:
            return PlannedServiceWindowResult(reason=REASON_UNRESOLVED_DESTINATION)

        # 4. Check schedule silencing (companion off-anchor or possessed)
        if schedule_silenced(npc):
            return PlannedServiceWindowResult(reason=REASON_SCHEDULE_SILENCED)

        # 5. Check schedule existence & validity
        raw_schedule = getattr(getattr(npc, "db", None), "schedule", None)
        if raw_schedule is None:
            return PlannedServiceWindowResult(reason=REASON_MISSING_SCHEDULE)

        parsed = parse_stored_schedule(npc)
        if parsed is None:
            return PlannedServiceWindowResult(reason=REASON_INDETERMINATE_SCHEDULE)

        # 6. Check exam schedule hold
        hold_read = read_exam_schedule_hold(npc)
        if not hold_read.known:
            return PlannedServiceWindowResult(reason=hold_read.reason or "exam_hold_unreadable")
        if hold_read.hold is not None and not hold_read.hold.released:
            # Active hold defers settlement indefinitely with no knowable end
            return PlannedServiceWindowResult(reason=REASON_ACTIVE_EXAM_HOLD)

        # 7. Bounded projection
        cycle_seconds = parsed.cycle_seconds
        current_cycle = current_tick // cycle_seconds
        projection_end_tick = (current_cycle + 2) * cycle_seconds

        # Actual current location and schedule_state
        sim_location = getattr(npc, "location", None)
        sim_state = getattr(getattr(npc, "db", None), "schedule_state", None)

        # Cache target room resolutions to avoid repeated DB/model scans
        resolved_rooms: dict[str, Any] = {}

        def get_room(target: str | None) -> Any:
            if not target:
                return None
            if target not in resolved_rooms:
                resolved_rooms[target] = npc_schedules._resolve_destination(target)
            return resolved_rooms[target]

        # An arrival due at the exact current tick remains planned until actual location confirms it.
        # If the host is already at dest_room, any move entry leaving dest_room due at current_tick
        # relocates the host away, ending presence.
        if current_tick > 0:
            occurrences_at_current = due_occurrences(parsed, current_tick - 1, current_tick)
            for _, _, entry in occurrences_at_current:
                if entry.kind == "state":
                    sim_state = entry.state
                elif entry.kind == "move" and sim_location is dest_room:
                    sim_location = get_room(entry.target)
                    sim_state = parsed.default_state

        # Check if host is currently present and service-capable right now
        active_window_start: int | None = None
        if sim_location is dest_room and sim_state not in _BLOCKING_STATES:
            active_window_start = current_tick

        # Collect due occurrences in (current_tick, projection_end_tick]
        occurrences = due_occurrences(parsed, current_tick, projection_end_tick)

        # Group occurrences by due_tick to evaluate intra-tick state transitions
        grouped_occurrences: dict[int, list[Any]] = {}
        for due_tick, entry_idx, entry in occurrences:
            grouped_occurrences.setdefault(due_tick, []).append((entry_idx, entry))

        sorted_ticks = sorted(grouped_occurrences.keys())

        for tick in sorted_ticks:
            tick_entries = grouped_occurrences[tick]

            # Traverse entries at this tick in entry_index order
            for entry_idx, entry in tick_entries:
                if entry.kind == "state":
                    sim_state = entry.state
                elif entry.kind == "move":
                    sim_location = get_room(entry.target)
                    sim_state = parsed.default_state

                now_capable = (sim_location is dest_room) and (sim_state not in _BLOCKING_STATES)

                if active_window_start is not None:
                    if not now_capable:
                        # An active window ended at this tick
                        if active_window_start < tick:
                            return PlannedServiceWindowResult(
                                interval=PlannedServiceInterval(active_window_start, tick)
                            )
                        # Instantaneous or closed at same start tick
                        active_window_start = None
                else:
                    if now_capable:
                        # A new window opened at this tick
                        active_window_start = tick

        # If an active window opened but didn't close before the projection end,
        # the search window cannot confirm its end.
        return PlannedServiceWindowResult(reason=REASON_UNCONFIRMABLE)
    except Exception:
        # Total fail-closed reader safety
        return PlannedServiceWindowResult(reason=REASON_INDETERMINATE_SCHEDULE)
