"""Tests for the guarded reply entry point, registration gates, and startup wiring."""


import dataclasses
from unittest.mock import patch
import unittest

from django.test import override_settings

from world.ai import guardrail
from world.ai import npc_dialogue
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import GuardrailRegistrationError
from world.ai.npc_dialogue import (
    NPCDialogueClientRequiredError,
    NPCDialogueNotRegisteredError,
    NPCDialogueReply,
    generate_npc_reply,
    register_npc_dialogue,
)
from world.ai.schemas.registry import DuplicateSchemaError, _OUTPUT_SCHEMAS
from world.ai.tests._dialogue_helpers import (
    _memory,
    _npc_context,
    _player_context,
    _raw,
    _reply_text,
    _reset_all,
    await_result,
)

from tools.spec_traceability import covers_requirement



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
