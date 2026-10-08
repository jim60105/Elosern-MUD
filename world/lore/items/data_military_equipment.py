"""Shared mass-produced military equipment; effect magnitudes belong to rules."""

from world.lore.items.vocab import (
    EquipmentModifierKey, ItemDefinition, ItemIconKey, ItemKind,
    ItemPresentation, ItemRarity,
)
from world.skills.equipment import EquipmentSlot

# Grade describes manufacture and supply. Rarity selects an existing authoring
# budget; it grants neither a purchase gate nor a runtime multiplier.
_ROWS = (
    ("e", "新兵", ItemRarity.COMMON, "鍛坊量產的新兵裝備，結構簡潔。"),
    ("d", "步兵", ItemRarity.UNCOMMON, "鍛坊量產的步兵裝備，適合長途行軍。"),
    ("c", "遊騎兵", ItemRarity.UNCOMMON, "鍛坊量產的遊騎兵裝備，兼顧防護與靈活。"),
    ("b", "符文老兵", ItemRarity.RARE, "軍械庫以制式符文附魔量產的老兵裝備。"),
    ("a", "軍械騎士", ItemRarity.EPIC, "軍械庫以制式附魔量產的騎士裝備。"),
    ("s", "軍械統帥", ItemRarity.LEGENDARY, "軍械庫以高階制式附魔量產的統帥裝備。"),
)

ROWS: tuple[ItemDefinition, ...] = tuple(
    ItemDefinition(
        key=f"military_{grade}_{shape}",
        display_name_zh=f"{name}{label}",
        price_table_key=(
            ("magic_weapon" if shape == "sword" else "magic_armor")
            if grade in "bas" else
            ("mundane_weapon" if shape == "sword" else "armor")
        ),
        sellable=True,
        presentation=ItemPresentation(
            kind=kind, icon_key=icon, rarity=rarity, summary_zh=summary,
        ),
        equipment_slot=slot,
        modifier_key=EquipmentModifierKey(f"military_{grade}_{shape}"),
    )
    for grade, name, rarity, summary in _ROWS
    for shape, label, kind, icon, slot in (
        ("sword", "軍劍", ItemKind.WEAPON, ItemIconKey.WEAPON, EquipmentSlot.WEAPON_MAIN),
        ("armor", "軍甲", ItemKind.ARMOR, ItemIconKey.ARMOR, EquipmentSlot.ARMOR),
    )
)
