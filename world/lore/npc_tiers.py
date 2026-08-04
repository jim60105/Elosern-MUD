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
    """One immutable NPC role-tier identity referenced by quest proposals."""

    key: str
    display_name_zh: str
    description: str


_NPC_TIERS = (
    NPCTier("civilian", "平民", "沒有戰鬥能力的普通市民。"),
    NPCTier("guard", "衛兵", "維持治安的守衛，受過基本戰鬥訓練。"),
    NPCTier("merchant", "商人", "往來各地的商人，攜帶貨物與錢財。"),
    NPCTier("adventurer", "冒險者", "以討伐與探索為業的冒險者。"),
    NPCTier("mage", "法師", "掌握魔法力量的施法者。"),
    NPCTier("noble", "貴族", "擁有領地或地位的貴族。"),
    NPCTier("bandit", "盜匪", "劫掠商旅與行人的盜匪。"),
    NPCTier("priest", "祭司", "侍奉神明的祭司。"),
    NPCTier("knight", "騎士", "身穿鎧甲、效忠領主的騎士。"),
)

# Frozen: consumers may read registry values but never extend or replace them.
NPC_TIER_REGISTRY: MappingProxyType[str, NPCTier] = MappingProxyType(
    {tier.key: tier for tier in _NPC_TIERS}
)
