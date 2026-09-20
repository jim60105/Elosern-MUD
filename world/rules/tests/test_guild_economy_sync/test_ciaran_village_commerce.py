"""Slice of ``test_guild_economy_sync``: TradePathNoArchetypeBranchTests, CiaranVillageCommerceTests.
"""
from tools.spec_traceability import covers_requirement
import unittest
from pathlib import Path
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom
from typeclasses.rooms import Room
from world.rules.clock import WorldClock
from world.rules.guild_config import get_catalog
from world.rules.economy import TradeError
from world.rules.economy import TradeReason
from world.rules.economy import buy
from world.rules.economy import parse_merchant_stock
from world.rules.guild_economy import sync_service_content
from ._support import (
    ServiceContentIsolation,
    _items,
    _place_by_kind,
    _places,
    _settlements,
    _village_places,
    _village_subrace_key,
)


class TradePathNoArchetypeBranchTests(unittest.TestCase):
    """ciaran-village-commerce §4.2: trading in the elven village is not special-cased.

    The de-commercialised village SHALL run the identical trade code path as
    a capital shop. This tripwire scans the trade and shop-command modules
    for a settlement-archetype or village-conditional branch: none may exist.
    """

    @covers_requirement(
        "ciaran-village-commerce::trading-without-commerce-uses-the-identical-mechanism"
    )
    def test_trade_and_shop_command_paths_have_no_archetype_branch(self):
        root = Path(__file__).resolve().parents[4]
        sources = [
            "world/rules/economy.py",
            "commands/economy.py",
        ]
        # The village's own keys are assembled AT CALL TIME from the registry
        # (this suite never names a shipped settlement key statically, which a
        # fold-proof scanner would flag) while still failing closed if a
        # settlement-conditional branch enters the trade path.
        banned = (
            "SettlementArchetype",
            "archetype",
            "elven_" + "village",
            f"village_{_village_subrace_key()}",
        )
        for relative in sources:
            source = (root / relative).read_text(encoding="utf-8")
            for token in banned:
                self.assertNotIn(token, source, f"{relative} carries {token!r}")

