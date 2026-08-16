"""Tests for validator-driven retries, degrade paths, and offline behaviour."""


import unittest

from django.test import override_settings

from world.ai.fake_client import FakeLLMClient
from world.ai.npc_dialogue import (
    MAX_SPEECH_LENGTH,
    generate_npc_reply,
    register_npc_dialogue,
)
from world.ai.tests._dialogue_helpers import (
    _HeldDialogueClient,
    _memory,
    _npc_context,
    _player_context,
    _raw,
    _reply_text,
    _reset_all,
    await_result,
)

from tools.spec_traceability import covers_requirement



class ValidatorRetryTests(unittest.TestCase):
    def setUp(self):
        _reset_all()
        register_npc_dialogue()

    def tearDown(self):
        _reset_all()

    def _run(self, client, **profiles):
        with override_settings(LLM_PROFILES=_raw(**profiles)):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            return await_result(d)

    def _run_with_affinity(self, client, affinity, **profiles):
        with override_settings(LLM_PROFILES=_raw(**profiles)):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
                affinity_context=affinity,
            )
            return await_result(d)

    def _run_with_secrets(self, client, secrets, **profiles):
        with override_settings(LLM_PROFILES=_raw(**profiles)):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
                no_leak_secrets=secrets,
            )
            return await_result(d)

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_valid_adjust_relation_delta_passes_on_the_first_attempt(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(intent={"kind": "adjust_relation", "delta": 3}),
        )
        reply = self._run(client)
        self.assertEqual(reply.intent, {"kind": "adjust_relation", "delta": 3})
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_out_of_range_delta_payload_is_rejected_and_retried(self):
        for bad in (-1, 11, 1.5, True):
            with self.subTest(delta=bad):
                client = FakeLLMClient()
                client.add_response(
                    lambda d: len(d.messages) == 2,
                    _reply_text(intent={"kind": "adjust_relation", "delta": bad}),
                )
                client.add_response(
                    lambda d: len(d.messages) == 3, _reply_text()
                )
                reply = self._run(client)
                self.assertEqual(len(client.calls), 2)
                self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])
                self.assertEqual(reply.intent, {"kind": "none"})

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_missing_or_extra_delta_payload_is_rejected_and_retried(self):
        for intent in (
            {"kind": "adjust_relation"},
            {"kind": "adjust_relation", "delta": 3, "extra": 1},
        ):
            with self.subTest(intent=intent):
                client = FakeLLMClient()
                client.add_response(
                    lambda d: len(d.messages) == 2, _reply_text(intent=intent)
                )
                client.add_response(
                    lambda d: len(d.messages) == 3, _reply_text()
                )
                reply = self._run(client)
                self.assertEqual(len(client.calls), 2)
                self.assertIn("delta", client.calls[1].messages[-1]["content"])
                self.assertEqual(reply.intent, {"kind": "none"})

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_valid_party_invite_payload_passes_on_the_first_attempt(self):
        for accept in (True, False):
            with self.subTest(accept=accept):
                client = FakeLLMClient()
                client.add_response(
                    lambda d: True,
                    _reply_text(intent={"kind": "party_invite", "accept": accept}),
                )
                reply = self._run(client)
                self.assertEqual(
                    reply.intent, {"kind": "party_invite", "accept": accept}
                )
                self.assertEqual(len(client.calls), 1)

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_malformed_party_invite_payload_is_rejected_and_retried(self):
        for intent in (
            {"kind": "party_invite", "accept": "yes"},
            {"kind": "party_invite", "accept": 1},
            {"kind": "party_invite"},
            {"kind": "party_invite", "accept": True, "extra": 1},
        ):
            with self.subTest(intent=intent):
                client = FakeLLMClient()
                client.add_response(
                    lambda d: len(d.messages) == 2, _reply_text(intent=intent)
                )
                client.add_response(
                    lambda d: len(d.messages) == 3, _reply_text()
                )
                reply = self._run(client)
                self.assertEqual(len(client.calls), 2)
                self.assertIn("accept", client.calls[1].messages[-1]["content"])
                self.assertEqual(reply.intent, {"kind": "none"})

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_speech_echoing_the_secret_value_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(speech="我對你的好感已經到了 55 點。"),
        )
        client.add_response(lambda d: len(d.messages) == 3, _reply_text())
        reply = self._run_with_affinity(
            client, {"value": 55, "cap": 99, "stage": "信賴"}
        )
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])
        self.assertEqual(reply.speech, "艾洛希雅對你點頭。")

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_speech_mentioning_only_the_stage_name_passes(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="你是我信賴的人。"),
        )
        reply = self._run_with_affinity(
            client, {"value": 55, "cap": 99, "stage": "信賴"}
        )
        self.assertEqual(reply.speech, "你是我信賴的人。")
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_leak_exhausts_retries_and_degrades_never_presenting_the_number(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="我對你的好感是 55 點。"),
        )
        result = self._run_with_affinity(
            client,
            {"value": 55, "cap": 99, "stage": "信賴"},
            npc_dialogue={"max_retries": 1},
        )
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_no_affinity_context_disables_the_leak_check(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="我對你的好感是 55 點。"),
        )
        reply = self._run(client)
        self.assertEqual(reply.speech, "我對你的好感是 55 點。")
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_fullwidth_digit_echo_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(speech="我對你的好感是 ５５ 點。"),
        )
        client.add_response(lambda d: len(d.messages) == 3, _reply_text())
        reply = self._run_with_affinity(
            client, {"value": 55, "cap": 99, "stage": "信賴"}
        )
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])
        self.assertEqual(reply.speech, "艾洛希雅對你點頭。")

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_interleaved_calls_keep_their_own_leak_context(self):
        client_a = _HeldDialogueClient()
        client_b = _HeldDialogueClient()
        d_a = generate_npc_reply(
            client_a,
            npc_context=_npc_context(),
            player_context=_player_context(),
            memory=_memory(),
            affinity_context={"value": 55, "cap": 99, "stage": "信賴"},
        )
        d_b = generate_npc_reply(
            client_b,
            npc_context=_npc_context(),
            player_context=_player_context(),
            memory=_memory(),
            affinity_context={"value": 2, "cap": 99, "stage": "初識"},
        )
        # Each reply echoes the OTHER call's secret number: a per-call leak
        # validator must be the only check that applies, so both pass with no
        # retry. A module-global context would cross-contaminate the two calls.
        client_a.deferred.callback(_reply_text(speech="我的好感是 2 點。"))
        client_b.deferred.callback(_reply_text(speech="我的好感是 55 點。"))
        reply_a = await_result(d_a)
        reply_b = await_result(d_b)
        self.assertEqual(reply_a.speech, "我的好感是 2 點。")
        self.assertEqual(reply_b.speech, "我的好感是 55 點。")
        self.assertEqual(len(client_a.calls), 1)
        self.assertEqual(len(client_b.calls), 1)

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_secret_set_echo_is_rejected_and_retried_without_any_affinity_record(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(speech="我的真實攻擊是 88 點。"),
        )
        client.add_response(lambda d: len(d.messages) == 3, _reply_text())
        reply = self._run_with_secrets(client, frozenset({"88"}))
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])
        self.assertEqual(reply.speech, "艾洛希雅對你點頭。")

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_secret_set_passes_a_disguised_value_echo(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="我看你的攻擊大約是 60 點。"),
        )
        reply = self._run_with_secrets(client, frozenset({"88"}))
        self.assertEqual(reply.speech, "我看你的攻擊大約是 60 點。")
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_empty_secret_set_installs_no_leak_check(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="我的好感是 55 點。"))
        reply = self._run_with_secrets(client, frozenset())
        self.assertEqual(reply.speech, "我的好感是 55 點。")
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_secret_set_exhausts_retries_and_degrades_never_presenting_the_number(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="我的真實攻擊是 88 點。"),
        )
        result = self._run_with_secrets(
            client, frozenset({"88"}), npc_dialogue={"max_retries": 1}
        )
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_interleaved_calls_keep_their_own_secret_sets(self):
        client_a = _HeldDialogueClient()
        client_b = _HeldDialogueClient()
        d_a = generate_npc_reply(
            client_a,
            npc_context=_npc_context(),
            player_context=_player_context(),
            memory=_memory(),
            no_leak_secrets=frozenset({"55"}),
        )
        d_b = generate_npc_reply(
            client_b,
            npc_context=_npc_context(),
            player_context=_player_context(),
            memory=_memory(),
            no_leak_secrets=frozenset({"88"}),
        )
        # Each reply echoes the OTHER call's secret number: a per-call
        # validator must be the only check that applies, so both pass with no
        # retry. A module-global context would cross-contaminate the two calls.
        client_a.deferred.callback(_reply_text(speech="我的真實攻擊是 88 點。"))
        client_b.deferred.callback(_reply_text(speech="我的好感是 55 點。"))
        reply_a = await_result(d_a)
        reply_b = await_result(d_b)
        self.assertEqual(reply_a.speech, "我的真實攻擊是 88 點。")
        self.assertEqual(reply_b.speech, "我的好感是 55 點。")
        self.assertEqual(len(client_a.calls), 1)
        self.assertEqual(len(client_b.calls), 1)

    @covers_requirement("persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values")
    def test_secret_set_with_affinity_context_covers_both_sources(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(speech="我的真實攻擊是 88 點。"),
        )
        client.add_response(lambda d: len(d.messages) == 3, _reply_text())
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
                affinity_context={"value": 55, "cap": 99, "stage": "信賴"},
                no_leak_secrets=frozenset({"88", "55", "99"}),
            )
            reply = await_result(d)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(reply.speech, "艾洛希雅對你點頭。")

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_unknown_intent_kind_is_rejected_and_retried_with_error_appended(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(intent={"kind": "bogus"}),
        )
        client.add_response(
            lambda d: len(d.messages) == 3, _reply_text()
        )
        reply = self._run(client)
        self.assertEqual(reply.speech, "艾洛希雅對你點頭。")
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_malformed_exam_payload_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(intent={"kind": "request_guild_exam", "target_rank": "E", "extra": 1}),
        )
        client.add_response(
            lambda d: len(d.messages) == 3, _reply_text()
        )
        reply = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("target_rank", client.calls[1].messages[-1]["content"])

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_missing_target_rank_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(intent={"kind": "request_guild_exam"}),
        )
        client.add_response(
            lambda d: len(d.messages) == 3, _reply_text()
        )
        reply = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(reply.intent, {"kind": "none"})

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_item_intent_with_invalid_payload_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _reply_text(intent={"kind": "give_item", "item_key": "healing_potion"}),
        )
        client.add_response(
            lambda d: len(d.messages) == 3, _reply_text()
        )
        reply = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("qty", client.calls[1].messages[-1]["content"])

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_empty_nonchinese_and_placeholder_speech_are_rejected_and_retried(self):
        for bad_speech in ("   ", "plain ASCII prose", "{actor} 對你出手。"):
            with self.subTest(speech=bad_speech):
                client = FakeLLMClient()
                client.add_response(lambda d: len(d.messages) == 2, _reply_text(speech=bad_speech))
                client.add_response(lambda d: len(d.messages) == 3, _reply_text())
                reply = self._run(client)
                self.assertEqual(len(client.calls), 2)
                self.assertEqual(reply.speech, "艾洛希雅對你點頭。")

    @covers_requirement("npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline")
    def test_valid_bounded_reply_passes_on_the_first_attempt(self):
        speech = "艾洛希雅與你並肩而立。" * (MAX_SPEECH_LENGTH // 12)
        self.assertLessEqual(len(speech), MAX_SPEECH_LENGTH)
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech=speech))
        reply = self._run(client)
        self.assertEqual(reply.speech, speech)
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_overlong_speech_is_rejected_and_degrades_to_none(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True, _reply_text(speech="字" * (MAX_SPEECH_LENGTH + 1))
        )
        result = self._run(client, npc_dialogue={"max_retries": 0})
        self.assertIsNone(result)


class DegradePathTests(unittest.TestCase):
    def setUp(self):
        _reset_all()
        register_npc_dialogue()

    def tearDown(self):
        _reset_all()

    def _run(self, client, **profiles):
        with override_settings(LLM_PROFILES=_raw(**profiles)):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            return await_result(d)

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_disabled_profile_resolves_to_none_with_zero_client_calls(self):
        client = FakeLLMClient()
        result = self._run(client, npc_dialogue={"enabled": False})
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_transport_failure_resolves_to_none_with_one_client_call(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        result = self._run(client)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_exhausted_retries_resolve_to_none_within_the_budget(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text(speech="no chinese here"))
        result = self._run(client, npc_dialogue={"max_retries": 2})
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 3)

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_degraded_call_changes_no_state(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        result = self._run(client)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 1)
