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
