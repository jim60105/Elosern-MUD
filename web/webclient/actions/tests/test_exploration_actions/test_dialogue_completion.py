"""Behavior test: the ``explore.dialogue_complete`` action and text parity.

Pins the exact five-field composed payload, the adapter's stable rejection
codes (nothing written on a rejection), the accepted path committing reading,
and the text interface: a complete attributed emission marks each node, a
partial emission marks nothing, and naming a public successor before its
predecessor is saved answers with the fixed refusal without writing.
"""

from __future__ import annotations

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.talk import CmdsTalk
from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.exploration_actions import (
    ExplorationActionError,
    _dialogue_complete_adapter,
    validate_dialogue_complete_payload,
)
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic
from world.lore.scenes import Scene, Speech
from world.narrative.dialogue_reading import completed_topic_ids
from world.rules.affinity_config import get_config
from world.rules.dialogue import (
    clear_dialogue_session,
    live_dialogue_session,
    select_authored_topic,
)
from world.rules.dialogue_context import host_dialogue_binding
from world.quests.catalog import register_catalog
from world.tests.synthetic_data import synthetic_registries

_TABLE_KEY = "t_completion_keeper"
_ROOT = f"{_TABLE_KEY}.root"
_CHILD = f"{_TABLE_KEY}.child"


def _scene(scene_id: str, text: str) -> Scene:
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(
            Speech(speaker="actor", text="合成問句。"),
            Speech(speaker="host", text=text),
        ),
    )


def _dialogue() -> AuthoredDialogue:
    return AuthoredDialogue(
        greeting="合成櫃檯後的人抬眼。",
        topics=(
            AuthoredTopic(
                topic_id=_ROOT,
                keyword="合成起頭",
                label="合成起頭",
                fallback=_scene("t_completion_root", "合成起頭內文"),
            ),
            AuthoredTopic(
                topic_id=_CHILD,
                keyword="合成接續",
                label="合成接續",
                fallback=_scene("t_completion_child", "合成接續內文"),
                predecessors=(_ROOT,),
                disclosure="pure_chain",
            ),
        ),
    )


class DialogueCompletionActionTests(EvenniaTest):
    """Validator, adapter and text-emission completion."""

    def setUp(self) -> None:
        super().setUp()
        register_catalog()
        get_config()
        scope = synthetic_registries(
            "dialogue", extra={"dialogue": {_TABLE_KEY: _dialogue()}}
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.room = create_object(Room, key="合成完成廳")
        self.player = create_object(PlayerCharacter, key="合成完成玩家")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.host = create_object(NPC, key="合成完成店主", location=self.room)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_TABLE_KEY)
        )

    def tearDown(self) -> None:
        clear_dialogue_session(self.player)
        super().tearDown()

    def _host_key(self) -> str:
        return host_dialogue_binding(self.host)[0]

    def _select(self, topic_id: str = _ROOT, *, selection_id: str = "sel-complete"):
        session = live_dialogue_session(self.player)
        return select_authored_topic(
            self.player,
            self.host,
            topic_id,
            selection_id=selection_id,
            expected_context_id=session.context_id if session is not None else None,
        )

    def _payload(self, delivery) -> dict:
        return {
            "npc_id": int(self.host.pk),
            "delivery_id": delivery.delivery_id,
            "context_id": delivery.context_id,
            "topic_id": delivery.topic_id,
            "scene_revision": delivery.scene_revision,
        }

    # -- validator -------------------------------------------------------

    def test_validator_accepts_exactly_the_composed_payload(self):
        payload = {
            "npc_id": 4,
            "delivery_id": "abc123",
            "context_id": "ctx123",
            "topic_id": _ROOT,
            "scene_revision": "r1",
        }
        self.assertEqual(validate_dialogue_complete_payload(payload), payload)
        for extra in (
            {"selection_id": "sel"},
            {"availability": "open"},
            {"owner_id": 1},
        ):
            with self.subTest(extra=extra):
                with self.assertRaises(ExplorationActionError):
                    validate_dialogue_complete_payload({**payload, **extra})
        with self.assertRaises(ExplorationActionError):
            validate_dialogue_complete_payload({**payload, "npc_id": 0})
        with self.assertRaises(ExplorationActionError):
            validate_dialogue_complete_payload({**payload, "delivery_id": ""})
        with self.assertRaises(ExplorationActionError):
            validate_dialogue_complete_payload({**payload, "context_id": ""})

    # -- adapter ---------------------------------------------------------

    def test_adapter_records_the_completion(self):
        delivery = self._select()
        result = _dialogue_complete_adapter(self.player, self._payload(delivery))
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "dialogue_completed")
        self.assertEqual(
            completed_topic_ids(self.player, self._host_key()), (_ROOT,)
        )
        repeated = _dialogue_complete_adapter(self.player, self._payload(delivery))
        self.assertEqual(repeated["outcome"], "success")

    def test_adapter_rejects_forged_claims_without_state(self):
        delivery = self._select()
        forged = {**self._payload(delivery), "delivery_id": "0000000000000000"}
        result = _dialogue_complete_adapter(self.player, forged)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "dialogue_receipt_unknown")
        self.assertEqual(completed_topic_ids(self.player, self._host_key()), ())

    def test_adapter_rejects_a_foreign_host_identity(self):
        delivery = self._select()
        other = create_object(NPC, key="合成完成路人", location=self.room)
        result = _dialogue_complete_adapter(
            self.player, {**self._payload(delivery), "npc_id": int(other.pk)}
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "stale_context")
        self.assertEqual(completed_topic_ids(self.player, self._host_key()), ())

    # -- text parity -----------------------------------------------------

    def _run_talk(self, args: str, *, msg=None) -> str:
        messages: list[str] = []
        with patch.object(
            self.player, "msg", side_effect=msg or messages.append
        ):
            command = CmdsTalk()
            command.caller = self.player
            command.args = args
            command.func()
        return "\n".join(messages)

    def test_text_full_emission_completes_the_chain(self):
        output = self._run_talk(f"{self.host.key} 合成起頭")
        self.assertIn("合成起頭內文", output)
        self.assertIn("合成接續內文", output)
        self.assertEqual(
            completed_topic_ids(self.player, self._host_key()), (_ROOT, _CHILD)
        )

    def test_text_partial_emission_marks_nothing(self):
        calls: list[str] = []

        def _fail_on_host_line(text: str) -> None:
            calls.append(text)
            if "合成起頭內文" in text:
                raise RuntimeError("transport died")

        output = self._run_talk(
            f"{self.host.key} 合成起頭", msg=_fail_on_host_line
        )
        # Emission stopped at the failed line: the actor line went out, the
        # chain was never attempted, and nothing was marked or echoed.
        self.assertEqual(len(calls), 2)
        self.assertEqual(output, "")
        self.assertEqual(completed_topic_ids(self.player, self._host_key()), ())

    def test_text_naming_a_successor_before_its_predecessor_is_refused(self):
        output = self._run_talk(f"{self.host.key} 合成接續")
        self.assertIn("前面的話還沒說完", output)
        self.assertNotIn("合成接續內文", output)
        self.assertIsNone(live_dialogue_session(self.player))
        self.assertEqual(completed_topic_ids(self.player, self._host_key()), ())
