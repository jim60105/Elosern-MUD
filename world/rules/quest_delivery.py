"""Deterministic quest-item delivery: one rule, two surfaces.

The registered ``explore.deliver`` web action and the ``交付`` player command
both call :func:`deliver_quest_item`, so the two surfaces can never diverge on
refusals or outcomes (change quest-deliver-action, design D5/D6).

The rule preflights the combat gate, co-location, the actor's active
``DELIVER`` stage bound to the recipient, and the held quantity — every
refusal returns before any write — and then performs the hand-over through the
existing ``world.rules.npc_intents._transfer_items`` primitive, whose
transaction, dual-entity snapshots, and delivery-observer wiring advance the
stage atomically with the item movement. The hand-over transfers exactly the
remaining objective quantity of the selected active stage; the payload carries
no quantity, so it is re-derived server-side.

A terminal record needs no refusal branch of its own: the strict reader
(``validate_record_runtime``) guarantees terminal records carry no runtime
bindings, so a post-completion hand-over to the same recipient and item
matches nothing and refuses with ``no_active_delivery``.
"""

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.lore.items import ITEM_REGISTRY
from world.observability import log_info
from world.quests.deliver import iter_bound_deliveries, select_deliver_stage
from world.quests.runtime import QuestState
from world.rules.combat_session import is_in_active_session

REASON_IN_COMBAT = "in_combat"
REASON_NOT_COLOCATED = "not_colocated"
REASON_NO_ACTIVE_DELIVERY = "no_active_delivery"
REASON_ITEM_NOT_HELD = "item_not_held"
REASON_TRANSFER_FAILED = "transfer_failed"

#: Stable Traditional Chinese refusal prose, one per stable reason code. Both
#: surfaces render these verbatim, so a rejection reads identically everywhere.
REFUSAL_MESSAGES: dict[str, str] = {
    REASON_IN_COMBAT: "戰鬥中無法交付物品。",
    REASON_NOT_COLOCATED: "對方不在這裡。",
    REASON_NO_ACTIVE_DELIVERY: "這裡沒有需要交付的任務物品。",
    REASON_ITEM_NOT_HELD: "你沒有帶著足夠的任務物品。",
    REASON_TRANSFER_FAILED: "物品交接失敗，什麼都沒有發生。",
}


def item_display_name(item_key: str) -> str:
    """The item registry's display name, or the raw key when unregistered."""
    definition = ITEM_REGISTRY.get(item_key)
    return definition.display_name_zh if definition is not None else item_key


@dataclass(frozen=True)
class DeliveryOutcome:
    """The deterministic result of one hand-over attempt.

    ``applied`` is ``True`` only when the transfer committed and the delivery
    observer advanced the stage in the same transaction. A refusal carries the
    stable reason ``code`` and its fixed Traditional Chinese ``message``; a
    refusal never mutated any state.
    """

    applied: bool
    code: str | None
    message: str


@dataclass(frozen=True)
class DeliveryStageView:
    """The read-only delivery state for one co-located bound recipient.

    One view per ``(recipient, item_key)`` pair with an active stage. When
    several in-progress records bind the same pair, the view carries the
    selected stage (lowest remaining quantity, ties in quest-log order) — the
    same selection :func:`deliver_quest_item` applies — so an enabled view is
    always satisfiable by the hand-over that follows it.
    """

    quest_id: str
    recipient_id: int
    item_key: str
    remaining: int
    held: int
    deliverable: bool
    reason: tuple[str, str] | None


def _held_count(actor: Any, item_key: str) -> int:
    return (getattr(actor.db, "inventory", None) or []).count(item_key)


