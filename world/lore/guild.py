"""Adventurer guild rank registry from design section 5.1 and lore-world-data.

Rank rows also carry the examiner's authored NPC identity (name + title) used
by the exam opponent spawn (npc-title-authored-identities D5); branch rows
carry the guild-host's authored identity. Load-time validation fails closed.
"""

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
    # Authored NPC identity of the rank examiner (npc-title-authored-identities).
    examiner_name: str
    examiner_title: str


@dataclass(frozen=True)
class GuildBranch:
    """A named guild branch locale (guild-economy D-3 validation identity)."""

    key: str
    display_name_zh: str
    # Authored NPC identity of the branch's service host (guild-economy sync).
    host_name: str
    host_title: str
    anchor_key: str | None = None


GUILD_RANK_REGISTRY: dict[str, GuildRank] = {
    "F": GuildRank("F", 1, 10, 100, "Simple collection and caravan escort tasks.", "g_f_rank", "雷加·鐵拳", "公會見習考官"),
    "E": GuildRank("E", 2, 100, 500, "Low-tier monster hunts.", "g_e_rank", "薇拉·晨風", "公會初階考官"),
    "D": GuildRank("D", 3, 500, 5_000, "Party-based dungeon runs.", "g_d_rank", "巴德·石肩", "公會中階考官"),
    "C": GuildRank("C", 4, 5_000, 50_000, "Work for an adventurer capable of acting alone.", "g_c_rank", "賽琳·夜鶯", "公會高階考官"),
    "B": GuildRank("B", 5, 50_000, 500_000, "High-difficulty commissions.", "g_b_rank", "霍克·赤刃", "公會資深考官"),
    "A": GuildRank("A", 6, 500_000, 5_000_000, "Top-tier human combat assignments.", "g_a_rank", "卡珊卓·銀輝", "公會首席考官"),
    "S": GuildRank("S", 7, 5_000_000, None, "Legendary assignments beyond the human scale.", "g_s_rank", "奧古斯丁·無名", "公會傳說考官"),
}

GUILD_BRANCH_REGISTRY: dict[str, GuildBranch] = {
    "guild_branch_altoria": GuildBranch(
        "guild_branch_altoria",
        "埃洛西恩冒險者公會 阿爾托利亞分會",
        "葛里安·衛登",
        "阿爾托利亞分會會長",
        "capital_altoria",
    ),
}


def _validated_identity(
    what: str, row_key: str, name: object, title: object, *, name_field: str, title_field: str
) -> None:
    """Run both shared validators over one authored identity, naming row and field."""
    # Function-local import keeps lore import-light and test-injectable.
    from world.rules.npc_identity import validate_npc_name, validate_npc_title

    try:
        validate_npc_name(name)
    except ValueError as error:
        raise ValueError(f"{what} {row_key} has an invalid {name_field}: {error}") from error
    try:
        validate_npc_title(title)
    except ValueError as error:
        raise ValueError(f"{what} {row_key} has an invalid {title_field}: {error}") from error


def validate_guild_npc_identities(
    ranks: dict[str, GuildRank] | None = None,
    branches: dict[str, GuildBranch] | None = None,
) -> None:
    """Fail closed on the shipped examiner/host authored identities (design D4).

    Pure checker callable with explicit dicts (tests); defaults to the shipped
    registries. Raises ValueError naming the offending row and rule.
    """
    for rank in (GUILD_RANK_REGISTRY if ranks is None else ranks).values():
        _validated_identity(
            "guild rank", rank.key, rank.examiner_name, rank.examiner_title,
            name_field="examiner_name", title_field="examiner_title",
        )
    for branch in (GUILD_BRANCH_REGISTRY if branches is None else branches).values():
        _validated_identity(
            "guild branch", branch.key, branch.host_name, branch.host_title,
            name_field="host_name", title_field="host_title",
        )


# Shipped rows must be valid the moment the module loads (titles.py precedent).
# The cross-registry name check runs here too (not only from shops.py): the
# function-local import is cycle-safe because shops.py reaches the guild
# registries function-locally as well, so loading either registry validates
# the whole authored-name set (design D4/D9).
validate_guild_npc_identities()

from world.lore.shops import validate_registry_identity_uniqueness  # noqa: E402

validate_registry_identity_uniqueness(branch_rows=GUILD_BRANCH_REGISTRY, rank_rows=GUILD_RANK_REGISTRY)
