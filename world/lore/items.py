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
    TOY = "toy"


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
    TOY = "toy"


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
    BEASTFOLK_GALE_EARRING = "beastfolk_gale_earring"
    BEASTFOLK_HEAVY_HIDE_ARMOR = "beastfolk_heavy_hide_armor"
    BEASTFOLK_REPEATING_BOW = "beastfolk_repeating_bow"
    BEASTFOLK_SPIRIT_WAND = "beastfolk_spirit_wand"
    BEASTFOLK_STALKER_GARB = "beastfolk_stalker_garb"
    BEASTFOLK_TRIBAL_TOTEM = "beastfolk_tribal_totem"
    BEASTFOLK_TWIN_CLAWS = "beastfolk_twin_claws"
    BEASTFOLK_WAR_SPEAR = "beastfolk_war_spear"
    BEASTFOLK_WARHAMMER = "beastfolk_warhammer"
    BLACK_MAID_DRESS = "black_maid_dress"
    CHAINMAIL = "chainmail"
    CRESCENT_EARRING = "crescent_earring"
    DARK_ELF_KIMONO = "dark_elf_kimono"
    DARK_ELF_NINJA_GARB = "dark_elf_ninja_garb"
    DRAGON_LAIR_TROPHY_BLADE = "dragon_lair_trophy_blade"
    ELVEN_FOREST_VEIL = "elven_forest_veil"
    ELVEN_LONGBOW = "elven_longbow"
    ELVEN_TRADITIONAL_ROBE = "elven_traditional_robe"
    ENTICING_LACE_SET = "enticing_lace_set"
    FEARLESS_BROOCH = "fearless_brooch"
    GILDED_SABER = "gilded_saber"
    GLIDING_CLOAK = "gliding_cloak"
    GREAT_AXE = "great_axe"
    GUILD_RECRUIT_BADGE = "guild_recruit_badge"
    HUNTERS_LONGBOW = "hunters_longbow"
    HUNTING_THROWING_AXE = "hunting_throwing_axe"
    HYPERESTHESIA_CHARM = "hyperesthesia_charm"
    IRON_DAGGER = "iron_dagger"
    IRON_SHIELD = "iron_shield"
    KNIGHT_BLADE = "knight_blade"
    KNIGHT_PLATEMAIL = "knight_platemail"
    LEATHER_ARMOR = "leather_armor"
    MAGE_ROBE = "mage_robe"
    MAGIC_SWORD = "magic_sword"
    NYMPH_BUDS_CLAMP = "nymph_buds_clamp"
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
    TREMOR_CRYSTAL = "tremor_crystal"
    WARM_HONEY_ORB = "warm_honey_orb"
    WARMTH_RUNE_EGG = "warmth_rune_egg"
    WOLF_FANG_NECKLACE = "wolf_fang_necklace"
    WOODEN_CLUB = "wooden_club"


