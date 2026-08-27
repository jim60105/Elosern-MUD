"""Immutable item identity and presentation registry for the deterministic economy (guild-economy D-8).

Item definitions carry no tunable numeric rules; exact prices, stock, and
restock quantities live in ``world/rules/rulebook/guild_economy.yaml`` and are
joined to these identities by the guild-economy catalog loader.

Presentation metadata — closed item kind, closed SVG icon key, closed rarity,
and a bounded Traditional Chinese summary — is registry-owned and read-only.
It is visual identity only: numeric combat, recovery, or comparison values
stay out of this registry until a deterministic item-effects capability
owns those facts.
"""

from dataclasses import dataclass
from enum import StrEnum

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
    """The immutable identity of one supported inventory item."""

    key: str
    display_name_zh: str
    price_table_key: str
    sellable: bool
    presentation: ItemPresentation

    def __post_init__(self) -> None:
        """Require the frozen presentation object on every registry entry."""
        if not isinstance(self.presentation, ItemPresentation):
            raise ValueError(
                f"item {self.key!r} presentation must be an ItemPresentation"
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
        ),
    )
}
