"""Member item transfer and equipment-toggle rules (party-item-transfer).

One deterministic entry both transports share: the WebClient
``party.transfer`` action and, in the next change, the text commands. The rule
re-derives the commander and both member identities through the party boundary,
refuses the ordered conditions with stable codes, and composes the giver's
removal with the receiver's addition through ``plan_inventory_delta`` inside
one transaction. It never advances time, changes affinity, or advances quest
deliveries.

:func:`toggle_member_equipment` is the sibling member-scoped equipment entry
(party-member-equipment): it authorizes one present member for the organizing
purpose and then calls the unchanged entity-scoped
``world.rules.equipment.toggle_equipment``, so the free-action semantics and
the draft-preview invalidation stay in their single owner.

:func:`use_member_item` is the member-scoped item-use entry
(companion-field-item-use): it authorizes one present member for the acting
purpose and then calls the unchanged entity-scoped
``world.rules.items.use_item``, so the member's own bag, SELF binding, and the
commander's six-second present-party advance stay in their single owner.

Both plans are computed inside the transfer transaction and before the first
write: a plan's ACQUIRE replacement dispatches quest-completion observers, and
their contract is to defer through ``transaction.on_commit``. Computing the
plans outside the savepoint would let a rolled-back transfer publish a
completion that never happened.

:func:`inventory_view` is the read-only ``party_inventory`` input
(party-inventory-panel): it groups one member's canonical bag into rows and
derives the use, toggle, and give descriptors from the same side-effect-free
preflights the settlement paths call. It never writes and never materializes
a lazy handler.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.lore.items import ITEM_REGISTRY
from world.observability import log_info, log_warn
from world.rules.equipment import (
    apply_inventory_plan,
    equipped_removal_conflict,
    materialize_registry_object,
    normalized_equipment,
    plan_inventory_delta,
    preflight_equipment_toggle,
    registry_key_for_object,
    toggle_equipment,
)
from world.rules.party import bound_owner_of
from world.rules.party_scope import (
    PARTY_SCOPE_MESSAGES,
    PURPOSE_ACT,
    PURPOSE_ORGANIZE,
    REASON_NOT_PARTY_MEMBER,
    PartyScopeError,
    authorize_member,
    party_in_combat,
    resolve_commander,
)
from world.rules.service_messages import SERVICE_REASON_MESSAGES
from world.rules.surfaces import (
    restore_attributes,
    restore_traits,
    snapshot_attributes,
    snapshot_traits,
)
from world.rules.wallet import read_wallet
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


@dataclass(frozen=True)
class MemberEquipmentOutcome:
    """One member-scoped toggle: whose equipment was addressed and its result.

    ``member`` is the re-derived live member the toggle ran against, so each
    transport can name it without re-deciding the member boundary.
    """

    member: Any
    result: Any


@dataclass(frozen=True)
class MemberItemUseOutcome:
    """One member-scoped item use: whose bag was addressed and its settlement.

    ``member`` is the re-derived live member the use ran against, so each
    transport can name it without re-deciding the member boundary.
    """

    member: Any
    settlement: Any


@dataclass(frozen=True)
class TransferPreflight:
    """One side-effect-free transfer eligibility verdict.

    ``allowed`` is true exactly when the transfer rule would accept the
    giver/item/quantity now. ``reason`` is the stable rejection code, or
    ``None`` when allowed. Presentation derives its ``give`` descriptor from
    this same function, so the panel and the settlement can never disagree
    about item-level eligibility.
    """

    allowed: bool
    reason: str | None = None


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


def preflight_transfer(
    giver: Any,
    item_key: Any,
    quantity: int = MIN_TRANSFER_QUANTITY,
    receiver: Any = None,
) -> TransferPreflight:
    """Apply the item rejections in the design's order, writing nothing.

    Shared by :func:`transfer_item` (through :func:`_reject_item`) and the
    ``party_inventory`` read model, so the panel's ``give`` descriptor is the
    settlement rule's own verdict rather than a second copy of its checks.
    ``receiver`` is optional because a bag row carries no chosen destination:
    the receiver-specific exam-kit lock can only be judged once a destination
    is named, and the settlement supplies it.
    """
    definition = (
        ITEM_REGISTRY.get(item_key) if isinstance(item_key, str) and item_key else None
    )
    if definition is None:
        return TransferPreflight(False, REASON_ITEM_NOT_HELD)
    if definition.guild_property:
        return TransferPreflight(False, REASON_ITEM_LOCKED)
    if exam_restriction(giver) is not None:
        return TransferPreflight(False, REASON_ITEM_LOCKED)
    if receiver is not None and exam_restriction(receiver) is not None:
        return TransferPreflight(False, REASON_ITEM_LOCKED)
    held = list(giver.db.inventory or [])
    if held.count(item_key) < quantity:
        return TransferPreflight(False, REASON_ITEM_NOT_HELD)
    if equipped_removal_conflict(giver, (item_key,) * quantity) is not None:
        return TransferPreflight(False, REASON_ITEM_EQUIPPED)
    return TransferPreflight(True)


def _reject_item(giver: Any, receiver: Any, item_key: Any, quantity: int) -> str:
    """Raise the preflight's stable rejection, or return the accepted key."""
    reason = preflight_transfer(giver, item_key, quantity, receiver=receiver).reason
    if reason is not None:
        raise PartyTransferError(reason)
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


