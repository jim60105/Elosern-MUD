"""Tests for the ScenarioDirector generative layer (scenario-director).

Covers the frozen proposal dataclasses (immutability by construction, closed
vocabularies, stage-index contiguity, JSON-safe payload round-trip), the
deterministic bounded prompt construction, the registered output schema and
semantic validators, atomic idempotent registration, the guarded entry point
with request-context enforcement, the hand-written template pool, the startup
wiring, and the offline test rule (FakeLLMClient only, never a live endpoint).
"""

import json
from unittest.mock import patch
import unittest

from django.test import override_settings

from world.ai import guardrail
from world.ai import scenario_director
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import GuardrailRegistrationError
from world.ai.scenario_director import (
    MAX_CONTEXT_FIELD_LENGTH,
    MAX_NAME_LENGTH,
    MAX_TOTAL_SIZE,
    QuestBlueprint,
    ScenarioDirectorClientRequiredError,
    ScenarioDirectorNotRegisteredError,
    ScenarioDirectorTemplateError,
    BlueprintFailure,
    BlueprintItemQuantity,
    BlueprintLocation,
    BlueprintNpcReq,
    BlueprintObjective,
    BlueprintPortrait,
    BlueprintReward,
    BlueprintStage,
    build_scenario_prompt,
    generate_quest_blueprint,
    register_scenario_director,
)
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import DuplicateSchemaError, _OUTPUT_SCHEMAS
from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.quests.tests._fixtures import RegistryIsolationMixin

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


def _item(item_key="healing_potion", quantity=1):
    return BlueprintItemQuantity(item_key, quantity)


def _location(layer="anchor", archetype="forest_path", anchor_key="capital_altoria"):
    return BlueprintLocation(
        layer=layer,
        archetype=archetype,
        anchor_key=anchor_key,
        scene_sentence="王都近郊的林間小徑，樹影搖曳。",
    )


def _stage(index=0, kind="defeat", monster_tier="low", location=None):
    return BlueprintStage(
        index=index,
        objective=BlueprintObjective(kind=kind, monster_tier=monster_tier),
        location=location if location is not None else _location(),
    )


def _blueprint(
    name="討伐低階魔物",
    quest_type="討伐",
    rank="F",
    issuer="guild_branch_altoria",
    stages=None,
    copper=50,
    merit=25,
    deadline_hours=None,
):
    if stages is None:
        stages = (_stage(),)
    return QuestBlueprint(
        name=name,
        quest_type=quest_type,
        rank=rank,
        issuer=issuer,
        stages=stages,
        reward=BlueprintReward(copper=copper, items=(_item(),), merit=merit),
        failure=BlueprintFailure(deadline_hours=deadline_hours, conditions=()),
    )


def _payload(blueprint=None):
    return (blueprint or _blueprint()).to_payload()


def _context(**overrides):
    context = {
        "requested_type": "討伐",
        "allowed_rank": "F",
        "issuer_branch": "guild_branch_altoria",
        "anchor": "capital_altoria",
    }
    context.update(overrides)
    return context


