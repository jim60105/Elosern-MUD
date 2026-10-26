"""Adventurer guild rank registry from design section 5.1 and lore-world-data.

Branch rows carry the host's authored NPC name used by the service-host sync;
rank rows carry progression and fixed-title metadata only (npc-identity-titles).
Load-time validation fails closed.
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

    @property
    def display_name_zh(self) -> str:
        """The player-facing rank name (the codex title), e.g. ``F 級``."""
        return f"{self.key} 級"


@dataclass(frozen=True)
class GuildBranch:
    """A named guild branch locale (guild-economy D-3 validation identity)."""

    key: str
    display_name_zh: str
    # Authored NPC identity of the branch's service host (guild-economy sync).
    host_name: str
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
        "葛里安‧衛登",
        "capital_altoria",
    ),
}


def _validated_identity(
    what: str, row_key: str, name: object, *, name_field: str
) -> None:
    """Run the shared name validator over one authored identity, naming row and field."""
    # Function-local import keeps lore import-light and test-injectable.
    from world.rules.npc_identity import validate_npc_name

    try:
        validate_npc_name(name)
    except ValueError as error:
        raise ValueError(f"{what} {row_key} has an invalid {name_field}: {error}") from error



def validate_guild_npc_identities(
    branches: dict[str, GuildBranch] | None = None,
) -> None:
    """Fail closed on the shipped branch-host authored identities (design D4).

    Pure checker callable with an explicit dict (tests); defaults to the
    shipped registry. Raises ValueError naming the offending row and rule.
    Ranks carry no examiner identity: the people who host examinations are
    persistent adventurers validated by ``world.rules.human_guild_hosts``.
    """
    for branch in (GUILD_BRANCH_REGISTRY if branches is None else branches).values():
        _validated_identity(
            "guild branch", branch.key, branch.host_name, name_field="host_name",
        )


# Shipped rows must be valid the moment the module loads (titles.py precedent).
# The cross-registry name check runs here too (not only from shops.py): the
# function-local import is cycle-safe because shops.py reaches the guild
# registries function-locally as well, so loading either registry validates
# the whole authored-name set (design D4/D9).
validate_guild_npc_identities()

from world.lore.settlements.shops import validate_registry_identity_uniqueness  # noqa: E402

validate_registry_identity_uniqueness(branch_rows=GUILD_BRANCH_REGISTRY)
