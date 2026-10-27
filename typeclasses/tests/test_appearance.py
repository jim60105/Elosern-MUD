"""Tests for the localized appearance layer (localize-limbo-zhtw: localized-appearance)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.contrib.grid.xyzgrid.xymap import XYMap
from evennia.objects.objects import DefaultObject
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, GridRoom, InstanceRoom, Room
from world.tests.synthetic_data import SYNTH_STARTER_EPITHET


class SceneFlavorParagraphTests(EvenniaTest):
    """The scene-flavor paragraph rides the shared room appearance hook."""

    _FLAVOR = "苔石在幽暗中泛著微光，潮濕的氣味與焚香交織，靜得只剩下風的低鳴。"

    def setUp(self):
        super().setUp()
        self.room1.key = "測試房間"
        self.room1.save()
        self.room2.key = "測試房間二"
        self.room2.save()
        self.room1.db.scene_flavor = self._FLAVOR
        create_object(
            "typeclasses.exits.Exit",
            key="南門",
            location=self.room1,
            destination=self.room2,
        )

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames", "scene-flavor::completed-flavor-is-pushed-to-present-players-and-rendered-in-look")
    def test_flavor_paragraph_appears_after_the_description_on_the_text_look_path(self):
        self.room1.db.desc = None
        appearance = self.char1.at_look(self.room1)
        self.assertLess(
            appearance.index("測試房間"), appearance.index("你沒有看到什麼特別的。")
        )
        self.assertLess(
            appearance.index("你沒有看到什麼特別的。"), appearance.index(self._FLAVOR)
        )
        self.assertLess(appearance.index(self._FLAVOR), appearance.index("出口："))
        self.assertNotIn("Exits", appearance)

    def test_flavor_paragraph_appears_after_a_real_description(self):
        self.room1.db.desc = "一間樸素的房間。"
        appearance = self.char1.at_look(self.room1)
        self.assertLess(appearance.index("一間樸素的房間。"), appearance.index(self._FLAVOR))

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames", "scene-flavor::completed-flavor-is-pushed-to-present-players-and-rendered-in-look")
    def test_flavor_paragraph_appears_on_the_webclient_look_path(self):
        from web.webclient.actions.exploration_actions import _look_adapter

        self.char1.location = self.room1
        with patch.object(self.char1, "msg") as msg:
            result = _look_adapter(self.char1, {"room": True})
        self.assertEqual(result["outcome"], "success")
        appearance = str(msg.call_args[0][0])
        self.assertIn(self._FLAVOR, appearance)
        self.assertLess(appearance.index(self._FLAVOR), appearance.index("出口："))

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames", "scene-flavor::completed-flavor-is-pushed-to-present-players-and-rendered-in-look")
    def test_at_look_seam_renders_the_flavor_paragraph(self):
        from world.maps.bootstrap import sync_grid

        sync_grid()
        self.char1.location = self.room1
        appearance = self.char1.at_look(self.room1)
        self.assertIn(self._FLAVOR, appearance)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_flavor_less_room_renders_no_paragraph(self):
        self.room1.db.scene_flavor = None
        appearance = self.char1.at_look(self.room1)
        self.assertNotIn(self._FLAVOR, appearance)
        self.assertIn("出口：", appearance)
        self.assertNotIn("Exits", appearance)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames", "scene-flavor::completed-flavor-is-pushed-to-present-players-and-rendered-in-look")
    def test_instance_room_renders_the_zh_tw_frame_and_the_flavor_paragraph(self):
        instance = create_object(InstanceRoom, key="場景", location=None)
        instance.db.desc = "深邃的洞穴內滴水聲迴盪。"
        instance.db.scene_flavor = self._FLAVOR
        create_object(
            "typeclasses.exits.Exit",
            key="返回",
            location=instance,
            destination=self.room1,
        )
        appearance = self.char1.at_look(instance)
        self.assertLess(
            appearance.index("深邃的洞穴內滴水聲迴盪。"), appearance.index(self._FLAVOR)
        )
        self.assertLess(appearance.index(self._FLAVOR), appearance.index("出口："))
        self.assertNotIn("Exits", appearance)
        self.assertNotIn("Characters", appearance)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_flavor_less_instance_room_adds_no_paragraph(self):
        instance = create_object(InstanceRoom, key="無氛圍場景", location=None)
        instance.db.desc = "深邃的洞穴內滴水聲迴盪。"
        create_object(
            "typeclasses.exits.Exit",
            key="返回",
            location=instance,
            destination=self.room1,
        )
        appearance = self.char1.at_look(instance)
        self.assertNotIn(self._FLAVOR, appearance)
        self.assertIn("出口：", appearance)
        self.assertNotIn("Exits", appearance)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_terrain_room_active_desc_path_survives_the_mixin_adoption(self):
        from typeclasses.rooms import TerrainRoom

        terrain = create_object(TerrainRoom, key="荒野", location=None)
        terrain.db.desc = "固定描述。"
        terrain.db.scene_flavor = self._FLAVOR
        terrain.ndb.active_desc = "準備好的移動描述。"
        desc = terrain.get_display_desc(self.char1)
        self.assertIn("準備好的移動描述。", desc)
        self.assertIn(self._FLAVOR, desc)
        self.assertNotIn("固定描述。", desc)


class GridLookTextMapTests(EvenniaCommandTestMixin, EvenniaTest):
    """Grid-room look emits only the ordinary appearance on every entry path.

    A real loaded synthetic map supplies both room types, a traversable exit
    and visible contents; every emitted ``msg`` call is inspected, so a
    separate ``xymap`` message cannot escape the assertions.
    """

    _FLAVOR = "測試氛圍：遠處傳來一聲鐘響。"

    def setUp(self):
        super().setUp()
        from world.tests.synthetic_grid_map import (
            ANCHOR_DESC,
            START_DESC,
            load_synthetic_grid,
            synthetic_rooms,
        )

        load_synthetic_grid()
        self.start, self.anchor, _end = synthetic_rooms()
        self.descriptions = {self.start.key: START_DESC, self.anchor.key: ANCHOR_DESC}
        self.start.db.scene_flavor = None
        self.anchor.db.scene_flavor = None
        self.start_object = create_object(DefaultObject, key="測試油燈", location=self.start)
        self.anchor_object = create_object(DefaultObject, key="測試告示牌", location=self.anchor)

    @staticmethod
    def _parts(call):
        """Return one emitted ``msg`` call's text and metadata."""
        value = call.kwargs.get("text", call.args[0] if call.args else None)
        metadata = {}
        if isinstance(value, tuple):
            value, metadata = value
        return str(value), dict(metadata or {})

    def _text_look_messages(self, room, cmdstring="看"):
        from commands.localized.general import CmdLook

        self.char1.location = room
        with (
            patch.object(XYMap, "get_visual_range") as visual_range,
            patch.object(self.char1, "msg") as recorder,
        ):
            self.call(
                CmdLook(),
                "",
                caller=self.char1,
                receiver=self.char2,
                cmdstring=cmdstring,
            )
        visual_range.assert_not_called()
        return [self._parts(call) for call in recorder.call_args_list]

    def _assert_no_automatic_map(self, messages):
        self.assertTrue(messages)
        for text, metadata in messages:
            self.assertNotEqual(metadata.get("type"), "xymap", text)
            self.assertNotIn("~", text, "the ASCII map separator leaked into a message")

    def _assert_ordinary_appearance(self, text, room, visible_object):
        self.assertIn(room.key, text)
        self.assertIn(self.descriptions[room.key], text)
        self.assertIn(visible_object.key, text)
        self.assertIn("出口：", text)
        self.assertIn(room.exits[0].key, text)
        self.assertNotIn("Exits:", text)
        self.assertLess(text.index(self.descriptions[room.key]), text.index("出口："))

    def _rooms(self):
        return ((self.start, self.start_object), (self.anchor, self.anchor_object))

    def _assert_appearance(self, text, room, visible_object, *, flavor):
        self._assert_ordinary_appearance(text, room, visible_object)
        if flavor:
            self.assertLess(
                text.index(self.descriptions[room.key]), text.index(self._FLAVOR)
            )
            self.assertLess(text.index(self._FLAVOR), text.index("出口："))
        else:
            self.assertNotIn(self._FLAVOR, text)

    def _at_look(self, room):
        with (
            patch.object(XYMap, "get_visual_range") as visual_range,
            patch.object(self.char1, "msg") as recorder,
        ):
            appearance = self.char1.at_look(room)
        visual_range.assert_not_called()
        recorder.assert_not_called()
        return appearance

    def _adapter_look(self, room):
        from web.webclient.actions.exploration_actions import (
            AFFECTED_FULL,
            _look_adapter,
        )

        self.char1.location = room
        with (
            patch.object(XYMap, "get_visual_range") as visual_range,
            patch.object(self.char1, "msg") as recorder,
        ):
            result = _look_adapter(self.char1, {"room": True})
        visual_range.assert_not_called()
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "looked")
        self.assertEqual(result["affected_panels"], AFFECTED_FULL)
        messages = [self._parts(call) for call in recorder.call_args_list]
        self._assert_no_automatic_map(messages)
        self.assertEqual(len(messages), 1)
        return messages[0][0]

    def _appearance_on_every_path(self, room, visible_object, *, flavor):
        """Return the appearance all three entry paths agree on."""
        text_messages = self._text_look_messages(room)
        self._assert_no_automatic_map(text_messages)
        self.assertEqual(len(text_messages), 1)
        text = text_messages[0][0]
        self._assert_appearance(text, room, visible_object, flavor=flavor)

        # Direct hook and browser action carry the same ordinary appearance;
        # the command alone wraps it in the `type: look` envelope.
        appearance = self._at_look(room)
        self.assertEqual(appearance, text)
        self._assert_appearance(appearance, room, visible_object, flavor=flavor)
        self.assertEqual(self._adapter_look(room), text)
        return text

    @covers_requirement("localized-appearance::grid-room-look-emits-the-ordinary-appearance-without-an-automatic-ascii-map")
    def test_grid_room_text_look_emits_only_the_ordinary_appearance(self):
        self.assertTrue(self.start.xymap, "the fixture map must be loaded")
        self.assertIsInstance(self.start, GridRoom)
        messages = self._text_look_messages(self.start)
        self._assert_no_automatic_map(messages)
        self.assertEqual(len(messages), 1)
        text, metadata = messages[0]
        self.assertEqual(metadata.get("type"), "look")
        self._assert_ordinary_appearance(text, self.start, self.start_object)

    @covers_requirement("localized-appearance::grid-room-look-emits-the-ordinary-appearance-without-an-automatic-ascii-map")
    def test_anchor_room_text_look_emits_no_map_message(self):
        self.assertTrue(self.anchor.xymap, "the fixture map must be loaded")
        self.assertIsInstance(self.anchor, AnchorRoom)
        messages = self._text_look_messages(self.anchor)
        self._assert_no_automatic_map(messages)
        self.assertEqual(len(messages), 1)
        self._assert_ordinary_appearance(messages[0][0], self.anchor, self.anchor_object)

    @covers_requirement("localized-appearance::grid-room-look-emits-the-ordinary-appearance-without-an-automatic-ascii-map")
    def test_english_look_alias_emits_no_map_message(self):
        for room, visible_object in self._rooms():
            with self.subTest(room=room.key):
                messages = self._text_look_messages(room, cmdstring="look")
                self._assert_no_automatic_map(messages)
                self.assertEqual(len(messages), 1)
                self._assert_ordinary_appearance(messages[0][0], room, visible_object)

    @covers_requirement("localized-appearance::grid-room-look-emits-the-ordinary-appearance-without-an-automatic-ascii-map")
    def test_direct_at_look_emits_no_map_side_message(self):
        for room, visible_object in self._rooms():
            with self.subTest(room=room.key):
                appearance = self._at_look(room)
                self._assert_ordinary_appearance(appearance, room, visible_object)

    @covers_requirement("localized-appearance::grid-room-look-emits-the-ordinary-appearance-without-an-automatic-ascii-map")
    def test_browser_look_adapter_emits_no_map_message(self):
        for room, visible_object in self._rooms():
            with self.subTest(room=room.key):
                text_messages = self._text_look_messages(room)
                self._assert_no_automatic_map(text_messages)
                # The envelope differs (command metadata vs. a plain string);
                # the appearance itself must be the same ordinary room text.
                self.assertEqual(self._adapter_look(room), text_messages[0][0])
                self._assert_ordinary_appearance(text_messages[0][0], room, visible_object)

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames", "localized-appearance::grid-room-look-emits-the-ordinary-appearance-without-an-automatic-ascii-map")
    def test_scene_flavor_and_ordinary_content_survive_without_a_map(self):
        for room, visible_object in self._rooms():
            with self.subTest(room=room.key, flavor=False):
                room.db.scene_flavor = None
                flavorless = self._appearance_on_every_path(
                    room, visible_object, flavor=False
                )
            with self.subTest(room=room.key, flavor=True):
                room.db.scene_flavor = self._FLAVOR
                flavored = self._appearance_on_every_path(
                    room, visible_object, flavor=True
                )
                # The flavor paragraph is the only difference between the two
                # appearances: contents, exit frame and ordering are intact.
                self.assertEqual(
                    [
                        line
                        for line in flavored.splitlines()
                        if line.strip() and self._FLAVOR not in line
                    ],
                    [line for line in flavorless.splitlines() if line.strip()],
                )

    def test_loaded_map_would_emit_an_ascii_map_under_an_explicit_override(self):
        # Positive control: the fixture really is a loaded map and the class
        # default is what suppresses the automatic rendering.
        with patch.object(self.char1, "msg") as recorder:
            self.char1.at_look(self.start, map_display=True)
        messages = [self._parts(call) for call in recorder.call_args_list]
        self.assertEqual(len(messages), 1)
        text, metadata = messages[0]
        self.assertEqual(metadata.get("type"), "xymap")
        self.assertIn("~", text)


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
        from world.quests.catalog import register_catalog

        register_catalog()
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


