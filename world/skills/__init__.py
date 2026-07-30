"""Skills and equipment surfaces from design sections 3.2 and 5.2."""

from .equipment import (
    ACCESSORY_MAX_SLOTS,
    EquipmentHandler,
    EquipmentSlot,
    list_items,
)
from .handler import ConferredSkillGrant, SkillHandler
from .registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec

__all__ = [
    "ACCESSORY_MAX_SLOTS",
    "ConferredSkillGrant",
    "EquipmentHandler",
    "EquipmentSlot",
    "SKILL_REGISTRY",
    "SkillDef",
    "SkillHandler",
    "SkillKind",
    "TargetSpec",
    "list_items",
]
