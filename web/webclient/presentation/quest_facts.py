"""Shared quest category vocabulary, reward bound, and canonical builder."""

from world.quests.definitions import QuestType
from world.quests.describe import describe_reward_parts

MAX_REWARD_ITEMS = 1
QUEST_CATEGORIES = {kind: kind.name.lower() for kind in QuestType}

__all__ = ["MAX_REWARD_ITEMS", "QUEST_CATEGORIES", "describe_reward_parts"]