def active_deliveries_for_recipient(
    actor: Any, recipient: Any
) -> tuple[DeliveryStageView, ...]:
    """Return the read-only delivery views for one co-located recipient.

    Pure read: the affordance builder calls this per present target; nothing
    here mutates state. Groups the actor's active bound ``DELIVER`` stages by
    item key and applies the shared lowest-remaining selection per group, in
    quest-log order.
    """
    groups: dict[str, list[tuple[Any, Any]]] = {}
    for record, definition, _objective in iter_bound_deliveries(
        actor, recipient, None
    ):
        if record.state is not QuestState.IN_PROGRESS:
            continue
        item_key = definition.stages[record.stage_index].objective.item_key
        groups.setdefault(item_key, []).append((record, definition))

    views: list[DeliveryStageView] = []
    for item_key, group in groups.items():
        selected = select_deliver_stage(group)
        if selected is None:  # pragma: no cover - active groups always select
            continue
        selected_record, _selected_definition, remaining = selected
        held = _held_count(actor, item_key)
        deliverable = held >= remaining
        views.append(
            DeliveryStageView(
                quest_id=selected_record.quest_id,
                recipient_id=int(recipient.pk),
                item_key=item_key,
                remaining=remaining,
                held=held,
                deliverable=deliverable,
                reason=None
                if deliverable
                else (REASON_ITEM_NOT_HELD, REFUSAL_MESSAGES[REASON_ITEM_NOT_HELD]),
            )
        )
    return tuple(views)


def _refuse(code: str) -> DeliveryOutcome:
    return DeliveryOutcome(False, code, REFUSAL_MESSAGES[code])


def deliver_quest_item(actor: Any, recipient: Any, item_key: str) -> DeliveryOutcome:
    """Hand the objective item to its bound recipient, or refuse before writing.

    The single deterministic entry point shared by the ``explore.deliver``
    action adapter and the ``交付`` player command. The combat gate precedes
    every other rule-level check (design D6); every refusal returns before any
    write.
    """
    if is_in_active_session(actor):
        return _refuse(REASON_IN_COMBAT)
    location = getattr(actor, "location", None)
    if location is None or location is not getattr(recipient, "location", None):
        return _refuse(REASON_NOT_COLOCATED)

    from world.rules.npc_intents import _transfer_items

    active = [
        (record, definition)
        for record, definition, _objective in iter_bound_deliveries(
            actor, recipient, item_key
        )
        if record.state is QuestState.IN_PROGRESS
    ]
    if not active:
        return _refuse(REASON_NO_ACTIVE_DELIVERY)
    selected = select_deliver_stage(active)
    if selected is None:  # pragma: no cover - active records always select
        return _refuse(REASON_NO_ACTIVE_DELIVERY)
    _selected_record, _selected_definition, remaining = selected

    if _held_count(actor, item_key) < remaining:
        return _refuse(REASON_ITEM_NOT_HELD)

    outcome = _transfer_items(
        giver=actor, receiver=recipient, item_key=item_key, qty=remaining
    )
    if not getattr(outcome, "applied", False):
        return _refuse(REASON_TRANSFER_FAILED)

    _schedule_handover_events(actor, recipient, item_key, active)
    display = item_display_name(item_key)
    recipient_name = getattr(recipient, "key", "?")
    if remaining == 1:
        message = f"你把{display}交給了{recipient_name}。"
    else:
        message = f"你把 {remaining} 個{display}交給了{recipient_name}。"
    return DeliveryOutcome(True, None, message)


def _schedule_handover_events(
    actor: Any,
    recipient: Any,
    item_key: str,
    active: list[tuple[Any, Any]],
) -> None:
    """Emit one ``delivery_handover`` boundary event per advanced quest.

    Only the in-progress records the transfer advances — never a terminal
    match. Scheduled on durable commit so a rolled-back transfer reports
    nothing.
    """
    char_id = str(getattr(actor, "pk", "?"))
    npc_id = str(getattr(recipient, "pk", "?"))
    for record, _definition in active:
        context = {
            "char": char_id,
            "quest": str(record.definition_key),
            "npc": npc_id,
            "item": item_key,
        }
        transaction.on_commit(
            lambda context=context: log_info("delivery_handover", context=context)
        )
