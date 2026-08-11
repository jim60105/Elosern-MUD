"""Tests for the composition root that posts generated quests to the guild board.

Covers ``request_generated_quest`` bridging a guarded director proposal to the
deterministic compile boundary: a valid fixture resolves to a registered
definition + offer + requirements with no generative state mutation; a disabled
profile resolves to a context-fitting template with zero client calls (and no
live client ever constructed); a cold import binds no ``world.ai`` logger; and
an unsupported offline context errbacks with the named template error.
"""

from unittest.mock import patch
import json
import unittest

from django.test import override_settings

from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.quests.compile import (
    SCENE_REQUIREMENT_REGISTRY,
    compile_quest_blueprint,
    scene_requirements_for,
)
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.guild_offers import GUILD_OFFER_REGISTRY

from server.ai_director_service import (
    EscortUnavailableError,
    NoSuitableTemplateError,
    request_generated_quest,
)

from tools.spec_traceability import covers_requirement


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _install_scenario_director():
    """Install the director layer idempotently after any module reload.

    ``world.ai.tests.test_scenario_director`` re-imports the module from
    ``sys.modules`` (cold-start test), which invalidates function identity for
    references captured earlier in the same process. Clearing the guardrail
    entries and re-registering through the live module keeps every later
    consumer deterministic regardless of test order.
    """
    from world.ai import guardrail, scenario_director
    from world.ai.schemas.registry import _OUTPUT_SCHEMAS

    guardrail._semantic_validators.pop("scenario_director", None)
    guardrail._degrade_fallbacks.pop("scenario_director", None)
    _OUTPUT_SCHEMAS.pop("scenario_director", None)
    scenario_director.register_scenario_director()


def _context(**overrides):
    context = {
        "requested_type": "討伐",
        "allowed_rank": "F",
        "issuer_branch": "guild_branch_altoria",
        "anchor": "capital_altoria",
    }
    context.update(overrides)
    return context


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


class AiDirectorServiceIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        self._requirements_items = list(SCENE_REQUIREMENT_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        SCENE_REQUIREMENT_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.update(self._requirements_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()


class AiDirectorServiceTests(AiDirectorServiceIsolation, unittest.TestCase):
    def setUp(self):
        super().setUp()
        _install_scenario_director()
        from world.ai import scenario_director as _sd
        # Pure-unit class: the durable store is a database Script, so the
        # store boundary is patched to keep every test here DB-free.
        patcher = patch(
            "world.quests.compile.append_generated_quest_payload", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    @covers_requirement("scene-builder::the-composition-root-posts-one-generated-quest-to-the-guild-board-and-degrades-offline")
    def test_valid_fixture_resolves_to_a_registered_quest_with_no_generative_mutation(self):
        from world.ai.director_templates import QUEST_TEMPLATE_POOL

        payload = QUEST_TEMPLATE_POOL[0].to_payload()
        client = FakeLLMClient()
        client.add_response(lambda d: True, json.dumps(payload, ensure_ascii=False))
        compiled = await_result(request_generated_quest(client, context=_context()))
        self.assertEqual(len(client.calls), 1)
        self.assertIn(compiled.definition.key, QUEST_DEFINITION_REGISTRY)
        self.assertIn(
            (compiled.definition.key, compiled.issuer_branch_key),
            GUILD_OFFER_REGISTRY,
        )
        self.assertEqual(
            len(scene_requirements_for(compiled.definition.key)), 1
        )
        self.assertTrue(
            compiled.definition.stages[0].objective.requires_bound_targets
        )

    @covers_requirement("scene-builder::the-composition-root-posts-one-generated-quest-to-the-guild-board-and-degrades-offline")
    def test_disabled_profile_resolves_to_a_template_with_zero_client_calls(self):
        disabled = _raw(scenario_director={"enabled": False})
        with (
            override_settings(LLM_PROFILES=disabled),
            patch(
                "world.ai.client.OpenAICompatClient",
                side_effect=AssertionError(
                    "must not construct the live client when the profile is disabled"
                ),
            ),
        ):
            compiled = await_result(request_generated_quest(context=_context()))
        self.assertIn(compiled.definition.key, QUEST_DEFINITION_REGISTRY)
        self.assertTrue(
            compiled.definition.stages[0].objective.requires_bound_targets,
            "the disabled draw must be the instance-layer bound-target template",
        )
        self.assertEqual(len(scene_requirements_for(compiled.definition.key)), 1)

    @covers_requirement("scene-builder::the-composition-root-posts-one-generated-quest-to-the-guild-board-and-degrades-offline")
    def test_unsatisfiable_offline_context_errbacks_with_named_error(self):
        disabled = _raw(scenario_director={"enabled": False})
        with override_settings(LLM_PROFILES=disabled):
            d = request_generated_quest(
                context=_context(requested_type="緊急", issuer_branch="guild_branch_altoria")
            )
            failure = await_result(d)
        self.assertTrue(failure.check(NoSuitableTemplateError))

    @covers_requirement("quest-blueprint::escort-quests-require-a-bound-protected-entity-path")
    def test_escort_request_is_refused_and_nothing_is_registered(self):
        definitions_before = dict(QUEST_DEFINITION_REGISTRY)
        offers_before = dict(GUILD_OFFER_REGISTRY)
        disabled = _raw(scenario_director={"enabled": False})
        with override_settings(LLM_PROFILES=disabled):
            d = request_generated_quest(
                context=_context(requested_type="護衛", issuer_branch="guild_branch_altoria")
            )
            failure = await_result(d)
        self.assertTrue(failure.check(EscortUnavailableError))
        self.assertEqual(dict(QUEST_DEFINITION_REGISTRY), definitions_before)
        self.assertEqual(dict(GUILD_OFFER_REGISTRY), offers_before)

    def test_escort_request_refuses_before_any_transport_work(self):
        client = FakeLLMClient()
        d = request_generated_quest(
            client, context=_context(requested_type="護衛", issuer_branch="guild_branch_altoria")
        )
        failure = await_result(d)
        self.assertTrue(failure.check(EscortUnavailableError))
        self.assertEqual(client.calls, [])

    @covers_requirement("scene-builder::the-composition-root-posts-one-generated-quest-to-the-guild-board-and-degrades-offline")
    def test_module_imports_before_server_initialization_without_binding_a_logger(self):
        import ast
        from pathlib import Path

        module_path = (
            Path(__file__).resolve().parents[2] / "ai_director_service.py"
        )
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.ImportFrom):
                names = [node.module]
            else:
                names = [alias.name for alias in node.names]
            for name in names:
                if name and (name == "world.ai" or name.startswith("world.ai.")):
                    self.fail(
                        f"module-level import {name} would bind a logger; "
                        "world.ai imports must be deferred to the call path"
                    )


if __name__ == "__main__":
    unittest.main()
