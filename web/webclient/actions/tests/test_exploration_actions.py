"""Exact exploration action payload validators and adapter tests.

Covers the six explore payload validators, the movement charge/recording
through the shared exit seam, the stale/tampered/locked rejections, the combat
``at_pre_move`` veto, the look onboarding hook, scripted and free-form
dialogue (offline degrade included), engage-to-combat, and the shared skip
helper arithmetic.
"""

from tools.spec_traceability import covers_requirement

import json
import unittest
from unittest.mock import patch

from django.test import override_settings

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room, TerrainRoom
from web.webclient.actions.exploration_actions import (
    MAX_EXIT_REF_CHARS,
    MAX_KEYWORD_ID_CHARS,
    MAX_NODE_ID_CHARS,
    MAX_SPEECH_CODE_POINTS,
    ExplorationActionError,
    _current_node,
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
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_talk_freeform_payload,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import _degrade_fallbacks, _semantic_validators
from world.ai.npc_dialogue import register_npc_dialogue
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.onboarding.guide_dialogue import GUARD_DIALOGUE_KEY
from world.onboarding.scenes import GUIDANCE_BEAT_ID, LOOK_BEAT_ID
from world.rules.clock import CLOCK_YAML, get_world_clock
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    is_in_active_session,
)
from world.rules.map_knowledge import encode_grid, encode_wild, parse_knowledge
from world.rules.time_skip import MAX_WEB_SKIP_SECONDS


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _reset_guardrail():
    _semantic_validators.clear()
    _degrade_fallbacks.clear()
    _OUTPUT_SCHEMAS.clear()


def _reply_text(speech="艾洛希雅對你點頭。", intent=None):
    return json.dumps(
        {"speech": speech, "intent": intent if intent is not None else {"kind": "none"}},
        ensure_ascii=False,
    )


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


