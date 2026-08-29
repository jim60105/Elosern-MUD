"""Deterministic equipment and inventory state writes (guild-economy D-5).

Gameplay inventory mutations flow through one validated planning boundary.
``plan_inventory_delta`` computes a complete immutable :class:`InventoryPlan`
(before/after lists and the ACQUIRE quest-log replacement) without applying it;
``apply_inventory_plan`` commits the inventory write and any ACQUIRE quest
progress atomically. ``add_item``/``remove_item`` remain convenience wrappers.
Import construction keeps populating the raw list directly -- that is initial
state, not gameplay acquisition.

The item-specific equipment toggle (add-inventory-item-actions D4) is the
sole gameplay writer of ``entity.db.equipment``:
``preflight_equipment_toggle`` resolves the slot from immutable registry
mechanics and computes an exact before/after plan without writing, and
``toggle_equipment`` repeats that preflight and applies the plan atomically.
Callers never supply a slot; equipped items stay in canonical inventory.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from django.db import transaction

from world.lore.items import ITEM_REGISTRY
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
    restore_traits,
    snapshot_traits,
)


class EquippedRemovalError(ValueError):
    """Raised when a removal would drop the last key of an equipped item."""


class InventoryError(ValueError):
    """An inventory operation violates the deterministic planning contract."""


def registry_key_for_object(obj: Any) -> str | None:
    """Map a contained Evennia Object to its ``ITEM_REGISTRY`` key.

    An explicit ``registry_key`` attribute wins over the object key, so a
    scene object authored with a name that happens to match a registry key
    never enters the canonical inventory by accident. Objects outside the
    registry map to ``None``.
    """
    attr_key = getattr(obj.db, "registry_key", None)
    if attr_key in ITEM_REGISTRY:
        return attr_key
    if obj.key in ITEM_REGISTRY:
        return obj.key
    return None


def materialize_registry_object(container: Any, item_key: str) -> Any:
    """Create the contained mirror Object for one canonical key entry.

    The object carries an explicit ``registry_key`` attribute so
    ``registry_key_for_object`` resolves it without relying on its key.
    """
    from evennia.utils.create import create_object

    return create_object(
        "typeclasses.objects.Object",
        key=item_key,
        attributes=[("registry_key", item_key)],
        location=container,
    )


@dataclass(frozen=True)
class InventoryPlan:
    """One validated, unapplied inventory mutation plus its quest delta.

    ``additions`` and ``removals`` preserve repeated keys. ``before`` and
    ``after`` are the complete flat repeated-key lists. ``acquire`` carries the
    precomputed ``(new_records, pin_operations)`` quest-runtime replacement for
    the plan's positive additions, or ``None`` when no active ACQUIRE objective
    matches.
    """

    entity: Any
    additions: tuple[str, ...]
    removals: tuple[str, ...]
    before: tuple[str, ...]
    after: tuple[str, ...]
    acquire: tuple[Any, Any] | None


def _validate_quantities(keys: tuple[Any, ...], field: str) -> None:
    for index, key in enumerate(keys):
        if isinstance(key, bool) or not isinstance(key, str) or not key:
            raise InventoryError(
                f"{field}[{index}] must be a non-empty item key"
            )


def _require_positive(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InventoryError(f"{name} must be a positive integer")
    return value


def _acquire_replacement(entity: Any, additions: tuple[str, ...]):
    """Compute the ACQUIRE quest-log replacement for positive additions.

    Delegates to ``world.quests`` so quest-record lifecycle stays quest-owned;
    the planner never constructs quest state itself.
    """
    if not additions:
        return None
    from world.quests.acquire import compute_acquire_replacement

    return compute_acquire_replacement(entity, additions)


def plan_inventory_delta(
    entity: Any,
    additions: tuple[str, ...] = (),
    removals: tuple[str, ...] = (),
) -> InventoryPlan:
    """Plan one inventory delta without applying it.

    Validates positive integer quantities (each entry counts one), known item
    keys for additions, and complete removal availability. The plan's ACQUIRE
    progress is computed only from its positive additions.
    """
    additions = tuple(additions)
    removals = tuple(removals)
    _validate_quantities(additions, "additions")
    _validate_quantities(removals, "removals")

    before = tuple(entity.db.inventory or [])
    after = list(before)
    for item_key in additions:
        after.append(item_key)
    remaining = list(before)
    for item_key in removals:
        if item_key not in remaining:
            raise InventoryError(
                f"cannot remove {item_key!r}: only {remaining.count(item_key)} held"
            )
        remaining.remove(item_key)
    conflict = equipped_removal_conflict(entity, removals)
    if conflict is not None:
        raise EquippedRemovalError(
            f"cannot remove {conflict!r}: it is equipped; unequip it first"
        )
    for item_key in removals:
        after.remove(item_key)

    return InventoryPlan(
        entity=entity,
        additions=additions,
        removals=removals,
        before=before,
        after=tuple(after),
        acquire=_acquire_replacement(entity, additions),
    )


def apply_inventory_plan(plan: InventoryPlan) -> None:
    """Commit one plan's inventory write and ACQUIRE quest delta atomically."""
    entity = plan.entity
    inventory_snapshot = attribute_snapshot(entity, "inventory")
    trait_snapshot = snapshot_traits(entity)
    quest_snapshot = attribute_snapshot(entity, "quest_log")
    pin_snapshots = {}
    from world.quests.transitions import snapshot_pin_reasons

    for room, _, _ in _acquire_pins(plan):
        pin_snapshots[id(room)] = snapshot_pin_reasons(room)

    try:
        with transaction.atomic():
            entity.db.inventory = list(plan.after)
            _apply_acquire(plan)
    except Exception:
        from world.rules.surfaces import restore_attribute_best_effort

        restore_attribute_best_effort(entity, "inventory", inventory_snapshot)
        restore_traits(entity, trait_snapshot)
        restore_attribute_best_effort(entity, "quest_log", quest_snapshot)
        from world.quests.transitions import restore_pin_reasons

        for room, _, _ in _acquire_pins(plan):
            restore_pin_reasons(room, pin_snapshots[id(room)])
        raise


