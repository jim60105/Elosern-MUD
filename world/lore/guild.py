"""Adventurer guild rank registry from design section 5.1 and lore-world-data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GuildRank:
    key: str
    order: int
    reward_min_copper: int
    reward_max_copper: int | None
    description: str


GUILD_RANK_REGISTRY: dict[str, GuildRank] = {
    "F": GuildRank("F", 1, 10, 100, "Simple collection and caravan escort tasks."),
    "E": GuildRank("E", 2, 100, 500, "Low-tier monster hunts."),
    "D": GuildRank("D", 3, 500, 5_000, "Party-based dungeon runs."),
    "C": GuildRank("C", 4, 5_000, 50_000, "Work for an adventurer capable of acting alone."),
    "B": GuildRank("B", 5, 50_000, 500_000, "High-difficulty commissions."),
    "A": GuildRank("A", 6, 500_000, 5_000_000, "Top-tier human combat assignments."),
    "S": GuildRank("S", 7, 5_000_000, None, "Legendary assignments beyond the human scale."),
}