class ScenarioDirectorProposalTypeTests(unittest.TestCase):
    @covers_requirement("scenario-director::questblueprint-is-the-closed-deeply-immutable-ai-proposal-type")
    def test_valid_blueprint_preserves_explicit_stage_indices(self):
        blueprint = _blueprint(
            stages=(
                BlueprintStage(
                    0, BlueprintObjective("defeat", monster_tier="low")
                ),
                BlueprintStage(
                    1,
                    BlueprintObjective("acquire", item_key="healing_potion", quantity=1),
                ),
            )
        )
        self.assertEqual([stage.index for stage in blueprint.stages], [0, 1])

    @covers_requirement("scenario-director::questblueprint-is-the-closed-deeply-immutable-ai-proposal-type")
    def test_content_cannot_be_mutated_after_construction(self):
        from dataclasses import FrozenInstanceError

        blueprint = _blueprint()
        with self.assertRaises(FrozenInstanceError):
            blueprint.name = "changed"
        with self.assertRaises(FrozenInstanceError):
            blueprint.stages[0].objective.monster_tier = "high"

    @covers_requirement("scenario-director::questblueprint-is-the-closed-deeply-immutable-ai-proposal-type")
    def test_mutable_containers_are_rejected_at_construction(self):
        with self.assertRaises(TypeError):
            QuestBlueprint(
                name="討伐",
                quest_type="討伐",
                rank="F",
                issuer="guild_branch_altoria",
                stages=[BlueprintStage(0, BlueprintObjective("defeat", monster_tier="low"))],
                reward=BlueprintReward(copper=50, items=(_item(),), merit=25),
                failure=BlueprintFailure(conditions=()),
            )

    @covers_requirement("scenario-director::questblueprint-is-the-closed-deeply-immutable-ai-proposal-type")
    def test_unknown_quest_type_fails_construction(self):
        with self.assertRaises(ValueError):
            _blueprint(quest_type="不明")

    @covers_requirement("scenario-director::questblueprint-is-the-closed-deeply-immutable-ai-proposal-type")
    def test_non_contiguous_stage_indices_fail_construction(self):
        with self.assertRaises(ValueError):
            _blueprint(
                stages=(
                    BlueprintStage(0, BlueprintObjective("defeat", monster_tier="low")),
                    BlueprintStage(2, BlueprintObjective("defeat", monster_tier="low")),
                )
            )

    def test_to_payload_round_trips_through_json_without_live_refs(self):
        blueprint = _blueprint()
        payload = blueprint.to_payload()
        round_tripped = json.loads(json.dumps(payload, ensure_ascii=False))
        rebuilt = QuestBlueprint.from_payload(round_tripped)
        self.assertEqual(rebuilt, blueprint)
        self.assertNotIn("object at", json.dumps(payload))

    def test_unknown_location_layer_fails_construction(self):
        with self.assertRaises(ValueError):
            BlueprintLocation(layer="nowhere")

    def test_unknown_objective_kind_fails_construction(self):
        with self.assertRaises(ValueError):
            BlueprintObjective(kind="explode")

    def test_objective_quantity_must_be_a_positive_integer(self):
        with self.assertRaises(ValueError):
            BlueprintObjective(kind="defeat", quantity=0)
        with self.assertRaises(ValueError):
            BlueprintObjective(kind="defeat", quantity=True)

    def test_failure_conditions_must_stay_empty(self):
        with self.assertRaises(ValueError):
            BlueprintFailure(conditions=("something",))

    def test_blueprint_requires_at_least_one_stage(self):
        with self.assertRaises(ValueError):
            _blueprint(stages=())


