"""Tests for the NPC dialogue generative layer (npc-dialogue).

Covers prompt construction (deterministic, bounded, disguised-stats and
affinity-context injection, entity-key-only), the guarded reply entry point,
the eight-kind intent whitelist and per-kind payload semantic validators
(including the bounded ``adjust_relation`` delta, the boolean ``party_invite``
accept, and the affinity no-leak check), degrade-to-``None`` behaviour,
registration semantics, and the startup wiring.
"""

import dataclasses
import json
from unittest.mock import patch
import unittest

from django.test import override_settings
from twisted.internet import defer

from world.ai import guardrail
from world.ai import npc_dialogue
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import GuardrailRegistrationError
from world.ai.npc_dialogue import (
    MAX_MEMORY_LINES,
    MAX_SPEECH_LENGTH,
    MAX_TOTAL_SIZE,
    NPCDialogueClientRequiredError,
    NPCDialogueNotRegisteredError,
    NPCDialogueReply,
    build_npc_dialogue_prompt,
    generate_npc_reply,
    register_npc_dialogue,
)
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import DuplicateSchemaError, _OUTPUT_SCHEMAS

from tools.spec_traceability import covers_requirement


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _semantic_reset():
    guardrail._semantic_validators.clear()


def _fallback_reset():
    guardrail._degrade_fallbacks.clear()


def _schema_reset():
    _OUTPUT_SCHEMAS.clear()


def _reset_all():
    _semantic_reset()
    _fallback_reset()
    _schema_reset()


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _npc_context():
    return {"name": "艾洛希雅", "desc": "南門的守衛", "location": "王都阿爾托利亞"}


def _player_context(disguised=None):
    return {
        "name": "薇歐蕾",
        "disguised_stats": disguised
        if disguised is not None
        else {"atk_phys": 5, "agility": 6, "defense": 6},
    }


def _memory(n=3):
    return [f"第{i}則對話" for i in range(1, n + 1)]


def _reply_text(speech="艾洛希雅對你點頭。", intent=None):
    return json.dumps(
        {"speech": speech, "intent": intent if intent is not None else {"kind": "none"}},
        ensure_ascii=False,
    )


class _HeldDialogueClient:
    """Dialogue test double whose response is a Deferred the test resolves."""

    def __init__(self):
        self.deferred = defer.Deferred()
        self.calls = []

    def get_response(self, descriptor):
        self.calls.append(descriptor)
        return self.deferred


class NPCDialoguePromptTests(unittest.TestCase):
    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_identical_inputs_produce_byte_identical_prompts(self):
        first = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory()
        )
        second = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory()
        )
        self.assertEqual(first, second)
        self.assertEqual(first[0]["role"], "system")
        self.assertEqual(first[1]["role"], "user")
        self.assertEqual(first[0]["content"], second[0]["content"])
        self.assertEqual(first[1]["content"], second[1]["content"])

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_disguised_stats_are_injected_so_a_disguised_elf_reads_as_weak(self):
        disguised = {"atk_phys": 5, "agility": 6, "defense": 6}
        system, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(disguised=disguised), _memory()
        )
        parsed = json.loads(user["content"])
        self.assertEqual(parsed["player"]["disguised_stats"], disguised)
        self.assertIn("atk_phys", user["content"])
        self.assertNotIn("10000", user["content"])

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_oversized_memory_is_truncated_deterministically_with_a_marker(self):
        memory = [f"對話 {i}" for i in range(1, MAX_MEMORY_LINES * 3 + 1)]
        system, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), memory
        )
        parsed = json.loads(user["content"])
        self.assertLessEqual(len(parsed["memory"]), MAX_MEMORY_LINES + 1)
        self.assertTrue(any("省略了較早的" in line for line in parsed["memory"]))
        self.assertEqual(parsed["memory"][-1], "對話 36")
        self.assertEqual(parsed["memory"][-2], "對話 35")

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_prompt_is_bounded_and_contains_no_live_entity_reference(self):
        memory = [f"x" * 500 for _ in range(MAX_MEMORY_LINES * 2)]
        system, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), memory
        )
        self.assertLessEqual(len(user["content"]), MAX_TOTAL_SIZE)
        self.assertNotIn("<", user["content"])
        self.assertNotIn("object at", user["content"])
        parsed = json.loads(user["content"])
        self.assertLessEqual(
            max(len(line) for line in parsed["memory"]), 201
        )

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_system_message_fixes_role_language_and_output_contract(self):
        system, _ = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory()
        )
        content = system["content"]
        self.assertIn("艾洛希雅", content)
        self.assertIn("伊洛瑟恩大陸", content)
        self.assertIn("正體中文", content)
        self.assertIn("speech", content)
        self.assertIn("intent", content)
        self.assertIn("不得虛構", content)

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_prompt_uses_entity_keys_with_no_true_stats_present(self):
        system, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory()
        )
        self.assertIn("薇歐蕾", user["content"])
        self.assertNotIn("atk_phys", system["content"])


