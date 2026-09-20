"""Data-contract test: guild/shop config validation contract
Slice of ``test_guild_config``: PriceScaleSectionTests, PlacePriceScalingTests.
"""
from tools.spec_traceability import covers_requirement
import unittest
from world.lore.items import ITEM_REGISTRY
from world.lore.items import ItemDefinition
from world.lore.items import ItemIconKey
from world.lore.items import ItemKind
from world.lore.items import ItemPresentation
from world.lore.items import ItemRarity
from world.rules.guild_config import GuildConfigError
from world.rules.guild_config import validate_price_scales
from world.rules.guild_config import validate_shop_configs
from ._support import (
    _price_shop_env,
    _price_shop_scope,
    _shipped_scales,
)


class PriceScaleSectionTests(unittest.TestCase):
    """``price_scales`` section and per-shop scale validation (design §4)."""

    def test_shipped_section_is_par(self):
        self.assertEqual(
            _shipped_scales(),
            {"capital_altoria": 100, "village_ciaran": 100},
        )

    def test_price_scales_must_be_a_mapping(self):
        with self.assertRaises(GuildConfigError):
            validate_price_scales([("capital_altoria", 100)])

    def test_unknown_settlement_key_is_rejected(self):
        with self.assertRaises(GuildConfigError) as caught:
            validate_price_scales({"t_no_such_city": 100})
        self.assertIn("t_no_such_city", str(caught.exception))

    def test_scale_must_be_an_integer(self):
        with self.assertRaises(GuildConfigError) as caught:
            validate_price_scales({"capital_altoria": 1.5})
        self.assertIn("capital_altoria", str(caught.exception))

    def test_scale_bounds_reject_zero_and_negative(self):
        for bad in (0, -1):
            with self.assertRaises(GuildConfigError) as caught:
                validate_price_scales({"capital_altoria": bad})
            self.assertIn("capital_altoria", str(caught.exception))

    def test_scale_bounds_accept_one_and_thousand(self):
        for keep in (1, 1000):
            self.assertEqual(
                validate_price_scales({"capital_altoria": keep}),
                {"capital_altoria": keep},
            )

    def test_scale_bounds_reject_above_thousand(self):
        with self.assertRaises(GuildConfigError) as caught:
            validate_price_scales({"capital_altoria": 1001})
        self.assertIn("capital_altoria", str(caught.exception))

    def test_shop_scale_must_be_an_integer(self):
        env = _price_shop_env(price_scale=1.5)
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        self.assertIn("t_price_stall", str(caught.exception))

    def test_shop_scale_bounds_reject_bad_values(self):
        for bad in (0, -1, 1001):
            env = _price_shop_env(price_scale=bad)
            with _price_shop_scope(env):
                with self.assertRaises(GuildConfigError):
                    validate_shop_configs([env["row"]], env["offers"], env["scales"])

    @covers_requirement(
        "place-price-scaling::a-place-s-final-offer-is-a-shared-base-adjusted-by-one-local-rule"
    )
    def test_shop_scale_overrides_settlement_entry(self):
        env = _price_shop_env(price_scale=150)
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(config.offers[0].buy_copper, (25 * 150 + 50) // 100)

    @covers_requirement(
        "place-price-scaling::a-place-s-final-offer-is-a-shared-base-adjusted-by-one-local-rule"
    )
    def test_shop_inherits_settlement_scale(self):
        env = _price_shop_env(scales={"t_scale_city": 150})
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(config.offers[0].buy_copper, (25 * 150 + 50) // 100)

    def test_shop_settlement_without_scale_entry_fails_load(self):
        env = _price_shop_env(scales={"t_other_city": 100})
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        message = str(caught.exception)
        self.assertIn("t_scale_city", message)
        self.assertIn("t_price_store", message)

class PlacePriceScalingTests(unittest.TestCase):
    """Resolved price model over synthetic places (place-price-scaling §4/§8)."""

    @covers_requirement(
        "place-price-scaling::a-place-s-final-offer-is-a-shared-base-adjusted-by-one-local-rule"
    )
    def test_rounding_boundaries_are_half_up(self):
        # (base * scale + 50) // 100: 25@150 -> 37.5 rounds up to 38;
        # 10@150 -> 15 exact; 33@150 -> 49.5 rounds up to 50.
        env = _price_shop_env(base_buy=25, base_sell=10, price_scale=150)
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(
            (config.offers[0].buy_copper, config.offers[0].sell_copper),
            (38, 15),
        )

        env = _price_shop_env(base_buy=33, base_sell=33, price_scale=150)
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(config.offers[0].buy_copper, 50)

    @covers_requirement(
        "place-price-scaling::a-place-s-final-offer-is-a-shared-base-adjusted-by-one-local-rule"
    )
    def test_par_scale_leaves_prices_unchanged(self):
        env = _price_shop_env(base_buy=25, base_sell=10, price_scale=100)
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(
            (config.offers[0].buy_copper, config.offers[0].sell_copper),
            (25, 10),
        )

    @covers_requirement(
        "place-price-scaling::resolved-prices-are-validated-not-the-bases"
    )
    def test_scaled_price_outside_band_fails_load(self):
        # Base 25 is legal inside band 20..30 at par; at scale 150 it
        # resolves to 38, above the ceiling, and load fails naming the
        # place, the item and the resolved value.
        env = _price_shop_env(band_min=20, band_max=30, base_buy=25, price_scale=150)
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        message = str(caught.exception)
        self.assertIn("t_price_store", message)
        self.assertIn("t_price_probe", message)
        self.assertIn("38", message)

    @covers_requirement(
        "place-price-scaling::resolved-prices-are-validated-not-the-bases"
    )
    def test_scaled_sell_above_buy_fails_load(self):
        # The inverted base (sell 30 > buy 25) is legal at assortment level
        # now; the moved rejection fires on the resolved values here.
        env = _price_shop_env(base_buy=25, base_sell=30)
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        message = str(caught.exception)
        self.assertIn("t_price_store", message)
        self.assertIn("t_price_probe", message)
        self.assertIn("30", message)

    @covers_requirement(
        "place-price-scaling::an-override-is-complete-or-rejected"
    )
    def test_override_is_absolute_and_not_scaled(self):
        override = {
            "item_key": "t_price_probe",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
            "restock_quantity": 1,
        }
        env = _price_shop_env(price_scale=200, overrides=(override,))
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(
            (config.offers[0].buy_copper, config.offers[0].sell_copper),
            (42, 21),
        )

    @covers_requirement(
        "place-price-scaling::an-override-is-complete-or-rejected"
    )
    def test_partial_override_fails_naming_missing_fields(self):
        partial = {
            "item_key": "t_price_probe",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
        }
        env = _price_shop_env(overrides=(partial,))
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        message = str(caught.exception)
        self.assertIn("t_price_store", message)
        self.assertIn("t_price_probe", message)
        self.assertIn("restock_quantity", message)

    @covers_requirement(
        "place-price-scaling::an-override-is-complete-or-rejected"
    )
    def test_override_for_unoffered_item_fails_load(self):
        # A known item that is in none of the place's assortments and is not
        # one of its additions: the override names an unoffered good.
        curio = ItemDefinition(
            key="t_price_curio",
            display_name_zh="合成珍奇",
            price_table_key="t_price_band",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MISC,
                icon_key=ItemIconKey.MISC,
                rarity=ItemRarity.COMMON,
                summary_zh="合成價格縮放的珍奇物。",
            ),
        )
        override = {
            "item_key": "t_price_curio",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
            "restock_quantity": 1,
        }
        env = _price_shop_env(overrides=(override,))
        env["items"]["t_price_curio"] = curio
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        message = str(caught.exception)
        self.assertIn("t_price_store", message)
        self.assertIn("t_price_curio", message)

    @covers_requirement(
        "place-price-scaling::a-place-may-add-and-remove-individual-items"
    )
    def test_extra_without_override_fails_load(self):
        env = _price_shop_env(extra_item_keys=("t_price_curio",))
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        self.assertIn("t_price_curio", str(caught.exception))

    @covers_requirement(
        "place-price-scaling::a-place-may-add-and-remove-individual-items"
    )
    def test_extra_with_complete_override_is_offered(self):
        curio = ItemDefinition(
            key="t_price_curio",
            display_name_zh="合成珍奇",
            price_table_key="t_price_band",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MISC,
                icon_key=ItemIconKey.MISC,
                rarity=ItemRarity.COMMON,
                summary_zh="合成價格縮放的珍奇物。",
            ),
        )
        override = {
            "item_key": "t_price_curio",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
            "restock_quantity": 1,
        }
        env = _price_shop_env(extra_item_keys=("t_price_curio",), overrides=(override,))
        env["items"]["t_price_curio"] = curio
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(
            {offer.item_key for offer in config.offers},
            {"t_price_probe", "t_price_curio"},
        )

    @covers_requirement(
        "place-price-scaling::a-place-may-add-and-remove-individual-items"
    )
    def test_removal_matching_no_assortment_item_fails_load(self):
        env = _price_shop_env(excluded_item_keys=("t_no_such_item",))
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        self.assertIn("t_no_such_item", str(caught.exception))

    @covers_requirement(
        "place-price-scaling::a-place-may-add-and-remove-individual-items"
    )
    def test_removal_drops_the_item_from_offers(self):
        env = _price_shop_env(excluded_item_keys=("t_price_probe",))
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(config.offers, ())

    @covers_requirement(
        "place-price-scaling::a-place-may-add-and-remove-individual-items"
    )
    def test_override_for_removed_item_fails_load(self):
        override = {
            "item_key": "t_price_probe",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
            "restock_quantity": 1,
        }
        env = _price_shop_env(
            excluded_item_keys=("t_price_probe",), overrides=(override,)
        )
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        self.assertIn("t_price_probe", str(caught.exception))

    @covers_requirement(
        "place-price-scaling::a-place-s-final-offer-is-a-shared-base-adjusted-by-one-local-rule"
    )
    def test_same_item_two_places_stays_one_definition(self):
        # Design §8: one item at two resolved prices is one item definition.
        scaled = _price_shop_env()
        override = {
            "item_key": "t_price_probe",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
            "restock_quantity": 1,
        }
        overridden = _price_shop_env(
            shop_key="t_price_stall_b",
            place_key="t_price_store_b",
            overrides=(override,),
        )
        with _price_shop_scope(scaled, overridden):
            configs = validate_shop_configs(
                [scaled["row"], overridden["row"]],
                scaled["offers"],
                scaled["scales"],
            )
            first = configs["t_price_stall"].offers[0]
            second = configs["t_price_stall_b"].offers[0]
            self.assertEqual(first.item_key, second.item_key)
            self.assertIs(ITEM_REGISTRY[first.item_key], ITEM_REGISTRY[second.item_key])
            self.assertNotEqual(first.buy_copper, second.buy_copper)


if __name__ == "__main__":
    unittest.main()