def toggle_member_equipment(
    acting: Any, member_id: Any, item_key: Any
) -> MemberEquipmentOutcome:
    """Toggle one present party member's own equipment (a free action).

    ``acting`` is the authenticated character; ``member_id`` is a member dbid
    re-derived through the party boundary and never trusted as identity. The
    organizing purpose admits a knocked-out member, because reorganizing gear
    is not acting. The toggle itself is the unchanged entity-scoped
    :func:`world.rules.equipment.toggle_equipment`, so it stays free in
    exploration and in combat and its draft-preview invalidation keeps running
    for the re-equipped member's own commander.

    Membership failures raise :class:`PartyScopeError` with the shared stable
    code and message; equipment rejections come back in the result, exactly as
    the entity-scoped rule reports them.
    """
    commander = resolve_commander(acting)
    member = authorize_member(
        commander, member_id, PURPOSE_ORGANIZE, anchor=acting
    )
    return MemberEquipmentOutcome(
        member=member, result=toggle_equipment(member, item_key)
    )


def use_member_item(
    acting: Any, member_id: Any, item_key: Any, target: Any = None
) -> MemberItemUseOutcome:
    """Use one item from a present party member's own bag (a field action).

    ``acting`` is the authenticated character; ``member_id`` is a member dbid
    re-derived through the party boundary for the acting purpose and never
    trusted as identity, so a forged, stale, absent, or knocked-out member is
    rejected with the shared stable code before anything is read or written.
    ``target`` is the caller's single explicit choice, resolved by the
    transport relative to the member's room and consumed only by
    single-scope effects.

    The use itself is the unchanged entity-scoped
    :func:`world.rules.items.use_item` with the member as its actor: the
    member's own bag is consumed, SELF effects bind to the member, and the
    command's six-second advance settles the present party through the
    member's resolved commander.

    A party session anywhere in the request refuses the field path with the
    item rule's own ``active_combat`` rejection and no mutation: the member's
    ``use_item`` alone would not see a session persisted under the commander,
    and a combat round is the only place an item selection may be made.
    """
    from world.rules.items import (
        ItemUseReason,
        ItemUseResult,
        ItemUseSettlement,
        use_item,
    )

    commander = resolve_commander(acting)
    member = authorize_member(commander, member_id, PURPOSE_ACT, anchor=acting)
    if party_in_combat(acting, member):
        return MemberItemUseOutcome(
            member=member,
            settlement=ItemUseSettlement(
                ItemUseResult(
                    outcome="rejected", reason=ItemUseReason.ACTIVE_SESSION
                )
            ),
        )
    return MemberItemUseOutcome(
        member=member, settlement=use_item(member, item_key, target=target)
    )


