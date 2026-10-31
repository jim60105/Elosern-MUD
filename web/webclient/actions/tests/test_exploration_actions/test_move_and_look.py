"""explore.move traversal/charging and explore.look adapter tests."""
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
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
from unittest.mock import PropertyMock, patch
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

    def _settled(self, payload):
        """Run one move and execute the commit callbacks its success waits for.

        A wilderness step releases its result only when the movement-owning
        transaction commits. The test harness queues that callback until the
        capture block exits, exactly as production commits inside
        ``settle_movement`` before the adapter returns.
        """
        from twisted.internet.defer import Deferred

        with self.captureOnCommitCallbacks(execute=True):
            result = self._move(payload)
        if isinstance(result, Deferred):
            self.assertTrue(
                result.called, "the committed step must release its result"
            )
            return result.result
        return result



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


    @covers_requirement("webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path")
    def test_coordinate_change_in_a_reused_wilderness_room_reports_success(self):
        room = create_object(TerrainRoom, key="測試荒野房間")
        self.player.location = room
        self.exit_obj.location = room
        self.exit_obj.destination = room
        coordinates = [1, 1]

        def traverse(actor, destination):
            self.assertIs(actor.location, destination)
            coordinates[1] += 1

        with patch.object(
            TerrainRoom, "coordinates", new_callable=PropertyMock,
            side_effect=lambda: tuple(coordinates),
        ), patch.object(self.exit_obj, "at_traverse", traverse):
            source = _current_node(self.player)
            result = self._settled(
                {"exit_ref": str(int(self.exit_obj.id)), "current_node": source}
            )
            self.assertEqual(result["outcome"], "success")
            self.assertEqual(result["code"], "moved")
            # The canonical-coordinate success is a wilderness step, so the
            # result carries its interrupt slot; this patched traversal never
            # runs the settlement, so there is nothing to compare and the
            # legal empty list rides along.
            self.assertEqual(result["data"], {"interrupts": []})
            self.assertNotEqual(_current_node(self.player), source)
            self.assertIs(self.player.location, room)

    def test_unreadable_coordinates_in_a_reused_room_do_not_report_success(self):
        room = create_object(TerrainRoom, key="測試荒野房間")
        self.player.location = room
        self.exit_obj.location = room
        self.exit_obj.destination = room
        with patch.object(
            TerrainRoom, "coordinates", new_callable=PropertyMock,
            side_effect=[(1, 1), None],
        ), patch.object(self.exit_obj, "at_traverse", lambda actor, destination: None):
            result = self._move(
                {
                    "exit_ref": str(int(self.exit_obj.id)),
                    "current_node": encode_wild(WILDERNESS_NAME, 1, 1),
                }
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "move_failed")
        self.assertIs(self.player.location, room)

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
        from world.maps.static_references import settlement_node_xyz

        gate_xyz = settlement_node_xyz(registry[sorted(registry)[0]].gate)

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


    @covers_requirement("webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path")
    def test_move_payload_admits_only_the_exact_optional_walk_union(self):
        base = {"exit_ref": "42", "current_node": "wild:elosern:5:5"}
        self.assertEqual(validate_move_payload(base), base)
        self.assertEqual(
            validate_move_payload(
                {**base, "walk": {"pace": "cautious", "stop_at_night": True}}
            ),
            {**base, "walk": {"pace": "cautious", "stop_at_night": True}},
        )
        rejected = (
            # extra / missing keys at either level
            {**base, "direction": "n"},
            {**base, "walk": {"pace": "cautious"}},
            {**base, "walk": {"pace": "cautious", "stop_at_night": True, "x": 1}},
            {**base, "walk": None},
            {**base, "walk": ["cautious", True]},
            # an unknown pace and non-boolean switches
            {**base, "walk": {"pace": "sprint", "stop_at_night": True}},
            {**base, "walk": {"pace": "forced", "stop_at_night": 1}},
            {**base, "walk": {"pace": "forced", "stop_at_night": "yes"}},
            # the walk pace must be a string, never a boolean
            {**base, "walk": {"pace": True, "stop_at_night": True}},
            # a class instance is not the exact object form
            {**base, "walk": type("Walk", (), {"pace": "forced", "stop_at_night": True})()},
        )
        for payload in rejected:
            with self.subTest(payload=payload):
                with self.assertRaises(ExplorationActionError):
                    validate_move_payload(payload)


    @covers_requirement("webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path")
    def test_an_unchanged_canonical_node_rejects_whatever_the_room_identity(self):
        # A traversal that swapped the pooled room object while keeping the
        # canonical cell is not a step: the result must be move_failed.
        source_room = create_object(TerrainRoom, key="荒野甲")
        target_room = create_object(TerrainRoom, key="荒野乙")
        self.player.location = source_room
        self.exit_obj.location = source_room
        self.exit_obj.destination = target_room

        def traverse(actor, destination):
            actor.location = destination

        with patch.object(
            TerrainRoom,
            "coordinates",
            new_callable=PropertyMock,
            return_value=(4, 9),
        ), patch.object(self.exit_obj, "at_traverse", traverse):
            result = self._move(
                {
                    "exit_ref": str(int(self.exit_obj.id)),
                    "current_node": encode_wild(WILDERNESS_NAME, 4, 9),
                }
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "move_failed")
        self.assertNotIn("data", result)


    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_a_refused_step_carries_no_interrupt_data(self):
        before = get_world_clock().tick
        result = self._move(
            {"exit_ref": str(int(self.exit_obj.id)), "current_node": "room:9999"}
        )
        self.assertEqual(result["code"], "stale_location")
        self.assertNotIn("data", result)
        self.assertEqual(get_world_clock().tick, before)


    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_a_movement_owned_failure_restores_knowledge_and_carries_no_interrupts(self):
        import world.rules.map_knowledge as map_knowledge

        real_record = map_knowledge.record_arrival

        def failing_record(character):
            # Fail after the arrival write, still inside the movement-owned
            # transaction, so the settlement's own compensation must restore
            # the durable and cached observation state.
            real_record(character)
            raise RuntimeError("synthetic post-knowledge failure")

        before = get_world_clock().tick
        with patch.object(map_knowledge, "record_arrival", failing_record):
            result = self._move(
                {
                    "exit_ref": str(int(self.exit_obj.id)),
                    "current_node": f"room:{int(self.room1.pk)}",
                }
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "move_failed")
        self.assertNotIn("data", result)
        self.assertIs(self.player.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)
        with self.assertRaises(KnowledgeError):
            parse_knowledge(self.player)


    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_a_caller_rollback_discards_the_commit_qualified_result(self):
        from django.db import transaction
        from twisted.internet.defer import Deferred

        room = create_object(TerrainRoom, key="測試荒野房間")
        self.player.location = room
        self.exit_obj.location = room
        self.exit_obj.destination = room
        coordinates = [1, 1]

        def traverse(actor, destination):
            coordinates[1] += 1

        with patch.object(
            TerrainRoom,
            "coordinates",
            new_callable=PropertyMock,
            side_effect=lambda: tuple(coordinates),
        ), patch.object(self.exit_obj, "at_traverse", traverse):
            source = _current_node(self.player)
            with transaction.atomic():
                result = self._move(
                    {
                        "exit_ref": str(int(self.exit_obj.id)),
                        "current_node": source,
                    }
                )
                self.assertIsInstance(result, Deferred)
                transaction.set_rollback(True)
        self.assertFalse(
            result.called,
            "a rolled-back caller transaction must never publish the step",
        )


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


    @covers_requirement("webclient-exploration-menu::interaction-publication-and-shared-local-target-resolution-use-visible-candidates")
    def test_look_at_hidden_target_is_rejected_as_no_target(self):
        target = create_object(NPC, key="路人", location=self.room1)
        target.locks.add("view:false()")
        with patch.object(self.player, "msg") as msg:
            result = _look_adapter(self.player, {"target_id": int(target.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_target")
        self.assertEqual(result["message"], "這裡沒有這個對象。")
        msg.assert_not_called()

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


class WildernessMoveInterruptTests(BattlefieldIsolation, EvenniaTest):
    """A real wilderness world: committed steps carry committed interrupts.

    The fixture enters the wilderness through the production east gate and
    pins a revealed window around the landing cell, so the paired planner
    prediction and the committed adapter step describe the same cell.
    """

    def setUp(self):
        super().setUp()
        from typeclasses.exits import WildernessGateExit
        from typeclasses.rooms import GridRoom, Room
        from world.maps.bootstrap import sync_grid, sync_wilderness
        from world.tests.geography_fixture import publish_shipped_map_world

        publish_shipped_map_world()
        self.room1.key = "Room1"
        self.room1.save()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=_east_gate_xyz()).first()
        self.gate = next(
            exit_obj
            for exit_obj in self.east_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        )
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.location = self.east_gate
        self.pinned: set[tuple[int, int]] = set()

    # -- fixture helpers -------------------------------------------------
    def _move(self, payload):
        from twisted.internet.defer import Deferred

        with self.captureOnCommitCallbacks(execute=True):
            result = _move_adapter(self.char1, payload)
        if isinstance(result, Deferred):
            self.assertTrue(
                result.called, "the committed step must release its result"
            )
            return result.result
        return result

    def pin_knowledge(self, visits):
        from world.maps.wilderness_provider import WILDERNESS_NAME
        from world.rules.map_knowledge import CHUNK_CELLS, KNOWLEDGE_ATTR, SCHEMA_VERSION

        chunks: dict[str, dict[str, dict[str, int]]] = {}
        for (x, y), sight in visits.items():
            chunk = chunks.setdefault(f"{x // CHUNK_CELLS}:{y // CHUNK_CELLS}", {})
            chunk[str((y % CHUNK_CELLS) * CHUNK_CELLS + (x % CHUNK_CELLS))] = {
                "first_seen_tick": 1,
                "last_seen_tick": 1,
                "sight": sight,
            }
        self.char1.attributes.add(
            KNOWLEDGE_ATTR,
            {
                "schema_version": SCHEMA_VERSION,
                "visited": {},
                "wilderness": {WILDERNESS_NAME: chunks},
            },
        )
        self.pinned.update(tuple(cell) for cell in visits)

    def _enter(self):
        """Enter the wilderness through the real gate and pin its window."""
        result = self._move(
            {
                "exit_ref": str(int(self.gate.id)),
                "current_node": _current_node(self.char1),
            }
        )
        self.assertEqual(result["outcome"], "success")
        self.origin = tuple(self.char1.location.coordinates)
        self.pin_knowledge(
            {
                (self.origin[0] + dx, self.origin[1] + dy): 8
                for dx in range(-2, 3)
                for dy in range(-2, 3)
            }
        )
        return result

    def _step(self):
        """The first revealed, gateway-free neighbour's exit and cell."""
        from world.maps import wilderness_destination
        from world.maps.wilderness_destination import (
            DIRECTION_DELTAS,
            normalize_wilderness_direction,
        )
        from world.rules.travel_plan import DIRECTION_ORDER

        origin = tuple(self.char1.location.coordinates)
        for direction in DIRECTION_ORDER:
            dx, dy = DIRECTION_DELTAS[direction]
            if wilderness_destination.find_gateway(origin, direction) is not None:
                continue
            target = wilderness_destination.wilderness_neighbor(
                origin[0], origin[1], direction
            )
            if target is None or target not in self.pinned:
                continue
            exit_obj = next(
                (
                    exit_obj
                    for exit_obj in self.char1.location.exits
                    if normalize_wilderness_direction(exit_obj.key) == direction
                ),
                None,
            )
            if exit_obj is not None:
                return exit_obj, target
        self.fail("no revealed wilderness step is available")

    def _step_payload(self, exit_obj, *, walk=None):
        payload = {
            "exit_ref": str(int(exit_obj.id)),
            "current_node": _current_node(self.char1),
        }
        if walk is not None:
            payload["walk"] = walk
        return payload

    def _set_reserve(self, reserve):
        from world.rules.fatigue import (
            SleepPosture,
            initialize_fatigue_state,
            read_optional_fatigue_state,
            write_fatigue_state,
        )

        if read_optional_fatigue_state(self.char1) is None:
            initialize_fatigue_state(self.char1)
        write_fatigue_state(self.char1, reserve, SleepPosture.AWAKE)

    def _advance_to(self, tick: int) -> None:
        """Advance the canonical world clock to ``tick`` through its own API."""
        from world.rules.clock import AdvanceSource

        clock = get_world_clock()
        clock.advance(tick - clock.tick, AdvanceSource.COMMAND, [self.char1])
        self.assertEqual(get_world_clock().tick, tick)

    # -- evidence --------------------------------------------------------
    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_a_gate_entry_carries_committed_interrupts_without_a_capture_failure(self):
        from world.rules.travel_interrupts import FLAG_ORDER

        result = self._enter()
        interrupts = result["data"]["interrupts"]
        self.assertIsInstance(interrupts, list)
        self.assertEqual(len(interrupts), len(set(interrupts)))
        self.assertTrue(set(interrupts) <= set(FLAG_ORDER))
        # Without a walk context the pace/night flags never raise.
        self.assertNotIn("pace_threshold", interrupts)
        self.assertNotIn("nightfall", interrupts)

    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_the_natural_arrival_flag_reports_the_landmark_cell(self):
        from world.rules.travel_interrupts import landmark_keys_at

        result = self._enter()
        origin = tuple(self.char1.location.coordinates)
        expected = bool(landmark_keys_at(origin))
        self.assertEqual(
            "landmark_reached" in result["data"]["interrupts"], expected
        )

    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_capturing_the_committed_facts_writes_nothing(self):
        from world.rules.surfaces import attribute_snapshot
        from world.rules.travel_interrupts import read_movement_facts

        self._enter()
        clock = get_world_clock()
        tick = clock.tick
        knowledge = attribute_snapshot(self.char1, "map_knowledge")
        facts = read_movement_facts(self.char1, self.char1.location)
        self.assertEqual(facts.cell, tuple(self.char1.location.coordinates))
        self.assertEqual(len(facts.travellers), 1)
        self.assertEqual(clock.tick, tick)
        self.assertEqual(attribute_snapshot(self.char1, "map_knowledge"), knowledge)

    @covers_requirement(
        "wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts"
    )
    def test_pooled_room_facts_follow_coordinates_not_object_identity(self):
        from world.rules.travel_interrupts import read_movement_facts

        self._enter()
        room = self.char1.location
        first = self.origin
        second = (first[0] + 1, first[1])
        with patch.object(
            TerrainRoom,
            "coordinates",
            new_callable=PropertyMock,
            return_value=first,
        ):
            before = read_movement_facts(self.char1, room)
        with patch.object(
            TerrainRoom,
            "coordinates",
            new_callable=PropertyMock,
            return_value=second,
        ):
            after = read_movement_facts(self.char1, room)
        self.assertEqual(before.cell, first)
        self.assertEqual(after.cell, second)

    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_an_after_capture_setup_failure_never_fails_the_committed_move(self):
        import world.rules.movement_settlement as settlement

        self._enter()
        exit_obj, _cell = self._step()
        before = get_world_clock().tick
        with patch(
            "world.rules.travel_interrupts.wilderness_cell",
            side_effect=RuntimeError("synthetic destination-cell failure"),
        ), patch.object(settlement, "log_warn") as log_warn:
            result = self._move(self._step_payload(exit_obj))
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["data"], {"interrupts": []})
        self.assertGreater(
            get_world_clock().tick,
            before,
            "the committed step must keep its charge",
        )
        events = [call.args[0] for call in log_warn.call_args_list]
        self.assertIn("travel_interrupts_failed", events)

    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_a_before_capture_failure_reports_the_current_tick(self):
        import world.rules.movement_settlement as settlement

        self._enter()
        exit_obj, _cell = self._step()
        tick_before = get_world_clock().tick
        with patch(
            "world.rules.travel_interrupts.read_movement_facts",
            side_effect=RuntimeError("synthetic source capture failure"),
        ), patch.object(settlement, "log_warn") as log_warn:
            result = self._move(self._step_payload(exit_obj))
        self.assertEqual(result["outcome"], "success")
        failures = [
            call.kwargs["context"]
            for call in log_warn.call_args_list
            if call.args and call.args[0] == "travel_interrupts_failed"
        ]
        self.assertTrue(failures)
        self.assertEqual(failures[0]["tick"], tick_before)
        self.assertEqual(failures[0]["step"], "before")

    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_initial_pace_state_matches_move_interrupt(self):
        from world.rules.fatigue import FatigueStage, get_policy
        from world.rules.tests.test_travel_plan import _STAGE_RESERVES
        from world.rules.travel_plan import plan_travel, read_travel_snapshot

        self._enter()
        for initial in (
            FatigueStage.LIGHT,
            FatigueStage.MODERATE,
            FatigueStage.SEVERE,
        ):
            for pace in ("cautious", "standard", "forced"):
                with self.subTest(initial=initial, pace=pace):
                    self._set_reserve(_STAGE_RESERVES[initial])
                    exit_obj, target = self._step()
                    plan = plan_travel(
                        read_travel_snapshot(self.char1), target, pace, False
                    )
                    result = self._move(
                        self._step_payload(
                            exit_obj,
                            walk={"pace": pace, "stop_at_night": False},
                        )
                    )
                    self.assertEqual(result["outcome"], "success")
                    planner_stops = plan.stop_reason == "pace_threshold"
                    self.assertEqual(
                        "pace_threshold" in result["data"]["interrupts"],
                        planner_stops,
                        "the move must stop on the same threshold as travel.plan",
                    )

    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_nightfall_raises_only_for_a_charged_crossing(self):
        self._enter()
        self._advance_to(_night_start_tick() - 1)
        exit_obj, _cell = self._step()
        result = self._move(
            self._step_payload(
                exit_obj, walk={"pace": "forced", "stop_at_night": True}
            )
        )
        self.assertEqual(result["outcome"], "success")
        self.assertGreater(get_world_clock().tick, _night_start_tick() - 1)
        self.assertIn("nightfall", result["data"]["interrupts"])

    @covers_requirement(
        "wilderness-travel-interrupts::interrupt-results-respect-movement-failure-boundaries"
    )
    def test_a_flight_waived_zero_charge_step_cannot_cross_into_night(self):
        from world.rules.fatigue import get_policy

        self._enter()
        self.char1.db.skills = {"active": [], "passive": ["flight"]}
        self._set_reserve(get_policy().max_units)
        self._advance_to(_night_start_tick() - 1)
        exit_obj, _cell = self._step()
        result = self._move(
            self._step_payload(
                exit_obj, walk={"pace": "forced", "stop_at_night": True}
            )
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick, _night_start_tick() - 1)
        self.assertNotIn("nightfall", result["data"]["interrupts"])


def _east_gate_xyz():
    """The production east-gate grid coordinate, probed from the registry."""
    import importlib

    registry = getattr(
        importlib.import_module("world.lore.wilderness_entry"),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    )
    entries = [
        entry
        for entry in registry.values()
        if entry.gate_for("w") is not None and entry.gate_for("n") is not None
    ]
    if len(entries) != 1:
        raise AssertionError(entries)
    from world.maps.static_references import settlement_node_xyz

    return settlement_node_xyz(entries[0].gate_for("w").destination)


def _night_start_tick() -> int:
    """One tick at the first second of the shipped night phase."""
    from world.rules import sight

    start_hour = next(
        entry[1] for entry in sight.POLICY.phases if entry[0] == "night"
    )
    return start_hour * 3600


if __name__ == "__main__":
    unittest.main()
