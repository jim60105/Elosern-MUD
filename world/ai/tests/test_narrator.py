"""Tests for the narrator layer (narrator).

Covers prompt construction (deterministic, bounded, entity-key-only), the
guarded narrate entry point, degrade-to-template behavior, registration
semantics, semantic validators, and the settings-load wiring.
"""

import json
from unittest.mock import patch
import unittest

from django.test import override_settings

from world.ai import guardrail
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import GuardrailRegistrationError
from world.ai import narrator
from world.ai.narrator import (
    MAX_ENTRIES,
    MAX_FIELD_LENGTH,
    MAX_PROSE_LENGTH,
    MAX_TOTAL_SIZE,
    NarratorClientRequiredError,
    NarratorNotRegisteredError,
    build_narrator_prompt,
    narrate_event_logs,
    register_narrator,
)
from world.ai.profiles import default_profiles
from world.rules.event_log import EventEntry, EventLog, render_plain_text

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


def _entry(kind="damage", actor="elosia", target="violet", data=None, template=None):
    return EventEntry(
        kind=kind,
        actor=actor,
        target=target,
        data=data or {"amount": 12},
        text_template=template or "{actor} 對 {target} 造成 {data[amount]} 點傷害。",
    )


def _log(actor="elosia", skill_key="basic_attack", targets=("violet",), entries=None):
    return EventLog(
        actor=actor,
        skill_key=skill_key,
        targets=tuple(targets),
        entries=tuple(entries or (_entry(),)),
        time_cost_seconds=5,
    )


def _join_renderer(logs):
    return "\n".join(render_plain_text(log) for log in logs)


