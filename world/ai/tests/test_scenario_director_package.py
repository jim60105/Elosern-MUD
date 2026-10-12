"""The beat-scoped scene route: extended blueprint contract and no-content gates.

Nothing here draws authored filler: the route either returns a schema-valid
extended blueprint or the single no-content marker ``None``.
"""

import json
from unittest import TestCase
from unittest.mock import patch

from django.test import override_settings

from tools.spec_traceability import covers_requirement

from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.ai.scenario_director import (
    generate_beat_scene_blueprint,
    get_template_pool,
    register_scenario_director,
)
from world.ai.scenario_director.generation import (
    BLUEPRINT_KEYS,
    EXTENDED_BLUEPRINT_SCHEMA,
    PACKAGE_SECTION_KEYS,
)
from world.ai.scenario_director.packages import PACKAGE_PAYLOAD_SCHEMA
from world.ai.scenario_director.validators import (
    SCENARIO_DIRECTOR_OUTPUT_SCHEMA,
    ScenarioDirectorClientRequiredError,
)
from world.ai.tests._director_helpers import _context


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def await_result(deferred):
    result = deferred.result
    deferred.addErrback(lambda failure: None)
    return result


class ExtendedBlueprintContractTests(TestCase):
    """The extended contract is composed from both upstream schemas."""

    @covers_requirement(
        "scenario-director::confirmed-scene-requirements-demand-a-complete-upstream-blueprint"
    )
    def test_the_extended_contract_keeps_the_blueprint_and_adds_the_sections(self):
        self.assertEqual(
            set(EXTENDED_BLUEPRINT_SCHEMA["properties"]),
            set(SCENARIO_DIRECTOR_OUTPUT_SCHEMA["properties"])
            | set(PACKAGE_SECTION_KEYS)
            | {"display_name"},
        )
        for key in SCENARIO_DIRECTOR_OUTPUT_SCHEMA["required"]:
            self.assertIn(key, EXTENDED_BLUEPRINT_SCHEMA["required"])
        for key in (
            "roles",
            "relationships",
            "knowledge",
            "encounters",
            "dialogue",
            "commissions",
        ):
            self.assertIn(key, EXTENDED_BLUEPRINT_SCHEMA["required"])
        self.assertFalse(EXTENDED_BLUEPRINT_SCHEMA["additionalProperties"])
        self.assertEqual(
            BLUEPRINT_KEYS, tuple(SCENARIO_DIRECTOR_OUTPUT_SCHEMA["required"])
        )

    @covers_requirement(
        "scenario-director::confirmed-scene-requirements-demand-a-complete-upstream-blueprint"
    )
    def test_the_sections_are_the_upstream_package_sections(self):
        for key in PACKAGE_SECTION_KEYS:
            self.assertIs(
                EXTENDED_BLUEPRINT_SCHEMA["properties"][key],
                PACKAGE_PAYLOAD_SCHEMA["properties"][key],
            )

    def test_only_the_scene_route_shares_the_declared_sections(self):
        # The generic quest blueprint contract stays blueprint-only, so the
        # scenario_director layer's existing callers are unchanged.
        for key in PACKAGE_SECTION_KEYS:
            self.assertNotIn(key, SCENARIO_DIRECTOR_OUTPUT_SCHEMA["properties"])


class BeatSceneRouteTests(TestCase):
    """The route's descriptor contract and its no-content gates."""

    def setUp(self):
        register_scenario_director()

    def test_explicit_none_client_is_refused_before_any_transport(self):
        result = generate_beat_scene_blueprint(None, context=_context())
        self.assertTrue(result.result.check(ScenarioDirectorClientRequiredError))
        result.addErrback(lambda failure: None)

    @covers_requirement(
        "scenario-director::confirmed-scene-requirements-demand-a-complete-upstream-blueprint"
    )
    def test_the_call_declares_the_extended_contract_inline(self):
        client = FakeLLMClient()
        client.add_response(
            lambda descriptor: True,
            json.dumps(get_template_pool()[0].to_payload(), ensure_ascii=False),
        )
        with override_settings(LLM_PROFILES=_raw()):
            result = await_result(
                generate_beat_scene_blueprint(client, context=_context())
            )
        # A schema-valid blueprint is not a scene package: bounded no content,
        # after the existing retry budget, and never a template draw.
        self.assertIsNone(result)
        self.assertGreaterEqual(len(client.calls), 1)
        self.assertIs(client.calls[0].output_schema, EXTENDED_BLUEPRINT_SCHEMA)
        self.assertEqual(client.calls[0].schema_id, "scenario_director")

    @covers_requirement(
        "scenario-director::confirmed-scene-requirements-demand-a-complete-upstream-blueprint"
    )
    def test_a_disabled_profile_resolves_to_none_without_a_template_draw(self):
        client = FakeLLMClient()
        with override_settings(
            LLM_PROFILES=_raw(scenario_director={"enabled": False})
        ):
            with patch(
                "world.ai.scenario_director.generation.get_template_pool",
                side_effect=AssertionError("the beat scene route never draws filler"),
            ):
                result = await_result(
                    generate_beat_scene_blueprint(client, context=_context())
                )
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 0)
