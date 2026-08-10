"""Tests for the scene-flavor layer (scene-flavor).

Covers prompt construction (deterministic, bounded, four-value system
rendering, stable user JSON), the guarded generate entry point, the semantic
validation gates (length bounds, CJK surface, no digits), retry-and-degrade
behaviour, registration semantics, and the startup wiring.
"""

import json
from unittest.mock import patch
import unittest

from django.test import override_settings

from world.ai import guardrail
from world.ai import scene_flavor
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import GuardrailRegistrationError
from world.ai.scene_flavor import (
    MAX_FIELD_LENGTH,
    MAX_FLAVOR_LENGTH,
    MIN_FLAVOR_LENGTH,
    SceneFlavorClientRequiredError,
    SceneFlavorContext,
    SceneFlavorNotRegisteredError,
    build_scene_flavor_prompt,
    generate_scene_flavor,
    register_scene_flavor,
)
from world.ai.profiles import default_profiles
from world.prompts.loader import PromptUnavailableError

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


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _context(**overrides):
    values = {
        "scene_sentence": "古老森林深處的祭壇，石面上刻滿符文。",
        "quest_context": "採集任務：深入遺忘森林採集靈藥草",
        "room_name": "林間祭壇",
        "region": "遺忘森林",
    }
    values.update(overrides)
    return SceneFlavorContext(**values)


_VALID_FLAVOR = (
    "祭壇的苔石在幽暗中泛著微光，潮濕的泥土氣味與燃過的薰香交織，"
    "耳邊只有風穿過石縫的低鳴，靜得彷彿整座森林都在屏息凝視。"
)


class SceneFlavorPromptTests(unittest.TestCase):
    @covers_requirement("scene-flavor::the-flavor-prompt-is-deterministic-and-data-driven")
    def test_identical_contexts_produce_byte_identical_prompts(self):
        first = build_scene_flavor_prompt(_context())
        second = build_scene_flavor_prompt(_context())
        self.assertEqual(first, second)
        self.assertEqual(first[0]["role"], "system")
        self.assertEqual(first[1]["role"], "user")
        self.assertEqual(first[0]["content"], second[0]["content"])
        self.assertEqual(first[1]["content"], second[1]["content"])

    @covers_requirement("scene-flavor::the-flavor-prompt-is-deterministic-and-data-driven")
    def test_system_message_substitutes_all_four_capped_values(self):
        context = _context(
            scene_sentence="古老森林深處的祭壇",
            quest_context="採集任務：採集靈藥草",
            room_name="林間祭壇",
            region="遺忘森林",
        )
        system, _ = build_scene_flavor_prompt(context)
        self.assertIn("古老森林深處的祭壇", system["content"])
        self.assertIn("採集任務：採集靈藥草", system["content"])
        self.assertIn("林間祭壇", system["content"])
        self.assertIn("遺忘森林", system["content"])
        self.assertNotIn("{scene_sentence}", system["content"])
        self.assertNotIn("{quest_context}", system["content"])
        self.assertNotIn("{room_name}", system["content"])
        self.assertNotIn("{region}", system["content"])

    @covers_requirement("scene-flavor::the-flavor-prompt-is-deterministic-and-data-driven")
    def test_user_message_is_stable_sorted_json_of_the_bounded_context(self):
        system, user = build_scene_flavor_prompt(_context())
        parsed = json.loads(user["content"])
        self.assertEqual(
            parsed,
            {
                "scene_sentence": "古老森林深處的祭壇，石面上刻滿符文。",
                "quest_context": "採集任務：深入遺忘森林採集靈藥草",
                "room_name": "林間祭壇",
                "region": "遺忘森林",
            },
        )
        self.assertNotIn("\\u", user["content"])
        self.assertNotIn("\\u", system["content"])

    @covers_requirement("scene-flavor::the-flavor-prompt-is-deterministic-and-data-driven")
    def test_oversized_context_fragments_are_capped_within_module_bounds(self):
        long_text = "字" * (MAX_FIELD_LENGTH * 2)
        system, user = build_scene_flavor_prompt(
            _context(
                scene_sentence=long_text,
                quest_context=long_text,
                room_name=long_text,
                region=long_text,
            )
        )
        self.assertLessEqual(len(system["content"]), MAX_FIELD_LENGTH * 5)
        self.assertLessEqual(len(user["content"]), MAX_FIELD_LENGTH * 5)
        parsed = json.loads(user["content"])
        for key in ("scene_sentence", "quest_context", "room_name", "region"):
            self.assertLessEqual(len(parsed[key]), MAX_FIELD_LENGTH)
        self.assertIn("…", parsed["scene_sentence"])

    def test_context_is_never_materialized_from_live_entities(self):
        system, user = build_scene_flavor_prompt(_context())
        for message in (system["content"], user["content"]):
            self.assertNotIn("<", message)
            self.assertNotIn("object at", message)


class SceneFlavorEntryPointTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()
        register_scene_flavor()

    def tearDown(self):
        _semantic_reset()
        _fallback_reset()

    @covers_requirement("scene-flavor::the-scene-flavor-layer-is-a-pure-guarded-generative-layer-on-the-scene-builder-profile")
    @covers_requirement("scene-flavor::the-flavor-output-is-plain-text-with-deterministic-gates")
    def test_valid_flavor_resolves_with_no_state_change(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _VALID_FLAVOR)
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_scene_flavor(_context(), client)
            result = await_result(d)
        self.assertEqual(result, _VALID_FLAVOR)
        self.assertEqual(len(client.calls), 1)
        self.assertIsInstance(result, str)
        public_names = {
            name
            for name in dir(scene_flavor)
            if not name.startswith("_") and not name.startswith("test")
        }
        self.assertFalse(any("write" in name or "apply" in name for name in public_names))

    @covers_requirement("scene-flavor::the-scene-flavor-layer-is-a-pure-guarded-generative-layer-on-the-scene-builder-profile")
    def test_explicit_none_client_is_rejected_before_any_work(self):
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_scene_flavor(_context(), None)
            failure = await_result(d)
        self.assertTrue(failure.check(SceneFlavorClientRequiredError))

    @covers_requirement("scene-flavor::the-scene-flavor-layer-is-a-pure-guarded-generative-layer-on-the-scene-builder-profile")
    def test_disabled_profile_short_circuits_to_none_with_zero_client_calls(self):
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(scene_builder={"enabled": False})):
            d = generate_scene_flavor(_context(), client)
            result = await_result(d)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("scene-flavor::the-flavor-output-is-plain-text-with-deterministic-gates")
    def test_transport_failure_resolves_to_none(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_scene_flavor(_context(), client)
            result = await_result(d)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("scene-flavor::the-flavor-prompt-is-deterministic-and-data-driven")
    def test_prompt_unavailable_key_degrades_to_none(self):
        client = FakeLLMClient()
        with patch(
            "world.ai.scene_flavor.render_prompt",
            side_effect=PromptUnavailableError(
                "scene_builder.yaml", "scene_builder.system", "broken"
            ),
        ):
            with override_settings(LLM_PROFILES=_raw()):
                d = generate_scene_flavor(_context(), client)
                result = await_result(d)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 0)


class SceneFlavorValidatorTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()
        register_scene_flavor()

    def tearDown(self):
        _semantic_reset()
        _fallback_reset()

    @covers_requirement("scene-flavor::the-flavor-output-is-plain-text-with-deterministic-gates")
    def test_flavor_containing_digits_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            "風中飄來 3 隻狼的低吼，森林深處一片死寂，微光穿過層疊樹影。",
        )
        client.add_response(lambda d: len(d.messages) == 3, _VALID_FLAVOR)
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_scene_flavor(_context(), client)
            result = await_result(d)
        self.assertEqual(result, _VALID_FLAVOR)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])

    @covers_requirement("scene-flavor::the-flavor-output-is-plain-text-with-deterministic-gates")
    def test_fullwidth_digit_is_also_rejected(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            "風中飄來 ３ 隻狼的低吼，森林深處一片死寂，微光穿過層疊樹影。",
        )
        client.add_response(lambda d: len(d.messages) == 3, _VALID_FLAVOR)
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_scene_flavor(_context(), client)
            result = await_result(d)
        self.assertEqual(result, _VALID_FLAVOR)
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scene-flavor::the-flavor-output-is-plain-text-with-deterministic-gates")
    def test_non_chinese_flavor_is_rejected_and_never_returned(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, "The altar glows in the dim forest. " * 3)
        with override_settings(LLM_PROFILES=_raw(scene_builder={"max_retries": 0})):
            d = generate_scene_flavor(_context(), client)
            result = await_result(d)
        self.assertIsNone(result)

    @covers_requirement("scene-flavor::the-flavor-output-is-plain-text-with-deterministic-gates")
    def test_undersized_flavor_is_rejected(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, "祭壇微光。")
        with override_settings(LLM_PROFILES=_raw(scene_builder={"max_retries": 0})):
            d = generate_scene_flavor(_context(), client)
            result = await_result(d)
        self.assertIsNone(result)

    @covers_requirement("scene-flavor::the-flavor-output-is-plain-text-with-deterministic-gates")
    def test_overlong_flavor_is_rejected(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, "字" * (MAX_FLAVOR_LENGTH + 1))
        with override_settings(LLM_PROFILES=_raw(scene_builder={"max_retries": 0})):
            d = generate_scene_flavor(_context(), client)
            result = await_result(d)
        self.assertIsNone(result)

    @covers_requirement("scene-flavor::the-flavor-output-is-plain-text-with-deterministic-gates")
    def test_retry_exhaustion_degrades_to_none(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            "風中飄來 3 隻狼的低吼，森林深處一片死寂，微光穿過層疊樹影。",
        )
        with override_settings(LLM_PROFILES=_raw(scene_builder={"max_retries": 1})):
            d = generate_scene_flavor(_context(), client)
            result = await_result(d)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scene-flavor::the-flavor-output-is-plain-text-with-deterministic-gates")
    def test_retry_appends_the_error_message_under_the_profile_budget(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            "風中飄來 3 隻狼的低吼，森林深處一片死寂，微光穿過層疊樹影。",
        )
        client.add_response(lambda d: len(d.messages) == 3, _VALID_FLAVOR)
        with override_settings(LLM_PROFILES=_raw(scene_builder={"max_retries": 1})):
            d = generate_scene_flavor(_context(), client)
            result = await_result(d)
        self.assertEqual(result, _VALID_FLAVOR)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("digit", client.calls[1].messages[-1]["content"])


class SceneFlavorRegistrationTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()

    def tearDown(self):
        _semantic_reset()
        _fallback_reset()

    @covers_requirement("scene-flavor::the-scene-flavor-layer-is-a-pure-guarded-generative-layer-on-the-scene-builder-profile")
    def test_generating_before_registration_errbacks_with_named_error(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _VALID_FLAVOR)
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_scene_flavor(_context(), client)
            failure = await_result(d)
        self.assertTrue(failure.check(SceneFlavorNotRegisteredError))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("scene-flavor::the-scene-flavor-layer-is-a-pure-guarded-generative-layer-on-the-scene-builder-profile")
    def test_duplicate_registration_is_a_noop(self):
        register_scene_flavor()
        register_scene_flavor()
        self.assertTrue(scene_flavor._is_registered())

    @covers_requirement("scene-flavor::the-scene-flavor-layer-is-a-pure-guarded-generative-layer-on-the-scene-builder-profile")
    def test_partial_hook_registration_failure_leaves_no_hooks(self):
        calls = {"count": 0}

        def flaky_validator(layer, name, validator):
            calls["count"] += 1
            if calls["count"] == 2:
                raise GuardrailRegistrationError(
                    f"semantic validator {layer}.{name} already registered"
                )
            return guardrail.register_semantic_validator(layer, name, validator)

        with patch("world.ai.scene_flavor.register_semantic_validator", flaky_validator):
            with self.assertRaises(GuardrailRegistrationError):
                register_scene_flavor()
        self.assertNotIn("scene_builder", guardrail._degrade_fallbacks)
        self.assertEqual(
            guardrail._semantic_validators.get("scene_builder", {}), {}
        )

    @covers_requirement("scene-flavor::the-scene-flavor-layer-is-a-pure-guarded-generative-layer-on-the-scene-builder-profile")
    def test_partial_own_state_is_rolled_back_on_a_later_failure(self):
        from world.ai.guardrail import register_degrade_fallback

        register_degrade_fallback("scene_builder", scene_flavor._degrade_fallback)
        names = list(scene_flavor._VALIDATORS)
        first_name, foreign_name = names[0], names[1]
        guardrail.register_semantic_validator(
            "scene_builder", first_name, scene_flavor._VALIDATORS[first_name]
        )
        guardrail.register_semantic_validator(
            "scene_builder", foreign_name, lambda parsed: ["foreign"]
        )
        with self.assertRaises(GuardrailRegistrationError):
            register_scene_flavor()
        self.assertNotIn("scene_builder", guardrail._degrade_fallbacks)
        remaining = guardrail._semantic_validators.get("scene_builder", {})
        self.assertNotIn(first_name, remaining)
        self.assertIn(foreign_name, remaining)

    @covers_requirement("scene-flavor::the-scene-flavor-layer-is-a-pure-guarded-generative-layer-on-the-scene-builder-profile")
    def test_foreign_same_name_hooks_do_not_pass_the_registration_gate(self):
        for name, _ in scene_flavor._VALIDATORS.items():
            guardrail.register_semantic_validator(
                "scene_builder", name, lambda parsed: ["foreign"]
            )
        self.assertFalse(scene_flavor._is_registered())
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_scene_flavor(_context(), client)
            failure = await_result(d)
        self.assertTrue(failure.check(SceneFlavorNotRegisteredError))


class SceneFlavorStartupRegistrationTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()

    def tearDown(self):
        _semantic_reset()
        _fallback_reset()

    @covers_requirement("scene-flavor::the-scene-flavor-layer-is-a-pure-guarded-generative-layer-on-the-scene-builder-profile")
    def test_startup_seam_registers_the_layer_with_the_sentinel_fallback(self):
        from server.conf.at_server_startstop import _register_scene_flavor_layer

        _register_scene_flavor_layer()
        self.assertTrue(scene_flavor._is_registered())
        self.assertIs(
            guardrail._degrade_fallbacks["scene_builder"],
            scene_flavor._degrade_fallback,
        )

    @covers_requirement("scene-flavor::the-scene-flavor-layer-is-a-pure-guarded-generative-layer-on-the-scene-builder-profile")
    def test_startup_seam_survives_a_foreign_scene_flavor_registration(self):
        from server.conf.at_server_startstop import _register_scene_flavor_layer

        guardrail.register_degrade_fallback("scene_builder", lambda: "foreign-degrade")
        _register_scene_flavor_layer()
        self.assertFalse(scene_flavor._is_registered())


if __name__ == "__main__":
    unittest.main()
