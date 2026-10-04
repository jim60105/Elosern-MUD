"""Synthetic behavior tests for the StoryDirector generative layer.

Everything here is deterministic and offline: ``FakeLLMClient`` replays recorded
text and no test opens a socket or calls a live model. The story-director
capability's own requirement ids land at archive sync, so substantive tests are
annotated against the existing canonical main ids they establish.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from jsonschema import Draft7Validator

import world.ai.story_director as story_director
from world.ai import guardrail
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import (
    GuardrailRegistrationError,
    register_semantic_validator as _register_semantic_validator,
)
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.ai.story_director import (
    STORY_DIRECTOR_OUTPUT_SCHEMA,
    BeatProposal,
    StoryDirectorClientRequiredError,
    StoryDirectorNotRegisteredError,
    generate_beat_proposal,
    register_story_director,
    render_director_frame,
)
from world.ai.story_director import validators
from world.ai.story_director.generation import _is_registered
from world.ai.story_director.validators import (
    _validate_kind_known,
    _validate_no_write_claims,
    _validate_summary_bounded_cjk,
)

from tools.spec_traceability import covers_requirement

MESSAGES = (
    {"role": "system", "content": "story director contract"},
    {"role": "user", "content": "bounded context"},
)


def _reset_all() -> None:
    guardrail._semantic_validators.clear()
    guardrail._degrade_fallbacks.clear()
    _OUTPUT_SCHEMAS.clear()


def _await(d):
    result = d.result
    d.addErrback(lambda failure: None)
    return result


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer] = {**raw[layer], **values}
    return raw


def _payload(**overrides):
    payload = {"kind": "follow_up", "summary": "尤漢娜在森林邊界留下了記號。"}
    payload.update(overrides)
    return payload


class BeatProposalValueTests(unittest.TestCase):
    def test_from_payload_builds_a_frozen_value(self):
        proposal = BeatProposal.from_payload(
            _payload(recipient=" 201 ", relation_delta=2)
        )
        self.assertEqual(proposal.kind, "follow_up")
        self.assertEqual(proposal.summary, "尤漢娜在森林邊界留下了記號。")
        self.assertEqual(proposal.recipient, "201")
        self.assertEqual(proposal.relation_delta, 2)
        self.assertEqual(proposal.writes, ())

    def test_unknown_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            BeatProposal.from_payload(_payload(kind="season_finale"))

    def test_mutable_container_is_rejected_by_construction(self):
        with self.assertRaises(TypeError):
            BeatProposal(kind="follow_up", summary="有依據的後續。", writes=["trait"])

    def test_relation_delta_is_bounded(self):
        with self.assertRaises(ValueError):
            BeatProposal(kind="invitation", summary="邀請。", relation_delta=11)
        with self.assertRaises(TypeError):
            BeatProposal.from_payload(_payload(relation_delta="2"))

    def test_empty_summary_is_rejected(self):
        with self.assertRaises(ValueError):
            BeatProposal.from_payload(_payload(summary="   "))


class OutputContractTests(unittest.TestCase):
    def _errors(self, payload):
        validator = Draft7Validator(STORY_DIRECTOR_OUTPUT_SCHEMA)
        return [error.message for error in validator.iter_errors(payload)]

    def test_schema_accepts_a_bounded_proposal(self):
        self.assertEqual(self._errors(_payload()), [])

    def test_schema_rejects_unknown_kind_and_extra_property(self):
        self.assertTrue(self._errors(_payload(kind="season_finale")))
        self.assertTrue(self._errors(_payload(effect="quest_complete")))
        self.assertTrue(self._errors(_payload(summary="字" * 601)))

    def test_semantic_validators_require_a_bounded_cjk_summary(self):
        self.assertTrue(_validate_summary_bounded_cjk(_payload(summary="latin only")))
        self.assertEqual(_validate_summary_bounded_cjk(_payload()), [])
        self.assertTrue(_validate_kind_known(_payload(kind="season_finale")))

    def test_semantic_validators_reject_write_claims(self):
        self.assertTrue(_validate_no_write_claims(_payload(writes=["trait"])))
        self.assertEqual(_validate_no_write_claims(_payload()), [])


class ContextFrameTests(unittest.TestCase):
    def test_frame_rendering_is_deterministic_and_bounded(self):
        context = {
            "owner": "101",
            "source": {"kind": "thread", "ref": "t1", "revision": 3},
            "facts": ["事" * 5000],
        }
        first = render_director_frame(context)
        self.assertEqual(first, render_director_frame(context))
        self.assertLessEqual(len(first), 6000)
        self.assertLess(len(first), len("事") * 5000)
        self.assertLessEqual(len(json.loads(first)["facts"][0]), 300)

    def test_frame_rejects_non_mapping(self):
        with self.assertRaises(TypeError):
            render_director_frame(("not", "a", "mapping"))


class StoryDirectorRegistrationTests(unittest.TestCase):
    def setUp(self):
        _reset_all()

    def tearDown(self):
        _reset_all()

    def test_duplicate_registration_is_a_noop(self):
        register_story_director()
        register_story_director()
        self.assertTrue(_is_registered())
        self.assertIs(
            guardrail._degrade_fallbacks["story_director"], validators._HOOKS.fallback
        )
        self.assertEqual(
            set(guardrail._semantic_validators["story_director"]),
            set(validators._HOOKS.validators),
        )
        self.assertIs(_OUTPUT_SCHEMAS["story_director"], STORY_DIRECTOR_OUTPUT_SCHEMA)

    def test_partial_hook_failure_leaves_no_story_director_hooks(self):
        calls = {"count": 0}

        def flaky_validator(layer, name, validator):
            calls["count"] += 1
            if calls["count"] == 2:
                raise GuardrailRegistrationError(f"validator {layer}.{name} taken")
            return _register_semantic_validator(layer, name, validator)

        with patch("world.ai.guardrail.register_semantic_validator", flaky_validator):
            with self.assertRaises(GuardrailRegistrationError):
                register_story_director()
        self.assertNotIn("story_director", guardrail._degrade_fallbacks)
        self.assertEqual(
            guardrail._semantic_validators.get("story_director", {}), {}
        )
        self.assertNotIn("story_director", _OUTPUT_SCHEMAS)

    def test_generation_before_registration_fails_loudly(self):
        with override_settings(LLM_PROFILES=_raw()):
            failure = _await(generate_beat_proposal(FakeLLMClient(), MESSAGES))
        self.assertTrue(failure.check(StoryDirectorNotRegisteredError))

    def test_generation_requires_an_injected_client(self):
        register_story_director()
        failure = _await(generate_beat_proposal(None, MESSAGES))
        self.assertTrue(failure.check(StoryDirectorClientRequiredError))


class StoryDirectorGenerationTests(unittest.TestCase):
    def setUp(self):
        _reset_all()
        register_story_director()

    def tearDown(self):
        _reset_all()

    def _client(self, text):
        client = FakeLLMClient()
        client.add_response(lambda descriptor: descriptor.schema_id == "story_director", text)
        return client

    def test_valid_payload_returns_a_frozen_proposal(self):
        client = self._client(json.dumps(_payload()))
        with override_settings(LLM_PROFILES=_raw()):
            result = _await(generate_beat_proposal(client, MESSAGES))
        self.assertIsInstance(result, BeatProposal)
        self.assertEqual(result.kind, "follow_up")
        self.assertEqual(len(client.calls), 1)

    def test_malformed_body_degrades_to_no_content(self):
        client = FakeLLMClient()
        client.add_response(
            lambda descriptor: descriptor.schema_id == "story_director", "{not json"
        )
        with override_settings(LLM_PROFILES=_raw()):
            result = _await(generate_beat_proposal(client, MESSAGES))
        self.assertIsNone(result)

    def test_write_claim_is_rejected_and_degrades_to_no_content(self):
        client = self._client(json.dumps(_payload(writes=["trait"])))
        with override_settings(LLM_PROFILES=_raw()):
            result = _await(generate_beat_proposal(client, MESSAGES))
        self.assertIsNone(result)

    def test_disabled_profile_degrades_to_no_content_without_a_call(self):
        client = self._client(json.dumps(_payload()))
        with override_settings(LLM_PROFILES=_raw(story_director={"enabled": False})):
            result = _await(generate_beat_proposal(client, MESSAGES))
        self.assertIsNone(result)
        self.assertEqual(client.calls, [])


class StoryDirectorTransportBoundaryTests(unittest.TestCase):
    """The generative package imports no writer, typeclass, or live transport."""

    def test_package_sources_carry_no_deterministic_or_transport_imports(self):
        package = Path(story_director.__file__).parent
        banned = (
            "from world.rules",
            "import world.rules",
            "from world.maps",
            "from world.quests",
            "from typeclasses",
            "import socket",
            "world.ai.client",
        )
        sources = {
            path: path.read_text(encoding="utf-8")
            for path in sorted(package.glob("*.py"))
        }
        for path, source in sources.items():
            for fragment in banned:
                self.assertNotIn(fragment, source, f"{path.name} imports {fragment}")