def _acquire_pins(plan: InventoryPlan) -> tuple[Any, ...]:
    return plan.acquire[1] if plan.acquire is not None else ()


def _apply_acquire(plan: InventoryPlan) -> None:
    """Apply one plan's precomputed ACQUIRE replacement inside the caller transaction."""
    if plan.acquire is None:
        return
    new_records, pin_operations = plan.acquire
    from world.quests.transitions import apply_quest_log_delta

    apply_quest_log_delta(plan.entity, list(new_records), pin_operations)


def add_item(entity: Any, item_key: str) -> None:
    """Append one item key through the validated planning boundary."""
    apply_inventory_plan(plan_inventory_delta(entity, additions=(item_key,)))


def remove_item(entity: Any, item_key: str) -> None:
    """Remove one matching item key through the validated planning boundary."""
    apply_inventory_plan(plan_inventory_delta(entity, removals=(item_key,)))


class EquipmentToggleReason(StrEnum):
    """Stable named rejection reasons for the item-specific equipment toggle."""

    UNKNOWN_ITEM = "unknown_item"
    NOT_EQUIPMENT = "not_equipment"
    ITEM_NOT_HELD = "item_not_held"
    ACCESSORY_SLOTS_FULL = "accessory_slots_full"
    MALFORMED_STORAGE = "malformed_equipment"


@dataclass(frozen=True)
class EquipmentTogglePlan:
    """The complete immutable before/after equipment mapping for one toggle.

    ``action`` names the settlement shape; ``replaced_key`` is the prior
    singleton occupant that becomes unequipped (still held), never an
    accessory chosen by the system.
    """

    entity: Any
    item_key: str
    slot: Any
    action: str
    before: dict
    after: dict
    replaced_key: str | None = None