class ExplorationValidatorTests(unittest.TestCase):
    def test_move_payload_exact(self):
        self.assertEqual(
            validate_move_payload({"exit_ref": "42", "current_node": "room:5"}),
            {"exit_ref": "42", "current_node": "room:5"},
        )
        for bad in (
            None,
            {"exit_ref": "42"},
            {"exit_ref": "42", "current_node": "room:5", "extra": 1},
            {"exit_ref": "x" * (MAX_EXIT_REF_CHARS + 1), "current_node": "room:5"},
            {"exit_ref": "中文", "current_node": "room:5"},
            {"exit_ref": "42", "current_node": "not:a:node"},
            {"exit_ref": "42", "current_node": "x" * (MAX_NODE_ID_CHARS + 1)},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_move_payload(bad)

    def test_look_payload_exact(self):
        self.assertEqual(validate_look_payload({"room": True}), {"room": True})
        self.assertEqual(validate_look_payload({"target_id": 7}), {"target_id": 7})
        for bad in (
            None,
            {"room": True, "target_id": 7},
            {"room": "yes"},
            {"target_id": 0},
            {"target_id": "7"},
            {},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_look_payload(bad)

    def test_talk_scripted_payload_exact(self):
        self.assertEqual(
            validate_talk_scripted_payload({"npc_id": 3, "keyword_id": "公會"}),
            {"npc_id": 3, "keyword_id": "公會"},
        )
        for bad in (
            None,
            {"npc_id": 3},
            {"npc_id": 0, "keyword_id": "公會"},
            {"npc_id": True, "keyword_id": "公會"},
            {"npc_id": 3, "keyword_id": ""},
            {"npc_id": 3, "keyword_id": "x" * (MAX_KEYWORD_ID_CHARS + 1)},
            {"npc_id": 3, "keyword_id": "公會", "extra": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_talk_scripted_payload(bad)

    def test_talk_freeform_payload_exact(self):
        self.assertEqual(
            validate_talk_freeform_payload({"npc_id": 3, "speech": "你好"}),
            {"npc_id": 3, "speech": "你好"},
        )
        for bad in (
            None,
            {"npc_id": 3},
            {"npc_id": 3, "speech": ""},
            {"npc_id": 3, "speech": "你" * (MAX_SPEECH_CODE_POINTS + 1)},
            {"npc_id": 3, "speech": "你好", "actor": "x"},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_talk_freeform_payload(bad)

    def test_party_invite_payload_exact(self):
        self.assertEqual(
            validate_party_invite_payload({"npc_id": 3, "message": ""}),
            {"npc_id": 3, "message": ""},
        )
        self.assertEqual(
            validate_party_invite_payload({"npc_id": 3, "message": "你願意嗎？"}),
            {"npc_id": 3, "message": "你願意嗎？"},
        )
        for bad in (
            None,
            {"npc_id": 3},
            {"npc_id": 3, "message": None},
            {"npc_id": 3, "message": "你" * (MAX_SPEECH_CODE_POINTS + 1)},
            {"npc_id": 0, "message": ""},
            {"npc_id": 3, "message": "", "extra": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_party_invite_payload(bad)

    def test_party_leave_payload_exact(self):
        self.assertEqual(
            validate_party_leave_payload({"npc_id": 9}), {"npc_id": 9}
        )
        for bad in (
            None,
            {"npc_id": 0},
            {"npc_id": "9"},
            {"npc_id": True},
            {},
            {"npc_id": 9, "x": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_party_leave_payload(bad)

    def test_engage_payload_exact(self):
        self.assertEqual(validate_engage_payload({"monster_id": 9}), {"monster_id": 9})
        for bad in (
            None,
            {"monster_id": 0},
            {"monster_id": "9"},
            {"monster_id": True},
            {},
            {"monster_id": 9, "x": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_engage_payload(bad)

    def test_wait_payload_exact(self):
        self.assertEqual(validate_wait_payload({"daypart": "dawn"}), {"daypart": "dawn"})
        self.assertEqual(validate_wait_payload({"seconds": 3600}), {"seconds": 3600})
        self.assertEqual(validate_wait_payload({"sleep": True}), {"sleep": True})
        for bad in (
            None,
            {"daypart": "tea"},
            {"seconds": 0},
            {"seconds": MAX_WEB_SKIP_SECONDS + 1},
            {"seconds": "3600"},
            {"sleep": "yes"},
            {"daypart": "dawn", "seconds": 60},
            {},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_wait_payload(bad)

    def test_no_payload_accepts_actor_host_session_destination_price_or_clock(self):
        for field in (
            "actor",
            "host",
            "session_id",
            "destination",
            "destination_room",
            "price",
            "stock",
            "clock",
            "tick",
        ):
            for validator in (
                validate_move_payload,
                validate_look_payload,
                validate_talk_scripted_payload,
                validate_talk_freeform_payload,
                validate_party_invite_payload,
                validate_party_leave_payload,
                validate_engage_payload,
                validate_wait_payload,
            ):
                with self.assertRaises(ExplorationActionError):
                    validator({field: "x"})


class ExplorationActionAdapterTests(EvenniaTestCase):
    def setUp(self):
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

        sync_grid()
        gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        exit_obj = create_object(
            Exit, key="東", location=gate, destination=self.destination
        )
        self.player.location = gate
        node = encode_grid(SOUTH_GATE_XYZ[2], SOUTH_GATE_XYZ[0], SOUTH_GATE_XYZ[1])
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

    @covers_requirement("webclient-exploration-menu::explore-look-reuses-the-command-appearance-path-and-preserves-onboarding-look-hooks")
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

    def test_look_at_absent_target_rejects_without_onboarding_write(self):
        before = self.player.first_arrival_seen
        result = _look_adapter(self.player, {"target_id": 999999})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_target")
        self.assertEqual(self.player.first_arrival_seen, before)

    @covers_requirement("webclient-exploration-menu::explore-look-reuses-the-command-appearance-path-and-preserves-onboarding-look-hooks")
    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_look_at_room_advances_the_onboarding_look_beat(self):
        sync_grid()
        gate = self.room1
        gate.key = "南門"
        gate.save()
        self.player.location = gate
        self.player.onboarding_beat = LOOK_BEAT_ID
        self.player.guide_progress = {"state": "active", "seen_keywords": []}
        self.player.onboarded = False
        with patch.object(self.player, "msg"):
            result = _look_adapter(self.player, {"room": True})
        self.assertEqual(result["outcome"], "success")
        self.assertTrue(self.player.first_arrival_seen)
        self.assertEqual(self.player.onboarding_beat, GUIDANCE_BEAT_ID)

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

    # ------------------------------------------------------------------
    # explore.talk_scripted
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_scripted_host_answers_and_guard_records_the_keyword(self):
        host = create_object(NPC, key="南門守衛", location=self.room1)
        from typeclasses.components import OnboardingGuide

        host.components.add(
            OnboardingGuide.create(host, dialogue_key=GUARD_DIALOGUE_KEY)
        )
        self.player.guide_progress = {"state": "active", "seen_keywords": []}
        self.player.save()
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": "公會"}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIn("冒險者公會", result["message"])
        progress = self.player.guide_progress or {}
        self.assertIn("公會", progress.get("seen_keywords", []))

    def test_scripted_host_no_state_answer(self):
        host = create_object(NPC, key="公會職員", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": "任務"}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIn("guild", result["message"])
        # A scripted host never writes guide state.
        self.assertFalse(self.player.guide_progress)

    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_turnin_keyword_flows_through_the_shared_dialogue_resolution(self):
        host = create_object(NPC, key="公會職員", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
        from typeclasses.components import GuildStaff

        host.components.add(
            GuildStaff.create(host, service_id="staff", branch_key="guild_branch_altoria")
        )
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": "回報"}
        )
        self.assertEqual(result["outcome"], "success")
        # The unregistered player receives the authored register-first line
        # through the shared resolution; no claim or quest state can change.
        self.assertIn("guild register", result["message"])
        self.assertFalse(self.player.guide_progress)

    def test_unregistered_keyword_rejects_without_writing(self):
        host = create_object(NPC, key="南門守衛", location=self.room1)
        from typeclasses.components import OnboardingGuide

        host.components.add(
            OnboardingGuide.create(host, dialogue_key=GUARD_DIALOGUE_KEY)
        )
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": "不存在的話題"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unregistered_keyword")
        self.assertFalse(self.player.guide_progress)

    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_no_longer_present_npc_rejects_before_any_dialogue_api(self):
        host = create_object(NPC, key="南門守衛", location=self.room1)
        from typeclasses.components import OnboardingGuide

        host.components.add(
            OnboardingGuide.create(host, dialogue_key=GUARD_DIALOGUE_KEY)
        )
        host.location = create_object(Room, key="別處", location=None)
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk"
        ) as talk:
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": "公會"}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")
        talk.assert_not_called()
        self.assertFalse(self.player.guide_progress)

    def test_non_dialogue_host_rejects_before_any_dialogue_api(self):
        plain = create_object(NPC, key="路人", location=self.room1)
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(plain.pk), "keyword_id": "公會"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "not_dialogue_host")

    def test_talk_response_failure_and_silence_are_rejected(self):
        host = create_object(NPC, key="南門守衛", location=self.room1)
        from typeclasses.components import OnboardingGuide

        host.components.add(
            OnboardingGuide.create(host, dialogue_key=GUARD_DIALOGUE_KEY)
        )
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk",
            side_effect=RuntimeError("boom"),
        ):
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": "公會"}
            )
        self.assertEqual(result["code"], "dialogue_failed")
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk",
            return_value=None,
        ):
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": "公會"}
            )
        self.assertEqual(result["code"], "no_response")

    # ------------------------------------------------------------------
    # explore.talk_freeform
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_reply_memory_and_verified_intent_are_applied(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        npc.db.inventory = ["healing_potion"]
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(
                speech="我給你一瓶藥水。",
                intent={"kind": "give_item", "item_key": "healing_potion", "qty": 1},
            ),
        )
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg"):
            result = await_result(
                _talk_freeform_adapter(
                    self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                )
            )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(list(self.player.db.inventory or []), ["healing_potion"])
        self.assertEqual(list(npc.db.inventory or []), [])
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(
            npc._chat_lines(self.player),
            ["探索行動測試: 你好", "對話精靈: 我給你一瓶藥水。"],
        )

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_offline_degrade_yields_greeting_and_no_client_call(self):
        npc = create_object(LLMNPC, key="公會職員", location=self.room1)
        npc.components.add(ScriptedDialogue.create(npc, dialogue_key="guild_staff"))
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ), patch.object(self.player, "msg") as msg:
                result = await_result(
                    _talk_freeform_adapter(
                        self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(len(client.calls), 0)
        texts = [str(call.args[0]) for call in msg.call_args_list if call.args]
        self.assertTrue(any("歡迎來到冒險者公會" in text for text in texts))

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_illegal_intent_is_discarded_while_speech_is_kept(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="我要你交出所有錢。", intent={"kind": "take_item"}),
        )
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg"):
            result = await_result(
                _talk_freeform_adapter(
                    self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                )
            )
        self.assertEqual(result["outcome"], "success")
        # Speech is kept (memory), the illegal intent changes no state.
        self.assertEqual(npc._chat_lines(self.player)[0], "探索行動測試: 你好")
        self.assertIsNone(self.player.db.guild_registration)
        self.assertEqual(list(self.player.db.inventory or []), [])

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_tampered_npc_id_rejects_before_any_client_work(self):
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _talk_freeform_adapter(
                self.player, {"npc_id": 999999, "speech": "你好"}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_transport_failure_settles_as_dialogue_failed(self):
        from twisted.internet.defer import fail as defer_fail

        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        failing = defer_fail(Exception("transport down"))
        with patch.object(
            npc, "at_talked_to", return_value=failing
        ), patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client"
        ):
            result = await_result(
                _talk_freeform_adapter(
                    self.player, {"npc_id": int(npc.pk), "speech": "你好"}
                )
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "dialogue_failed")

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_host_rejects_scripted_talk_without_a_transaction(self):
        host = create_object(NPC, key="公會職員", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
        host.db.schedule_state = "busy"
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk"
        ) as talk:
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": "任務"}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertIn("她現在正忙著", result["message"])
        talk.assert_not_called()
        self.assertFalse(self.player.guide_progress)

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_host_rejects_freeform_talk_before_any_seam_work(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        npc.db.schedule_state = "resting"
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(npc, "at_talked_to") as seam:
            result = _talk_freeform_adapter(
                self.player, {"npc_id": int(npc.pk), "speech": "你好"}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertIn("她現在正忙著", result["message"])
        seam.assert_not_called()
        self.assertEqual(len(client.calls), 0)
        self.assertEqual(npc._chat_lines(self.player), [])

    # ------------------------------------------------------------------
    # explore.party_invite / explore.party_leave
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_accept_joins_and_notifies(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(
                speech="我願意與你同行。",
                intent={"kind": "party_invite", "accept": True},
            ),
        )
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg") as msg:
            result = await_result(
                _party_invite_adapter(
                    self.player, {"npc_id": int(npc.pk), "message": "你願意嗎？"}
                )
            )
        self.assertEqual(result["outcome"], "success")
        from world.rules.party import JOINED_MESSAGE, is_companion

        self.assertTrue(is_companion(npc, self.player))
        texts = " ".join(str(call.args[0]) for call in msg.call_args_list if call.args)
        self.assertIn(JOINED_MESSAGE, texts)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_offline_threshold_decides_with_no_client_call(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(npc, self.player, AffinitySource.QUEST_COMPLETION, 70)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ):
                result = await_result(
                    _party_invite_adapter(
                        self.player, {"npc_id": int(npc.pk), "message": ""}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        from world.rules.party import is_companion

        self.assertTrue(is_companion(npc, self.player))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_offline_below_threshold_rejects(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ):
                result = await_result(
                    _party_invite_adapter(
                        self.player, {"npc_id": int(npc.pk), "message": ""}
                    )
                )
        self.assertEqual(result["outcome"], "success")
        from world.rules.party import is_companion

        self.assertFalse(is_companion(npc, self.player))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_full_party_rejects_before_the_ai_call(self):
        from world.rules.party import PARTY_MAX_COMPANIONS, join_party

        for index in range(PARTY_MAX_COMPANIONS):
            join_party(
                create_object(LLMNPC, key=f"同伴{index}", location=self.room1),
                self.player,
            )
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _party_invite_adapter(
                self.player, {"npc_id": int(npc.pk), "message": ""}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "party_full")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_already_companion_rejects_before_the_ai_call(self):
        from world.rules.party import join_party

        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        join_party(npc, self.player)
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _party_invite_adapter(
                self.player, {"npc_id": int(npc.pk), "message": ""}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "already_companion")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-invite-proposes-a-party-through-the-guarded-dialogue-seam")
    def test_party_invite_non_llm_npc_rejects(self):
        npc = create_object(NPC, key="普通村民", location=self.room1)
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ):
            result = _party_invite_adapter(
                self.player, {"npc_id": int(npc.pk), "message": ""}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("webclient-exploration-menu::explore-party-leave-dismisses-a-bound-companion-without-affinity-change")
    def test_party_leave_dismisses_without_affinity_change(self):
        from world.rules.affinity import AffinitySource, apply_affinity_change
        from world.rules.party import is_companion, join_party

        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        apply_affinity_change(npc, self.player, AffinitySource.QUEST_COMPLETION, 55)
        join_party(npc, self.player)
        before = npc.relations.affinity_for(self.player)
        result = _party_leave_adapter(
            self.player, {"npc_id": int(npc.pk)}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertFalse(is_companion(npc, self.player))
        self.assertIsNone(npc.db.party_member)
        self.assertEqual(npc.relations.affinity_for(self.player), before)

    @covers_requirement("webclient-exploration-menu::explore-party-leave-dismisses-a-bound-companion-without-affinity-change")
    def test_party_leave_unbound_target_rejects(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        result = _party_leave_adapter(
            self.player, {"npc_id": int(npc.pk)}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "not_companion")

    @covers_requirement("webclient-exploration-menu::explore-party-leave-dismisses-a-bound-companion-without-affinity-change")
    def test_party_leave_tampered_npc_id_rejects(self):
        result = _party_leave_adapter(self.player, {"npc_id": 999999})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")

    # ------------------------------------------------------------------
    # explore.engage
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-engage-delegates-to-the-existing-engage-contract")
    def test_engage_transitions_to_combat(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        result = _engage_adapter(self.player, {"monster_id": int(monster.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["affected_panels"], ("status", "context_actions"))
        self.assertTrue(is_in_active_session(self.player))

    def test_engage_rejects_remote_or_dead_target_without_session(self):
        result = _engage_adapter(self.player, {"monster_id": 999999})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_monster")
        self.assertFalse(is_in_active_session(self.player))

        monster = create_object(Monster, key="死掉的哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.current = 0
        monster.save()
        result = _engage_adapter(self.player, {"monster_id": int(monster.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "target_dead")
        self.assertFalse(is_in_active_session(self.player))

    def test_engage_already_in_combat_and_session_failures_are_rejected(self):
        first = create_object(Monster, key="哥布林甲", location=self.room1)
        first.threat_tier = "low"
        first.apply_monster_tier("floor")
        second = create_object(Monster, key="哥布林乙", location=self.room1)
        second.threat_tier = "low"
        second.apply_monster_tier("floor")
        engage(self.player, first)
        self.assertTrue(is_in_active_session(self.player))
        result = _engage_adapter(self.player, {"monster_id": int(second.pk)})
        self.assertEqual(result["code"], "already_in_combat")

        with patch(
            "web.webclient.actions.exploration_actions.engage",
            side_effect=CombatSessionError(SessionReason.NOT_PRESENT),
        ):
            result = _engage_adapter(self.player, {"monster_id": int(second.pk)})
        self.assertEqual(result["code"], "no_monster")

        with patch(
            "web.webclient.actions.exploration_actions.engage",
            side_effect=CombatSessionError("unexpected"),
        ):
            result = _engage_adapter(self.player, {"monster_id": int(second.pk)})
        self.assertEqual(result["code"], "engage_failed")

    # ------------------------------------------------------------------
    # explore.wait
    # ------------------------------------------------------------------

    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_wait_until_dawn_advances_to_the_next_occurrence(self):
        from world.rules.clock import seconds_until_daypart

        get_world_clock()._persist(2 * 3600)  # 2:00
        expected = seconds_until_daypart(get_world_clock().calendar, "dawn")
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"daypart": "dawn"})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick - before, expected)
        self.assertIn("時間經過了", result["message"])

    def test_wait_custom_duration_is_parsed_server_side(self):
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"seconds": 3600})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick - before, 3600)

    def test_wait_sleep_uses_full_regen_and_is_bounded(self):
        from world.rules.time_skip import seconds_to_full_regen

        expected = seconds_to_full_regen(self.player)
        self.assertLessEqual(expected, MAX_WEB_SKIP_SECONDS)
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"sleep": True})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick - before, expected)

    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_unsafe_skip_rejects_before_any_clock_advance(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"daypart": "dawn"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unsafe_skip")
        self.assertIn("怪物", result["message"])
        self.assertEqual(get_world_clock().tick, before)

    def test_unknown_daypart_and_skip_failure_are_rejected(self):
        result = _wait_adapter(self.player, {"daypart": "tea"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_daypart")
        with patch(
            "web.webclient.actions.exploration_actions.advance_skip",
            side_effect=RuntimeError("boom"),
        ):
            result = _wait_adapter(self.player, {"seconds": 60})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "skip_failed")


if __name__ == "__main__":
    unittest.main()
