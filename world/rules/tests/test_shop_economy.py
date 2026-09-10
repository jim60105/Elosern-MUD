"""Atomic shop trade tests (tasks 9.1-9.5).

Every trade rides kit rows: one synthetic shop config over three kit items
(scoped item/price/shop registries), with the offer rules authored here so
each assertion names its own numbers.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase

from commands.localized import CmdDrop, CmdGet, CmdGive
from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
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
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    live_item_registry,
    price_band,
    synth_catalog,
    synth_offer_rule,
    synth_shop_config,
)
from world.skills.equipment import list_items
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_SHOPS

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
            result = buy(self.player, self.merchant_npc, _T_APPLE, 2)
        self.assertEqual(result["total_copper"], _buy_copper(_T_APPLE) * 2)
        self.assertEqual(result["wallet"], 100 - _buy_copper(_T_APPLE) * 2)
        self.assertEqual(list_items(self.player), [_T_APPLE, _T_APPLE])
        stock = parse_merchant_stock(self.merchant)
        self.assertEqual(stock[_T_APPLE], 18)
        self.assertEqual(self.merchant_npc.relations.affinity_for(self.player), 1)

    def test_insufficient_funds_changes_nothing(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, _T_FANG, 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.INSUFFICIENT_FUNDS)
        self.assertEqual(self.player.db.wallet, 100)
        self.assertEqual(list_items(self.player), [])
        self.assertGreater(_buy_copper(_T_FANG), 100)
        self.assertEqual(parse_merchant_stock(self.merchant)[_T_FANG], 1)
        self.assertFalse(self.merchant_npc.relations.has_record(self.player))

    def test_insufficient_stock_changes_nothing(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, _T_SPRAY, 4)
        self.assertEqual(ctx.exception.args[0], TradeReason.INSUFFICIENT_STOCK)

    def test_sale_cannot_overflow_merchant_stock(self):
        self.player.db.wallet = 0
        self.player.db.inventory = [_T_FANG, _T_FANG, _T_FANG]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                sell(self.player, self.merchant_npc, _T_FANG, 3)
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
            result = sell(self.player, self.merchant_npc, _T_SPRAY, 2)
        self.assertEqual(result["total_copper"], _sell_copper(_T_SPRAY) * 2)
        self.assertEqual(self.player.db.wallet, _sell_copper(_T_SPRAY) * 2)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(parse_merchant_stock(self.merchant)[_T_SPRAY], 5)
        self.assertEqual(self.merchant_npc.relations.affinity_for(self.player), 1)

    @covers_requirement("shop-economy::item-and-shop-identities-are-immutable-while-numeric-trade-rules-are-yaml-and-lore-constrained")
    def test_unknown_or_unsellable_item_rejected(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError):
                buy(self.player, self.merchant_npc, "no_such_item", 1)
        with self.assertRaises(TradeError) as ctx:
            sell(self.player, self.merchant_npc, "no_such_item", 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.UNKNOWN_ITEM)
        # The kit pass is a genuinely unsellable registry item; the sellable
        # gate precedes merchant and shop-open resolution.
        self.player.db.inventory = [_T_PASS]
        with self.assertRaises(TradeError) as ctx:
            sell(self.player, self.merchant_npc, _T_PASS, 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.UNSELLABLE)
        self.assertEqual(self.player.db.inventory, [_T_PASS])

    def test_closed_shop_rejects_trade(self):
        with patch("world.rules.economy.get_world_clock", return_value=WorldClock(3 * 3600)):
            self.assertFalse(shop_is_open(T_SHOP))
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, _T_APPLE, 1)
            self.assertEqual(ctx.exception.args[0], TradeReason.CLOSED)

    def test_bad_quantity_rejected(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            for bad in (0, -1, 1.5, True):
                with self.subTest(quantity=bad):
                    with self.assertRaises(TradeError) as ctx:
                        buy(self.player, self.merchant_npc, _T_APPLE, bad)
                    self.assertEqual(ctx.exception.args[0], TradeReason.BAD_QUANTITY)

    def test_remote_merchant_rejected(self):
        other = create_object(Room, key="other")
        self.player.location = other
        with self.assertRaises(TradeError) as ctx:
            buy(self.player, self.merchant_npc, _T_APPLE, 1)
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
            buy(self.player, self.merchant_npc, _T_APPLE, 1)
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
            result = buy(self.player, self.merchant_npc, _T_APPLE, 1)
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
            result = buy(self.player, self.merchant_npc, _T_APPLE, 1)
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
                buy(self.player, fake, _T_APPLE, 1)
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
                    buy(self.player, self.merchant_npc, _T_APPLE, 2)
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
            buy(self.player, self.merchant_npc, _T_APPLE, 1)
        self.assertNotIsInstance(self.player.db.wallet, float)
        self.assertEqual(self.player.db.wallet, 100 - _buy_copper(_T_APPLE))

    def _contained(self, item_key):
        return [obj for obj in self.player.contents if obj.key == item_key]

    @covers_requirement("shop-economy::shop-economy-stays-consistent-with-the-canonical-inventory")
    @covers_requirement("equipment-inventory::the-key-list-is-the-single-canonical-inventory-record-for-registry-items")
    def test_buy_materializes_a_contained_object_per_item(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, _T_APPLE, 2)
        self.assertEqual(len(self._contained(_T_APPLE)), 2)
        self.assertTrue(
            all(obj.db.registry_key == _T_APPLE for obj in self._contained(_T_APPLE))
        )
        self.assertEqual(list_items(self.player), [_T_APPLE, _T_APPLE])

    @covers_requirement("shop-economy::shop-economy-stays-consistent-with-the-canonical-inventory")
    def test_sell_removes_the_contained_objects(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, _T_APPLE, 2)
            sell(self.player, self.merchant_npc, _T_APPLE, 1)
        self.assertEqual(len(self._contained(_T_APPLE)), 1)
        self.assertEqual(list_items(self.player), [_T_APPLE])
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            sell(self.player, self.merchant_npc, _T_APPLE, 1)
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
            result = sell(self.player, self.merchant_npc, _T_APPLE, 2)
        self.assertEqual(result["quantity"], 2)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(self._contained(_T_APPLE), [])

    def test_bought_item_can_be_dropped(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, _T_APPLE, 1)
        output = self.call(CmdDrop(), _T_APPLE, caller=self.player)
        self.assertIn(f"你丟下了{_T_APPLE}。", output)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(self._contained(_T_APPLE), [])
        self.assertEqual(len([o for o in self.store.contents if o.key == _T_APPLE]), 1)

    def test_bought_item_can_be_given(self):
        recipient = create_object(PlayerCharacter, key="recipient", location=self.store)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, _T_APPLE, 1)
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
            result = sell(self.player, self.merchant_npc, _T_SPRAY, 1)
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
                buy_result = buy(self.player, self.merchant_npc, _T_APPLE, 2)
                sell_result = sell(self.player, self.merchant_npc, _T_APPLE, 2)
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
                sell(self.player, self.merchant_npc, _T_KNIFE, 1)
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
            result = sell(self.player, self.merchant_npc, _T_KNIFE, 1)
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(list_items(self.player), [_T_KNIFE])

    def test_unequipped_item_sells_normally(self):
        self.player.db.inventory = [_T_KNIFE]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, _T_KNIFE, 1)
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


if __name__ == "__main__":
    import unittest

    unittest.main()
