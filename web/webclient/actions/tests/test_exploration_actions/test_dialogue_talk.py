"""Scripted and free-form dialogue talk adapter tests."""
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from evennia.utils.test_resources import EvenniaTestCase
from world.ai.fake_client import FakeLLMClient
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
    DialogueDefinition,
    KeywordResponse,
)
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
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from django.test import override_settings
from unittest.mock import patch
from world.ai.npc_dialogue import register_npc_dialogue
import unittest
from ._support import (
    _HeldClient,
    _T_BRANCH,
    _T_DIALOGUE,
    _T_ITEM,
    _T_LODGE_GREETING,
    _T_LODGE_KEYWORD,
    _T_LODGE_LINE,
    _T_SKILL,
    _T_SKILL_ROW,
    _T_STAFF_TURNIN_LINE,
    _raw,
    _reply_text,
    _reset_guardrail,
    _t_dialogue_scope,
    await_result,
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
    # explore.talk_scripted
    # ------------------------------------------------------------------
    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_scripted_host_answers_with_the_authored_line(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIn(_T_LODGE_LINE, result["message"])


    def test_scripted_host_no_state_answer(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": "補貨"}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIn("櫃檯右側", result["message"])


    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_turnin_keyword_flows_through_the_shared_dialogue_resolution(self):
        # The production turnin special case keys off the (imported-constant)
        # staff-table/keyword pair: an unregistered player at a staff-hosted
        # desk gets the authored register-first line through the shared
        # resolution AND the known-keyword affinity gain is skipped purely.
        host = create_object(NPC, key="公會職員", location=self.room1)
        host.components.add(
            ScriptedDialogue.create(host, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        from typeclasses.components import GuildStaff

        host.components.add(
            GuildStaff.create(host, service_id="staff", branch_key=_T_BRANCH)
        )
        relations_before = host.db.relations_data
        result = _talk_scripted_adapter(
            self.player,
            {"npc_id": int(host.pk), "keyword_id": GUILD_STAFF_TURNIN_KEYWORD},
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIn(_T_STAFF_TURNIN_LINE, result["message"])
        # Losing the special case would route this known keyword through the
        # normal +1 talk-affinity write; the fixture surface must stay pure.
        self.assertEqual(host.db.relations_data, relations_before)


    def test_unregistered_keyword_rejects_without_writing(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(host.pk), "keyword_id": "不存在的話題"}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unregistered_keyword")


    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_no_longer_present_npc_rejects_before_any_dialogue_api(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        host.location = create_object(Room, key="別處", location=None)
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk"
        ) as talk:
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_npc")
        talk.assert_not_called()


    def test_non_dialogue_host_rejects_before_any_dialogue_api(self):
        plain = create_object(NPC, key="路人", location=self.room1)
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(plain.pk), "keyword_id": _T_LODGE_KEYWORD}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "not_dialogue_host")


    def test_talk_response_failure_and_silence_are_rejected(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk",
            side_effect=RuntimeError("boom"),
        ):
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
            )
        self.assertEqual(result["code"], "dialogue_failed")
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk",
            return_value=None,
        ):
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
            )
        self.assertEqual(result["code"], "no_response")



    # ------------------------------------------------------------------
    # explore.talk_freeform
    # ------------------------------------------------------------------
    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_reply_memory_and_verified_intent_are_applied(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        npc.db.inventory = [_T_ITEM]
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(
                speech="我給你一瓶藥水。",
                intent={"kind": "give_item", "item_key": _T_ITEM, "qty": 1},
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
        self.assertEqual(list(self.player.db.inventory or []), [_T_ITEM])
        self.assertEqual(list(npc.db.inventory or []), [])
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(
            npc._chat_lines(self.player),
            ["探索行動測試: 你好", "對話精靈: 我給你一瓶藥水。"],
        )


    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_offline_degrade_yields_greeting_and_no_client_call(self):
        npc = create_object(LLMNPC, key="客棧老板娘", location=self.room1)
        npc.components.add(ScriptedDialogue.create(npc, dialogue_key=_T_DIALOGUE))
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
        self.assertTrue(any(_T_LODGE_GREETING in text for text in texts))


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


    @covers_requirement("webclient-exploration-menu::freeform-talk-completion-rechecks-presence-before-applying-intents")
    def test_freeform_deferred_reply_after_the_player_moved_is_discarded(self):
        npc = create_object(LLMNPC, key="對話精靈", location=self.room1)
        npc.db.inventory = [_T_ITEM]
        client = _HeldClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ), patch.object(self.player, "msg") as msg:
            deferred = _talk_freeform_adapter(
                self.player, {"npc_id": int(npc.pk), "speech": "你好"}
            )
            self.player.location = self.destination
            client.deferred.callback(
                _reply_text(
                    speech="我給你一瓶藥水。",
                    intent={"kind": "give_item", "item_key": _T_ITEM, "qty": 1},
                )
            )
            result = await_result(deferred)
        self.assertEqual(result["outcome"], "success")
        self.assertIn("離開", result["message"])
        # The speech is shown (memory) and the stale note is surfaced, while
        # the intent changes no state (F22 completion gate).
        self.assertEqual(npc._chat_lines(self.player)[1], "對話精靈: 我給你一瓶藥水。")
        self.assertEqual(list(self.player.db.inventory or []), [])
        self.assertEqual(list(npc.db.inventory or []), [_T_ITEM])
        texts = [str(call.args[0]) for call in msg.call_args_list if call.args]
        self.assertIn("我給你一瓶藥水。", " ".join(texts))
        self.assertTrue(any("離開" in text for text in texts))


    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_host_rejects_scripted_talk_without_a_transaction(self):
        host = create_object(NPC, key="客棧老板娘", location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_T_DIALOGUE))
        host.db.schedule_state = "busy"
        with patch(
            "web.webclient.actions.exploration_actions.run_scripted_talk"
        ) as talk:
            result = _talk_scripted_adapter(
                self.player, {"npc_id": int(host.pk), "keyword_id": _T_LODGE_KEYWORD}
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertIn("她現在正忙著", result["message"])
        talk.assert_not_called()


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

if __name__ == "__main__":
    unittest.main()
