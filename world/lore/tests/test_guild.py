"""Self-consistency checks for guild reward bands."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.guild import GUILD_RANK_REGISTRY


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