class BlueprintCharacterizationTypeTests(unittest.TestCase):
    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_frozen_portrait_value_object_passes_the_immutability_guard(self):
        from dataclasses import FrozenInstanceError

        portrait = BlueprintPortrait(stable_key="library_keeper")
        self.assertEqual(portrait.stable_key, "library_keeper")
        with self.assertRaises(FrozenInstanceError):
            portrait.stable_key = "changed"
        requirement = BlueprintNpcReq(
            role="librarian",
            tier="civilian",
            disposition=None,
            display_name="莉絲·晨星",
            age=68,
            apparent_age=68,
            portrait=portrait,
        )
        self.assertEqual(requirement.portrait.stable_key, "library_keeper")

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_mutable_containers_are_still_rejected_under_a_portrait_field(self):
        with self.assertRaises(TypeError):
            BlueprintNpcReq(
                role="librarian",
                tier="civilian",
                portrait={"stable_key": "library_keeper"},  # raw dict rejected
            )

    @covers_requirement("blueprint-portrait-policy::the-blueprint-lifecycle-preserves-the-characterization-fields")
    def test_round_trip_preserves_all_four_characterization_fields(self):
        blueprint = _blueprint(
            stages=(
                BlueprintStage(
                    index=0,
                    objective=BlueprintObjective(
                        kind="defeat", quantity=1, monster_tier=None
                    ),
                    location=BlueprintLocation(
                        layer="instance",
                        archetype="forest_path",
                        anchor_key=None,
                        anchor_near="capital_altoria",
                        xyz=None,
                        scene_sentence="王都近郊的林間小徑，樹影搖曳。",
                    ),
                    npc_reqs=(
                        BlueprintNpcReq(
                            role="bandit",
                            tier="bandit",
                            disposition=None,
                            display_name="黑鬍",
                            age=35,
                            apparent_age=35,
                            portrait=BlueprintPortrait(
                                stable_key="forest_bandit_chief"
                            ),
                            background="來自邊境的資深嚮導",
                            persona=(
                                ("personality", "沉穩"),
                                ("life_story", "守護森林多年"),
                                ("habit", "黃昏時擦拭獵弓"),
                            ),
                        ),
                    ),
                ),
            )
        )
        payload = blueprint.to_payload()
        round_tripped = json.loads(json.dumps(payload, ensure_ascii=False))
        rebuilt = QuestBlueprint.from_payload(round_tripped)
        requirement = rebuilt.stages[0].npc_reqs[0]
        self.assertEqual(requirement.display_name, "黑鬍")
        self.assertEqual(requirement.age, 35)
        self.assertEqual(requirement.apparent_age, 35)
        self.assertEqual(requirement.portrait.stable_key, "forest_bandit_chief")
        self.assertEqual(requirement.background, "來自邊境的資深嚮導")
        self.assertEqual(
            dict(requirement.persona),
            {
                "personality": "沉穩",
                "life_story": "守護森林多年",
                "habit": "黃昏時擦拭獵弓",
            },
        )

    @covers_requirement("blueprint-portrait-policy::the-blueprint-lifecycle-preserves-the-characterization-fields")
    def test_field_less_blueprint_round_trips_byte_identically(self):
        plain = _blueprint()
        payload = plain.to_payload()
        rebuilt = QuestBlueprint.from_payload(payload)
        self.assertEqual(rebuilt, plain)
        self.assertEqual(payload["stages"][0]["npc_req"], [])
        self.assertNotIn("display_name", payload["stages"][0])
        self.assertNotIn("portrait", payload["stages"][0])

    @covers_requirement("blueprint-portrait-policy::the-blueprint-lifecycle-preserves-the-characterization-fields")
    def test_characterization_differences_change_the_content_digest(self):
        from world.quests.compile import compile_quest_blueprint

        base = _blueprint()
        base_payload = base.to_payload()
        base_payload["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        base_payload["stages"][0]["location_req"] = {
            "layer": "instance",
            "archetype": "forest_path",
            "anchor_key": None,
            "anchor_near": "capital_altoria",
            "xyz": None,
            "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
        }
        base_payload["stages"][0]["npc_req"] = [
            {"role": "bandit", "tier": "bandit", "disposition": None}
        ]
        first = compile_quest_blueprint(base_payload)

        changed = json.loads(json.dumps(base_payload))
        changed["stages"][0]["npc_req"][0].update(
            {
                "display_name": "黑鬍",
                "age": 35,
                "apparent_age": 35,
                "portrait": {"stable_key": "forest_bandit_chief"},
            }
        )
        second = compile_quest_blueprint(changed)
        self.assertNotEqual(first.definition.key, second.definition.key)


class ScenarioDirectorPromptTests(unittest.TestCase):
    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_identical_contexts_produce_byte_identical_prompts(self):
        first = build_scenario_prompt(_context())
        second = build_scenario_prompt(_context())
        self.assertEqual(first, second)
        self.assertEqual(first[0]["role"], "system")
        self.assertEqual(first[1]["role"], "user")
        self.assertEqual(first[0]["content"], second[0]["content"])
        self.assertEqual(first[1]["content"], second[1]["content"])

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_oversized_context_is_bounded_and_valid(self):
        context = _context(note="字" * (MAX_CONTEXT_FIELD_LENGTH * 4))
        system, user = build_scenario_prompt(context)
        self.assertLessEqual(len(user["content"]), MAX_TOTAL_SIZE)
        parsed = json.loads(user["content"])
        self.assertLessEqual(len(parsed["note"]), MAX_CONTEXT_FIELD_LENGTH)
        self.assertEqual(parsed["issuer_branch"], "guild_branch_altoria")

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_system_message_names_the_blueprint_contract_and_fidelity(self):
        system, _ = build_scenario_prompt(_context())
        self.assertIn("QuestBlueprint", system["content"])
        self.assertIn("不得編造", system["content"])
        self.assertIn("正體中文", system["content"])
        self.assertIn("伊洛瑟恩大陸", system["content"])

    @covers_requirement("scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful")
    def test_user_message_carries_keys_and_no_live_objects(self):
        _, user = build_scenario_prompt(
            _context(issuer_branch="guild_branch_altoria", anchor="capital_altoria")
        )
        self.assertIn("guild_branch_altoria", user["content"])
        self.assertIn("capital_altoria", user["content"])
        self.assertNotIn("<", user["content"])
        self.assertNotIn("object at", user["content"])


