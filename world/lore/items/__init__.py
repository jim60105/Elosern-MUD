"""Immutable item identity and presentation registry for the deterministic economy (guild-economy D-8).

Item definitions carry no tunable numeric rules; exact prices, stock, and
restock quantities live in ``world/rules/rulebook/guild_economy.yaml`` and are
joined to these identities by the guild-economy catalog loader.

Presentation metadata (closed item kind, closed SVG icon key, closed rarity,
and a bounded Traditional Chinese summary) is registry-owned and read-only.
It is visual identity only: numeric combat, recovery, or comparison values
never enter this registry; the deterministic item-effect rulebooks in
``world/rules/rulebook/`` own every magnitude.

Item mechanics are the registry's only behavioral seam: an item declares
exactly one of an immutable use definition (``ItemUseMechanics``), an
equipment slot, or nothing at all. Presentation kind never selects or
modifies mechanics.

The single authored source is ``content/items/``: ``catalog.yaml`` names an
ordered list of slice files, each holding one ``items`` list. A usable row
authors its ordered effects under ``use_mechanics.effects`` and an equipment
row authors its dedicated ``equipment_effects`` mapping on the row itself.
:mod:`~world.lore.items.assembly` is the data-only reader that publishes the
definitions (``ITEM_REGISTRY``), per-key source provenance
(``ITEM_SOURCES``), and the raw inline effect inputs the two rules loaders
consume after lore has loaded.

Every name resolves through this package's namespace exactly as it always
has: consumers keep importing ``world.lore.items``. ``ITEM_REGISTRY`` is
re-exported live from the assembly (never rebound here), so in-place views of
that one dict stay visible through every import path.
"""

from world.lore.items.assembly import (
    CATALOG_DIRECTORY,
    CATALOG_FILENAME,
    ITEM_CATALOG,
    ITEM_EQUIPMENT_EFFECT_INPUTS,
    ITEM_REGISTRY,
    ITEM_SOURCES,
    ITEM_USE_EFFECT_INPUTS,
    ItemCatalog,
    ItemCatalogError,
    load_item_catalog,
)
from world.lore.items.vocab import (
    SUMMARY_MAX,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
    LiturgicalRole,
)

# Byte-identical old-module namespace parity: the single-module history's
# top-level imports are part of its observable surface (probes read the
# registry and EquipmentSlot through getattr string-concat seams, e.g.
# _equipment_rulebook_probes.py). These stay module-qualified so a package-path
# `patch(..., create=True)` can never silently replace the canonical objects.
from dataclasses import dataclass as dataclass  # noqa: F401  (old namespace name)
from enum import StrEnum as StrEnum  # noqa: F401
from world.skills.equipment import EquipmentSlot  # noqa: F401

__all__ = [
    "SUMMARY_MAX",
    "CATALOG_DIRECTORY",
    "CATALOG_FILENAME",
    "ITEM_CATALOG",
    "ITEM_EQUIPMENT_EFFECT_INPUTS",
    "ITEM_REGISTRY",
    "ITEM_SOURCES",
    "ITEM_USE_EFFECT_INPUTS",
    "ItemCatalog",
    "ItemCatalogError",
    "ItemDefinition",
    "ItemIconKey",
    "ItemKind",
    "ItemPresentation",
    "ItemRarity",
    "ItemUseMechanics",
    "LiturgicalRole",
    "load_item_catalog",
]
