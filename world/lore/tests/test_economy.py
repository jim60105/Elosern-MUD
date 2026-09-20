"""Data-contract test: price-table data contract
Self-consistency checks for currency and purchasing power."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.economy import PRICE_TABLE, PriceEntry, to_copper
from world.lore.guild import GUILD_RANK_REGISTRY


class EconomyRegistryTests(unittest.TestCase):
    @covers_requirement("lore-registries::currency-is-an-integer-count-of-\u9285-with-no-floats-in-the-money-path")
    def test_conversion(self):
        self.assertEqual(to_copper(gold=1), 10_000)
        self.assertEqual(to_copper(silver=1), 100)
        self.assertEqual(to_copper(copper=1), 1)
        self.assertIsInstance(to_copper(gold=1, silver=2, copper=3), int)

    def test_price_references_are_integral_and_ordered(self):
        self.assertEqual(len(PRICE_TABLE), 17)
        for entry in PRICE_TABLE.values():
            self.assertIsInstance(entry, PriceEntry)
            self.assertIsInstance(entry.min_copper, int)
            if entry.max_copper is not None:
                self.assertIsInstance(entry.max_copper, int)
                self.assertGreaterEqual(entry.max_copper, entry.min_copper)

    @covers_requirement(
        "masterwork-price-band::a-masterwork-price-band-spans-everyday-and-scarce-prices-for-the-same-object"
    )
    def test_masterwork_band_ceiling_stays_below_keepsake_floor(self):
        # The masterwork band is how a community-traded good carries a scarce
        # outside price; it must never bleed into relic's exclusive region, or
        # "never traded" would lose its meaning. Assert the relationship over
        # the live table bounds, not the row's literal values.
        masterwork = PRICE_TABLE["masterwork_gear"]
        relic = PRICE_TABLE["relic"]
        self.assertIsNotNone(masterwork.max_copper)
        self.assertLess(masterwork.max_copper, relic.min_copper)

    def test_guild_rewards_are_integral(self):
        for rank in GUILD_RANK_REGISTRY.values():
            self.assertIsInstance(rank.reward_min_copper, int)
            if rank.reward_max_copper is not None:
                self.assertIsInstance(rank.reward_max_copper, int)
