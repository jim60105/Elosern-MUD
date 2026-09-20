"""Slice of ``test_localized``: LocalizedCharacterCommandTests.
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

from ._support import (
    _MEAL,
    _MEAL_KEY,
    _POTION,
)


class LocalizedCharacterCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        # The registry-object give/get/drop paths carry kit item keys through
        # the canonical-key seams.
        scope = synthetic_registries("items", extra={"items": {_MEAL.key: _MEAL}})
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
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

    @covers_requirement("equipment-inventory::the-key-list-is-the-single-canonical-inventory-record-for-registry-items")
    @covers_requirement("equipment-inventory::localized-item-commands-synchronize-containment-and-the-key-list")
    def test_get_registry_object_records_the_canonical_key(self):
        create_object(
            "typeclasses.objects.Object",
            key=_POTION,
            attributes=[("registry_key", _POTION)],
            location=self.room1,
        )
        output = self.call(CmdGet(), _POTION)
        self.assertIn(f"你撿起了{_POTION}。", output)
        self.assertEqual(self.char1.db.inventory, [_POTION])
        self.assertEqual(
            len([o for o in self.char1.contents if o.key == _POTION]), 1
        )

    def test_get_registry_object_by_key_attribute_only(self):
        create_object(
            "typeclasses.objects.Object",
            key="藥水",
            attributes=[("registry_key", _POTION)],
            location=self.room1,
        )
        output = self.call(CmdGet(), "藥水")
        self.assertIn("你撿起了藥水。", output)
        self.assertEqual(self.char1.db.inventory, [_POTION])

    def test_get_stacked_registry_objects_add_one_key_per_object(self):
        create_object(
            "typeclasses.objects.Object",
            key=_POTION,
            attributes=[("registry_key", _POTION)],
            location=self.room1,
        )
        create_object(
            "typeclasses.objects.Object",
            key=_POTION,
            attributes=[("registry_key", _POTION)],
            location=self.room1,
        )
        output = self.call(CmdGet(), f"2 個 {_POTION}")
        self.assertIn(f"你撿起了2 個 {_POTION}。", output)
        self.assertEqual(
            self.char1.db.inventory, [_POTION, _POTION]
        )

    def test_drop_stacked_registry_objects_remove_one_key_per_object(self):
        self.char1.db.inventory = [_MEAL_KEY, _MEAL_KEY]
        create_object(
            "typeclasses.objects.Object",
            key=_MEAL_KEY,
            attributes=[("registry_key", _MEAL_KEY)],
            location=self.char1,
        )
        create_object(
            "typeclasses.objects.Object",
            key=_MEAL_KEY,
            attributes=[("registry_key", _MEAL_KEY)],
            location=self.char1,
        )
        output = self.call(CmdDrop(), f"2 個 {_MEAL_KEY}")
        self.assertIn(f"你丟下了2 個 {_MEAL_KEY}。", output)
        self.assertEqual(self.char1.db.inventory, [])
        self.assertEqual(len([o for o in self.room1.contents if o.key == _MEAL_KEY]), 2)

    def test_drop_registry_object_without_canonical_key_is_refused(self):
        create_object(
            "typeclasses.objects.Object",
            key=_MEAL_KEY,
            attributes=[("registry_key", _MEAL_KEY)],
            location=self.char1,
        )
        output = self.call(CmdDrop(), _MEAL_KEY)
        self.assertIn(f"你沒有帶著 {_MEAL_KEY}。", output)
        self.assertIsNone(self.char1.db.inventory)
        self.assertEqual(len([o for o in self.char1.contents if o.key == _MEAL_KEY]), 1)

    @covers_requirement("equipment-inventory::localized-item-commands-synchronize-containment-and-the-key-list")
    def test_get_non_registry_object_keeps_inventory_unchanged(self):
        create_object("typeclasses.objects.Object", key="銅幣", location=self.room1)
        output = self.call(CmdGet(), "銅幣")
        self.assertIn("你撿起了銅幣。", output)
        self.assertIsNone(self.char1.db.inventory)

    def test_drop_non_registry_object_keeps_inventory_unchanged(self):
        create_object("typeclasses.objects.Object", key="銅幣", location=self.char1)
        output = self.call(CmdDrop(), "銅幣")
        self.assertIn("你丟下了銅幣。", output)
        self.assertIsNone(self.char1.db.inventory)

    @covers_requirement("equipment-inventory::localized-item-commands-synchronize-containment-and-the-key-list")
    def test_drop_registry_object_removes_the_canonical_key(self):
        self.char1.db.inventory = [_MEAL_KEY]
        create_object(
            "typeclasses.objects.Object",
            key=_MEAL_KEY,
            attributes=[("registry_key", _MEAL_KEY)],
            location=self.char1,
        )
        output = self.call(CmdDrop(), _MEAL_KEY)
        self.assertIn(f"你丟下了{_MEAL_KEY}。", output)
        self.assertEqual(self.char1.db.inventory, [])
        self.assertEqual(len([o for o in self.room1.contents if o.key == _MEAL_KEY]), 1)

    @covers_requirement("equipment-inventory::localized-item-commands-synchronize-containment-and-the-key-list")
    def test_give_registry_object_transfers_the_canonical_key(self):
        self.char1.db.inventory = [_MEAL_KEY]
        self.char2.location = self.room1
        create_object(
            "typeclasses.objects.Object",
            key=_MEAL_KEY,
            attributes=[("registry_key", _MEAL_KEY)],
            location=self.char1,
        )
        output = self.call(CmdGive(), f"{_MEAL_KEY} = 路人")
        self.assertIn(f"你把{_MEAL_KEY}交給了", output)
        self.assertEqual(self.char1.db.inventory, [])
        self.assertEqual(self.char2.db.inventory, [_MEAL_KEY])
        self.assertEqual(len([o for o in self.char2.contents if o.key == _MEAL_KEY]), 1)

    def test_give_registry_object_to_npc_adds_the_canonical_key(self):
        self.char1.db.inventory = [_MEAL_KEY]
        npc = create_object(NPC, key="阿諾", location=self.room1)
        create_object(
            "typeclasses.objects.Object",
            key=_MEAL_KEY,
            attributes=[("registry_key", _MEAL_KEY)],
            location=self.char1,
        )
        output = self.call(CmdGive(), f"{_MEAL_KEY} = 阿諾")
        self.assertIn(f"你把{_MEAL_KEY}交給了", output)
        self.assertEqual(self.char1.db.inventory, [])
        self.assertEqual(npc.db.inventory, [_MEAL_KEY])
        self.assertEqual(len([o for o in npc.contents if o.key == _MEAL_KEY]), 1)

    def test_drop_canonical_key_without_object_materializes_the_mirror(self):
        self.char1.db.inventory = [_MEAL_KEY]
        output = self.call(CmdDrop(), _MEAL_KEY)
        self.assertIn(f"你丟下了{_MEAL_KEY}。", output)
        self.assertEqual(self.char1.db.inventory, [])
        mirrored = [o for o in self.room1.contents if o.key == _MEAL_KEY]
        self.assertEqual(len(mirrored), 1)
        self.assertEqual(mirrored[0].db.registry_key, _MEAL_KEY)

    def test_give_canonical_key_without_object_materializes_at_target(self):
        self.char1.db.inventory = [_MEAL_KEY]
        self.char2.location = self.room1
        output = self.call(CmdGive(), f"{_MEAL_KEY} = 路人")
        self.assertIn(f"你把{_MEAL_KEY}交給了", output)
        self.assertEqual(self.char1.db.inventory, [])
        self.assertEqual(self.char2.db.inventory, [_MEAL_KEY])
        mirrored = [o for o in self.char2.contents if o.key == _MEAL_KEY]
        self.assertEqual(len(mirrored), 1)
        self.assertEqual(mirrored[0].db.registry_key, _MEAL_KEY)

    def test_give_to_self_with_canonical_key_keeps_it(self):
        self.char1.db.inventory = [_MEAL_KEY]
        output = self.call(CmdGive(), f"{_MEAL_KEY} = 測試者")
        self.assertIn("留給了", output)
        self.assertEqual(self.char1.db.inventory, [_MEAL_KEY])

    @covers_requirement("equipment-inventory::localized-item-commands-synchronize-containment-and-the-key-list")
    def test_get_failed_move_aborts_the_batch_and_changes_nothing(self):
        first = create_object("typeclasses.objects.Object", key="銅幣", location=self.room1)
        second = create_object("typeclasses.objects.Object", key="銅幣", location=self.room1)
        real_move_to = DefaultObject.move_to
        calls = {"count": 0}

        def fake_move(self, destination, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                return False
            return real_move_to(self, destination, **kwargs)

        with patch.object(DefaultObject, "move_to", fake_move):
            output = self.call(CmdGet(), "2 個 銅幣")
        self.assertIn("那個撿不起來。", output)
        self.assertEqual([first.location, second.location], [self.room1, self.room1])
        self.assertEqual(len([o for o in self.room1.contents if o.key == "銅幣"]), 2)
        self.assertEqual(len([o for o in self.char1.contents if o.key == "銅幣"]), 0)
        self.assertEqual(self.char1.db.inventory or [], [])

    def test_get_exception_mid_transfer_changes_nothing(self):
        first = create_object("typeclasses.objects.Object", key="銅幣", location=self.room1)
        second = create_object("typeclasses.objects.Object", key="銅幣", location=self.room1)
        real_move_to = DefaultObject.move_to
        calls = {"count": 0}

        def fake_move(self, destination, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("move failed")
            return real_move_to(self, destination, **kwargs)

        with patch.object(DefaultObject, "move_to", fake_move):
            with self.assertRaises(RuntimeError):
                self.call(CmdGet(), "2 個 銅幣")
        self.assertEqual([first.location, second.location], [self.room1, self.room1])
        self.assertEqual(len([o for o in self.room1.contents if o.key == "銅幣"]), 2)
        self.assertEqual(len([o for o in self.char1.contents if o.key == "銅幣"]), 0)
        self.assertEqual(self.char1.db.inventory or [], [])

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
