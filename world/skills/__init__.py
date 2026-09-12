"""Skills and equipment surfaces from design sections 3.2 and 5.2."""

from .equipment import (
    ACCESSORY_MAX_SLOTS,
    EquipmentHandler,
    EquipmentSlot,
    list_items,
)
from .handler import ConferredSkillGrant, SkillHandler
from .registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec

# Declared bootstrap edge, not an import-order side effect: importing ANY
# module under world.skills initializes this package first, so installing the
# sexual-act catalogue here guarantees SKILL_REGISTRY always carries the
# catalogue rows — including the integrated divine_sexual_arts signature row
# (integrate-divine-sexual-arts-catalog) — no matter which module the host
# process imports first. The catalogue imports only stdlib plus lore leaf
# modules (sex, sexual_vocab) and this package's own effects/registry
# modules, which are already complete at this point, so the edge never
# cycles. It must stay last: the sidecar appends to the registry built above.
from . import sexual_acts  # noqa: F401

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