@dataclass(frozen=True)
class EquipmentTogglePreflight:
    """The outcome of one side-effect-free toggle eligibility check."""

    allowed: bool
    reason: EquipmentToggleReason | None = None
    plan: EquipmentTogglePlan | None = None


@dataclass(frozen=True)
class EquipmentToggleResult:
    """The outcome of one equipment-toggle settlement."""

    outcome: str
    reason: EquipmentToggleReason | None = None
    slot: Any = None
    action: str | None = None
    replaced_key: str | None = None


_EMPTY_EQUIPMENT_STATE: dict = {
    "weapon_main": None,
    "weapon_off": None,
    "armor": None,
    "accessories": [],
}

_SINGLETON_SLOTS = ("weapon_main", "weapon_off", "armor")


def _normalized_equipment(entity: Any) -> dict | None:
    """Normalize stored equipment strictly, or fail closed with ``None``.

    Accepts ``None``/empty as the empty mapping. Every other record must
    carry exactly the three singleton keys (``None`` or a non-empty string)
    and an ``accessories`` sequence of non-empty strings with at most one
    occurrence per key; anything else is malformed and never auto-repaired.
    """
    from world.skills.equipment import ACCESSORY_MAX_SLOTS

    raw = entity.db.equipment
    if raw is None or raw == {} or raw == _EMPTY_EQUIPMENT_STATE:
        return {**_EMPTY_EQUIPMENT_STATE, "accessories": []}
    if not isinstance(raw, Mapping) or set(raw) != set(_EMPTY_EQUIPMENT_STATE):
        return None
    normalized: dict = {}
    for slot_key in _SINGLETON_SLOTS:
        value = raw[slot_key]
        if value is None:
            normalized[slot_key] = None
            continue
        if isinstance(value, bool) or not isinstance(value, str) or not value.strip():
            return None
        normalized[slot_key] = value
    accessories = raw["accessories"]
    if isinstance(accessories, str) or not isinstance(accessories, Sequence):
        return None
    items: list[str] = []
    for entry in accessories:
        if isinstance(entry, bool) or not isinstance(entry, str) or not entry.strip():
            return None
        if entry in items:
            return None
        items.append(entry)
    if len(items) > ACCESSORY_MAX_SLOTS:
        return None
    normalized["accessories"] = items
    # Cross-slot integrity: one key may hold at most one occurrence across
    # the whole mapping, and every stored key must be registry-declared
    # equipment whose slot matches where it is stored. Registry membership
    # failures never depend on the live registry for the SHAPE checks above.
    from world.skills.equipment import EquipmentSlot

    occurrences: set[str] = set()
    for slot_key in _SINGLETON_SLOTS:
        value = normalized[slot_key]
        if value is None:
            continue
        if value in occurrences:
            return None
        occurrences.add(value)
    for value in items:
        if value in occurrences:
            return None
        occurrences.add(value)
    for slot_key in _SINGLETON_SLOTS:
        value = normalized[slot_key]
        if value is None:
            continue
        definition = ITEM_REGISTRY.get(value)
        if (
            definition is None
            or definition.equipment_slot is not EquipmentSlot(slot_key)
        ):
            return None
    for value in items:
        definition = ITEM_REGISTRY.get(value)
        if definition is None or definition.equipment_slot is not EquipmentSlot.ACCESSORY:
            return None
    return normalized


def equipped_removal_conflict(entity: Any, removals: Sequence[str]) -> str | None:
    """Return the first removal that would leave an equipped key unheld.

    Equipped items must remain in canonical inventory, so an inventory
    removal that drops the last held occurrence of an equipped key is a
    contract violation for every removal writer (sell, drop, give, NPC
    transfer). Fail-closed: malformed equipment storage protects every
    removal of a registry-declared equipment key.
    """
    from collections import Counter

    equipment = _normalized_equipment(entity)
    counts = Counter(entity.db.inventory or [])
    removed = Counter(removals)

    def empties(key: str) -> bool:
        return counts.get(key, 0) - removed.get(key, 0) < 1

    for key in removed:
        if not empties(key):
            continue
        if equipment is None:
            definition = ITEM_REGISTRY.get(key)
            if definition is not None and definition.equipment_slot is not None:
                return key
            continue
        stored = set(equipment["accessories"])
        stored.update(
            value
            for value in (
                equipment["weapon_main"],
                equipment["weapon_off"],
                equipment["armor"],
            )
            if value is not None
        )
        if key in stored:
            return key
    return None


