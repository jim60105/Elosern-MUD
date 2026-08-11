"""Deterministic equipment and inventory state writes (guild-economy D-5).

Gameplay inventory mutations flow through one validated planning boundary.
``plan_inventory_delta`` computes a complete immutable :class:`InventoryPlan`
(before/after lists and the ACQUIRE quest-log replacement) without applying it;
``apply_inventory_plan`` commits the inventory write and any ACQUIRE quest
progress atomically. ``add_item``/``remove_item`` remain convenience wrappers.
Import construction keeps populating the raw list directly -- that is initial
state, not gameplay acquisition.
"""

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.lore.items import ITEM_REGISTRY
from world.rules.surfaces import (
    attribute_snapshot,
    restore_traits,
    snapshot_traits,
)


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


def _equipment_snapshot(entity: Any) -> dict[str, str | list[str] | None]:
    raw = entity.db.equipment or {}
    return {
        "weapon_main": None,
        "weapon_off": None,
        "armor": None,
        **raw,
        "accessories": list(raw.get("accessories", [])),
    }


def equip_item(entity: Any, slot: Any, item_key: str) -> None:
    """Place an item key into one equipment slot."""
    from world.skills.equipment import ACCESSORY_MAX_SLOTS, EquipmentSlot

    equipment = _equipment_snapshot(entity)
    if slot is EquipmentSlot.ACCESSORY:
        accessories = equipment["accessories"]
        if len(accessories) >= ACCESSORY_MAX_SLOTS:
            raise ValueError("accessory slots are full")
        accessories.append(item_key)
    else:
        equipment[slot.value] = item_key
    entity.db.equipment = equipment


def unequip_item(entity: Any, slot: Any) -> str | None:
    """Remove and return a single item, or the last accessory."""
    from world.skills.equipment import EquipmentSlot

    equipment = _equipment_snapshot(entity)
    if slot is EquipmentSlot.ACCESSORY:
        accessories = equipment["accessories"]
        removed = accessories.pop() if accessories else None
    else:
        removed = equipment[slot.value]
        equipment[slot.value] = None
    entity.db.equipment = equipment
    return removed