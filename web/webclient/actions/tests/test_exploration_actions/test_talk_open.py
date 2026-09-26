"""``explore.talk_open``: open a conversation with the host's greeting (C9a).

The action mirrors ``explore.talk_scripted``'s gates (possession, presence, the
talk schedule gate, the conversable-host predicate) and then records the
session through the sole writer with the host's authored greeting, or the
fixed server-authored fallback line when the host has none. It calls no LLM,
advances no clock, and changes no affinity or memory: only
``db.dialogue_session`` moves.
"""
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room
from web.webclient.actions.exploration_actions import _talk_open_adapter
from world.ai.fake_client import FakeLLMClient
from world.rules.clock import get_world_clock
from world.rules.dialogue import (
    DialogueDefinition,
    KeywordResponse,
    greeting_for,
    live_dialogue_session,
)
from world.rules.party import join_party
from world.rules.player_messages import dialogue_open_fallback_line
from world.rules.possession import (
    REASON_POSSESSED_TALK,
    enter_possession,
    release_possession,
)
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests.combat_fixtures import BattlefieldIsolation
import unittest
from unittest.mock import patch

from ._support import _T_DIALOGUE

#: A greetingless authored row: ``greeting=None`` is the "no authored greeting"
#: case the fixed fallback line covers.
_T_GREETINGLESS_KEY = "t_synth_greetingless"
_T_GREETINGLESS_ROW = DialogueDefinition(
    greeting=None,
    responses=(KeywordResponse("話題", "「……」"),),
)

_TALK_OPEN_REQUIREMENT = (
    "webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting"
)


class TalkOpenAdapterTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        # One dialogue scope: the kit lodgekeeper row plus the greetingless row.
        open_synthetic_scope(
            self,
            "dialogue",
            extra={"dialogue": {_T_GREETINGLESS_KEY: _T_GREETINGLESS_ROW}},
        )
        get_world_clock()
        self.room1 = create_object(Room, key="起點")
        self.player = create_object(PlayerCharacter, key="開啟對話測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.destination = create_object(Room, key="目的地", location=None)

    def _scripted_host(self, key: str = "客棧老板娘", dialogue_key: str = _T_DIALOGUE) -> NPC:
        host = create_object(NPC, key=key, location=self.room1)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=dialogue_key))
        return host

    # ------------------------------------------------------------------
    # Success paths
    # ------------------------------------------------------------------
    @covers_requirement(_TALK_OPEN_REQUIREMENT)
    def test_scripted_host_opens_with_its_greeting(self):
        host = self._scripted_host()
        greeting = greeting_for(host)
        with patch.object(self.player, "msg") as msg:
            result = _talk_open_adapter(self.player, {"npc_id": int(host.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "dialogue_opened")
        self.assertEqual(result["message"], f"{host.key}說：{greeting}")
        self.assertEqual([call.args[0] for call in msg.call_args_list], [result["message"]])
        stored = self.player.db.dialogue_session
        self.assertIsNotNone(stored)
        self.assertEqual(stored["npc_id"], int(host.pk))
        self.assertEqual(stored["line"], greeting)
        session = live_dialogue_session(self.player)
        self.assertIsNotNone(session)
        self.assertEqual(session.npc_id, int(host.pk))

    @covers_requirement(_TALK_OPEN_REQUIREMENT)
    def test_llmnpc_without_a_component_opens_with_the_fallback_line(self):
        npc = create_object(LLMNPC, key="吟遊詩人", location=self.room1)
        result = _talk_open_adapter(self.player, {"npc_id": int(npc.pk)})
        self.assertEqual(result["outcome"], "success")
        fallback = dialogue_open_fallback_line(npc.key)
        self.assertEqual(result["message"], fallback)
        self.assertEqual(self.player.db.dialogue_session["line"], fallback)

    @covers_requirement(_TALK_OPEN_REQUIREMENT)
    def test_scripted_host_without_a_greeting_opens_with_the_fallback_line(self):
        host = self._scripted_host(key="無招呼者", dialogue_key=_T_GREETINGLESS_KEY)
        self.assertIsNone(greeting_for(host))
        result = _talk_open_adapter(self.player, {"npc_id": int(host.pk)})
        self.assertEqual(result["outcome"], "success")
        fallback = dialogue_open_fallback_line(host.key)
        self.assertEqual(result["message"], fallback)
        self.assertEqual(self.player.db.dialogue_session["line"], fallback)

    @covers_requirement(_TALK_OPEN_REQUIREMENT)
    def test_open_replaces_a_session_naming_another_host(self):
        first = self._scripted_host(key="第一位", dialogue_key=_T_GREETINGLESS_KEY)
        second = create_object(LLMNPC, key="第二位", location=self.room1)
        _talk_open_adapter(self.player, {"npc_id": int(first.pk)})
        result = _talk_open_adapter(self.player, {"npc_id": int(second.pk)})
        self.assertEqual(result["outcome"], "success")
        stored = self.player.db.dialogue_session
        self.assertEqual(stored["npc_id"], int(second.pk))
        self.assertEqual(stored["line"], dialogue_open_fallback_line(second.key))

    # ------------------------------------------------------------------
    # Rejections (no session write)
    # ------------------------------------------------------------------
    def test_departed_host_and_non_npc_reject_with_no_npc(self):
        host = self._scripted_host()
        host.location = self.destination
        for npc_id in (int(host.pk), 999999):
            with self.subTest(npc_id=npc_id):
                result = _talk_open_adapter(self.player, {"npc_id": npc_id})
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], "no_npc")
                self.assertIsNone(self.player.db.dialogue_session)

    def test_plain_npc_and_unresolvable_table_reject_with_not_dialogue_host(self):
        plain = create_object(NPC, key="路人", location=self.room1)
        broken = self._scripted_host(key="壞掉的NPC", dialogue_key="unknown_table")
        for host in (plain, broken):
            with self.subTest(host=host.key):
                result = _talk_open_adapter(self.player, {"npc_id": int(host.pk)})
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], "not_dialogue_host")
                self.assertIsNone(self.player.db.dialogue_session)

    def test_schedule_blocked_host_rejects_with_the_gate_reason(self):
        host = self._scripted_host()
        host.db.schedule_state = "busy"
        result = _talk_open_adapter(self.player, {"npc_id": int(host.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "schedule_blocked")
        self.assertIn("她現在正忙著", result["message"])
        self.assertIsNone(self.player.db.dialogue_session)

    def test_possessed_actor_rejects_before_resolving_the_host(self):
        companion = create_object(LLMNPC, key="被附身者", location=self.room1)
        join_party(companion, self.player)
        host = self._scripted_host()
        enter_possession(self.player, companion)
        try:
            result = _talk_open_adapter(companion, {"npc_id": int(host.pk)})
        finally:
            release_possession(self.player, npc=companion, reason="handback")
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], REASON_POSSESSED_TALK)
        self.assertIsNone(companion.db.dialogue_session)

    # ------------------------------------------------------------------
    # Side-effect freedom
    # ------------------------------------------------------------------
    @covers_requirement(_TALK_OPEN_REQUIREMENT)
    def test_a_successful_open_touches_nothing_but_the_session(self):
        host = self._scripted_host()
        tick_before = int(get_world_clock().tick)
        relations_before = host.db.relations_data
        memory_before = dict(host.db.chat_memory or {})
        client = FakeLLMClient()
        with patch(
            "web.webclient.actions.dialogue_composition.build_dialogue_client",
            return_value=client,
        ) as build_client:
            result = _talk_open_adapter(self.player, {"npc_id": int(host.pk)})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(int(get_world_clock().tick), tick_before)
        self.assertEqual(host.db.relations_data, relations_before)
        self.assertEqual(dict(host.db.chat_memory or {}), memory_before)
        self.assertEqual(client.calls, [])
        build_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
