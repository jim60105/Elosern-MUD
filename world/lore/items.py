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
"""

from dataclasses import dataclass
from enum import StrEnum

from world.skills.equipment import EquipmentSlot

# Player-facing item summaries are bounded; the bound mirrors the
# skill-registry label contract.
SUMMARY_MAX = 128


class ItemKind(StrEnum):
    """Closed item-category vocabulary owned by the lore registry."""

    FOOD = "food"
    POTION = "potion"
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    AMMUNITION = "ammunition"
    TOOL = "tool"
    MATERIAL = "material"
    MISC = "misc"


class ItemIconKey(StrEnum):
    """Closed local-SVG icon vocabulary.

    The Vue renderer maps each key to a self-hosted inline SVG; the registry
    never carries raw SVG, image URLs, CSS values, or emoji.
    """

    FOOD = "food"
    POTION = "potion"
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    AMMUNITION = "ammunition"
    TOOL = "tool"
    MATERIAL = "material"
    MISC = "misc"


class ItemRarity(StrEnum):
    """Closed rarity vocabulary used for visual treatment only.

    Rarity is a presentation classification, not a balance multiplier; it must
    not feed prices, stock, loot odds, or combat until a reviewed rules
    contract owns that behavior.
    """

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class ItemEffectKey(StrEnum):
    """Closed vocabulary of deterministic item-effect keys.

    Each key binds a usable-item definition to one entry in the item-effect
    rulebook; magnitudes and conditions never live in this registry. The
    loader in ``world/rules/items.py`` rejects any registered key without a
    canonical rulebook entry.
    """

    SELF_HEAL = "self_heal"
    GREATER_HEAL = "greater_heal"
    MANA_RESTORE = "mana_restore"


@dataclass(frozen=True)
class ItemUseMechanics:
    """The immutable use semantics of one registered consumable or reusable."""

    effect_key: ItemEffectKey
    consumable: bool
    combat_allowed: bool

    def __post_init__(self) -> None:
        """Enforce the closed effect vocabulary and boolean flags."""
        if not isinstance(self.effect_key, ItemEffectKey):
            raise ValueError(
                f"effect_key must be an ItemEffectKey member, got {self.effect_key!r}"
            )
        for name in ("consumable", "combat_allowed"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be a boolean")


@dataclass(frozen=True)
class ItemPresentation:
    """The frozen visual identity of one registered item."""

    kind: ItemKind
    icon_key: ItemIconKey
    rarity: ItemRarity
    summary_zh: str

    def __post_init__(self) -> None:
        """Enforce the closed presentation contracts at construction time."""
        for value, vocabulary in (
            (self.kind, ItemKind),
            (self.icon_key, ItemIconKey),
            (self.rarity, ItemRarity),
        ):
            if not isinstance(value, vocabulary):
                raise ValueError(
                    f"{vocabulary.__name__} member required, got {value!r}"
                )
        if not isinstance(self.summary_zh, str) or not self.summary_zh.strip():
            raise ValueError("summary_zh must be a non-empty string")
        if sum(1 for _ in self.summary_zh) > SUMMARY_MAX:
            raise ValueError(f"summary_zh exceeds {SUMMARY_MAX} code points")
        if any(breaker in self.summary_zh for breaker in ("\r", "\n", "\u2028", "\u2029")):
            raise ValueError("summary_zh must be a single line of plain text")
        if "<" in self.summary_zh:
            raise ValueError("summary_zh must not contain markup")
        if (
            "://" in self.summary_zh
            or self.summary_zh.startswith("//")
            or " //" in self.summary_zh
        ):
            raise ValueError("summary_zh must not contain URL forms")
        if any(
            0x2600 <= ord(ch) <= 0x27BF
            or 0x1F000 <= ord(ch) <= 0x1FAFF
            or 0x1F1E6 <= ord(ch) <= 0x1F1FF
            or ch in ("\u200d", "\u20e3", "\ufe0f")
            for ch in self.summary_zh
        ):
            raise ValueError("summary_zh must not contain emoji or emoji sequence parts")


@dataclass(frozen=True)
class ItemDefinition:
    """The immutable identity of one supported inventory item.

    Exactly one of ``use_mechanics`` or ``equipment_slot`` may be present;
    an item carrying neither is inspect-only. The pair is validated at
    construction so an ambiguous definition can never be presented or used.
    """

    key: str
    display_name_zh: str
    price_table_key: str
    sellable: bool
    presentation: ItemPresentation
    use_mechanics: ItemUseMechanics | None = None
    equipment_slot: EquipmentSlot | None = None

    def __post_init__(self) -> None:
        """Require the frozen presentation object and exclusive mechanics."""
        if not isinstance(self.presentation, ItemPresentation):
            raise ValueError(
                f"item {self.key!r} presentation must be an ItemPresentation"
            )
        if self.use_mechanics is not None and self.equipment_slot is not None:
            raise ValueError(
                f"item {self.key!r} declares both use mechanics and an "
                "equipment slot; the forms are mutually exclusive"
            )
        if self.use_mechanics is not None and not isinstance(
            self.use_mechanics, ItemUseMechanics
        ):
            raise ValueError(
                f"item {self.key!r} use_mechanics must be an ItemUseMechanics"
            )
        if self.equipment_slot is not None and not isinstance(
            self.equipment_slot, EquipmentSlot
        ):
            raise ValueError(
                f"item {self.key!r} equipment_slot must be an EquipmentSlot "
                f"member, got {self.equipment_slot!r}"
            )


ITEM_REGISTRY: dict[str, ItemDefinition] = {
    definition.key: definition
    for definition in (
        ItemDefinition(
            key="meal",
            display_name_zh="普通餐食",
            price_table_key="meal",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.COMMON,
                summary_zh="供旅人充飢的普通餐食。",
            ),
        ),
        ItemDefinition(
            key="healing_potion",
            display_name_zh="治療藥水",
            price_table_key="potion",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.POTION,
                icon_key=ItemIconKey.POTION,
                rarity=ItemRarity.RARE,
                summary_zh="盛裝於小瓶中的治療藥水。",
            ),
            use_mechanics=ItemUseMechanics(
                effect_key=ItemEffectKey.SELF_HEAL,
                consumable=True,
                combat_allowed=True,
            ),
        ),
        ItemDefinition(
            key="plain_sword",
            display_name_zh="普通劍",
            price_table_key="plain_sword",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.COMMON,
                summary_zh="鍛鐵打造的普通劍。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="iron_dagger",
            display_name_zh="鐵短刀",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.COMMON,
                summary_zh="王國鍛坊量產的輕便副手短刀。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_OFF,
        ),
        ItemDefinition(
            key="hunting_throwing_axe",
            display_name_zh="狩獵擲斧",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.COMMON,
                summary_zh="獸王國獵手常用的短柄擲斧。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_OFF,
        ),
        ItemDefinition(
            key="hunters_longbow",
            display_name_zh="獵手長弓",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="獸王國獸材層壓製成的獵用長弓。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="apprentice_focus_staff",
            display_name_zh="見習術師法杖",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOOL,
                icon_key=ItemIconKey.TOOL,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="帝國魔法學院見習生使用的導魔長杖。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="knight_blade",
            display_name_zh="騎士制式長劍",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="王國騎士團制式長劍，鍛造紮實。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="wooden_club",
            display_name_zh="木製棍棒",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.COMMON,
                summary_zh="農具房改製的堅硬木製棍棒。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="gilded_saber",
            display_name_zh="鍍金軍刀",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="貴族隨身佩戴的鍍金細軍刀。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="great_axe",
            display_name_zh="雙手巨斧",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="熊人戰士慣用的沉重雙手巨斧。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="ashen_scimitar",
            display_name_zh="灰燼彎刀",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="基亞蘭族鍛於餘燼之火的彎刀。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="steel_fang_dagger",
            display_name_zh="鋼牙短刀",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="貓科獵手慣用的銳利主手短刀。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="magic_sword",
            display_name_zh="魔導長劍",
            price_table_key="magic_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.EPIC,
                summary_zh="附魔師傅導入元素精萃的魔導劍。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="leather_armor",
            display_name_zh="皮甲",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.COMMON,
                summary_zh="冒險者入門的硬化皮革胸甲。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
        ),
        ItemDefinition(
            key="mage_robe",
            display_name_zh="術師長袍",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="織入護法絲的術師長袍。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
        ),
        ItemDefinition(
            key="chainmail",
            display_name_zh="鎖子甲",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="王國工坊編釘的細環鎖子甲。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
        ),
        ItemDefinition(
            key="iron_shield",
            display_name_zh="鐵盾",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.COMMON,
                summary_zh="新兵制式的圓面鐵盾。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_OFF,
        ),
        ItemDefinition(
            key="silver_hairpin",
            display_name_zh="銀髮簪",
            price_table_key="jewelry",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.COMMON,
                summary_zh="市井常見的細銀髮簪。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="wolf_fang_necklace",
            display_name_zh="狼牙項鍊",
            price_table_key="jewelry",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="獸人成年禮獵得狼牙製成的項鍊。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="pilgrim_medallion",
            display_name_zh="朝聖者銅符",
            price_table_key="jewelry",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="光明教會信眾佩戴的銅製聖徽。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="prism_charm",
            display_name_zh="三稜晶符",
            price_table_key="magic_accessory",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="伊歐拉斯族淬夢磨製的三稜晶飾符。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="protective_ring",
            display_name_zh="防禦戒指",
            price_table_key="magic_accessory",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.EPIC,
                summary_zh="鑲有結晶的稀有防禦魔導戒指。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="storage_pouch",
            display_name_zh="儲物袋",
            price_table_key="magic_accessory",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.RARE,
                summary_zh="帝國壟斷的空間魔法小袋。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="gliding_cloak",
            display_name_zh="滑翔斗篷",
            price_table_key="magic_accessory",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.EPIC,
                summary_zh="以蛛絲編織的稀有滑翔斗篷。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="magic_lamp",
            display_name_zh="魔法燈",
            price_table_key="tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOOL,
                icon_key=ItemIconKey.TOOL,
                rarity=ItemRarity.COMMON,
                summary_zh="持續發光的常見魔法照明燈。",
            ),
        ),
        ItemDefinition(
            key="healing_herb",
            display_name_zh="止血藥草",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.COMMON,
                summary_zh="採集任務常見的止血藥草。",
            ),
        ),
        ItemDefinition(
            key="rough_iron_ore",
            display_name_zh="粗鐵礦",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.COMMON,
                summary_zh="獸王國出口的未精煉鐵礦。",
            ),
        ),
        ItemDefinition(
            key="beast_crystal",
            display_name_zh="魔獸結晶",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.RARE,
                summary_zh="魔獸掉落、可製魔法道具的結晶。",
            ),
        ),
        ItemDefinition(
            key="evernight_shard",
            display_name_zh="永夜碎片",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.RARE,
                summary_zh="永夜迷宮深層採得的黑暗晶核碎片。",
            ),
        ),
        ItemDefinition(
            key="mana_core",
            display_name_zh="魔導晶核",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.RARE,
                summary_zh="魔導遺跡出土的高密度魔力晶核。",
            ),
        ),
        ItemDefinition(
            key="dragon_scale_fragment",
            display_name_zh="龍鱗碎片",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.EPIC,
                summary_zh="龍之巢穴尋得的龍鱗殘片。",
            ),
        ),
        ItemDefinition(
            key="elven_spider_silk",
            display_name_zh="精靈蛛絲",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.EPIC,
                summary_zh="傳自精靈族的輕韌蛛絲織料。",
            ),
        ),
        ItemDefinition(
            key="baptismal_holy_water",
            display_name_zh="受洗聖水",
            price_table_key="potion",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.POTION,
                icon_key=ItemIconKey.POTION,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="光明教會祝禱的受洗聖水。",
            ),
            use_mechanics=ItemUseMechanics(
                effect_key=ItemEffectKey.SELF_HEAL,
                consumable=True,
                combat_allowed=True,
            ),
        ),
        ItemDefinition(
            key="greater_healing_potion",
            display_name_zh="強效治療藥水",
            price_table_key="potion",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.POTION,
                icon_key=ItemIconKey.POTION,
                rarity=ItemRarity.RARE,
                summary_zh="濃縮煉製的高階治療藥劑。",
            ),
            use_mechanics=ItemUseMechanics(
                effect_key=ItemEffectKey.GREATER_HEAL,
                consumable=True,
                combat_allowed=True,
            ),
        ),
        ItemDefinition(
            key="mana_potion",
            display_name_zh="魔力藥水",
            price_table_key="potion",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.POTION,
                icon_key=ItemIconKey.POTION,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="恢復魔力的藍色藥劑。",
            ),
            use_mechanics=ItemUseMechanics(
                effect_key=ItemEffectKey.MANA_RESTORE,
                consumable=True,
                combat_allowed=True,
            ),
        ),
        ItemDefinition(
            key="elven_traditional_robe",
            display_name_zh="精靈傳統服飾",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.LEGENDARY,
                summary_zh="精靈族的白色蛛絲傳統服飾。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
        ),
        ItemDefinition(
            key="royal_signet_ring",
            display_name_zh="王室紋章細金戒指",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.RARE,
                summary_zh="嵌有王室紋章的細金戒指。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="royal_heirloom_pendant",
            display_name_zh="王室紋章吊墜",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.RARE,
                summary_zh="王室的紋章吊墜，貼身攜帶。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="rose_crest_rapier",
            display_name_zh="王室薔薇紋章輕劍",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.EPIC,
                summary_zh="劍柄刻有王室薔薇紋章的輕劍。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="black_maid_dress",
            display_name_zh="黑色女僕裝",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="貼身侍女的黑白女僕裝。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
        ),
        ItemDefinition(
            key="silver_feather_earring",
            display_name_zh="銀羽耳環",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.RARE,
                summary_zh="形如銀羽的耳環，從未離身。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="crescent_earring",
            display_name_zh="月牙耳環",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.EPIC,
                summary_zh="精靈族匠作的月牙形耳環。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
        ItemDefinition(
            key="dark_elf_kimono",
            display_name_zh="黑暗精靈傳統服飾",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.EPIC,
                summary_zh="基亞蘭族的墨黑短和服傳統服飾。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
        ),
        ItemDefinition(
            key="shadow_blade",
            display_name_zh="暗影鋼刀",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.LEGENDARY,
                summary_zh="暗影鋼鍛成的雙刀之一，主手刀。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
        ),
        ItemDefinition(
            key="shadow_blade_echo",
            display_name_zh="暗影鋼刀·影",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.LEGENDARY,
                summary_zh="暗影鋼鍛成的雙刀之一，副手影刀。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_OFF,
        ),
        ItemDefinition(
            key="dark_elf_ninja_garb",
            display_name_zh="黑暗精靈戰鬥服飾",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.EPIC,
                summary_zh="基亞蘭族的墨黑戰鬥服飾。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
        ),
        ItemDefinition(
            key="guild_recruit_badge",
            display_name_zh="公會見習徽記",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.MISC,
                rarity=ItemRarity.COMMON,
                summary_zh="冒險者公會發放的新人徽記。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
        ),
    )
}
