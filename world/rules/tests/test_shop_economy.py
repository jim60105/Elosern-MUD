"""Atomic shop trade tests (tasks 9.1-9.5).

Every trade rides kit rows: one synthetic shop config over three kit items
(scoped item/price/shop registries), with the offer rules authored here so
each assertion names its own numbers.
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase

from commands.localized import CmdDrop, CmdGet, CmdGive
from commands.economy import CmdBuy, CmdSell
from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.definitions import QuestStage
from world.quests.runtime import read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept as accept_quest_record,
    acquire as acquire_objective,
    quest as quest_definition,
    register as register_quest,
)
from world.lore.settlements.assortments import AssortmentDefinition
from world.lore.settlements.shops import ShopDefinition
from world.rules.clock import WorldClock
from world.rules.economy import (
    TradeError,
    TradeReason,
    buy,
    parse_merchant_stock,
    sell,
    shop_is_open,
)
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.guild_config import (
    GuildConfigError,
    ItemOfferRule,
    validate_shop_configs,
)
from world.rules.party import join_party
from world.rules.party_scope import (
    REASON_MEMBER_NOT_PRESENT,
    REASON_NOT_PARTY_MEMBER,
    PartyScopeError,
)
from world.rules.surfaces import attribute_snapshot
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    live_item_registry,
    live_price_table,
    price_band,
    synth_catalog,
    synth_offer_rule,
    synth_shop_config,
)
from world.skills.equipment import list_items
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_SHOPS,
    make_item,
    make_price,
)
from world.tests.synthetic_data.data_world import SYNTH_PLACES

T_SHOP = next(iter(SYNTH_SHOPS))
_T_SPRAY = SYNTH_ITEMS["t_ember_spray"].key
_T_FANG = SYNTH_ITEMS["t_iron_fang"].key
_T_APPLE = SYNTH_ITEMS["t_huskapple"].key
# The unsellable kit row (exercises the sellable gate's negative path).
_T_PASS = SYNTH_ITEMS["t_wayfarer_pass"].key
# The kit's slotted weapon: the equipped-removal guard needs real equipment.
_T_KNIFE = SYNTH_ITEMS["t_thorn_knife"].key


def _buy_copper(item_key: str) -> int:
    """The synthetic offer's buy price (mirrors synth_offer_rule derivation)."""
    floor, ceiling = price_band(item_key)
    buy_copper = floor + 2
    if ceiling is not None and buy_copper > ceiling:
        buy_copper = ceiling
    return buy_copper


def _sell_copper(item_key: str) -> int:
    return price_band(item_key)[0]


def _shop_config():
    """Built inside the scope: the offer rules read live price bands."""
    return synth_shop_config(
        T_SHOP,
        (_T_SPRAY, _T_FANG, _T_APPLE, _T_KNIFE),
        offer_rules=(
            synth_offer_rule(_T_SPRAY, max_stock=20),
            synth_offer_rule(_T_FANG, max_stock=3),
            synth_offer_rule(_T_APPLE, max_stock=20),
            # Low starting stock so guard sells never overflow the cap.
            synth_offer_rule(_T_KNIFE, max_stock=20, initial_stock=1),
        ),
    )


def _stock() -> dict[str, int]:
    return {_T_APPLE: 20, _T_SPRAY: 3, _T_FANG: 1}


class ShopRegistryIsolation(QuestRegistryIsolation):
    def setUp(self):
        # Scope before construction so catalog building and every trade-side
        # registry lookup resolve against kit rows.
        open_synthetic_scope(self, "items", "prices", "shops")
        super().setUp()
        register_catalog()
        install_synthetic_catalog(
            self, synth_catalog(shop_configs={T_SHOP: _shop_config()})
        )
        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()


