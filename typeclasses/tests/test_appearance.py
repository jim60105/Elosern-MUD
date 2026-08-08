"""Tests for the localized appearance layer (localize-limbo-zhtw: localized-appearance)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import Room


class LocalizedAppearanceTests(EvenniaTest):
    """The shared appearance frame is zh-tw for every entry path."""

    def setUp(self):
        super().setUp()
        self.room1.key = "測試房間"
        self.room1.save()
        self.room2.key = "測試房間二"
        self.room2.save()
        self.exit_obj = create_object(
            "typeclasses.exits.Exit",
            key="南門",
            location=self.room1,
            destination=self.room2,
        )
        self.thing = create_object(
            "typeclasses.objects.Object", key="銅幣", location=self.room1
        )

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_text_look_shows_zh_tw_frame(self):
        appearance = self.char1.at_look(self.room1)

        self.assertIn("測試房間", appearance)
        self.assertIn("出口：", appearance)
        self.assertIn("南門", appearance)
        self.assertIn("你看見：", appearance)
        self.assertIn("銅幣", appearance)
        self.assertNotIn("Exits", appearance)
        self.assertNotIn("Characters", appearance)
        self.assertNotIn("You see", appearance)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_webclient_look_action_shows_the_same_zh_tw_frame(self):
        from web.webclient.actions.exploration_actions import _look_adapter

        with patch.object(self.char1, "msg") as msg:
            result = _look_adapter(self.char1, {"room": True})
        self.assertEqual(result["outcome"], "success")
        appearance = str(msg.call_args[0][0])
        self.assertIn("出口：", appearance)
        self.assertIn("南門", appearance)
        self.assertIn("你看見：", appearance)
        self.assertNotIn("Exits", appearance)
        self.assertNotIn("You see", appearance)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_character_and_grouped_things_lines_are_zh_tw(self):
        self.char1.location = self.room1
        create_object(
            "typeclasses.objects.Object", key="銅幣", location=self.room1
        )
        create_object("typeclasses.characters.Character", key="路人", location=self.room1)

        appearance = self.char1.at_look(self.room1)

        self.assertIn("人物：", appearance)
        self.assertIn("路人", appearance)
        self.assertIn("2 個 銅幣", appearance)
        self.assertNotIn("Characters:", appearance)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_default_description_is_zh_tw(self):
        bare = create_object("typeclasses.objects.Object", key="無描述之物", location=None)
        self.assertEqual(bare.db.desc, None)
        self.assertEqual(bare.get_display_desc(self.char1), "你沒有看到什麼特別的。")


class AffinityStageLineTests(EvenniaTest):
    """The NPC affinity stage line renders identically on every entry path."""

    def setUp(self):
        super().setUp()
        self.room1.key = "測試房間"
        self.room1.save()
        self.char1.location = self.room1
        self.npc = create_object("typeclasses.npcs.NPC", key="店長", location=self.room1)
        self.npc.db.desc = "一位笑容可掬的店長。"
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(
            self.npc, self.char1, AffinitySource.QUEST_COMPLETION, 50
        )

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames", "affinity-system::affinity-presentation-is-stage-only-and-never-exposes-the-numeric-value")
    def test_stage_line_appears_on_the_text_look_path(self):
        appearance = self.char1.at_look(self.npc)
        self.assertIn("她看著你的眼神裡帶著信賴。", appearance)
        self.assertIn("店長", appearance)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_stage_line_appears_on_the_webclient_look_path(self):
        from web.webclient.actions.exploration_actions import _look_adapter

        with patch.object(self.char1, "msg") as msg:
            result = _look_adapter(self.char1, {"target_id": int(self.npc.pk)})
        self.assertEqual(result["outcome"], "success")
        appearance = str(msg.call_args[0][0])
        self.assertIn("她看著你的眼神裡帶著信賴。", appearance)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_no_stage_line_and_no_persistence_for_recordless_entities(self):
        plain = create_object("typeclasses.npcs.NPC", key="路人", location=self.room1)
        plain.db.desc = "一位普通的旅人。"
        monster = create_object(
            "typeclasses.monsters.Monster", key="野狼", location=self.room1
        )
        appearance = self.char1.at_look(plain)
        self.assertNotIn("信賴", appearance)
        self.assertNotIn("羈絆", appearance)
        monster_appearance = self.char1.at_look(monster)
        self.assertNotIn("羈絆", monster_appearance)
        self.assertIsNone(plain.db.relations_data)
        self.assertIsNone(monster.db.relations_data)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_no_numeric_affinity_value_appears_anywhere(self):
        for path in ("at_look", "get_display_desc"):
            appearance = getattr(self.char1, path)(self.npc)
            self.assertNotIn("50", appearance)
            self.assertNotIn("99", appearance)
            self.assertNotIn("70", appearance)
            self.assertNotIn("cap", appearance)
