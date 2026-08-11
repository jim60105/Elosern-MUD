"""Tests for the localized zh-tw default commands (localize-limbo-zhtw)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia import default_cmds
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

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
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room


class LocalizedCommandSurfaceTests(EvenniaTest):
    """The merged player cmdsets never expose a stock localized default."""

    def test_merged_cmdsets_expose_no_stock_localized_defaults(self):
        stock_classes = {
            default_cmds.CmdLook,
            default_cmds.CmdHelp,
            default_cmds.CmdSay,
            default_cmds.CmdPose,
            default_cmds.CmdGet,
            default_cmds.CmdDrop,
            default_cmds.CmdGive,
            default_cmds.CmdHome,
            default_cmds.CmdWhisper,
            default_cmds.CmdNick,
            default_cmds.CmdSetDesc,
            default_cmds.CmdQuit,
            default_cmds.CmdWho,
            default_cmds.CmdOOC,
            default_cmds.CmdIC,
            default_cmds.CmdPage,
            default_cmds.CmdPassword,
            default_cmds.CmdOption,
            default_cmds.CmdSessions,
            default_cmds.CmdColorTest,
            default_cmds.CmdStyle,
            default_cmds.CmdQuell,
        }
        for cmdset in (CharacterCmdSet(), AccountCmdSet()):
            for command in cmdset.commands:
                self.assertNotIn(type(command), stock_classes)

    def test_all_localized_keys_are_mounted(self):
        merged = {c.key for c in CharacterCmdSet().commands}
        merged.update({c.key for c in AccountCmdSet().commands})
        self.assertTrue(LOCALIZED_DEFAULT_KEYS.issubset(merged))


class LocalizedCharacterCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "測試房間"
        self.char1.key = "測試者"
        self.char2.key = "路人"
        self.room1.save()
        self.char1.save()
        self.char2.save()

    def test_look_without_location_reports_nothing_to_see(self):
        self.char1.location = None
        output = self.call(CmdLook(), "")
        self.assertIn("你沒有可以查看的地方！", output)

    def test_look_missing_target_is_silent(self):
        output = self.call(CmdLook(), "不存在的東西")
        self.assertIn("Could not find", output)

    def test_say_without_args_prompts(self):
        output = self.call(CmdSay(), "")
        self.assertIn("要說什麼？", output)

    def test_say_blocked_by_pre_say_is_silent(self):
        with patch.object(self.char1, "at_pre_say", return_value=None):
            output = self.call(CmdSay(), "你好")
        self.assertEqual(output, "")

    def test_get_without_args_prompts(self):
        output = self.call(CmdGet(), "")
        self.assertIn("要拿什麼？", output)

    def test_drop_without_args_prompts(self):
        output = self.call(CmdDrop(), "")
        self.assertIn("要丟什麼？", output)

    def test_give_without_args_prompts(self):
        output = self.call(CmdGive(), "")
        self.assertIn("用法：給", output)

    def test_whisper_without_receivers_is_silent(self):
        self.char2.location = self.room1
        with patch.object(self.char1, "search", return_value=None):
            output = self.call(CmdWhisper(), "路人 = 秘密")
        self.assertEqual(output, "")

    def test_home_moves_to_the_home_room(self):
        self.char1.home = self.room1
        self.char1.location = self.room2
        output = self.call(CmdHome(), "")
        self.assertIn("還是家最溫暖", output)
        self.assertIs(self.char1.location, self.room1)

    def test_nick_object_switch_creates_an_object_nick(self):
        output = self.call(CmdNick(), "/object 老闆 = 公會接待員")
        self.assertIn("Object-nick", output)

    def test_pose_without_args_prompts(self):
        output = self.call(CmdPose(), "")
        self.assertIn("你想做什麼？", output)

    def test_get_cannot_pick_up_self(self):
        output = self.call(CmdGet(), "測試者")
        self.assertIn("你不能拿自己。", output)

    def test_get_denied_object_uses_custom_error_message(self):
        obj = create_object("typeclasses.objects.Object", key="禁物", location=self.room1)
        obj.db.get_err_msg = "這是封印之物。"
        with patch.object(
            obj,
            "access",
            side_effect=lambda access_type, *a, **k: not (a and a[0] == "get"),
        ):
            output = self.call(CmdGet(), "禁物")
        self.assertIn("這是封印之物。", output)
        self.assertIs(obj.location, self.room1)

    def test_get_denied_object_reports_generic_message(self):
        obj = create_object("typeclasses.objects.Object", key="禁物", location=self.room1)
        with patch.object(
            obj,
            "access",
            side_effect=lambda access_type, *a, **k: not (a and a[0] == "get"),
        ):
            output = self.call(CmdGet(), "禁物")
        self.assertIn("你不能拿那個。", output)
        self.assertIs(obj.location, self.room1)

    def test_get_immovable_object_reports_failure(self):
        obj = create_object("typeclasses.objects.Object", key="巨石", location=self.room1)
        with patch.object(obj, "move_to", return_value=False):
            output = self.call(CmdGet(), "巨石")
        self.assertIn("那個撿不起來。", output)

    def test_drop_immovable_object_reports_failure(self):
        obj = create_object("typeclasses.objects.Object", key="黏石", location=self.char1)
        with patch.object(obj, "move_to", return_value=False):
            output = self.call(CmdDrop(), "黏石")
        self.assertIn("那個丟不掉。", output)

    def test_give_to_self_keeps_the_item(self):
        create_object("typeclasses.objects.Object", key="銅幣", location=self.char1)
        output = self.call(CmdGive(), "銅幣 = 測試者")
        self.assertIn("留給了", output)
        self.assertEqual(len([o for o in self.char1.contents if o.key == "銅幣"]), 1)

    def test_give_unmovable_item_reports_failure(self):
        create_object("typeclasses.objects.Object", key="銅幣", location=self.char1)
        self.char2.location = self.room1
        with patch("evennia.objects.objects.DefaultObject.move_to", return_value=False):
            output = self.call(CmdGive(), "銅幣 = 路人")
        self.assertIn("你無法把物品交給", output)

    def test_home_without_a_home_reports_none(self):
        self.char1.home = None
        output = self.call(CmdHome(), "")
        self.assertIn("你沒有家！", output)

    def test_whisper_usage_prompts(self):
        output = self.call(CmdWhisper(), "路人")
        self.assertIn("用法：耳語", output)

    def test_nick_clearall_switch(self):
        output = self.call(CmdNick(), "/clearall")
        self.assertIn("已清除所有暱稱。", output)

    def test_nick_delete_invalid_index(self):
        output = self.call(CmdNick(), "/delete 99")
        self.assertIn("無效的暱稱編號", output)

    def test_nick_delete_without_match(self):
        output = self.call(CmdNick(), "/delete 從未設定過的暱稱")
        self.assertIn("沒有符合的暱稱可以移除。", output)

    def test_nick_lookup_without_match(self):
        output = self.call(CmdNick(), "不存在的字首")
        self.assertIn("找不到以", output)

    def test_nick_identical_string_and_replacement_is_rejected(self):
        output = self.call(CmdNick(), "hi = hi")
        self.assertIn("一樣沒有意義", output)

    def test_nick_template_mismatch_is_rejected(self):
        output = self.call(CmdNick(), "$1 = 說")
        self.assertIn("必須使用相同的 $-標記", output)

    def test_nick_identical_replacement_is_reported(self):
        self.call(CmdNick(), "hi = 說 你好")
        output = self.call(CmdNick(), "hi = 說 你好")
        self.assertIn("已經設有一模一樣的", output)

    def test_setdesc_without_args_prompts(self):
        output = self.call(CmdSetDesc(), "")
        self.assertIn("你必須加上一段描述。", output)

    def test_look_command_delegates_to_at_look(self):
        with patch.object(self.char1, "at_look", return_value="外觀內容") as at_look:
            self.call(CmdLook(), "")
        at_look.assert_called_once()

    def test_look_english_alias_still_works(self):
        with patch.object(self.char1, "at_look", return_value="外觀內容") as at_look:
            self.call(CmdLook(), "", cmdstring="look")
        at_look.assert_called_once()

    def test_say_command_echoes_zh_tw(self):
        output = self.call(CmdSay(), "你好", msg="你 說：「你好」")
        self.assertIn("你 說：「你好」", output)

    def test_pose_command_broadcasts_zh_tw(self):
        output = self.call(CmdPose(), "靠著牆壁微笑。", msg="測試者 靠著牆壁微笑。")
        self.assertIn("測試者 靠著牆壁微笑。", output)

    def test_get_command_picks_up_zh_tw(self):
        obj = create_object("typeclasses.objects.Object", key="銅幣", location=self.room1)
        output = self.call(CmdGet(), "銅幣", msg="你撿起了銅幣。")
        self.assertEqual(obj.location, self.char1)
        self.assertIn("你撿起了銅幣。", output)

    def test_get_command_accepts_zh_tw_classifier_count(self):
        create_object("typeclasses.objects.Object", key="銅幣", location=self.room1)
        create_object("typeclasses.objects.Object", key="銅幣", location=self.room1)
        output = self.call(CmdGet(), "2 個 銅幣", msg="你撿起了2 個 銅幣。")
        self.assertIn("你撿起了2 個 銅幣。", output)
        self.assertEqual(len([o for o in self.char1.contents if o.key == "銅幣"]), 2)

    def test_drop_command_drops_zh_tw(self):
        obj = create_object("typeclasses.objects.Object", key="銅幣", location=self.char1)
        output = self.call(CmdDrop(), "銅幣", msg="你丟下了銅幣。")
        self.assertEqual(obj.location, self.room1)
        self.assertIn("你丟下了銅幣。", output)

    def test_give_command_hands_over_zh_tw(self):
        create_object("typeclasses.objects.Object", key="銅幣", location=self.char1)
        self.char2.location = self.room1
        output = self.call(CmdGive(), "銅幣 = 路人", msg="你把銅幣交給了")
        self.assertIn("你把銅幣交給了", output)

    def test_home_command_zh_tw(self):
        self.char1.home = self.room1
        self.char1.location = self.room1
        output = self.call(CmdHome(), "", msg="你已經在家了！")
        self.assertIn("你已經在家了！", output)

    def test_whisper_command_zh_tw(self):
        self.char2.location = self.room1
        messages = self.call(
            CmdWhisper(),
            "路人 = 秘密",
            msg={self.char2: "測試者 悄聲對你說：「秘密」"},
        )
        self.assertIn("悄聲對你說：「秘密」", messages)

    def test_nick_command_zh_tw(self):
        output = self.call(CmdNick(), "hi = 說 你好")
        self.assertIn("對應到", output)
        output = self.call(CmdNick(), "/delete hi")
        self.assertIn("已移除", output)

    def test_setdesc_command_zh_tw(self):
        output = self.call(CmdSetDesc(), "一位沉默的旅人。")
        self.assertEqual(self.char1.db.desc, "一位沉默的旅人。")
        self.assertIn("你已設定你的描述。", output)


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


class LocalizedXyzGridCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        from world.maps.bootstrap import sync_grid
        from world.maps.limbo import LIMBO_KEY

        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        from typeclasses.rooms import GridRoom

        self.south_gate = GridRoom.objects.filter_xyz(xyz=(2, 0, "capital_altoria")).first()
        self.char1.location = self.south_gate

    def test_map_command_off_grid_zh_tw(self):
        bare = create_object(Room, key="空白房", location=None)
        self.char1.location = bare
        output = self.call(CmdMap(), "")
        self.assertIn("你目前的位置不在網格上。", output)

    def test_goto_path_mode_shows_route_without_moving(self):
        before = self.char1.location
        output = self.call(CmdGoto(), "南大道", cmdstring="path")
        self.assertIn("共有 1 步", output)
        self.assertIs(self.char1.location, before)

    def test_goto_command_auto_walks_via_zh_tw_key(self):
        with patch("commands.localized.xyzgrid.delay", lambda *args, **kwargs: None):
            self.call(CmdGoto(), "南大道")
        self.assertEqual(self.char1.location.key, "南大道")

    def test_goto_english_alias_still_auto_walks(self):
        with patch("commands.localized.xyzgrid.delay", lambda *args, **kwargs: None):
            self.call(CmdGoto(), "南大道", cmdstring="goto")
        self.assertEqual(self.char1.location.key, "南大道")

    def test_goto_without_target_shows_usage(self):
        output = self.call(CmdGoto(), "")
        self.assertIn("用法：前往", output)

    def test_goto_displays_the_current_path(self):
        from types import SimpleNamespace

        self.char1.ndb.xy_path_data = SimpleNamespace(
            target=self.south_gate, task=None, directions=["east", "north"]
        )
        output = self.call(CmdGoto(), "")
        self.assertIn("的路徑：", output)

    def test_goto_clear_removes_the_current_path(self):
        from types import SimpleNamespace

        self.char1.ndb.xy_path_data = SimpleNamespace(
            target=self.south_gate, task=None, directions=["east"]
        )
        output = self.call(CmdGoto(), "clear", cmdstring="path")
        self.assertIn("已清除前往路徑。", output)
        self.assertIsNone(self.char1.ndb.xy_path_data)

    def test_goto_xyz_query_without_a_room_reports_none(self):
        output = self.call(CmdGoto(), "(99,99)")
        self.assertIn("找不到 (99,99)", output)

    def test_goto_unknown_destination_does_not_move(self):
        before = self.char1.location
        self.call(CmdGoto(), "不存在的村落")
        self.assertIs(self.char1.location, before)

    def test_map_command_displays_the_current_map(self):
        output = self.call(CmdMap(), "")
        self.assertTrue(output)

    def test_map_list_command_zh_tw(self):
        output = self.call(CmdMap(), "list")
        self.assertIn("網格上的地圖", output)

    def test_map_unknown_z_coordinate_zh_tw(self):
        output = self.call(CmdMap(), "z9")
        self.assertIn("找不到 XYMap", output)


class LocalizedHelpCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def _merged_cmdset(self):
        from evennia import CmdSet

        merged = CmdSet()
        for cmdset in (CharacterCmdSet(), AccountCmdSet()):
            for command in cmdset.commands:
                merged.add(command)
        return merged

    def test_help_index_is_zh_tw(self):
        output = self.call(CmdHelp(), "", cmdset=self._merged_cmdset())
        self.assertIn("指令", output)
        self.assertIn("看", output)
        self.assertNotIn("Commands", output)

    def test_help_entry_view_is_zh_tw(self):
        output = self.call(CmdHelp(), "說", cmdset=self._merged_cmdset())
        self.assertIn("說明：", output)
        self.assertIn("別名", output)

    def test_help_no_match_is_zh_tw(self):
        output = self.call(CmdHelp(), "不存在的東西", cmdset=self._merged_cmdset())
        self.assertIn("沒有符合", output)

    def test_help_db_entries_appear_in_the_index_section(self):
        from evennia.utils.create import create_help_entry

        create_help_entry("測試世界主題", "一篇關於世界的說明。", category="general")
        output = self.call(CmdHelp(), "", cmdset=self._merged_cmdset())
        self.assertIn("遊戲與世界", output)
        self.assertIn("測試世界主題", output)

    def test_help_suggestions_find_entry_text_matches(self):
        from evennia.utils.create import create_help_entry

        create_help_entry("測試主題", "其中提到了 中央廣場 這個地方。", category="general")
        output = self.call(CmdHelp(), "中央廣場", cmdset=self._merged_cmdset())
        self.assertIn("其他建議主題", output)
        self.assertIn("測試主題", output)


class LocalizedLookOnboardingIntegrationTests(EvenniaCommandTestMixin, EvenniaTest):
    """The localized 看 command still advances the onboarding look beat."""

    def test_look_command_advances_the_onboarding_look_beat(self):
        from world.maps.bootstrap import sync_grid
        from world.rules.onboarding import LOOK_BEAT_ID, GUIDANCE_BEAT_ID

        sync_grid()
        gate = self.room1
        gate.key = "南門"
        gate.save()
        self.char1.location = gate
        self.char1.onboarding_beat = LOOK_BEAT_ID
        self.char1.guide_progress = {"state": "active", "seen_keywords": []}
        self.char1.onboarded = False
        self.call(CmdLook(), "")
        self.assertTrue(self.char1.first_arrival_seen)
        self.assertEqual(self.char1.onboarding_beat, GUIDANCE_BEAT_ID)
