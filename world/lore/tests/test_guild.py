"""Data-contract test: guild registry content contract
Self-consistency checks for guild reward bands."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.guild import (
    GUILD_BRANCH_REGISTRY,
    GUILD_RANK_REGISTRY,
    GuildBranch,
    GuildRank,
    validate_guild_npc_identities,
)


class GuildRegistryTests(unittest.TestCase):
    @covers_requirement("lore-registries::guildrank-registry-provides-ordered-reward-bands-in-copper")
    def test_rank_order_and_reward_ladder(self):
        ranks = sorted(GUILD_RANK_REGISTRY.values(), key=lambda rank: rank.order)
        self.assertEqual([rank.key for rank in ranks], ["F", "E", "D", "C", "B", "A", "S"])
        self.assertEqual([rank.order for rank in ranks], list(range(1, 8)))
        for rank, next_rank in zip(ranks, ranks[1:]):
            self.assertIsInstance(rank.reward_min_copper, int)
            self.assertIsInstance(rank.reward_max_copper, int)
            self.assertGreater(rank.reward_max_copper, rank.reward_min_copper)
            self.assertEqual(rank.reward_max_copper, next_rank.reward_min_copper)
        self.assertIsNone(ranks[-1].reward_max_copper)
        self.assertIsInstance(ranks[-1].reward_min_copper, int)


class GuildNPCIdentityTests(unittest.TestCase):
    """Authored host identities fail closed at load (design D4)."""

    def test_invalid_branch_host_name_is_named_by_row_and_field(self):
        row = GUILD_BRANCH_REGISTRY["guild_branch_altoria"]
        bad = {
            "k": GuildBranch(row.key, row.display_name_zh, "  ", row.host_title, row.anchor_key)
        }
        with self.assertRaises(ValueError) as caught:
            validate_guild_npc_identities(branches=bad)
        self.assertIn("invalid host_name", str(caught.exception))

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_rank_metadata_carries_no_opponent_factory_identity(self):
        # Ranks keep progression/reward/title metadata only; examination
        # hosts are qualified persistent people, never a rank-owned identity.
        import dataclasses

        names = {field.name for field in dataclasses.fields(GuildRank)}
        self.assertFalse({"examiner_name", "examiner_title", "examiner_profile_key"} & names)
        row = GUILD_RANK_REGISTRY["D"]
        with self.assertRaises(TypeError):
            GuildRank(
                row.key, row.order, row.reward_min_copper, row.reward_max_copper,
                row.description, row.title_key, "無主考官",
            )

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_shipped_rows_load_clean(self):
        # The module-level call already ran at import; an explicit re-run is a
        # no-op proof that every shipped row passes both shared validators.
        validate_guild_npc_identities()