class AffinityPromptTests(unittest.TestCase):
    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_affinity_block_carries_the_true_value_cap_and_stage(self):
        context = {"value": 55, "cap": 99, "stage": "信賴"}
        system, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), affinity_context=context
        )
        parsed = json.loads(user["content"])
        self.assertEqual(
            parsed["player"]["affinity"],
            {"value": 55, "cap": 99, "stage": "信賴"},
        )

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_recordless_player_omits_the_affinity_block(self):
        _, user = build_npc_dialogue_prompt(
            _npc_context(),
            _player_context(),
            _memory(),
            affinity_context=None,
        )
        parsed = json.loads(user["content"])
        self.assertNotIn("affinity", parsed["player"])

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_prompts_stay_byte_identical_with_and_without_the_block(self):
        context = {"value": 55, "cap": 99, "stage": "信賴"}
        first = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), affinity_context=context
        )
        second = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), affinity_context=context
        )
        self.assertEqual(first, second)
        self.assertEqual(first[1]["content"], second[1]["content"])
        without = build_npc_dialogue_prompt(_npc_context(), _player_context(), _memory())
        plain = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), affinity_context=None
        )
        self.assertEqual(without, plain)
        self.assertNotEqual(first[1]["content"], without[1]["content"])
        self.assertIn('"affinity"', first[1]["content"])


class AffinityValidatorUnitTests(unittest.TestCase):
    """Direct shape tests for the adjust_relation and no-leak validators."""

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_relation_payload_requires_exactly_one_integer_delta_in_range(self):
        valid = {"kind": "adjust_relation", "delta": 3}
        self.assertEqual(
            npc_dialogue._validate_relation_payload({"speech": "s", "intent": valid}), []
        )
        for bad in (
            {"kind": "adjust_relation", "delta": -1},
            {"kind": "adjust_relation", "delta": 11},
            {"kind": "adjust_relation", "delta": 1.5},
            {"kind": "adjust_relation", "delta": True},
            {"kind": "adjust_relation"},
            {"kind": "adjust_relation", "delta": 3, "extra": 1},
        ):
            with self.subTest(intent=bad):
                self.assertTrue(
                    npc_dialogue._validate_relation_payload(
                        {"speech": "s", "intent": bad}
                    )
                )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_relation_validator_ignores_other_intent_kinds(self):
        for intent in (
            {"kind": "none"},
            {"kind": "request_guild_exam", "target_rank": "E"},
            {"kind": "give_item", "item_key": "x", "qty": 1},
        ):
            with self.subTest(intent=intent):
                self.assertEqual(
                    npc_dialogue._validate_relation_payload(
                        {"speech": "s", "intent": intent}
                    ),
                    [],
                )

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_no_leak_validator_rejects_value_and_cap_substrings(self):
        validate = npc_dialogue._make_no_affinity_leak_validator(55, 99)
        self.assertEqual(validate({"speech": "你是我的信賴。"}), [])
        self.assertTrue(validate({"speech": "好感 55 點。"}))
        self.assertTrue(validate({"speech": "上限是 99。"}))
        self.assertTrue(validate({"speech": "好感是 ５５ 點。"}))

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_no_leak_validator_is_bound_to_its_own_call_numbers(self):
        validate = npc_dialogue._make_no_affinity_leak_validator(55, 99)
        self.assertEqual(validate({"speech": "好感 2 點。"}), [])
        other = npc_dialogue._make_no_affinity_leak_validator(2, 99)
        self.assertTrue(other({"speech": "好感 2 點。"}))


