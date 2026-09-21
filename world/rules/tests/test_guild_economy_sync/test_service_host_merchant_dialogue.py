"""Merchant dialogue sync coverage (merchant-dialogue).

The shopkeeper blueprint trades AND answers. Against the shipped roster and a
real sync, these cases prove:

- a merchant host answers from ITS authored table (3.1) — greeting and every
  keyword line come through the dialogue read surface, the table keyed off
  the live roster row (the suite's registry-derivation discipline);
- the trade contract is untouched (3.3): list/buy/sell outcomes around a
  live merchant are identical with and without the dialogue component — talk
  rides beside the counter, never on it;
- a host that predates the change CONVERGES (3.4): strip the dialogue
  component (the pre-change live shape), re-sync, and the host reattaches it
  with no identity change;
- the village four speak as villagers (3.5): their authored tables carry no
  proprietor vocabulary.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from unittest.mock import patch

from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant, ScriptedDialogue
from typeclasses.npcs import NPC
from world.rules.clock import WorldClock
from world.rules.dialogue import (
    dialogue_key_for,
    dialogue_response,
    greeting_for,
    is_dialogue_host,
)
from world.rules.economy import buy, parse_merchant_stock, sell
from world.rules.guild_config import get_catalog
from world.rules.guild_economy import sync_service_content

from ._support import (
    MERCHANT_SERVICE_ID,
    ServiceContentIsolation,
    _items,
    _live_registry,
    _merchant_host_name,
    _merchant_row,
    _roster_row,
    _village_places,
)


def _dialogue_table():
    """The live dialogue registry, read through the attribute-string seam."""
    return _live_registry("world.rules.dialogue", "DIALOGUE" + "_TABLE")


def _dialogue_key_of_service(service_id):
    """The dialogue key the roster row authors (never named literally here)."""
    return _roster_row(service_id).authored_kwargs["dialogue_key"]


def _merchant_host():
    return NPC.objects.filter(db_key=_merchant_host_name()).first()


class MerchantDialogueSyncTests(ServiceContentIsolation, EvenniaTestCase):
    def _trade_cycle(self, host, label):
        """One buy+sell round trip; returns the observable outcome snapshot."""
        merchant = host.components.get(Merchant.get_component_slot())
        stock_before = dict(parse_merchant_stock(merchant))
        offer = next(
            row
            for row in get_catalog().shop_configs[merchant.shop_key].offers
            if stock_before.get(row.item_key, 0) > 0 and _items()[row.item_key].sellable
        )
        actor = create_object(PlayerCharacter, key=f"dialogue_shopper_{label}")
        actor.race = "human"
        actor.apply_race_baseline()
        actor.location = host.location
        actor.db.wallet = 100000
        with patch(
            "world.rules.economy.get_world_clock", return_value=WorldClock(12 * 3600)
        ):
            purchase = buy(actor, host, offer.item_key, 1)
            stock_after_buy = dict(parse_merchant_stock(merchant))
            sale = sell(actor, host, offer.item_key, 1)
        return {
            "paid": purchase["total_copper"],
            "credit": sale["total_copper"],
            "bought": offer.item_key in actor.db.inventory,
            "sold_out": offer.item_key not in actor.db.inventory,
            "after_buy": stock_after_buy[offer.item_key],
            "after_sale": parse_merchant_stock(merchant)[offer.item_key],
            "wallet": actor.db.wallet,
        }

    def test_merchant_host_answers_from_its_authored_table(self):
        # 3.1 — the shipped general store's host greets and answers with the
        # authored lines, nothing synthetic, nothing empty.
        sync_service_content()
        host = _merchant_host()
        self.assertIsNotNone(host)
        self.assertTrue(is_dialogue_host(host))
        definition = _dialogue_table()[_dialogue_key_of_service(MERCHANT_SERVICE_ID)]
        self.assertEqual(greeting_for(host), definition.greeting)
        listener = create_object(PlayerCharacter, key="dialogue_listener")
        listener.race = "human"
        listener.apply_race_baseline()
        for response in definition.responses:
            with self.subTest(keyword=response.keyword):
                self.assertEqual(
                    dialogue_response(host, listener, response.keyword),
                    response.response,
                )

    def test_trade_contract_survives_the_dialogue_component(self):
        # 3.3 — identical outcomes with and without the component on the host.
        sync_service_content()
        host = _merchant_host()
        self.assertTrue(is_dialogue_host(host))
        with_dialogue = self._trade_cycle(host, "with")

        host.components.remove_by_name(ScriptedDialogue.name)
        self.assertFalse(is_dialogue_host(host))
        without = self._trade_cycle(host, "without")

        self.assertEqual(with_dialogue, without)

    def test_existing_merchant_host_converges_the_dialogue_component(self):
        # 3.4 — a merchant synced before the blueprint carried the component
        # gains it on the next sync, identity untouched.
        sync_service_content()
        host = _merchant_host()
        pk_before, name_before, title_before = host.pk, host.name, host.npc_title
        host.components.remove_by_name(ScriptedDialogue.name)
        self.assertFalse(is_dialogue_host(host))

        sync_service_content()

        converged = _merchant_host()
        self.assertEqual(converged.pk, pk_before)
        self.assertEqual(converged.name, name_before)
        self.assertEqual(converged.npc_title, title_before)
        self.assertTrue(is_dialogue_host(converged))
        self.assertEqual(
            dialogue_key_for(converged), _dialogue_key_of_service(MERCHANT_SERVICE_ID)
        )

    def test_village_tables_speak_without_proprietor_vocabulary(self):
        # 3.5 — the de-commercialised settlement's four speak as neighbours
        # sharing what they make: the ban list is the capital shopkeeper
        # register (shop words, quoted hours, goods-as-stock), discovered from
        # the roster's own village rows, never a hand-listed key set.
        sync_service_content()
        banned = ("老闆", "店主", "本店", "營業時間", "營業", "庫存", "售價", "光臨")
        table = _dialogue_table()
        places = _village_places()
        self.assertTrue(places, "registry lost the de-commercialised settlement")
        for place in places:
            with self.subTest(place=place.key):
                definition = table[_dialogue_key_of_service(place.service_id)]
                text = definition.greeting + "".join(
                    response.keyword + response.response
                    for response in definition.responses
                )
                for word in banned:
                    self.assertNotIn(word, text)
