"""Guild-owned reducing accessories; the exam policy owns their restrictions."""

from world.lore.items.vocab import (
    EquipmentModifierKey, ItemDefinition, ItemIconKey, ItemKind,
    ItemPresentation, ItemRarity,
)
from world.skills.equipment import EquipmentSlot

ROWS = tuple(
    ItemDefinition(
        key=f"guild_limit_{grade}",
        display_name_zh=f"公會 {grade.upper()} 級封印環",
        price_table_key="magic_accessory",
        sellable=False,
        guild_property=True,
        presentation=ItemPresentation(
            kind=ItemKind.ACCESSORY,
            icon_key=ItemIconKey.ACCESSORY,
            rarity=ItemRarity.COMMON,
            summary_zh="公會保管的封印環，供考官在考核時抑制力量。",
        ),
        equipment_slot=EquipmentSlot.ACCESSORY,
        modifier_key=EquipmentModifierKey(f"guild_limit_{grade}"),
    )
    for grade in ("e", "d", "c", "b")
)
