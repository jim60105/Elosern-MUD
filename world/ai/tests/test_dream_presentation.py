"""Behavior tests for the dream collaborator layer (dream-explicit-presentation).

Covers the deterministic bounded prompt (server-supplied phase, spoiler-filtered
permitted context, no shared director history), the guarded explicit-exchange
acceptance, the semantic gates (phase fidelity, metadata/spoiler leak,
state-change claim, named-deity identity, summary no-new-question), the
retry/degrade paths, registration/atomic rollback, and the startup seam. All
generation is recorded ``FakeLLMClient`` only; no test opens a model service.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings

from world.ai import dream, guardrail
from world.ai.dream import (
    DREAM_EXCHANGE_SCHEMA,
    FORBIDDEN_DIVINE_MARKERS,
    MAX_ADVENTURE_LINES,
    DreamClientRequiredError,
    DreamNotRegisteredError,
    build_dream_prompt,
    generate_dream_exchange,
    register_dream,
)
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import GuardrailRegistrationError
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.narrative.authoring import CollaboratorBrief
from world.narrative.dream_track import (
    MODE_CONVERGENCE,
    MODE_EXCHANGE,
    MODE_SUMMARY,
    exchange_mode,
    prospective_state,
    track_state,
)
from world.prompts.loader import PromptUnavailableError

from tools.spec_traceability import covers_requirement

# Synthetic explicit fixture prose (kept in the test file, never shipped as
# prompt text): the approved capability accepts explicit sexual content.
_EXPLICIT_SCENE = (
    "純白房間裡，兩具赤裸的身體在床榻上緊緊交纏，肌膚相貼、喘息交錯，"
    "手指沿著背脊一路撫下，濕熱的觸感讓彼此的呼吸越來越急。"
)
_COUNTERPART_LINE = "「別急，我們還有很多時間。」她貼著耳邊低語，掌心仍按在胸前。"


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _reset():
    guardrail._semantic_validators.clear()
    guardrail._degrade_fallbacks.clear()
    _OUTPUT_SCHEMAS.pop("dream", None)


def _brief(**overrides):
    values = {
        "owner_id": "owner-secret",
        "submission_key": "draft-secret:v1",
        "version": 1,
        "summary": "建立一段以神殿夜談為底的新故事。",
        "themes": ("神殿夜談",),
        "atmosphere": ("靜謐",),
        "participants": ("1001",),
        "emphasis": ("對話",),
        "exclusions": ("暴力",),
    }
    values.update(overrides)
    return CollaboratorBrief(**values)


def _response(scene=_EXPLICIT_SCENE, dialogue=_COUNTERPART_LINE, phase=None, completed=0, **extra):
    payload = {
        "scene": scene,
        "dialogue": dialogue,
        "phase": phase if phase is not None else prospective_state(completed).level,
    }
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)


class DreamPromptTests(unittest.TestCase):
    def setUp(self):
        _reset()
        register_dream()

    def tearDown(self):
        _reset()

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_identical_inputs_produce_byte_identical_prompts(self):
        state = prospective_state(0)
        first = build_dream_prompt(
            state=state, mode=MODE_EXCHANGE, player_message="我們談談好嗎？"
        )
        second = build_dream_prompt(
            state=state, mode=MODE_EXCHANGE, player_message="我們談談好嗎？"
        )
        self.assertEqual(first, second)
        self.assertEqual(first[0]["role"], "system")
        self.assertEqual(first[1]["role"], "user")
        self.assertEqual(first[0]["content"], second[0]["content"])

    @covers_requirement("dream-explicit-presentation::server-owned-dream-arousal-advances-only-with-completed-exchanges")
    def test_system_prompt_carries_the_server_supplied_phase(self):
        state = prospective_state(4)
        system, _user = build_dream_prompt(
            state=state, mode=MODE_CONVERGENCE, player_message="繼續。"
        )
        self.assertIn(state.level, system["content"])
        self.assertIn(state.climax_phase, system["content"])
        self.assertIn(str(state.completed), system["content"])
        self.assertIn(MODE_CONVERGENCE, system["content"])
        self.assertNotIn("{phase}", system["content"])
        self.assertNotIn("{mode}", system["content"])

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_user_payload_carries_only_permitted_context(self):
        system, user = build_dream_prompt(
            state=prospective_state(1),
            mode=MODE_EXCHANGE,
            player_message="我想加入更多冒險。",
            brief=_brief(),
            adventure_summary=["走過老森林的岔路", "在公會領過一次委託"],
        )
        payload = json.loads(user["content"])
        self.assertEqual(
            set(payload), {"player_message", "preferences", "adventure_summary"}
        )
        # No StoryDirector/system/hidden fields and no owner identities.
        lowered = user["content"]
        self.assertNotIn("director", lowered)
        self.assertNotIn("system", lowered)
        self.assertNotIn("owner-secret", lowered)
        self.assertNotIn("draft-secret", lowered)
        self.assertIn("神殿夜談", payload["preferences"]["summary"])
        self.assertEqual(payload["preferences"]["participants"], ["1001"])

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_adventure_summary_is_capped_deterministically(self):
        _system, user = build_dream_prompt(
            state=prospective_state(0),
            mode=MODE_EXCHANGE,
            player_message="繼續。",
            adventure_summary=[f"事件{i}" for i in range(MAX_ADVENTURE_LINES * 3)],
        )
        payload = json.loads(user["content"])
        self.assertEqual(len(payload["adventure_summary"]), MAX_ADVENTURE_LINES)

    @covers_requirement("dream-explicit-presentation::server-owned-dream-arousal-advances-only-with-completed-exchanges")
    def test_prompt_construction_does_not_advance_the_track(self):
        committed = track_state(2)
        lookahead = prospective_state(2)
        build_dream_prompt(state=lookahead, mode=MODE_EXCHANGE, player_message="x" * 10)
        # The lookahead is a distinct next-exchange projection, and building the
        # prompt left the committed state exactly where it was.
        self.assertNotEqual(lookahead, committed)
        self.assertEqual(track_state(2), committed)

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_adventure_summary_must_be_a_sequence_of_strings(self):
        _system, user = build_dream_prompt(
            state=prospective_state(0),
            mode=MODE_EXCHANGE,
            player_message="繼續。",
            adventure_summary=5,
        )
        self.assertNotIn("adventure_summary", json.loads(user["content"]))

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_cap_string_never_exceeds_a_tiny_limit(self):
        self.assertEqual(dream._cap_string("abcdef", 0), "")
        self.assertEqual(dream._cap_string("abcdef", 1), "a")


class DreamGenerationTests(unittest.TestCase):
    def setUp(self):
        _reset()
        register_dream()

    def tearDown(self):
        _reset()

    def _generate(self, client, **overrides):
        kwargs = {"completed": 0, "player_message": "我想繼續這個方向。"}
        kwargs.update(overrides)
        return generate_dream_exchange(client, **kwargs)

    @covers_requirement("dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame")
    def test_recorded_explicit_response_validates(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _response())
        with override_settings(LLM_PROFILES=_raw()):
            result = await_result(self._generate(client))
        self.assertIsNotNone(result)
        self.assertEqual(result.scene, _EXPLICIT_SCENE)
        self.assertEqual(result.dialogue, _COUNTERPART_LINE)
        self.assertEqual(result.phase, prospective_state(0).level)
        self.assertEqual(result.mode, MODE_EXCHANGE)
        self.assertEqual(result.completed, 1)

    def test_generation_logs_identifiers_only(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _response())
        with override_settings(LLM_PROFILES=_raw()):
            with patch("world.ai.dream.log_info") as info:
                result = await_result(self._generate(client))
        self.assertIsNotNone(result)
        (event,), kwargs = info.call_args
        self.assertEqual(event, "dream_exchange_generated")
        context = kwargs["context"]
        self.assertEqual(
            set(context), {"layer", "completed", "mode", "phase", "climax_phase"}
        )
        self.assertNotIn(_EXPLICIT_SCENE, json.dumps(context, ensure_ascii=False))
        self.assertNotIn(_COUNTERPART_LINE, json.dumps(context, ensure_ascii=False))

    @covers_requirement("dream-explicit-presentation::server-owned-dream-arousal-advances-only-with-completed-exchanges")
    def test_arbitrary_phase_advance_is_rejected(self):
        client = FakeLLMClient()
        # Declares a later canonical band than the server supplied.
        client.add_response(
            lambda d: True, _response(phase=prospective_state(4).level)
        )
        with override_settings(LLM_PROFILES=_raw()):
            result = await_result(self._generate(client))
        self.assertIsNone(result)

    @covers_requirement("dream-explicit-presentation::server-owned-dream-arousal-advances-only-with-completed-exchanges")
    def test_phase_retry_reuses_the_same_server_phase(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _response(phase=prospective_state(4).level),
        )
        client.add_response(lambda d: len(d.messages) == 3, _response())
        with override_settings(LLM_PROFILES=_raw()):
            result = await_result(self._generate(client))
        self.assertIsNotNone(result)
        self.assertEqual(result.phase, prospective_state(0).level)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("phase", client.calls[1].messages[-1]["content"])

    @covers_requirement("dream-explicit-presentation::server-owned-dream-arousal-advances-only-with-completed-exchanges")
    def test_fifth_exchange_is_convergence_and_satisfies_climax_phase(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _response(completed=4))
        with override_settings(LLM_PROFILES=_raw()):
            result = await_result(self._generate(client, completed=4))
        self.assertIsNotNone(result)
        self.assertEqual(result.mode, MODE_CONVERGENCE)
        self.assertEqual(exchange_mode(4), MODE_CONVERGENCE)
        self.assertEqual(result.completed, 5)

    @covers_requirement("dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame")
    def test_sixth_exchange_summary_rejects_a_new_question(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _response(dialogue="「這樣好嗎？」", completed=5))
        with override_settings(LLM_PROFILES=_raw(dream={"max_retries": 0})):
            result = await_result(self._generate(client, completed=5))
        self.assertIsNone(result)

    @covers_requirement("dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame")
    def test_sixth_exchange_summary_without_a_question_validates(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _response(dialogue="我們把這個方向定下來。", completed=5),
        )
        with override_settings(LLM_PROFILES=_raw()):
            result = await_result(self._generate(client, completed=5))
        self.assertIsNotNone(result)
        self.assertEqual(result.mode, MODE_SUMMARY)

    @covers_requirement("dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame")
    def test_sixth_exchange_summary_rejects_a_vertical_question_mark(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True, _response(dialogue="你喜歡這樣嗎\ufe16", completed=5)
        )
        with override_settings(LLM_PROFILES=_raw(dream={"max_retries": 0})):
            result = await_result(self._generate(client, completed=5))
        self.assertIsNone(result)

    @covers_requirement("dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame")
    def test_named_deity_assertion_is_rejected(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _response(dialogue="我是這個世界唯一的神。"),
        )
        with (
            patch("world.ai.dream.FORBIDDEN_DIVINE_MARKERS", ("唯一的神",)),
            override_settings(LLM_PROFILES=_raw(dream={"max_retries": 0})),
        ):
            result = await_result(self._generate(client))
        self.assertIsNone(result)

    @covers_requirement("dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame")
    def test_shipped_divine_marker_vocabulary_is_nonempty(self):
        self.assertTrue(FORBIDDEN_DIVINE_MARKERS)
        self.assertTrue(
            all(isinstance(marker, str) and marker.strip() for marker in FORBIDDEN_DIVINE_MARKERS)
        )

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_metadata_leak_is_rejected(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True, _response(dialogue="合成外洩欄位：內部審核內容。")
        )
        with (
            patch("world.ai.dream.FORBIDDEN_METADATA_MARKERS", ("合成外洩欄位",)),
            override_settings(LLM_PROFILES=_raw(dream={"max_retries": 0})),
        ):
            result = await_result(self._generate(client))
        self.assertIsNone(result)

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_shipped_metadata_marker_is_rejected_without_patching(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True, _response(dialogue="系統提示：這裡是內部審核內容。")
        )
        with override_settings(LLM_PROFILES=_raw(dream={"max_retries": 0})):
            result = await_result(self._generate(client))
        self.assertIsNone(result)

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_ascii_marker_matching_is_case_insensitive(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True, _response(dialogue="Metadata: internal review notes.")
        )
        with override_settings(LLM_PROFILES=_raw(dream={"max_retries": 0})):
            result = await_result(self._generate(client))
        self.assertIsNone(result)

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_state_change_claim_is_rejected(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True, _response(dialogue="合成狀態宣告：事情已經定案。")
        )
        with (
            patch("world.ai.dream.FORBIDDEN_STATE_CHANGE_MARKERS", ("合成狀態宣告",)),
            override_settings(LLM_PROFILES=_raw(dream={"max_retries": 0})),
        ):
            result = await_result(self._generate(client))
        self.assertIsNone(result)

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_shipped_state_change_marker_is_rejected_without_patching(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True, _response(dialogue="任務已完成，你可以放心了。")
        )
        with override_settings(LLM_PROFILES=_raw(dream={"max_retries": 0})):
            result = await_result(self._generate(client))
        self.assertIsNone(result)

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_extra_system_field_is_rejected_by_the_schema(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _response(system="hidden"))
        with override_settings(LLM_PROFILES=_raw(dream={"max_retries": 0})):
            result = await_result(self._generate(client))
        self.assertIsNone(result)

    @covers_requirement("dream-explicit-presentation::server-owned-dream-arousal-advances-only-with-completed-exchanges")
    def test_transport_failure_degrades_to_none(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        with override_settings(LLM_PROFILES=_raw()):
            result = await_result(self._generate(client))
        self.assertIsNone(result)

    def test_prompt_unavailable_degrades_without_a_call(self):
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            with patch(
                "world.ai.dream.render_prompt",
                side_effect=PromptUnavailableError("dream.yaml", "dream.system", "unavailable"),
            ):
                result = await_result(self._generate(client))
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 0)

    def test_generating_before_registration_errbacks_with_named_error(self):
        _reset()
        client = FakeLLMClient()
        client.add_response(lambda d: True, _response())
        with override_settings(LLM_PROFILES=_raw()):
            result = await_result(self._generate(client))
        self.assertTrue(result.check(DreamNotRegisteredError))
        self.assertEqual(len(client.calls), 0)

    def test_explicit_none_client_errbacks_before_transport(self):
        failure = await_result(self._generate(None))
        self.assertTrue(failure.check(DreamClientRequiredError))


class DreamRegistrationTests(unittest.TestCase):
    def setUp(self):
        _reset()

    def tearDown(self):
        _reset()

    def test_duplicate_registration_is_a_noop(self):
        register_dream()
        register_dream()
        self.assertTrue(dream._is_registered())

    def test_partial_hook_registration_failure_leaves_no_hooks(self):
        calls = {"count": 0}

        def flaky_validator(layer, name, validator):
            calls["count"] += 1
            if calls["count"] == 2:
                raise GuardrailRegistrationError(
                    f"semantic validator {layer}.{name} already registered"
                )
            return guardrail.register_semantic_validator(layer, name, validator)

        with patch("world.ai.guardrail.register_semantic_validator", flaky_validator):
            with self.assertRaises(GuardrailRegistrationError):
                register_dream()
        self.assertNotIn("dream", guardrail._degrade_fallbacks)
        self.assertEqual(guardrail._semantic_validators.get("dream", {}), {})

    def test_foreign_hooks_are_never_overridden(self):
        for name in dream._VALIDATORS:
            guardrail.register_semantic_validator("dream", name, lambda parsed: ["foreign"])
        self.assertFalse(dream._is_registered())
        with self.assertRaises(GuardrailRegistrationError):
            register_dream()
        self.assertFalse(dream._is_registered())

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_dream_capability_is_separate_from_the_story_director(self):
        register_dream()
        self.assertEqual(guardrail._semantic_validators.get("scenario_director", {}), {})
        self.assertNotIn("scenario_director", guardrail._degrade_fallbacks)
        source = Path(dream.__file__).read_text(encoding="utf-8")
        self.assertNotIn("from world.ai.scenario_director", source)
        self.assertNotIn("import world.ai.scenario_director", source)
        self.assertNotIn("director_templates", source)
        # A shared deployment profile is still a distinct frozen profile object,
        # so capability history and permissions are never shared.
        from world.ai.profiles import build_profiles, default_profiles

        profiles = build_profiles(default_profiles())
        self.assertIsNot(profiles["dream"], profiles["scenario_director"])

    @covers_requirement("dream-explicit-presentation::collaborator-has-separate-spoiler-filtered-capability-access")
    def test_dream_schema_is_registered_under_its_own_id(self):
        register_dream()
        self.assertIs(_OUTPUT_SCHEMAS["dream"], DREAM_EXCHANGE_SCHEMA)

    def test_startup_seam_registers_the_layer(self):
        from server.conf.at_server_startstop import _register_dream_layer

        _register_dream_layer()
        self.assertTrue(dream._is_registered())
        self.assertIs(guardrail._degrade_fallbacks["dream"], dream._degrade_fallback)

    def test_startup_seam_survives_a_foreign_registration(self):
        from server.conf.at_server_startstop import _register_dream_layer

        guardrail.register_degrade_fallback("dream", lambda: "foreign-degrade")
        _register_dream_layer()
        self.assertFalse(dream._is_registered())


if __name__ == "__main__":
    unittest.main()
