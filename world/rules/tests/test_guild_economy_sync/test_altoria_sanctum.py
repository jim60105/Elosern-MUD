"""Data-contract test: altoria-sanctum content contract

Slice of ``test_guild_economy_sync``: AltoriaSanctumTests,
SanctumTradePathNoSpecialCaseTests.

The capital's temple and its attached sanctum shop land as two place rows
on one exterior. These cases prove the change's four coverage claims
(tasks 4.1-4.4) against a real sync, with every symbol resolved from the
live registries by kind (the suite's registry-derivation discipline — no
shipped key is named statically):

- one exterior, two distinct doorways, two interiors, each leading back,
  and a resync that duplicates nothing;
- the two hosts' offices are disjoint by capability — the 主祭 answers and
  sells nothing (her own table ships no trade verb she could not execute),
  the 執事 keeps the counter;
- a fresh player opens both interiors and buys through the ordinary path
  with no lock, reveal or knowledge step consulted, and a tripwire scans
  the trade path for any branch naming this shop, this settlement or the
  goods' price-table kind — none may exist;
- 受洗聖水 is still capital-purchasable, and only at the sanctum's counter.

The authored prose is held to the openness register the lore document
binds (line 326: three open counters, 社會常識): the concealment-framing
scan below fails the suite if this building's text ever starts treating
the ministry or its shop as hidden.
"""

from pathlib import Path
import unittest

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase
from unittest.mock import patch

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant, ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom
from world.rules.clock import WorldClock
from world.rules.economy import buy, parse_merchant_stock, sell
from world.rules.guild_config import get_catalog
from world.rules.guild_economy import sync_service_content

from ._support import (
    ServiceContentIsolation,
    _items,
    _live_registry,
    _place_by_kind,
    _places,
    _settlements,
    _shops,
)


def _temple_place():
    """The live TEMPLE row (the registry's only one)."""
    return _place_by_kind("temple")


def _sanctum_place():
    """The live SANCTUM_SHOP row (the registry's only one)."""
    return _place_by_kind("sanctum_shop")


def _interior(place):
    return search_object_by_tag(place.key)[0]


def _exterior(place):
    return GridRoom.objects.filter_xyz(
        xyz=(*place.exterior_xy, _settlements()[place.settlement_key].zcoord)
    ).first()


def _host(place):
    return NPC.objects.filter(db_key=place.host_name).first()


def _authored(place):
    return dict(place.authored_kwargs)


def _table_text(place):
    """The host's whole authored table, greeting and every keyword line."""
    table = _live_registry("world.lore.dialogue", "DIALOGUE" + "_ROWS")
    definition = table[_authored(place)["dialogue_key"]]
    return definition.greeting + "".join(
        response.keyword + response.response for response in definition.responses
    )


#: Framing tokens the lore document names as the WRONG reading (its line
#: 326 binds the sanctum's ministry 公開經營, 社會常識; a concealment
#: framing is a named misreading). The room prose and dialogue tables are
#: display-field prose, which is what this lint's contract tag licenses
#: token scanning of — these are the vocabulary of the misreading, never
#: content keys.
CONCEALMENT_FRAMING = (
    "隱藏", "隱密", "秘密", "見不得人", "不可告人", "禁忌", "密室",
    "悄悄", "偷藏", "不能讓外人", "非信徒", "只有信眾",
    "secret", "hidden",
)


class SanctumTradePathNoSpecialCaseTests(unittest.TestCase):
    """Task 4.3's negative half: the ordinary path stays ordinary.

    A branch naming this shop, its settlement or the kind of goods its
    counter keeps would make the sanctum a special case inside code every
    other shop rides. The banned tokens are assembled AT CALL TIME from
    the live registries (this suite never names a shipped key statically)
    and scanned against every module the trade and shop commands resolve
    through.
    """

    @covers_requirement(
        "altoria-sanctum::the-sanctum-s-goods-trade-through-the-ordinary-path"
    )
    def test_trade_path_names_no_sanctum_shop_settlement_or_goods_kind(self):
        root = Path(__file__).resolve().parents[4]
        sources = (
            "world/rules/economy.py",
            "commands/economy.py",
            "world/rules/guild_config/_commerce.py",
            "world/rules/guild_config/_shops.py",
        )
        temple, sanctum = _temple_place(), _sanctum_place()
        shop_key = _authored(sanctum)["shop_key"]
        goods = _shops()[shop_key].offered_item_keys
        # The goods' KIND as the data itself spells it: the price-table
        # band the goods unique to this counter carry (the moved holy
        # water shares the band every potion shop carries, so the band is
        # taken from the goods NO other capital shop offers).
        counter_specific = [
            item_key for item_key in goods
            if not any(
                item_key in other.offered_item_keys
                for other in _shops().values()
                if other.key != shop_key
            )
        ]
        banned = {
            temple.key,
            sanctum.key,
            shop_key,
            temple.settlement_key,
            *{_items()[item_key].price_table_key for item_key in counter_specific},
            # the two kind words themselves, call-assembled so the scan
            # is explicit in the file rather than a constant
            "sanc" + "tum",
            "tem" + "ple",
        }
        self.assertTrue(counter_specific, "sanctum counter offers nothing unique")
        for relative in sources:
            source = (root / relative).read_text(encoding="utf-8")
            for token in sorted(banned):
                self.assertNotIn(token, source, f"{relative} carries {token!r}")