class DisplayedStatsBlockTests(EvenniaTest):
    """The displayed-stats block rides the shared target-appearance path."""

    def setUp(self):
        super().setUp()
        # Register the quest catalog in this class's own setup: the affinity
        # rulebook load resolves ``introductory_hunt`` from the definition
        # registry, so this class must not depend on an earlier test to have
        # registered it (mirrors ``AffinityStageLineTests``).
        from world.quests.catalog import register_catalog

        register_catalog()
        self.room1.key = "測試房間"
        self.room1.save()
        self.char1.location = self.room1
        self.npc = create_object("typeclasses.npcs.NPC", key="守衛", location=self.room1)
        self.npc.race = "human"
        self.npc.apply_race_baseline()
        self.npc.db.desc = "一位專注的守衛。"
        # Disguise the attack so the block visibly uses displayed values.
        self.npc.db.disguised_stats = {"atk_phys": 60}

    @covers_requirement("displayed-stats-view::look-target-appends-the-displayed-stats-block-room-look-never-does")
    def test_text_look_at_living_target_appends_the_block_after_the_description(self):
        appearance = self.char1.at_look(self.npc)
        self.assertIn("一位專注的守衛。", appearance)
        self.assertIn("攻擊：60", appearance)
        self.assertLess(
            appearance.index("一位專注的守衛。"), appearance.index("攻擊：60")
        )

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_block_ordering_is_description_then_block_then_affinity_stage_line(self):
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(
            self.npc, self.char1, AffinitySource.QUEST_COMPLETION, 50
        )
        appearance = self.char1.at_look(self.npc)
        self.assertLess(
            appearance.index("一位專注的守衛。"), appearance.index("攻擊：60")
        )
        self.assertLess(
            appearance.index("攻擊：60"),
            appearance.index("她看著你的眼神裡帶著信賴。"),
        )

    @covers_requirement("displayed-stats-view::look-target-appends-the-displayed-stats-block-room-look-never-does")
    def test_player_and_monster_targets_show_the_block(self):
        self.char2.race = "human"
        self.char2.apply_race_baseline()
        self.char2.location = self.room1
        player_appearance = self.char1.at_look(self.char2)
        self.assertIn("攻擊：", player_appearance)
        monster = create_object(
            "typeclasses.monsters.Monster", key="野狼", location=self.room1
        )
        monster.threat_tier = "low"
        monster.apply_monster_tier()
        monster_appearance = self.char1.at_look(monster)
        self.assertIn("攻擊：", monster_appearance)

    @covers_requirement("displayed-stats-view::look-target-appends-the-displayed-stats-block-room-look-never-does")
    def test_room_look_has_no_block(self):
        appearance = self.char1.at_look(self.room1)
        self.assertNotIn("攻擊：", appearance)
        self.assertNotIn("敏捷：", appearance)

    @covers_requirement("displayed-stats-view::look-target-appends-the-displayed-stats-block-room-look-never-does")
    def test_non_living_object_target_has_no_block(self):
        thing = create_object(
            "typeclasses.objects.Object", key="石頭", location=self.room1
        )
        appearance = self.char1.at_look(thing)
        self.assertNotIn("攻擊：", appearance)

    @covers_requirement("displayed-stats-view::display-stat-block-renders-the-displayed-combat-five-through-the-disguise-accessor")
    def test_block_reads_displayed_values_never_true_values(self):
        self.npc.traits.atk_phys.base = 88
        appearance = self.char1.at_look(self.npc)
        self.assertIn("攻擊：60", appearance)
        self.assertNotIn("攻擊：88", appearance)

    @covers_requirement("displayed-stats-view::look-target-appends-the-displayed-stats-block-room-look-never-does")
    def test_at_look_through_the_ordinary_seam_appends_the_block(self):
        self.char1.location = self.room1
        appearance = self.char1.at_look(self.npc)
        self.assertIn("攻擊：60", appearance)


