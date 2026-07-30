"""Equipment and inventory handling from design sections 3.2 and 5.2."""

from enum import StrEnum
from typing import Any


class EquipmentSlot(StrEnum):
    """Project slots inspired by, but distinct from, evadventure locations."""

    WEAPON_MAIN = "weapon_main"
    WEAPON_OFF = "weapon_off"
    ARMOR = "armor"
    ACCESSORY = "accessory"


ACCESSORY_MAX_SLOTS = 3
_EMPTY_EQUIPMENT = {
    "weapon_main": None,
    "weapon_off": None,
    "armor": None,
    "accessories": [],
}


class EquipmentHandler:
    """Read an entity's private equipment storage."""

    ACCESSORY_MAX_SLOTS = ACCESSORY_MAX_SLOTS

    def __init__(self, entity: Any):
        self.entity = entity

    @property
    def _raw(self) -> dict[str, str | list[str] | None]:
        raw = self.entity.db.equipment
        if not raw:
            return {
                **_EMPTY_EQUIPMENT,
                "accessories": [],
            }
        return raw

    def slot_contents(
        self, slot: EquipmentSlot
    ) -> str | list[str] | None:
        """Return one slot's stored item key or accessory list."""
        if slot is EquipmentSlot.ACCESSORY:
            return list(self._raw.get("accessories", []))
        return self._raw.get(slot.value)

def list_items(entity: Any) -> list[str]:
    """Return a copy of the flat inventory."""
    return list(entity.db.inventory or [])