class ScenarioDirectorValidatorTests(unittest.TestCase):
    def setUp(self):
        _reset_all()
        register_scenario_director()

    def tearDown(self):
        _reset_all()

    @covers_requirement("guardrail::semantic-validators-are-pluggable-and-layer-scoped")
    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_malformed_rank_reward_and_item_shapes_are_rejected(self):
        validators = scenario_director._VALIDATORS
        self.assertTrue(validators["rank_known"]({"rank": 7}))
        reward_errors = validators["reward_in_band"](
            {"rank": "F", "reward": {"copper": True, "merit": -1}}
        )
        self.assertIn("reward copper must be an integer", reward_errors)
        self.assertIn("reward merit must be a non-negative integer", reward_errors)
        self.assertEqual(validators["reward_in_band"]({"reward": "nope"}), [])
        self.assertEqual(validators["reward_items_known"]({"reward": {}}), [])
        item_errors = validators["reward_items_known"](
            {
                "reward": {
                    "items": [
                        {"item_key": "healing_potion", "quantity": 0},
                        {"item_key": "healing_potion", "quantity": 1},
                        {"item_key": "no_such_item", "quantity": 1},
                        "bogus",
                    ]
                }
            }
        )
        self.assertIn(
            "reward item 'healing_potion' quantity must be a positive integer",
            item_errors,
        )
        self.assertIn("duplicate reward item key 'healing_potion'", item_errors)
        self.assertIn("unknown reward item 'no_such_item'", item_errors)
        self.assertIn("reward items must be objects", item_errors)

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_validators_tolerate_malformed_root_and_stage_shapes(self):
        validators = scenario_director._VALIDATORS
        self.assertEqual(
            validators["rank_known"]("not-a-dict"),
            ["quest rank None is not in GUILD_RANK_REGISTRY"],
        )
        self.assertEqual(validators["reward_in_band"]("not-a-dict"), [])
        self.assertEqual(validators["reward_items_known"]("not-a-dict"), [])
        for name in (
            "archetype_known",
            "npc_tier_known",
            "monster_tier_known",
            "anchor_known",
            "defeat_selector",
            "objective_selectors",
            "stage_indices_contiguous",
            "deadline_valid",
        ):
            self.assertEqual(validators[name]("not-a-dict"), [], name)

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_unknown_rank_is_rejected_and_retried_with_error_appended(self):
        client = FakeLLMClient()
        bad = _payload(_blueprint(rank="Z"))
        good = _payload()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(good, ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result.rank, "F")
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_out_of_band_reward_copper_is_rejected(self):
        client = FakeLLMClient()
        bad = _payload(_blueprint(copper=10_000))
        good = _payload()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(good, ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result.reward.copper, 50)
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_unknown_archetype_is_rejected(self):
        client = FakeLLMClient()
        bad = _blueprint(stages=(_stage(location=_location(archetype="bogus")),))
        good = _blueprint()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(_payload(bad), ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(good), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, good)

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_unknown_npc_tier_is_rejected(self):
        client = FakeLLMClient()
        bad = _blueprint(
            stages=(
                BlueprintStage(
                    0,
                    BlueprintObjective("defeat", monster_tier="low"),
                    location=None,
                    npc_reqs=(BlueprintNpcReq("victim", "bogus"),),
                ),
            )
        )
        good = _blueprint()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(_payload(bad), ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(good), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, good)

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_npc_persona_and_background_are_validated_through_the_shared_helper(self):
        validators = scenario_director._VALIDATORS
        validate_npc = validators["npc_characterization"]
        good = {
            "stages": [
                {
                    "npc_req": [
                        {
                            "role": "bandit",
                            "tier": "bandit",
                            "persona": {
                                "personality": "沉穩",
                                "life_story": "守護森林多年",
                                "habit": "黃昏時擦拭獵弓",
                            },
                            "background": "來自邊境的嚮導",
                        }
                    ]
                }
            ]
        }
        self.assertEqual(validate_npc(good), [])
        over_bound = {
            "stages": [
                {
                    "npc_req": [
                        {
                            "role": "bandit",
                            "tier": "bandit",
                            "persona": {"personality": "x" * 601},
                        }
                    ]
                }
            ]
        }
        errors = validate_npc(over_bound)
        self.assertTrue(
            any("persona.personality" in error for error in errors), errors
        )
        non_text = {
            "stages": [
                {
                    "npc_req": [
                        {
                            "role": "bandit",
                            "tier": "bandit",
                            "background": 42,
                        }
                    ]
                }
            ]
        }
        self.assertTrue(validate_npc(non_text))

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_unknown_monster_tier_is_rejected(self):
        client = FakeLLMClient()
        bad = _blueprint(stages=(_stage(monster_tier="bogus"),))
        good = _blueprint()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(_payload(bad), ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(good), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, good)

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_unknown_issuer_is_rejected(self):
        client = FakeLLMClient()
        bad = _payload(_blueprint(issuer="guild_branch_bogus"))
        good = _payload()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(good, ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result.issuer, "guild_branch_altoria")

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_non_contiguous_stage_indices_are_rejected(self):
        client = FakeLLMClient()
        bad = _payload()
        bad["stages"] = [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": "low"},
                "location_req": None,
                "npc_req": [],
            },
            {
                "index": 2,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": "low"},
                "location_req": None,
                "npc_req": [],
            },
        ]
        good = _blueprint()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(good), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, good)

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_valid_bounded_blueprint_passes_on_first_attempt(self):
        client = FakeLLMClient()
        client.add_response(lambda d: True, json.dumps(_payload(), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result.rank, "F")
        self.assertEqual(len(client.calls), 1)

    def test_defeat_without_selector_is_rejected_and_retried(self):
        client = FakeLLMClient()
        bad = _payload()
        bad["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        bad["stages"][0]["npc_req"] = []
        good = _blueprint()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(good), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, good)
        self.assertEqual(len(client.calls), 2)

    def test_defeat_with_both_selectors_is_rejected_and_retried(self):
        client = FakeLLMClient()
        bad = _payload()
        bad["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": "low",
        }
        bad["stages"][0]["npc_req"] = [
            {"role": "victim", "tier": "civilian", "disposition": "frightened"}
        ]
        good = _blueprint()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(good), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, good)
        self.assertEqual(len(client.calls), 2)

    def test_acquire_without_item_key_is_rejected_and_retried(self):
        client = FakeLLMClient()
        bad = _payload()
        bad["quest_type"] = "採集"
        bad["stages"][0]["objective"] = {"kind": "acquire", "quantity": 1, "item_key": None}
        bad["stages"][0]["location_req"] = None
        good = _blueprint()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(good), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, good)
        self.assertEqual(len(client.calls), 2)

    def test_reach_without_destination_is_rejected_and_retried(self):
        client = FakeLLMClient()
        bad = _payload()
        bad["quest_type"] = "探索"
        bad["stages"][0]["objective"] = {"kind": "reach_location", "quantity": 1}
        bad["stages"][0]["location_req"] = None
        good = _blueprint()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(good), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, good)
        self.assertEqual(len(client.calls), 2)

    def test_unplaced_anchor_is_rejected_and_retried(self):
        client = FakeLLMClient()
        bad = _payload()
        bad["stages"][0]["location_req"]["anchor_key"] = "capital_grandia"
        good = _blueprint()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(good), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, good)
        self.assertEqual(len(client.calls), 2)