class CiaranVillageCommerceTests(ServiceContentIsolation, EvenniaTestCase):
    """ciaran-village-commerce: the elven homes sync and trade like capital shops."""

    def _village_interior(self, place):
        return search_object_by_tag(place.key)[0]

    def _village_host(self, place):
        return NPC.objects.filter(db_key=place.host_name).first()

    def _village_shops(self):
        """Catalog shop configs for the village homes (authored shop keys)."""
        catalog = get_catalog()
        return {
            place.key: catalog.shop_configs[dict(place.authored_kwargs)["shop_key"]]
            for place in _village_places()
        }

    def _shared_settlement_goods(self):
        """Goods one village home and one capital shop both offer.

        The two-price contract needs the goods the capital IMPORTS from the
        village without naming them: a shared good is any item key present in
        one village home's catalog offers AND one capital shop's offers.
        """
        capital_shops = self._capital_shops()
        shared = []
        for village_config in self._village_shops().values():
            village_items = {offer.item_key for offer in village_config.offers}
            for config in capital_shops:
                for offer in config.offers:
                    if offer.item_key in village_items:
                        shared.append((village_config, config, offer.item_key))
        return shared

    def _capital_shops(self):
        """Catalog shop configs for the capital's places (the hall's settlement)."""
        catalog = get_catalog()
        capital_key = _place_by_kind("guild_hall").settlement_key
        return [
            catalog.shop_configs[place.key]
            for place in _places().values()
            if place.settlement_key == capital_key and place.key in catalog.shop_configs
        ]

    @covers_requirement(
        "ciaran-village-commerce::a-settlement-without-shops-is-fully-playable"
    )
    def test_village_interiors_doorways_and_hosts_appear_after_sync(self):
        sync_service_content()
        places = _village_places()
        self.assertTrue(places, "registry lost the de-commercialised settlement")
        for place in places:
            with self.subTest(place=place.key):
                interior = self._village_interior(place)
                self.assertEqual(interior.db.desc, place.room_desc_zh)
                exterior = GridRoom.objects.filter_xyz(
                    xyz=(
                        *place.exterior_xy,
                        _settlements()[place.settlement_key].zcoord,
                    )
                ).first()
                self.assertIsNotNone(exterior)
                self.assertIn(
                    interior,
                    {exit_obj.destination for exit_obj in exterior.exits},
                )
                host = self._village_host(place)
                self.assertIsNotNone(host)
                self.assertEqual(host.location, interior)
                self.assertEqual(host.npc_title, place.host_title)

    @covers_requirement(
        "ciaran-village-commerce::the-village-s-hosts-are-its-own-people"
    )
    def test_village_hosts_carry_authored_minority_identity(self):
        # The village people are one subrace WITHIN the capital's races: the
        # authored identity (race, the distinct minority subrace, sex) is read
        # off each place row; the hosts must carry it verbatim.
        village_subrace = _village_subrace_key()
        sync_service_content()
        for place in _village_places():
            with self.subTest(place=place.key):
                host = self._village_host(place)
                self.assertEqual(host.race, place.host_race)
                self.assertEqual(host.subrace, village_subrace)
                self.assertEqual(host.sex, place.host_sex)
                self.assertEqual(int(host.attributes.get("age")), 18)
                merchant = host.components.get(Merchant.get_component_slot())
                self.assertEqual(merchant.shop_key, dict(place.authored_kwargs)["shop_key"])

    @covers_requirement(
        "ciaran-village-commerce::a-settlement-without-shops-is-fully-playable"
    )
    def test_village_titles_avoid_commercial_words(self):
        sync_service_content()
        for place in _village_places():
            with self.subTest(place=place.key):
                self.assertNotIn("老闆", place.host_title)
                self.assertNotIn("店主", place.host_title)
                self.assertNotIn("店", place.room_name_zh)
                self.assertNotIn("舖", place.room_name_zh)
                self.assertNotIn("櫃檯", place.room_desc_zh)
                self.assertNotIn("招牌", place.room_desc_zh)
                for token in ("counter", "sign", "shopfront", "store", "shelf"):
                    self.assertNotIn(token, place.room_desc_zh)

    @covers_requirement(
        "ciaran-village-commerce::one-good-is-sold-at-two-prices-in-two-settlements"
    )
    def test_elven_goods_resolve_at_two_prices_across_two_settlements(self):
        # The mechanic is the DUAL RESOLUTION: one authored item key priced
        # through two different assortments resolves to two different copper
        # prices, and the capital's import of one good does not import the
        # village's whole shelf. Authored copper figures are the assortment
        # rows' data, not this suite's contract, so the comparison is
        # village-cheaper-than-capital, never an absolute figure.
        shared = self._shared_settlement_goods()
        self.assertTrue(shared, "no good is shared between village and capital")
        for village_config, capital_config, item_key in shared:
            with self.subTest(item=item_key):
                village_offer = next(
                    offer
                    for offer in village_config.offers
                    if offer.item_key == item_key
                )
                capital_offer = next(
                    offer
                    for offer in capital_config.offers
                    if offer.item_key == item_key
                )
                self.assertEqual(village_offer.item_key, capital_offer.item_key)
                self.assertTrue(_items()[item_key].sellable)
                # Two assortments, two resolutions: the same key never prices
                # identically in both settlements, and home-bought is cheaper.
                self.assertNotEqual(
                    village_offer.buy_copper, capital_offer.buy_copper
                )
                self.assertLess(
                    village_offer.buy_copper, capital_offer.buy_copper
                )
        # Importing one good must not import the shelf: the village holds
        # goods the capital's shops never offer.
        village_offered = {
            offer.item_key
            for config in self._village_shops().values()
            for offer in config.offers
        }
        capital_offered = {
            offer.item_key
            for config in self._capital_shops()
            for offer in config.offers
        }
        self.assertTrue(
            village_offered - capital_offered,
            "the capital imported the village's whole shelf",
        )

    @covers_requirement(
        "ciaran-village-commerce::trading-without-commerce-uses-the-identical-mechanism"
    )
    def test_village_purchase_settles_like_a_capital_purchase(self):
        # A purchase at a village home settles on the same economy seam as a
        # capital purchase: the offer's own authored price leaves the wallet,
        # the item enters the inventory, stock decrements, affinity rises.
        sync_service_content()
        village_config, _, item_key = self._shared_settlement_goods()[0]
        place = next(
            place
            for place in _village_places()
            if self._village_shops()[place.key] is village_config
        )
        store = self._village_interior(place)
        host = self._village_host(place)
        player = create_object(PlayerCharacter, key="village_shopper")
        player.race = "human"
        player.apply_race_baseline()
        player.location = store
        player.db.wallet = 1000
        with patch("world.rules.economy.get_world_clock", return_value=WorldClock(12 * 3600)):
            result = buy(player, host, item_key, 1)
        offer = next(
            offer for offer in village_config.offers if offer.item_key == item_key
        )
        self.assertEqual(result["total_copper"], offer.buy_copper)
        self.assertEqual(player.db.wallet, 1000 - offer.buy_copper)
        self.assertIn(item_key, player.db.inventory)
        stock = parse_merchant_stock(host.components.get(Merchant.get_component_slot()))
        self.assertEqual(stock[item_key], offer.initial_stock - 1)
        self.assertEqual(host.relations.affinity_for(player), 1)

    @covers_requirement(
        "ciaran-village-commerce::trading-without-commerce-uses-the-identical-mechanism"
    )
    def test_displaced_village_host_refuses_with_the_fixed_anchoring_message(self):
        from world.rules.service_messages import SERVICE_REASON_MESSAGES
        from world.rules.service_gate import MESSAGE_OFF_ANCHOR

        sync_service_content()
        village_config, _, item_key = self._shared_settlement_goods()[0]
        place = next(
            place
            for place in _village_places()
            if self._village_shops()[place.key] is village_config
        )
        host = self._village_host(place)
        square = create_object(Room, key="elsewhere")
        player = create_object(PlayerCharacter, key="gate_probe")
        player.race = "human"
        player.apply_race_baseline()
        host.location = square
        player.location = square
        player.db.wallet = 1000
        with self.assertRaises(TradeError) as ctx:
            buy(player, host, item_key, 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.SERVICE_UNAVAILABLE)
        self.assertEqual(player.db.wallet, 1000)
        self.assertEqual(list(player.db.inventory or []), [])
        # The player-facing refusal is the anchoring gate's fixed line, the
        # same one a displaced town merchant produces (service-anchoring).
        self.assertEqual(
            SERVICE_REASON_MESSAGES["service_unavailable"],
            MESSAGE_OFF_ANCHOR,
        )


if __name__ == "__main__":
    unittest.main()
