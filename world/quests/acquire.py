"""ACQUIRE quest progress from deterministic inventory-plan additions (guild-economy D-5).

An ACQUIRE objective advances only from the positive additions of a committed
inventory plan. The computation lives in the quest package so quest-record
lifecycle stays quest-owned: the equipment planner asks this module for a
replacement; reward and shop operations reuse the same helper inside their own
surrounding transaction.
"""

from collections import Counter
from dataclasses import replace
from typing import Any

from .definitions import ObjectiveKind
from .runtime import (
    QuestState,
    definition_for,
    fulfill_record,
    read_records,
)
from .transitions import release_stage_binding


def _matching_active_stages(
    entity: Any,
    additions: Counter,
) -> list[Any]:
    """Return active records whose current ACQUIRE objective item matches."""
    records = read_records(entity)
    matching: list[Any] = []
    for record in records:
        if record.state is not QuestState.IN_PROGRESS:
            continue
        definition = definition_for(record)
        objective = definition.stages[record.stage_index].objective
        if objective.kind is not ObjectiveKind.ACQUIRE:
            continue
        if objective.item_key not in additions:
            continue
        matching.append((record, definition))
    return matching


def compute_acquire_replacement(
    entity: Any,
    additions: Any,
) -> tuple[list[Any], tuple[Any, ...]] | None:
    """Compute the quest-log replacement for one plan's positive additions.

    Returns ``(new_records, pin_operations)`` when at least one active ACQUIRE
    objective gained progress, else ``None``. Each matching quest advances at
    most one stage; surplus quantity is not carried into the next stage.
    Counter semantics allow repeated item keys to satisfy repeated quantities
    without inventing fractions.
    """
    if isinstance(additions, Counter):
        counts = additions
    else:
        counts = Counter(additions)

    matching = _matching_active_stages(entity, counts)
    if not matching:
        return None

    replacements: dict[str, Any] = {}
    pin_operations: list[Any] = []
    for record, definition in matching:
        objective = definition.stages[record.stage_index].objective
        available = counts.get(objective.item_key, 0)
        remaining = objective.quantity - record.stage_progress
        gained = min(available, remaining)
        if gained < 1:
            continue
        new_progress = record.stage_progress + gained
        if new_progress >= objective.quantity:
            replacements[record.quest_id] = fulfill_record(record, definition)
            pin_operations.extend(release_stage_binding(entity, record))
        else:
            replacements[record.quest_id] = replace(
                record,
                stage_progress=new_progress,
            )

    if not replacements:
        return None
    return (
        [replacements.get(record.quest_id, record) for record in read_records(entity)],
        tuple(pin_operations),
    )