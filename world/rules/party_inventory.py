"""Member item transfer rule (party-item-transfer).

One deterministic entry both transports share: the WebClient
``party.transfer`` action and, in the next change, the text commands. The rule
re-derives the commander and both member identities through the party boundary,
refuses the ordered conditions with stable codes, and composes the giver's
removal with the receiver's addition through ``plan_inventory_delta`` inside
one transaction. It never advances time, changes affinity, or advances quest
deliveries.

Both plans are computed inside the transfer transaction and before the first
write: a plan's ACQUIRE replacement dispatches quest-completion observers, and
their contract is to defer through ``transaction.on_commit``. Computing the
plans outside the savepoint would let a rolled-back transfer publish a
completion that never happened.
"""

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.lore.items import ITEM_REGISTRY
from world.observability import log_info, log_warn
from world.rules.equipment import (
    apply_inventory_plan,
    equipped_removal_conflict,
    materialize_registry_object,
    plan_inventory_delta,
    registry_key_for_object,
)
from world.rules.party_scope import (
    PARTY_SCOPE_MESSAGES,
    PURPOSE_ORGANIZE,
    PartyScopeError,
    authorize_member,
    party_in_combat,
    resolve_commander,
)
from world.rules.surfaces import (
    restore_attributes,
    restore_traits,
    snapshot_attributes,
    snapshot_traits,
)
from world.skills.restrictions import exam_restriction

REASON_TRANSFER_IN_COMBAT = "transfer_in_combat"
REASON_TRANSFER_SAME_MEMBER = "transfer_same_member"
REASON_INVALID_QUANTITY = "invalid_quantity"
REASON_ITEM_NOT_HELD = "item_not_held"
REASON_ITEM_LOCKED = "item_locked"
REASON_ITEM_EQUIPPED = "item_equipped"

MIN_TRANSFER_QUANTITY = 1
MAX_TRANSFER_QUANTITY = 99

#: Fixed player-facing rejection lines: one per stable code, shared by every
#: transport so the action and the text commands never drift.
TRANSFER_MESSAGES: dict[str, str] = {
    REASON_TRANSFER_IN_COMBAT: "戰鬥中無法交換物品。",
    REASON_TRANSFER_SAME_MEMBER: "不能交給同一個人。",
    REASON_ITEM_EQUIPPED: "已裝備的物品無法交換；請先卸下。",
    REASON_ITEM_LOCKED: "這件物品無法交換。",
    REASON_ITEM_NOT_HELD: "對方沒有足夠的這件物品。",
    REASON_INVALID_QUANTITY: "數量不正確。",
}

#: The four inventory-bearing surfaces ``CmdGive`` snapshots around a transfer.
_SURFACE_KEYS = ("inventory", "quest_log", "wallet", "guild_reward_claims")


class PartyTransferError(RuntimeError):
    """A member transfer was rejected; ``reason`` is one stable code."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        self.message = TRANSFER_MESSAGES.get(reason) or PARTY_SCOPE_MESSAGES[reason]
        super().__init__(reason)


class _TransferRefused(RuntimeError):
    """A quiet ``move_to`` refused; the enclosing transaction restores both bags."""


@dataclass(frozen=True)
class TransferOutcome:
    """One committed transfer: what moved, for the transport's own prose."""

    giver: Any
    receiver: Any
    item_key: str
    quantity: int


def _live_entity(dbid: Any) -> Any | None:
    """Resolve one identity dbid for the combat read, without authorizing it."""
    if isinstance(dbid, bool) or not isinstance(dbid, int) or dbid < 1:
        return None
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(id=dbid).first()


def _reject_quantity(quantity: Any) -> int:
    """Return the bounded quantity or reject with ``invalid_quantity``."""
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise PartyTransferError(REASON_INVALID_QUANTITY)
    if not MIN_TRANSFER_QUANTITY <= quantity <= MAX_TRANSFER_QUANTITY:
        raise PartyTransferError(REASON_INVALID_QUANTITY)
    return quantity


