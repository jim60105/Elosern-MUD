"""Tests for atomic registration, the guarded entry point, the template pool, and startup wiring."""


import json
from unittest.mock import patch
import unittest

from django.test import override_settings

from world.ai import guardrail
from world.ai import scenario_director
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import GuardrailRegistrationError
from world.ai.scenario_director import (
    QuestBlueprint,
    ScenarioDirectorClientRequiredError,
    ScenarioDirectorNotRegisteredError,
    ScenarioDirectorTemplateError,
    generate_quest_blueprint,
    register_scenario_director,
)
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.ai.tests._director_helpers import (
    _blueprint,
    _context,
    _instance_payload,
    _payload,
    _raw,
    _reset_all,
    await_result,
)
from world.quests.tests._fixtures import RegistryIsolationMixin

from tools.spec_traceability import covers_requirement



class ScenarioDirectorRegistrationTests(unittest.TestCase):
    def setUp(self):
        _reset_all()

    def tearDown(self):
        _reset_all()

    @covers_requirement("scenario-director::hook-registration-is-atomic-idempotent-and-boot-tolerant")
    def test_duplicate_registration_is_a_noop(self):
        register_scenario_director()
        register_scenario_director()
        self.assertTrue(scenario_director._is_registered())
        self.assertIn("scenario_director", guardrail._degrade_fallbacks)
        self.assertEqual(
            set(guardrail._semantic_validators["scenario_director"]),
            set(scenario_director._VALIDATORS),
        )
        self.assertIs(_OUTPUT_SCHEMAS["scenario_director"], scenario_director.SCENARIO_DIRECTOR_OUTPUT_SCHEMA)

    @covers_requirement("scenario-director::hook-registration-is-atomic-idempotent-and-boot-tolerant")
    def test_partial_hook_failure_leaves_no_scenario_director_hooks(self):
        calls = {"count": 0}

        def flaky_validator(layer, name, validator):
            calls["count"] += 1
            if calls["count"] == 2:
                raise GuardrailRegistrationError(
                    f"semantic validator {layer}.{name} already registered"
                )
            return guardrail.register_semantic_validator(layer, name, validator)

        with patch("world.ai.scenario_director.register_semantic_validator", flaky_validator):
            with self.assertRaises(GuardrailRegistrationError):
                register_scenario_director()
        self.assertNotIn("scenario_director", guardrail._degrade_fallbacks)
        self.assertEqual(guardrail._semantic_validators.get("scenario_director", {}), {})
        self.assertNotIn("scenario_director", _OUTPUT_SCHEMAS)

    def test_foreign_same_name_validator_does_not_pass_the_gate(self):
        from world.ai.guardrail import register_degrade_fallback, register_semantic_validator

        register_degrade_fallback("scenario_director", scenario_director._degrade_fallback)
        for name in scenario_director._VALIDATORS:
            register_semantic_validator("scenario_director", name, lambda parsed: ["foreign"])
        self.assertFalse(scenario_director._is_registered())
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            failure = await_result(d)
        self.assertTrue(failure.check(ScenarioDirectorNotRegisteredError))


