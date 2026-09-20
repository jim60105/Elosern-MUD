"""Item-domain catalogs: prices, items, and their rulebook-side effect profiles.
"""

from __future__ import annotations

from world.lore.economy import PriceEntry
from world.lore.items import (
    ItemDefinition,
    EquipmentModifierKey,
    EquipmentSlot,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
)
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemStat,
    ItemTargetScope,
)

from world.tests.synthetic_data.vocab import _first_equipment_modifier_key

# ---------------------------------------------------------------------------
# Catalogs (design D1): a few representative entries each, real dataclasses.
# Growth happens in migration changes through the make_* factories.
# ---------------------------------------------------------------------------

SYNTH_PRICES: dict[str, PriceEntry] = {
    "t_spruce_lodging": PriceEntry(
        "t_spruce_lodging", "雲杉驛站一晚", 18, 18, "One synthetic inn night."
    ),
    "t_mossmeals": PriceEntry(
        "t_mossmeals", "苔徑簡餐", 6, 12, "One synthetic meal."
    ),
    "t_ironbite_steel": PriceEntry(
        "t_ironbite_steel", "鐵牙制式武裝", 120, 600, "A synthetic weapon band."
    ),
    "t_huskapples": PriceEntry(
        "t_huskapples", "燼殼果實", 20, None, "Open-ended synthetic material price."
    ),
}

SYNTH_ITEMS: dict[str, ItemDefinition] = {
    "t_ember_spray": ItemDefinition(
        key="t_ember_spray",
        display_name_zh="熾焰噴射劑",
        price_table_key="t_mossmeals",
        sellable=True,
        presentation=ItemPresentation(
            kind=ItemKind.POTION,
            icon_key=ItemIconKey.POTION,
            rarity=ItemRarity.COMMON,
            summary_zh="噴灑時散發橘紅霧氣的合成藥劑。",
        ),
        use_mechanics=ItemUseMechanics(
            consumable=True,
            combat_allowed=True,
        ),
    ),
    "t_iron_fang": ItemDefinition(
        key="t_iron_fang",
        display_name_zh="鐵牙短刃",
        price_table_key="t_ironbite_steel",
        sellable=True,
        presentation=ItemPresentation(
            kind=ItemKind.WEAPON,
            icon_key=ItemIconKey.WEAPON,
            rarity=ItemRarity.UNCOMMON,
            summary_zh="以鍛鐵鋸齒打造的合成短刃。",
        ),
    ),
    # Slotted gear: the starting-kit validator requires every kit item to
    # carry an equipment slot, and every slotted item to bind one member of
    # the closed shipped modifier enum — borrowed at runtime, never named.
    # The synthetic key itself is unbound in the shipped rulebook, so no
    # scoped consumer resolves an effect layer through this gear.
    "t_thorn_knife": ItemDefinition(
        key="t_thorn_knife",
        display_name_zh="荊刺小刀",
        price_table_key="t_ironbite_steel",
        sellable=True,
        presentation=ItemPresentation(
            kind=ItemKind.WEAPON,
            icon_key=ItemIconKey.WEAPON,
            rarity=ItemRarity.COMMON,
            summary_zh="刀刃帶刺的合成入門短刀。",
        ),
        equipment_slot=EquipmentSlot.WEAPON_MAIN,
        modifier_key=_first_equipment_modifier_key(),
    ),
    "t_wayfarer_pass": ItemDefinition(
        key="t_wayfarer_pass",
        display_name_zh="行旅通行證",
        price_table_key="t_spruce_lodging",
        sellable=False,
        presentation=ItemPresentation(
            kind=ItemKind.MISC,
            icon_key=ItemIconKey.MISC,
            rarity=ItemRarity.COMMON,
            summary_zh="蓋著合成驛站印信的行旅憑證。",
        ),
    ),
    "t_huskapple": ItemDefinition(
        key="t_huskapple",
        display_name_zh="燼殼果",
        price_table_key="t_huskapples",
        sellable=True,
        presentation=ItemPresentation(
            kind=ItemKind.MATERIAL,
            icon_key=ItemIconKey.MATERIAL,
            rarity=ItemRarity.COMMON,
            summary_zh="外殼如冷燼的合成素材果實。",
        ),
    ),
}

# The rulebook-side half of every usable kit row: settlement resolves an
# item's effects by ITEM key through the live profile map, so a scoped item
# registry without scoped profiles would leave the kit's one usable row with
# no declared effect. Local fixtures that add their own usable items register
# their own profiles through the same logical target via ``extra=``.
SYNTH_ITEM_EFFECT_PROFILES: dict[str, ItemEffectProfile] = {
    "t_ember_spray": ItemEffectProfile(
        # The explicit self scope is load-bearing now that preflight routes
        # every effect through the shared resolver: it marks the kit's
        # healing row as one the targeting pipeline binds to the actor.
        effects=(GaugeAdjustEffect(stat=ItemStat.HP, amount=40, scope=ItemTargetScope.SELF),)
    ),
}
