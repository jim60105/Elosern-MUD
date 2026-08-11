"""Tests for the deterministic quest compile boundary (scenario-director).

Covers ``compile_quest_blueprint`` (re-validation against the lore registries,
the pinned per-stage mapping contract, content-digest keys, raw-dict rejection),
``register_generated_quest`` (all-or-nothing publication with preflight and
rollback), the shared payload contract with the ``scenario_director`` guardrail,
and an offline end-to-end loop through the full deterministic quest lifecycle
with no LLM and no generative state mutation.
"""

import json
from unittest.mock import patch
import unittest

from django.test import override_settings

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.ai.fake_client import FakeLLMClient
from world.ai.scenario_director import (
    BlueprintLocation,
    BlueprintObjective,
    BlueprintPortrait,
    BlueprintStage,
    QuestBlueprint,
    generate_quest_blueprint,
    register_scenario_director,
)
from world.ai.profiles import default_profiles
from world.quests.compile import (
    CompiledQuest,
    QuestCompileError,
    SCENE_REQUIREMENT_REGISTRY,
    compile_quest_blueprint,
    register_generated_quest,
    scene_requirements_for,
)
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    DestinationKind,
    ObjectiveKind,
    QuestDefinition,
    QuestDefinitionError,
    QuestStage,
    RoomLocator,
    register_quest_definition,
    validate_definition,
)
from world.quests.runtime import QuestState, accept_quest, read_records
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.action import (
    ActionRequest,
    ActionResolver,
)
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
)
from world.rules.guild import register_adventurer, turn_in_quest
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    QuestReward,
)
from world.rules.surfaces import read_counter_trait

from tools.spec_traceability import covers_requirement


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _quest_type(quest_type="討伐"):
    return quest_type


