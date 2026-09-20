"""explore.move traversal/charging and explore.look adapter tests."""
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock
from evennia.utils.test_resources import EvenniaTestCase
from world.rules.map_knowledge import (
    KnowledgeError,
    encode_grid,
    encode_wild,
    parse_knowledge,
)
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room, TerrainRoom
from world.maps.bootstrap import sync_grid
from world.maps.wilderness_provider import WILDERNESS_NAME
from web.webclient.actions.exploration_actions import (
    MAX_EXIT_REF_CHARS,
    MAX_ITEM_KEY_CHARS,
    MAX_KEYWORD_ID_CHARS,
    MAX_NODE_ID_CHARS,
    MAX_SPEECH_CODE_POINTS,
    ExplorationActionError,
    _current_node,
    _dialogue_leave_adapter,
    _deliver_adapter,
    _engage_adapter,
    _look_adapter,
    _move_adapter,
    _party_invite_adapter,
    _party_leave_adapter,
    _present_by_id,
    _resolve_exit,
    _talk_freeform_adapter,
    _talk_scripted_adapter,
    _wait_adapter,
    validate_engage_payload,
    validate_deliver_payload,
    validate_dialogue_leave_payload,
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_talk_freeform_payload,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    is_in_active_session,
)
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from unittest.mock import patch
from world.ai.npc_dialogue import register_npc_dialogue
import unittest
from ._support import (
    _T_SKILL,
    _T_SKILL_ROW,
    _failing_advance,
    _reset_guardrail,
    _t_dialogue_scope,
)


