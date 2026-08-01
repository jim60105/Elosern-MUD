"""Command-level tests for guild, combat, and economy commands (tasks 11.1-11.4)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff, Merchant
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from commands.guild import (
    CmdGuildAccept,
    CmdGuildList,
    CmdGuildRegister,
    CmdGuildTurnIn,
)
from commands.combat import CmdEngage, CmdGuildExam
from commands.economy import CmdBuy, CmdSell, CmdShopStock
from world.quests.catalog import register_catalog
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.runtime import fulfill_record, read_records
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.quests.transitions import apply_quest_log_replacement
from world.rules.guild_config import CATALOG, load_catalog_into_cache
from world.rules.guild_offers import GUILD_OFFER_REGISTRY, register_guild_offer
from world.rules.surfaces import write_counter_trait
from world.rules.combat_session import engage


class CommandIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        register_catalog()
        load_catalog_into_cache()
        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()


class GuildCommandTests(CommandIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="guild hall")
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.staff = create_object(NPC, key="staff", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        from world.rules.guild_config import register_catalog_offers

        register_catalog_offers(load_catalog_into_cache())

    def test_register_list_accept_turnin_flow(self):
        self.call(CmdGuildRegister(), "", "你已註冊為冒險者")
        self.call(CmdGuildList(), "", "任務板")
        self.call(CmdGuildAccept(), "introductory_hunt", "你接取了任務")

        record = next(r for r in read_records(self.char1) if r.definition_key == "introductory_hunt")
        completed = fulfill_record(record, QUEST_DEFINITION_REGISTRY["introductory_hunt"])
        records = read_records(self.char1)
        apply_quest_log_replacement(
            self.char1,
            [completed if r.quest_id == record.quest_id else r for r in records],
        )
        self.call(CmdGuildTurnIn(), record.quest_id, "你回報了任務")

    def test_absent_staff_rejects(self):
        self.char1.location = create_object(Room, key="empty")
        self.call(CmdGuildRegister(), "", "這裡沒有公會服務人員")

    def test_ambiguous_staff_rejects(self):
        second = create_object(NPC, key="staff2", location=self.hall)
        second.components.add(
            GuildStaff.create(second, service_id="staff2", branch_key="guild_branch_altoria")
        )
        self.call(CmdGuildRegister(), "", "這裡沒有公會服務人員")


class CombatCommandTests(CommandIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.arena = create_object(Room, key="arena")
        self.char1.location = self.arena
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.monster = create_object(Monster, key="goblin", location=self.arena)
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier("floor")

    def test_engage_prompts_and_monster_not_remote(self):
        self.call(CmdEngage(), "goblin", "戰鬥開始")
        self.assertIsNotNone(self.char1.db.active_combat)


class EconomyCommandTests(CommandIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.store = create_object(Room, key="store")
        self.char1.location = self.store
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.db.wallet = 500
        self.merchant_npc = create_object(NPC, key="merchant", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc,
            service_id="merchant",
            shop_key="altoria_general_store",
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {
            "meal": 20,
            "healing_potion": 3,
            "plain_sword": 1,
        }

    @covers_requirement("shop-economy::player-facing-shop-commands-use-only-a-local-unambiguous-merchant")
    def test_stock_buy_sell_flow(self):
        with patch("world.rules.economy.get_world_clock") as clock:
            clock.return_value.tick = 12 * 3600
            self.call(CmdShopStock(), "", "商店（營業中）")
            self.call(CmdBuy(), "meal 2", "你買了 2 個")
            self.call(CmdSell(), "meal 1", "你賣了 1 個")
        self.assertEqual(self.char1.db.wallet, 500 - 20 + 5)


if __name__ == "__main__":
    import unittest

    unittest.main()