# ---------------------------------------------------------------------------
# Read-only member inventory view (party-inventory-panel).
# ---------------------------------------------------------------------------

#: The row ceiling the services inventory already enforces; the panel ships
#: one bounded screen of aggregated rows.
MAX_MEMBER_INVENTORY_ROWS = 32

#: The closed descriptor routes the panel publishes.
ROUTE_FIELD_USE = "field_use"
ROUTE_COMBAT_DRAFT = "combat_draft"
ROUTE_TOGGLE = "toggle"


class PartyInventoryViewError(ValueError):
    """The viewed member's canonical inventory cannot be read truthfully.

    ``args[0]`` is one stable code: ``malformed_inventory``,
    ``malformed_equipment``, ``wallet_unreadable``, or a party-scope code when
    no commander resolves. The presenter turns any of them into the common
    unavailable form rather than inventing rows, counts, or descriptors.
    """


@dataclass(frozen=True)
class UseDescriptor:
    """One row's use descriptor: field use out of combat, draft in combat."""

    route: str
    enabled: bool
    reason: str | None = None


@dataclass(frozen=True)
class ToggleDescriptor:
    """One equipment row's free toggle descriptor."""

    route: str
    enabled: bool
    reason: str | None = None


@dataclass(frozen=True)
class GiveDescriptor:
    """One row's transfer descriptor.

    ``max_quantity`` is the row's unequipped copy count (the delta's own
    definition), independent of ``enabled``: a locked or combat-barred row can
    still report how many copies are not worn.
    """

    enabled: bool
    reason: str | None
    max_quantity: int


@dataclass(frozen=True)
class MemberEquipmentView:
    """The viewed member's normalized worn slots plus the rule's cap."""

    weapon_main: str | None
    weapon_off: str | None
    armor: str | None
    accessories: tuple[str, ...]
    accessory_limit: int


@dataclass(frozen=True)
class MemberInventoryRow:
    """One aggregated item key with its presentation and three descriptors."""

    item_key: str
    display_name: str
    held: int
    equipped_count: int
    slot: str | None
    presentation: Any | None
    use: UseDescriptor | None
    toggle: ToggleDescriptor | None
    give: GiveDescriptor


@dataclass(frozen=True)
class MemberInventoryView:
    """The frozen read-only inputs of the ``party_inventory`` panel."""

    member: Any
    purse: int
    equipment: MemberEquipmentView
    rows: tuple[MemberInventoryRow, ...]


def _strict_inventory(member: Any) -> list[str]:
    """Read the canonical flat inventory strictly, or fail closed."""
    raw = member.db.inventory
    if raw is None:
        return []
    if isinstance(raw, str) or not isinstance(raw, Sequence):
        raise PartyInventoryViewError("malformed_inventory")
    entries = list(raw)
    if not all(isinstance(entry, str) for entry in entries):
        raise PartyInventoryViewError("malformed_inventory")
    return entries


def _commander_of(member: Any) -> Any | None:
    """The commander whose party purse the viewed member's panel reports."""
    from typeclasses.characters import PlayerCharacter

    if isinstance(member, PlayerCharacter):
        return member
    return bound_owner_of(member)


def _scope_reason(commander: Any, member: Any, purpose: str) -> str | None:
    """The member boundary's fixed refusal line, or ``None`` when admitted."""
    try:
        authorize_member(commander, int(member.pk), purpose)
    except PartyScopeError as error:
        return PARTY_SCOPE_MESSAGES[error.reason]
    return None


def _reason_message(code: str) -> str:
    return SERVICE_REASON_MESSAGES.get(code, "此操作目前無法完成。")


def _equipment_view(equipment: dict) -> MemberEquipmentView:
    from world.skills.equipment import ACCESSORY_MAX_SLOTS

    return MemberEquipmentView(
        weapon_main=equipment["weapon_main"],
        weapon_off=equipment["weapon_off"],
        armor=equipment["armor"],
        accessories=tuple(equipment["accessories"]),
        accessory_limit=ACCESSORY_MAX_SLOTS,
    )


