"""Adventurer guild rank registry from design section 5.1 and lore-world-data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GuildRank:
    key: str
    order: int
    reward_min_copper: int
    reward_max_copper: int | None
    description: str
    # The paired fixed-title key (title-system D3); every rank row carries one.
    title_key: str


@dataclass(frozen=True)
class GuildBranch:
    """A named guild branch locale (guild-economy D-3 validation identity)."""

    key: str
    display_name_zh: str
    anchor_key: str | None = None


GUILD_RANK_REGISTRY: dict[str, GuildRank] = {
    "F": GuildRank("F", 1, 10, 100, "Simple collection and caravan escort tasks.", "g_f_rank"),
    "E": GuildRank("E", 2, 100, 500, "Low-tier monster hunts.", "g_e_rank"),
    "D": GuildRank("D", 3, 500, 5_000, "Party-based dungeon runs.", "g_d_rank"),
    "C": GuildRank("C", 4, 5_000, 50_000, "Work for an adventurer capable of acting alone.", "g_c_rank"),
    "B": GuildRank("B", 5, 50_000, 500_000, "High-difficulty commissions.", "g_b_rank"),
    "A": GuildRank("A", 6, 500_000, 5_000_000, "Top-tier human combat assignments.", "g_a_rank"),
    "S": GuildRank("S", 7, 5_000_000, None, "Legendary assignments beyond the human scale.", "g_s_rank"),
}

GUILD_BRANCH_REGISTRY: dict[str, GuildBranch] = {
    "guild_branch_altoria": GuildBranch(
        "guild_branch_altoria",
        "埃洛西恩冒險者公會 阿爾托利亞分會",
        "capital_altoria",
    ),
}
