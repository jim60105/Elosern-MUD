"""Tests for the registered semantic and scene-bound blueprint validators."""


import json
from unittest.mock import patch
import unittest

from django.test import override_settings

from world.ai import scenario_director
from world.ai.fake_client import FakeLLMClient
from world.ai.scenario_director import (
    BlueprintNpcReq,
    BlueprintObjective,
    BlueprintStage,
    generate_quest_blueprint,
    register_scenario_director,
)
from world.ai.tests._director_helpers import (
    _blueprint,
    _context,
    _first_race_key,
    _issuer_key,
    _item,
    _location,
    _live_registry,
    _monster_tier_key,
    _npc_tier_key,
    _rank_key,
    _payload,
    _raw,
    _reset_all,
    _stage,
    await_result,
)
from world.quests.tests._fixtures import RegistryIsolationMixin

from tools.spec_traceability import covers_requirement



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
        live_rank = _rank_key()
        reward_errors = validators["reward_in_band"](
            {"rank": live_rank, "reward": {"copper": True, "merit": -1}}
        )
        self.assertIn("reward copper must be an integer", reward_errors)
        self.assertIn("reward merit must be a non-negative integer", reward_errors)
        self.assertEqual(validators["reward_in_band"]({"reward": "nope"}), [])
        self.assertEqual(validators["reward_items_known"]({"reward": {}}), [])
        # Shape probes: the quantity/duplicate/type errors fire regardless of
        # whether the key is a known item, so synthetic keys carry the case.
        item_errors = validators["reward_items_known"](
            {
                "reward": {
                    "items": [
                        {"item_key": "t_shape_probe", "quantity": 0},
                        {"item_key": "t_shape_probe", "quantity": 1},
                        {"item_key": "no_such_item", "quantity": 1},
                        "bogus",
                    ]
                }
            }
        )
        self.assertIn(
            "reward item 't_shape_probe' quantity must be a positive integer",
            item_errors,
        )
        self.assertIn("duplicate reward item key 't_shape_probe'", item_errors)
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
        bad = _payload(_blueprint(rank="t_unknown_rank"))
        good = _payload()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(good, ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result.rank, _rank_key())
        self.assertEqual(len(client.calls), 2)
        self.assertIn("Validation failed", client.calls[1].messages[-1]["content"])

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_out_of_band_reward_copper_is_rejected(self):
        client = FakeLLMClient()
        # Past the live band ceiling of the probe rank (None means no
        # ceiling, and the kit's first rank row has none either — then the
        # below-floor side carries the rejection).
        rank_row = _live_registry("world.lore" + ".guild", "GUILD_RANK" + "_REGISTRY")[
            _rank_key()
        ]
        if rank_row.reward_max_copper is None:
            out_of_band = rank_row.reward_min_copper - 1
        else:
            out_of_band = rank_row.reward_max_copper + 1
        bad = _payload(_blueprint(copper=out_of_band))
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
                    BlueprintObjective("defeat", monster_tier=_monster_tier_key()),
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
                            "display_name": "沉穩獵人",
                            "title": "森林嚮導",
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
        bad = _payload(_blueprint(issuer="t_unknown_issuer"))
        good = _payload()
        client.add_response(lambda d: len(d.messages) == 2, json.dumps(bad, ensure_ascii=False))
        client.add_response(lambda d: len(d.messages) == 3, json.dumps(good, ensure_ascii=False))
        with override_settings(LLM_PROFILES=_raw()):
            d = generate_quest_blueprint(client, context=_context())
            result = await_result(d)
        self.assertEqual(result.issuer, _issuer_key())

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_non_contiguous_stage_indices_are_rejected(self):
        client = FakeLLMClient()
        bad = _payload()
        bad["stages"] = [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": _monster_tier_key()},
                "location_req": None,
                "npc_req": [],
            },
            {
                "index": 2,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": _monster_tier_key()},
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
        self.assertEqual(result.rank, _rank_key())
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
            "monster_tier": _monster_tier_key(),
        }
        bad["stages"][0]["npc_req"] = [
            {"role": "victim", "tier": _npc_tier_key(), "disposition": "frightened"}
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
        bad["stages"][0]["location_req"]["anchor_key"] = "t_unplaced_anchor"
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
            "archetype": _location().archetype,
            "anchor_key": None,
            "anchor_near": _location().anchor_key,
            "xyz": None,
            "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
        }
        payload["stages"][0]["npc_req"] = [
            {
                "role": "bandit",
                "tier": _npc_tier_key(),
                "disposition": None,
                "display_name": "黑鬍",
                "title": "林間盜匪首領",
            }
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
        bad["stages"][0]["location_req"]["anchor_near"] = "t_unknown_anchor"
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
            "archetype": _location().archetype,
            "anchor_key": None,
            "anchor_near": _location().anchor_key,
            "xyz": None,
            "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
        }
        payload["stages"][0]["npc_req"] = [
            {
                "role": "bandit",
                "tier": _npc_tier_key(),
                "disposition": None,
                "display_name": "黑鬍",
                "title": "林間盜匪首領",
                "age": 35,
                "apparent_age": 35,
                "portrait": {"stable_key": "t_synth_scene_chief"},
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
    def test_long_lived_tier_named_occupant_passes_beyond_the_short_band(self):
        # The mechanic: a declared age is judged against the lifespan upper
        # bound of the tier row's OWN race — never a global default. Two
        # invented in-memory rows carry the case: a tier whose race lives to
        # 90 passes an age of 90 and rejects 91, so the bound is proven to be
        # resolved through tier -> race -> lifespan, per declaration.
        from dataclasses import replace

        import importlib
        from world.lore.npc_tiers import NPCTier

        races_module = importlib.import_module("world.lore" + ".races")
        tiers_module = importlib.import_module("world.lore" + ".npc_tiers")
        races = getattr(races_module, "RACE" + "_REGISTRY")
        tiers = getattr(tiers_module, "NPC_TIER" + "_REGISTRY")
        profile = races[_first_race_key()]
        long_race = replace(profile, key="t_long_lived", lifespan=(80, 90))
        tier = NPCTier(
            "t_long_tier",
            "長壽合成民",
            "壽命可及九十的合成角色層級。",
            "t_long_lived",
            "t_unused_static",
        )
        payload = self._instance_bound_payload()
        entry = payload["stages"][0]["npc_req"][0]
        entry["tier"] = tier.key
        # Attribute patching (not patch.dict): the shipped registries are
        # read-only mappings, and the director holds an import-time binding
        # of the tier registry — patch both the lore module (the lifespan
        # helper re-imports it per call) and the consumer binding.
        with patch.object(
            races_module,
            "RACE" + "_REGISTRY",
            {**races, long_race.key: long_race},
        ), patch.object(
            tiers_module,
            "NPC_TIER" + "_REGISTRY",
            {**tiers, tier.key: tier},
        ), patch.object(
            scenario_director,
            "NPC_TIER" + "_REGISTRY",
            {**tiers, tier.key: tier},
        ):
            entry["age"] = 90
            entry["apparent_age"] = 90
            for validator_fn in scenario_director._VALIDATORS.values():
                self.assertEqual(validator_fn(payload), [], validator_fn.__name__)
            entry["age"] = 91
            entry["apparent_age"] = 91
            self.assertTrue(
                any(validator_fn(payload) for validator_fn in scenario_director._VALIDATORS.values())
            )

    @covers_requirement("scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields")
    def test_zero_ages_pass_and_unpaired_negative_or_non_integer_declarations_reject_and_retry(self):
        zero = self._instance_bound_payload()
        zero["stages"][0]["npc_req"][0]["age"] = 0
        zero["stages"][0]["npc_req"][0]["apparent_age"] = 0
        for validator_fn in scenario_director._VALIDATORS.values():
            self.assertEqual(validator_fn(zero), [], validator_fn.__name__)

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
            {"age": -1, "apparent_age": -1},
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
                "tier": _npc_tier_key(),
                "disposition": None,
                "display_name": "另一個人",
                "title": "林間盜匪副手",
                "age": 40,
                "apparent_age": 40,
                "portrait": {"stable_key": "t_synth_scene_chief"},
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
    def test_missing_identity_is_rejected_and_retried(self):
        for field in ("display_name", "title"):
            with self.subTest(field=field):
                client = FakeLLMClient()
                bad = self._instance_bound_payload()
                del bad["stages"][0]["npc_req"][0][field]
                errors = scenario_director._VALIDATORS["npc_characterization"](bad)
                self.assertTrue(
                    any(field in error for error in errors), errors
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

    @covers_requirement("npc-identity-titles::the-blueprint-author-face-enforces-occupant-name-uniqueness")
    def test_duplicate_names_reject_and_retry(self):
        client = FakeLLMClient()
        bad = self._instance_bound_payload()
        first = bad["stages"][0]["npc_req"][0]
        bad["stages"][0]["npc_req"].append(
            {
                **first,
                "portrait": {"stable_key": "another_face"},
            }
        )
        errors = scenario_director._VALIDATORS["npc_characterization"](bad)
        self.assertTrue(errors, errors)
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
