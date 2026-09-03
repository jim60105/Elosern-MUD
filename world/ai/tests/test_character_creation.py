"""Tests for the character creation generative layer (generative-character-concept).

Covers prompt construction (deterministic, bounded, registry-derived race
catalog, entity-key-only), the guarded proposal entry point, the deterministic
proposal validation (registry membership, subrace compatibility, in-band
allocations with exact budget, registered suggested skills, exact three-field
bounded persona), the transient-fill normalisation matrix (clamp/truncate/trim
instead of discarding the reply), whole-proposal rejection with appended-error
retries, degrade-to-``None`` behaviour, registration semantics, and the startup
wiring.
"""

import json
from unittest.mock import patch
import unittest

from django.test import override_settings

from world.ai import guardrail
from world.ai import character_creation
from world.ai.character_creation import (
    MAX_CATALOG_LENGTH,
    MAX_CONCEPT_LENGTH,
    MAX_PERSONA_FIELD_LENGTH,
    MAX_SUGGESTED_SKILLS,
    ALLOCATABLE_AXES,
    CharacterCreationClientRequiredError,
    CharacterCreationNotRegisteredError,
    CharacterProposal,
    build_character_creation_prompt,
    build_race_catalog,
    generate_character_proposal,
    register_character_creation,
)
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import DuplicateSchemaError, _OUTPUT_SCHEMAS
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.prompts.loader import PromptUnavailableError
from world.skills.registry import SKILL_REGISTRY

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


