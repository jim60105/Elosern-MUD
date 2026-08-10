"""Tests for the localized appearance layer (localize-limbo-zhtw: localized-appearance)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import InstanceRoom, Room


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
    def test_grid_room_keeps_the_map_display_and_renders_the_flavor_paragraph(self):
        from typeclasses.rooms import GridRoom

        grid, errors = GridRoom.create(key="街道", xyz=(1, 1, "probe_map"))
        self.assertEqual(errors, [])
        grid.db.desc = "鋪著石板的大道。"
        grid.db.scene_flavor = self._FLAVOR
        create_object(
            "typeclasses.exits.Exit",
            key="北門",
            location=grid,
            destination=self.room1,
        )
        appearance = self.char1.at_look(grid)
        self.assertLess(
            appearance.index("鋪著石板的大道。"), appearance.index(self._FLAVOR)
        )
        self.assertLess(appearance.index(self._FLAVOR), appearance.index("出口："))
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
    def test_onboarding_look_beat_still_completes_with_the_block_present(self):
        from world.maps.bootstrap import sync_grid
        from world.rules.onboarding import GUIDANCE_BEAT_ID, LOOK_BEAT_ID

        sync_grid()
        gate = self.room1
        gate.key = "南門"
        gate.save()
        self.char1.location = gate
        self.char1.onboarding_beat = LOOK_BEAT_ID
        self.char1.guide_progress = {"state": "active", "seen_keywords": []}
        self.char1.onboarded = False
        appearance = self.char1.at_look(self.npc)
        self.assertIn("攻擊：60", appearance)
        self.assertTrue(self.char1.first_arrival_seen)
        self.assertEqual(self.char1.onboarding_beat, GUIDANCE_BEAT_ID)
