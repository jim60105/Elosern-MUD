"""Tests for the ``LLMNPC`` generative-dialogue entity typeclass (npc-dialogue).

Covers the ``at_talked_to`` seam: valid-reply presentation and verified-intent
application, degraded greeting-or-silence, per-character chat-memory trimming,
the thinking-timer contract on a deterministic clock, the explicit ``None``
client rejection, the deferred-import rule that keeps the typeclass free of
module-scope generative imports, and the structured ``run_npc_exchange``
helper (party-core D-2) that separates the exchange from intent application.
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from twisted.internet import defer

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import LLMNPC
from world.ai import guardrail
from world.ai.fake_client import FakeLLMClient
from world.ai.npc_dialogue import (
    NPCDialogueClientRequiredError,
    register_npc_dialogue,
)
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.onboarding.guide_dialogue import GUILD_STAFF_DIALOGUE_KEY
from world.rules.affinity import apply_affinity_change
from world.rules.npc_intents import is_stale_context

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[2]


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _reset_all():
    guardrail._semantic_validators.clear()
    guardrail._degrade_fallbacks.clear()
    _OUTPUT_SCHEMAS.clear()


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _reply_text(speech="艾洛希雅對你點頭。", intent=None):
    return json.dumps(
        {"speech": speech, "intent": intent if intent is not None else {"kind": "none"}},
        ensure_ascii=False,
    )


def _inventory(entity):
    return list(entity.db.inventory or [])


def _msg_texts(msg_mock):
    return [str(call.args[0]) for call in msg_mock.call_args_list if call.args]


class _HeldClient:
    """Test double whose response is a Deferred the test resolves manually."""

    def __init__(self):
        self.deferred = defer.Deferred()
        self.calls = []

    def get_response(self, descriptor):
        self.calls.append(descriptor)
        return self.deferred


class DialogueExchangeHelperTests(EvenniaTest):
    """The structured ``run_npc_exchange`` helper (party-core D-2)."""

    def setUp(self):
        super().setUp()
        _reset_all()
        register_npc_dialogue()
        self.player = create_object(PlayerCharacter, key="exchange player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.npc = create_object(LLMNPC, key="交換精靈", location=self.room1)

    def tearDown(self):
        _reset_all()
        super().tearDown()

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_exchange_returns_a_reply_and_applies_no_intent(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(
                speech="我會考慮看看。",
                intent={"kind": "give_item", "item_key": "healing_potion", "qty": 1},
            ),
        )
        self.npc.db.inventory = ["healing_potion"]
        result = await_result(self.npc.run_npc_exchange("請與我同行", self.player, client))
        self.assertFalse(result.degraded)
        self.assertEqual(result.reply.speech, "我會考慮看看。")
        self.assertEqual(result.reply.intent["kind"], "give_item")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(_inventory(self.player), [])
        self.assertEqual(_inventory(self.npc), ["healing_potion"])
        lines = self.npc._chat_lines(self.player)
        self.assertEqual(lines, ["exchange player: 請與我同行", "交換精靈: 我會考慮看看。"])

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_exchange_marks_the_degraded_terminal_explicitly(self):
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            result = await_result(
                self.npc.run_npc_exchange("請與我同行", self.player, client)
            )
        self.assertTrue(result.degraded)
        self.assertIsNone(result.reply)
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_exchange_rejects_an_explicit_none_client(self):
        d = self.npc.run_npc_exchange("請與我同行", self.player, None)
        failure = await_result(d)
        self.assertTrue(failure.check(NPCDialogueClientRequiredError))

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_exchange_appends_only_the_reply_never_the_degraded_greeting(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="我願意與你同行。", intent={"kind": "none"}),
        )
        await_result(self.npc.run_npc_exchange("請與我同行", self.player, client))
        lines = self.npc._chat_lines(self.player)
        self.assertEqual(lines, ["exchange player: 請與我同行", "交換精靈: 我願意與你同行。"])


class LLMNPCSeamTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        _reset_all()
        register_npc_dialogue()
        self.player = create_object(PlayerCharacter, key="dialogue player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.npc = create_object(LLMNPC, key="對話精靈", location=self.room1)

    def tearDown(self):
        _reset_all()
        super().tearDown()

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_valid_reply_is_presented_and_verified_intent_applied(self):
        self.npc.db.inventory = ["healing_potion"]
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(
                speech="我給你一瓶藥水。",
                intent={"kind": "give_item", "item_key": "healing_potion", "qty": 1},
            ),
        )
        with patch.object(self.player, "msg") as msg:
            await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(len(client.calls), 1)
        texts = _msg_texts(msg)
        self.assertIn("我給你一瓶藥水。", " ".join(texts))
        self.assertEqual(_inventory(self.player), ["healing_potion"])
        self.assertEqual(_inventory(self.npc), [])
        lines = self.npc._chat_lines(self.player)
        self.assertEqual(lines, ["dialogue player: 你好", "對話精靈: 我給你一瓶藥水。"])

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_memory_is_appended_and_trimmed_to_the_window(self):
        self.npc.max_chat_memory_size = 2
        for greeting, reply in (
            ("問候一", "回應一。"),
            ("問候二", "回應二。"),
            ("問候三", "回應三。"),
        ):
            client = FakeLLMClient()
            client.add_response(lambda d: True, _reply_text(speech=reply))
            with patch.object(self.player, "msg"):
                await_result(self.npc.at_talked_to(greeting, self.player, client))
        lines = self.npc._chat_lines(self.player)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines, ["dialogue player: 問候三", "對話精靈: 回應三。"])

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_degraded_outcome_yields_the_authored_greeting_when_present(self):
        self.npc.components.add(
            ScriptedDialogue.create(self.npc, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch.object(self.player, "msg") as msg:
                await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(len(client.calls), 0)
        texts = _msg_texts(msg)
        self.assertEqual(len(texts), 1)
        self.assertIn("歡迎來到冒險者公會", texts[0])
        self.assertEqual(_inventory(self.player), [])

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_degraded_outcome_with_no_greeting_is_silence(self):
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch.object(self.player, "msg") as msg:
                await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(msg.call_count, 0)
        self.assertEqual(len(client.calls), 0)
        self.assertEqual(_inventory(self.player), [])
        lines = self.npc._chat_lines(self.player)
        self.assertEqual(len(lines), 1)

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_schedule_blocked_seam_shows_the_stable_reason_and_runs_nothing(self):
        self.npc.db.schedule_state = "busy"
        client = FakeLLMClient()
        with patch.object(self.player, "msg") as msg:
            await_result(self.npc.at_talked_to("你好", self.player, client))
        texts = _msg_texts(msg)
        self.assertEqual(texts, ["她現在正忙著，沒有理會你。"])
        self.assertEqual(len(client.calls), 0)
        self.assertEqual(self.npc._chat_lines(self.player), [])
        self.assertEqual(_inventory(self.player), [])

    @covers_requirement("npc-dialogue::async-dialogue-intents-revalidate-context-at-completion")
    def test_player_leaving_mid_exchange_shows_the_note_and_drops_the_intent(self):
        self.npc.db.inventory = ["healing_potion"]
        client = _HeldClient()
        with patch.object(self.player, "msg") as msg:
            d = self.npc.at_talked_to("你好", self.player, client)
            self.player.location = self.room2
            client.deferred.callback(
                _reply_text(
                    speech="我給你一瓶藥水。",
                    intent={"kind": "give_item", "item_key": "healing_potion", "qty": 1},
                )
            )
            outcome = await_result(d)
        self.assertFalse(outcome.applied)
        self.assertTrue(is_stale_context(outcome))
        texts = _msg_texts(msg)
        self.assertIn("我給你一瓶藥水。", " ".join(texts))
        self.assertTrue(any("離開" in text for text in texts))
        self.assertEqual(_inventory(self.player), [])
        self.assertEqual(_inventory(self.npc), ["healing_potion"])
        self.assertIn("對話精靈: 我給你一瓶藥水。", self.npc._chat_lines(self.player))

    @covers_requirement("npc-dialogue::async-dialogue-intents-revalidate-context-at-completion")
    def test_npc_leaving_mid_exchange_shows_the_note_and_drops_the_intent(self):
        self.npc.db.inventory = ["healing_potion"]
        client = _HeldClient()
        with patch.object(self.player, "msg") as msg:
            d = self.npc.at_talked_to("你好", self.player, client)
            self.npc.location = self.room2
            client.deferred.callback(
                _reply_text(
                    speech="我給你一瓶藥水。",
                    intent={"kind": "give_item", "item_key": "healing_potion", "qty": 1},
                )
            )
            outcome = await_result(d)
        self.assertTrue(is_stale_context(outcome))
        texts = _msg_texts(msg)
        self.assertIn("我給你一瓶藥水。", " ".join(texts))
        self.assertTrue(any("離開" in text for text in texts))
        self.assertEqual(_inventory(self.player), [])
        self.assertEqual(_inventory(self.npc), ["healing_potion"])
        self.assertIn("對話精靈: 我給你一瓶藥水。", self.npc._chat_lines(self.player))

    @covers_requirement("npc-dialogue::async-dialogue-intents-revalidate-context-at-completion")
    def test_busy_transition_mid_exchange_shows_the_note_and_drops_the_intent(self):
        self.npc.db.inventory = ["healing_potion"]
        client = _HeldClient()
        with patch.object(self.player, "msg") as msg:
            d = self.npc.at_talked_to("你好", self.player, client)
            self.npc.db.schedule_state = "busy"
            client.deferred.callback(
                _reply_text(
                    speech="我給你一瓶藥水。",
                    intent={"kind": "give_item", "item_key": "healing_potion", "qty": 1},
                )
            )
            outcome = await_result(d)
        self.assertTrue(is_stale_context(outcome))
        texts = _msg_texts(msg)
        self.assertIn("我給你一瓶藥水。", " ".join(texts))
        self.assertTrue(any("無法交談" in text for text in texts))
        self.assertEqual(_inventory(self.player), [])
        self.assertEqual(_inventory(self.npc), ["healing_potion"])

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_thinking_feedback_sends_one_message_after_timeout_and_cancels(self):
        from twisted.internet import task

        clock = task.Clock()
        client = _HeldClient()
        with patch.object(self.player, "msg") as msg:
            d = self.npc.at_talked_to("你好", self.player, client, reactor=clock)
            clock.advance(float(self.npc.thinking_timeout))
            self.assertEqual(
                _msg_texts(msg), [self.npc._thinking_text()]
            )
            client.deferred.callback(
                _reply_text(speech="回應終於來了。", intent={"kind": "none"})
            )
            await_result(d)
        texts = _msg_texts(msg)
        self.assertEqual(texts.count(self.npc._thinking_text()), 1)
        self.assertIn("回應終於來了。", " ".join(texts))
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_fast_reply_never_emits_a_thinking_message(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text())
        with patch.object(self.player, "msg") as msg:
            await_result(self.npc.at_talked_to("你好", self.player, client))
        texts = _msg_texts(msg)
        self.assertEqual(len(texts), 1)
        self.assertNotIn("沉思", texts[0])

    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_explicit_none_client_is_rejected_by_the_seam(self):
        d = self.npc.at_talked_to("你好", self.player, None)
        failure = await_result(d)
        self.assertTrue(failure.check(NPCDialogueClientRequiredError))

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_seam_injects_affinity_context_without_persisting(self):
        apply_affinity_change(self.npc, self.player, "ai_dialogue", 2)
        before = dict(self.npc.db.relations_data or {})
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="我會記住你的心意。"))
        with patch.object(self.player, "msg") as msg:
            await_result(self.npc.at_talked_to("你好", self.player, client))
        parsed = json.loads(client.calls[0].messages[-1]["content"])
        self.assertEqual(
            parsed["player"]["affinity"],
            {"value": 2, "cap": 99, "stage": "初識"},
        )
        self.assertEqual(dict(self.npc.db.relations_data or {}), before)
        self.assertIn("我會記住你的心意。", " ".join(_msg_texts(msg)))

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_recordless_player_yields_no_affinity_block_and_no_record(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="我會記住你的心意。"))
        with patch.object(self.player, "msg"):
            await_result(self.npc.at_talked_to("你好", self.player, client))
        parsed = json.loads(client.calls[0].messages[-1]["content"])
        self.assertNotIn("affinity", parsed["player"])
        self.assertFalse(self.npc.relations.has_record(self.player))

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_corrupted_relations_record_still_lets_the_talk_complete(self):
        self.npc.db.relations_data = {str(self.player.pk): "corrupted"}
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="我會記住你的心意。"))
        with patch.object(self.player, "msg") as msg:
            await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertIn("我會記住你的心意。", " ".join(_msg_texts(msg)))
        self.assertEqual(
            self.npc.db.relations_data, {str(self.player.pk): "corrupted"}
        )

    @covers_requirement("persona-dialogue-injection::persona-wiring-is-read-only-and-value-passing")
    @covers_requirement("persona-dialogue-injection::the-npc-s-own-persona-feeds-the-dialogue-system-message")
    @covers_requirement("persona-dialogue-injection::the-player-s-persona-feeds-the-user-payload-as-player-persona")
    def test_seam_injects_both_persona_blocks_and_never_mutates_the_records(self):
        self.npc.db.persona = {
            "personality": "沉穩",
            "life_story": "曾在邊境服役",
            "habit": "清晨練劍",
        }
        self.player.db.persona = {"personality": "溫柔", "life_story": "商人世家"}
        npc_before = dict(self.npc.db.persona)
        player_before = dict(self.player.db.persona)
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="我會記住你的心意。"))
        with patch.object(self.player, "msg"):
            await_result(self.npc.at_talked_to("你好", self.player, client))
        system = client.calls[0].messages[0]["content"]
        parsed = json.loads(client.calls[0].messages[-1]["content"])
        self.assertIn("性格：沉穩", system)
        self.assertIn("人生經歷：曾在邊境服役", system)
        self.assertIn("習慣：清晨練劍", system)
        self.assertEqual(parsed["player"]["persona"], "性格：溫柔\n人生經歷：商人世家")
        self.assertNotIn("{persona}", system)
        self.assertEqual(dict(self.npc.db.persona), npc_before)
        self.assertEqual(dict(self.player.db.persona), player_before)

    @covers_requirement("persona-dialogue-injection::the-npc-s-own-persona-feeds-the-dialogue-system-message")
    @covers_requirement("persona-dialogue-injection::the-player-s-persona-feeds-the-user-payload-as-player-persona")
    def test_seam_without_persona_injects_no_block_or_token(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="我會記住你的心意。"))
        with patch.object(self.player, "msg"):
            await_result(self.npc.at_talked_to("你好", self.player, client))
        system = client.calls[0].messages[0]["content"]
        parsed = json.loads(client.calls[0].messages[-1]["content"])
        self.assertNotIn("{persona}", system)
        self.assertNotIn("性格：", system)
        self.assertNotIn("persona", parsed["player"])

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_disguised_npc_true_value_echo_is_rejected_and_disguised_value_passes(self):
        self.npc.race = "human"
        self.npc.apply_race_baseline()
        self.npc.traits.atk_phys.base = 88
        self.npc.db.disguised_stats = {"atk_phys": 60}
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(speech="我的真實攻擊是 88 點。"),
        )
        client.add_response(
            lambda d: len(d.messages) == 3,
            _reply_text(speech="我看你的攻擊大約是 60 點。"),
        )
        with patch.object(self.player, "msg") as msg:
            await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(len(client.calls), 2)
        texts = " ".join(_msg_texts(msg))
        self.assertIn("我看你的攻擊", texts)
        self.assertNotIn("真實攻擊是 88", texts)

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_disguise_leak_check_fires_without_any_affinity_record(self):
        self.npc.race = "human"
        self.npc.apply_race_baseline()
        self.npc.traits.atk_phys.base = 88
        self.npc.db.disguised_stats = {"atk_phys": 60}
        self.assertFalse(self.npc.relations.has_record(self.player))
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(speech="我的真實攻擊是 88 點。"),
        )
        client.add_response(lambda d: len(d.messages) == 3, _reply_text())
        with patch.object(self.player, "msg"):
            await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_hp_is_protected_at_its_current_gauge_value_not_the_maximum(self):
        self.npc.race = "human"
        self.npc.apply_race_baseline()
        self.npc.traits.hp.base = 100
        self.npc.traits.hp.current = 40
        self.assertEqual(self.npc.traits.hp.value, 40)
        self.assertNotEqual(self.npc.traits.hp.value, self.npc.traits.hp.max)
        self.npc.db.disguised_stats = {"hp": 100}
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(speech="我的體力只剩 40 點。"),
        )
        client.add_response(
            lambda d: len(d.messages) == 3,
            _reply_text(speech="我的體力是 100 點。"),
        )
        with patch.object(self.player, "msg"):
            await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_no_disguise_keeps_affinity_only_binding(self):
        apply_affinity_change(self.npc, self.player, "ai_dialogue", 2)
        self.npc.db.disguised_stats = None
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="我的真實攻擊是 88 點。"),
        )
        with patch.object(self.player, "msg"):
            await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(len(client.calls), 1)
        parsed = json.loads(client.calls[0].messages[-1]["content"])
        self.assertEqual(parsed["player"]["affinity"]["value"], 2)

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_no_leak_secrets_bind_per_player_affinity_on_top_of_the_disguise_set(self):
        self.npc.race = "human"
        self.npc.apply_race_baseline()
        true_atk = int(self.npc.traits.atk_phys.value)
        self.npc.db.disguised_stats = {"atk_phys": true_atk + 10}
        apply_affinity_change(self.npc, self.player, "ai_dialogue", 2)
        second = create_object(PlayerCharacter, key="second player")
        second.race = "human"
        second.apply_race_baseline()
        second.location = self.room1
        self.assertEqual(
            self.npc._no_leak_secrets(self.player),
            frozenset({"2", "99", str(true_atk)}),
        )
        self.assertEqual(
            self.npc._no_leak_secrets(second), frozenset({str(true_atk)})
        )

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_disguised_traitless_npc_skips_missing_traits_and_talks_normally(self):
        self.npc.db.disguised_stats = {"atk_phys": 60}
        self.assertEqual(self.npc.traits.all(), [])
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="我會記住你的心意。"))
        with patch.object(self.player, "msg") as msg:
            await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(len(client.calls), 1)
        self.assertIn("我會記住你的心意。", " ".join(_msg_texts(msg)))

    @covers_requirement("persona-dialogue-injection::persona-wiring-is-read-only-and-value-passing")
    def test_building_a_prompt_persists_no_affinity_or_persona_state(self):
        apply_affinity_change(self.npc, self.player, "ai_dialogue", 2)
        self.npc.db.persona = {"personality": "沉穩"}
        self.player.db.persona = {"habit": "夜間閱讀"}
        relations_before = dict(self.npc.db.relations_data or {})
        npc_persona_before = dict(self.npc.db.persona)
        player_persona_before = dict(self.player.db.persona)
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="我會記住你的心意。"))
        with patch.object(self.player, "msg"):
            await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(dict(self.npc.db.relations_data or {}), relations_before)
        self.assertEqual(dict(self.npc.db.persona), npc_persona_before)
        self.assertEqual(dict(self.player.db.persona), player_persona_before)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_adjust_relation_flows_prompt_to_applier_to_record(self):
        apply_affinity_change(self.npc, self.player, "ai_dialogue", 2)
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(
                speech="我會記住你的心意。",
                intent={"kind": "adjust_relation", "delta": 3},
            ),
        )
        with patch.object(self.player, "msg") as msg:
            await_result(self.npc.at_talked_to("你好", self.player, client))
        parsed = json.loads(client.calls[0].messages[-1]["content"])
        self.assertEqual(parsed["player"]["affinity"]["value"], 2)
        self.assertIn("我會記住你的心意。", " ".join(_msg_texts(msg)))
        record = self.npc.relations._load(self.player)
        self.assertEqual(record.value, 5)
        self.assertEqual(record.daily_gain, 5)

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_leak_echo_reply_retries_and_never_presents_the_number(self):
        apply_affinity_change(self.npc, self.player, "ai_dialogue", 2)
        before = dict(self.npc.db.relations_data or {})
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(speech="我對你的好感是 2 點。"),
        )
        client.add_response(
            lambda d: len(d.messages) == 3,
            _reply_text(speech="我會記住你的心意。"),
        )
        with patch.object(self.player, "msg") as msg:
            await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(len(client.calls), 2)
        texts = " ".join(_msg_texts(msg))
        self.assertIn("我會記住你的心意。", texts)
        self.assertNotIn("2 點", texts)
        self.assertEqual(dict(self.npc.db.relations_data or {}), before)

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_offline_profile_leaves_affinity_unchanged(self):
        apply_affinity_change(self.npc, self.player, "ai_dialogue", 2)
        before = dict(self.npc.db.relations_data or {})
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            with patch.object(self.player, "msg"):
                await_result(self.npc.at_talked_to("你好", self.player, client))
        self.assertEqual(len(client.calls), 0)
        self.assertEqual(dict(self.npc.db.relations_data or {}), before)
        self.assertEqual(self.npc.relations.affinity_for(self.player), 2)


class LLMNPCDeferredImportTests(unittest.TestCase):
    @covers_requirement("npc-dialogue::the-llmnpc-entity-provides-chat-memory-thinking-state-and-a-dialogue-seam")
    def test_typeclass_import_stays_clear_of_module_scope_generative_imports(self):
        source = (
            "import os, sys\n"
            "os.environ['MUD_TEST_SETTINGS'] = '1'\n"
            "os.environ['DJANGO_SETTINGS_MODULE'] = 'server.conf.test_settings'\n"
            "sys.argv = ['evennia', 'test']\n"
            "import evennia\n"
            "assert evennia.logger is None, 'precondition: evennia not initialized'\n"
            "import django\n"
            "django.setup()\n"
            "import sys as _sys\n"
            "assert 'world.ai.guardrail' not in _sys.modules, 'settings-load reached the guardrail pre-init'\n"
            "evennia._init()\n"
            "import typeclasses.npcs\n"
            "assert 'world.ai.guardrail' not in _sys.modules, 'typeclass import pulled in the guardrail'\n"
            "assert 'world.rules.npc_intents' not in _sys.modules, 'typeclass import pulled in the applier'\n"
            "from world.ai import guardrail\n"
            "assert guardrail.logger is not None, 'guardrail logger bound to None'\n"
            "print('OK')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", source],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
