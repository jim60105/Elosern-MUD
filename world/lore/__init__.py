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
from .magic import MAGIC_TIER_REGISTRY, MagicTier
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
from .sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SENSITIVITY_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from .titles import (
    FIXED_TITLE_REGISTRY,
    STARTER_EPITHET,
    FixedTitleDef,
    StarterEpithet,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
    TitleRegistryError,
    validate_fixed_titles,
)

__all__ = [
    "ANCHOR_REGISTRY",
    "AROUSAL_LEVELS",
    "CLIMAX_PHASE_LEVELS",
    "COPPER_PER_GOLD",
    "COPPER_PER_SILVER",
    "ELEMENT_REGISTRY",
    "EXPOSURE_LEVELS",
    "FIXED_TITLE_REGISTRY",
    "GUILD_RANK_REGISTRY",
    "MAGIC_TIER_REGISTRY",
    "MONSTER_TIER_REGISTRY",
    "NATION_REGISTRY",
    "PRICE_TABLE",
    "RACE_REGISTRY",
    "SENSITIVITY_LEVELS",
    "SHAME_LEVELS",
    "STARTER_EPITHET",
    "STATIC_TIER_REGISTRY",
    "SUBRACE_REGISTRY",
    "Anchor",
    "AnchorKind",
    "Element",
    "FixedTitleDef",
    "GuildRank",
    "MagicTier",
    "MonsterTier",
    "Nation",
    "PriceEntry",
    "RaceProfile",
    "StaticBand",
    "StaticTier",
    "StatModifiers",
    "StarterEpithet",
    "Subrace",
    "TitleCategory",
    "TitlePredicate",
    "TitlePredicateFamily",
    "TitleRegistryError",
    "Vitals",
    "WETNESS_LEVELS",
    "to_copper",
    "validate_fixed_titles",
]
