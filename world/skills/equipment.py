"""Equipment and inventory handling from design sections 3.2 and 5.2."""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any


class EquipmentSlot(StrEnum):
    """Project slots inspired by, but distinct from, evadventure locations."""

    WEAPON_MAIN = "weapon_main"
    WEAPON_OFF = "weapon_off"
    ARMOR = "armor"
    ACCESSORY = "accessory"


ACCESSORY_MAX_SLOTS = 5
_EMPTY_EQUIPMENT = {
    "weapon_main": None,
    "weapon_off": None,
    "armor": None,
    "accessories": [],
}


def dual_wielding_from_storage(entity: Any) -> bool:
    """Whether both weapon slots hold an equipped item key, read from storage.

    Reads only the stored equipment mapping without materializing any handler,
    so the no-create combat-modifier and status paths can supply the fact
    without violating their no-create contracts. Malformed storage (missing,
    non-mapping, or non-string slot values) fails closed to ``False``.
    """
    raw = entity.db.equipment
    if not isinstance(raw, Mapping):
        return False
    main = raw.get("weapon_main")
    off = raw.get("weapon_off")
    return (
        isinstance(main, str) and bool(main)
        and isinstance(off, str) and bool(off)
    )


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

    @property
    def is_dual_wielding(self) -> bool:
        """Whether both weapon slots hold an equipped item key."""
        return dual_wielding_from_storage(self.entity)

def list_items(entity: Any) -> list[str]:
    """Return a copy of the flat inventory."""
    return list(entity.db.inventory or [])