def _reject_item(giver: Any, receiver: Any, item_key: Any, quantity: int) -> str:
    """Apply the item rejections in the design's order and return the key."""
    definition = (
        ITEM_REGISTRY.get(item_key) if isinstance(item_key, str) and item_key else None
    )
    if definition is None:
        raise PartyTransferError(REASON_ITEM_NOT_HELD)
    if definition.guild_property:
        raise PartyTransferError(REASON_ITEM_LOCKED)
    if exam_restriction(giver) is not None or exam_restriction(receiver) is not None:
        raise PartyTransferError(REASON_ITEM_LOCKED)
    held = list(giver.db.inventory or [])
    if held.count(item_key) < quantity:
        raise PartyTransferError(REASON_ITEM_NOT_HELD)
    if equipped_removal_conflict(giver, (item_key,) * quantity) is not None:
        raise PartyTransferError(REASON_ITEM_EQUIPPED)
    return item_key


def resolve_item_token(entity: Any, token: Any) -> str:
    """The registry key ``entity``'s canonical bag answers to for ``token``.

    Text commands accept the registry key or the held display name; both
    resolve against the giver's canonical ``db.inventory`` list only, never a
    containment search, so a refusal is always the rule's own stable code. An
    unresolved token is returned unchanged and rejected by :func:`_reject_item`
    as ``item_not_held``.
    """
    stripped = token.strip() if isinstance(token, str) else ""
    held = list(getattr(entity.db, "inventory", None) or [])
    if stripped in held:
        return stripped
    for key in held:
        definition = ITEM_REGISTRY.get(key)
        if definition is not None and definition.display_name_zh == stripped:
            return key
    return stripped


def _mirrors(holder: Any, item_key: str) -> list[Any]:
    """The contained mirror objects answering to ``item_key``."""
    return [
        obj
        for obj in holder.contents_get(content_type="object")
        if registry_key_for_object(obj) == item_key
    ]


def _surface_snapshots(entity: Any) -> dict[str, Any]:
    return snapshot_attributes(entity, _SURFACE_KEYS) | {
        "traits": snapshot_traits(entity)
    }


def _restore_surface_snapshots(entity: Any, snapshots: dict[str, Any]) -> None:
    restore_attributes(entity, {key: snapshots[key] for key in _SURFACE_KEYS})
    restore_traits(entity, snapshots["traits"])


def _contents_snapshot(*holders: Any) -> dict[int, tuple[Any, Any]]:
    """Every contained object's identity and pre-transfer location."""
    return {
        obj.pk: (obj, obj.location)
        for holder in holders
        for obj in holder.contents_get(content_type="object")
    }


def _plan_pin_operations(plan: Any) -> tuple[Any, ...]:
    """The plan's direct ACQUIRE pins plus its AUTO-settlement chain pins.

    Applying a plan can settle an ``AUTO`` reward whose paid items complete a
    further ACQUIRE stage: those rooms are absent from ``plan.acquire[1]``, so
    the outer rollback boundary must plan them here (the same preflight
    ``world/rules/gm.py`` performs) before any write.
    """
    if plan.acquire is None:
        return ()
    from world.quests.settlement import plan_auto_settlement_chain

    operations = list(plan.acquire[1])
    settlement = plan_auto_settlement_chain(
        plan.entity, list(plan.entity.db.quest_log or []), list(plan.acquire[0])
    )
    operations.extend(settlement.chain_pins)
    return tuple(operations)


def _pin_snapshots(
    pin_operations: tuple[Any, ...],
) -> dict[int, tuple[Any, Any]]:
    """The pre-transfer pin reasons of every room the transfer may unpin."""
    from world.quests.transitions import snapshot_pin_reasons

    snapshots: dict[int, tuple[Any, Any]] = {}
    for room, _, _ in pin_operations:
        if id(room) not in snapshots:
            snapshots[id(room)] = (room, snapshot_pin_reasons(room))
    return snapshots


def _restore_pin_snapshots(snapshots: dict[int, tuple[Any, Any]]) -> None:
    from world.quests.transitions import restore_pin_reasons

    for room, snapshot in snapshots.values():
        restore_pin_reasons(room, snapshot)


