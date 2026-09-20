"""The talk adapters' dialogue-session writes (align-07)."""
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from evennia.utils.test_resources import EvenniaTestCase
from world.ai.fake_client import FakeLLMClient
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room, TerrainRoom
from typeclasses.components import ScriptedDialogue
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
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock
from django.test import override_settings
from unittest.mock import patch
from world.ai.npc_dialogue import register_npc_dialogue
import unittest
from ._support import (
    _HeldClient,
    _T_DIALOGUE,
    _T_LODGE_GREETING,
    _T_LODGE_KEYWORD,
    _T_LODGE_LINE,
    _raw,
    _reply_text,
    _reset_guardrail,
    _t_dialogue_scope,
    await_result,
)


class DialogueSessionRecordingAdapterTests(BattlefieldIsolation, EvenniaTestCase):
    """The talk adapters are the WS-side dialogue-session writers (align-07).

    Every case observes only the persisted ``db.dialogue_session`` — the
    state-only surface this change ships; the panel/mode land in
    webclient-align-10.
    """

    def setUp(self):
        _t_dialogue_scope(self)
        from world.quests.catalog import register_catalog

        register_catalog()
        _reset_guardrail()
        register_npc_dialogue()
        get_world_clock()
        self.room1 = create_object(Room, key="起點")
        self.player = create_object(PlayerCharacter, key="對話.session測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.destination = create_object(Room, key="目的地", location=None)

    def tearDown(self):
        _reset_guardrail()
        super().tearDown()

    @covers_requirement(
        "webclient-dialogue-session::the-dialogue-session-is-deterministic-core-only-character-state"
    )
    def test_scripted_success_records_the_delivered_authored_line(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
        )
        self.assertEqual(result["outcome"], "success")
        stored = self.player.db.dialogue_session
        self.assertIsNotNone(stored)
        self.assertEqual(stored["npc_id"], int(host.pk))
        self.assertIn(_T_LODGE_LINE, stored["line"])
        self.assertIn(stored["line"], result["message"])

    def test_scripted_rejections_record_nothing(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": "不存在的話題"}
        )
        self.assertEqual(result["code"], "unregistered_keyword")
        self.assertIsNone(self.player.db.dialogue_session)

    def test_freeform_settled_reply_records_the_presented_line(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="我對你點頭。"))
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
        stored = self.player.db.dialogue_session
        self.assertIsNotNone(stored)
        self.assertEqual(stored["npc_id"], int(npc.pk))
        self.assertEqual(stored["line"], "我對你點頭。")

    def test_freeform_authored_degrade_greeting_records(self):
        npc = create_object(LLMNPC, key="客棧老板娘", location=self.room1)
        npc.components.add(ScriptedDialogue.create(npc, dialogue_key=_T_DIALOGUE))
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
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
        stored = self.player.db.dialogue_session
        self.assertIsNotNone(stored)
        self.assertIn(_T_LODGE_GREETING, stored["line"])

    def test_freeform_silent_degrade_records_nothing(self):
        npc = create_object(LLMNPC, key="無表精靈", location=self.room1)
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
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
        self.assertIsNone(self.player.db.dialogue_session)

    def test_freeform_mid_flight_stale_completion_records_nothing(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        client = _HeldClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg"):
            deferred = _talk_freeform_adapter(
                self.player, {"npc_id": int(npc.pk), "speech": "你好"}
            )
            self.player.location = self.destination
            client.deferred.callback(_reply_text(speech="我對你點頭。"))
            result = await_result(deferred)
        self.assertEqual(result["outcome"], "success")
        self.assertIn("離開", result["message"])
        self.assertIsNone(self.player.db.dialogue_session)

if __name__ == "__main__":
    unittest.main()
