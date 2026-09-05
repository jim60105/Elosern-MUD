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
    CmdGuildLog,
    CmdGuildRegister,
    CmdGuildShow,
    CmdGuildTurnIn,
)
from commands.combat import CmdEngage, CmdGuildExam
from commands.economy import CmdBuy, CmdSell, CmdShopStock
from world.quests.catalog import register_catalog
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.runtime import fulfill_record, read_records
from world.quests.tests._fixtures import QuestRegistryIsolation, quest, register
from world.quests.transitions import apply_quest_log_replacement
from world.rules.guild_config import CATALOG, load_catalog_into_cache
from world.rules.guild_offers import GUILD_OFFER_REGISTRY, register_guild_offer
from world.rules.surfaces import write_counter_trait
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.skills.equipment import list_items


class CommandIsolation(BattlefieldIsolation, QuestRegistryIsolation):
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
        output = self.call(CmdGuildTurnIn(), record.quest_id, "你回報了任務")
        self.assertIn("獲得異名：南門新客", output)
        # The retired onboarding welcome must never resurface on a claim.
        self.assertNotIn("你的第一個日子在這裡圓滿結束", output)
        # A later distinct successful claim pays normally and stays title-silent.
        from world.quests.runtime import accept_quest

        second = accept_quest(self.char1, "introductory_hunt")
        second_completed = fulfill_record(
            second, QUEST_DEFINITION_REGISTRY["introductory_hunt"]
        )
        records = read_records(self.char1)
        apply_quest_log_replacement(
            self.char1,
            [
                second_completed if r.quest_id == second.quest_id else r
                for r in records
            ],
        )
        output = self.call(
            CmdGuildTurnIn(), second_completed.quest_id, "你回報了任務"
        )
        self.assertNotIn("獲得異名", output)

    def test_absent_staff_rejects(self):
        self.char1.location = create_object(Room, key="empty")
        self.call(CmdGuildRegister(), "", "這裡沒有公會服務人員")

    def test_off_anchor_clerk_refuses_with_the_gate_line(self):
        # A sync-converged place-bound clerk traveling off its anchor is
        # refused through the command surface with the gate's fixed message
        # (service-anchoring), never framed as a registration failure.
        from world.rules.service_gate import MESSAGE_OFF_ANCHOR

        component = self.staff.components.get(GuildStaff.get_component_slot())
        component.service_binding = "place"
        component.anchor_room_id = self.hall.pk
        square = create_object(Room, key="town square")
        self.staff.location = square
        self.char1.location = square
        self.call(CmdGuildRegister(), "", MESSAGE_OFF_ANCHOR)
        self.assertIsNone(self.char1.db.guild_registration)

    def test_ambiguous_staff_rejects(self):
        second = create_object(NPC, key="staff2", location=self.hall)
        second.components.add(
            GuildStaff.create(second, service_id="staff2", branch_key="guild_branch_altoria")
        )
        self.call(CmdGuildRegister(), "", "這裡沒有公會服務人員")


class QuestDetailCommandTests(CommandIsolation, EvenniaCommandTestMixin, EvenniaTest):
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
        from world.quests.runtime import accept_quest
        from world.rules.guild import register_adventurer

        register_adventurer(self.char1, self.staff)
        self.record = accept_quest(self.char1, "introductory_hunt")

    @covers_requirement(
        "quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail",
        "guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host",
    )
    def test_show_accepted_detail_without_staff(self):
        self.char1.location = create_object(Room, key="empty")
        output = self.call(CmdGuildShow(), self.record.quest_id, caller=self.char1)
        self.assertIn("討伐低階魔物", output)
        self.assertIn("進行中", output)
        self.assertIn("討伐 1 隻低階魔物", output)
        self.assertIn("進度：0 / 1", output)
        self.assertIn("獎勵：銅 50", output)

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_show_unknown_id_is_rejected_without_state_change(self):
        self.char1.location = create_object(Room, key="empty")
        output = self.call(CmdGuildShow(), "bogus:1", caller=self.char1)
        self.assertIn("找不到這個任務", output)
        self.assertEqual(read_records(self.char1), [self.record])

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_show_reward_omitted_when_definition_has_no_offer(self):
        register(quest("no_offer_hunt"))
        from world.quests.runtime import accept_quest

        record = accept_quest(self.char1, "no_offer_hunt")
        self.char1.location = create_object(Room, key="empty")
        output = self.call(CmdGuildShow(), record.quest_id, caller=self.char1)
        self.assertIn("測試任務 no_offer_hunt", output)
        self.assertNotIn("獎勵", output)

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_show_unregistered_player_sees_no_reward_section(self):
        self.char1.db.guild_registration = None
        from typeclasses.characters import PlayerCharacter

        player = create_object(PlayerCharacter, key="unregistered")
        player.location = self.char1.location
        from world.quests.runtime import accept_quest

        record = accept_quest(player, "introductory_hunt")
        output = self.call(CmdGuildShow(), record.quest_id, caller=player)
        self.assertIn("討伐低階魔物", output)
        self.assertNotIn("獎勵", output)

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_show_malformed_registration_errors(self):
        self.char1.db.guild_registration = {"branch_key": "guild_branch_altoria"}
        self.char1.location = create_object(Room, key="empty")
        output = self.call(CmdGuildShow(), self.record.quest_id, caller=self.char1)
        self.assertIn("無法顯示任務詳情", output)

    @covers_requirement("quest-detail-view::a-player-can-inspect-one-own-quest-s-full-detail")
    def test_show_expired_deadline_reports_overdue(self):
        from unittest.mock import patch

        register(quest("deadline_hunt", deadline_hours=1))
        from world.quests.runtime import accept_quest

        record = accept_quest(self.char1, "deadline_hunt")
        self.char1.location = create_object(Room, key="empty")
        from world.rules.clock import CLOCK_YAML

        with patch("commands.guild.get_world_clock") as clock:
            clock.return_value.tick = record.deadline_tick
            output = self.call(CmdGuildShow(), record.quest_id, caller=self.char1)
        self.assertIn("已逾期", output)

    @covers_requirement(
        "guild-quest-board::board-listing-and-quest-log-surface-objective-guidance",
    )
    def test_board_rows_show_first_objective_one_liner(self):
        output = self.call(CmdGuildList(), "", caller=self.char1)
        self.assertIn("討伐 1 隻低階魔物", output)
        self.assertIn("introductory_hunt", output)

    @covers_requirement(
        "guild-quest-board::board-listing-and-quest-log-surface-objective-guidance",
    )
    def test_log_hints_at_the_detail_command(self):
        output = self.call(CmdGuildLog(), "", caller=self.char1)
        self.assertIn("guild show", output)

    @covers_requirement(
        "guild-quest-board::board-listing-and-quest-log-surface-objective-guidance",
    )
    def test_objective_summaries_do_not_change_eligibility(self):
        from world.rules.guild_offers import list_guild_offers

        eligible = [offer.definition_key for offer in list_guild_offers(self.char1, self.staff)]
        output = self.call(CmdGuildList(), "", caller=self.char1)
        for key in eligible:
            self.assertIn(key, output)
        self.assertEqual(eligible, ["introductory_hunt"])


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