def _proposal_text(**overrides):
    """A schema-valid human proposal whose allocations sum to the budget."""
    payload = {
        "race_key": "human",
        "subrace_key": "human_commoner",
        "allocations": {
            "hp": 100,
            "mp": 50,
            "sp": 0,
            "atk_phys": 10,
            "agility": 10,
            "defense": 11,
            "magic_power": 43,
        },
        "suggested_skills": ["flight"],
        "persona": {
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
        },
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


class CharacterCreationPromptTests(unittest.TestCase):
    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_identical_inputs_produce_byte_identical_prompts(self):
        first = build_character_creation_prompt("流浪的精靈劍士")
        second = build_character_creation_prompt("流浪的精靈劍士")
        self.assertEqual(first, second)
        self.assertEqual(first[0]["role"], "system")
        self.assertEqual(first[1]["role"], "user")
        self.assertEqual(first[0]["content"], second[0]["content"])
        self.assertIn("流浪的精靈劍士", first[0]["content"])
        self.assertIn("流浪的精靈劍士", first[1]["content"])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_concept_is_capped_before_it_enters_any_prompt(self):
        concept = "構" * (MAX_CONCEPT_LENGTH + 10)
        system, user = build_character_creation_prompt(concept)
        self.assertIn("…", system["content"])
        self.assertNotIn("構" * (MAX_CONCEPT_LENGTH + 1), system["content"])
        self.assertIn("…", user["content"])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_race_catalog_is_registry_derived_and_bounded(self):
        from world.ai.character_creation import _TRUNCATION_MARKER

        catalog = build_race_catalog()
        self.assertLessEqual(len(catalog), MAX_CATALOG_LENGTH)
        for race_key in RACE_REGISTRY:
            self.assertIn(race_key, catalog)
        for subrace_key in SUBRACE_REGISTRY:
            self.assertIn(subrace_key, catalog)
        skill_section = catalog.partition("可建議技能鍵值：")[2]
        if catalog.endswith(_TRUNCATION_MARKER):
            skill_section = skill_section[: -len(_TRUNCATION_MARKER)]
            self.assertTrue(skill_section, "a truncated catalog still lists skills")
        for segment in skill_section.split("、"):
            self.assertTrue(segment)
            self.assertIn(segment, SKILL_REGISTRY)
        self.assertEqual(build_race_catalog(), build_race_catalog())

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_race_catalog_carries_only_the_annotated_affinity_numbers(self):
        import re

        catalog = build_race_catalog()
        # The single sanctioned numbers are the per-race affinity input bounds
        # annotated on every race entry; no other mechanical number appears.
        from world.ai.character_creation import _AFFINITY_INPUT_BOUNDS

        for race_key, bound in _AFFINITY_INPUT_BOUNDS.items():
            description = RACE_REGISTRY[race_key].description
            self.assertIn(
                f"{race_key}（{description}，親附上限：{bound}）", catalog
            )
        stripped = re.sub(r"，親附上限：\d+）", "", catalog)
        self.assertEqual(re.findall(r"\d", stripped), [])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_race_catalog_names_the_element_keys(self):
        from world.lore.elements import ELEMENT_REGISTRY

        catalog = build_race_catalog()
        element_line = catalog.partition("元素鍵值：")[2].partition("\n")[0]
        for key in ELEMENT_REGISTRY:
            self.assertIn(key, element_line)

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_prompt_template_requests_the_expanded_blueprint_without_adult_wording(self):
        # The authored template (before player-concept interpolation) must name
        # the five transient fields, instruct the affinity bound, and carry no
        # adult-age wording. The rendered system message embeds the player's
        # concept, so this reads the source template directly.
        from pathlib import Path

        import yaml

        from world.prompts.loader import _prompt_root

        path = Path(_prompt_root()) / "character_creation.yaml"
        template = yaml.safe_load(path.read_text(encoding="utf-8"))["prompts"][
            "character_creation.system"
        ]
        for field in (
            "display_name",
            "age",
            "apparent_age",
            "background",
            "affinity_elements",
        ):
            self.assertIn(field, template)
        self.assertIn("親附上限", template)
        self.assertIn("精靈必須留空", template)
        self.assertIn("600 字以內", template)
        self.assertNotIn("18", template)
        self.assertNotIn("成年", template)
        self.assertNotIn("年齡一律由玩家自己輸入", template)
        self.assertNotIn("不得加入年齡欄位", template)


class CharacterCreationProposalTests(unittest.TestCase):
    def setUp(self):
        _reset_all()
        register_character_creation()

    def tearDown(self):
        _reset_all()

    def _run(self, client, **profiles):
        with override_settings(LLM_PROFILES=_raw(**profiles)):
            d = generate_character_proposal(client, concept="流浪的精靈劍士")
            return await_result(d)

    @covers_requirement("generative-character-concept::the-character-concept-command-runs-a-guarded-generative-proposal-pipeline")
    def test_valid_proposal_is_accepted_and_frozen(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _proposal_text())
        result = self._run(client)
        self.assertIsInstance(result, CharacterProposal)
        self.assertEqual(result.race_key, "human")
        self.assertEqual(result.subrace_key, "human_commoner")
        self.assertEqual(
            result.allocations,
            {"hp": 100, "mp": 50, "sp": 0, "atk_phys": 10, "agility": 10, "defense": 11, "magic_power": 43},
        )
        self.assertEqual(result.suggested_skills, ("flight",))
        self.assertEqual(
            result.persona,
            {"personality": "沉穩", "life_story": "來自邊境的小村", "habit": "清晨練劍"},
        )
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_elf_proposal_with_subrace_passes(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: True,
            _proposal_text(
                race_key="elf",
                subrace_key="fionnen",
                allocations={
                    "hp": 0,
                    "mp": 0,
                    "sp": 0,
                    "atk_phys": 12,
                    "agility": 12,
                    "defense": 13,
                    "magic_power": 400,
                },
                suggested_skills=["flight", "fire_mastery"],
            ),
        )
        result = self._run(client)
        self.assertEqual(result.race_key, "elf")
        self.assertEqual(result.subrace_key, "fionnen")

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_unregistered_race_key_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(race_key="dragon"),
        )
        client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
        result = self._run(client)
        self.assertEqual(result.race_key, "human")
        self.assertEqual(len(client.calls), 2)
        self.assertIn("not a registered race", client.calls[1].messages[-1]["content"])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_unregistered_subrace_and_mismatched_subrace_are_rejected(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(race_key="elf", subrace_key="wolfkin"),
        )
        client.add_response(
            lambda d: len(d.messages) == 3,
            _proposal_text(race_key="elf", subrace_key="nowhere"),
        )
        client.add_response(lambda d: len(d.messages) == 4, _proposal_text())
        result = self._run(client)
        self.assertEqual(len(client.calls), 3)
        messages = [call.messages[-1]["content"] for call in client.calls]
        self.assertIn("does not belong to race", messages[1])
        self.assertIn("not a registered subrace", messages[2])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_a_proposal_without_a_subrace_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(subrace_key=None),
        )
        client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
        result = self._run(client)
        self.assertEqual(result.subrace_key, "human_commoner")
        self.assertEqual(len(client.calls), 2)
        self.assertIn(
            "subrace_key must be a registered subrace",
            client.calls[1].messages[-1]["content"],
        )

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_unregistered_skill_key_is_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(suggested_skills=["teleport"]),
        )
        client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
        result = self._run(client)
        self.assertEqual(result.suggested_skills, ("flight",))
        self.assertEqual(len(client.calls), 2)
        self.assertIn("not a registered skill", client.calls[1].messages[-1]["content"])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_repeated_skill_keys_are_rejected(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(suggested_skills=["flight", "flight"]),
        )
        client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
        result = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("repeats", client.calls[1].messages[-1]["content"])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_out_of_band_allocations_are_rejected_and_retried(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(
                allocations={
                    "hp": 500,
                    "mp": 0,
                    "sp": 0,
                    "atk_phys": 0,
                    "agility": 0,
                    "defense": 0,
                    "magic_power": 0,
                }
            ),
        )
        client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
        result = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("must be an integer from 0 to", client.calls[1].messages[-1]["content"])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_budget_mismatch_is_rejected(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(
                allocations={
                    "hp": 100,
                    "mp": 50,
                    "sp": 0,
                    "atk_phys": 10,
                    "agility": 10,
                    "defense": 12,
                    "magic_power": 41,
                }
            ),
        )
        client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
        result = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("must sum exactly", client.calls[1].messages[-1]["content"])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_wrong_allocation_axis_set_is_rejected(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(
                allocations={
                    "hp": 100,
                    "mp": 50,
                    "sp": 0,
                    "atk_phys": 10,
                    "agility": 10,
                }
            ),
        )
        client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
        result = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("exactly the seven starting axes", client.calls[1].messages[-1]["content"])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_age_field_is_accepted_and_delivered(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _proposal_text(age=30))
        result = self._run(client)
        self.assertEqual(result.race_key, "human")
        self.assertEqual(result.age, 30)
        self.assertIsNone(result.apparent_age)
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_extra_numeric_field_is_rejected(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(magic_power=5),
        )
        client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
        result = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("magic_power", client.calls[1].messages[-1]["content"])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_invalid_persona_rejects_the_whole_proposal_and_retries(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(
                persona={"personality": "沉穩", "life_story": "來自邊境的小村"}
            ),
        )
        client.add_response(
            lambda d: len(d.messages) == 3,
            _proposal_text(
                persona={
                    "personality": "沉穩",
                    "life_story": "來自邊境的小村",
                    "habit": "清晨練劍",
                    "extra": "多餘",
                }
            ),
        )
        client.add_response(lambda d: len(d.messages) == 4, _proposal_text())
        result = self._run(client)
        self.assertEqual(result.persona["habit"], "清晨練劍")
        self.assertEqual(len(client.calls), 3)
        messages = [call.messages[-1]["content"] for call in client.calls]
        self.assertIn("must contain exactly", messages[1])
        self.assertIn("must contain exactly", messages[2])

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_overlong_persona_field_rejects_the_whole_proposal(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(
                persona={
                    "personality": "字" * (MAX_PERSONA_FIELD_LENGTH + 1),
                    "life_story": "來自邊境的小村",
                    "habit": "清晨練劍",
                }
            ),
        )
        client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
        result = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("length cap", client.calls[1].messages[-1]["content"])

    @covers_requirement("generative-character-concept::the-character-creation-layer-is-registered-in-the-guardrail-with-retry-and-degrade")
    def test_empty_persona_field_rejects_the_whole_proposal(self):
        client = FakeLLMClient()
        client.add_response(
            lambda d: len(d.messages) == 2,
            _proposal_text(
                persona={"personality": "", "life_story": "來自邊境的小村", "habit": "清晨練劍"}
            ),
        )
        client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
        result = self._run(client)
        self.assertEqual(len(client.calls), 2)
        self.assertIn("non-empty", client.calls[1].messages[-1]["content"])

    @covers_requirement("generative-character-concept::the-character-creation-layer-is-registered-in-the-guardrail-with-retry-and-degrade")
    def test_non_json_output_degrades_without_touching_state(self):
        client = FakeLLMClient()
        client.add_malformed_body(lambda d: True)
        result = self._run(client)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("generative-character-concept::the-character-creation-layer-is-registered-in-the-guardrail-with-retry-and-degrade")
    def test_retry_exhaustion_degrades_within_the_budget(self):
        client = FakeLLMClient()
        # A boolean age is a type error the output schema rejects on every
        # attempt: structurally invalid output keeps the retry path intact.
        client.add_response(lambda d: True, _proposal_text(age=True))
        result = self._run(client, character_creation={"max_retries": 2})
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 3)

    @covers_requirement("generative-character-concept::the-character-creation-layer-is-registered-in-the-guardrail-with-retry-and-degrade")
    def test_disabled_profile_resolves_to_none_with_zero_client_calls(self):
        client = FakeLLMClient()
        result = self._run(client, character_creation={"enabled": False})
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 0)

    @covers_requirement("generative-character-concept::the-character-creation-layer-is-registered-in-the-guardrail-with-retry-and-degrade")
    def test_transport_failure_resolves_to_none(self):
        client = FakeLLMClient()
        client.add_timeout(lambda d: True)
        result = self._run(client)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("generative-character-concept::the-character-creation-layer-is-registered-in-the-guardrail-with-retry-and-degrade")
    def test_prompt_unavailable_key_degrades_with_zero_client_calls(self):
        client = FakeLLMClient()
        with patch(
            "world.ai.character_creation.render_prompt",
            side_effect=PromptUnavailableError("character_creation.yaml", "character_creation.system", "broken"),
        ):
            result = self._run(client)
        self.assertIsNone(result)
        self.assertEqual(len(client.calls), 0)

    def test_explicit_none_client_is_rejected(self):
        d = generate_character_proposal(None, concept="流浪的精靈劍士")
        failure = await_result(d)
        self.assertTrue(failure.check(CharacterCreationClientRequiredError))

    def test_unregistered_layer_raises_a_named_error(self):
        _reset_all()
        d = generate_character_proposal(FakeLLMClient(), concept="流浪的精靈劍士")
        failure = await_result(d)
        self.assertTrue(failure.check(CharacterCreationNotRegisteredError))


