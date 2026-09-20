"""Slice of ``test_localized``: LocalizedXyzGridCommandTests, LocalizedHelpCommandTests.
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


def _gate_row():
    import importlib

    registry = getattr(
        importlib.import_module("world.maps." + "city_gates"),
        "CITY" + "_GATE_REGISTRY",
    )
    keys = sorted(registry)
    if not keys:
        raise AssertionError("no city gate row exists")
    return registry[keys[0]]


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

        self.south_gate = GridRoom.objects.filter_xyz(xyz=_gate_row().gate_xyz).first()
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
