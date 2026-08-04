"""Immutable NPC role-tier registry for quest proposals.

Change 20's quest proposals reference NPC tiers (design section 7.1: a
``frightened civilian``). The vocabulary is shared by the ``world/ai`` proposal
validators, change 21's SceneBuilder, and the ``world/quests`` compiler, so it
lives here as immutable lore data rather than as ``world/ai`` constants that
deterministic consumers could not legally import.
"""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class NPCTier:
    """One immutable NPC role-tier identity referenced by quest proposals.

    ``race_key`` and ``static_tier_key`` name immutable entries of
    ``RACE_REGISTRY`` and ``STATIC_TIER_REGISTRY`` so change 21's SceneBuilder
    derives a role tier's deterministic physical stats from the lore tables
    instead of duplicating balance constants. The referenced static tier must
    belong to the referenced race; a registry test locks that invariant.
    """

    key: str
    display_name_zh: str
    description: str
    race_key: str
    static_tier_key: str


_NPC_TIERS = (
    NPCTier("civilian", "平民", "沒有戰鬥能力的普通市民。", "human", "human_commoner"),
    NPCTier("guard", "衛兵", "維持治安的守衛，受過基本戰鬥訓練。", "human", "human_adventurer"),
    NPCTier("merchant", "商人", "往來各地的商人，攜帶貨物與錢財。", "human", "human_commoner"),
    NPCTier("adventurer", "冒險者", "以討伐與探索為業的冒險者。", "human", "human_adventurer"),
    NPCTier("mage", "法師", "掌握魔法力量的施法者。", "human", "human_commoner"),
    NPCTier("noble", "貴族", "擁有領地或地位的貴族。", "human", "human_commoner"),
    NPCTier("bandit", "盜匪", "劫掠商旅與行人的盜匪。", "human", "human_adventurer"),
    NPCTier("priest", "祭司", "侍奉神明的祭司。", "human", "human_commoner"),
    NPCTier("knight", "騎士", "身穿鎧甲、效忠領主的騎士。", "human", "human_elite"),
)

# Frozen: consumers may read registry values but never extend or replace them.
NPC_TIER_REGISTRY: MappingProxyType[str, NPCTier] = MappingProxyType(
    {tier.key: tier for tier in _NPC_TIERS}
)
