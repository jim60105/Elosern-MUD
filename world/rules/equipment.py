"""Deterministic equipment and inventory state writes."""

from typing import Any

from world.skills.equipment import ACCESSORY_MAX_SLOTS, EquipmentSlot


_EMPTY_EQUIPMENT = {
    "weapon_main": None,
    "weapon_off": None,
    "armor": None,
    "accessories": [],
}


def _equipment_snapshot(entity: Any) -> dict[str, str | list[str] | None]:
    raw = entity.db.equipment or {}
    return {
        **_EMPTY_EQUIPMENT,
        **raw,
        "accessories": list(raw.get("accessories", [])),
    }


def equip_item(entity: Any, slot: EquipmentSlot, item_key: str) -> None:
    """Place an item key into one equipment slot."""
    equipment = _equipment_snapshot(entity)
    if slot is EquipmentSlot.ACCESSORY:
        accessories = equipment["accessories"]
        if len(accessories) >= ACCESSORY_MAX_SLOTS:
            raise ValueError("accessory slots are full")
        accessories.append(item_key)
    else:
        equipment[slot.value] = item_key
    entity.db.equipment = equipment


def unequip_item(entity: Any, slot: EquipmentSlot) -> str | None:
    """Remove and return a single item, or the last accessory."""
    equipment = _equipment_snapshot(entity)
    if slot is EquipmentSlot.ACCESSORY:
        accessories = equipment["accessories"]
        removed = accessories.pop() if accessories else None
    else:
        removed = equipment[slot.value]
        equipment[slot.value] = None
    entity.db.equipment = equipment
    return removed


def add_item(entity: Any, item_key: str) -> None:
    """Append an item key to the flat inventory."""
    entity.db.inventory = [*(entity.db.inventory or []), item_key]


def remove_item(entity: Any, item_key: str) -> None:
    """Remove one matching item key when present."""
    items = list(entity.db.inventory or [])
    if item_key in items:
        items.remove(item_key)
    entity.db.inventory = items