@dataclass(frozen=True)
class ItemUseMechanics:
    """The immutable use semantics of one registered consumable or reusable.

    What a use *does* is declared in the item-effect rulebook keyed by the
    item key (``world/rules/item_effects.py``); this record only states that
    the item can be used and what a use costs structurally — effects never
    live in this registry (item-effect-model design §3.1).
    """

    consumable: bool
    combat_allowed: bool

    def __post_init__(self) -> None:
        """Enforce the boolean flags."""
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
                summary_zh="獸人戰士慣用的沉重雙手巨斧。",
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
                summary_zh="精靈鍛於餘燼之火的彎刀。",
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
                summary_zh="獸人獵手慣用的銳利主手短刀。",
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
                summary_zh="精靈淬夢磨製的三稜晶飾符。",
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
                summary_zh="光明教會祝禱的受洗聖水，能移除身上所有負面狀態。",
            ),
            use_mechanics=ItemUseMechanics(
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
                summary_zh="精靈族的白色蛛絲傳統服飾，精靈村商店的鎮店商品，「以坦露為聖」文化的具體體現。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.ELVEN_TRADITIONAL_ROBE,
        ),
        ItemDefinition(
            key="royal_signet_ring",
            display_name_zh="薇歐蕾特的誕生細金戒",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.RARE,
                summary_zh="王室在長女誕生之年打造的紋章細金戒，全王國只鍛了這一枚；她右手無名指佩戴的細金戒指，是隨身攜帶的唯一身分象徵。",
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
                summary_zh="王室的紋章吊墜，代代相傳、貼身攜帶，象徵王室血脈的延續。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.ROYAL_HEIRLOOM_PENDANT,
        ),
        ItemDefinition(
            key="rose_crest_rapier",
            display_name_zh="薇歐蕾特親刻薔薇輕劍",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.EPIC,
                summary_zh="劍柄末端刻有薇歐蕾特親手雕的王室薔薇紋章——紋章出自王女之手，全大陸獨一無二，是主僕情誼的信物。",
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
                summary_zh="侍女常見的黑白女僕裝，貼身剪裁自帶服從的暗示。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.BLACK_MAID_DRESS,
        ),
        ItemDefinition(
            key="silver_feather_earring",
            display_name_zh="十二歲的銀羽",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.RARE,
                summary_zh="薇歐蕾特十二歲那年親贈的銀羽耳環，自贈與那日起從未摘下；名字本身就是一段年月。",
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
                summary_zh="精靈匠作的月牙形耳環，精靈工藝的代表作，精靈村商店的定番首飾。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.CRESCENT_EARRING,
        ),
        ItemDefinition(
            key="dark_elf_kimono",
            display_name_zh="精靈短袍傳統服飾",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.EPIC,
                summary_zh="精靈的墨黑短袍傳統服飾，以遊女為原型的族群服裝美學，精靈村商店的現成品。",
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
            display_name_zh="精靈戰鬥服飾",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.EPIC,
                summary_zh="精靈的墨黑戰鬥服飾，以忍者為原型的族群服裝美學，兼顧行動力，精靈村商店的現成品。",
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
                summary_zh="公會登錄時發給的見習徽記，是公會承認的身分證明；不可轉讓、不可交易，配戴時防禦 +1。",
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
                rarity=ItemRarity.RARE,
                summary_zh="光明教會修女的白銀聖袍：前襟自鎖骨一路開到臍下，兩側腰身只以聖徽細鏈相連，下襬分襬讓腿根全無遮擋，裙下從不著寸縷——聖職服儀刻意做成這副模樣，修女隨時掀開下襬就能被按在祭壇邊行房，體現以坦露為聖的教義精神。",
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
                rarity=ItemRarity.LEGENDARY,
                summary_zh="傳說由聖女親手繡製的祭儀聖袍：近乎透明的聖絲只護住肩頸與背脊，胸口自鎖骨以下的起伏一覽無遺，腰間懸鈴不繫帶，分襬開至腰際，裙下的聖光裡什麼都不藏；聖女只領受、不施予，高潮本身就是公開的祝福奇蹟，聖寵如光暈環繞穿戴之人。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.SAINTESS_VESTMENTS,
        ),
        # Inspect-only lore codex items: 6 Foods (land-lore-inspect-only-items D2)
        ItemDefinition(
            key="kingdom_rye_hardtack",
            display_name_zh="王國黑麥硬麵包",
            price_table_key="meal",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.COMMON,
                summary_zh="礦工下坑必帶的黑麥硬麵包，耐嚼且扛餓。",
            ),
        ),
        ItemDefinition(
            key="adventurer_field_ration",
            display_name_zh="冒險者攜行口糧",
            price_table_key="meal",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.COMMON,
                summary_zh="公會統一配發的壓縮口糧，D 級以下常見裝備。",
            ),
        ),
        ItemDefinition(
            key="imperial_candied_fruit",
            display_name_zh="帝國蜜漬果乾",
            price_table_key="specialty_food",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.COMMON,
                summary_zh="東南港口特產的蜜漬水果乾，耐放又香甜。",
            ),
        ),
        ItemDefinition(
            key="beastfolk_smoked_jerky",
            display_name_zh="獸王國燻獸肉乾",
            price_table_key="specialty_food",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.COMMON,
                summary_zh="高地獵手以獵物燻製而成的肉乾，蛋白質豐富。",
            ),
        ),
        ItemDefinition(
            key="harbor_lobster_bisque",
            display_name_zh="東南港灣龍蝦濃湯",
            price_table_key="specialty_food",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.COMMON,
                summary_zh="港口城市貴族餐廳的招牌濃湯，滋味濃郁。",
            ),
        ),
        ItemDefinition(
            key="elven_candied_blossom",
            display_name_zh="精靈蜜漬花蕊",
            price_table_key="specialty_food",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="精靈少量流出人類社會的花蕊蜜餞，甜而不膩。",
            ),
        ),
        # Inspect-only lore codex items: 5 Remedies
        ItemDefinition(
            key="miners_bracing_broth",
            display_name_zh="王國礦工提神湯",
            price_table_key="potion",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.POTION,
                icon_key=ItemIconKey.POTION,
                rarity=ItemRarity.COMMON,
                summary_zh="礦工下坑前灌下的辛辣提神湯，效果全憑意志力。",
            ),
        ),
        ItemDefinition(
            key="beastfolk_herbal_salve",
            display_name_zh="獸王國藥草膏",
            price_table_key="potion",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.POTION,
                icon_key=ItemIconKey.POTION,
                rarity=ItemRarity.COMMON,
                summary_zh="部族薩滿以高地藥草熬製的敷膏，外用居多。",
            ),
        ),
        ItemDefinition(
            key="passion_draught",
            display_name_zh="迷情藥",
            price_table_key="potion",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.POTION,
                icon_key=ItemIconKey.POTION,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="黑市流傳的催情酊劑，〔飾品〕迷情絲頸環便是浸過這類藥劑製成；效力溫和，可被意志壓制。",
            ),
        ),
        ItemDefinition(
            key="spirit_dew",
            display_name_zh="靈露",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.POTION,
                icon_key=ItemIconKey.POTION,
                rarity=ItemRarity.EPIC,
                summary_zh="以鮮活精靈體液為藥引低溫蒸餾出的金色藥劑，以極強的催情效力聞名，傳聞飲下者會在高潮般的熱浪中親眼看著自己的傷口合攏。",
            ),
        ),
        ItemDefinition(
            key="elven_tear",
            display_name_zh="精靈之淚",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.POTION,
                icon_key=ItemIconKey.POTION,
                rarity=ItemRarity.EPIC,
                summary_zh="精靈情緒激動時分泌的稀罕淚珠，鍊金師視為頂級藥引。",
            ),
        ),
        # Inspect-only lore codex items: 4 Tools
        ItemDefinition(
            key="enchanted_compass",
            display_name_zh="附魔羅盤",
            price_table_key="tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOOL,
                icon_key=ItemIconKey.TOOL,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="內嵌小型魔力晶片的羅盤，在迷宮中仍能指出「地表方向」。",
            ),
        ),
        ItemDefinition(
            key="dungeon_flare_talisman",
            display_name_zh="迷宮探照符",
            price_table_key="tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOOL,
                icon_key=ItemIconKey.TOOL,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="一次性符紙，撕開後照亮周遭一小段時間，深層迷宮探索必備。",
            ),
        ),
        ItemDefinition(
            key="beastfolk_signal_conch",
            display_name_zh="通訊法螺",
            price_table_key="tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOOL,
                icon_key=ItemIconKey.TOOL,
                rarity=ItemRarity.RARE,
                summary_zh="灌注風屬性魔力後可傳遞短距離語音的巨型海螺。",
            ),
        ),
        ItemDefinition(
            key="camp_ward_kit",
            display_name_zh="露營魔導具",
            price_table_key="tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOOL,
                icon_key=ItemIconKey.TOOL,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="展開後形成小型結界帳篷，隔絕野外的風雨與蟲獸。",
            ),
        ),
        # Inspect-only lore codex items: 6 Materials
        ItemDefinition(
            key="goblin_ear",
            display_name_zh="哥布林耳朵",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.COMMON,
                summary_zh="公會討伐任務常見的證明物，一對耳朵換一份微薄報酬。",
            ),
        ),
        ItemDefinition(
            key="slime_residue",
            display_name_zh="史萊姆黏液",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.COMMON,
                summary_zh="黏稠且帶弱酸性的史萊姆殘留物，煉金坊常見原料。",
            ),
        ),
        ItemDefinition(
            key="earth_drake_scale",
            display_name_zh="地龍鱗片",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.RARE,
                summary_zh="地龍蛻下或討伐後取得的鱗片，質地堅硬耐熱。",
            ),
        ),
        ItemDefinition(
            key="troll_fang",
            display_name_zh="巨魔尖牙",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.EPIC,
                summary_zh="高階魔獸巨魔的犬齒，質地近乎精鋼。",
            ),
        ),
        ItemDefinition(
            key="elven_essence",
            display_name_zh="精靈體液",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.EPIC,
                summary_zh="以鎖魔玻璃瓶封存的鮮活精靈體液，蘊含強大魔力與極強催情效力的液態素材；生命力一旦消散就淪為凡液，只有具備保鮮手段的鍊金師敢經手，視為珍寶。",
            ),
        ),
        ItemDefinition(
            key="ancient_dragon_heart",
            display_name_zh="古龍心臟",
            price_table_key="material",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MATERIAL,
                icon_key=ItemIconKey.MATERIAL,
                rarity=ItemRarity.LEGENDARY,
                summary_zh="傳說中古龍的心臟，據信是製作神代等級魔法道具的唯一材料，全大陸未有交易紀錄。",
            ),
        ),
        # Inspect-only lore codex items: 3 Curios
        ItemDefinition(
            key="family_crest_token",
            display_name_zh="家族信物",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.MISC,
                icon_key=ItemIconKey.MISC,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="由家族長輩傳下、刻有家紋或圖騰的小型物件，通常是任務或劇情的身分線索。",
            ),
        ),
        ItemDefinition(
            key="ancient_mystery_key",
            display_name_zh="謎樣的古老鑰匙",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.MISC,
                icon_key=ItemIconKey.MISC,
                rarity=ItemRarity.RARE,
                summary_zh="造型古樸、無法辨識鎖孔用途的鑰匙，據信與某座已知或未知的迷宮有關。",
            ),
        ),
        ItemDefinition(
            key="elven_child_toy",
            display_name_zh="精靈的簡陋玩具",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.MISC,
                icon_key=ItemIconKey.MISC,
                rarity=ItemRarity.COMMON,
                summary_zh="精靈孩童隨手製作的簡陋玩具，若被外人拾獲，通常代表附近有精靈幼體活動——世界觀提醒：精靈幼體對其他種族十分危險，因為他們不擅控制力道、不分是非。",
            ),
        ),
        # Regional equipment: 5 Beastfolk Weapons (land-lore-regional-equipment)
        ItemDefinition(
            key="beastfolk_warhammer",
            display_name_zh="獸人重鎚",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="部族鍛爐打造的巨型戰鎚，非獸人臂力難以掄動。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
            modifier_key=EquipmentModifierKey.BEASTFOLK_WARHAMMER,
        ),
        ItemDefinition(
            key="beastfolk_repeating_bow",
            display_name_zh="獸人連射短弓",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="獸人擅用的輕量連射短弓，講求速度而非單發威力。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
            modifier_key=EquipmentModifierKey.BEASTFOLK_REPEATING_BOW,
        ),
        ItemDefinition(
            key="beastfolk_war_spear",
            display_name_zh="獸人陣地長槍",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="獸人部族列陣時使用的長槍，攻守兼備。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
            modifier_key=EquipmentModifierKey.BEASTFOLK_WAR_SPEAR,
        ),
        ItemDefinition(
            key="beastfolk_twin_claws",
            display_name_zh="獸人雙爪刃",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="獸人綁縛於指節的鋒利爪刃，高攻但幾乎不設防禦。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
            modifier_key=EquipmentModifierKey.BEASTFOLK_TWIN_CLAWS,
        ),
        ItemDefinition(
            key="beastfolk_spirit_wand",
            display_name_zh="獸人導靈短杖",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="獸人以魔力見長所用的短杖，罕見的獸人法具。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
            modifier_key=EquipmentModifierKey.BEASTFOLK_SPIRIT_WAND,
        ),
        # Regional equipment: Elven and Trophy Weapons (land-lore-regional-equipment)
        ItemDefinition(
            key="elven_longbow",
            display_name_zh="精靈長弓",
            price_table_key="mundane_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.RARE,
                summary_zh="精靈以自產弓術淬鍊而成的長弓，箭無虛發。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
            modifier_key=EquipmentModifierKey.ELVEN_LONGBOW,
        ),
        ItemDefinition(
            key="dragon_lair_trophy_blade",
            display_name_zh="龍之巢穴戰利品劍",
            price_table_key="magic_weapon",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.WEAPON,
                icon_key=ItemIconKey.WEAPON,
                rarity=ItemRarity.EPIC,
                summary_zh="深入龍之巢穴討伐後才可能取得的鍛龍鱗劍，帶著淡淡硫磺氣息。",
            ),
            equipment_slot=EquipmentSlot.WEAPON_MAIN,
            modifier_key=EquipmentModifierKey.DRAGON_LAIR_TROPHY_BLADE,
        ),
        # Regional equipment: Armor and Accessories (land-lore-regional-equipment)
        ItemDefinition(
            key="beastfolk_heavy_hide_armor",
            display_name_zh="獸人厚甲",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="以獸皮與鐵片疊層縫製的部族重甲，犧牲機動換取硬度。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.BEASTFOLK_HEAVY_HIDE_ARMOR,
        ),
        ItemDefinition(
            key="beastfolk_stalker_garb",
            display_name_zh="獸人輕行衣",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="獸人暗殺者慣用的貼身輕甲，幾乎不影響身法。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.BEASTFOLK_STALKER_GARB,
        ),
        ItemDefinition(
            key="elven_forest_veil",
            display_name_zh="精靈森林輕紗",
            price_table_key="armor",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ARMOR,
                icon_key=ItemIconKey.ARMOR,
                rarity=ItemRarity.LEGENDARY,
                summary_zh="精靈以晨露編織的輕紗長裙，傳統服飾的精靈分支款式，精靈村商店應季上架的季節限定品。",
            ),
            equipment_slot=EquipmentSlot.ARMOR,
            modifier_key=EquipmentModifierKey.ELVEN_FOREST_VEIL,
        ),
        ItemDefinition(
            key="beastfolk_tribal_totem",
            display_name_zh="獸人部族圖騰",
            price_table_key="jewelry",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="以獵得的獸爪製成的部族圖騰項飾，力量與防禦並重。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.BEASTFOLK_TRIBAL_TOTEM,
        ),
        ItemDefinition(
            key="beastfolk_gale_earring",
            display_name_zh="獸人疾風耳環",
            price_table_key="jewelry",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.ACCESSORY,
                icon_key=ItemIconKey.ACCESSORY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="獸人以自身耳形為靈感打造的耳環，象徵族群的速度自豪。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.BEASTFOLK_GALE_EARRING,
        ),
        # Wearable intimacy accessories (add-toy-item-category)
        ItemDefinition(
            key="nymph_buds_clamp",
            display_name_zh="花蒂銀夾",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="聖所銀匠打的細銀乳夾，服儀的一部分，夾住之後每一口呼吸、每一步走動都被反覆輕錐，癢得發燙也摘不下手。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.NYMPH_BUDS_CLAMP,
        ),
        ItemDefinition(
            key="warm_honey_orb",
            display_name_zh="暖蜜魔導珠",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="聖所器具店常見貨色裡的蜜色魔導珠，以體溫為動力源源不絕地暖磨最敏感的那處，一戴就是一整日。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.WARM_HONEY_ORB,
        ),
        ItemDefinition(
            key="hyperesthesia_charm",
            display_name_zh="尖銳觸感之飾",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="聖所販售的祝禱掛飾，效果直白：佩戴期間皮膚的觸感被整體放大，衣料摩擦都變成細密的電流，平日無感的輕觸都會一路鑽進神經，從早到晚渾身不對勁。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.HYPERESTHESIA_CHARM,
        ),
        ItemDefinition(
            key="warmth_rune_egg",
            display_name_zh="恆溫魔法卵",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="刻入恆溫魔法陣的鵝卵石小卵，含在體內便持續溫熱下體、催出潤澤，外頭沒人看得出來。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.WARMTH_RUNE_EGG,
        ),
        ItemDefinition(
            key="tremor_crystal",
            display_name_zh="恆振晶",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.RARE,
                summary_zh="精靈匠作的乳色魔導晶，刻著人類學者讀不懂的微振術式，貼身藏好便能以恆定微顫終日刺激花心，術式撐到下次造訪精靈村前從不停歇。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.TREMOR_CRYSTAL,
        ),
        # Usable intimacy devices (land-usable-intimacy-items)
        ItemDefinition(
            key="aphrodisiac_bath_salts",
            display_name_zh="催情浴鹽",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="浴場的招牌入浴劑，泡完整個皮膚的敏感度輕飄飄地抬高整個晚上，冒險歸來的定番享受。",
            ),
            use_mechanics=ItemUseMechanics(
                consumable=True,
                combat_allowed=False,
            ),
        ),
        ItemDefinition(
            key="kiss_of_goddess_mist",
            display_name_zh="女神之吻聖霧",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.RARE,
                summary_zh="聖所「女神之吻」禮儀聖霧的裝瓶紀念品，一噴讓全身敏感度瞬間拉到頂，信徒把它當成能帶回家的神蹟。",
            ),
            use_mechanics=ItemUseMechanics(
                consumable=False,
                combat_allowed=False,
            ),
        ),
        ItemDefinition(
            key="censer_of_desire",
            display_name_zh="情欲香爐",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.RARE,
                summary_zh="聖所禮儀用的小巧香爐，爐煙沾上肌膚就化作綿長酥癢，越是動情燒得越是歡。",
            ),
            use_mechanics=ItemUseMechanics(
                consumable=False,
                combat_allowed=False,
            ),
        ),
        ItemDefinition(
            key="embracing_vine",
            display_name_zh="纏枝魔藤",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.RARE,
                summary_zh="一盆栽在陶盆裡的魔法藤蔓，澆水醒來後會溫柔地纏上全身每一處敏感地，以恰好不弄傷人的力道緩慢收緊磨蹭，一個季度後自己縮回盆裡沉睡，等下次澆水再醒。",
            ),
            use_mechanics=ItemUseMechanics(
                consumable=False,
                combat_allowed=False,
            ),
        ),
        ItemDefinition(
            key="spark_candy",
            display_name_zh="微電跳蛋糖",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="含在嘴裡就對舌頭送微電流的神奇糖果，電流順著神經一路麻到下半身；外表和普通糖果無異，不知情的孩子常常誤食，附魔師公會因此被投訴過很多次。",
            ),
            use_mechanics=ItemUseMechanics(
                consumable=True,
                combat_allowed=False,
            ),
        ),
        ItemDefinition(
            key="slime_lube_gel",
            display_name_zh="史萊姆潤滑凝膠",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="〔素材〕史萊姆黏液的下游製品：滅菌處理過的黏液分裝包，滑潤持久怎麼塗都不會乾，讓摩擦的每一寸都變成放大的觸感。",
            ),
            use_mechanics=ItemUseMechanics(
                consumable=True,
                combat_allowed=False,
            ),
        ),
        ItemDefinition(
            key="hot_kiss_potion",
            display_name_zh="熱吻藥水",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="喝下去從舌頭一路暖到小腹的粉紅藥劑；鍊金坊的正經生意，櫃檯前永遠站著情侶和新婚夫妻。",
            ),
            use_mechanics=ItemUseMechanics(
                consumable=True,
                combat_allowed=False,
            ),
        ),
    )
}