class PartyInviteValidatorUnitTests(unittest.TestCase):
    """Direct shape tests for the party_invite semantic validator."""

    def test_party_payload_requires_exactly_one_boolean_accept(self):
        for valid in (True, False):
            with self.subTest(accept=valid):
                self.assertEqual(
                    npc_dialogue._validate_party_payload(
                        {"speech": "s", "intent": {"kind": "party_invite", "accept": valid}}
                    ),
                    [],
                )
        for bad in (
            {"kind": "party_invite"},
            {"kind": "party_invite", "accept": "yes"},
            {"kind": "party_invite", "accept": 1},
            {"kind": "party_invite", "accept": True, "extra": 1},
        ):
            with self.subTest(intent=bad):
                self.assertTrue(
                    npc_dialogue._validate_party_payload({"speech": "s", "intent": bad})
                )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_party_validator_ignores_other_intent_kinds(self):
        for intent in (
            {"kind": "none"},
            {"kind": "request_guild_exam", "target_rank": "E"},
            {"kind": "adjust_relation", "delta": 3},
        ):
            with self.subTest(intent=intent):
                self.assertEqual(
                    npc_dialogue._validate_party_payload(
                        {"speech": "s", "intent": intent}
                    ),
                    [],
                )

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_whitelist_and_schema_carry_party_invite(self):
        self.assertIn("party_invite", npc_dialogue.NPC_INTENT_KINDS)
        properties = npc_dialogue.NPC_DIALOGUE_OUTPUT_SCHEMA["properties"]["intent"]["properties"]
        self.assertEqual(properties["accept"], {"type": "boolean"})


class ReplyEntryPointTests(unittest.TestCase):
    def setUp(self):
        _reset_all()
        register_npc_dialogue()

    def tearDown(self):
        _reset_all()

    @covers_requirement("npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline")
    def test_valid_reply_resolves_to_a_frozen_reply_with_no_state_change(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="艾洛希雅對你點頭。", intent={"kind": "none"}),
        )
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            reply = await_result(d)
        self.assertIsInstance(reply, NPCDialogueReply)
        self.assertEqual(reply.speech, "艾洛希雅對你點頭。")
        self.assertEqual(reply.intent, {"kind": "none"})
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0].schema_id, "npc_dialogue")

    @covers_requirement("npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline")
    def test_schema_valid_reply_resolves_with_no_retry(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text())
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            reply = await_result(d)
        self.assertEqual(reply.speech, "艾洛希雅對你點頭。")
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline")
    def test_explicit_none_client_is_rejected_before_any_transport_work(self):
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                None,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            failure = await_result(d)
        self.assertTrue(failure.check(NPCDialogueClientRequiredError))

    @covers_requirement("npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline")
    def test_none_client_priority_over_an_exploding_memory_iterable(self):
        def exploding():
            raise RuntimeError("iterable exploded before any client check")
            yield  # pragma: no cover

        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                None,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=exploding(),
            )
            failure = await_result(d)
        self.assertTrue(failure.check(NPCDialogueClientRequiredError))

    @covers_requirement("npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline")
    def test_returned_value_is_a_plain_frozen_value_with_no_write_back_path(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text())
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            reply = await_result(d)
        self.assertTrue(dataclasses.is_dataclass(reply))
        self.assertTrue(dataclasses.is_dataclass(NPCDialogueReply))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            reply.speech = "changed"
        public_names = {
            name
            for name in dir(npc_dialogue)
            if not name.startswith("_") and not name.startswith("test")
        }
        self.assertFalse(any("parse" in name or "apply" in name for name in public_names))

    @covers_requirement("npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline")
    def test_degraded_call_resolves_to_none_never_a_sentinel(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            result = await_result(d)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 1)