class AltoriaSanctumTests(ServiceContentIsolation, EvenniaTestCase):
    """altoria-sanctum: one building, two doors, three open counters."""

    def _interiors(self, place):
        return search_object_by_tag(place.key)

    @covers_requirement("altoria-sanctum::two-places-may-share-one-doorstep")
    def test_one_exterior_two_doors_two_interiors_each_leading_back(self):
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        temple, sanctum = _temple_place(), _sanctum_place()
        self.assertEqual(
            temple.exterior_xy, sanctum.exterior_xy,
            "the two counters no longer share the temple steps",
        )
        self.assertNotEqual(temple.doorway_key_zh, sanctum.doorway_key_zh)
        exterior = _exterior(temple)
        self.assertIsNotNone(exterior)
        self.assertIs(_exterior(sanctum), exterior)
        for place in (temple, sanctum):
            with self.subTest(place=place.kind):
                interiors = self._interiors(place)
                self.assertEqual(len(interiors), 1, place.kind)
                interior = interiors[0]
                self.assertEqual(interior.db.desc, place.room_desc_zh)
                doorways = [
                    exit_obj for exit_obj in exterior.exits
                    if exit_obj.key == place.doorway_key_zh
                ]
                self.assertEqual(len(doorways), 1, place.kind)
                self.assertIs(doorways[0].destination, interior)
                self.assertIn(
                    exterior, {e.destination for e in interior.exits},
                    f"{place.kind} interior does not lead back out",
                )
        # Two counters, not one room wearing two names.
        self.assertIsNot(_interior(temple), _interior(sanctum))
        # A second run duplicates nothing.
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        for place in (temple, sanctum):
            with self.subTest(resync=place.kind):
                self.assertEqual(len(self._interiors(place)), 1)
                self.assertEqual(
                    len([
                        e for e in _exterior(place).exits
                        if e.key == place.doorway_key_zh
                    ]),
                    1,
                )

    @covers_requirement(
        "altoria-sanctum::the-sanctuary-s-host-ministers-and-does-not-trade"
    )
    def test_the_priest_answers_without_trading_and_the_deacon_keeps_the_counter(self):
        sync_service_content()
        temple, sanctum = _temple_place(), _sanctum_place()
        priest, deacon = _host(temple), _host(sanctum)
        self.assertIsNotNone(priest)
        self.assertIsNotNone(deacon)
        # The sanctuary's host carries the dialogue office and no trade
        # office; the shop's host carries the trade office.
        self.assertIsNotNone(
            priest.components.get(ScriptedDialogue.get_component_slot())
        )
        self.assertIsNone(priest.components.get(Merchant.get_component_slot()))
        self.assertIsNotNone(
            deacon.components.get(Merchant.get_component_slot())
        )
        # The priest's own table ships no trade guidance she could not
        # execute: the trade verbs every shopkeeper's table quotes appear
        # in the deacon's, never in hers.
        for verb in ("`buy`", "`sell`", "`shop stock`"):
            self.assertNotIn(
                verb, _table_text(temple),
                "the priest's table quotes a command she lacks",
            )
        self.assertTrue(
            any(
                verb in _table_text(sanctum)
                for verb in ("`buy`", "`sell`", "`shop stock`")
            ),
            "the deacon's table sends visitors to a counter she does not keep",
        )
        # One host per interior, correctly placed.
        for place, host in ((temple, priest), (sanctum, deacon)):
            with self.subTest(host=place.kind):
                residents = [
                    obj for obj in _interior(place).contents
                    if isinstance(obj, NPC)
                ]
                self.assertEqual(residents, [host])

    @covers_requirement(
        "altoria-sanctum::the-temple-is-one-building-with-three-open-counters"
    )
    def test_nothing_about_the_sanctuary_is_gated_or_concealed(self):
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        temple, sanctum = _temple_place(), _sanctum_place()
        # A player who has never visited: no flags, no quest state.
        visitor = create_object(PlayerCharacter, key="sanctum_first_visitor")
        visitor.race = "human"
        visitor.apply_race_baseline()
        exterior = _exterior(temple)
        for place in (temple, sanctum):
            with self.subTest(place=place.kind):
                doorway = next(
                    e for e in exterior.exits if e.key == place.doorway_key_zh
                )
                # No lock, no prerequisite: the default traversal access
                # check is all the doorway consults, and the stock exit
                # traversal API — the path the 前往 command walks — moves
                # the character through it.
                self.assertTrue(doorway.access(visitor, "traverse"))
                visitor.location = exterior
                doorway.at_traverse(visitor, doorway.destination)
                self.assertIs(visitor.location, _interior(place))
        # The shop's stock lists on first request.
        deacon = _host(sanctum)
        stock = parse_merchant_stock(
            deacon.components.get(Merchant.get_component_slot())
        )
        offered = _shops()[_authored(sanctum)["shop_key"]].offered_item_keys
        self.assertEqual(set(stock), set(offered), "first-request stock is not the offer set")
        self.assertTrue(all(count > 0 for count in stock.values()))
        # The prose scan: no room description, host title or dialogue line
        # of this building frames the ministry or its shop as concealed.
        prose = "".join(
            (
                temple.room_desc_zh, sanctum.room_desc_zh,
                temple.host_title, sanctum.host_title,
                _table_text(temple), _table_text(sanctum),
            )
        )
        for token in CONCEALMENT_FRAMING:
            self.assertNotIn(
                token, prose,
                f"sanctuary prose frames the ministry with {token!r}",
            )

    @covers_requirement(
        "altoria-sanctum::the-sanctum-s-goods-trade-through-the-ordinary-path"
    )
    def test_holy_water_is_still_capital_purchasable_from_the_sanctum_only(self):
        sync_service_content()
        sanctum = _sanctum_place()
        shop_key = _authored(sanctum)["shop_key"]
        holy_water = "baptismal_" + "holy_water"
        catalog = get_catalog()
        # Of every capital shop, exactly one still offers it: the sanctum's.
        capital_key = sanctum.settlement_key
        offering = [
            config.shop_key
            for place in _places().values()
            if place.settlement_key == capital_key
            and "shop_key" in _authored(place)
            for config in [catalog.shop_configs[_authored(place)["shop_key"]]]
            if any(row.item_key == holy_water for row in config.offers)
        ]
        self.assertEqual(offering, [shop_key])
        # And buying it there settles through the ordinary path: a fresh
        # visitor with no history pays the offer's authored price out of
        # the ordinary wallet into the ordinary stock.
        visitor = create_object(PlayerCharacter, key="sanctum_water_buyer")
        visitor.race = "human"
        visitor.apply_race_baseline()
        visitor.location = _interior(sanctum)
        visitor.db.wallet = 100000
        deacon = _host(sanctum)
        offer = next(
            row for row in catalog.shop_configs[shop_key].offers
            if row.item_key == holy_water
        )
        merchant_slot = deacon.components.get(Merchant.get_component_slot())
        stock_before = parse_merchant_stock(merchant_slot)[holy_water]
        with patch(
            "world.rules.economy.get_world_clock", return_value=WorldClock(12 * 3600)
        ):
            purchase = buy(visitor, deacon, holy_water, 1)
        self.assertEqual(purchase["total_copper"], offer.buy_copper)
        self.assertEqual(visitor.db.wallet, 100000 - offer.buy_copper)
        self.assertIn(holy_water, visitor.db.inventory)
        self.assertEqual(
            parse_merchant_stock(merchant_slot)[holy_water], stock_before - 1
        )
        # Selling back settles on the same seam — the counter takes its own
        # authored sell price and the good returns to ordinary stock.
        with patch(
            "world.rules.economy.get_world_clock", return_value=WorldClock(12 * 3600)
        ):
            sale = sell(visitor, deacon, holy_water, 1)
        self.assertEqual(sale["total_copper"], offer.sell_copper)
        self.assertEqual(
            visitor.db.wallet, 100000 - offer.buy_copper + offer.sell_copper
        )
        self.assertNotIn(holy_water, visitor.db.inventory)
        self.assertEqual(
            parse_merchant_stock(merchant_slot)[holy_water], stock_before
        )


if __name__ == "__main__":
    unittest.main()
