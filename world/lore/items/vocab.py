"""Vocabulary and value types for the item registry.

Holds the ``SUMMARY_MAX`` bound, the closed ``ItemKind``/``ItemIconKey``/
``ItemRarity``/``EquipmentModifierKey`` vocabularies, and the frozen
``ItemUseMechanics``/``ItemPresentation``/``ItemDefinition`` dataclasses,
moved verbatim from the head of the single ``world/lore/items.py`` module.
``EquipmentSlot`` stays imported here because ``ItemDefinition`` validates
against it at construction.
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
    ROYAL_TRAVELING_ROBE = "royal_traveling_robe"
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