class ScheduleGateCommandTests(CommandIsolation, EvenniaCommandTestMixin, EvenniaTest):
    """Schedule-state gating on the command surfaces (npc-schedule-runtime D4).

    A busy/resting merchant or guild host refuses the transaction on every
    command surface with the stable rejection line and no state change; an
    unblocked host behaves exactly as before (covered by the flow tests).
    """

    BLOCKED = "她現在正忙著，沒有理會你。"

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
        self.merchant.merchant_stock = {"meal": 20, "healing_potion": 3, "plain_sword": 1}
        self.hall = create_object(Room, key="guild hall")
        self.staff = create_object(NPC, key="staff", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        from world.rules.guild_config import register_catalog_offers

        register_catalog_offers(load_catalog_into_cache())

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_merchant_blocks_buy_without_a_transaction(self):
        self.merchant_npc.db.schedule_state = "busy"
        self.call(CmdBuy(), "meal 2", self.BLOCKED)
        self.assertEqual(self.char1.db.wallet, 500)
        self.assertEqual(self.merchant.merchant_stock["meal"], 20)

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_resting_merchant_blocks_sell_without_a_transaction(self):
        self.merchant_npc.db.schedule_state = "resting"
        self.char1.db.inventory = ["meal"]
        self.call(CmdSell(), "meal 1", self.BLOCKED)
        self.assertEqual(self.char1.db.wallet, 500)
        self.assertEqual(list_items(self.char1), ["meal"])

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_guild_host_blocks_register_without_state_change(self):
        self.char1.location = self.hall
        self.staff.db.schedule_state = "busy"
        self.call(CmdGuildRegister(), "", self.BLOCKED)
        self.assertIsNone(self.char1.db.guild_registration)

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_guild_host_blocks_turnin_without_a_claim(self):
        from world.rules.guild import register_adventurer

        self.char1.location = self.hall
        register_adventurer(self.char1, self.staff)
        from world.quests.runtime import accept_quest, fulfill_record, read_records
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY

        record = accept_quest(self.char1, "introductory_hunt")
        completed = fulfill_record(record, QUEST_DEFINITION_REGISTRY["introductory_hunt"])
        from world.quests.transitions import apply_quest_log_replacement

        apply_quest_log_replacement(self.char1, [completed])
        self.staff.db.schedule_state = "busy"
        self.call(CmdGuildTurnIn(), completed.quest_id, self.BLOCKED)
        self.assertEqual(read_records(self.char1), [completed])

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_examiner_blocks_the_exam_command_without_a_session(self):
        from typeclasses.components import GuildExaminer

        self.char1.location = self.hall
        examiner = create_object(NPC, key="examiner", location=self.hall)
        examiner.components.add(
            GuildExaminer.create(
                examiner, service_id="examiner", branch_key="guild_branch_altoria"
            )
        )
        examiner.db.schedule_state = "busy"
        self.call(CmdGuildExam(), "E", self.BLOCKED)
        self.assertIsNone(self.char1.db.active_combat)

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_duty_state_does_not_block_shop_buy(self):
        self.merchant_npc.db.schedule_state = "duty"
        with patch("world.rules.economy.get_world_clock") as clock:
            clock.return_value.tick = 12 * 3600
            self.call(CmdBuy(), "meal 2", "你買了 2 個")
        self.assertEqual(self.char1.db.wallet, 480)


if __name__ == "__main__":
    import unittest

    unittest.main()