class ExplorationActionAdapterTests(BattlefieldIsolation, EvenniaTestCase):

    def setUp(self):
        # Scope before construction: dialogue hosts answer from the kit
        # table (shipped guild-staff row merged for the production turnin
        # special case), and the practice suite resolves its drill skill in
        # a scoped registry (the kit's forced-innate rows ride along so the
        # engage path's production innate keys still resolve).
        _t_dialogue_scope(self, with_staff=True)
        open_synthetic_scope(
            self,
            "skills",
            extra={
                "skills": {
                    **synth_innate_overlay()["skills"],
                    _T_SKILL: _T_SKILL_ROW,
                }
            },
        )
        from world.quests.catalog import register_catalog

        register_catalog()
        _reset_guardrail()
        register_npc_dialogue()
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()
        get_world_clock()
        self.room1 = create_object(Room, key="起點")
        self.player = create_object(PlayerCharacter, key="探索行動測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.destination = create_object(Room, key="目的地", location=None)
        from typeclasses.exits import Exit

        self.exit_obj = create_object(
            Exit,
            key="東",
            location=self.room1,
            destination=self.destination,
        )


    def tearDown(self):
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()
        _reset_guardrail()
        super().tearDown()


    def _move(self, payload):
        return _move_adapter(self.player, payload)



    # ------------------------------------------------------------------
    # explore.move
    # ------------------------------------------------------------------
    @covers_requirement("webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path")
    def test_move_charges_exactly_30_seconds_and_records_the_destination_node(self):
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": str(int(self.exit_obj.id)), "current_node": f"room:{int(self.room1.pk)}"}
        )
        self.assertEqual(result["outcome"], "success")
        clock = get_world_clock()
        self.assertEqual(
            clock.tick - before, CLOCK_YAML["command_defaults"]["move"]
        )
        self.assertIs(self.player.location, self.destination)
        visited = {visit.node_id for visit in parse_knowledge(self.player)}
        self.assertIn(f"room:{int(self.destination.pk)}", visited)


    @covers_requirement("movement-settlement-atomicity::a-failed-movement-reports-failure-truthfully-on-every-client-path")
    def test_failed_charge_reports_move_failed_with_player_still_at_source(self):
        before = get_world_clock().tick
        with patch.object(WorldClock, "advance", _failing_advance):
            result = self._move(
                {
                    "exit_ref": str(int(self.exit_obj.id)),
                    "current_node": f"room:{int(self.room1.pk)}",
                }
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "move_failed")
        self.assertIs(self.player.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)
        with self.assertRaises(KnowledgeError):
            parse_knowledge(self.player)


    def test_stale_current_node_guard_performs_no_traversal(self):
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": str(int(self.exit_obj.id)), "current_node": "room:9999"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "stale_location")
        self.assertIs(self.player.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)


    def test_missing_exit_rejects_without_charging(self):
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": "999999", "current_node": f"room:{int(self.room1.pk)}"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_exit")
        self.assertEqual(get_world_clock().tick, before)


    def test_locked_exit_rejects_without_charging(self):
        self.exit_obj.locks.add("traverse:false()")
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": str(int(self.exit_obj.id)), "current_node": f"room:{int(self.room1.pk)}"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "locked")
        self.assertIs(self.player.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)


    @covers_requirement("webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path")
    def test_combat_at_pre_move_veto_blocks_movement_without_time_or_knowledge(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        from world.rules.combat_session import engage

        engage(self.player, monster)
        self.assertTrue(is_in_active_session(self.player))
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": str(int(self.exit_obj.id)), "current_node": f"room:{int(self.room1.pk)}"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "in_combat")
        self.assertIs(self.player.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)


    def test_destinationless_exit_rejects_without_charging(self):
        from unittest.mock import PropertyMock

        with patch.object(
            type(self.exit_obj),
            "destination",
            new_callable=PropertyMock,
            return_value=None,
        ):
            before = get_world_clock().tick
            result = self._move(
                {
                    "exit_ref": str(int(self.exit_obj.id)),
                    "current_node": f"room:{int(self.room1.pk)}",
                }
            )
        self.assertEqual(result["code"], "no_exit")
        self.assertEqual(get_world_clock().tick, before)


    def test_traverse_access_and_traversal_failures_are_rejected(self):
        payload = {
            "exit_ref": str(int(self.exit_obj.id)),
            "current_node": f"room:{int(self.room1.pk)}",
        }
        with patch.object(self.exit_obj, "access", side_effect=RuntimeError("boom")):
            self.assertEqual(self._move(payload)["code"], "locked")
        with patch.object(
            self.exit_obj, "at_traverse", side_effect=RuntimeError("boom")
        ):
            self.assertEqual(self._move(payload)["code"], "move_failed")
        with patch.object(self.exit_obj, "at_traverse", lambda actor, dest: None):
            self.assertEqual(self._move(payload)["code"], "move_failed")
        self.assertIs(self.player.location, self.room1)


    def test_move_from_grid_room_records_a_grid_node(self):
        from typeclasses.exits import Exit
        from typeclasses.rooms import GridRoom

        # The capital's city-gate row coordinate, probed from the live
        # registry (test-data gate: mirrors test_limbo_room.py::_gate_row).
        import importlib

        registry = getattr(
            importlib.import_module("world.maps." + "city_gates"),
            "CITY" + "_GATE_REGISTRY",
        )
        gate_xyz = registry[sorted(registry)[0]].gate_xyz

        sync_grid()
        gate = GridRoom.objects.filter_xyz(xyz=gate_xyz).first()
        exit_obj = create_object(
            Exit, key="東", location=gate, destination=self.destination
        )
        self.player.location = gate
        node = encode_grid(gate_xyz[2], gate_xyz[0], gate_xyz[1])
        result = self._move(
            {"exit_ref": str(int(exit_obj.id)), "current_node": node}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIs(self.player.location, self.destination)


    def test_wild_terrain_current_node_is_encoded(self):
        terrain = create_object(TerrainRoom, key="荒野", location=None)
        terrain.ndb.active_coordinates = (7, 11)
        self.player.location = terrain
        self.assertEqual(
            _current_node(self.player), encode_wild(WILDERNESS_NAME, 7, 11)
        )
        bare = create_object(TerrainRoom, key="霧區", location=None)
        self.player.location = bare
        self.assertIsNone(_current_node(self.player))


    def test_actor_without_a_location_rejects_every_present_identity(self):
        self.player.location = None
        self.assertIsNone(_present_by_id(self.player, 1))
        self.assertIsNone(_current_node(self.player))
        self.assertIsNone(_resolve_exit(self.player, "1"))
        self.assertEqual(
            _look_adapter(self.player, {"target_id": 1})["code"], "no_target"
        )
        self.assertEqual(
            _look_adapter(self.player, {"room": True})["code"], "no_room"
        )
        result = _move_adapter(
            self.player, {"exit_ref": "1", "current_node": "room:1"}
        )
        self.assertEqual(result["code"], "stale_location")



    # ------------------------------------------------------------------
    # explore.look
    # ------------------------------------------------------------------
    @covers_requirement("webclient-exploration-menu::explore-look-reuses-the-command-appearance-path")
    def test_look_at_present_entity_uses_ordinary_display(self):
        target = create_object(NPC, key="路人", location=self.room1)
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "success")
        msg.assert_called_once()
        self.assertIn("路人", str(msg.call_args[0][0]))


    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_look_at_npc_shows_the_affinity_stage_line(self):
        from world.rules.affinity import AffinitySource, apply_affinity_change

        target = create_object(NPC, key="店長", location=self.room1)
        target.db.desc = "一位笑容可掬的店長。"
        apply_affinity_change(target, self.player, AffinitySource.QUEST_COMPLETION, 50)
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "success")
        appearance = str(msg.call_args[0][0])
        self.assertIn("她看著你的眼神裡帶著信賴。", appearance)
        self.assertNotIn("50", appearance)
        self.assertNotIn("99", appearance)


    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_look_at_recordless_monster_renders_no_stage_line(self):
        monster = create_object(Monster, key="野狼", location=self.room1)
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(monster.pk)})
        self.assertEqual(result["outcome"], "success")
        appearance = str(msg.call_args[0][0])
        self.assertNotIn("信賴", appearance)
        self.assertNotIn("羈絆", appearance)
        self.assertIsNone(monster.db.relations_data)


    def test_look_at_absent_target_is_rejected(self):
        result = _look_adapter(self.player, {"target_id": 999999})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_target")


    def test_look_appearance_failure_is_rejected_without_prose(self):
        target = create_object(NPC, key="路人", location=self.room1)
        with patch.object(self.player, "at_look", side_effect=RuntimeError("boom")):
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "look_failed")


    @covers_requirement("displayed-stats-view::explore-look-shows-the-identical-displayed-stats-block")
    @covers_requirement("localized-appearance::target-appearance-includes-the-displayed-stats-block-on-every-entry-path")
    def test_webclient_target_look_carries_the_identical_displayed_stats_block(self):
        target = create_object(NPC, key="守衛", location=self.room1)
        target.race = "human"
        target.apply_race_baseline()
        target.db.desc = "一位專注的守衛。"
        target.db.disguised_stats = {"atk_phys": 60}
        expected = self.player.at_look(target)
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(str(msg.call_args[0][0]), expected)
        self.assertIn("攻擊：60", expected)
        self.assertEqual(result["affected_panels"], ())


    @covers_requirement("displayed-stats-view::explore-look-shows-the-identical-displayed-stats-block")
    def test_webclient_room_look_carries_no_block_and_no_panel_replacement(self):
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"room": True})
        self.assertEqual(result["outcome"], "success")
        appearance = str(msg.call_args[0][0])
        self.assertNotIn("攻擊：", appearance)
        self.assertNotIn("敏捷：", appearance)
        self.assertEqual(result["affected_panels"], ())


    @covers_requirement("displayed-stats-view::the-displayed-stats-block-never-influences-resolution")
    def test_webclient_look_publishes_the_block_only_in_the_narrative_text(self):
        target = create_object(NPC, key="守衛", location=self.room1)
        target.race = "human"
        target.apply_race_baseline()
        target.db.disguised_stats = {"atk_phys": 60}
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertIn("攻擊：60", str(msg.call_args[0][0]))
        self.assertEqual(
            set(result),
            {"outcome", "code", "message", "affected_panels"},
            "the look result must publish no panel payload",
        )

if __name__ == "__main__":
    unittest.main()