def _equipped_counts(equipment: dict) -> dict[str, int]:
    """One equipped occurrence per worn key (normalization forbids repeats)."""
    counts: dict[str, int] = {}
    for key in (
        equipment["weapon_main"],
        equipment["weapon_off"],
        equipment["armor"],
    ):
        if key is not None:
            counts[key] = 1
    for key in equipment["accessories"]:
        counts[key] = 1
    return counts


def _field_use_descriptor(
    member: Any, item_key: str, definition: Any, scope_reason: str | None
) -> UseDescriptor | None:
    """The exploration use descriptor, or ``None`` for a non-usable key."""
    if definition is None or definition.use_mechanics is None:
        return None
    if scope_reason is not None:
        return UseDescriptor(ROUTE_FIELD_USE, False, scope_reason)
    from world.rules.items import ItemUseRequest, preflight_item_use
    from world.rules.targeting import RoomActionContext

    preflight = preflight_item_use(
        ItemUseRequest(actor=member, item_key=item_key),
        in_combat=False,
        context=RoomActionContext(member.location),
    )
    if preflight.allowed:
        return UseDescriptor(ROUTE_FIELD_USE, True, None)
    code = "" if preflight.reason is None else str(preflight.reason.value)
    return UseDescriptor(ROUTE_FIELD_USE, False, _reason_message(code))


def _combat_item_choices(member: Any) -> tuple[dict[str, Any], str | None]:
    """The member's combat item choices, or ``({}, reason)`` when unavailable."""
    from world.rules.combat import BattlefieldActionContext
    from world.rules.combat_session import (
        CombatSessionError,
        SessionReason,
        authorize_combat_actor,
        read_session,
        reconstruct_battlefield,
    )
    from world.rules.items import enumerate_actor_item_choices
    from world.rules.player_messages import session_reason_message

    commander = _commander_of(member)
    if commander is None:
        return {}, session_reason_message(str(SessionReason.NO_ACTIVE_SESSION))
    try:
        record = read_session(commander)
        if record is None:
            return {}, session_reason_message(str(SessionReason.NO_ACTIVE_SESSION))
        battlefield = reconstruct_battlefield(commander, record)
        authorize_combat_actor(commander, member, record, battlefield)
    except CombatSessionError as error:
        code = (
            str(error.args[0])
            if error.args
            else str(SessionReason.FORBIDDEN_ACTOR)
        )
        return {}, session_reason_message(code)
    context = BattlefieldActionContext(
        battlefield, event_context={"battlefield": battlefield}
    )
    choices = enumerate_actor_item_choices(
        member,
        context,
        candidate_entities=list(battlefield.roster.values()),
        in_combat=True,
    )
    return {choice.item_key: choice for choice in choices}, None


def _combat_use_descriptor(
    item_key: str,
    definition: Any,
    choices: dict[str, Any],
    unavailable_reason: str | None,
) -> UseDescriptor | None:
    """The combat-draft use descriptor, or ``None`` when the item is inapplicable."""
    if definition is None or definition.use_mechanics is None:
        return None
    if unavailable_reason is not None:
        return UseDescriptor(ROUTE_COMBAT_DRAFT, False, unavailable_reason)
    choice = choices.get(item_key)
    if choice is None:
        return None
    if choice.enabled:
        return UseDescriptor(ROUTE_COMBAT_DRAFT, True, None)
    code = "" if choice.reason is None else str(choice.reason.value)
    return UseDescriptor(ROUTE_COMBAT_DRAFT, False, _reason_message(code))


def _toggle_descriptor(
    member: Any, item_key: str, definition: Any, scope_reason: str | None
) -> ToggleDescriptor | None:
    """The free toggle descriptor, or ``None`` for a non-equipment key."""
    if definition is None or definition.equipment_slot is None:
        return None
    if scope_reason is not None:
        return ToggleDescriptor(ROUTE_TOGGLE, False, scope_reason)
    preflight = preflight_equipment_toggle(member, item_key)
    if preflight.allowed:
        return ToggleDescriptor(ROUTE_TOGGLE, True, None)
    code = "" if preflight.reason is None else str(preflight.reason.value)
    return ToggleDescriptor(ROUTE_TOGGLE, False, _reason_message(code))