def _flush_rolled_back_instances() -> None:
    """Evict idmapper entries whose rows the rollback removed.

    Evennia's idmapper is not transaction-aware, and materializing a missing
    mirror *creates* a row with no pre-transfer snapshot to restore: the row
    rolls back while the instance stays cached, the same failure mode
    ``world/rules/clock.py`` reconciles for created stage objects. Runs only
    on the failure path, where the number of cached objects is small.
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


def _restore_transfer(
    holders: tuple[Any, ...],
    surfaces: list[dict[str, Any]],
    contents: dict[int, tuple[Any, Any]],
    pins: dict[int, tuple[Any, Any]],
) -> None:
    """Re-point rolled-back moves and restore both bags' in-process state.

    Every step is independent and best-effort: a cleanup failure must never
    replace the transfer failure the caller is about to re-raise.
    """
    for obj, location in contents.values():
        obj.db_location = location
    try:
        _flush_rolled_back_instances()
    except Exception as error:
        log_warn(
            "party_transfer_restore_failed",
            exc=error,
            context={"stage": "idmapper"},
        )
    for holder, snapshot in zip(holders, surfaces):
        _restore_surface_snapshots(holder, snapshot)
    _restore_pin_snapshots(pins)
    for holder in holders:
        try:
            holder.contents_cache.init()
        except Exception as error:
            log_warn(
                "party_transfer_restore_failed",
                exc=error,
                context={"stage": "contents_cache", "char": str(holder.pk)},
            )


def transfer_item(
    acting: Any,
    giver_id: Any,
    receiver_id: Any,
    item_key: Any,
    quantity: Any,
) -> TransferOutcome:
    """Move ``quantity`` copies of ``item_key`` between two party members.

    ``acting`` is the authenticated character; ``giver_id`` and ``receiver_id``
    are member dbids re-derived through the party boundary and never trusted as
    identity. Rejections raise :class:`PartyTransferError` with a stable
    ``reason`` and the fixed ``message``; membership rejections keep the shared
    party codes. A successful call registers one ``party_transfer`` info event
    on the enclosing transaction's commit.
    """
    giver = _live_entity(giver_id)
    receiver = _live_entity(receiver_id)
    if party_in_combat(acting, giver, receiver):
        raise PartyTransferError(REASON_TRANSFER_IN_COMBAT)
    try:
        commander = resolve_commander(acting)
        giver = authorize_member(commander, giver_id, PURPOSE_ORGANIZE, anchor=acting)
        receiver = authorize_member(
            commander, receiver_id, PURPOSE_ORGANIZE, anchor=acting
        )
    except PartyScopeError as error:
        raise PartyTransferError(error.reason) from error
    if giver is receiver:
        raise PartyTransferError(REASON_TRANSFER_SAME_MEMBER)
    quantity = _reject_quantity(quantity)
    item_key = _reject_item(giver, receiver, item_key, quantity)

    moved = _mirrors(giver, item_key)[:quantity]
    holders = (giver, receiver)
    surfaces = [_surface_snapshots(holder) for holder in holders]
    contents = _contents_snapshot(*holders)
    pins: dict[int, tuple[Any, Any]] = {}
    event_context = {
        "giver": giver.pk,
        "receiver": receiver.pk,
        "item": item_key,
        "quantity": quantity,
    }
    try:
        with transaction.atomic():
            giver_plan = plan_inventory_delta(giver, removals=(item_key,) * quantity)
            receiver_plan = plan_inventory_delta(
                receiver, additions=(item_key,) * quantity
            )
            pin_operations = (
                *_plan_pin_operations(giver_plan),
                *_plan_pin_operations(receiver_plan),
            )
            pins = _pin_snapshots(pin_operations)
            for obj in moved:
                if not obj.move_to(receiver, quiet=True, move_type="give"):
                    raise _TransferRefused(item_key)
            for _ in range(quantity - len(moved)):
                materialize_registry_object(receiver, item_key)
            apply_inventory_plan(giver_plan)
            apply_inventory_plan(receiver_plan)
            transaction.on_commit(
                lambda context=event_context: log_info(
                    "party_transfer", context=context
                )
            )
    except Exception:
        _restore_transfer(holders, surfaces, contents, pins)
        raise
    return TransferOutcome(
        giver=giver,
        receiver=receiver,
        item_key=item_key,
        quantity=quantity,
    )