class SceneBoundValidatorTests(RegistryIsolationMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        _reset_all()
        register_scenario_director()

    def tearDown(self):
        _reset_all()

    def _instance_bound_payload(self, **overrides):
        payload = _payload()
        payload["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        payload["stages"][0]["location_req"] = {
            "layer": "instance",
            "archetype": "forest_path",
            "anchor_key": None,
            "anchor_near": "capital_altoria",
            "xyz": None,
            "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
        }
        payload["stages"][0]["npc_req"] = [
            {"role": "bandit", "tier": "bandit", "disposition": None}
        ]
        payload.update(overrides)
        return payload

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_occupant_stage_at_anchor_is_rejected_and_retried(self):
        bad = self._instance_bound_payload()
        bad["stages"][0]["location_req"]["layer"] = "anchor"
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, _blueprint())
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_bound_defeat_quantity_exceeding_is_rejected_and_retried(self):
        bad = self._instance_bound_payload()
        bad["stages"][0]["objective"]["quantity"] = 2
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, _blueprint())
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_unknown_anchor_near_is_rejected_and_retried(self):
        bad = _payload()
        bad["stages"][0]["location_req"]["anchor_near"] = "capital_grandia"
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, _blueprint())
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_escort_stage_at_instance_is_rejected_and_retried(self):
        bad = self._instance_bound_payload()
        bad["quest_type"] = "護衛"
        bad["stages"][0]["objective"] = {"kind": "escort", "quantity": 1}
        bad["stages"][0]["npc_req"] = []
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, _blueprint())
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    @covers_requirement("quest-blueprint::escort-quests-require-a-bound-protected-entity-path")
    def test_escort_stage_at_anchor_is_rejected_and_retried(self):
        bad = _payload()
        bad["quest_type"] = "護衛"
        bad["stages"][0]["objective"] = {"kind": "escort", "quantity": 1}
        bad["stages"][0]["npc_req"] = []
        for validator_fn in scenario_director._VALIDATORS.values():
            if validator_fn(bad):
                break
        else:
            self.fail("no validator rejected the unbindable escort proposal")
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, _blueprint())
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    @covers_requirement("quest-blueprint::reach-and-escort-objectives-accept-only-quantity-one")
    def test_reach_quantity_two_is_rejected_and_retried(self):
        bad = _payload()
        bad["quest_type"] = "探索"
        bad["stages"][0]["objective"] = {"kind": "reach_location", "quantity": 2}
        client = FakeLLMClient()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(_payload(), ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, _blueprint())
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_valid_instance_bound_payload_passes_guardrail_and_compiles(self):
        payload = self._instance_bound_payload()
        for validator_fn in scenario_director._VALIDATORS.values():
            self.assertEqual(validator_fn(payload), [])
        from world.quests.compile import (
            SCENE_REQUIREMENT_REGISTRY,
            compile_quest_blueprint,
            register_generated_quest,
        )
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY, validate_definition
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        compiled = compile_quest_blueprint(payload)
        validate_definition(compiled.definition)
        with patch(
            "world.quests.compile.append_generated_quest_payload", return_value=True
        ):
            register_generated_quest(compiled)
        self.assertIn(compiled.definition.key, QUEST_DEFINITION_REGISTRY)