class PersonaBlockLookTests(EvenniaTest):
    """The persona block rides the shared look appearance path (persona-store)."""

    _PERSONA = {
        "identity": {},
        "personality": "沉穩",
        "life_story": "來自邊境的小村",
        "habit": "清晨練劍",
        "appearance": {},
        "social_connection": {},
        "background": "在公會登記的新人冒險者",
    }

    def setUp(self):
        super().setUp()
        self.room1.key = "測試房間"
        self.room1.save()
        self.char1.location = self.room1
        self.char1.db.persona = dict(self._PERSONA)
        self.npc = create_object("typeclasses.npcs.NPC", key="店長", location=self.room1)
        self.npc.db.persona = dict(self._PERSONA)
        self.npc.db.desc = "一位笑容可掬的店長。"

    @covers_requirement("persona-store::the-look-appearance-path-renders-a-living-entity-s-persona-block")
    def test_looking_at_yourself_shows_the_persona_block(self):
        appearance = self.char1.at_look(self.char1)
        self.assertIn("性格：沉穩", appearance)
        self.assertIn("背景：在公會登記的新人冒險者", appearance)

    @covers_requirement("persona-store::the-look-appearance-path-renders-a-living-entity-s-persona-block")
    def test_looking_at_another_player_shows_that_character_s_persona_block(self):
        self.char2.race = "human"
        self.char2.apply_race_baseline()
        self.char2.location = self.room1
        self.char2.db.persona = {
            "identity": {},
            "personality": "開朗",
            "life_story": "來自北方",
            "habit": "清晨慢跑",
            "appearance": {},
            "social_connection": {},
            "background": "另一位冒險者的背景",
        }
        appearance = self.char1.at_look(self.char2)
        self.assertIn("性格：開朗", appearance)
        self.assertIn("背景：另一位冒險者的背景", appearance)
        # The looker's own block is not the target's.
        self.assertNotIn("背景：在公會登記的新人冒險者", appearance)

    @covers_requirement("persona-store::the-look-appearance-path-renders-a-living-entity-s-persona-block")
    def test_looking_at_an_npc_shows_its_persona_block(self):
        appearance = self.char1.at_look(self.npc)
        self.assertIn("性格：沉穩", appearance)
        self.assertIn("背景：在公會登記的新人冒險者", appearance)

    @covers_requirement("persona-store::the-look-appearance-path-renders-a-living-entity-s-persona-block")
    def test_looking_at_the_room_or_an_object_omits_any_persona_block(self):
        room_appearance = self.char1.at_look(self.room1)
        self.assertNotIn("性格：", room_appearance)
        self.assertNotIn("背景：", room_appearance)
        thing = create_object(
            "typeclasses.objects.Object", key="石頭", location=self.room1
        )
        object_appearance = self.char1.at_look(thing)
        self.assertNotIn("性格：", object_appearance)
        self.assertNotIn("背景：", object_appearance)

    @covers_requirement("persona-store::the-look-appearance-path-renders-a-living-entity-s-persona-block")
    def test_persona_less_entity_renders_no_block(self):
        monster = create_object(
            "typeclasses.monsters.Monster", key="野狼", location=self.room1
        )
        monster.threat_tier = "low"
        monster.apply_monster_tier()
        appearance = self.char1.at_look(monster)
        self.assertNotIn("性格：", appearance)
        self.assertNotIn("背景：", appearance)


