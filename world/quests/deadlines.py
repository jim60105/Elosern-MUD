"""World-clock deadline settlement for active quests (D-7)."""

from typing import Any

from evennia.utils.logger import log_warn

from typeclasses.characters import PlayerCharacter
from world.rules.clock import ScheduledEvent

from .runtime import (
    QuestDataError,
    QuestState,
    fail_record,
    read_records,
)
from .transitions import apply_quest_log_replacement, release_stage_binding


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
            log_warn(f"quest_deadlines: {player.key}: malformed quest log: {error}")
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
            log_warn(f"quest_deadlines: {player.key}: settlement failed: {error}")
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