def normalized_equipment(entity: Any) -> dict | None:
    """Public pure read of the fail-closed normalized equipment mapping.

    Returns the same normalization ``preflight_equipment_toggle`` and
    ``toggle_equipment`` settle against (``None`` means malformed storage);
    presentation surfaces must derive equipped truth from this function so
    the visible state and the only mutating API can never disagree.
    """
    return _normalized_equipment(entity)


def _equipped_singleton_key(equipment: Mapping, item_key: str) -> str | None:
    """Return the singleton slot key currently holding ``item_key``."""
    for slot_key in _SINGLETON_SLOTS:
        if equipment[slot_key] == item_key:
            return slot_key
    return None


def preflight_equipment_toggle(
    entity: Any, item_key: str
) -> EquipmentTogglePreflight:
    """Compute one toggle's exact effect against current state, writing nothing.

    Resolves the item's single slot from immutable registry mechanics,
    verifies canonical inventory ownership, normalizes stored equipment
    fail-closed, and returns the complete before/after plan with stable
    named reasons. Shared verbatim by presentation and settlement.
    """
    from world.skills.equipment import ACCESSORY_MAX_SLOTS, EquipmentSlot

    definition = ITEM_REGISTRY.get(item_key)
    if definition is None:
        return EquipmentTogglePreflight(
            allowed=False, reason=EquipmentToggleReason.UNKNOWN_ITEM
        )
    slot = definition.equipment_slot
    if slot is None:
        return EquipmentTogglePreflight(
            allowed=False, reason=EquipmentToggleReason.NOT_EQUIPMENT
        )
    inventory = entity.db.inventory
    if inventory is None:
        held: list[str] = []
    elif isinstance(inventory, str) or not isinstance(inventory, Sequence):
        return EquipmentTogglePreflight(
            allowed=False, reason=EquipmentToggleReason.MALFORMED_STORAGE
        )
    else:
        if not all(isinstance(entry, str) for entry in inventory):
            return EquipmentTogglePreflight(
                allowed=False, reason=EquipmentToggleReason.MALFORMED_STORAGE
            )
        held = list(inventory)
    if item_key not in held:
        return EquipmentTogglePreflight(
            allowed=False, reason=EquipmentToggleReason.ITEM_NOT_HELD
        )
    before = _normalized_equipment(entity)
    if before is None:
        return EquipmentTogglePreflight(
            allowed=False, reason=EquipmentToggleReason.MALFORMED_STORAGE
        )
    after = {**before, "accessories": list(before["accessories"])}
    if slot is EquipmentSlot.ACCESSORY:
        if item_key in after["accessories"]:
            after["accessories"] = [k for k in after["accessories"] if k != item_key]
            action = "unequip-accessory"
        elif len(after["accessories"]) >= ACCESSORY_MAX_SLOTS:
            return EquipmentTogglePreflight(
                allowed=False, reason=EquipmentToggleReason.ACCESSORY_SLOTS_FULL
            )
        else:
            after["accessories"].append(item_key)
            action = "equip-accessory"
        replaced_key = None
    else:
        occupied = _equipped_singleton_key(before, item_key)
        if occupied is not None:
            after[occupied] = None
            action = "unequip-singleton"
            replaced_key = None
        else:
            prior = before[slot.value]
            replaced_key = prior if prior is not None and prior != item_key else None
            after[slot.value] = item_key
            action = "equip-singleton"
    plan = EquipmentTogglePlan(
        entity=entity,
        item_key=item_key,
        slot=slot,
        action=action,
        before=before,
        after=after,
        replaced_key=replaced_key,
    )
    return EquipmentTogglePreflight(allowed=True, reason=None, plan=plan)


