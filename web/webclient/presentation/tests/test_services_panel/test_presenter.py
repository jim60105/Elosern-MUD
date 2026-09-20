"""Services panel presenter tests: guild/shop/quest envelopes through the registry."""
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff, Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import build_production_registry
from world.quests.definitions import QUEST_DEFINITION_REGISTRY, QuestStage
from world.quests.tests._fixtures import defeat, quest, register
from world.rules.clock import get_world_clock
from world.rules.guild import register_adventurer
from world.rules.guild_offers import GUILD_OFFER_REGISTRY, GuildQuestOffer, QuestReward, accept_guild_offer, register_guild_offer
from world.rules.surfaces import write_counter_trait
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import install_synthetic_catalog, price_band, synth_catalog, synth_shop_config
from world.tests.synthetic_data import SYNTH_ITEMS
from ._support import BRANCH, T_SHOP, _T_SPRAY, _T_THORN
import unittest


class ServicesPresenterTests(BattlefieldIsolation, EvenniaTestCase):

    def setUp(self):
        # Scope before construction: branch/shop/item identities resolve
        # against kit rows inside the synthetic shop catalog.
        open_synthetic_scope(self, "guild_branches", "items", "prices", "shops")
        super().setUp()
        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offers = list(GUILD_OFFER_REGISTRY.items())
        install_synthetic_catalog(
            self, synth_catalog(shop_configs={T_SHOP: synth_shop_config(T_SHOP, (_T_SPRAY, _T_THORN))})
        )
        get_world_clock()
        self.room1 = create_object(Room, key="guild hall")

        self.store = create_object(Room, key="general store")
        self.staff = create_object(NPC, key="guild master", location=self.room1)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key=BRANCH)
        )
        self.staff.components.add(
            GuildExaminer.create(self.staff, service_id="examiner", branch_key=BRANCH)
        )
        self.merchant_npc = create_object(NPC, key="shop keeper", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc, service_id="store", shop_key=T_SHOP
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {_T_SPRAY: 20, _T_THORN: 3}

        self.player = create_object(PlayerCharacter, key="service presenter")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.db.wallet = 1000
        register_adventurer(self.player, staff=self.staff)
        write_counter_trait(self.player, "guild_merit", 60)
        # One invented branch-local offer stands in for any catalog row.
        self.board_quest = register(
            quest("services_panel_quest", stages=(QuestStage(0, defeat(tier="low")),))
        )
        register_guild_offer(
            GuildQuestOffer(
                definition_key=self.board_quest.key,
                issuer_branch_key=BRANCH,
                reward=QuestReward(copper=50, items=(), merit=25),
            )
        )
        accept_guild_offer(self.player, self.staff, self.board_quest.key)


    def tearDown(self):
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offers)
        super().tearDown()


    def _context(self):
        return PresentationContext(actor=self.player, protocol_version=1)


    def _render(self):
        return build_production_registry().render("services", self._context())


    @covers_requirement("webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel")
    def test_guild_hall_renders_available_services_payload(self):
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "services")
        self.assertIsNone(payload["shop"])
        self.assertIsNotNone(payload["guild"])
        self.assertIsNotNone(payload["player"])
        self.assertEqual(payload["pagination"]["board_total"], 1)
        self.assertEqual(payload["pagination"]["quest_total"], 1)
        self.assertEqual(payload["player"]["guild_rank"], "F")
        self.assertEqual(payload["guild"]["registration"]["registered"], True)


    def test_shop_renders_exact_copper_and_open_state(self):
        self.player.location = self.store
        get_world_clock()._persist(12 * 3600)
        payload = self._render()
        self.assertIsNotNone(payload["shop"])
        self.assertTrue(payload["shop"]["open"])
        spray = next(row for row in payload["shop"]["stock"] if row["item_key"] == _T_SPRAY)
        floor, _ceiling = price_band(_T_SPRAY)
        self.assertEqual(spray["buy_copper"], floor + 2)
        self.assertEqual(spray["sell_copper"], floor)
        self.assertEqual(spray["stock"], 20)
        self.assertIsNotNone(spray["buy"]["quantity"])
        self.assertIsNone(payload["guild"])


    def test_registered_panels_publish_affected_panels(self):
        # Rendering never mutates canonical surfaces.
        before = {
            "wallet": self.player.db.wallet,
            "quest_log": list(self.player.db.quest_log or []),
        }
        self._render()
        self.assertEqual(self.player.db.wallet, before["wallet"])
        self.assertEqual(list(self.player.db.quest_log or []), before["quest_log"])


    @covers_requirement("webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel")
    def test_combat_mode_ships_personal_inventory_only(self):
        from evennia.utils.create import create_object as co
        from typeclasses.monsters import Monster

        self.player.db.inventory = [_T_SPRAY]
        monster = co(Monster, key="goblin", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        from world.rules.combat_session import engage

        engage(self.player, monster)
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["host"])
        self.assertIsNone(payload["guild"])
        self.assertIsNone(payload["shop"])
        self.assertIsNotNone(payload["player"])
        self.assertIsNotNone(payload["inventory"])
        self.assertEqual(payload["pagination"]["board_total"], 0)
        self.assertEqual(payload["pagination"]["quest_total"], 0)
        self.assertEqual(payload["pagination"]["stock_total"], 0)
        self.assertEqual(payload["pagination"]["sellable_total"], 0)
        row = payload["inventory"]["rows"][0]
        self.assertEqual(row["item_key"], _T_SPRAY)
        self.assertEqual(row["action"]["action_id"], "inventory.use")


    def test_creation_pending_renders_unavailable_form(self):
        self.player.db.creation_pending = True
        payload = self._render()
        self.assertFalse(payload["available"])


    def test_corrupt_quest_log_degrades_only_guild_surface(self):
        self.player.db.quest_log = [{"quest_id": "broken", "definition_key": "nope"}]
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["guild"])
        self.assertIsNotNone(payload["inventory"])
        self.assertEqual(payload["pagination"]["board_total"], 0)
        self.assertEqual(payload["pagination"]["quest_total"], 0)


    def test_malformed_stock_degrades_only_shop_surface(self):
        self.merchant.merchant_stock = {"nope": 5}
        self.player.location = self.store
        get_world_clock()._persist(12 * 3600)
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["shop"])
        self.assertIsNotNone(payload["inventory"])


    @covers_requirement("webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory")
    def test_registered_inventory_projects_registry_presentation(self):
        self.player.db.inventory = [_T_SPRAY, _T_SPRAY, _T_THORN]
        payload = self._render()
        rows = {row["item_key"]: row for row in payload["inventory"]["rows"]}
        kit_row = SYNTH_ITEMS["t_ember_spray"]
        self.assertEqual(
            rows[_T_SPRAY]["presentation"],
            {
                "kind": kit_row.presentation.kind.value,
                "icon_key": kit_row.presentation.icon_key.value,
                "rarity": kit_row.presentation.rarity.value,
                "summary": kit_row.presentation.summary_zh,
            },
        )
        self.assertEqual(rows[_T_SPRAY]["held"], 2)
        self.assertEqual(
            rows[_T_THORN]["presentation"]["rarity"],
            SYNTH_ITEMS["t_thorn_knife"].presentation.rarity.value,
        )


    @covers_requirement("webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory")
    def test_unknown_inventory_key_projects_null_presentation(self):
        self.player.db.inventory = ["mystery_relic", "mystery_relic", _T_SPRAY]
        payload = self._render()
        rows = {row["item_key"]: row for row in payload["inventory"]["rows"]}
        self.assertIsNone(rows["mystery_relic"]["presentation"])
        self.assertEqual(rows["mystery_relic"]["display_name"], "mystery_relic")
        self.assertIsNotNone(rows[_T_SPRAY]["presentation"])


    @covers_requirement("webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel")
    def test_rendering_inventory_never_mutates_canonical_state(self):
        self.player.db.inventory = [_T_SPRAY, _T_SPRAY, "mystery_relic", _T_THORN]
        self.player.db.equipment = {
            "weapon_main": _T_THORN,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        before = {
            "inventory": list(self.player.db.inventory or []),
            "equipment": dict(self.player.db.equipment or {}),
            "wallet": self.player.db.wallet,
            "quest_log": list(self.player.db.quest_log or []),
        }
        payload = self._render()
        self.assertEqual(list(self.player.db.inventory or []), before["inventory"])
        self.assertEqual(dict(self.player.db.equipment or {}), before["equipment"])
        self.assertEqual(self.player.db.wallet, before["wallet"])
        self.assertEqual(list(self.player.db.quest_log or []), before["quest_log"])
        row = next(r for r in payload["inventory"]["rows"] if r["item_key"] == _T_THORN)
        self.assertTrue(row["equipped"])


    def test_unregistered_presenter_is_honest(self):
        newcomer = create_object(PlayerCharacter, key="newcomer")
        newcomer.race = "human"
        newcomer.apply_race_baseline()
        newcomer.location = self.room1
        newcomer.db.wallet = 5
        context = PresentationContext(actor=newcomer, protocol_version=1)
        payload = build_production_registry().render("services", context)
        self.assertTrue(payload["available"])
        self.assertFalse(payload["player"]["guild_registered"])
        self.assertIsNone(payload["player"]["guild_rank"])
        self.assertEqual(payload["guild"]["board"], [])
        self.assertEqual(payload["guild"]["registration"]["register"]["enabled"], True)


if __name__ == "__main__":
    unittest.main()
