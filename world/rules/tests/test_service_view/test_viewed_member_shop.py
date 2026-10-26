"""Slice of ``test_service_view``: the v7 shop rows for the viewed party member.

The shop rows describe one viewed member (services-shop-structured-rows): each
stock row carries that member's held count and server equipment delta, the
sellable rows list that member's unequipped copies, and buy/sell enablement
names that member with the party purse (the commander's wallet). The
descriptors mirror ``economy.buy``/``economy.sell``, so a parity check runs the
real trade at every advertised maximum.

Data-independent: every item, price and equipment magnitude is authored by
this file.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.components import GuildStaff, Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.party_view_selection import PartyViewSelection
from web.webclient.presentation.registry import build_production_registry
from world.lore.items import EquipmentModifierKey, EquipmentSlot
from world.rules.clock import get_world_clock
from world.rules.economy import TradeError, TradeReason, buy, sell
from world.rules.equipment_effects import EquipmentEffectRule
from world.rules.guild_config import ItemOfferRule
from world.rules.party import join_party, leave_party
from world.rules.possession import enter_possession
from world.rules.service_view import build_services_view
from world.rules.tests._combat_session_helpers import (
    _player,
    _race_key,
    open_synthetic_scope,
)
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
    synth_shop_config,
    synthetic_branch_key,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.quests.tests._fixtures import register_catalog_once
from world.tests.synthetic_data import make_item

# The shipped affinity rulebook cross-references one catalog quest by key, and
# a real trade applies merchant affinity, so the catalog definitions must be
# present in-process (registered at import, before any synthetic scope).
register_catalog_once()

_SHOP = "t_viewed_shop"
_SWORD = make_item(
    "t_viewed_sword",
    display_name_zh="測試鋼劍",
    sellable=True,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.PLAIN_SWORD,
)
_STAFF = make_item(
    "t_viewed_staff",
    display_name_zh="測試法杖",
    sellable=True,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.APPRENTICE_FOCUS_STAFF,
)
_WARHAMMER = make_item(
    "t_viewed_warhammer",
    display_name_zh="測試戰鎚",
    sellable=True,
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=EquipmentModifierKey.BEASTFOLK_WARHAMMER,
)
_CHARMS = tuple(
    make_item(
        f"t_viewed_charm_{index}",
        display_name_zh=f"測試飾品{index}",
        sellable=True,
        equipment_slot=EquipmentSlot.ACCESSORY,
        modifier_key=EquipmentModifierKey.SILVER_HAIRPIN,
    )
    for index in range(6)
)
_TONIC = make_item("t_viewed_tonic", display_name_zh="測試藥水", sellable=True)
_UNKNOWN = "t_viewed_unregistered_relic"

_ITEMS = {row.key: row for row in (_SWORD, _STAFF, _WARHAMMER, *_CHARMS, _TONIC)}

# Test-authored magnitudes: staff +0 -> sword +6; warhammer +10 -> sword -4.
_EFFECT_RULES = {
    EquipmentModifierKey.PLAIN_SWORD: EquipmentEffectRule(
        adjustments={"atk_phys": 6}, gauge_caps={}, immune=(), attached_buffs=(), exposure_bias=0
    ),
    EquipmentModifierKey.APPRENTICE_FOCUS_STAFF: EquipmentEffectRule(
        adjustments={}, gauge_caps={}, immune=(), attached_buffs=(), exposure_bias=0
    ),
    EquipmentModifierKey.BEASTFOLK_WARHAMMER: EquipmentEffectRule(
        adjustments={"atk_phys": 10}, gauge_caps={}, immune=(), attached_buffs=(), exposure_bias=0
    ),
    EquipmentModifierKey.SILVER_HAIRPIN: EquipmentEffectRule(
        adjustments={"defense": 2}, gauge_caps={}, immune=(), attached_buffs=(), exposure_bias=0
    ),
}

_EMPTY = {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []}


def _offer(item_key, buy_copper, sell_copper, max_stock):
    return ItemOfferRule(
        item_key=item_key,
        buy_copper=buy_copper,
        sell_copper=sell_copper,
        max_stock=max_stock,
        initial_stock=max_stock,
        restock_quantity=1,
    )


class ViewedMemberShopTests(BattlefieldIsolation, EvenniaTest):
    """A commander, one present companion, and a co-located merchant."""

    def setUp(self):
        open_synthetic_scope(self, "items", extra={"items": dict(_ITEMS)})
        effects = patch.dict(
            "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES", _EFFECT_RULES
        )
        effects.start()
        self.addCleanup(effects.stop)
        super().setUp()
        offers = (
            _offer(_SWORD.key, 20, 10, 5),
            _offer(_TONIC.key, 8, 4, 10),
            _offer(_CHARMS[5].key, 30, 15, 2),
            _offer(_STAFF.key, 14, 7, 3),
            _offer(_UNKNOWN, 9, 4, 4),
        )
        install_synthetic_catalog(
            self,
            synth_catalog(
                shop_configs={
                    _SHOP: synth_shop_config(_SHOP, (), offer_rules=offers)
                }
            ),
        )
        get_world_clock()._persist(12 * 3600)
        self.room = create_object(Room, key="viewed shop room")
        self.far_room = create_object(Room, key="viewed shop far room")
        self.keeper = create_object(NPC, key="viewed shop keeper", location=self.room)
        merchant = Merchant.create(self.keeper, service_id="viewed_store", shop_key=_SHOP)
        # A serving host declares its authored availability binding: the gate
        # fails closed on a missing one.
        merchant.service_binding = "person"
        self.keeper.components.add(merchant)
        merchant.merchant_stock = {
            _SWORD.key: 3,
            _TONIC.key: 10,
            _CHARMS[5].key: 1,
            _STAFF.key: 3,
        }
        self.merchant = merchant
        self.commander = _player("viewed shop commander")
        self.commander.location = self.room
        self.commander.db.wallet = 1000
        self.commander.db.inventory = []
        self.commander.db.equipment = dict(_EMPTY)
        self.aila = create_object(NPC, key="艾拉", location=self.room, home=self.room)
        self.aila.race = _race_key()
        self.aila.apply_race_baseline()
        join_party(self.aila, self.commander)
        self.aila.db.inventory = []
        self.aila.db.equipment = dict(_EMPTY)
        self.aila.db.wallet = 999999

    def _shop(self, viewed=None):
        return build_services_view(self.commander, viewed=viewed).shop

    def _enter_possession(self):
        self.commander.account = self.account
        self.account.characters.add(self.commander)
        self.session.puppet = self.commander
        self.commander.sessions.add(self.session)
        enter_possession(self.commander, self.aila)

    def _stock(self, shop, item_key):
        return next(row for row in shop.stock if row.item_key == item_key)

    def _sellable(self, shop):
        return {row.item_key: row for row in shop.sellable}

    def _changes(self, delta):
        return [(change.key, change.label, change.amount) for change in delta.changes]

    @covers_requirement(
        "webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory"
    )
    def test_consumable_row_reports_presentation_and_viewed_held_with_null_delta(self):
        self.aila.db.inventory = [_TONIC.key, _TONIC.key]
        shop = self._shop(self.aila)
        self.assertEqual(shop.member_id, int(self.aila.pk))
        tonic = self._stock(shop, _TONIC.key)
        self.assertEqual(tonic.presentation, _TONIC.presentation)
        self.assertEqual(tonic.viewed.held, 2)
        self.assertIsNone(tonic.viewed.delta)
        # The commander holds none: the facts are the viewed member's only.
        self.assertEqual(self._stock(self._shop(), _TONIC.key).viewed.held, 0)

    @covers_requirement(
        "webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory"
    )
    def test_equipment_row_carries_the_viewed_members_server_delta(self):
        self.aila.db.inventory = [_STAFF.key]
        self.aila.db.equipment = {**_EMPTY, "weapon_main": _STAFF.key}
        self.commander.db.inventory = [_WARHAMMER.key]
        self.commander.db.equipment = {**_EMPTY, "weapon_main": _WARHAMMER.key}
        aila = self._stock(self._shop(self.aila), _SWORD.key)
        self.assertTrue(aila.viewed.delta.equippable)
        self.assertEqual(self._changes(aila.viewed.delta), [("atk_phys", "攻擊", 6)])
        self.assertEqual(aila.viewed.held, 0)
        commander = self._stock(self._shop(self.commander), _SWORD.key)
        self.assertEqual(self._changes(commander.viewed.delta), [("atk_phys", "攻擊", -4)])
        # A worn stock item is no change at all.
        staff = self._stock(self._shop(self.aila), _STAFF.key)
        self.assertTrue(staff.viewed.delta.equippable)
        self.assertEqual(staff.viewed.delta.changes, ())
        self.assertEqual(staff.viewed.held, 1)

    @covers_requirement(
        "webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory"
    )
    def test_full_accessory_set_reports_not_equippable_while_buy_stays_enabled(self):
        worn = [charm.key for charm in _CHARMS[:5]]
        self.aila.db.inventory = list(worn)
        self.aila.db.equipment = {**_EMPTY, "accessories": list(worn)}
        row = self._stock(self._shop(self.aila), _CHARMS[5].key)
        self.assertFalse(row.viewed.delta.equippable)
        self.assertEqual(row.viewed.delta.reason, "accessory_slots_full")
        self.assertTrue(row.buy.enabled)

    def test_unregistered_offer_key_is_inspect_only(self):
        row = self._stock(self._shop(self.aila), _UNKNOWN)
        self.assertIsNone(row.presentation)
        self.assertIsNone(row.viewed.delta)
        self.assertEqual(row.display_name, _UNKNOWN)
        self.assertFalse(row.buy.enabled)
        self.assertEqual(row.buy.reason_code, "unknown_item")

    @covers_requirement(
        "webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory"
    )
    def test_sellable_rows_list_only_the_viewed_members_unequipped_copies(self):
        self.aila.db.inventory = [_SWORD.key, _SWORD.key, _STAFF.key, _TONIC.key]
        self.aila.db.equipment = {**_EMPTY, "weapon_main": _STAFF.key}
        self.commander.db.inventory = [_TONIC.key, _TONIC.key, _TONIC.key]
        sellable = self._sellable(self._shop(self.aila))
        # Two swords, none worn; the only staff is worn so it is absent.
        self.assertEqual(sellable[_SWORD.key].held, 2)
        self.assertEqual(sellable[_SWORD.key].sell_copper, 10)
        self.assertEqual(sellable[_SWORD.key].presentation, _SWORD.presentation)
        self.assertNotIn(_STAFF.key, sellable)
        self.assertEqual(sellable[_TONIC.key].held, 1)
        # A worn duplicate leaves the unequipped count only.
        self.aila.db.equipment = {**_EMPTY, "weapon_main": _SWORD.key}
        sellable = self._sellable(self._shop(self.aila))
        self.assertEqual(sellable[_SWORD.key].held, 1)
        self.assertEqual(sellable[_SWORD.key].sell.quantity_max, 1)
        self.assertIn(_STAFF.key, sellable)

    @covers_requirement(
        "webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory"
    )
    def test_buy_enablement_reads_the_party_purse_not_the_member_wallet(self):
        self.commander.db.wallet = 19
        row = self._stock(self._shop(self.aila), _SWORD.key)
        self.assertFalse(row.buy.enabled)
        self.assertEqual(row.buy.reason_code, "insufficient_funds")
        # 45 copper buys two swords at 20 though three are stocked.
        self.commander.db.wallet = 45
        row = self._stock(self._shop(self.aila), _SWORD.key)
        self.assertTrue(row.buy.enabled)
        self.assertEqual((row.buy.quantity_min, row.buy.quantity_max), (1, 2))

    @covers_requirement(
        "webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory"
    )
    def test_absent_member_keeps_facts_and_disables_trades_with_the_scope_reason(self):
        self.aila.db.inventory = [_TONIC.key]
        self.aila.location = self.far_room
        shop = self._shop(self.aila)
        self.assertEqual(shop.member_id, int(self.aila.pk))
        tonic = self._stock(shop, _TONIC.key)
        self.assertEqual(tonic.viewed.held, 1)
        self.assertFalse(tonic.buy.enabled)
        self.assertEqual(tonic.buy.reason_code, "member_not_present")
        self.assertEqual(tonic.buy.reason_message, "對方不在這裡。")
        self.assertEqual(self._sellable(shop)[_TONIC.key].sell.reason_code, "member_not_present")

    def test_closed_shop_reason_precedes_the_member_scope(self):
        self.aila.location = self.far_room
        get_world_clock()._persist(3 * 3600)
        shop = self._shop(self.aila)
        self.assertFalse(shop.open)
        self.assertEqual({row.buy.reason_code for row in shop.stock}, {"closed"})

    def test_malformed_viewed_equipment_degrades_only_the_shop(self):
        self.aila.db.equipment = {"weapon_main": 7}
        view = build_services_view(self.commander, viewed=self.aila)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "malformed_equipment")
        self.assertIsNotNone(view.player)

    @covers_requirement(
        "webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory"
    )
    def test_enabled_descriptors_match_the_trade_rule_at_their_advertised_maximum(self):
        # Parity: every advertised maximum succeeds through the real rule and
        # one more is refused, so the local mirror never over-grants.
        self.commander.db.wallet = 45
        row = self._stock(self._shop(self.aila), _SWORD.key)
        with self.assertRaises(TradeError) as refused:
            buy(self.commander, self.keeper, _SWORD.key, row.buy.quantity_max + 1, self.aila.pk)
        self.assertIs(refused.exception.args[0], TradeReason.INSUFFICIENT_FUNDS)
        result = buy(self.commander, self.keeper, _SWORD.key, row.buy.quantity_max, self.aila.pk)
        self.assertEqual(result["wallet"], 5)
        self.assertEqual(self.aila.db.inventory.count(_SWORD.key), 2)

        self.aila.db.equipment = {**_EMPTY, "weapon_main": _SWORD.key}
        sold = self._sellable(self._shop(self.aila))[_SWORD.key]
        self.assertEqual(sold.sell.quantity_max, 1)
        with self.assertRaises(TradeError) as equipped:
            sell(self.commander, self.keeper, _SWORD.key, 2, self.aila.pk)
        self.assertIs(equipped.exception.args[0], TradeReason.EQUIPPED_ITEM)
        sell(self.commander, self.keeper, _SWORD.key, sold.sell.quantity_max, self.aila.pk)
        self.assertEqual(self.commander.db.wallet, 15)

    def test_full_merchant_cap_disables_sell_like_the_trade_rule(self):
        self.aila.db.inventory = [_STAFF.key]
        row = self._sellable(self._shop(self.aila))[_STAFF.key]
        self.assertFalse(row.sell.enabled)
        self.assertEqual(row.sell.reason_code, "stock_overflow")
        with self.assertRaises(TradeError) as refused:
            sell(self.commander, self.keeper, _STAFF.key, 1, self.aila.pk)
        self.assertIs(refused.exception.args[0], TradeReason.STOCK_OVERFLOW)

    def _render(self, selection=None, actor=None):
        context = PresentationContext(
            actor=actor or self.commander, protocol_version=1, party_view=selection
        )
        return build_production_registry().render("services", context)

    @covers_requirement(
        "webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel"
    )
    def test_presenter_follows_the_viewed_member_and_falls_back_to_the_commander(self):
        self.aila.db.inventory = [_TONIC.key]
        selection = PartyViewSelection(
            int(self.commander.pk), int(self.aila.pk), "shop"
        )
        payload = self._render(selection)
        self.assertEqual(payload["schema_version"], 7)
        self.assertNotIn("inventory", payload)
        self.assertNotIn("inventory_total", payload["pagination"])
        shop = payload["shop"]
        self.assertEqual(shop["member_id"], int(self.aila.pk))
        tonic = next(row for row in shop["stock"] if row["item_key"] == _TONIC.key)
        self.assertEqual(tonic["viewed"], {"held": 1, "delta": None})
        self.assertNotIn("sell_copper", tonic)
        self.assertNotIn("buy_copper", shop["sellable"][0])
        # A member who left the party no longer chooses the facts.
        leave_party(self.aila, self.commander, "dismissed")
        self.assertEqual(self._render(selection)["shop"]["member_id"], int(self.commander.pk))
        self.assertEqual(self._render()["shop"]["member_id"], int(self.commander.pk))

    def test_unexpected_delta_failure_degrades_only_the_shop(self):
        with patch(
            "world.rules.service_view.equipment_delta", side_effect=RuntimeError("boom")
        ):
            view = build_services_view(self.commander, viewed=self.aila)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "equipment_delta_unavailable")
        self.assertEqual(view.player.wallet, 1000)

    @covers_requirement(
        "webclient-service-menus::service-presentation-resolves-hosts-per-service-class-and-a-stable-player-summary"
    )
    def test_possessed_actor_keeps_the_owner_summary_and_merchant_shop(self):
        guild = create_object(NPC, key="公會職員", location=self.room)
        guild.components.add(
            GuildStaff.create(
                guild, service_id="staff", branch_key=synthetic_branch_key()
            )
        )
        self.aila.db.inventory = [_TONIC.key, _TONIC.key]
        self._enter_possession()
        self.assertEqual(self.session.puppet, self.aila)
        view = build_services_view(self.aila, viewed=self.aila)
        # The player summary belongs to the owner, not the puppet.
        self.assertEqual(view.player.wallet, 1000)
        self.assertEqual(view.player.guild_rank, None)
        # Guild and rank are omitted without a failure reason.
        self.assertIsNone(view.guild)
        self.assertIsNone(view.guild_unavailable_reason)
        self.assertEqual(view.host.display_name, "viewed shop keeper")
        self.assertIsNotNone(view.shop)
        self.assertEqual(view.shop.member_id, int(self.aila.pk))
        tonic = self._stock(view.shop, _TONIC.key)
        self.assertEqual(tonic.viewed.held, 2)
        self.assertEqual(view.pagination.board_total, 0)
        self.assertEqual(view.pagination.quest_total, 0)
        self.assertEqual(view.pagination.stock_total, len(view.shop.stock))
        self.assertEqual(view.pagination.sellable_total, len(view.shop.sellable))

    @covers_requirement(
        "webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel"
    )
    def test_possessed_malformed_merchant_degrades_only_the_shop(self):
        self.merchant.merchant_stock = {"nope": 1}
        self._enter_possession()
        view = build_services_view(self.aila, viewed=self.aila)
        self.assertEqual(view.player.wallet, 1000)
        self.assertIsNone(view.guild)
        self.assertIsNone(view.guild_unavailable_reason)
        self.assertIsNotNone(view.host)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "malformed_stock")
        self.assertEqual(view.pagination.stock_total, 0)
        self.assertEqual(view.pagination.sellable_total, 0)

    @covers_requirement(
        "webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel"
    )
    def test_combat_suppression_wins_over_a_possessed_merchant(self):
        # Enter possession first (the entry gate refuses combat), then attach
        # the active session to the possessed puppet.
        self._enter_possession()
        self.aila.db.active_combat = {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 1,
            "player_ids": [int(self.commander.pk)],
            "enemy_ids": [2],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
            "engagement_id": "hostile:1:0:1",
            "round_revision": 0,
            "draft_version": 0,
            "draft_entries": {},
            "confirmed_actors": [],
        }
        view = build_services_view(self.aila, viewed=self.aila)
        self.assertEqual(view.player.wallet, 1000)
        self.assertIsNone(view.host)
        self.assertIsNone(view.guild)
        self.assertIsNone(view.shop)
        self.assertIsNone(view.guild_unavailable_reason)
        self.assertIsNone(view.shop_unavailable_reason)
        self.assertEqual(view.pagination.board_total, 0)
        self.assertEqual(view.pagination.quest_total, 0)
        self.assertEqual(view.pagination.stock_total, 0)
        self.assertEqual(view.pagination.sellable_total, 0)

    @covers_requirement(
        "webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel"
    )
    def test_oversized_payload_drops_only_the_shop_surface(self):
        from web.webclient.presentation import services as presenter
        from web.webclient.presentation.protocol import (
            MAX_CANONICAL_JSON_BYTES,
            json_byte_size,
        )

        sizes = iter([MAX_CANONICAL_JSON_BYTES + 1])

        def first_measure_overflows(payload):
            return next(sizes, None) or json_byte_size(payload)

        with patch.object(presenter, "json_byte_size", side_effect=first_measure_overflows):
            payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["shop"])
        self.assertEqual(payload["pagination"]["stock_total"], 0)
        self.assertEqual(payload["pagination"]["sellable_total"], 0)
        self.assertEqual(payload["player"]["wallet"], 1000)