class ScenarioDirectorEntryPointTests(unittest.TestCase):
    def setUp(self):
        _reset_all()
        register_scenario_director()

    def tearDown(self):
        _reset_all()

    @covers_requirement("guardrail::guarded-generative-calls-validate-retry-then-degrade")
    @covers_requirement("scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context")
    def test_valid_context_fitting_blueprint_resolves_with_no_state_change(self):
        client = FakeLLMClient()
        blueprint = _blueprint()
        client.add_response(lambda d: True, json.dumps(_payload(blueprint), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertIsInstance(result, QuestBlueprint)
        self.assertEqual(result, blueprint)
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context")
    def test_explicit_none_client_errbacks_before_any_prompt_or_transport_work(self):
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(None, context=_context())
            failure = await_result(d)
        self.assertTrue(failure.check(ScenarioDirectorClientRequiredError))

    @covers_requirement("scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context")
    def test_context_misfitting_blueprint_is_replaced_by_a_fitting_template(self):
        client = FakeLLMClient()
        # C rank with C-band copper: schema- and semantically valid, but it does
        # not fit an F-rank request, so the post-guardrail fitness gate must
        # treat it as a degrade trigger and draw a fitting template.
        foreign = _blueprint(issuer="guild_branch_altoria", rank="C", copper=10_000)
        client.add_response(lambda d: True, json.dumps(_payload(foreign), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertLessEqual(
            scenario_director._rank_order(result.rank),
            scenario_director._rank_order("F"),
        )
        self.assertEqual(result.issuer, "guild_branch_altoria")

    @covers_requirement("scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context")
    def test_disabled_profile_draws_a_template_with_zero_client_calls(self):
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(scenario_director={"enabled": False})):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertIsInstance(result, QuestBlueprint)
        self.assertTrue(scenario_director._fits_context(result, _context()))
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context")
    def test_transport_failure_and_exhausted_retries_draw_a_template(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertIsInstance(result, QuestBlueprint)
        self.assertTrue(scenario_director._fits_context(result, _context()))

        exhausting = FakeLLMClient()
        exhausting.add_response(lambda d: True, json.dumps(_payload(_blueprint(rank="Z")), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw(scenario_director={"max_retries": 1})):
            d = generate_quest_blueprint(exhausting, context=_context())
            result = await_result(d)
        self.assertIsInstance(result, QuestBlueprint)
        self.assertTrue(scenario_director._fits_context(result, _context()))

    @covers_requirement("scenario-director::the-hand-written-template-pool-provides-offline-quest-generation")
    @covers_requirement("scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context")
    def test_identical_degraded_contexts_draw_identical_templates(self):
        disabled = _raw(scenario_director={"enabled": False})
        results = []
        for _ in range(2):
            with override_settings(LLM_PROFILES=disabled):
                d = generate_quest_blueprint(FakeLLMClient(), context=_context())
                results.append(await_result(d))
        self.assertEqual(results[0], results[1])

    @covers_requirement("scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context")
    def test_unsatisfiable_context_errbacks_with_template_error(self):
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(scenario_director={"enabled": False})):
            d = generate_quest_blueprint(
                client, context=_context(requested_type="緊急", issuer_branch="guild_branch_altoria")
            )
            failure = await_result(d)
        self.assertTrue(failure.check(ScenarioDirectorTemplateError))

    @covers_requirement("scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context")
    def test_calling_before_registration_errbacks_with_named_error(self):
        _reset_all()
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            failure = await_result(d)
        self.assertTrue(failure.check(ScenarioDirectorNotRegisteredError))


class ScenarioDirectorTemplatePoolTests(RegistryIsolationMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        _reset_all()
        register_scenario_director()

    def tearDown(self):
        _reset_all()

    @covers_requirement("scenario-director::the-hand-written-template-pool-provides-offline-quest-generation")
    def test_pool_is_non_empty(self):
        from world.ai.director_templates import QUEST_TEMPLATE_POOL

        self.assertGreaterEqual(len(QUEST_TEMPLATE_POOL), 2)

    @covers_requirement("scenario-director::the-hand-written-template-pool-provides-offline-quest-generation")
    def test_every_entry_validates_against_schema_and_validators(self):
        from jsonschema import Draft7Validator

        from world.ai.director_templates import QUEST_TEMPLATE_POOL
        from world.ai.scenario_director import SCENARIO_DIRECTOR_OUTPUT_SCHEMA

        validator = Draft7Validator(SCENARIO_DIRECTOR_OUTPUT_SCHEMA)
        for entry in QUEST_TEMPLATE_POOL:
            with self.subTest(entry=entry.name):
                payload = entry.to_payload()
                self.assertEqual(
                    [error.message for error in validator.iter_errors(payload)], []
                )
                for name, validator_fn in scenario_director._VALIDATORS.items():
                    self.assertEqual(validator_fn(payload), [], name)

    @covers_requirement("scenario-director::the-hand-written-template-pool-provides-offline-quest-generation")
    def test_degraded_draw_is_deterministic_and_context_fitting(self):
        first = scenario_director._draw_template(_context())
        second = scenario_director._draw_template(_context())
        self.assertEqual(first, second)
        self.assertTrue(scenario_director._fits_context(first, _context()))

    @covers_requirement("scenario-director::the-hand-written-template-pool-provides-offline-quest-generation")
    def test_cold_start_import_has_no_module_level_cycle(self):
        import importlib
        import sys

        import world.ai

        # Keep the pre-test module objects: re-importing replaces them in
        # sys.modules and as attributes on the ``world.ai`` package, and
        # invalidates the identities every other test in the process bound at
        # import time (order-independent execution requires the original
        # modules to be restored afterwards).
        original = {
            name: module
            for name, module in sys.modules.items()
            if name.startswith("world.ai.director_templates")
            or name.startswith("world.ai.scenario_director")
        }
        for module in list(sys.modules):
            if module.startswith("world.ai.director_templates") or module.startswith(
                "world.ai.scenario_director"
            ):
                del sys.modules[module]
        try:
            pool = importlib.import_module("world.ai.director_templates")
            self.assertTrue(pool.QUEST_TEMPLATE_POOL)
            director = importlib.import_module("world.ai.scenario_director")
            self.assertTrue(director.get_template_pool())
        finally:
            # Restore the pre-test modules and package attributes, and purge
            # every probe-created module that did not exist before the test
            # (a re-imported module that stays behind would bind a fresh
            # scenario_director identity and break later tests in this
            # process).
            sys.modules.update(original)
            for name, module in list(sys.modules.items()):
                if name.startswith("world.ai.director_templates") or name.startswith(
                    "world.ai.scenario_director"
                ):
                    if name not in original:
                        del sys.modules[name]
            for attribute in ("director_templates", "scenario_director"):
                if not hasattr(world.ai, attribute):
                    continue
                original_module = original.get(f"world.ai.{attribute}")
                if original_module is None:
                    delattr(world.ai, attribute)
                else:
                    setattr(world.ai, attribute, original_module)

    @covers_requirement("scenario-director::the-hand-written-template-pool-provides-offline-quest-generation")
    def test_every_entry_compiles_to_a_registrable_definition(self):
        from world.quests.compile import compile_quest_blueprint, register_generated_quest
        from world.quests.definitions import (
            QUEST_DEFINITION_REGISTRY,
            validate_definition,
        )
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY
        from world.ai.director_templates import QUEST_TEMPLATE_POOL

        for entry in QUEST_TEMPLATE_POOL:
            with self.subTest(entry=entry.name):
                compiled = compile_quest_blueprint(entry.to_payload())
                validate_definition(compiled.definition)
                with patch(
                    "world.quests.compile.append_generated_quest_payload",
                    return_value=True,
                ):
                    register_generated_quest(compiled)
                self.assertIn(compiled.definition.key, QUEST_DEFINITION_REGISTRY)
                self.assertIn(
                    (compiled.definition.key, compiled.issuer_branch_key),
                    GUILD_OFFER_REGISTRY,
                )

    @covers_requirement("scene-builder::the-hand-written-template-pool-gains-an-instance-layer-scene-so-offline-play-exercises-the-materializer")
    def test_instance_layer_template_validates_compiles_and_registers_with_requirements(self):
        from jsonschema import Draft7Validator

        from world.ai.director_templates import QUEST_TEMPLATE_POOL
        from world.quests.compile import (
            SCENE_REQUIREMENT_REGISTRY,
            compile_quest_blueprint,
            register_generated_quest,
            scene_requirements_for,
        )
        from world.quests.definitions import (
            QUEST_DEFINITION_REGISTRY,
            DestinationKind,
            validate_definition,
        )
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        instance = next(
            entry
            for entry in QUEST_TEMPLATE_POOL
            if any(
                stage.location is not None
                and stage.location.layer == "instance"
                and stage.npc_reqs
                for stage in entry.stages
            )
        )
        payload = instance.to_payload()
        validator = Draft7Validator(scenario_director.SCENARIO_DIRECTOR_OUTPUT_SCHEMA)
        self.assertEqual([error.message for error in validator.iter_errors(payload)], [])
        for validator_fn in scenario_director._VALIDATORS.values():
            self.assertEqual(validator_fn(payload), [])
        compiled = compile_quest_blueprint(payload)
        validate_definition(compiled.definition)
        with patch(
            "world.quests.compile.append_generated_quest_payload", return_value=True
        ):
            register_generated_quest(compiled)
        self.assertIn(compiled.definition.key, QUEST_DEFINITION_REGISTRY)
        self.assertIn(
            (compiled.definition.key, compiled.issuer_branch_key),
            GUILD_OFFER_REGISTRY,
        )
        requirements = scene_requirements_for(compiled.definition.key)
        self.assertTrue(requirements)
        self.assertTrue(
            requirements[0].location is not None
            and requirements[0].location.kind is DestinationKind.BOUND_INSTANCE
        )
        self.assertTrue(requirements[0].npc_reqs)

    @covers_requirement("scene-builder::the-hand-written-template-pool-gains-an-instance-layer-scene-so-offline-play-exercises-the-materializer")
    def test_offline_request_can_produce_a_materializable_instance_quest(self):
        from world.ai.director_templates import QUEST_TEMPLATE_POOL

        with override_settings(LLM_PROFILES=_raw(scenario_director={"enabled": False})):
            d = generate_quest_blueprint(FakeLLMClient(), context=_context())
            result = await_result(d)
        self.assertEqual(
            result,
            next(
                entry
                for entry in QUEST_TEMPLATE_POOL
                if any(
                    stage.location is not None
                    and stage.location.layer == "instance"
                    and stage.npc_reqs
                    for stage in entry.stages
                )
            ),
        )

    @covers_requirement("blueprint-portrait-policy::the-hand-written-template-pool-may-carry-characterization-fields")
    def test_valid_named_template_registers(self):
        from world.ai.director_templates import QUEST_TEMPLATE_POOL

        named = next(
            entry
            for entry in QUEST_TEMPLATE_POOL
            if any(
                requirement.portrait is not None
                for stage in entry.stages
                for requirement in stage.npc_reqs
            )
        )
        payload = named.to_payload()
        for validator_fn in scenario_director._VALIDATORS.values():
            self.assertEqual(validator_fn(payload), [], validator_fn.__name__)
        from world.quests.compile import compile_quest_blueprint

        compiled = compile_quest_blueprint(payload)
        self.assertTrue(compiled.definition.key)

    @covers_requirement("blueprint-portrait-policy::the-hand-written-template-pool-may-carry-characterization-fields")
    def test_malformed_underage_template_is_rejected_at_registration(self):
        from world.ai.director_templates import QUEST_TEMPLATE_POOL

        named = next(
            entry
            for entry in QUEST_TEMPLATE_POOL
            if any(
                requirement.portrait is not None
                for stage in entry.stages
                for requirement in stage.npc_reqs
            )
        )
        payload = named.to_payload()
        for stage in payload["stages"]:
            for requirement in stage.get("npc_req") or []:
                if "age" in requirement:
                    requirement["age"] = 17
                    requirement["apparent_age"] = 17
        errors = [
            message
            for validator_fn in scenario_director._VALIDATORS.values()
            for message in validator_fn(payload)
        ]
        self.assertTrue(errors, "an underage template must be rejected at registration")


class RegistryRestoreRegressionTests(unittest.TestCase):
    """Regression: registered generated content must not outlive its test.

    The pre-fix scenario-director tests cleared the three process-global
    registries destructively, so a later test in the same process (for example
    the affinity-rulebook load in ``DisplayedStatsBlockTests``) saw empty
    registries and failed. The single test below proves the restoration
    contract directly, so it holds under any test ordering (serial, parallel,
    shuffled, reversed).
    """

    @covers_requirement("evennia-test-optimization::tests-restore-process-global-registry-state")
    def test_registries_hold_exactly_the_pre_test_contents_after_a_mutating_test(self):
        from world.quests.compile import (
            SCENE_REQUIREMENT_REGISTRY,
            compile_quest_blueprint,
            register_generated_quest,
        )
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        class _GeneratedProbe(RegistryIsolationMixin, unittest.TestCase):
            def runTest(self):
                pass

        quests_before = dict(QUEST_DEFINITION_REGISTRY)
        offers_before = dict(GUILD_OFFER_REGISTRY)
        requirements_before = dict(SCENE_REQUIREMENT_REGISTRY)

        probe = _GeneratedProbe("runTest")
        probe.setUp()
        try:
            compiled = compile_quest_blueprint(_instance_payload())
            with patch(
                "world.quests.compile.append_generated_quest_payload",
                return_value=True,
            ):
                register_generated_quest(compiled)
            self.assertIn(compiled.definition.key, QUEST_DEFINITION_REGISTRY)
            self.assertIn(
                (compiled.definition.key, compiled.issuer_branch_key),
                GUILD_OFFER_REGISTRY,
            )
        finally:
            # The destructive pre-fix tests cleared the registries here; the
            # addCleanup-registered restoration must bring back every entry
            # even when an assertion above fails.
            probe.doCleanups()

        self.assertEqual(dict(QUEST_DEFINITION_REGISTRY), quests_before)
        self.assertEqual(dict(GUILD_OFFER_REGISTRY), offers_before)
        self.assertEqual(dict(SCENE_REQUIREMENT_REGISTRY), requirements_before)


class ScenarioDirectorStartupRegistrationTests(unittest.TestCase):
    def setUp(self):
        _reset_all()

    def tearDown(self):
        _reset_all()

    @covers_requirement("scenario-director::hook-registration-is-atomic-idempotent-and-boot-tolerant")
    def test_startup_seam_registers_the_scenario_director_layer(self):
        from server.conf.at_server_startstop import _register_scenario_director_layer

        _register_scenario_director_layer()
        self.assertTrue(scenario_director._is_registered())

    @covers_requirement("scenario-director::hook-registration-is-atomic-idempotent-and-boot-tolerant")
    def test_startup_seam_survives_a_foreign_scenario_director_registration(self):
        from server.conf.at_server_startstop import _register_scenario_director_layer
        from world.ai.guardrail import register_degrade_fallback

        register_degrade_fallback("scenario_director", lambda: "foreign-degrade")
        _register_scenario_director_layer()
        self.assertFalse(scenario_director._is_registered())


class ScenarioDirectorOfflineTestRuleTests(unittest.TestCase):
    @covers_requirement("scenario-director::the-scenario-director-layer-preserves-the-single-writer-and-transport-boundaries")
    def test_no_live_client_constructor_or_socket_in_scenario_director_tests(self):
        import pathlib

        tests_dir = (
            pathlib.Path(scenario_director.__file__).resolve().parent / "tests"
        )
        modules = sorted(tests_dir.glob("test_scenario_director_*.py"))
        self.assertTrue(modules, "no scenario-director test modules found")
        client_constructor = "OpenAICompatClient" + "("
        socket_import = "import so" + "cket"
        socket_from = "from so" + "cket"
        for module in modules:
            source = module.read_text(encoding="utf-8")
            self.assertNotIn(client_constructor, source)
            self.assertNotIn(socket_import, source)
            self.assertNotIn(socket_from, source)