def sync_equipment_gauge_limits(entity: Any) -> None:
    """Recompute every gauge ceiling from the currently worn equipment.

    The single writer of the non-literal gauge ceiling (wire-equipment-
    combat-modifiers D1): ``mod`` is recomputed from scratch as the sum of
    the worn items' rulebook gauge caps — never accumulated, so repeated
    toggles cannot drift — and the literal ``base`` is never written. Absent
    gauge traits are skipped. When a recompute lowers a ceiling, the stored
    ``current`` settles down to the lowered ceiling (the read-side clamp does
    not write back, and the strict status read model rejects a stored value
    above the effective maximum). Call only inside ``toggle_equipment``'s
    transaction, after the equipment write it reads.
    """
    from world.rules.equipment_effects import equipment_gauge_caps

    caps = equipment_gauge_caps(entity)
    for key in ("hp", "mp", "sp"):
        gauge = entity.traits.get(key)
        if gauge is None or gauge.trait_type != "gauge":
            continue
        total = int(caps.get(key, 0))
        if gauge.mod != total:
            gauge.mod = total
        ceiling = gauge.max
        data = gauge._data
        stored = data.get(
            "current", (data["base"] + data["mod"]) * data["mult"]
        )
        if stored > ceiling:
            gauge.current = ceiling


def toggle_equipment(entity: Any, item_key: str) -> EquipmentToggleResult:
    """Atomically equip or unequip one held, registry-declared equipment key.

    Mutation repeats the shared preflight and writes the complete replacement
    mapping plus the recompute-from-scratch gauge-ceiling sync inside one
    transaction, restoring the in-process equipment cache, the trait storage
    (handler caches refreshed), and the buff storage when the write fails.
    Equipped items remain in canonical inventory; the caller never supplies a
    slot and no unrelated accessory is ever removed.

    Attached buffs travel with the toggle (P3): the worn-set diff against the
    same before/after plan removes the instances of unequipped items first,
    then applies the instances of newly equipped items, each keyed by
    definition and item key with ``unique_per_source`` stacking. The ``buffs``
    attribute joins the snapshot set because Evennia's BuffHandler keeps no
    cache of its own — every read goes through the attribute, so an
    assignment-restore leaves live handler reads consistent with storage.
    Snapshots are captured before the one outer transaction and every surface
    is restored in snapshot order.
    """
    from world.rules.buffs import _add_buff, _remove_buff_keys
    from world.rules.equipment_effects import attached_buff_instances

    preflight = preflight_equipment_toggle(entity, item_key)
    if not preflight.allowed or preflight.plan is None:
        return EquipmentToggleResult(
            outcome="rejected", reason=preflight.reason
        )
    plan = preflight.plan
    snapshot = attribute_snapshot(entity, "equipment")
    traits_snapshot = snapshot_traits(entity)
    buffs_snapshot = attribute_snapshot(entity, "buffs")
    before_attached = attached_buff_instances(plan.before)
    after_attached = attached_buff_instances(plan.after)
    removed = tuple(sorted(before_attached.keys() - after_attached.keys()))
    added = sorted(after_attached.keys() - before_attached.keys())
    try:
        with transaction.atomic():
            entity.db.equipment = plan.after
            sync_equipment_gauge_limits(entity)
            if removed:
                _remove_buff_keys(entity, removed)
            for instance_key in added:
                buff_key, item_key = after_attached[instance_key]
                _add_buff(
                    entity,
                    buff_key,
                    instance_key=instance_key,
                    source_key=item_key,
                )
    except Exception:
        restore_attribute_best_effort(entity, "buffs", buffs_snapshot)
        restore_attribute_best_effort(entity, "equipment", snapshot)
        restore_traits(entity, traits_snapshot)
        raise
    return EquipmentToggleResult(
        outcome="success",
        slot=plan.slot,
        action=plan.action,
        replaced_key=plan.replaced_key,
    )