class ShopTradeTests(ShopRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.store = create_object(Room, key="store")
        self.merchant_npc = create_object(NPC, key="t_synth_stallkeeper", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc,
            service_id="store",
            shop_key=T_SHOP,
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = _stock()
        self.player = create_object(PlayerCharacter, key="shopper")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.store
        self.player.db.wallet = 100

    def _open_clock(self, hour=12):
        tick = hour * 3600
        return WorldClock(tick)

    @covers_requirement("shop-economy::buying-and-selling-commit-wallet-inventory-acquisition-progress-and-stock-atomically", "affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths")
    def test_successful_purchase_uses_integer_copper(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = buy(self.player, self.merchant_npc, _T_APPLE, 2, self.player.pk)
        self.assertEqual(result["total_copper"], _buy_copper(_T_APPLE) * 2)
        self.assertEqual(result["wallet"], 100 - _buy_copper(_T_APPLE) * 2)
        self.assertEqual(list_items(self.player), [_T_APPLE, _T_APPLE])
        stock = parse_merchant_stock(self.merchant)
        self.assertEqual(stock[_T_APPLE], 18)
        self.assertEqual(self.merchant_npc.relations.affinity_for(self.player), 1)

    def test_insufficient_funds_changes_nothing(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, _T_FANG, 1, self.player.pk)
        self.assertEqual(ctx.exception.args[0], TradeReason.INSUFFICIENT_FUNDS)
        self.assertEqual(self.player.db.wallet, 100)
        self.assertEqual(list_items(self.player), [])
        self.assertGreater(_buy_copper(_T_FANG), 100)
        self.assertEqual(parse_merchant_stock(self.merchant)[_T_FANG], 1)
        self.assertFalse(self.merchant_npc.relations.has_record(self.player))

    def test_insufficient_stock_changes_nothing(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, _T_SPRAY, 4, self.player.pk)
        self.assertEqual(ctx.exception.args[0], TradeReason.INSUFFICIENT_STOCK)

    def test_sale_cannot_overflow_merchant_stock(self):
        self.player.db.wallet = 0
        self.player.db.inventory = [_T_FANG, _T_FANG, _T_FANG]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                sell(self.player, self.merchant_npc, _T_FANG, 3, self.player.pk)
        self.assertEqual(ctx.exception.args[0], TradeReason.STOCK_OVERFLOW)
        self.assertEqual(self.player.db.wallet, 0)
        self.assertEqual(
            list_items(self.player),
            [_T_FANG, _T_FANG, _T_FANG],
        )
        self.assertFalse(self.merchant_npc.relations.has_record(self.player))

    def test_successful_sale_credits_exact_copper(self):
        self.player.db.wallet = 0
        self.player.db.inventory = [_T_SPRAY, _T_SPRAY]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, _T_SPRAY, 2, self.player.pk)
        self.assertEqual(result["total_copper"], _sell_copper(_T_SPRAY) * 2)
        self.assertEqual(self.player.db.wallet, _sell_copper(_T_SPRAY) * 2)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(parse_merchant_stock(self.merchant)[_T_SPRAY], 5)
        self.assertEqual(self.merchant_npc.relations.affinity_for(self.player), 1)

    @covers_requirement("shop-economy::item-and-shop-identities-are-immutable-while-numeric-trade-rules-are-yaml-and-lore-constrained")
    def test_unknown_or_unsellable_item_rejected(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError):
                buy(self.player, self.merchant_npc, "no_such_item", 1, self.player.pk)
        with self.assertRaises(TradeError) as ctx:
            sell(self.player, self.merchant_npc, "no_such_item", 1, self.player.pk)
        self.assertEqual(ctx.exception.args[0], TradeReason.UNKNOWN_ITEM)
        # The kit pass is a genuinely unsellable registry item; the sellable
        # gate precedes merchant and shop-open resolution.
        self.player.db.inventory = [_T_PASS]
        with self.assertRaises(TradeError) as ctx:
            sell(self.player, self.merchant_npc, _T_PASS, 1, self.player.pk)
        self.assertEqual(ctx.exception.args[0], TradeReason.UNSELLABLE)
        self.assertEqual(self.player.db.inventory, [_T_PASS])

    @covers_requirement(
        "lore-item-catalog::a-non-sellable-item-never-reaches-a-merchant-transaction"
    )
    def test_non_sellable_item_refuses_trade_and_outranks_shop_listing(self):
        self.player.db.wallet = 100
        self.player.db.inventory = [_T_PASS]
        # Selling an unsellable item is refused, wallet and inventory unchanged
        with self.assertRaises(TradeError) as ctx:
            sell(self.player, self.merchant_npc, _T_PASS, 1, self.player.pk)
        self.assertEqual(ctx.exception.args[0], TradeReason.UNSELLABLE)
        self.assertEqual(self.player.db.wallet, 100)
        self.assertEqual(self.player.db.inventory, [_T_PASS])

        # Even if a synthetic shop's offers explicitly list the unsellable key:
        config_with_pass = synth_shop_config(
            T_SHOP,
            (_T_SPRAY, _T_FANG, _T_APPLE, _T_KNIFE, _T_PASS),
            offer_rules=(
                synth_offer_rule(_T_SPRAY, max_stock=20),
                synth_offer_rule(_T_FANG, max_stock=3),
                synth_offer_rule(_T_APPLE, max_stock=20),
                synth_offer_rule(_T_KNIFE, max_stock=20, initial_stock=1),
                synth_offer_rule(_T_PASS, max_stock=10, initial_stock=5),
            ),
        )
        install_synthetic_catalog(
            self, synth_catalog(shop_configs={T_SHOP: config_with_pass})
        )
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            # Selling is still refused by item sellability
            with self.assertRaises(TradeError) as ctx:
                sell(self.player, self.merchant_npc, _T_PASS, 1, self.player.pk)
            self.assertEqual(ctx.exception.args[0], TradeReason.UNSELLABLE)
            self.assertEqual(self.player.db.wallet, 100)
            self.assertEqual(self.player.db.inventory, [_T_PASS])

            # Buying is also refused by item sellability
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, _T_PASS, 1, self.player.pk)
            self.assertEqual(ctx.exception.args[0], TradeReason.UNSELLABLE)
            self.assertEqual(self.player.db.wallet, 100)
            self.assertEqual(self.player.db.inventory, [_T_PASS])

    @covers_requirement(
        "lore-item-catalog::a-non-sellable-item-never-reaches-a-merchant-transaction"
    )
    def test_a_listed_keepsake_refuses_both_directions_before_any_write(self):
        # A file-local keepsake-band item that a synthetic shop lists anyway:
        # the load-time rejections keep such a listing from shipping, and this
        # is the runtime backstop. Buy and sell must refuse on the item's own
        # sellability before wallet, inventory, stock, acquisition progress or
        # affinity change -- and the held keepsake stays holdable and
        # inspectable.
        keepsake = make_item(
            "t_keepsake_probe",
            display_name_zh="合成信物",
            price_table_key="t_keepsake_band",
            sellable=False,
        )
        band = make_price(
            "t_keepsake_band",
            display_name_zh="合成信物帶",
            min_copper=999_999,
            max_copper=None,
            notes="Synthetic keepsake band.",
        )
        config = synth_shop_config(
            T_SHOP,
            (_T_SPRAY, _T_FANG, _T_APPLE, _T_KNIFE, keepsake.key),
            offer_rules=(
                synth_offer_rule(_T_SPRAY, max_stock=20),
                synth_offer_rule(_T_FANG, max_stock=3),
                synth_offer_rule(_T_APPLE, max_stock=20),
                synth_offer_rule(_T_KNIFE, max_stock=20, initial_stock=1),
                ItemOfferRule(
                    item_key=keepsake.key,
                    buy_copper=999_999,
                    sell_copper=0,
                    max_stock=2,
                    initial_stock=2,
                    restock_quantity=1,
                ),
            ),
        )
        live_item_registry()[keepsake.key] = keepsake
        live_price_table()[band.key] = band
        try:
            install_synthetic_catalog(
                self, synth_catalog(shop_configs={T_SHOP: config})
            )
            self.player.db.wallet = 5_000_000
            self.player.db.inventory = [keepsake.key]
            self.player.db.quest_log = []

            def snapshot():
                return (
                    int(self.player.db.wallet),
                    list(self.player.db.inventory),
                    list(self.player.db.quest_log or []),
                    dict(parse_merchant_stock(self.merchant)),
                    self.merchant_npc.relations.has_record(self.player),
                    self.merchant_npc.relations.affinity_for(self.player),
                )

            before = snapshot()
            with patch(
                "world.rules.economy.get_world_clock",
                return_value=self._open_clock(),
            ):
                with self.assertRaises(TradeError) as ctx:
                    sell(self.player, self.merchant_npc, keepsake.key, 1, self.player.pk)
                self.assertEqual(ctx.exception.args[0], TradeReason.UNSELLABLE)
                with self.assertRaises(TradeError) as ctx:
                    buy(self.player, self.merchant_npc, keepsake.key, 1, self.player.pk)
                self.assertEqual(ctx.exception.args[0], TradeReason.UNSELLABLE)
            self.assertEqual(snapshot(), before)

            # Still held and inspectable: identity and presentation resolve.
            self.assertEqual(list_items(self.player), [keepsake.key])
            held = live_item_registry()[keepsake.key]
            self.assertEqual(held.display_name_zh, "合成信物")
            self.assertTrue(held.presentation.summary_zh.strip())
        finally:
            live_item_registry().pop(keepsake.key, None)
            live_price_table().pop(band.key, None)

    @covers_requirement(
        "lore-item-catalog::registration-does-not-entitle-an-item-to-a-market"
    )
    def test_unstocked_registered_item_functional_and_refuses_buy_as_not_offered(self):
        unstocked_key = "t_unstocked_item"
        unstocked_def = make_item(
            unstocked_key,
            display_name_zh="合成未上架信物",
            price_table_key="t_ironbite_steel",
        )
        live_item_registry()[unstocked_key] = unstocked_def

        # Can be granted into inventory and inspected
        self.player.db.inventory = [unstocked_key]
        self.assertIn(unstocked_key, self.player.db.inventory)
        item = live_item_registry()[unstocked_key]
        self.assertEqual(item.display_name_zh, "合成未上架信物")
        self.assertTrue(item.presentation.summary_zh)

        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            # Buying the unstocked registered item is refused with NOT_OFFERED
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, unstocked_key, 1, self.player.pk)
            self.assertEqual(ctx.exception.args[0], TradeReason.NOT_OFFERED)

            # Distinct from an unknown key which produces UNKNOWN_ITEM
            with self.assertRaises(TradeError) as ctx_unknown:
                buy(self.player, self.merchant_npc, "completely_unknown_key", 1, self.player.pk)
            self.assertEqual(ctx_unknown.exception.args[0], TradeReason.UNKNOWN_ITEM)

    def test_closed_shop_rejects_trade(self):
        with patch("world.rules.economy.get_world_clock", return_value=WorldClock(3 * 3600)):
            self.assertFalse(shop_is_open(T_SHOP))
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, _T_APPLE, 1, self.player.pk)
            self.assertEqual(ctx.exception.args[0], TradeReason.CLOSED)

    def test_bad_quantity_rejected(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            for bad in (0, -1, 1.5, True):
                with self.subTest(quantity=bad):
                    with self.assertRaises(TradeError) as ctx:
                        buy(self.player, self.merchant_npc, _T_APPLE, bad, self.player.pk)
                    self.assertEqual(ctx.exception.args[0], TradeReason.BAD_QUANTITY)

    def test_remote_merchant_rejected(self):
        other = create_object(Room, key="other")
        self.player.location = other
        with self.assertRaises(TradeError) as ctx:
            buy(self.player, self.merchant_npc, _T_APPLE, 1, self.player.pk)
        self.assertEqual(ctx.exception.args[0], TradeReason.REMOTE_MERCHANT)

    def _make_place_bound(self):
        # The sync writes these on every shipped host; the hand-built shop
        # fixture emulates one converged place-bound merchant (service-
        # anchoring): its anchor is the store it was assembled for.
        self.merchant.service_binding = "place"
        self.merchant.anchor_room_id = self.store.pk

    @covers_requirement(
        "shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant"
    )
    def test_traveling_place_bound_merchant_refuses_without_state_change(self):
        from commands.economy import CmdShopStock
        from world.rules.service_gate import MESSAGE_OFF_ANCHOR

        self._make_place_bound()
        square = create_object(Room, key="town square")
        self.merchant_npc.location = square
        self.player.location = square
        wallet_before = self.player.db.wallet
        with self.assertRaises(TradeError) as ctx:
            buy(self.player, self.merchant_npc, _T_APPLE, 1, self.player.pk)
        self.assertEqual(ctx.exception.args[0], TradeReason.SERVICE_UNAVAILABLE)
        self.assertEqual(self.player.db.wallet, wallet_before)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(parse_merchant_stock(self.merchant)[_T_APPLE], 20)
        self.assertFalse(self.merchant_npc.relations.has_record(self.player))
        # Stock listing refuses with the gate's fixed line, not a stock dump.
        output = self.call(CmdShopStock(), "", caller=self.player)
        self.assertEqual(output, MESSAGE_OFF_ANCHOR)

    def test_at_anchor_place_bound_merchant_behaves_as_before_the_gate(self):
        self._make_place_bound()
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = buy(self.player, self.merchant_npc, _T_APPLE, 1, self.player.pk)
        self.assertEqual(result["total_copper"], _buy_copper(_T_APPLE))
        self.assertEqual(self.player.db.wallet, 100 - _buy_copper(_T_APPLE))

    @covers_requirement(
        "shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant"
    )
    def test_person_bound_merchant_trades_anywhere(self):
        # A person-bound host travels with no anchor: co-presence is the only
        # requirement, so the gate never fires away from any room.
        self.merchant.service_binding = "person"
        square = create_object(Room, key="market square")
        self.merchant_npc.location = square
        self.player.location = square
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = buy(self.player, self.merchant_npc, _T_APPLE, 1, self.player.pk)
        self.assertEqual(result["total_copper"], _buy_copper(_T_APPLE))
        self.assertEqual(self.player.db.wallet, 100 - _buy_copper(_T_APPLE))

    @covers_requirement("affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths")
    def test_non_npc_merchant_host_is_rejected_before_any_write(self):
        from typeclasses.monsters import Monster

        fake = create_object(Monster, key="fake merchant", location=self.store)
        fake.components.add(
            Merchant.create(fake, service_id="m", shop_key=T_SHOP)
        )
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, fake, _T_APPLE, 1, self.player.pk)
        self.assertEqual(ctx.exception.args[0], TradeReason.NO_MERCHANT)
        self.assertEqual(self.player.db.wallet, 100)
        self.assertEqual(list_items(self.player), [])
        self.assertFalse(fake.relations.has_record(self.player))

    def test_fault_injection_restores_every_trade_surface(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            snapshot = (
                self.player.db.wallet,
                list(self.player.db.inventory or []),
                parse_merchant_stock(self.merchant)[_T_APPLE],
                self.merchant_npc.db.relations_data,
            )

            class FakeAtomic:
                def __enter__(self):
                    return self

                def __exit__(self, *exc_info):
                    raise RuntimeError("db failure")

            with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
                with self.assertRaises(RuntimeError):
                    buy(self.player, self.merchant_npc, _T_APPLE, 2, self.player.pk)
            self.assertEqual(
                (
                    self.player.db.wallet,
                    list(self.player.db.inventory or []),
                    parse_merchant_stock(self.merchant)[_T_APPLE],
                    self.merchant_npc.db.relations_data,
                ),
                snapshot,
            )

    def test_no_float_created_by_trade(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, _T_APPLE, 1, self.player.pk)
        self.assertNotIsInstance(self.player.db.wallet, float)
        self.assertEqual(self.player.db.wallet, 100 - _buy_copper(_T_APPLE))

    def _contained(self, item_key):
        return [obj for obj in self.player.contents if obj.key == item_key]

    @covers_requirement("shop-economy::shop-economy-stays-consistent-with-the-canonical-inventory")
    @covers_requirement("equipment-inventory::the-key-list-is-the-single-canonical-inventory-record-for-registry-items")
    def test_buy_materializes_a_contained_object_per_item(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, _T_APPLE, 2, self.player.pk)
        self.assertEqual(len(self._contained(_T_APPLE)), 2)
        self.assertTrue(
            all(obj.db.registry_key == _T_APPLE for obj in self._contained(_T_APPLE))
        )
        self.assertEqual(list_items(self.player), [_T_APPLE, _T_APPLE])

    @covers_requirement("shop-economy::shop-economy-stays-consistent-with-the-canonical-inventory")
    def test_sell_removes_the_contained_objects(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, _T_APPLE, 2, self.player.pk)
            sell(self.player, self.merchant_npc, _T_APPLE, 1, self.player.pk)
        self.assertEqual(len(self._contained(_T_APPLE)), 1)
        self.assertEqual(list_items(self.player), [_T_APPLE])
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            sell(self.player, self.merchant_npc, _T_APPLE, 1, self.player.pk)
        self.assertEqual(self._contained(_T_APPLE), [])
        self.assertEqual(list_items(self.player), [])

    def test_sell_deletes_what_exists_when_containment_holds_fewer(self):
        self.player.db.inventory = [_T_APPLE, _T_APPLE]
        self.merchant.merchant_stock = {_T_APPLE: 5}
        create_object(
            "typeclasses.objects.Object",
            key=_T_APPLE,
            attributes=[("registry_key", _T_APPLE)],
            location=self.player,
        )
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, _T_APPLE, 2, self.player.pk)
        self.assertEqual(result["quantity"], 2)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(self._contained(_T_APPLE), [])

    def test_bought_item_can_be_dropped(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, _T_APPLE, 1, self.player.pk)
        output = self.call(CmdDrop(), _T_APPLE, caller=self.player)
        self.assertIn(f"你丟下了{_T_APPLE}。", output)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(self._contained(_T_APPLE), [])
        self.assertEqual(len([o for o in self.store.contents if o.key == _T_APPLE]), 1)

    def test_bought_item_can_be_given(self):
        recipient = create_object(PlayerCharacter, key="recipient", location=self.store)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, _T_APPLE, 1, self.player.pk)
        output = self.call(CmdGive(), f"{_T_APPLE} = recipient", caller=self.player)
        self.assertIn(f"你把{_T_APPLE}交給了", output)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(self._contained(_T_APPLE), [])
        self.assertEqual(len([o for o in recipient.contents if o.key == _T_APPLE]), 1)

    @covers_requirement("shop-economy::shop-economy-stays-consistent-with-the-canonical-inventory")
    def test_picked_up_item_is_sellable(self):
        create_object(
            "typeclasses.objects.Object",
            key=_T_SPRAY,
            attributes=[("registry_key", _T_SPRAY)],
            location=self.store,
        )
        self.call(CmdGet(), _T_SPRAY, caller=self.player)
        self.assertEqual(list_items(self.player), [_T_SPRAY])
        self.assertEqual(len(self._contained(_T_SPRAY)), 1)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, _T_SPRAY, 1, self.player.pk)
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(self._contained(_T_SPRAY), [])

    @covers_requirement(
        "item-presentation-metadata::presentation-metadata-does-not-claim-unimplemented-mechanics"
    )
    def test_presentation_swap_leaves_buy_sell_outcomes_unchanged(self):
        """Swapping a registry item's presentation must not change trade results."""
        from world.lore.items import (
            ItemDefinition,
            ItemIconKey,
            ItemKind,
            ItemPresentation,
            ItemRarity,
        )

        registry = live_item_registry()
        original = registry[_T_APPLE]
        altered = ItemDefinition(
            key=_T_APPLE,
            display_name_zh=original.display_name_zh,
            price_table_key=original.price_table_key,
            sellable=original.sellable,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.LEGENDARY,
                summary_zh="旅人充飢的普通餐食。",
            ),
        )  # the row's own identity fields stay untouched; only the look swaps

        def trade_round():
            self.player.db.wallet = 100
            self.player.db.inventory = []
            self.merchant.merchant_stock = _stock()
            with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
                buy_result = buy(
                    self.player, self.merchant_npc, _T_APPLE, 2, self.player.pk
                )
                sell_result = sell(
                    self.player, self.merchant_npc, _T_APPLE, 2, self.player.pk
                )
            return (
                buy_result,
                sell_result,
                list_items(self.player),
                parse_merchant_stock(self.merchant),
                self.player.db.wallet,
            )

        baseline = trade_round()
        registry[_T_APPLE] = altered
        try:
            swapped = trade_round()
        finally:
            registry[_T_APPLE] = original

        self.assertEqual(swapped, baseline)


