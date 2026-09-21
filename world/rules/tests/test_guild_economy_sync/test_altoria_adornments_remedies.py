"""Specialist accessory/remedy shops trade through the ordinary path.

Slice of ``test_guild_economy_sync``: AdornmentsRemediesSyncTests
(altoria-adornments-and-remedies tasks 4.3 + the delta's
reachable/open/tradeable scenarios).

The two newest capital merchant places are located THROUGH THE REGISTRY by
their service kinds — no shipped key, name or price is written in this
module. Against a real sync this proves their interiors are permanent and
reachable, their hosts stand inside them, and a player standing at the
counter can list and buy through the ordinary commands, with the listing
naming the shop's own room.
"""

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement
from commands.economy import CmdBuy, CmdShopStock
from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom
from world.rules.clock import WorldClock
from world.rules.economy import parse_merchant_stock, shop_is_open_at
from world.rules.guild_config import get_catalog
from world.rules.guild_economy import sync_service_content
from world.skills.equipment import list_items

from ._support import ServiceContentIsolation, _places, _settlements


def _specialist_places():
    """The two capital places whose kind is the accessory/remedy trade.

    Located by KIND, never by key: the rows are read from the live registry,
    so this module survives a rename and fails on a missing trade, not on a
    spelling.
    """
    return [
        place
        for place in _places().values()
        if place.kind in ("jeweller", "alchemist")
    ]


def _interior(place):
    return search_object_by_tag(place.key)[0]


def _exterior(place):
    zcoord = _settlements()[place.settlement_key].zcoord
    return GridRoom.objects.filter_xyz(xyz=(*place.exterior_xy, zcoord)).first()


def _midday_tick(config):
    """A tick inside the shop's own authored opening window."""
    return ((config.open_hour + config.close_hour) // 2) * 3600


class AdornmentsRemediesSyncTests(
    ServiceContentIsolation, EvenniaCommandTestMixin, EvenniaTest
):
    def setUp(self):
        super().setUp()
        places = _specialist_places()
        self.assertEqual(
            len(places), 2, "the capital lost its specialist accessory/remedy places"
        )

    @covers_requirement(
        "sample-city-altoria::altoria-service-content-synchronizes-idempotently-without-resetting-live-state"
    )
    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached"
    )
    def test_specialist_interiors_are_permanent_reachable_and_hosted(self):
        sync_service_content()
        for place in _specialist_places():
            with self.subTest(kind=place.kind):
                interiors = search_object_by_tag(place.key)
                self.assertEqual(len(interiors), 1, "interior duplicated")
                interior = interiors[0]
                self.assertIsNone(interior.db.expire_tick)
                exterior = _exterior(place)
                self.assertIn(interior, {exit_obj.destination for exit_obj in exterior.exits})
                self.assertIn(exterior, {exit_obj.destination for exit_obj in interior.exits})
                host = NPC.objects.filter(db_key=place.host_name).first()
                self.assertIsNotNone(host)
                self.assertEqual(host.location, interior)
                self.assertTrue(host.components.has(Merchant.get_component_slot()))

    @covers_requirement(
        "sample-city-altoria::altoria-service-content-synchronizes-idempotently-without-resetting-live-state"
    )
    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached"
    )
    def test_specialist_shops_are_open_and_tradeable_from_the_counter(self):
        sync_service_content()
        for place in _specialist_places():
            with self.subTest(kind=place.kind):
                host = NPC.objects.filter(db_key=place.host_name).first()
                merchant = host.components.get(Merchant.get_component_slot())
                config = get_catalog().shop_configs[merchant.shop_key]
                tick = _midday_tick(config)
                self.assertTrue(shop_is_open_at(merchant.shop_key, tick))

                # The stock listing names the shop's own room and every
                # offered good with its live stock count.
                buyer = create_object(PlayerCharacter, key=f"buyer_{place.kind}")
                buyer.race = place.host_race
                buyer.apply_race_baseline()
                buyer.location = _interior(place)
                buyer.db.wallet = 1_000_000
                stock = parse_merchant_stock(merchant)
                with patch(
                    "world.rules.economy.get_world_clock", return_value=WorldClock(tick)
                ):
                    listing = self.call(CmdShopStock(), "", caller=buyer)
                    # The same open-hours window carries the purchase: buy()
                    # re-reads the clock through the same seam the command does.
                    offer = min(
                        (row for row in config.offers if stock.get(row.item_key, 0) > 0),
                        key=lambda row: row.buy_copper,
                    )
                    # The purchase itself rides the ordinary command, not the
                    # API underneath it: parser, merchant resolution, schedule
                    # gate and trade wiring all have to work for a player.
                    purchase = self.call(
                        CmdBuy(), f"{offer.item_key} 1", caller=buyer
                    )
                self.assertIn("你買了", purchase)
                # The listing is headed by the shop's OWN room name, so the
                # two specialists can never echo each other's counter.
                self.assertIn(place.room_name_zh, listing)
                self.assertIn("營業中", listing)
                for row in config.offers:
                    self.assertIn(row.item_key, listing)
                self.assertIn(offer.item_key, list_items(buyer))
                self.assertLess(buyer.db.wallet, 1_000_000)
                self.assertEqual(
                    parse_merchant_stock(merchant)[offer.item_key],
                    stock[offer.item_key] - 1,
                )
