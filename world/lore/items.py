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


class EquipmentModifierKey(StrEnum):
    """Closed vocabulary of equipment-effect modifier keys.

    Each key binds one equipment-slot item definition to exactly one entry in
    the equipment-effect rulebook; magnitudes never live in this registry.
    The value of every member is the item key it binds; the validated loader
    in ``world/rules/equipment_effects.py`` rejects any unbound key, orphaned
    rulebook entry, or duplicated binding at startup.
    """

    APPRENTICE_FOCUS_STAFF = "apprentice_focus_staff"
    APOTHECARY_BEADS = "apothecary_beads"
    ARCHMAGE_MENDING_ROBE = "archmage_mending_robe"
    ASHEN_SCIMITAR = "ashen_scimitar"
    BLACK_MAID_DRESS = "black_maid_dress"
    CHAINMAIL = "chainmail"
    CRESCENT_EARRING = "crescent_earring"
    DARK_ELF_KIMONO = "dark_elf_kimono"
    DARK_ELF_NINJA_GARB = "dark_elf_ninja_garb"
    ELVEN_TRADITIONAL_ROBE = "elven_traditional_robe"
    ENTICING_LACE_SET = "enticing_lace_set"
    FEARLESS_BROOCH = "fearless_brooch"
    GILDED_SABER = "gilded_saber"
    GLIDING_CLOAK = "gliding_cloak"
    GREAT_AXE = "great_axe"
    GUILD_RECRUIT_BADGE = "guild_recruit_badge"
    HUNTERS_LONGBOW = "hunters_longbow"
    HUNTING_THROWING_AXE = "hunting_throwing_axe"
    IRON_DAGGER = "iron_dagger"
    IRON_SHIELD = "iron_shield"
    KNIGHT_BLADE = "knight_blade"
    KNIGHT_PLATEMAIL = "knight_platemail"
    LEATHER_ARMOR = "leather_armor"
    MAGE_ROBE = "mage_robe"
    MAGIC_SWORD = "magic_sword"
    PASSION_SILK_CHOKER = "passion_silk_choker"
    PILGRIM_MEDALLION = "pilgrim_medallion"
    PLAIN_SWORD = "plain_sword"
    PRISM_CHARM = "prism_charm"
    PROTECTIVE_RING = "protective_ring"
    PURIFIED_PENDANT = "purified_pendant"
    RADIANT_HOLY_EMBLEM = "radiant_holy_emblem"
    ROSE_CREST_RAPIER = "rose_crest_rapier"
    ROYAL_HEIRLOOM_PENDANT = "royal_heirloom_pendant"
    ROYAL_SIGNET_RING = "royal_signet_ring"
    SAINTESS_VESTMENTS = "saintess_vestments"
    SISTER_VESTMENTS = "sister_vestments"
    SHADOW_BLADE = "shadow_blade"
    SHADOW_BLADE_ECHO = "shadow_blade_echo"
    SILVER_FEATHER_EARRING = "silver_feather_earring"
    SILVER_HAIRPIN = "silver_hairpin"
    STEEL_FANG_DAGGER = "steel_fang_dagger"
    STORAGE_POUCH = "storage_pouch"
    WOLF_FANG_NECKLACE = "wolf_fang_necklace"
    WOODEN_CLUB = "wooden_club"


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
    An equipment-slot item must additionally carry exactly one
    ``EquipmentModifierKey`` member; the equipment-effect rulebook load
    then enforces that its value equals the item key (registered items may
    not borrow another item's binding).
    """

    key: str
    display_name_zh: str
    price_table_key: str
    sellable: bool
    presentation: ItemPresentation
    use_mechanics: ItemUseMechanics | None = None
    equipment_slot: EquipmentSlot | None = None
    modifier_key: EquipmentModifierKey | None = None

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
        if self.modifier_key is not None and self.equipment_slot is None:
            raise ValueError(
                f"item {self.key!r} declares a modifier key without an "
                "equipment slot; only equipment can bind rulebook effects"
            )
        if self.equipment_slot is not None and self.modifier_key is None:
            raise ValueError(
                f"item {self.key!r} declares an equipment slot without a "
                "modifier key; every equipment definition binds exactly one "
                "rulebook entry"
            )
        if self.modifier_key is not None and not isinstance(
            self.modifier_key, EquipmentModifierKey
        ):
            raise ValueError(
                f"item {self.key!r} modifier_key must be an "
                f"EquipmentModifierKey member, got {self.modifier_key!r}"
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
            modifier_key=EquipmentModifierKey.PLAIN_SWORD,
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
            modifier_key=EquipmentModifierKey.IRON_DAGGER,
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
            modifier_key=EquipmentModifierKey.HUNTING_THROWING_AXE,
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
            modifier_key=EquipmentModifierKey.HUNTERS_LONGBOW,
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
            modifier_key=EquipmentModifierKey.APPRENTICE_FOCUS_STAFF,
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
            modifier_key=EquipmentModifierKey.KNIGHT_BLADE,
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
            modifier_key=EquipmentModifierKey.WOODEN_CLUB,
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
            modifier_key=EquipmentModifierKey.GILDED_SABER,
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
            modifier_key=EquipmentModifierKey.GREAT_AXE,
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
            modifier_key=EquipmentModifierKey.ASHEN_SCIMITAR,
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
            modifier_key=EquipmentModifierKey.STEEL_FANG_DAGGER,
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
            modifier_key=EquipmentModifierKey.MAGIC_SWORD,
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
            modifier_key=EquipmentModifierKey.LEATHER_ARMOR,
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
            modifier_key=EquipmentModifierKey.MAGE_ROBE,
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
            modifier_key=EquipmentModifierKey.CHAINMAIL,
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
            modifier_key=EquipmentModifierKey.IRON_SHIELD,
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
            modifier_key=EquipmentModifierKey.SILVER_HAIRPIN,
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
            modifier_key=EquipmentModifierKey.WOLF_FANG_NECKLACE,
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
            modifier_key=EquipmentModifierKey.PILGRIM_MEDALLION,
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
            modifier_key=EquipmentModifierKey.PRISM_CHARM,
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
            modifier_key=EquipmentModifierKey.PROTECTIVE_RING,
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
            modifier_key=EquipmentModifierKey.STORAGE_POUCH,
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
            modifier_key=EquipmentModifierKey.GLIDING_CLOAK,
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
            modifier_key=EquipmentModifierKey.ELVEN_TRADITIONAL_ROBE,
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
            modifier_key=EquipmentModifierKey.ROYAL_SIGNET_RING,
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
            modifier_key=EquipmentModifierKey.ROYAL_HEIRLOOM_PENDANT,
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
            modifier_key=EquipmentModifierKey.ROSE_CREST_RAPIER,
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
            modifier_key=EquipmentModifierKey.BLACK_MAID_DRESS,
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
            modifier_key=EquipmentModifierKey.SILVER_FEATHER_EARRING,
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
            modifier_key=EquipmentModifierKey.CRESCENT_EARRING,
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
            modifier_key=EquipmentModifierKey.DARK_ELF_KIMONO,
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
            modifier_key=EquipmentModifierKey.SHADOW_BLADE,
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
            modifier_key=EquipmentModifierKey.SHADOW_BLADE_ECHO,
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
            modifier_key=EquipmentModifierKey.DARK_ELF_NINJA_GARB,
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
            modifier_key=EquipmentModifierKey.GUILD_RECRUIT_BADGE,
        ),
        ItemDefinition(
            key="purified_pendant",
            display_name_zh="淨化吊墜",
            price_table_key="magic_accessory",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.RARE,
                summary_zh="牧師以聖水反覆洗禮的銀質吊墜，據說能隔絕瘴毒。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.PURIFIED_PENDANT,
        ),
        ItemDefinition(
            key="fearless_brooch",
            display_name_zh="無懼胸針",
            price_table_key="magic_accessory",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.RARE,
                summary_zh="獵魔人佩戴的赤鐵胸針，佩戴者無視恐懼的低語。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.FEARLESS_BROOCH,
        ),
        ItemDefinition(
            key="knight_platemail",
            display_name_zh="騎士全套板甲",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.RARE,
                summary_zh="騎士團儀仗用的全身板甲，防護全面但極為沉重。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.KNIGHT_PLATEMAIL,
        ),
        ItemDefinition(
            key="apothecary_beads",
            display_name_zh="藥師珠串",
            price_table_key="jewelry",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="草藥師以藥草樹脂煉成的珠串，溫潤的氣息緩緩滋養身體。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.APOTHECARY_BEADS,
        ),
        ItemDefinition(
            key="archmage_mending_robe",
            display_name_zh="大術師補綴長袍",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.EPIC,
                summary_zh="內裡縫滿回復符文的學者長袍，施法時法力的耗損明顯減輕。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.ARCHMAGE_MENDING_ROBE,
        ),
        ItemDefinition(
            key="enticing_lace_set",
            display_name_zh="誘蠱蕾絲內衣",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="黑市流傳的紫色蕾絲內衣，穿者舉手投足自帶挑逗的氣息。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.ENTICING_LACE_SET,
        ),
        ItemDefinition(
            key="passion_silk_choker",
            display_name_zh="迷情絲頸環",
            price_table_key="jewelry",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.EPIC,
                summary_zh="浸過迷情藥的深紅絲絨頸環，肌膚愈親近，感官愈熾熱。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.PASSION_SILK_CHOKER,
        ),
        ItemDefinition(
            key="sister_vestments",
            display_name_zh="修女聖袍",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="光明教會修女的白銀聖袍，祈禱時聖光會輕撫傷口的所在。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.SISTER_VESTMENTS,
        ),
        ItemDefinition(
            key="radiant_holy_emblem",
            display_name_zh="光輝聖徽",
            price_table_key="magic_accessory",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.RARE,
                summary_zh="牧師祝禱的日輪聖徽，聖光為虔信者癒傷驅邪。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.RADIANT_HOLY_EMBLEM,
        ),
        ItemDefinition(
            key="saintess_vestments",
            display_name_zh="聖女聖袍",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.EPIC,
                summary_zh="傳說由聖女親手繡製的祭儀聖袍，聖寵如光暈環繞穿戴之人。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.SAINTESS_VESTMENTS,
        ),
    )
}