class NarratorPromptTests(unittest.TestCase):
    @covers_requirement("narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_identical_inputs_produce_byte_identical_prompts(self):
        log = _log()
        first = build_narrator_prompt((log,))
        second = build_narrator_prompt((log,))
        self.assertEqual(first, second)
        self.assertEqual(first[0]["role"], "system")
        self.assertEqual(first[1]["role"], "user")
        self.assertEqual(first[0]["content"], second[0]["content"])
        self.assertEqual(first[1]["content"], second[1]["content"])

    @covers_requirement("narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_prompt_carries_the_full_deterministic_record(self):
        log = _log()
        system, user = build_narrator_prompt((log,))
        parsed = json.loads(user["content"])
        self.assertEqual(len(parsed["event_logs"]), 1)
        payload = parsed["event_logs"][0]
        self.assertEqual(payload["actor"], "elosia")
        self.assertEqual(payload["skill_key"], "basic_attack")
        self.assertEqual(payload["targets"], ["violet"])
        self.assertEqual(payload["time_cost_seconds"], 5)
        self.assertEqual(payload["entries"][0]["kind"], "damage")
        self.assertEqual(payload["entries"][0]["text_template"], log.entries[0].text_template)

    @covers_requirement("narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_large_combat_round_produces_a_bounded_prompt(self):
        entries = [_entry() for _ in range(MAX_ENTRIES * 2)]
        log = EventLog(
            actor="a" * (MAX_FIELD_LENGTH * 2),
            skill_key="long" * (MAX_FIELD_LENGTH * 2),
            targets=("t" * (MAX_FIELD_LENGTH * 2),),
            entries=tuple(entries),
            time_cost_seconds=5,
        )
        system, user = build_narrator_prompt((log,))
        self.assertLessEqual(len(user["content"]), MAX_TOTAL_SIZE)
        parsed = json.loads(user["content"])
        self.assertIn("truncated_entries", parsed)
        self.assertTrue(parsed["truncated_entries"] > 0)
        self.assertEqual(len(parsed["event_logs"][0]["entries"]), MAX_ENTRIES)
        self.assertLessEqual(len(parsed["event_logs"][0]["actor"]), MAX_FIELD_LENGTH)

    @covers_requirement("narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_prompt_carries_entity_keys_and_no_live_references(self):
        log = _log()
        system, user = build_narrator_prompt((log,))
        self.assertIn("elosia", user["content"])
        self.assertIn("violet", user["content"])
        self.assertNotIn("<", user["content"])
        self.assertNotIn("object at", user["content"])
        parsed = json.loads(user["content"])
        self.assertEqual(parsed["event_logs"][0]["actor"], "elosia")
        self.assertEqual(parsed["event_logs"][0]["entries"][0]["target"], "violet")

    @covers_requirement("narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_system_message_requires_fidelity_and_traditional_chinese(self):
        system, _ = build_narrator_prompt((_log(),))
        self.assertIn("正體中文", system["content"])
        self.assertIn("不得虛構", system["content"])
        self.assertIn("伊洛瑟恩大陸", system["content"])

    @covers_requirement("narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_overwhelm_summary_preserves_team_keys_and_data_within_bounds(self):
        summary_entry = EventEntry(
            kind="overwhelm_resolution",
            actor="team_a",
            target="team_b",
            data={"rounds": 3, "hits": 5, "total_damage": 120},
            text_template="團隊 {actor} 壓倒了 {target}。",
        )
        log = EventLog(
            actor="team_a",
            skill_key="overwhelm",
            targets=("team_b",),
            entries=(summary_entry,),
            time_cost_seconds=0,
        )
        system, user = build_narrator_prompt((log,))
        parsed = json.loads(user["content"])
        entry = parsed["event_logs"][0]["entries"][0]
        self.assertEqual(entry["kind"], "overwhelm_resolution")
        self.assertEqual(entry["actor"], "team_a")
        self.assertEqual(entry["target"], "team_b")
        self.assertEqual(
            entry["data"],
            {"rounds": 3, "hits": 5, "total_damage": 120},
        )
        self.assertLessEqual(len(user["content"]), MAX_TOTAL_SIZE)

    @covers_requirement("narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_prompt_stays_valid_json_for_pathological_inputs(self):
        huge_data = {"k%d" % i: "x" * 500 for i in range(500)}
        wide_log = EventLog(
            actor="a" * 500,
            skill_key="s" * 500,
            targets=tuple("t%d" % i for i in range(500)),
            entries=tuple(_entry(data=huge_data) for _ in range(200)),
            time_cost_seconds=5,
        )
        many_empty_logs = [
            EventLog(
                actor="actor%d" % i,
                skill_key="key%d" % i,
                targets=tuple("t%d" % j for j in range(50)),
                entries=(),
                time_cost_seconds=1,
            )
            for i in range(200)
        ]
        for logs in ((wide_log,), tuple(many_empty_logs), (wide_log, *many_empty_logs)):
            with self.subTest(logs=len(logs)):
                system, user = build_narrator_prompt(logs)
                self.assertLessEqual(len(user["content"]), MAX_TOTAL_SIZE)
                parsed = json.loads(user["content"])
                self.assertIn("event_logs", parsed)


class NarrateEntryPointTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()
        register_narrator(_join_renderer)

    def tearDown(self):
        _semantic_reset()
        _fallback_reset()

    @covers_requirement("narrator::narrator-maps-eventlogs-to-traditional-chinese-prose-through-the-guarded-pipeline")
    def test_valid_client_response_resolves_to_prose_with_no_state_change(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, "艾洛希雅揮劍斬向薇歐蕾，造成十二點傷害。")
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, "艾洛希雅揮劍斬向薇歐蕾，造成十二點傷害。")
        self.assertEqual(len(client.calls), 1)
        self.assertIsInstance(result, str)

    @covers_requirement("narrator::narrator-maps-eventlogs-to-traditional-chinese-prose-through-the-guarded-pipeline")
    def test_multiple_event_logs_narrate_as_one_coherent_passage(self):
        first = _log(actor="elosia")
        second = _log(actor="violet", skill_key="basic_attack", targets=("elosia",))
        client = FakeLLMClient()
        client.add_response(lambda d: True, "兩段紀錄合而為一。")
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((first, second), client)
            result = await_result(d)
        self.assertEqual(result, "兩段紀錄合而為一。")
        self.assertEqual(len(client.calls), 1)
        parsed = json.loads(client.calls[0].messages[1]["content"])
        self.assertEqual(len(parsed["event_logs"]), 2)
        self.assertEqual(parsed["event_logs"][0]["actor"], "elosia")
        self.assertEqual(parsed["event_logs"][1]["actor"], "violet")

    @covers_requirement("narrator::narrator-maps-eventlogs-to-traditional-chinese-prose-through-the-guarded-pipeline")
    def test_explicit_none_client_is_rejected_before_any_transport_work(self):
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), None)
            failure = await_result(d)
        self.assertTrue(failure.check(NarratorClientRequiredError))

    @covers_requirement("narrator::narrator-maps-eventlogs-to-traditional-chinese-prose-through-the-guarded-pipeline")
    def test_none_client_priority_over_a_throwing_iterable(self):
        def exploding():
            raise RuntimeError("iterable exploded before any client check")
            yield  # pragma: no cover

        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs(exploding(), None)
            failure = await_result(d)
        self.assertTrue(failure.check(NarratorClientRequiredError))

    @covers_requirement("narrator::narrator-maps-eventlogs-to-traditional-chinese-prose-through-the-guarded-pipeline")
    def test_returned_value_is_plain_prose_with_no_write_back_path(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, "純文本敘事。")
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertIsInstance(result, str)
        public_names = {
            name
            for name in dir(narrator)
            if not name.startswith("_") and not name.startswith("test")
        }
        self.assertFalse(any("parse" in name or "apply" in name for name in public_names))

    @covers_requirement(
        "narrator::narrator-prompt-construction-is-deterministic-bounded-and-faithful",
        "narrator::narrator-degrades-to-deterministic-template-rendering-when-the-pipeline-fails",
    )
    def test_oversized_input_degrades_to_full_template_with_zero_client_calls(self):
        entries = [_entry() for _ in range(MAX_ENTRIES + 1)]
        log = EventLog(
            actor="elosia",
            skill_key="basic_attack",
            targets=("violet",),
            entries=tuple(entries),
            time_cost_seconds=5,
        )
        client = FakeLLMClient()
        client.add_response(lambda d: True, "不應被使用的回應。")
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((log,), client)
            result = await_result(d)
        self.assertEqual(result, _join_renderer((log,)))
        self.assertEqual(len(client.calls), 0)


class NarratorDegradeTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()
        register_narrator(_join_renderer)

    def tearDown(self):
        _semantic_reset()
        _fallback_reset()

    @covers_requirement("narrator::narrator-degrades-to-deterministic-template-rendering-when-the-pipeline-fails")
    def test_disabled_profile_returns_template_prose_with_zero_client_calls(self):
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(narrator={"enabled": False})):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, _join_renderer((_log(),)))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("narrator::narrator-degrades-to-deterministic-template-rendering-when-the-pipeline-fails")
    def test_transport_failure_degrades_to_template_prose(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, _join_renderer((_log(),)))
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("narrator::narrator-degrades-to-deterministic-template-rendering-when-the-pipeline-fails")
    def test_exhausted_validation_retries_degrade_to_template_prose(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, "not chinese prose")
        with override_settings(LLM_PROFILES=_raw(narrator={"max_retries": 1})):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, _join_renderer((_log(),)))
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("narrator::narrator-degrades-to-deterministic-template-rendering-when-the-pipeline-fails")
    def test_degraded_output_is_byte_identical_to_template_rendering(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, _join_renderer((_log(),)))


class NarratorRegistrationTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()

    def tearDown(self):
        _semantic_reset()
        _fallback_reset()

    @covers_requirement("narrator::narrator-preserves-the-single-writer-and-transport-boundaries")
    def test_narrating_before_registration_errbacks_with_named_error(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, "不該回傳。")
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            failure = await_result(d)
        self.assertTrue(failure.check(NarratorNotRegisteredError))

    @covers_requirement("narrator::narrator-preserves-the-single-writer-and-transport-boundaries")
    def test_narrating_after_registry_reset_errbacks_with_named_error(self):
        register_narrator(_join_renderer)
        _semantic_reset()
        _fallback_reset()
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            failure = await_result(d)
        self.assertTrue(failure.check(NarratorNotRegisteredError))

    @covers_requirement("narrator::narrator-preserves-the-single-writer-and-transport-boundaries")
    def test_duplicate_registration_keeps_the_first_renderer(self):
        register_narrator(lambda logs: "FIRST")
        register_narrator(lambda logs: "SECOND")
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(narrator={"enabled": False})):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, "FIRST")
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("narrator::narrator-preserves-the-single-writer-and-transport-boundaries")
    def test_partial_hook_registration_failure_leaves_no_narrator_hooks(self):
        calls = {"count": 0}

        def flaky_validator(layer, name, validator):
            calls["count"] += 1
            if calls["count"] == 2:
                raise GuardrailRegistrationError(
                    f"semantic validator {layer}.{name} already registered"
                )
            return guardrail.register_semantic_validator(layer, name, validator)

        with patch("world.ai.narrator.register_semantic_validator", flaky_validator):
            with self.assertRaises(GuardrailRegistrationError):
                register_narrator(_join_renderer)
        self.assertNotIn("narrator", guardrail._degrade_fallbacks)
        self.assertEqual(guardrail._semantic_validators.get("narrator", {}), {})

    @covers_requirement("narrator::narrator-preserves-the-single-writer-and-transport-boundaries")
    def test_partial_own_state_is_rolled_back_on_a_later_failure(self):
        from world.ai.guardrail import register_degrade_fallback, register_semantic_validator

        register_degrade_fallback("narrator", narrator._degrade_fallback)
        names = list(narrator._VALIDATORS)
        first_name, foreign_name = names[0], names[1]
        register_semantic_validator("narrator", first_name, narrator._VALIDATORS[first_name])
        register_semantic_validator("narrator", foreign_name, lambda parsed: ["foreign"])
        with self.assertRaises(GuardrailRegistrationError):
            register_narrator(_join_renderer)
        self.assertNotIn("narrator", guardrail._degrade_fallbacks)
        remaining = guardrail._semantic_validators.get("narrator", {})
        self.assertNotIn(first_name, remaining)
        self.assertIn(foreign_name, remaining)

    @covers_requirement("narrator::narrator-preserves-the-single-writer-and-transport-boundaries")
    def test_foreign_same_name_validator_does_not_pass_the_registration_gate(self):
        from world.ai.guardrail import register_degrade_fallback, register_semantic_validator

        register_degrade_fallback("narrator", narrator._degrade_fallback)
        for name, _ in narrator._VALIDATORS.items():
            register_semantic_validator("narrator", name, lambda parsed: ["foreign"])
        self.assertFalse(narrator._is_registered())
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            failure = await_result(d)
        self.assertTrue(failure.check(NarratorNotRegisteredError))


class NarratorValidatorTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()
        register_narrator(_join_renderer)

    def tearDown(self):
        _semantic_reset()
        _fallback_reset()

    @covers_requirement("narrator::narrator-semantic-validation-keeps-prose-within-safe-bounds")
    def test_empty_prose_is_rejected_and_retried_with_error_appended(self):
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, "   ")
        client.add_response(lambda d: len(d.messages) == 3, "艾洛希雅發出空揮。")
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, "艾洛希雅發出空揮。")
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])

    @covers_requirement("narrator::narrator-semantic-validation-keeps-prose-within-safe-bounds")
    def test_non_chinese_prose_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, "nothing here")
        client.add_response(lambda d: len(d.messages) == 3, "艾洛希雅向薇歐蕾點頭。")
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, "艾洛希雅向薇歐蕾點頭。")
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("narrator::narrator-semantic-validation-keeps-prose-within-safe-bounds")
    def test_template_placeholder_leakage_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, "{actor} 對 {target} 出手。")
        client.add_response(lambda d: len(d.messages) == 3, "艾洛希雅出手。")
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, "艾洛希雅出手。")
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("narrator::narrator-semantic-validation-keeps-prose-within-safe-bounds")
    def test_bounded_length_chinese_prose_passes_on_first_attempt(self):
        prose = "艾洛希雅與薇歐蕾在長廊上對峙。" * (MAX_PROSE_LENGTH // 20)
        self.assertLessEqual(len(prose), MAX_PROSE_LENGTH)
        client = FakeLLMClient()
        client.add_response(lambda d: True, prose)
        with override_settings(LLM_PROFILES=_raw()):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, prose)
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("narrator::narrator-semantic-validation-keeps-prose-within-safe-bounds")
    def test_overlong_prose_is_rejected_and_degrades(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, "字" * (MAX_PROSE_LENGTH + 1))
        with override_settings(LLM_PROFILES=_raw(narrator={"max_retries": 0})):
            d = narrate_event_logs((_log(),), client)
            result = await_result(d)
        self.assertEqual(result, _join_renderer((_log(),)))


class NarratorStartupRegistrationTests(unittest.TestCase):
    def setUp(self):
        _semantic_reset()
        _fallback_reset()

    def tearDown(self):
        _semantic_reset()
        _fallback_reset()

    @covers_requirement("narrator::narrator-preserves-the-single-writer-and-transport-boundaries")
    def test_startup_seam_registers_narrator_with_a_working_renderer(self):
        from server.conf.at_server_startstop import _register_narrator_layer

        _register_narrator_layer()
        self.assertTrue(narrator._is_registered())
        log = _log()
        self.assertEqual(
            narrator._template_renderer((log,)),
            _join_renderer((log,)),
        )

    @covers_requirement("narrator::narrator-preserves-the-single-writer-and-transport-boundaries")
    def test_startup_seam_survives_a_foreign_narrator_registration(self):
        from server.conf.at_server_startstop import _register_narrator_layer
        from world.ai.guardrail import register_degrade_fallback

        register_degrade_fallback("narrator", lambda: "foreign-degrade")
        _register_narrator_layer()
        self.assertFalse(narrator._is_registered())


if __name__ == "__main__":
    unittest.main()
