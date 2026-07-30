"""Typed static world data from design document section 5.1."""

from .anchors import ANCHOR_REGISTRY, Anchor, AnchorKind
from .economy import (
    COPPER_PER_GOLD,
    COPPER_PER_SILVER,
    PRICE_TABLE,
    PriceEntry,
    to_copper,
)
from .elements import ELEMENT_REGISTRY, Element
from .guild import GUILD_RANK_REGISTRY, GuildRank
from .magic import MAGIC_TIER_REGISTRY, RANK_TITLE_REGISTRY, MagicTier, RankTitle
from .monsters import MONSTER_TIER_REGISTRY, MonsterTier
from .nations import NATION_REGISTRY, Nation
from .races import (
    RACE_REGISTRY,
    STATIC_TIER_REGISTRY,
    SUBRACE_REGISTRY,
    RaceProfile,
    StaticBand,
    StaticTier,
    StatModifiers,
    Subrace,
    Vitals,
)

__all__ = [
    "ANCHOR_REGISTRY",
    "COPPER_PER_GOLD",
    "COPPER_PER_SILVER",
    "ELEMENT_REGISTRY",
    "GUILD_RANK_REGISTRY",
    "MAGIC_TIER_REGISTRY",
    "MONSTER_TIER_REGISTRY",
    "NATION_REGISTRY",
    "PRICE_TABLE",
    "RACE_REGISTRY",
    "RANK_TITLE_REGISTRY",
    "STATIC_TIER_REGISTRY",
    "SUBRACE_REGISTRY",
    "Anchor",
    "AnchorKind",
    "Element",
    "GuildRank",
    "MagicTier",
    "MonsterTier",
    "Nation",
    "PriceEntry",
    "RaceProfile",
    "RankTitle",
    "StaticBand",
    "StaticTier",
    "StatModifiers",
    "Subrace",
    "Vitals",
    "to_copper",
]