class PartyShopTradeTests(ShopRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
    """Member-scoped shop trades: the member's bag and the commander's purse.

    Covers shop-party-recipient-seller: a purchase names a recipient and
    debits the unchanged buy price from the party purse (the commander's
    wallet), a sale names a seller and credits the unchanged sell price to
    that purse, only the seller's unequipped copies sell, a forged or absent
    member is refused before pricing, and a failed commit restores the purse,
    both bags, the member's quest log and the merchant stock.

    The three added ``shop-economy`` requirement IDs are indexed only after
    archival synchronization promotes this delta into the main spec, so the
    annotations below name the current canonical requirements the behaviour
    substantively establishes.
    """

    EMPTY_EQUIPMENT = {
        "weapon_main": None,
        "weapon_off": None,
        "armor": None,
        "accessories": [],
    }

    def setUp(self):
        super().setUp()
        self.store = create_object(Room, key="party store")
        self.merchant_npc = create_object(
            NPC, key="t_synth_partystallkeeper", location=self.store
        )
        self.merchant = Merchant.create(
            self.merchant_npc,
            service_id="party-store",
            shop_key=T_SHOP,
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = _stock()
        self.player = create_object(PlayerCharacter, key="party shopper")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.store
        self.player.db.wallet = 1240
        self.companion = self._companion("艾拉")

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.store, home=self.store)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        return npc

    def _open_clock(self, hour=12):
        return WorldClock(hour * 3600)

    def _surface(self, *members):
        return (
            int(self.player.db.wallet or 0),
            {int(member.pk): list(member.db.inventory or []) for member in members},
            dict(parse_merchant_stock(self.merchant)),
        )

    @covers_requirement(
        "shop-economy::buying-and-selling-commit-wallet-inventory-acquisition-progress-and-stock-atomically",
        "shop-economy::shop-economy-stays-consistent-with-the-canonical-inventory",
        "affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths",
    )
    def test_companion_recipient_purchase_debits_the_party_purse(self):
        # Independent arithmetic: the purse starts at 1,240 and the authored
        # offer rule prices this kit row, so three units must leave exactly
        # 1,240 - 3 * buy_copper and fill only the companion's bag.
        stock_before = parse_merchant_stock(self.merchant)[_T_APPLE]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = buy(
                self.player, self.merchant_npc, _T_APPLE, 3, self.companion.pk
            )
        total = 3 * _buy_copper(_T_APPLE)
        self.assertEqual(result["total_copper"], total)
        self.assertEqual(result["wallet"], 1240 - total)
        self.assertEqual(int(self.player.db.wallet), 1240 - total)
        self.assertEqual(list_items(self.companion), [_T_APPLE] * 3)
        self.assertEqual(list_items(self.player), [])
        # The contained mirrors follow the recipient, not the purse owner.
        self.assertEqual(
            [obj.key for obj in self.companion.contents if obj.key == _T_APPLE],
            [_T_APPLE] * 3,
        )
        self.assertEqual(
            parse_merchant_stock(self.merchant)[_T_APPLE], stock_before - 3
        )
        # The commander pays, so the trade affinity stays with the commander.
        self.assertEqual(self.merchant_npc.relations.affinity_for(self.player), 1)
        self.assertFalse(self.merchant_npc.relations.has_record(self.companion))

    def test_forged_or_absent_member_is_refused_before_pricing(self):
        outsider = create_object(NPC, key="路人", location=self.store)
        elsewhere = create_object(Room, key="elsewhere")
        before = self._surface(self.player, self.companion)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            for member_id in (outsider.pk, 999999):
                with self.assertRaises(PartyScopeError) as caught:
                    buy(
                        self.player,
                        self.merchant_npc,
                        _T_APPLE,
                        1,
                        member_id,
                    )
                self.assertEqual(caught.exception.reason, REASON_NOT_PARTY_MEMBER)
            self.companion.location = elsewhere
            with self.assertRaises(PartyScopeError) as caught:
                buy(
                    self.player,
                    self.merchant_npc,
                    _T_APPLE,
                    1,
                    self.companion.pk,
                )
            self.assertEqual(caught.exception.reason, REASON_MEMBER_NOT_PRESENT)
            with self.assertRaises(PartyScopeError) as caught:
                sell(
                    self.player,
                    self.merchant_npc,
                    _T_APPLE,
                    1,
                    outsider.pk,
                )
            self.assertEqual(caught.exception.reason, REASON_NOT_PARTY_MEMBER)
        self.assertEqual(self._surface(self.player, self.companion), before)
        self.assertFalse(self.merchant_npc.relations.has_record(self.player))

    def test_companion_recipient_insufficient_purse_changes_nothing(self):
        self.player.db.wallet = _buy_copper(_T_FANG) - 1
        before = self._surface(self.player, self.companion)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as caught:
                buy(
                    self.player,
                    self.merchant_npc,
                    _T_FANG,
                    1,
                    self.companion.pk,
                )
        self.assertEqual(caught.exception.args[0], TradeReason.INSUFFICIENT_FUNDS)
        self.assertEqual(self._surface(self.player, self.companion), before)

    @covers_requirement(
        "shop-economy::buying-and-selling-commit-wallet-inventory-acquisition-progress-and-stock-atomically"
    )
    def test_acquire_progress_follows_the_recipient(self):
        # Pinned observed behaviour (design "ACQUIRE progress"): the planner
        # advances the recipient's own ACQUIRE objectives, so buying into a
        # companion's bag never advances the commander's matching objective.
        definition = register_quest(
            quest_definition(
                "t_party_shop_acquire",
                stages=(
                    QuestStage(index=0, objective=acquire_objective(_T_APPLE, 3)),
                ),
            )
        )
        commander_record = accept_quest_record(self.player, definition)
        companion_record = accept_quest_record(self.companion, definition)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, _T_APPLE, 2, self.companion.pk)
        companion_rows = {
            record.quest_id: record for record in read_records(self.companion)
        }
        commander_rows = {
            record.quest_id: record for record in read_records(self.player)
        }
        self.assertEqual(
            companion_rows[companion_record.quest_id].stage_progress, 2
        )
        self.assertEqual(commander_rows[commander_record.quest_id].stage_progress, 0)

    def test_fault_injection_restores_purse_both_bags_quest_log_and_stock(self):
        definition = register_quest(
            quest_definition(
                "t_party_shop_acquire_rollback",
                stages=(
                    QuestStage(index=0, objective=acquire_objective(_T_APPLE, 3)),
                ),
            )
        )
        accept_quest_record(self.companion, definition)
        self.companion.db.inventory = [_T_APPLE]
        wallet_before = int(self.player.db.wallet)
        commander_bag = list(self.player.db.inventory or [])
        companion_bag = list(self.companion.db.inventory or [])
        quest_before = attribute_snapshot(self.companion, "quest_log")
        stock_before = dict(parse_merchant_stock(self.merchant))
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with patch(
                "world.rules.economy.materialize_registry_object",
                side_effect=RuntimeError("mirror failure"),
            ):
                with self.assertRaises(RuntimeError):
                    buy(
                        self.player,
                        self.merchant_npc,
                        _T_APPLE,
                        2,
                        self.companion.pk,
                    )
        self.assertEqual(int(self.player.db.wallet), wallet_before)
        self.assertEqual(list(self.player.db.inventory or []), commander_bag)
        self.assertEqual(list(self.companion.db.inventory or []), companion_bag)
        self.assertEqual(
            attribute_snapshot(self.companion, "quest_log"), quest_before
        )
        self.assertEqual(dict(parse_merchant_stock(self.merchant)), stock_before)

    def test_fault_injection_restores_an_auto_settled_companion_wallet(self):
        # An AUTO issuance pays the quest actor's own wallet inside the
        # quest-log delta, so a companion's wallet is a trade surface the
        # snapshot must cover even though the commander owns the purse.
        from world.quests.runtime import accept_quest
        from world.rules.guild_offers import QuestReward
        from world.rules.quest_issuance import (
            QuestIssuance,
            Settlement,
            npc_issuer_key,
            register_quest_issuance,
        )

        definition = register_quest(
            quest_definition(
                "t_party_shop_auto_rollback",
                stages=(
                    QuestStage(index=0, objective=acquire_objective(_T_APPLE, 3)),
                ),
            )
        )
        issuer = npc_issuer_key(content_key="t_party_shop_auto_rollback")
        register_quest_issuance(
            QuestIssuance(
                definition_key=definition.key,
                issuer_key=issuer,
                reward=QuestReward(copper=7, items=(), merit=0),
                settlement=Settlement.AUTO,
            )
        )
        accept_quest(self.companion, definition.key, issuer)
        self.companion.db.wallet = 0
        wallet_before = int(self.player.db.wallet)
        quest_before = attribute_snapshot(self.companion, "quest_log")
        claims_before = attribute_snapshot(self.companion, "guild_reward_claims")
        stock_before = dict(parse_merchant_stock(self.merchant))
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with patch(
                "world.rules.economy.materialize_registry_object",
                side_effect=RuntimeError("mirror failure"),
            ):
                with self.assertRaises(RuntimeError):
                    buy(
                        self.player,
                        self.merchant_npc,
                        _T_APPLE,
                        3,
                        self.companion.pk,
                    )
        self.assertEqual(int(self.player.db.wallet), wallet_before)
        self.assertEqual(int(self.companion.db.wallet or 0), 0)
        self.assertEqual(list(self.companion.db.inventory or []), [])
        self.assertEqual(
            attribute_snapshot(self.companion, "quest_log"), quest_before
        )
        self.assertEqual(
            attribute_snapshot(self.companion, "guild_reward_claims"), claims_before
        )
        self.assertEqual(dict(parse_merchant_stock(self.merchant)), stock_before)

    @covers_requirement(
        "shop-economy::buying-and-selling-commit-wallet-inventory-acquisition-progress-and-stock-atomically",
        "shop-economy::shop-economy-stays-consistent-with-the-canonical-inventory",
        "affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths",
    )
    def test_companion_seller_proceeds_credit_the_party_purse(self):
        self.player.db.wallet = 0
        self.companion.db.inventory = [_T_SPRAY, _T_SPRAY]
        stock_before = parse_merchant_stock(self.merchant)[_T_SPRAY]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(
                self.player, self.merchant_npc, _T_SPRAY, 2, self.companion.pk
            )
        expected = 2 * _sell_copper(_T_SPRAY)
        self.assertEqual(result["total_copper"], expected)
        self.assertEqual(result["wallet"], expected)
        self.assertEqual(int(self.player.db.wallet), expected)
        self.assertEqual(list_items(self.companion), [])
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(
            parse_merchant_stock(self.merchant)[_T_SPRAY], stock_before + 2
        )
        self.assertEqual(self.merchant_npc.relations.affinity_for(self.player), 1)
        self.assertFalse(self.merchant_npc.relations.has_record(self.companion))

    def test_companion_equipped_copy_is_not_sellable(self):
        self.player.db.wallet = 0
        self.companion.db.inventory = [_T_KNIFE]
        self.companion.db.equipment = {
            **self.EMPTY_EQUIPMENT,
            "weapon_main": _T_KNIFE,
        }
        before = self._surface(self.player, self.companion)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as caught:
                sell(
                    self.player,
                    self.merchant_npc,
                    _T_KNIFE,
                    1,
                    self.companion.pk,
                )
        self.assertEqual(caught.exception.args[0], TradeReason.EQUIPPED_ITEM)
        self.assertEqual(self._surface(self.player, self.companion), before)
        self.assertEqual(
            self.companion.db.equipment["weapon_main"], _T_KNIFE
        )

    def test_companion_spare_copy_sells_while_equipped(self):
        self.player.db.wallet = 0
        self.companion.db.inventory = [_T_KNIFE, _T_KNIFE]
        self.companion.db.equipment = {
            **self.EMPTY_EQUIPMENT,
            "weapon_main": _T_KNIFE,
        }
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(
                self.player, self.merchant_npc, _T_KNIFE, 1, self.companion.pk
            )
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(list_items(self.companion), [_T_KNIFE])
        self.assertEqual(
            self.companion.db.equipment["weapon_main"], _T_KNIFE
        )

    def test_companion_seller_stock_cap_refuses(self):
        self.player.db.wallet = 0
        self.companion.db.inventory = [_T_FANG, _T_FANG, _T_FANG]
        before = self._surface(self.player, self.companion)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as caught:
                sell(
                    self.player,
                    self.merchant_npc,
                    _T_FANG,
                    3,
                    self.companion.pk,
                )
        self.assertEqual(caught.exception.args[0], TradeReason.STOCK_OVERFLOW)
        self.assertEqual(self._surface(self.player, self.companion), before)

    @covers_requirement(
        "shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant"
    )
    def test_text_member_trades_match_the_action(self):
        # Text/action parity: the same rule entry settles both transports, so
        # the typed `= <成員>` purchase leaves the same purse delta and the
        # same member bag the `shop.buy` recipient payload produces.
        kahn = self._companion("卡恩")
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            action = buy(self.player, self.merchant_npc, _T_APPLE, 3, kahn.pk)
            output = self.call(
                CmdBuy(), f"{_T_APPLE} 3 = 艾拉", caller=self.player
            )
        self.assertIn("你買了 3 個", output)
        self.assertEqual(
            int(self.player.db.wallet), action["wallet"] - action["total_copper"]
        )
        self.assertEqual(list_items(self.companion), [_T_APPLE] * 3)
        self.assertEqual(list_items(kahn), [_T_APPLE] * 3)

    @covers_requirement(
        "shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant"
    )
    def test_text_member_sale_matches_the_action(self):
        kahn = self._companion("卡恩")
        self.player.db.wallet = 0
        self.companion.db.inventory = [_T_SPRAY]
        kahn.db.inventory = [_T_SPRAY]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            action = sell(self.player, self.merchant_npc, _T_SPRAY, 1, kahn.pk)
            output = self.call(
                CmdSell(), f"{_T_SPRAY} 1 = 艾拉", caller=self.player
            )
        self.assertIn("你賣了 1 個", output)
        self.assertEqual(
            int(self.player.db.wallet), 2 * action["total_copper"]
        )
        self.assertEqual(list_items(self.companion), [])
        self.assertEqual(list_items(kahn), [])

    def test_text_member_token_refusals_match_the_action(self):
        from world.rules.party_scope import PARTY_SCOPE_MESSAGES

        create_object(NPC, key="路人", location=self.store)
        before = self._surface(self.player, self.companion)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            unknown = self.call(
                CmdBuy(), f"{_T_APPLE} 1 = 路人", caller=self.player
            )
            empty = self.call(
                CmdSell(), f"{_T_APPLE} 1 =", caller=self.player
            )
        refusal = PARTY_SCOPE_MESSAGES[REASON_NOT_PARTY_MEMBER]
        self.assertEqual(unknown.strip(), refusal)
        self.assertEqual(empty.strip(), refusal)
        self.assertEqual(self._surface(self.player, self.companion), before)

    def test_text_default_trade_names_the_caller(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            output = self.call(CmdBuy(), f"{_T_APPLE} 1", caller=self.player)
        self.assertIn("你買了 1 個", output)
        self.assertEqual(list_items(self.player), [_T_APPLE])
        self.assertEqual(list_items(self.companion), [])

    def test_text_trades_refuse_possession(self):
        from world.rules.possession import (
            POSSESSED_REFUSAL_MESSAGES,
            REASON_POSSESSED_SHOP,
        )

        # The text client answers a possessed trade exactly like the web
        # adapters: the shared fixed line, before any host or argument work,
        # whatever member the line names.
        self.companion.db.possessed_by = self.player.pk
        refusal = POSSESSED_REFUSAL_MESSAGES[REASON_POSSESSED_SHOP]
        before = self._surface(self.player, self.companion)
        buy_output = self.call(CmdBuy(), f"{_T_APPLE} 1", caller=self.companion)
        sell_output = self.call(
            CmdSell(), f"{_T_APPLE} 1 = 艾拉", caller=self.companion
        )
        self.assertEqual(buy_output.strip(), refusal)
        self.assertEqual(sell_output.strip(), refusal)
        self.assertEqual(self._surface(self.player, self.companion), before)

    def test_shop_aliases_include_the_design_command_table(self):
        self.assertIn("買", CmdBuy.aliases)
        self.assertIn("賣", CmdSell.aliases)


class EquippedRemovalGuardTests(ShopRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
    """Rubber-duck run-2 blocker: removal writers never unhold an equipped key."""

    EMPTY_EQUIPMENT = {
        "weapon_main": None,
        "weapon_off": None,
        "armor": None,
        "accessories": [],
    }

    def setUp(self):
        super().setUp()
        self.store = create_object(Room, key="guard store")
        self.merchant_npc = create_object(NPC, key="t_synth_guardkeeper", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc,
            service_id="guard-store",
            shop_key=T_SHOP,
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {**_stock(), _T_KNIFE: 1}
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.store
        self.player.db.wallet = 0
        self.player.db.inventory = []
        self.player.db.equipment = dict(self.EMPTY_EQUIPMENT)

    def _open_clock(self, hour=12):
        return WorldClock(hour * 3600)

    def _wear(self, *keys):
        self.player.db.inventory = list(keys)
        if keys:
            self.player.db.equipment = {
                **self.EMPTY_EQUIPMENT,
                "weapon_main": keys[0],
            }

    def test_sell_last_equipped_key_is_refused_without_mutation(self):
        self.player.db.inventory = [_T_KNIFE]
        self.player.db.equipment = {**self.EMPTY_EQUIPMENT, "weapon_main": _T_KNIFE}
        stock_before = parse_merchant_stock(self.merchant)[_T_KNIFE]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                sell(self.player, self.merchant_npc, _T_KNIFE, 1, self.player.pk)
        self.assertEqual(ctx.exception.args[0], TradeReason.EQUIPPED_ITEM)
        self.assertEqual(self.player.db.wallet, 0)
        self.assertEqual(list_items(self.player), [_T_KNIFE])
        self.assertEqual(
            self.player.db.equipment["weapon_main"], _T_KNIFE
        )
        self.assertEqual(parse_merchant_stock(self.merchant)[_T_KNIFE], stock_before)

    def test_sell_leaving_one_equipped_copy_is_allowed(self):
        self.player.db.inventory = [_T_KNIFE, _T_KNIFE]
        self.player.db.equipment = {**self.EMPTY_EQUIPMENT, "weapon_main": _T_KNIFE}
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, _T_KNIFE, 1, self.player.pk)
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(list_items(self.player), [_T_KNIFE])

    def test_unequipped_item_sells_normally(self):
        self.player.db.inventory = [_T_KNIFE]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, _T_KNIFE, 1, self.player.pk)
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(list_items(self.player), [])

    def test_planner_raises_equipped_removal_error(self):
        from world.rules.equipment import (
            EquippedRemovalError,
            equipped_removal_conflict,
            plan_inventory_delta,
        )

        self.player.db.inventory = [_T_KNIFE]
        self.player.db.equipment = {**self.EMPTY_EQUIPMENT, "weapon_main": _T_KNIFE}
        self.assertEqual(
            equipped_removal_conflict(self.player, (_T_KNIFE,)), _T_KNIFE
        )
        self.assertIsNone(equipped_removal_conflict(self.player, (_T_APPLE,)))
        with self.assertRaises(EquippedRemovalError):
            plan_inventory_delta(self.player, removals=(_T_KNIFE,))
        # Malformed storage protects every removal of a registry equipment key.
        self.player.db.equipment = "corrupt"
        self.assertEqual(
            equipped_removal_conflict(self.player, (_T_KNIFE,)), _T_KNIFE
        )
        self.assertIsNone(equipped_removal_conflict(self.player, (_T_APPLE,)))

    def test_drop_and_give_refuse_the_last_equipped_key(self):
        self.char2.location = self.store
        self.player.db.inventory = [_T_KNIFE]
        self.player.db.equipment = {**self.EMPTY_EQUIPMENT, "weapon_main": _T_KNIFE}
        self.call(
            CmdDrop(),
            _T_KNIFE,
            "你無法丟下已裝備的物品。",
            caller=self.player,
        )
        self.assertEqual(list_items(self.player), [_T_KNIFE])
        self.call(
            CmdGive(),
            f"{_T_KNIFE} = {self.char2.key}",
            "你無法給予已裝備的物品。",
            caller=self.player,
        )
        self.assertEqual(list_items(self.player), [_T_KNIFE])

class MerchantStockParsingTests(ShopRegistryIsolation, EvenniaTestCase):
    @covers_requirement("shop-economy::merchant-stock-is-finite-persistent-repeated-item-quantity-state")
    def test_malformed_stock_fails_closed(self):
        from typeclasses.components import Merchant as MerchantComponent

        npc = create_object(NPC, key="bad merchant")
        merchant = MerchantComponent.create(npc, service_id="m", shop_key=T_SHOP)
        npc.components.add(merchant)
        for bad in ({_T_APPLE: -1}, {_T_APPLE: 1.5}, {"no_such_item": 1}):
            merchant.merchant_stock = bad
            with self.subTest(stock=bad):
                with self.assertRaises(TradeError) as ctx:
                    parse_merchant_stock(merchant)
                self.assertEqual(ctx.exception.args[0], TradeReason.MALFORMED_STOCK)


def _shop_row(shop_key: str) -> dict:
    return {
        "shop_key": shop_key,
        "open_hour": 8,
        "close_hour": 20,
        "restock_hour": 6,
    }


def _mossgate_offers() -> dict:
    """Offer rules for the kit assortment."""
    return {
        "t_mossgate_goods": {
            item_key: synth_offer_rule(item_key)
            for item_key in (_T_SPRAY, _T_FANG, _T_APPLE)
        },
    }


_MOSSGATE_SCALES = {"t_mossgate": 100}


def _place_row(shop_key: str) -> "PlaceDefinition":
    """A place row authoring ``shop_key`` (kit store template)."""
    base = SYNTH_PLACES["t_mossgate_store"]
    return replace(
        base,
        key=f"t_place_for_{shop_key}",
        authored_kwargs=(("shop_key", shop_key),),
        assortment_keys=("t_mossgate_goods",),
    )


class ShopCompletenessDefectTests(EvenniaTestCase):
    """The shops-completeness check is keyed on shop identity (design §1.1).

    A synthetic two-shop registry where the second shop has no rule row: the
    shipped defect keyed the accounting on a constant component type, so the
    closing check collapsed to one entry and silently accepted the second
    shop. Every row here is kit or file-local fixture data.
    """

    SECOND_SHOP = "t_second_stall"

    def setUp(self):
        second_shop = ShopDefinition(
            key=self.SECOND_SHOP,
            host_name="苔徑二號攤",
            host_title="苔徑市集合成二號攤主",
            assortment_keys=("t_mossgate_goods",),
        )
        open_synthetic_scope(
            self,
            "items",
            "prices",
            "places",
            "shops",
            extra={
                "shops": {self.SECOND_SHOP: second_shop},
                "places": {_place_row(self.SECOND_SHOP).key: _place_row(self.SECOND_SHOP)},
            },
        )
        super().setUp()

    @covers_requirement(
        "commerce-assortments::every-shop-s-numeric-rules-are-accounted-for-at-load"
    )
    def test_second_shop_with_no_rules_is_rejected(self):
        with self.assertRaises(GuildConfigError) as caught:
            validate_shop_configs(
                [_shop_row(T_SHOP)],
                _mossgate_offers(),
                _MOSSGATE_SCALES,
            )
        message = str(caught.exception)
        self.assertIn("missing rules", message)
        self.assertIn(self.SECOND_SHOP, message)

    @covers_requirement(
        "commerce-assortments::every-shop-s-numeric-rules-are-accounted-for-at-load"
    )
    def test_rules_naming_a_shop_without_identity_are_rejected(self):
        with self.assertRaises(GuildConfigError) as caught:
            validate_shop_configs(
                [_shop_row("t_no_such_shop")],
                _mossgate_offers(),
                _MOSSGATE_SCALES,
            )
        self.assertIn("t_no_such_shop", str(caught.exception))

    def test_both_shops_with_rules_resolve_the_same_goods(self):
        configs = validate_shop_configs(
            [_shop_row(T_SHOP), _shop_row(self.SECOND_SHOP)],
            _mossgate_offers(),
            _MOSSGATE_SCALES,
        )
        expected = {_T_SPRAY, _T_FANG, _T_APPLE}
        self.assertEqual(
            {offer.item_key for offer in configs[T_SHOP].offers},
            expected,
        )
        self.assertEqual(
            {offer.item_key for offer in configs[self.SECOND_SHOP].offers},
            expected,
        )


class ShopAssortmentResolutionTests(EvenniaTestCase):
    """Assortment-referencing rejections over file-local fixture registries.

    Each test opens its own scope so the two-or-more shops are exactly the
    ones the scenario needs; the completeness accounting stays satisfied.
    """

    OVERLAP_ASSORTMENT = "t_overlap_goods"

    @covers_requirement(
        "commerce-assortments::a-shop-s-offered-goods-are-derived-from-the-assortments-it-references"
    )
    def test_shop_referencing_unknown_assortment_is_rejected(self):
        shop = ShopDefinition(
            key="t_unknown_ref_stall",
            host_name="苔徑迷路攤",
            host_title="苔徑市集合成迷路攤主",
            assortment_keys=("t_no_such_assortment",),
        )
        open_synthetic_scope(
            self,
            "items",
            "prices",
            "places",
            "shops",
            extra={"shops": {shop.key: shop}},
        )
        with self.assertRaises(GuildConfigError) as caught:
            validate_shop_configs(
                [_shop_row(shop.key)],
                _mossgate_offers(),
                _MOSSGATE_SCALES,
            )
        message = str(caught.exception)
        self.assertIn(shop.key, message)
        self.assertIn("t_no_such_assortment", message)

    @covers_requirement(
        "commerce-assortments::a-shop-s-offered-goods-are-derived-from-the-assortments-it-references"
    )
    def test_one_shop_overlapping_its_own_assortments_is_rejected(self):
        overlap = AssortmentDefinition(self.OVERLAP_ASSORTMENT, "苔徑重疊貨", (_T_APPLE,))
        shop = ShopDefinition(
            key="t_overlap_stall",
            host_name="苔徑疊櫃攤",
            host_title="苔徑市集合成疊櫃攤主",
            assortment_keys=("t_mossgate_goods", self.OVERLAP_ASSORTMENT),
        )
        open_synthetic_scope(
            self,
            "items",
            "prices",
            "places",
            "shops",
            extra={
                "assortments": {self.OVERLAP_ASSORTMENT: overlap},
                "shops": {shop.key: shop},
                "places": {_place_row(shop.key).key: _place_row(shop.key)},
            },
        )
        floor, _ceiling = price_band(_T_APPLE)
        offers = _mossgate_offers()
        offers[self.OVERLAP_ASSORTMENT] = {
            _T_APPLE: replace(
                synth_offer_rule(_T_APPLE, max_stock=7),
                buy_copper=floor + 7,
            ),
        }
        with self.assertRaises(GuildConfigError) as caught:
            validate_shop_configs([_shop_row(shop.key)], offers, _MOSSGATE_SCALES)
        message = str(caught.exception)
        self.assertIn(shop.key, message)
        self.assertIn(_T_APPLE, message)
        self.assertIn("t_mossgate_goods", message)
        self.assertIn(self.OVERLAP_ASSORTMENT, message)

    @covers_requirement(
        "commerce-assortments::a-shop-s-offered-goods-are-derived-from-the-assortments-it-references"
    )
    def test_two_shops_sharing_a_key_resolve_it_at_their_own_prices(self):
        # One good sold in two places at two prices is the model working,
        # not a collision: the overlap rejection is scoped to a single shop.
        overlap = AssortmentDefinition(self.OVERLAP_ASSORTMENT, "苔徑重疊貨", (_T_APPLE,))
        shop = ShopDefinition(
            key="t_shared_apple_stall",
            host_name="苔徑蘋果攤",
            host_title="苔徑市集合成蘋果攤主",
            assortment_keys=(self.OVERLAP_ASSORTMENT,),
        )
        open_synthetic_scope(
            self,
            "items",
            "prices",
            "places",
            "shops",
            extra={
                "assortments": {self.OVERLAP_ASSORTMENT: overlap},
                "shops": {shop.key: shop},
                "places": {_place_row(shop.key).key: _place_row(shop.key)},
            },
        )
        floor, _ceiling = price_band(_T_APPLE)
        offers = _mossgate_offers()
        offers[self.OVERLAP_ASSORTMENT] = {
            _T_APPLE: replace(
                synth_offer_rule(_T_APPLE, max_stock=7),
                buy_copper=floor + 7,
            ),
        }
        configs = validate_shop_configs(
            [_shop_row(T_SHOP), _shop_row(shop.key)],
            offers,
            _MOSSGATE_SCALES,
        )
        mossgate_apple = next(
            offer for offer in configs[T_SHOP].offers if offer.item_key == _T_APPLE
        )
        shared_apple = next(
            offer for offer in configs[shop.key].offers if offer.item_key == _T_APPLE
        )
        self.assertEqual(mossgate_apple.buy_copper, floor + 2)
        self.assertEqual(shared_apple.buy_copper, floor + 7)


if __name__ == "__main__":
    import unittest

    unittest.main()
