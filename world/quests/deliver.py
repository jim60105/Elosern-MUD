"""DELIVER quest progress from committed item transfers.

A DELIVER objective advances only from a committed item transfer in which the
quest holder is the giver, the receiver is the stage's bound recipient, and
the transferred key matches the objective's item_key. The computation lives
in the quest package so quest-record lifecycle stays quest-owned.

The observer is pure: it computes a quest-log replacement and pin operations
without writing state or attributes. There is no public progress-assertion
entry point: delivery progress is reachable only from a committed transfer.
"""

from dataclasses import replace
from typing import Any

from django.db import transaction

from world.observability import log_info
from .definitions import ObjectiveKind
from .runtime import (
    QuestRecord,
    QuestState,
    definition_for,
    fulfill_record_for,
    read_records,
)
from .transitions import release_stage_binding


def _matching_active_stages(
    giver: Any,
    receiver: Any,
    item_key: str,
) -> list[tuple[QuestRecord, Any]]:
    """Return active records whose current DELIVER objective matches the transfer."""
    return [
        (record, definition)
        for record, definition, _objective in iter_bound_deliveries(
            giver, receiver, item_key
        )
        if record.state is QuestState.IN_PROGRESS
    ]


def iter_bound_deliveries(
    giver: Any,
    receiver: Any,
    item_key: str | None,
) -> list[tuple[QuestRecord, Any, Any]]:
    """Return every record whose current stage is a DELIVER objective bound to
    ``receiver`` for ``item_key`` (or for any item when ``item_key`` is
    ``None``), in any record state, in quest-log order.

    The single matching source for both the delivery observer and the
    deterministic hand-over rule, so the two can never disagree on what
    counts as a bound delivery stage.
    """
    receiver_id = getattr(receiver, "pk", None)
    if receiver_id is None:
        return []
    try:
        target_pk = int(receiver_id)
    except (TypeError, ValueError):  # observability: ignore R2: non-integer receiver pk cannot match stored integer target ids
        return []

    bound: list[tuple[QuestRecord, Any, Any]] = []
    for record in read_records(giver):
        definition = definition_for(record)
        objective = definition.stages[record.stage_index].objective
        if objective.kind is not ObjectiveKind.DELIVER:
            continue
        if item_key is not None and objective.item_key != item_key:
            continue
        if target_pk not in record.objective_target_ids:
            continue
        bound.append((record, definition, objective))
    return bound


def select_deliver_stage(
    active: list[tuple[QuestRecord, Any]],
) -> tuple[QuestRecord, Any, int] | None:
    """Select the active stage a hand-over satisfies, with its remaining quantity.

    The lowest remaining quantity wins (ties break in quest-log order), so an
    advertised delivery is always satisfiable by the hand-over that follows it
    and every enabled invocation makes progress. The delivery observer still
    advances every matching active record by ``min(transferred, its own
    remaining)``.
    """
    selected: tuple[QuestRecord, Any, int] | None = None
    for record, definition in active:
        objective = definition.stages[record.stage_index].objective
        remaining = objective.quantity - record.stage_progress
        if selected is None or remaining < selected[2]:
            selected = (record, definition, remaining)
    return selected


def compute_deliver_replacement(
    giver: Any,
    receiver: Any,
    item_key: str,
    quantity: int,
) -> tuple[list[QuestRecord], tuple[Any, ...]] | None:
    """Compute the quest-log replacement for one committed item transfer.

    Returns ``(new_records, pin_operations)`` when at least one active DELIVER
    objective gained progress, else ``None``. Each matching quest advances at
    most one stage; surplus quantity is not carried into the next stage.
    """
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        return None

    matching = _matching_active_stages(giver, receiver, item_key)
    if not matching:
        return None

    replacements: dict[str, QuestRecord] = {}
    pin_operations: list[Any] = []
    for record, definition in matching:
        objective = definition.stages[record.stage_index].objective
        remaining = objective.quantity - record.stage_progress
        gained = min(quantity, remaining)
        if gained < 1:
            continue
        new_progress = record.stage_progress + gained
        if new_progress >= objective.quantity:
            replacements[record.quest_id] = fulfill_record_for(
                giver, record, definition
            )
            pin_operations.extend(release_stage_binding(giver, record))
        else:
            replacements[record.quest_id] = replace(
                record,
                stage_progress=new_progress,
            )

    if not replacements:
        return None
    return (
        [replacements.get(record.quest_id, record) for record in read_records(giver)],
        tuple(pin_operations),
    )


def schedule_delivery_events(
    giver: Any,
    records_before: dict[str, QuestRecord],
    new_records: list[QuestRecord],
) -> None:
    """Emit one ``delivery_progress`` event per advanced quest on durable commit."""
    advances: list[dict[str, str]] = []
    char_id = str(getattr(giver, "pk", "?"))
    for record in new_records:
        old = records_before.get(record.quest_id)
        if old is None:
            continue
        if (
            record.stage_progress != old.stage_progress
            or record.stage_index != old.stage_index
            or record.state != old.state
        ):
            advances.append(
                {"char": char_id, "quest": str(record.definition_key), "step": str(old.stage_index)}
            )
    for context in sorted(advances, key=lambda item: item["quest"]):
        transaction.on_commit(
            lambda context=context: log_info("delivery_progress", context=context)
        )
