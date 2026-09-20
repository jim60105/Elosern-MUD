"""Immutable item identity and presentation registry for the deterministic economy (guild-economy D-8).

Item definitions carry no tunable numeric rules; exact prices, stock, and
restock quantities live in ``world/rules/rulebook/guild_economy.yaml`` and are
joined to these identities by the guild-economy catalog loader.

Presentation metadata — closed item kind, closed SVG icon key, closed rarity,
and a bounded Traditional Chinese summary — is registry-owned and read-only.
It is visual identity only: numeric combat, recovery, or comparison values
never enter this registry; the deterministic item-effects rulebook in
``world/rules/rulebook/item_effects.yaml`` owns every magnitude.

Item mechanics are the registry's only behavioral seam: an item declares
exactly one of an immutable use definition (``ItemUseMechanics``), an
equipment slot, or nothing at all. Presentation kind never selects or
modifies mechanics.

The single-module history is split into modules of a shared surface (the
``world.skills.registry`` package precedent applies here):
:mod:`~world.lore.items.vocab` holds the bound, the closed vocabularies, and
the frozen dataclasses; the ``data_*`` modules each carry one contiguous,
in-order domain slice of the former ``ITEM_REGISTRY`` literal (section
comments included); :mod:`~world.lore.items.assembly` concatenates the slices
into ``ITEM_REGISTRY`` in exact global order.

Every name resolves through this package's namespace exactly as the single
``world/lore/items.py`` module exported it: consumers keep importing
``world.lore.items``. ``ITEM_REGISTRY`` is re-exported live from the
assembly (never rebound here), so in-place views of that one dict stay
visible through every import path.
"""

from world.lore.items.assembly import ITEM_REGISTRY
from world.lore.items.vocab import (
    SUMMARY_MAX,
    EquipmentModifierKey,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
)

# Byte-identical old-module namespace parity: the single-module history's
# top-level imports are part of its observable surface (probes read the
# registry and EquipmentSlot/EquipmentModifierKey through getattr
# string-concat seams, e.g. _equipment_rulebook_probes.py). These stay
# module-qualified so a package-path `patch(..., create=True)` can never
# silently replace the canonical objects.
from dataclasses import dataclass as dataclass  # noqa: F401  (old namespace name)
from enum import StrEnum as StrEnum  # noqa: F401
from world.skills.equipment import EquipmentSlot  # noqa: F401

__all__ = [
    "SUMMARY_MAX",
    "ITEM_REGISTRY",
    "EquipmentModifierKey",
    "ItemDefinition",
    "ItemIconKey",
    "ItemKind",
    "ItemPresentation",
    "ItemRarity",
    "ItemUseMechanics",
]