class AllocationParityTests(unittest.TestCase):
    """The layer's registry-derived bands/budget must match the preflight's.

    The layer cannot import ``world.rules`` (transport-boundary contract), so
    the band arithmetic is re-derived from the same lore registries. This test
    pins every race/subrace combination against the authoritative
    ``resolve_starting_profile`` so a future registry or rules change cannot
    make the layer accept a proposal the activation preflight would reject.
    """

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_bands_and_budget_match_the_deterministic_preflight_for_every_profile(self):
        from world.ai.character_creation import _allocation_budget, _race_bands
        from world.rules.character_creation import resolve_starting_profile

        for race_key in RACE_REGISTRY:
            subrace_keys = [
                key for key, subrace in SUBRACE_REGISTRY.items()
                if subrace.race_key == race_key
            ]
            for subrace_key in subrace_keys:
                with self.subTest(race=race_key, subrace=subrace_key):
                    profile = resolve_starting_profile(race_key, subrace_key)
                    self.assertEqual(
                        _race_bands(race_key, subrace_key),
                        profile.bounds_dict(),
                    )
                    self.assertEqual(
                        _allocation_budget(race_key, subrace_key),
                        profile.budget,
                    )


class TransientFillParityTests(unittest.TestCase):
    """The layer's transient-fill bounds must mirror the authoritative rules.

    The transport-boundary contract forbids importing ``world.rules`` from the
    layer, so the bounds are local mirrors (the ``ALLOCATABLE_AXES`` precedent).
    These assertions lock every mirrored value against the rule layer.
    """

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_transient_fill_bounds_mirror_the_rule_layer(self):
        from world.rules import creation_wizard
        from world.rules import character_creation as rules_creation

        self.assertEqual(
            character_creation.ADULT_AGE_MINIMUM, creation_wizard.AGE_MINIMUM
        )
        self.assertEqual(
            character_creation.AGE_MAXIMUM_BOUND, creation_wizard.AGE_MAXIMUM
        )
        self.assertEqual(
            character_creation._AFFINITY_INPUT_BOUNDS,
            rules_creation._AFFINITY_INPUT_BOUNDS,
        )
        self.assertEqual(
            set(character_creation._AFFINITY_INPUT_BOUNDS), set(RACE_REGISTRY)
        )