def _defeat_payload(**overrides):
    payload = {
        "name": "討伐低階魔物",
        "quest_type": "討伐",
        "rank": "F",
        "issuer": "guild_branch_altoria",
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": "low"},
                "location_req": {
                    "layer": "anchor",
                    "archetype": "forest_path",
                    "anchor_key": "capital_altoria",
                    "anchor_near": None,
                    "xyz": None,
                    "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
                },
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [{"item_key": "healing_potion", "quantity": 1}], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload


def _acquire_payload(**overrides):
    payload = {
        "name": "採集治療藥水",
        "quest_type": "採集",
        "rank": "F",
        "issuer": "guild_branch_altoria",
        "stages": [
            {
                "index": 0,
                "objective": {
                    "kind": "acquire",
                    "quantity": 1,
                    "item_key": "healing_potion",
                },
                "location_req": None,
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": 72, "conditions": []},
    }
    payload.update(overrides)
    return payload


def _characterized_payload(**overrides):
    payload = _defeat_payload()
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


class CompileRegistryIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()


class CompileQuestBlueprintTests(CompileRegistryIsolation, unittest.TestCase):
    @covers_requirement("quest-blueprint::questdefinition-is-the-immutable-deterministic-input-to-quest-runtime")
    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_valid_payload_compiles_to_a_registrable_definition(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        self.assertIsInstance(compiled, CompiledQuest)
        validate_definition(compiled.definition)
        self.assertEqual(compiled.definition.quest_type.value, "討伐")
        self.assertEqual(compiled.definition.rank, "F")
        self.assertEqual(compiled.definition.stages[0].objective.kind, ObjectiveKind.DEFEAT)
        self.assertEqual(compiled.definition.stages[0].objective.monster_tier, "low")
        self.assertEqual(compiled.reward.copper, 50)
        self.assertEqual(compiled.reward.items[0].item_key, "healing_potion")
        self.assertEqual(compiled.issuer_branch_key, "guild_branch_altoria")

    @covers_requirement("scenario-director::the-canonical-payload-contract-is-versioned-and-shared-by-both-boundaries")
    def test_every_stage_kind_has_one_deterministic_mapping(self):
        reach = compile_quest_blueprint(
            {
                "name": "探查王都廣場",
                "quest_type": "探索",
                "rank": "F",
                "issuer": "guild_branch_altoria",
                "stages": [
                    {
                        "index": 0,
                        "objective": {"kind": "reach_location", "quantity": 1},
                        "location_req": {
                            "layer": "anchor",
                            "archetype": "city_street",
                            "anchor_key": "capital_altoria",
                            "anchor_near": None,
                            "xyz": None,
                            "scene_sentence": "聖潔王都的中央廣場，人聲鼎沸。",
                        },
                        "npc_req": [],
                    }
                ],
                "reward": {"copper": 50, "items": [], "merit": 25},
                "failure": {"deadline_hours": 72, "conditions": []},
            }
        )
        stage = reach.definition.stages[0]
        self.assertEqual(stage.objective.kind, ObjectiveKind.REACH)
        self.assertEqual(
            stage.objective.destination.kind, DestinationKind.ANCHOR
        )
        self.assertEqual(stage.objective.destination.anchor_key, "capital_altoria")

        acquire = compile_quest_blueprint(_acquire_payload())
        acquire_stage = acquire.definition.stages[0]
        self.assertEqual(acquire_stage.objective.kind, ObjectiveKind.ACQUIRE)
        self.assertEqual(acquire_stage.objective.item_key, "healing_potion")
        self.assertEqual(acquire_stage.objective.quantity, 1)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_defeat_bound_variant_uses_npc_reqs(self):
        payload = _defeat_payload()
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
            {"role": "victim", "tier": "civilian", "disposition": "frightened"}
        ]
        compiled = compile_quest_blueprint(payload)
        stage = compiled.definition.stages[0]
        self.assertEqual(stage.objective.kind, ObjectiveKind.DEFEAT)
        self.assertTrue(stage.objective.requires_bound_targets)
        self.assertIsNone(stage.objective.monster_tier)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_out_of_band_reward_raises_with_no_registry_change(self):
        bad = _defeat_payload()
        bad["reward"]["copper"] = 10_000
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, dict(self._registry_items))

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_unknown_item_key_raises_with_no_registry_change(self):
        bad = _defeat_payload()
        bad["reward"]["items"] = [{"item_key": "bogus_potion", "quantity": 1}]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, dict(self._registry_items))

    @covers_requirement("scenario-director::the-canonical-payload-contract-is-versioned-and-shared-by-both-boundaries")
    def test_wilderness_layer_raises_a_named_error(self):
        bad = _defeat_payload()
        bad["stages"][0]["location_req"]["layer"] = "wilderness"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    @covers_requirement("scenario-director::the-canonical-payload-contract-is-versioned-and-shared-by-both-boundaries")
    def test_non_empty_conditions_raise_a_named_error(self):
        bad = _defeat_payload()
        bad["failure"]["conditions"] = ["deadline_expired"]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_equal_content_yields_equal_keys(self):
        first = compile_quest_blueprint(_defeat_payload())
        second = compile_quest_blueprint(_defeat_payload())
        self.assertEqual(first.definition.key, second.definition.key)
        self.assertTrue(first.definition.key.startswith("ai_"))

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_every_guardrail_constraint_is_rechecked_unvalidated(self):
        bad = _defeat_payload()
        bad["rank"] = "Z"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["location_req"]["archetype"] = "bogus"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["issuer"] = "guild_branch_bogus"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["failure"]["deadline_hours"] = -1
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    def test_compiler_revalidates_name_string_contract(self):
        for name in ("", "not chinese", "x" * 81, "{actor} placeholder"):
            bad = _defeat_payload()
            bad["name"] = name
            with self.assertRaises(QuestCompileError):
                compile_quest_blueprint(bad)

    def test_compiler_revalidates_scene_sentence_string_contract(self):
        for sentence in ("not chinese", "x" * 501, "{target} placeholder"):
            bad = _defeat_payload()
            bad["stages"][0]["location_req"]["scene_sentence"] = sentence
            with self.assertRaises(QuestCompileError):
                compile_quest_blueprint(bad)

    def test_compiler_rejects_conditions_none_or_missing(self):
        bad = _defeat_payload()
        bad["failure"]["conditions"] = None
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        del bad["failure"]["conditions"]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    def test_compiler_rejects_missing_npc_req(self):
        bad = _defeat_payload()
        del bad["stages"][0]["npc_req"]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    def test_defeat_without_selector_is_rejected_by_compiler(self):
        bad = _defeat_payload()
        bad["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        bad["stages"][0]["npc_req"] = []
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    def test_defeat_with_both_selectors_is_rejected_by_compiler(self):
        bad = _defeat_payload()
        bad["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": "low",
        }
        bad["stages"][0]["npc_req"] = [
            {"role": "victim", "tier": "civilian", "disposition": "frightened"}
        ]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    def test_acquire_without_item_key_is_rejected_by_compiler(self):
        bad = _defeat_payload()
        bad["quest_type"] = "採集"
        bad["stages"][0]["objective"] = {"kind": "acquire", "quantity": 1, "item_key": None}
        bad["stages"][0]["location_req"] = None
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    def test_reach_without_destination_is_rejected_by_compiler(self):
        bad = _defeat_payload()
        bad["quest_type"] = "探索"
        bad["stages"][0]["objective"] = {"kind": "reach_location", "quantity": 1}
        bad["stages"][0]["location_req"] = None
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    def test_unplaced_anchor_is_rejected_by_compiler(self):
        bad = _defeat_payload()
        bad["stages"][0]["location_req"]["anchor_key"] = "capital_grandia"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    def test_compiler_rejects_malformed_reward_shapes(self):
        bad = _defeat_payload()
        bad["reward"] = "lots"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["reward"]["copper"] = True
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["reward"]["merit"] = -1
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["reward"]["items"] = "healing_potion"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["reward"]["items"] = ["healing_potion"]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["reward"]["items"] = [{"item_key": "", "quantity": 1}]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["reward"]["items"] = [{"item_key": "no_such_item", "quantity": 1}]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["reward"]["items"] = [{"item_key": "healing_potion", "quantity": 0}]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["reward"]["items"] = [
            {"item_key": "healing_potion", "quantity": 1},
            {"item_key": "healing_potion", "quantity": 1},
        ]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    def test_compiler_rejects_malformed_location_shapes(self):
        bad = _defeat_payload()
        bad["stages"][0]["location_req"]["layer"] = "wilderness"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["location_req"] = {"layer": "grid"}
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["location_req"] = {
            "layer": "grid",
            "xyz": ["a", 1, "capital_altoria"],
        }
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["location_req"] = {"layer": "grid", "xyz": [1, 2, "no_such_map"]}
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["location_req"] = {
            "layer": "instance",
            "anchor_key": "capital_altoria",
            "xyz": None,
        }
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["location_req"] = {"layer": "anchor", "anchor_key": None}
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    def test_compiler_rejects_malformed_objective_and_npc_shapes(self):
        bad = _defeat_payload()
        bad["stages"][0]["objective"] = {"kind": "explode", "quantity": 1}
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["objective"]["monster_tier"] = "bogus"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["npc_req"] = "victim"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["npc_req"] = [{"role": "", "tier": "civilian"}]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["npc_req"] = [{"role": "victim", "tier": "bogus"}]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["stages"][0]["npc_req"] = [{"role": "victim", "tier": "civilian", "disposition": 5}]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

        bad = _defeat_payload()
        bad["quest_type"] = "採集"
        bad["stages"][0]["objective"] = {"kind": "acquire", "quantity": 1, "item_key": "bogus"}
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_raw_ai_shaped_dict_is_still_rejected_by_the_runtime_registry(self):
        with self.assertRaises(QuestDefinitionError):
            register_quest_definition(_defeat_payload())
        self.assertEqual(QUEST_DEFINITION_REGISTRY, dict(self._registry_items))


class RegisterGeneratedQuestTests(CompileRegistryIsolation, unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Pure-unit class: the durable store is a database Script, so the
        # store boundary is patched to keep every test here DB-free.
        patcher = patch(
            "world.quests.compile.append_generated_quest_payload", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _compiled(self):
        return compile_quest_blueprint(_defeat_payload())

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_double_registration_is_idempotent(self):
        compiled = self._compiled()
        register_generated_quest(compiled)
        register_generated_quest(compiled)
        self.assertEqual(
            len(QUEST_DEFINITION_REGISTRY),
            len(self._registry_items) + 1,
        )
        self.assertEqual(
            len(GUILD_OFFER_REGISTRY),
            len(self._offer_items) + 1,
        )

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_conflicting_offer_rolls_back_the_definition_write(self):
        first = compile_quest_blueprint(
            {
                **_defeat_payload(),
                "reward": {"copper": 50, "items": [], "merit": 25},
            }
        )
        register_generated_quest(first)
        before_definition = dict(QUEST_DEFINITION_REGISTRY)
        before_offer = dict(GUILD_OFFER_REGISTRY)

        conflicting = compile_quest_blueprint(
            {
                **_defeat_payload(),
                "reward": {"copper": 60, "items": [], "merit": 25},
            }
        )
        with self.assertRaises(QuestCompileError):
            register_generated_quest(conflicting)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before_definition)
        self.assertEqual(GUILD_OFFER_REGISTRY, before_offer)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_definition_new_plus_offer_conflicting_leaves_both_registries_unchanged(self):
        # A conflicting offer already exists for the identity of a definition
        # that is not yet registered (possible through direct registry writes).
        # The preflight must reject before writing the definition, so neither
        # registry changes.
        compiled = self._compiled()
        existing_offer = GuildQuestOffer(
            definition_key=compiled.definition.key,
            issuer_branch_key="guild_branch_altoria",
            reward=QuestReward(
                copper=60,
                items=(),
                merit=25,
            ),
        )
        GUILD_OFFER_REGISTRY[(compiled.definition.key, "guild_branch_altoria")] = (
            existing_offer
        )
        before_definition = dict(QUEST_DEFINITION_REGISTRY)
        before_offer = dict(GUILD_OFFER_REGISTRY)
        with self.assertRaises(QuestCompileError):
            register_generated_quest(compiled)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before_definition)
        self.assertEqual(GUILD_OFFER_REGISTRY, before_offer)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    @covers_requirement("quest-blueprint::escort-quests-require-a-bound-protected-entity-path")
    def test_register_generated_quest_refuses_escort_stages(self):
        from ._fixtures import anchor_locator, escort, quest
        from world.quests.definitions import QuestType

        definition = quest(
            "escort_publication_guard",
            quest_type=QuestType.ESCORT,
            stages=(QuestStage(0, escort(anchor_locator())),),
        )
        compiled = CompiledQuest(
            definition=definition,
            reward=QuestReward(copper=50, items=(), merit=25),
            issuer_branch_key="guild_branch_altoria",
            stage_requirements=(),
        )
        with self.assertRaisesRegex(
            QuestCompileError,
            "ESCORT stages cannot be published until a protected-entity "
            "binding flow exists",
        ):
            register_generated_quest(compiled)
        self.assertNotIn(definition.key, QUEST_DEFINITION_REGISTRY)
        self.assertNotIn(
            (definition.key, "guild_branch_altoria"), GUILD_OFFER_REGISTRY
        )


class SceneBoundCompileTests(CompileRegistryIsolation, unittest.TestCase):
    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_occupant_stage_at_anchor_is_rejected_by_the_compiler(self):
        payload = _defeat_payload()
        payload["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        payload["stages"][0]["npc_req"] = [
            {"role": "victim", "tier": "civilian", "disposition": None}
        ]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(payload)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_occupant_stage_at_grid_is_rejected_by_the_compiler(self):
        payload = _defeat_payload()
        payload["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        payload["stages"][0]["location_req"] = {
            "layer": "grid",
            "archetype": "forest_path",
            "anchor_key": None,
            "anchor_near": None,
            "xyz": [2, 2, "capital_altoria"],
            "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
        }
        payload["stages"][0]["npc_req"] = [
            {"role": "victim", "tier": "civilian", "disposition": None}
        ]
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(payload)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_escort_stage_at_instance_is_rejected_by_the_compiler(self):
        payload = _defeat_payload()
        payload["quest_type"] = "護衛"
        payload["stages"][0]["objective"] = {"kind": "escort", "quantity": 1}
        payload["stages"][0]["location_req"] = {
            "layer": "instance",
            "archetype": "forest_path",
            "anchor_key": None,
            "anchor_near": "capital_altoria",
            "xyz": None,
            "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
        }
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(payload)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    @covers_requirement("quest-blueprint::escort-quests-require-a-bound-protected-entity-path")
    def test_escort_stage_at_anchor_is_rejected_by_the_compiler(self):
        payload = _defeat_payload()
        payload["quest_type"] = "護衛"
        payload["stages"][0]["objective"] = {"kind": "escort", "quantity": 1}
        payload["stages"][0]["npc_req"] = []
        with self.assertRaisesRegex(
            QuestCompileError,
            "ESCORT objective, which cannot be published until a "
            "protected-entity binding flow exists",
        ):
            compile_quest_blueprint(payload)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    @covers_requirement("quest-blueprint::reach-and-escort-objectives-accept-only-quantity-one")
    def test_escort_stage_with_quantity_two_is_rejected_by_the_compiler(self):
        payload = _defeat_payload()
        payload["stages"][0]["objective"] = {"kind": "reach_location", "quantity": 2}
        with self.assertRaisesRegex(
            QuestCompileError, "reach objective quantity must be exactly 1"
        ):
            compile_quest_blueprint(payload)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_bound_defeat_quantity_exceeding_npc_reqs_is_rejected(self):
        payload = _defeat_payload()
        payload["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 2,
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
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(payload)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_unknown_anchor_near_is_rejected_by_the_compiler(self):
        payload = _defeat_payload()
        payload["stages"][0]["location_req"]["anchor_near"] = "capital_grandia"
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(payload)

    @covers_requirement("scenario-director::scene-bound-proposal-stages-are-validated-before-publication")
    def test_unvalidated_scene_bound_violation_is_rejected_deterministically(self):
        from world.ai.scenario_director import _VALIDATORS

        payload = _defeat_payload()
        payload["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        payload["stages"][0]["npc_req"] = [
            {"role": "bandit", "tier": "bandit", "disposition": None}
        ]
        guardrail_errors = []
        for validator in _VALIDATORS.values():
            guardrail_errors.extend(validator(payload))
        self.assertTrue(guardrail_errors, "guardrail must reject the same payload")
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(payload)


class SceneRequirementRegistryTests(CompileRegistryIsolation, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._requirements_items = list(SCENE_REQUIREMENT_REGISTRY.items())
        # Pure-unit class: the durable store is a database Script, so the
        # store boundary is patched to keep every test here DB-free.
        patcher = patch(
            "world.quests.compile.append_generated_quest_payload", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        SCENE_REQUIREMENT_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.update(self._requirements_items)
        super().tearDown()

    def _bound_compiled(self):
        payload = _defeat_payload()
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
        return compile_quest_blueprint(payload)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_scene_requirements_are_registered_with_the_publication(self):
        compiled = self._bound_compiled()
        register_generated_quest(compiled)
        requirements = scene_requirements_for(compiled.definition.key)
        self.assertEqual(len(requirements), 1)
        self.assertEqual(requirements[0].index, 0)
        self.assertEqual(requirements[0].npc_reqs, (("bandit", "bandit", None),))
        self.assertEqual(compiled.stage_requirements, requirements)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_double_registration_keeps_one_requirement_entry(self):
        compiled = self._bound_compiled()
        register_generated_quest(compiled)
        before = scene_requirements_for(compiled.definition.key)
        register_generated_quest(compiled)
        after = scene_requirements_for(compiled.definition.key)
        self.assertEqual(len(before), 1)
        self.assertEqual(after, before)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_two_blueprints_differing_only_in_scenes_compile_to_different_keys(self):
        first = self._bound_compiled()
        second_payload = _defeat_payload()
        second_payload["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        second_payload["stages"][0]["location_req"] = {
            "layer": "instance",
            "archetype": "forest_path",
            "anchor_key": None,
            "anchor_near": "capital_altoria",
            "xyz": None,
            "scene_sentence": "另一段不同的場景描述。",
        }
        second_payload["stages"][0]["npc_req"] = [
            {"role": "bandit", "tier": "bandit", "disposition": None}
        ]
        second = compile_quest_blueprint(second_payload)
        self.assertNotEqual(first.definition.key, second.definition.key)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_conflicting_offer_rollback_leaves_no_requirement_entry(self):
        compiled = self._bound_compiled()
        existing_offer = GuildQuestOffer(
            definition_key=compiled.definition.key,
            issuer_branch_key="guild_branch_altoria",
            reward=QuestReward(copper=60, items=(), merit=25),
        )
        GUILD_OFFER_REGISTRY[(compiled.definition.key, "guild_branch_altoria")] = (
            existing_offer
        )
        before_definition = dict(QUEST_DEFINITION_REGISTRY)
        before_offer = dict(GUILD_OFFER_REGISTRY)
        with self.assertRaises(QuestCompileError):
            register_generated_quest(compiled)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before_definition)
        self.assertEqual(GUILD_OFFER_REGISTRY, before_offer)
        self.assertNotIn(compiled.definition.key, SCENE_REQUIREMENT_REGISTRY)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_hand_written_definition_reads_back_empty_requirements(self):
        from world.quests.catalog import INTRODUCTORY_HUNT

        register_quest_definition(INTRODUCTORY_HUNT)
        self.assertEqual(scene_requirements_for(INTRODUCTORY_HUNT.key), ())
        self.assertNotIn(INTRODUCTORY_HUNT.key, SCENE_REQUIREMENT_REGISTRY)


class CharacterizationCompileTests(CompileRegistryIsolation, unittest.TestCase):
    @covers_requirement("blueprint-portrait-policy::the-compile-boundary-carries-the-characterization-fields")
    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_compiled_requirement_preserves_the_optional_fields(self):
        compiled = compile_quest_blueprint(_characterized_payload())
        requirement = compiled.stage_requirements[0]
        characterization = requirement.characterizations[0]
        self.assertEqual(characterization.display_name, "黑鬍")
        self.assertEqual(characterization.age, 35)
        self.assertEqual(characterization.apparent_age, 35)
        self.assertEqual(characterization.portrait_stable_key, "forest_bandit_chief")

    @covers_requirement("blueprint-portrait-policy::the-compile-boundary-carries-the-characterization-fields")
    def test_field_less_blueprint_compiles_to_unchanged_shape(self):
        field_less = compile_quest_blueprint(_defeat_payload())
        characterized = compile_quest_blueprint(_characterized_payload())
        self.assertEqual(field_less.stage_requirements[0].npc_reqs, ())
        self.assertEqual(field_less.stage_requirements[0].characterizations, ())

    @covers_requirement("blueprint-portrait-policy::the-compile-boundary-carries-the-characterization-fields")
    def test_characterization_differences_change_the_generated_key(self):
        base = _characterized_payload()
        first = compile_quest_blueprint(base)
        changed = json.loads(json.dumps(base))
        changed["stages"][0]["npc_req"][0]["display_name"] = "另一個人"
        second = compile_quest_blueprint(changed)
        self.assertNotEqual(first.definition.key, second.definition.key)

    @covers_requirement("blueprint-portrait-policy::the-compile-boundary-carries-the-characterization-fields")
    @covers_requirement("blueprint-portrait-policy::the-shared-bound-helper-is-the-single-validation-rule-source-for-both-layers")
    def test_malformed_characterization_rejects_before_registration(self):
        def unpaired(entry):
            del entry["apparent_age"]

        def underage(entry):
            entry.update(age=17, apparent_age=17)

        def boolean(entry):
            entry.update(age=True, apparent_age=35)

        def out_of_band(entry):
            entry.update(age=120, apparent_age=120)

        def empty_key(entry):
            entry.update(portrait={"stable_key": ""})

        for mutate in (unpaired, underage, boolean, out_of_band, empty_key):
            with self.subTest(mutate=mutate.__name__):
                bad = _characterized_payload()
                mutate(bad["stages"][0]["npc_req"][0])
                with self.assertRaises(QuestCompileError):
                    compile_quest_blueprint(bad)

    @covers_requirement("blueprint-portrait-policy::the-shared-bound-helper-is-the-single-validation-rule-source-for-both-layers")
    def test_conflicting_duplicate_stable_key_rejects_at_compile(self):
        bad = _characterized_payload()
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
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(bad)

    @covers_requirement("blueprint-portrait-policy::the-compile-boundary-carries-the-characterization-fields")
    def test_elven_tier_characterization_validates_against_the_elf_band(self):
        payload = _characterized_payload()
        payload["stages"][0]["npc_req"][0]["tier"] = "elven_civilian"
        payload["stages"][0]["npc_req"][0]["age"] = 300
        payload["stages"][0]["npc_req"][0]["apparent_age"] = 300
        compiled = compile_quest_blueprint(payload)
        self.assertEqual(
            compiled.stage_requirements[0].characterizations[0].age, 300
        )

    @covers_requirement("blueprint-portrait-policy::the-compile-boundary-carries-the-characterization-fields")
    def test_characterizations_must_stay_aligned_with_npc_reqs(self):
        from world.quests.compile import (
            StageNpcCharacterization,
            StageSpawnRequirement,
        )

        with self.assertRaises(ValueError):
            StageSpawnRequirement(
                index=0,
                objective_kind=ObjectiveKind.DEFEAT,
                location=RoomLocator(DestinationKind.BOUND_INSTANCE),
                archetype="forest_path",
                anchor_near="capital_altoria",
                scene_sentence="王都近郊的林間小徑，樹影搖曳。",
                npc_reqs=(("bandit", "bandit", None),),
                characterizations=(
                    StageNpcCharacterization(),
                    StageNpcCharacterization(),
                ),
            )
        StageSpawnRequirement(
            index=0,
            objective_kind=ObjectiveKind.DEFEAT,
            location=RoomLocator(DestinationKind.BOUND_INSTANCE),
            archetype="forest_path",
            anchor_near="capital_altoria",
            scene_sentence="王都近郊的林間小徑，樹影搖曳。",
            npc_reqs=(("bandit", "bandit", None),),
            characterizations=(StageNpcCharacterization(),),
        )


class SharedPayloadContractTests(CompileRegistryIsolation, unittest.TestCase):
    @covers_requirement("scenario-director::the-canonical-payload-contract-is-versioned-and-shared-by-both-boundaries")
    def test_guardrail_valid_payload_compiles_without_contract_rejection(self):
        from jsonschema import Draft7Validator

        from world.ai.director_templates import QUEST_TEMPLATE_POOL
        from world.ai.scenario_director import (
            SCENARIO_DIRECTOR_OUTPUT_SCHEMA,
            _VALIDATORS,
        )

        for entry in QUEST_TEMPLATE_POOL:
            with self.subTest(entry=entry.name):
                payload = entry.to_payload()
                validator = Draft7Validator(SCENARIO_DIRECTOR_OUTPUT_SCHEMA)
                self.assertEqual(
                    [error.message for error in validator.iter_errors(payload)], []
                )
                for validator_fn in _VALIDATORS.values():
                    self.assertEqual(validator_fn(payload), [])
                compiled = compile_quest_blueprint(payload)
                validate_definition(compiled.definition)


class OfflineDirectorEndToEndTests(CompileRegistryIsolation, EvenniaTest):
    """Offline loop through the template draw, compile, register, accept,
    fight, and turn-in with no LLM call and no generative state mutation."""

    def setUp(self):
        super().setUp()
        from world.quests.bootstrap import sync_quest_runtime

        sync_quest_runtime()
        register_scenario_director()
        self.hall = create_object(Room, key="offline-hall")
        self.staff = create_object(NPC, key="offline staff", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(
                self.staff,
                service_id="staff",
                branch_key="guild_branch_altoria",
            )
        )
        self.player = create_object(PlayerCharacter, key="offline-director-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.player.location = self.hall
        register_adventurer(self.player, self.staff)

    def _monster(self, key: str, hp: int = 1) -> Monster:
        monster = create_object(Monster, key=key, location=self.player.location)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp._data["current"] = hp
        return monster

    def _resolve_lethal(self, monster: Monster):
        field = Battlefield(
            {"party": frozenset({self.player.key}), "foes": frozenset({monster.key})},
            {self.player.key: self.player, monster.key: monster},
        )
        request = ActionRequest(
            self.player,
            "fire_ball",
            [monster],
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    @covers_requirement("quest-progress-tracking::change-15-exposes-a-deterministic-no-ai-completion-seam-for-phase-4")
    @covers_requirement("scenario-director::the-hand-written-template-pool-provides-offline-quest-generation")
    def test_offline_loop_completes_with_no_llm_and_no_generative_mutation(self):
        disabled = {layer: {"enabled": False} for layer in ("narrator", "npc_dialogue", "scenario_director", "scene_builder")}
        client = FakeLLMClient()
        context = {
            "requested_type": "討伐",
            "allowed_rank": "F",
            "issuer_branch": "guild_branch_altoria",
            "anchor": "capital_altoria",
        }
        with override_settings(LLM_PROFILES=_raw(**disabled)):
            d = generate_quest_blueprint(client, context=context)
            blueprint = await_result(d)
        self.assertIsInstance(blueprint, QuestBlueprint)
        self.assertEqual(len(client.calls), 0)

        compiled = compile_quest_blueprint(blueprint.to_payload())
        register_generated_quest(compiled)
        self.assertTrue(scene_requirements_for(compiled.definition.key))

        record = accept_quest(self.player, compiled.definition.key)
        self.assertIs(record.state, QuestState.IN_PROGRESS)
        from world.quests.binding import bind_stage_runtime

        from typeclasses.rooms import InstanceRoom

        room = create_object(InstanceRoom, key="offline-director-instance")
        monster = self._monster("offline-director-goblin")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            objective_targets=(monster,),
        )
        result = self._resolve_lethal(monster)
        self.assertEqual(result.outcome, "success")

        completed = [
            r
            for r in read_records(self.player)
            if r.definition_key == compiled.definition.key
            and r.state is QuestState.COMPLETED
        ]
        self.assertTrue(completed, "quest did not auto-complete offline")

        turn_in = turn_in_quest(self.player, self.staff, completed[0].quest_id)
        self.assertEqual(turn_in["copper"], compiled.reward.copper)
        self.assertEqual(turn_in["merit"], compiled.reward.merit)
        self.assertEqual(self.player.db.wallet, compiled.reward.copper)
        self.assertEqual(read_counter_trait(self.player, "guild_merit"), compiled.reward.merit)
        for item in compiled.reward.items:
            self.assertIn(item.item_key, self.player.db.inventory)


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


if __name__ == "__main__":
    unittest.main()
