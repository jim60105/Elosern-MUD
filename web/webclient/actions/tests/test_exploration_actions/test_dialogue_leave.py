"""``explore.dialogue_leave`` ends the live session (webclient-align-11)."""
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from evennia.utils.test_resources import EvenniaTestCase
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
from unittest.mock import patch
from world.ai.npc_dialogue import register_npc_dialogue
import unittest
from ._support import (
    _T_DIALOGUE,
    _T_LODGE_KEYWORD,
    _reset_guardrail,
    _t_dialogue_scope,
)


class DialogueLeaveAdapterTests(BattlefieldIsolation, EvenniaTestCase):
    """``explore.dialogue_leave`` ends the live session through the sole writer
    and writes nothing on rejection (webclient-align-11)."""

    def setUp(self):
        _t_dialogue_scope(self)
        from world.quests.catalog import register_catalog

        register_catalog()
        _reset_guardrail()
        register_npc_dialogue()
        get_world_clock()
        self.room1 = create_object(Room, key="起點")
        self.player = create_object(PlayerCharacter, key="對話.leave測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.host = create_object(NPC, key="客棧老板娘", location=self.room1)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_T_DIALOGUE)
        )

    def tearDown(self):
        _reset_guardrail()
        super().tearDown()

    def _open_session(self) -> None:
        result = _talk_scripted_adapter(
            self.player, {"npc_id": int(self.host.pk), "keyword_id": _T_LODGE_KEYWORD}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertIsNotNone(self.player.db.dialogue_session)

    @covers_requirement(
        "webclient-dialogue-session::explore-dialogue-leave-ends-the-live-session-through-the-sole-writer"
    )
    def test_success_clears_the_session_and_only_the_session(self):
        self._open_session()
        with patch.object(self.player, "msg"):
            result = _dialogue_leave_adapter(
                self.player, {"npc_id": int(self.host.pk)}
            )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "dialogue_left")
        self.assertIn("你結束了對話。", result["message"])
        self.assertIsNone(self.player.db.dialogue_session)
        # The full-snapshot affected set lets the dispatcher's completion
        # publish recompute the mode back to exploration.
        self.assertEqual(result["affected_panels"], ())

    def test_mismatched_npc_id_rejects_with_zero_writes(self):
        self._open_session()
        other = create_object(NPC, key="路人", location=self.room1)
        stored = self.player.db.dialogue_session
        result = _dialogue_leave_adapter(self.player, {"npc_id": int(other.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "dialogue_inactive")
        self.assertEqual(self.player.db.dialogue_session, stored)

    def test_no_live_session_rejects(self):
        result = _dialogue_leave_adapter(self.player, {"npc_id": int(self.host.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "dialogue_inactive")
        self.assertIsNone(self.player.db.dialogue_session)

if __name__ == "__main__":
    unittest.main()