def _in_band_allocations(race_key: str, subrace_key: str) -> dict[str, int]:
    """Greedily spend a race's full allocation budget inside its bands."""
    from world.ai.character_creation import _allocation_budget, _race_bands

    bands = _race_bands(race_key, subrace_key)
    remaining = _allocation_budget(race_key, subrace_key)
    allocations: dict[str, int] = {}
    for axis in ALLOCATABLE_AXES:
        span = bands[axis][1] - bands[axis][0]
        take = min(span, remaining)
        allocations[axis] = take
        remaining -= take
    assert remaining == 0
    return allocations


class TransientFillNormalizationTests(unittest.TestCase):
    """Out-of-bounds transient-fill values normalise, never discard the reply."""

    def setUp(self):
        _reset_all()
        register_character_creation()

    def tearDown(self):
        _reset_all()

    def _run(self, client, **profiles):
        with override_settings(LLM_PROFILES=_raw(**profiles)):
            d = generate_character_proposal(client, concept="流浪的精靈劍士")
            return await_result(d)

    def _once(self, **payload_overrides):
        client = FakeLLMClient()
        client.add_response(lambda d: True, _proposal_text(**payload_overrides))
        return self._run(client), client

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_ages_clamp_to_the_band_without_consuming_a_retry(self):
        cases = [
            ({"age": 17, "apparent_age": 10}, 18, 18),
            ({"age": 10001, "apparent_age": 99999}, 10000, 10000),
            ({"age": 18, "apparent_age": 10000}, 18, 10000),
            ({"age": 30, "apparent_age": 25}, 30, 25),
        ]
        for payload, age, apparent in cases:
            with self.subTest(**payload):
                result, client = self._once(**payload)
                self.assertEqual(result.age, age)
                self.assertEqual(result.apparent_age, apparent)
                self.assertEqual(len(client.calls), 1)

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_transient_text_is_truncated_or_collapses_to_absent(self):
        from world.ai.character_creation import MAX_DISPLAY_NAME_CODE_POINTS

        result, client = self._once(
            display_name="名" * (MAX_DISPLAY_NAME_CODE_POINTS + 1),
            background="景" * (MAX_PERSONA_FIELD_LENGTH + 1),
        )
        self.assertEqual(
            result.display_name, "名" * MAX_DISPLAY_NAME_CODE_POINTS
        )
        self.assertEqual(result.background, "景" * MAX_PERSONA_FIELD_LENGTH)
        self.assertEqual(len(client.calls), 1)

        result, _ = self._once(display_name="   ", background=" \n ")
        self.assertIsNone(result.display_name)
        self.assertIsNone(result.background)

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_affinity_is_trimmed_to_the_registry_and_the_race_bound(self):
        result, _ = self._once(affinity_elements=["fire", "unknown", "fire", "water"])
        self.assertEqual(result.affinity_elements, ("fire", "water"))

        result, _ = self._once(affinity_elements=["unknown", "ghost"])
        self.assertEqual(result.affinity_elements, ())

        beastfolk = {
            "race_key": "beastfolk",
            "subrace_key": "catkin",
            "allocations": _in_band_allocations("beastfolk", "catkin"),
        }
        result, _ = self._once(**beastfolk, affinity_elements=["fire", "water"])
        self.assertEqual(result.affinity_elements, ("fire",))

        elf = {
            "race_key": "elf",
            "subrace_key": "fionnen",
            "allocations": _in_band_allocations("elf", "fionnen"),
        }
        result, _ = self._once(**elf, affinity_elements=["fire", "water", "wind"])
        self.assertEqual(result.affinity_elements, ())

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_absent_transient_fields_normalise_to_none(self):
        result, client = self._once()
        self.assertIsNone(result.display_name)
        self.assertIsNone(result.age)
        self.assertIsNone(result.apparent_age)
        self.assertIsNone(result.background)
        self.assertIsNone(result.affinity_elements)
        self.assertEqual(len(client.calls), 1)

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_wrong_typed_transient_fields_take_the_retry_path(self):
        for label, payload in [
            ("boolean age", {"age": True}),
            ("non-list affinity", {"affinity_elements": "fire"}),
            ("non-string name", {"display_name": 42}),
        ]:
            with self.subTest(label):
                client = FakeLLMClient()
                client.add_response(
                    lambda d: len(d.messages) == 2, _proposal_text(**payload)
                )
                client.add_response(lambda d: len(d.messages) == 3, _proposal_text())
                result = self._run(client)
                self.assertEqual(len(client.calls), 2)
                self.assertIsNotNone(result)
                self.assertIsNone(result.age)

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_elf_affinity_bound_annotation_still_empties_a_valid_elf_set(self):
        elf = {
            "race_key": "elf",
            "subrace_key": "fionnen",
            "allocations": _in_band_allocations("elf", "fionnen"),
        }
        result, client = self._once(**elf, affinity_elements=["fire"])
        self.assertEqual(result.race_key, "elf")
        self.assertEqual(result.affinity_elements, ())
        self.assertEqual(len(client.calls), 1)
    """The layer's registry-derived bands/budget must match the preflight's.

    The layer cannot import ``world.rules`` (transport-boundary contract), so
    the band arithmetic is re-derived from the same lore registries. This test
    pins every race/subrace combination against the authoritative
    ``resolve_starting_profile`` so a future registry or rules change cannot
    make the layer accept a proposal the activation preflight would reject.
    """

    @covers_requirement("generative-character-concept::proposals-are-validated-deterministically-against-the-registries")
    def test_bands_and_budget_match_the_deterministic_preflight_for_every_profile(self):
        from world.ai.character_creation import _allocation_budget, _race_bands
        from world.rules.character_creation import resolve_starting_profile

        for race_key in RACE_REGISTRY:
            subrace_keys = [
                key for key, subrace in SUBRACE_REGISTRY.items()
                if subrace.race_key == race_key
            ]
            for subrace_key in subrace_keys:
                with self.subTest(race=race_key, subrace=subrace_key):
                    profile = resolve_starting_profile(race_key, subrace_key)
                    self.assertEqual(
                        _race_bands(race_key, subrace_key),
                        profile.bounds_dict(),
                    )
                    self.assertEqual(
                        _allocation_budget(race_key, subrace_key),
                        profile.budget,
                    )