class TitleAppearanceLineTests(EvenniaTest):
    """The composed full title reads as the entity's public 稱號 line (D6).

    Looking at a titled entity shows one 「稱號：全銜」 line between the
    displayed-stats block and the persona block; an untitled entity — or one
    whose title state is malformed — renders exactly the pre-title appearance,
    and the byte-pinned displayed-stats rows never change.
    """

    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        # The composed 稱號 line reads the banked epithet; the starter seam is
        # swapped for the shared synthetic declaration so the line is asserted
        # without pinning the shipped display spelling.
        starter_seam = patch(
            "world.lore.titles.STARTER_EPITHET", SYNTH_STARTER_EPITHET
        )
        starter_seam.start()
        self.addCleanup(starter_seam.stop)
        register_catalog()
        self.room1.key = "測試房間"
        self.room1.save()
        self.char1.location = self.room1
        self.target = create_object(
            "typeclasses.characters.PlayerCharacter",
            key="稱號持有者",
            location=self.room1,
        )
        self.target.race = "human"
        self.target.apply_race_baseline()
        self.target.db.desc = "一位沉默的旅人。"

    def test_an_untitled_entity_renders_no_title_line(self):
        appearance = self.char1.at_look(self.target)
        self.assertIn("一位沉默的旅人。", appearance)
        self.assertNotIn("稱號：", appearance)

    @covers_requirement("title-system::narrative-consumers-compose-predicates-read-the-collection")
    def test_a_titled_entity_shows_the_composed_full_title(self):
        from world.rules.titles import award_first_quest_epithet, award_guild_rank_title

        award_guild_rank_title(self.target, "F", source_id="test:init:rank:F")

        award_first_quest_epithet(self.target, source_id="test:init:first_quest")
        appearance = self.char1.at_look(self.target)
        self.assertIn(f"稱號：F級冒險者　{SYNTH_STARTER_EPITHET.display}", appearance)

    def test_the_line_follows_the_description_and_the_displayed_stats_block(self):
        from world.rules.titles import award_first_quest_epithet, award_guild_rank_title

        award_guild_rank_title(self.target, "F", source_id="test:init:rank:F")

        award_first_quest_epithet(self.target, source_id="test:init:first_quest")
        appearance = self.char1.at_look(self.target)
        self.assertLess(
            appearance.index("一位沉默的旅人。"), appearance.index("稱號：")
        )
        self.assertLess(appearance.index("攻擊："), appearance.index("稱號："))

    def test_the_displayed_stats_block_is_untouched_by_titles(self):
        from world.rules.displayed_stats import display_stat_block

        from world.rules.titles import award_first_quest_epithet, award_guild_rank_title

        before = display_stat_block(self.target, looker=self.char1)
        award_guild_rank_title(self.target, "F", source_id="test:init:rank:F")
        award_first_quest_epithet(self.target, source_id="test:init:first_quest")
        self.assertEqual(display_stat_block(self.target, looker=self.char1), before)
        self.assertNotIn("稱號", before)

    def test_the_title_line_reaches_the_webclient_look_path_too(self):
        from unittest.mock import patch as _patch

        from web.webclient.actions.exploration_actions import _look_adapter

        from world.rules.titles import award_first_quest_epithet, award_guild_rank_title

        award_guild_rank_title(self.target, "F", source_id="test:init:rank:F")

        award_first_quest_epithet(self.target, source_id="test:init:first_quest")
        with _patch.object(self.char1, "msg") as msg:
            result = _look_adapter(self.char1, {"target_id": int(self.target.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertIn(
            f"稱號：F級冒險者　{SYNTH_STARTER_EPITHET.display}",
            str(msg.call_args[0][0]),
        )

    def test_malformed_title_state_degrades_to_the_untitled_appearance(self):
        from world.rules.titles import award_first_quest_epithet, award_guild_rank_title

        baseline = self.char1.at_look(self.target)
        award_guild_rank_title(self.target, "F", source_id="test:init:rank:F")
        award_first_quest_epithet(self.target, source_id="test:init:first_quest")
        self.target.attributes.add("title_collection", "damaged")
        self.assertEqual(self.char1.at_look(self.target), baseline)


class NPCTitleAppearanceTests(EvenniaCommandTestMixin, EvenniaTest):
    """Every text appearance surface renders the plain authored name.

    A stored title is inert: the room character line, the look header, the
    webclient ``explore.look`` seam and the real 「看 <目標>」 command all read
    the plain key, and no reader consults the stored attribute at all.
    """

    def setUp(self):
        super().setUp()
        self.room1.key = "南門廣場"
        self.room1.save()
        self.char1.location = self.room1
        self.char2.location = self.room1
        self.sentinel = create_object(
            "typeclasses.npcs.NPC", key="塞提斯", location=self.room1
        )
        self.sentinel.attributes.add("npc_title", "南門守衛")
        self.plain = create_object(
            "typeclasses.npcs.NPC", key="布魯諾", location=self.room1
        )
        self.monster = create_object(
            "typeclasses.monsters.Monster", key="野狼", location=self.room1
        )

    @covers_requirement('npc-identity-titles::every-npc-identity-surface-uses-the-plain-authored-name')
    def test_room_character_line_renders_plain_names_only(self):
        appearance = self.char1.at_look(self.room1)
        self.assertIn("人物：", appearance)
        for name in ("塞提斯", "布魯諾", "野狼", self.char2.key):
            self.assertIn(name, appearance)
            self.assertNotIn(f"{name}\u3000", appearance)
        self.assertNotIn("南門守衛", appearance)

    @covers_requirement('npc-identity-titles::the-existing-appearance-and-exploration-contracts-are-unchanged')
    def test_look_header_is_plain_on_every_entry_path(self):
        from commands.localized.general import CmdLook
        from evennia.utils import ansi

        text = self.char1.at_look(self.sentinel)
        self.assertIn("塞提斯", text)
        self.assertNotIn("南門守衛", text)
        from web.webclient.actions.exploration_actions import _look_adapter

        with patch.object(self.char1, "msg") as msg:
            result = _look_adapter(self.char1, {"target_id": int(self.sentinel.pk)})
        self.assertEqual(result["outcome"], "success")
        webclient = str(msg.call_args[0][0])
        # Same object, same looker, same framework: the headers must be equal.
        self.assertEqual(text, webclient)
        # Third path: the real 「看 <目標>」 command resolves by the plain key
        # and renders the same appearance (the localized-appearance contract
        # names all three entry paths, not just the two seams above).
        command = self.call(CmdLook(), "塞提斯", msg=None)
        self.assertIn("塞提斯", command)
        self.assertNotIn("南門守衛", command)
        # self.call strips ANSI (noansi default); normalize the seam string the
        # same way so the three paths compare on identical rendered text. The
        # 「看 <NPC>」 command additionally appends the selected NPC's service
        # report (npc-service-text-parity), so the header it starts with is
        # what must match the two appearance seams.
        header = ansi.parse_ansi(text, strip_ansi=True).strip()
        self.assertTrue(
            command.startswith(header),
            "the 看 <NPC> header must match the appearance seams",
        )
        self.assertNotEqual(
            command,
            header,
            "看 <NPC> appends the NPC's service report after the header",
        )

    def test_untitled_and_plain_targets_keep_their_headers(self):
        self.assertIn("布魯諾", self.char1.at_look(self.plain))
        self.assertNotIn("\u3000", self.char1.at_look(self.plain))
        self.assertNotIn("\u3000", self.char1.at_look(self.monster))
        self.assertNotIn("\u3000", self.char1.at_look(self.char2))

    def test_looking_at_an_npc_carrying_characters_raises_nothing(self):
        self.plain.location = self.sentinel
        appearance = self.char1.at_look(self.sentinel)
        self.assertIn("塞提斯", appearance)
        self.assertIn("布魯諾", appearance)


class NPCTitleEchoRegressionTests(EvenniaCommandTestMixin, EvenniaTest):
    """Process text (move/say/whisper/get/give) names the NPC by plain key only.

    Each case renders once with a historical title stored in the raw attribute,
    asserting no title text or separator reaches the echo.
    """

    def setUp(self):
        super().setUp()
        self.room1.key = "南門廣場"
        self.room1.save()
        self.char1.location = self.room1
        self.npc = create_object("typeclasses.npcs.NPC", key="塞提斯", location=self.room1)

    def _texts(self, msg_mock):
        texts = []
        for call in msg_mock.call_args_list:
            payload = call.args[0] if call.args else call.kwargs.get("text")
            if isinstance(payload, tuple):
                payload = payload[0]
            texts.append(str(payload))
        return texts

    def _with_stored_title(self, emit, receiver=None):
        """Capture ``emit`` with a historical stored title on the speaker."""
        receiver = receiver if receiver is not None else self.char1
        self.npc.attributes.add("npc_title", "南門守衛")
        with patch.object(receiver, "msg") as sentinel_msg:
            emit()
        texts = self._texts(sentinel_msg)
        self.assertTrue(texts, "the echo captured no message at all")
        for text in texts:
            self.assertNotIn("南門守衛", text)
            self.assertNotIn("\u3000", text)

    def test_movement_announcements_stay_plain(self):
        def move_round_trip():
            self.npc.move_to(self.room2)
            self.npc.move_to(self.room1)

        self._with_stored_title(move_round_trip)

    def test_say_location_echo_stays_plain(self):
        def say():
            self.npc.at_say(
                "這裡有動靜。", msg_self=None, msg_location="{object} 說：「{speech}」"
            )

        self._with_stored_title(say)

    def test_whisper_receiver_echo_stays_plain(self):
        def whisper():
            self.npc.at_say(
                "秘密。",
                msg_self=None,
                msg_receivers="{object} 悄聲對你說：「{speech}」",
                msg_location=None,
                receivers=[self.char1],
                whisper=True,
            )

        self._with_stored_title(whisper)

    def test_pickup_echo_stays_plain(self):
        # The localized 拿 command's room echo is the observed surface (the
        # at_get hook itself is silent in Evennia 6.1).
        from commands.localized import CmdGet

        coin = create_object("typeclasses.objects.Object", key="銅幣", location=self.room1)

        def pickup():
            coin.location = self.room1
            self.call(CmdGet(), "銅幣", caller=self.npc)

        self._with_stored_title(pickup)

    def test_give_echo_stays_plain(self):
        # The receiver's echo renders the giver's display name (the localized
        # 給 command emits no third-party broadcast; at_give is silent).
        from commands.localized import CmdGive

        coin = create_object("typeclasses.objects.Object", key="銅幣", location=self.npc)
        self.char2.location = self.room1

        def give():
            coin.location = self.npc
            self.call(CmdGive(), f"銅幣 = {self.char2.key}", caller=self.npc)

        self._with_stored_title(give, receiver=self.char2)
