"""World-clock deadline settlement for active quests (D-7)."""

from typing import Any

from evennia.objects.models import ObjectDB
from world.observability import log_warn

from typeclasses.characters import PlayerCharacter
from world.rules.clock import ScheduledEvent, SurfaceSnapshot

from .runtime import (
    QuestDataError,
    QuestState,
    fail_record,
    read_records,
)
from .transitions import (
    apply_quest_log_replacement,
    release_stage_binding,
    snapshot_pin_reasons,
    snapshot_quest_log,
)


def snapshot_quest_deadline_surfaces(
    start_tick: int, end_tick: int
) -> dict[int, SurfaceSnapshot]:
    """Snapshot the durable surfaces ``settle_quest_deadlines`` may write.

    The advance-surface contract for the ``quest_deadlines`` source: every
    player with a non-empty quest log (whose ``quest_log`` may be replaced)
    plus every room an in-progress record currently binds (whose
    ``pin_reasons`` ``release_stage_binding`` may rewrite). Reuses the shared
    quest-log and pin snapshot handlers so the contract cannot drift from the
    transition layer. Pure read: no attribute, location, or tag changes.
    """
    registry: dict[int, SurfaceSnapshot] = {}
    for player in PlayerCharacter.objects.all_family():
        raw_log = player.db.quest_log
        if not raw_log:
            continue
        registry[id(player)] = SurfaceSnapshot(
            attributes={("quest_log", None): snapshot_quest_log(player)}
        )
        try:
            records = read_records(player)
        except QuestDataError as error:
            log_warn(
                "quest_deadlines_malformed_log",
                context={"char": str(player.pk)},
                exc=error,
            )
            continue
        for record in records:
            if record.state is not QuestState.IN_PROGRESS or record.stage_room_id is None:
                continue
            room = ObjectDB.objects.filter(id=record.stage_room_id).first()
            if room is None:
                continue
            snapshot = registry.get(id(room))
            if snapshot is None:
                registry[id(room)] = SurfaceSnapshot(
                    attributes={("pin_reasons", None): snapshot_pin_reasons(room)}
                )
            else:
                snapshot.attributes[("pin_reasons", None)] = snapshot_pin_reasons(room)
    return registry


def settle_quest_deadlines(start_tick: int, end_tick: int) -> list[ScheduledEvent]:
    """Fail every active record whose deadline is at or before ``end_tick``.

    Each character's complete quest log and pins are replaced atomically or
    left untouched; a malformed log is isolated with a diagnostic so other
    characters still settle. Returns one JSON-safe ``ScheduledEvent`` per
    failed quest.
    """
    events: list[ScheduledEvent] = []
    for player in PlayerCharacter.objects.all_family():
        raw_log = player.db.quest_log
        if not raw_log:
            continue
        try:
            records = read_records(player)
        except QuestDataError as error:
            log_warn(
                "quest_deadlines_malformed_log",
                context={"char": str(player.pk)},
                exc=error,
            )
            continue
        new_records = list(records)
        pin_operations = []
        due: list[Any] = []
        for index, record in enumerate(records):
            if (
                record.state is not QuestState.IN_PROGRESS
                or record.deadline_tick is None
            ):
                continue
            if record.deadline_tick > end_tick:
                continue
            due.append(record)
            new_records[index] = fail_record(record, "deadline_expired")
            pin_operations.extend(release_stage_binding(player, record))
        if not due:
            continue
        try:
            apply_quest_log_replacement(player, new_records, pin_operations)
        except Exception as error:
            log_warn(
                "quest_deadline_settlement_failed",
                context={"char": str(player.pk)},
                exc=error,
            )
            continue
        events.extend(
            ScheduledEvent(
                "quest_deadline_expired",
                end_tick,
                {
                    "character_id": int(player.pk),
                    "quest_id": record.quest_id,
                    "definition_key": record.definition_key,
                },
            )
            for record in due
        )
    return events