def _give_descriptor(
    member: Any,
    item_key: str,
    *,
    held: int,
    equipped_count: int,
    in_combat: bool,
    scope_reason: str | None,
) -> GiveDescriptor:
    """The transfer descriptor from the shared preflight plus the row grouping."""
    max_quantity = max(held - equipped_count, 0)
    if in_combat:
        return GiveDescriptor(
            False, TRANSFER_MESSAGES[REASON_TRANSFER_IN_COMBAT], max_quantity
        )
    if scope_reason is not None:
        return GiveDescriptor(False, scope_reason, max_quantity)
    preflight = preflight_transfer(member, item_key)
    if preflight.allowed:
        return GiveDescriptor(True, None, max_quantity)
    reason = preflight.reason or REASON_ITEM_NOT_HELD
    return GiveDescriptor(False, TRANSFER_MESSAGES[reason], max_quantity)


def inventory_view(member: Any, *, in_combat: bool) -> MemberInventoryView:
    """Build the frozen read-only ``party_inventory`` inputs for one member.

    Groups the member's canonical bag keys into rows (held count, equipped
    count, registry slot), normalizes the member's worn slots, and derives the
    three descriptors from the rules' own side-effect-free preflights: field
    use or the combat draft, the free equipment toggle, and the transfer
    preflight with the member as giver. The purse is the commander's wallet,
    never the viewed companion's. Nothing is written and no lazy handler is
    materialized.

    Raises :class:`PartyInventoryViewError` with a stable code when canonical
    inventory, equipment, or the commander wallet cannot be read truthfully.
    """
    inventory = _strict_inventory(member)
    equipment = normalized_equipment(member)
    if equipment is None:
        raise PartyInventoryViewError("malformed_equipment")
    commander = _commander_of(member)
    if commander is None:
        raise PartyInventoryViewError(REASON_NOT_PARTY_MEMBER)
    try:
        purse = read_wallet(commander, PartyInventoryViewError)
    except ValueError as error:
        raise PartyInventoryViewError("wallet_unreadable") from error

    act_reason = None if in_combat else _scope_reason(commander, member, PURPOSE_ACT)
    organize_reason = _scope_reason(commander, member, PURPOSE_ORGANIZE)
    choices: dict[str, Any] = {}
    draft_reason: str | None = None
    if in_combat:
        choices, draft_reason = _combat_item_choices(member)

    equipped = _equipped_counts(equipment)
    counts = Counter(inventory)
    rows: list[MemberInventoryRow] = []
    for item_key in sorted(counts):
        definition = ITEM_REGISTRY.get(item_key)
        held = counts[item_key]
        equipped_count = equipped.get(item_key, 0)
        slot = (
            None
            if definition is None or definition.equipment_slot is None
            else definition.equipment_slot.value
        )
        rows.append(
            MemberInventoryRow(
                item_key=item_key,
                display_name=(
                    definition.display_name_zh
                    if definition is not None
                    else item_key
                ),
                held=held,
                equipped_count=equipped_count,
                slot=slot,
                presentation=(
                    definition.presentation if definition is not None else None
                ),
                use=(
                    _combat_use_descriptor(item_key, definition, choices, draft_reason)
                    if in_combat
                    else _field_use_descriptor(member, item_key, definition, act_reason)
                ),
                toggle=_toggle_descriptor(
                    member, item_key, definition, organize_reason
                ),
                give=_give_descriptor(
                    member,
                    item_key,
                    held=held,
                    equipped_count=equipped_count,
                    in_combat=in_combat,
                    scope_reason=organize_reason,
                ),
            )
        )
        if len(rows) >= MAX_MEMBER_INVENTORY_ROWS:
            break
    return MemberInventoryView(
        member=member,
        purse=purse,
        equipment=_equipment_view(equipment),
        rows=tuple(rows),
    )