class CharacterizationValidatorTests(unittest.TestCase):
    def setUp(self):
        _reset_all()
        register_scenario_director()

    def tearDown(self):
        _reset_all()

    def _instance_bound_payload(self, **overrides):
        payload = _payload()
        payload["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        payload["stages"][0]["location_req"] = {
            "layer": "instance",
            "archetype": "forest_path",
            "anchor_key": None,
            "anchor_near": "capital_altoria",
            "xyz": None,
            "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
        }
        payload["stages"][0]["npc_req"] = [
            {
                "role": "bandit",
                "tier": "bandit",
                "disposition": None,
                "display_name": "黑鬍",
                "age": 35,
                "apparent_age": 35,
                "portrait": {"stable_key": "forest_bandit_chief"},
            }
        ]
        payload.update(overrides)
        return payload

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_valid_named_occupant_with_ages_passes_validation(self):
        payload = self._instance_bound_payload()
        for validator_fn in scenario_director._VALIDATORS.values():
            self.assertEqual(validator_fn(payload), [], validator_fn.__name__)

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_elven_tier_named_occupant_passes_within_the_elf_band(self):
        payload = self._instance_bound_payload()
        payload["stages"][0]["npc_req"][0]["tier"] = "elven_civilian"
        payload["stages"][0]["npc_req"][0]["age"] = 300
        payload["stages"][0]["npc_req"][0]["apparent_age"] = 300
        for validator_fn in scenario_director._VALIDATORS.values():
            self.assertEqual(validator_fn(payload), [], validator_fn.__name__)

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_unpaired_underage_or_non_integer_declarations_reject_and_retry(self):
        def apply_bad(bad, fields):
            entry = bad["stages"][0]["npc_req"][0]
            if fields == "age_only":
                del entry["apparent_age"]
            elif fields == "apparent_only":
                del entry["age"]
            else:
                entry.update(fields)

        bad_cases = [
            "age_only",
            "apparent_only",
            {"age": 17, "apparent_age": 17},
            {"age": True, "apparent_age": 35},
            {"age": 35, "apparent_age": 30.5},
            {"age": None, "apparent_age": 35},
            {"age": 120, "apparent_age": 120},
        ]
        for fields in bad_cases:
            with self.subTest(fields=fields):
                client = FakeLLMClient()
                bad = self._instance_bound_payload()
                apply_bad(bad, fields)
                client.add_response(
                    lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False)
                )
                client.add_response(
                    lambda d: len(d.messages) == 3,
                    json.dumps(_payload(), ensure_ascii=False),
                )
                with override_settings(LLM_PROFILES=_raw()):
                    d = generate_quest_blueprint(client, context=_context())
                    result = await_result(d)
                self.assertEqual(result, _blueprint())
                self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_malformed_portrait_object_rejects_and_retries(self):
        bad_portraits = [
            "forest_bandit_chief",
            {"stable_key": "ok", "mode": "named"},
            {"stable_key": ""},
            {"stable_key": "a:b"},
        ]
        for portrait in bad_portraits:
            with self.subTest(portrait=portrait):
                client = FakeLLMClient()
                bad = self._instance_bound_payload()
                bad["stages"][0]["npc_req"][0]["portrait"] = portrait
                client.add_response(
                    lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False)
                )
                client.add_response(
                    lambda d: len(d.messages) == 3,
                    json.dumps(_payload(), ensure_ascii=False),
                )
                with override_settings(LLM_PROFILES=_raw()):
                    d = generate_quest_blueprint(client, context=_context())
                    result = await_result(d)
                self.assertEqual(result, _blueprint())
                self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    @covers_requirement("art-stable-key-contract::the-character-portrait-keyspace-reserves-the-digit-only-region-for-player-characters")
    def test_digit_only_portrait_stable_key_rejects_and_retries(self):
        client = FakeLLMClient()
        bad = self._instance_bound_payload()
        bad["stages"][0]["npc_req"][0]["portrait"] = {"stable_key": "7"}
        self.assertTrue(
            any(
                validator_fn(bad)
                for validator_fn in scenario_director._VALIDATORS.values()
            )
        )
        client.add_response(
            lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False)
        )
        client.add_response(
            lambda d: len(d.messages) == 3,
            json.dumps(_payload(), ensure_ascii=False),
        )
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, _blueprint())
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_overlong_display_name_rejects_and_retries(self):
        client = FakeLLMClient()
        bad = self._instance_bound_payload()
        bad["stages"][0]["npc_req"][0]["display_name"] = "字" * 65
        client.add_response(
            lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False)
        )
        client.add_response(
            lambda d: len(d.messages) == 3, json.dumps(_payload(), ensure_ascii=False)
        )
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, _blueprint())
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_conflicting_duplicate_key_rejects_and_retries(self):
        client = FakeLLMClient()
        bad = self._instance_bound_payload()
        bad["stages"][0]["npc_req"].append(
            {
                "role": "bandit",
                "tier": "bandit",
                "disposition": None,
                "display_name": "另一個人",
                "age": 40,
                "apparent_age": 40,
                "portrait": {"stable_key": "forest_bandit_chief"},
            }
        )
        client.add_response(
            lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False)
        )
        client.add_response(
            lambda d: len(d.messages) == 3, json.dumps(_payload(), ensure_ascii=False)
        )
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result, _blueprint())
        self.assertEqual(len(client.calls), 2)

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_field_less_entries_validate_unchanged(self):
        payload = self._instance_bound_payload()
        payload["stages"][0]["npc_req"][0] = {
            "role": "bandit",
            "tier": "bandit",
            "disposition": None,
        }
        for validator_fn in scenario_director._VALIDATORS.values():
            self.assertEqual(validator_fn(payload), [], validator_fn.__name__)


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


def _instance_payload():
    """A valid instance-bound payload (registers scene requirements)."""
    payload = _payload()
    payload["stages"][0]["objective"] = {
        "kind": "defeat",
        "quantity": 1,
        "monster_tier": None,
    }
    payload["stages"][0]["location_req"] = {
        "layer": "instance",
        "archetype": "forest_path",
        "anchor_key": None,
        "anchor_near": "capital_altoria",
        "xyz": None,
        "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
    }
    payload["stages"][0]["npc_req"] = [
        {"role": "bandit", "tier": "bandit", "disposition": None}
    ]
    return payload


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

        test_path = (
            pathlib.Path(scenario_director.__file__).resolve().parent
            / "tests"
            / "test_scenario_director.py"
        )
        source = test_path.read_text(encoding="utf-8")
        client_constructor = "OpenAICompatClient" + "("
        socket_import = "import so" + "cket"
        socket_from = "from so" + "cket"
        self.assertNotIn(client_constructor, source)
        self.assertNotIn(socket_import, source)
        self.assertNotIn(socket_from, source)


if __name__ == "__main__":
    unittest.main()