class RegistrationTests(unittest.TestCase):
    def tearDown(self):
        _reset_all()

    def test_registration_is_idempotent_and_holds_every_hook(self):
        register_character_creation()
        self.assertTrue(character_creation._is_registered())
        register_character_creation()
        self.assertTrue(character_creation._is_registered())
        self.assertEqual(
            set(guardrail._semantic_validators["character_creation"]),
            set(character_creation._VALIDATORS),
        )
        self.assertIs(
            guardrail._degrade_fallbacks["character_creation"],
            character_creation._degrade_fallback,
        )
        self.assertIs(
            _OUTPUT_SCHEMAS["character_creation"],
            character_creation.CHARACTER_CREATION_OUTPUT_SCHEMA,
        )

    def test_registration_is_atomic_on_partial_failure(self):
        _reset_all()
        guardrail._degrade_fallbacks["character_creation"] = lambda: "foreign"
        with self.assertRaises(Exception):
            register_character_creation()
        self.assertFalse(character_creation._is_registered())

    def test_schema_conflict_raises_without_half_installed_hooks(self):
        _reset_all()
        _OUTPUT_SCHEMAS["character_creation"] = {"type": "object"}
        with self.assertRaises(DuplicateSchemaError):
            register_character_creation()
        self.assertNotIn("character_creation", guardrail._degrade_fallbacks)
        self.assertEqual(
            guardrail._semantic_validators.get("character_creation"), {}
        )
        self.assertFalse(character_creation._is_registered())


class StartupRegistrationTests(unittest.TestCase):
    def setUp(self):
        _reset_all()

    def tearDown(self):
        _reset_all()

    @covers_requirement("generative-character-concept::the-character-creation-layer-is-registered-in-the-guardrail-with-retry-and-degrade")
    def test_startup_seam_registers_the_layer_with_the_sentinel_fallback(self):
        from server.conf.at_server_startstop import _register_character_creation_layer

        _register_character_creation_layer()
        self.assertTrue(character_creation._is_registered())
        self.assertIs(
            guardrail._degrade_fallbacks["character_creation"],
            character_creation._degrade_fallback,
        )

    @covers_requirement("generative-character-concept::the-character-creation-layer-is-registered-in-the-guardrail-with-retry-and-degrade")
    def test_startup_seam_survives_a_foreign_character_creation_registration(self):
        from server.conf.at_server_startstop import _register_character_creation_layer

        guardrail.register_degrade_fallback("character_creation", lambda: "foreign-degrade")
        _register_character_creation_layer()
        self.assertFalse(character_creation._is_registered())


if __name__ == "__main__":
    unittest.main()
