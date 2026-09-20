"""Slice of ``test_localized``: LocalizedAccountCommandTests.
"""
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from django.test import override_settings
from evennia import default_cmds
from evennia.objects.objects import DefaultObject
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase
from commands.default_cmdsets import AccountCmdSet, CharacterCmdSet
from commands.localized import (
    CmdDrop,
    CmdGet,
    CmdGive,
    CmdGoto,
    CmdHelp,
    CmdHome,
    CmdIC,
    CmdLook,
    CmdMap,
    CmdNick,
    CmdOOC,
    CmdOOCLook,
    CmdOption,
    CmdPage,
    CmdPassword,
    CmdPose,
    CmdQuell,
    CmdQuit,
    CmdSay,
    CmdSessions,
    CmdSetDesc,
    CmdStyle,
    CmdWhisper,
    CmdWho,
    CmdColorTest,
    LOCALIZED_DEFAULT_KEYS,
)
from typeclasses.rooms import InstanceRoom
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    acquire,
    deliver,
    quest,
    register,
)
from world.rules.combat_session import engage
from world.rules.quest_delivery import active_deliveries_for_recipient
from world.rules.tests._combat_session_helpers import _monster
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import make_item, synthetic_registries


class LocalizedAccountCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def test_who_command_zh_tw(self):
        output = self.call(CmdWho(), "", caller=self.account, msg="在線帳號：")
        self.assertIn("在線帳號：", output)

    def test_ooc_command_zh_tw_when_already_ooc(self):
        first = self.call(CmdOOC(), "", caller=self.account)
        self.assertIn("你已離開角色", first)
        second = self.call(CmdOOC(), "", caller=self.account, msg="你已經在 OOC 狀態了。")
        self.assertIn("你已經在 OOC 狀態了。", second)

    def test_ic_command_usage_zh_tw(self):
        self.account.db._last_puppet = None
        output = self.call(CmdIC(), "", caller=self.account)
        self.assertIn("用法：進入世界 <角色>", output)

    def test_page_command_empty_list_zh_tw(self):
        output = self.call(CmdPage(), "", caller=self.account)
        self.assertIn("你還沒有傳送或接收任何傳訊。", output)

    def test_password_command_usage_zh_tw(self):
        output = self.call(CmdPassword(), "", caller=self.account)
        self.assertIn("用法：密碼 <舊密碼> = <新密碼>", output)

    def test_option_command_lists_settings_zh_tw(self):
        output = self.call(CmdOption(), "", caller=self.account)
        self.assertIn("客戶端設定", output)

    def test_sessions_command_zh_tw(self):
        output = self.call(CmdSessions(), "", caller=self.account)
        self.assertIn("你目前的連線：", output)

    def test_color_command_usage_zh_tw(self):
        output = self.call(CmdColorTest(), "nonsense", caller=self.account)
        self.assertIn("用法：色彩 ansi", output)

    def test_style_command_lists_options_zh_tw(self):
        output = self.call(CmdStyle(), "", caller=self.account)
        self.assertIn("選項", output)

    def test_quell_command_zh_tw(self):
        output = self.call(CmdQuell(), "", caller=self.account)
        self.assertTrue(self.account.attributes.get("_quell"))
        self.assertIn("降權", output)
        output = self.call(CmdQuell(), "", caller=self.account, cmdstring="取消降權")
        self.assertFalse(self.account.attributes.get("_quell"))

    def test_quit_command_zh_tw(self):
        with patch.object(self.account, "disconnect_session_from_account"):
            output = self.call(CmdQuit(), "", caller=self.account)
        self.assertIn("登出", output)

    def test_ooc_look_while_puppeted_is_blocked(self):
        output = self.call(CmdOOCLook(), "", caller=self.account)
        self.assertIn("你目前沒有能力查看四周。", output)

    def test_ooc_and_ooc_look_render_playable_list_at_cap_one_and_raised_cap(self):
        # 1. Start puppeted, leave character (OOC) at MAX_NR_CHARACTERS=1
        with override_settings(MAX_NR_CHARACTERS=1):
            output = self.call(CmdOOC(), "", caller=self.account)
            self.assertIn("你已離開角色", output)
            self.assertNotIn("回到遊戲", output)
            self.assertIn(self.char1.key, output)

            # OOC Look while unpuppeted at MAX_NR_CHARACTERS=1
            output_look = self.call(CmdOOCLook(), "", caller=self.account)
            self.assertNotIn("回到遊戲", output_look)
            self.assertIn(self.char1.key, output_look)

        # 2. Re-puppet and test at raised cap (MAX_NR_CHARACTERS=5)
        self.account.puppet_object(self.session, self.char1)
        with override_settings(MAX_NR_CHARACTERS=5):
            output = self.call(CmdOOC(), "", caller=self.account)
            self.assertIn("你已離開角色", output)
            self.assertNotIn("回到遊戲", output)
            self.assertIn(self.char1.key, output)

            # OOC Look while unpuppeted at MAX_NR_CHARACTERS=5
            output_look = self.call(CmdOOCLook(), "", caller=self.account)
            self.assertNotIn("回到遊戲", output_look)
            self.assertIn(self.char1.key, output_look)

    def test_ic_command_puppets_the_only_matching_character(self):
        with patch.object(self.account, "puppet_object") as puppet:
            self.call(CmdIC(), "Char", caller=self.account)
        puppet.assert_called_once()
        self.assertEqual(self.account.db._last_puppet, self.char1)

    def test_ic_command_unknown_name_is_rejected(self):
        output = self.call(CmdIC(), "不存在", caller=self.account)
        self.assertIn("那不是一個有效的角色。", output)

    def test_ic_command_multiple_matches_are_reported(self):
        first = create_object(PlayerCharacter, key="雙胞")
        second = create_object(PlayerCharacter, key="雙胞")
        self.account.characters.add(first)
        self.account.characters.add(second)
        output = self.call(CmdIC(), "雙胞", caller=self.account)
        self.assertIn("多個同名目標", output)

    def test_ic_command_puppet_failure_is_reported(self):
        with patch.object(
            self.account, "puppet_object", side_effect=RuntimeError("blocked")
        ):
            output = self.call(CmdIC(), "Char", caller=self.account)
        self.assertIn("你無法附身", output)

    def test_ooc_command_unpuppet_failure_is_reported(self):
        with patch.object(
            self.account, "unpuppet_object", side_effect=RuntimeError("blocked")
        ):
            output = self.call(CmdOOC(), "", caller=self.account)
        self.assertIn("無法離開角色", output)

    def test_who_doing_alias_hides_session_data(self):
        output = self.call(CmdWho(), "", caller=self.account, cmdstring="doing")
        self.assertIn("在線帳號：", output)
        self.assertNotIn("協定", output)

    def test_option_save_and_clear_switches(self):
        output = self.call(CmdOption(), "/save", caller=self.account)
        self.assertIn("已儲存所有選項", output)
        self.assertIsNotNone(self.account.attributes.get("_saved_protocol_flags"))
        output = self.call(CmdOption(), "/clear", caller=self.account)
        self.assertIn("已清除所有已儲存的選項。", output)
        self.assertEqual(self.account.attributes.get("_saved_protocol_flags"), {})

    def test_option_changes_and_keeps_a_boolean_flag(self):
        # The test session has no live Portal to sync flags to; the flag dict
        # mutation inside the command is what is exercised. Every value change
        # (and even an unchanged value) ends in update_flags.
        with patch("evennia.server.serversession.ServerSession.update_flags"):
            output = self.call(CmdOption(), "ANSI = on", caller=self.account)
            self.assertIn("已從", output)
            self.assertTrue(self.session.protocol_flags["ANSI"])
            output = self.call(CmdOption(), "ANSI = on", caller=self.account)
            self.assertIn("保持為", output)

    def test_option_unknown_name_is_rejected(self):
        output = self.call(CmdOption(), "BOGUS = 1", caller=self.account)
        self.assertIn("沒有名為", output)

    def test_option_invalid_encoding_is_rejected(self):
        output = self.call(CmdOption(), "ENCODING = 不存在的編碼", caller=self.account)
        self.assertIn("無法設定選項", output)

    def test_option_usage_without_a_value(self):
        output = self.call(CmdOption(), "ANSI", caller=self.account)
        self.assertIn("用法：選項", output)

    def test_password_change_success(self):
        output = self.call(
            CmdPassword(), "testpassword = newpass123", caller=self.account
        )
        self.assertIn("密碼已變更。", output)
        self.assertTrue(self.account.check_password("newpass123"))

    def test_password_wrong_old_password_is_rejected(self):
        output = self.call(
            CmdPassword(), "wrongpass = newpass123", caller=self.account
        )
        self.assertIn("舊密碼不正確。", output)
        self.assertFalse(self.account.check_password("newpass123"))

    def test_password_weak_new_password_is_rejected(self):
        output = self.call(CmdPassword(), "testpassword = 1", caller=self.account)
        self.assertFalse(self.account.check_password("1"))
        self.assertTrue(self.account.check_password("testpassword"))

    def test_quit_all_disconnects_every_session(self):
        with patch.object(
            self.account, "disconnect_session_from_account"
        ) as disconnect:
            output = self.call(CmdQuit(), "/all", caller=self.account)
        self.assertIn("登出", output)
        disconnect.assert_called()

    def test_color_test_ansi_palette(self):
        output = self.call(CmdColorTest(), "ansi", caller=self.account)
        self.assertIn("ANSI 色彩", output)

    def test_color_test_xterm256_palette(self):
        output = self.call(CmdColorTest(), "xterm256", caller=self.account)
        self.assertIn("Xterm256 色彩", output)

    def test_color_test_truecolor_palette(self):
        output = self.call(CmdColorTest(), "truecolor", caller=self.account)
        self.assertIn("真彩色", output)

    def test_quell_when_already_quelled(self):
        self.account.attributes.add("_quell", True)
        output = self.call(CmdQuell(), "", caller=self.account)
        self.assertIn("已經在降權中", output)

    def test_unquell_when_not_quelled(self):
        output = self.call(CmdQuell(), "", caller=self.account, cmdstring="取消降權")
        self.assertIn("目前已經使用正常的帳號權限", output)

    def test_quell_without_a_puppet(self):
        self.session.puppet = None
        output = self.call(CmdQuell(), "", caller=self.account)
        self.assertIn("降權帳號權限", output)
