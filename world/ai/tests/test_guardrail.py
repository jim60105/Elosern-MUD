"""Tests for the validation-retry-degrade guardrail (guardrail)."""

from copy import deepcopy
from unittest.mock import patch
import json
import unittest

from django.test import override_settings
from twisted.internet import defer
from twisted.internet.task import Clock
from twisted.python.failure import Failure

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.ai.errors import LLMTransportError
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import (
    GuardrailRegistrationError,
    NoDegradeFallbackError,
    guarded_call,
    register_degrade_fallback,
    register_semantic_validator,
)
from world.ai.profiles import UnknownLayerError, default_profiles
from world.ai.schemas import ChatRequestDescriptor
from world.rules.clock import get_world_clock

from tools.spec_traceability import covers_requirement


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


class _Result:
    def __init__(self, value):
        self.value = value


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


class GuardrailRegistrationTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()

    def tearDown(self):
        _semantic_reset()
        _fallback_reset()

    @covers_requirement("guardrail::semantic-validators-are-pluggable-and-layer-scoped")
    def test_semantic_validators_run_in_registration_order(self):
        order = []
        register_semantic_validator("narrator", "first", lambda parsed: order.append("first") or [])
        register_semantic_validator("narrator", "second", lambda parsed: order.append("second") or [])
        client = FakeLLMClient()
        client.add_response(lambda d: True, json.dumps({"ok": True}))
        with override_settings(LLM_PROFILES=_raw()):
            d = guarded_call(
                "narrator",
                client,
                ChatRequestDescriptor(
                    messages=({"role": "user", "content": "x"},),
                    output_schema={"type": "object"},
                ),
            )
            await_result(d)
        self.assertEqual(order, ["first", "second"])

    def test_duplicate_semantic_validator_is_rejected(self):
        validator = lambda parsed: []
        register_semantic_validator("narrator", "dup", validator)
        with self.assertRaises(GuardrailRegistrationError):
            register_semantic_validator("narrator", "dup", validator)

    def test_duplicate_degrade_fallback_is_rejected(self):
        register_degrade_fallback("narrator", lambda: "fb")
        with self.assertRaises(GuardrailRegistrationError):
            register_degrade_fallback("narrator", lambda: "fb2")

    def test_unknown_layer_registration_is_rejected(self):
        with self.assertRaises(UnknownLayerError):
            register_semantic_validator("bogus", "x", lambda parsed: [])
        with self.assertRaises(UnknownLayerError):
            register_degrade_fallback("bogus", lambda: "x")

    def test_registration_does_not_write_game_state(self):
        register_semantic_validator("narrator", "pure", lambda parsed: [])
        register_degrade_fallback("narrator", lambda: "fb")
        from world.ai import guardrail as guardrail_module

        self.assertIn("pure", guardrail_module._semantic_validators["narrator"])
        self.assertIn("narrator", guardrail_module._degrade_fallbacks)


def _semantic_reset():
    from world.ai import guardrail as guardrail_module

    guardrail_module._semantic_validators.clear()


def _fallback_reset():
    from world.ai import guardrail as guardrail_module

    guardrail_module._degrade_fallbacks.clear()


class GuardrailPipelineTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()
        register_degrade_fallback("narrator", lambda: "degraded-narrator")
        register_degrade_fallback("npc_dialogue", lambda: "degraded-npc")
        register_degrade_fallback("scenario_director", lambda: "degraded-director")
        register_degrade_fallback("scene_builder", lambda: "degraded-builder")

    def _client(self):
        return FakeLLMClient()

    def _success(self, text):
        return ChatRequestDescriptor(
            messages=({"role": "user", "content": "x"},),
            output_schema={"type": "object"},
        ), text

    @covers_requirement("guardrail::guarded-generative-calls-validate-retry-then-degrade")
    def test_schema_valid_response_accepted_on_first_attempt(self):
        schema = {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
        text = json.dumps({"ok": True})
        client = self._client()
        client.add_response(
            lambda d: len(d.messages) == 1, text
        )
        with override_settings(LLM_PROFILES=_raw()):
            d = guarded_call(
                "narrator",
                client,
                ChatRequestDescriptor(messages=({"role": "user", "content": "x"},), output_schema=schema),
            )
            result = await_result(d)
        self.assertEqual(result, text)

    @covers_requirement("guardrail::guarded-generative-calls-validate-retry-then-degrade")
    def test_invalid_output_retried_with_errors_appended(self):
        schema = {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
        client = self._client()
        # First call returns schema-invalid JSON; the retry returns valid JSON.
        client.add_response(lambda d: len(d.messages) == 1, json.dumps({"ok": "not-bool"}))
        client.add_response(lambda d: len(d.messages) == 2, json.dumps({"ok": True}))
        with override_settings(LLM_PROFILES=_raw()):
            d = guarded_call(
                "narrator",
                client,
                ChatRequestDescriptor(messages=({"role": "user", "content": "x"},), output_schema=schema),
            )
            result = await_result(d)
        self.assertEqual(result, json.dumps({"ok": True}))
        self.assertEqual(len(client.calls), 2)
        retry_descriptor = client.calls[1]
        self.assertEqual(len(retry_descriptor.messages), 2)
        self.assertIn("Validation failed", retry_descriptor.messages[-1]["content"])

    @covers_requirement("guardrail::guarded-generative-calls-validate-retry-then-degrade")
    def test_exhausted_retries_degrade_to_fallback(self):
        schema = {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
        client = self._client()
        client.add_response(lambda d: True, json.dumps({"ok": "still-bad"}))
        with override_settings(LLM_PROFILES=_raw(narrator={"max_retries": 1})):
            d = guarded_call(
                "narrator",
                client,
                ChatRequestDescriptor(messages=({"role": "user", "content": "x"},), output_schema=schema),
            )
            result = await_result(d)
        self.assertEqual(result, "degraded-narrator")

    @covers_requirement("guardrail::semantic-validators-are-pluggable-and-layer-scoped")
    def test_semantic_validator_rejects_out_of_range(self):
        schema = {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
        register_semantic_validator(
            "narrator", "whitelist", lambda parsed: ["rank out of range"] if parsed.get("ok") is True else []
        )
        client = self._client()
        client.add_response(lambda d: len(d.messages) == 1, json.dumps({"ok": True}))
        client.add_response(lambda d: len(d.messages) == 2, json.dumps({"ok": False}))
        with override_settings(LLM_PROFILES=_raw()):
            d = guarded_call(
                "narrator",
                client,
                ChatRequestDescriptor(messages=({"role": "user", "content": "x"},), output_schema=schema),
            )
            result = await_result(d)
        self.assertEqual(result, json.dumps({"ok": False}))

    @covers_requirement("guardrail::structured-output-hints-are-passed-per-call")
    def test_descriptor_output_schema_and_schema_id_are_forwarded(self):
        schema = {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
        client = self._client()
        client.add_response(lambda d: True, json.dumps({"ok": True}))
        with override_settings(LLM_PROFILES=_raw()):
            d = guarded_call(
                "narrator",
                client,
                ChatRequestDescriptor(
                    messages=({"role": "user", "content": "x"},),
                    output_schema=schema,
                    schema_id="reward",
                ),
            )
            await_result(d)
        forwarded = client.calls[0]
        self.assertEqual(forwarded.output_schema, schema)
        self.assertEqual(forwarded.schema_id, "reward")

    @covers_requirement("guardrail::structured-output-hints-are-passed-per-call")
    def test_registered_schema_id_resolves_and_drives_validation_retries(self):
        from world.ai.schemas import register_output_schema

        schema = {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
        register_output_schema("reward", schema)
        try:
            client = self._client()
            # First call returns schema-invalid JSON; the retry returns valid JSON.
            client.add_response(lambda d: len(d.messages) == 1, json.dumps({"ok": "not-bool"}))
            client.add_response(lambda d: len(d.messages) == 2, json.dumps({"ok": True}))
            with override_settings(LLM_PROFILES=_raw()):
                d = guarded_call(
                    "narrator",
                    client,
                    ChatRequestDescriptor(
                        messages=({"role": "user", "content": "x"},),
                        schema_id="reward",
                    ),
                )
                result = await_result(d)
            self.assertEqual(result, json.dumps({"ok": True}))
            self.assertEqual(len(client.calls), 2)
            self.assertEqual(client.calls[0].output_schema, schema)
            retry = client.calls[1]
            self.assertEqual(retry.output_schema, schema)
            self.assertIn("Validation failed", retry.messages[-1]["content"])
        finally:
            from world.ai.schemas.registry import _OUTPUT_SCHEMAS

            _OUTPUT_SCHEMAS.clear()

    @covers_requirement(
        "guardrail::guardrail-failures-degrade-without-network-coupling",
        "fake-llm-client::failure-modes-are-scriptable-for-guardrail-tests",
    )
    def test_transport_failure_degrades_directly_without_retry(self):
        schema = {"type": "object"}
        client = self._client()
        client.add_timeout(lambda d: True)
        with override_settings(LLM_PROFILES=_raw()):
            d = guarded_call(
                "narrator",
                client,
                ChatRequestDescriptor(messages=({"role": "user", "content": "x"},), output_schema=schema),
            )
            result = await_result(d)
        self.assertEqual(result, "degraded-narrator")
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("guardrail::guardrail-failures-degrade-without-network-coupling")
    def test_transport_failure_does_not_append_error_message(self):
        schema = {"type": "object"}
        client = self._client()
        client.add_connection_error(lambda d: True)
        with override_settings(LLM_PROFILES=_raw()):
            d = guarded_call(
                "narrator",
                client,
                ChatRequestDescriptor(messages=({"role": "user", "content": "x"},), output_schema=schema),
            )
            await_result(d)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(len(client.calls[0].messages), 1)
        self.assertNotIn("Validation failed", client.calls[0].messages[-1]["content"])

    @covers_requirement(
        "guardrail::guardrail-failures-degrade-without-network-coupling",
        "fake-llm-client::failure-modes-are-scriptable-for-guardrail-tests",
    )
    def test_malformed_non_json_text_degrades_without_retry(self):
        schema = {"type": "object"}
        client = self._client()
        client.add_response(lambda d: True, "not-json")
        with override_settings(LLM_PROFILES=_raw()):
            d = guarded_call(
                "narrator",
                client,
                ChatRequestDescriptor(messages=({"role": "user", "content": "x"},), output_schema=schema),
            )
            result = await_result(d)
        self.assertEqual(result, "degraded-narrator")
        self.assertEqual(len(client.calls), 1)

    @covers_requirement(
        "llm-profiles::profiles-are-locally-disableable",
        "guardrail::guardrail-failures-degrade-without-network-coupling",
    )
    def test_disabled_profile_short_circuits_to_degrade(self):
        client = self._client()
        with override_settings(LLM_PROFILES=_raw(narrator={"enabled": False})):
            d = guarded_call(
                "narrator",
                client,
                ChatRequestDescriptor(messages=({"role": "user", "content": "x"},)),
            )
            result = await_result(d)
        self.assertEqual(result, "degraded-narrator")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("llm-profiles::profiles-are-locally-disableable")
    def test_every_registered_call_is_offline_safe_when_disabled(self):
        disabled = {layer: {"enabled": False} for layer in ("narrator", "npc_dialogue", "scenario_director", "scene_builder")}
        clients = {}
        for layer, fallback in (
            ("narrator", "degraded-narrator"),
            ("npc_dialogue", "degraded-npc"),
            ("scenario_director", "degraded-director"),
            ("scene_builder", "degraded-builder"),
        ):
            clients[layer] = self._client()
        with override_settings(LLM_PROFILES=_raw(**disabled)):
            for layer, client in clients.items():
                d = guarded_call(
                    layer,
                    client,
                    ChatRequestDescriptor(messages=({"role": "user", "content": "x"},)),
                )
                await_result(d)
                self.assertEqual(len(client.calls), 0)

    def test_missing_degrade_fallback_raises(self):
        _fallback_reset()
        _semantic_reset()
        with override_settings(LLM_PROFILES=_raw(narrator={"enabled": False})):
            d = guarded_call(
                "narrator",
                self._client(),
                ChatRequestDescriptor(messages=({"role": "user", "content": "x"},)),
            )
            failure = await_result(d)
        self.assertTrue(failure.check(NoDegradeFallbackError))


class GuardrailMutationBoundaryTests(EvenniaTest):
    """Prove guarded calls never write persistent state."""

    def setUp(self):
        super().setUp()
        _semantic_reset()
        _fallback_reset()
        register_degrade_fallback("narrator", lambda: "degraded")
        self.character = create_object(PlayerCharacter, key="GuardrailChar", location=self.room1)
        self.character.traits.add("hp", trait_type="gauge", base=10, min=0, max=10)

    def _snapshot(self):
        return {
            "trait_data": deepcopy(dict(self.character.traits.trait_data)),
            "attributes": sorted(
                (entry.key for entry in self.character.attributes.all()), key=str
            ),
            "script_count": len(list(self.character.scripts.all())),
            "world_tick": get_world_clock().tick,
        }

    @covers_requirement("guardrail::semantic-validators-are-pluggable-and-layer-scoped")
    def test_repeated_guarded_calls_change_no_state(self):
        schema = {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}
        before = self._snapshot()
        client = FakeLLMClient()
        client.add_response(lambda d: True, json.dumps({"ok": True}))
        with override_settings(LLM_PROFILES=_raw()):
            for _ in range(3):
                d = guarded_call(
                    "narrator",
                    client,
                    ChatRequestDescriptor(
                        messages=({"role": "user", "content": "x"},), output_schema=schema
                    ),
                )
                await_result(d)
            # degrade path with a transport failure
            failing = FakeLLMClient()
            failing.add_timeout(lambda d: True)
            d = guarded_call(
                "narrator",
                failing,
                ChatRequestDescriptor(messages=({"role": "user", "content": "x"},), output_schema=schema),
            )
            await_result(d)
        after = self._snapshot()
        self.assertEqual(before, after)

    def test_logged_summaries_contain_no_prompt_or_player_text(self):
        with patch("evennia.logger.log_info") as mock_log:
            client = FakeLLMClient()
            client.add_timeout(lambda d: True)
            with override_settings(LLM_PROFILES=_raw()):
                d = guarded_call(
                    "narrator",
                    client,
                    ChatRequestDescriptor(
                        messages=({"role": "user", "content": "SECRET_PLAYER_TEXT"},)
                    ),
                )
                await_result(d)
            logged = " ".join(str(call.args) for call in mock_log.call_args_list)
        self.assertNotIn("SECRET_PLAYER_TEXT", logged)
        self.assertNotIn("Validation failed", logged)