class RegistrationGateTests(unittest.TestCase):
    def setUp(self):
        _reset_all()

    def tearDown(self):
        _reset_all()

    @covers_requirement("npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline")
    def test_calling_before_registration_errbacks_with_named_error(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _reply_text())
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            failure = await_result(d)
        self.assertTrue(failure.check(NPCDialogueNotRegisteredError))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline")
    def test_calling_after_registry_reset_errbacks_with_named_error(self):
        register_npc_dialogue()
        _reset_all()
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            failure = await_result(d)
        self.assertTrue(failure.check(NPCDialogueNotRegisteredError))

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_duplicate_registration_is_a_noop_keeping_the_first(self):
        register_npc_dialogue()
        register_npc_dialogue()
        self.assertTrue(npc_dialogue._is_registered())
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(npc_dialogue={"enabled": False})):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            result = await_result(d)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_partial_hook_registration_failure_leaves_no_npc_dialogue_hooks(self):
        calls = {"count": 0}

        def flaky_validator(layer, name, validator):
            calls["count"] += 1
            if calls["count"] == 2:
                raise GuardrailRegistrationError(
                    f"semantic validator {layer}.{name} already registered"
                )
            return guardrail.register_semantic_validator(layer, name, validator)

        with patch("world.ai.npc_dialogue.register_semantic_validator", flaky_validator):
            with self.assertRaises(GuardrailRegistrationError):
                register_npc_dialogue()
        self.assertNotIn("npc_dialogue", guardrail._degrade_fallbacks)
        self.assertEqual(guardrail._semantic_validators.get("npc_dialogue", {}), {})
        self.assertNotIn("npc_dialogue", _OUTPUT_SCHEMAS)

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_partial_own_state_is_rolled_back_on_a_later_failure(self):
        from world.ai.guardrail import register_degrade_fallback, register_semantic_validator

        register_degrade_fallback("npc_dialogue", npc_dialogue._degrade_fallback)
        names = list(npc_dialogue._VALIDATORS)
        first_name, foreign_name = names[0], names[1]
        register_semantic_validator(
            "npc_dialogue", first_name, npc_dialogue._VALIDATORS[first_name]
        )
        register_semantic_validator(
            "npc_dialogue", foreign_name, lambda parsed: ["foreign"]
        )
        with self.assertRaises(GuardrailRegistrationError):
            register_npc_dialogue()
        self.assertNotIn("npc_dialogue", guardrail._degrade_fallbacks)
        remaining = guardrail._semantic_validators.get("npc_dialogue", {})
        self.assertNotIn(first_name, remaining)
        self.assertIn(foreign_name, remaining)
        self.assertNotIn("npc_dialogue", _OUTPUT_SCHEMAS)

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_foreign_same_name_validator_does_not_pass_the_registration_gate(self):
        from world.ai.guardrail import register_degrade_fallback, register_semantic_validator

        register_degrade_fallback("npc_dialogue", npc_dialogue._degrade_fallback)
        for name, _ in npc_dialogue._VALIDATORS.items():
            register_semantic_validator(
                "npc_dialogue", name, lambda parsed: ["foreign"]
            )
        self.assertFalse(npc_dialogue._is_registered())
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_npc_reply(
                client,
                npc_context=_npc_context(),
                player_context=_player_context(),
                memory=_memory(),
            )
            failure = await_result(d)
        self.assertTrue(failure.check(NPCDialogueNotRegisteredError))

    @covers_requirement("npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind")
    def test_foreign_schema_registration_is_not_silently_overridden(self):
        from world.ai.guardrail import register_degrade_fallback, register_semantic_validator

        register_degrade_fallback("npc_dialogue", npc_dialogue._degrade_fallback)
        for name, validator in npc_dialogue._VALIDATORS.items():
            register_semantic_validator("npc_dialogue", name, validator)
        _OUTPUT_SCHEMAS["npc_dialogue"] = {"type": "object"}
        self.assertFalse(npc_dialogue._is_registered())
        with self.assertRaises(DuplicateSchemaError):
            register_npc_dialogue()
        self.assertNotIn("npc_dialogue", guardrail._degrade_fallbacks)
        self.assertEqual(guardrail._semantic_validators.get("npc_dialogue", {}), {})


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

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
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

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
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

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
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

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
    def test_no_affinity_context_disables_the_leak_check(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _reply_text(speech="我對你的好感是 55 點。"),
        )
        reply = self._run(client)
        self.assertEqual(reply.speech, "我對你的好感是 55 點。")
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
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

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-and-affinity-context")
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


class StartupRegistrationTests(unittest.TestCase):
    def setUp(self):
        _reset_all()

    def tearDown(self):
        _reset_all()

    @covers_requirement("npc-dialogue::the-generative-dialogue-layer-preserves-the-transport-and-single-writer-boundaries")
    def test_startup_seam_registers_the_layer_with_the_sentinel_fallback(self):
        from server.conf.at_server_startstop import _register_npc_dialogue_layer

        _register_npc_dialogue_layer()
        self.assertTrue(npc_dialogue._is_registered())
        self.assertIs(
            guardrail._degrade_fallbacks["npc_dialogue"],
            npc_dialogue._degrade_fallback,
        )

    @covers_requirement("npc-dialogue::the-generative-dialogue-layer-preserves-the-transport-and-single-writer-boundaries")
    def test_startup_seam_survives_a_foreign_npc_dialogue_registration(self):
        from server.conf.at_server_startstop import _register_npc_dialogue_layer
        from world.ai.guardrail import register_degrade_fallback

        register_degrade_fallback("npc_dialogue", lambda: "foreign-degrade")
        _register_npc_dialogue_layer()
        self.assertFalse(npc_dialogue._is_registered())


if __name__ == "__main__":
    unittest.main()
