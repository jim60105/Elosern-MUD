"""Deterministic quest-compile tests (CompileQuestBlueprintTests family).

Covers ``compile_quest_blueprint`` re-validation, the pinned per-stage mapping
contract, content-digest keys, raw-dict rejection, scene-bound proposal stage
validation, and characterization payload handling. Shared isolation and
payload helpers come from ``_compile_helpers``.
"""

import json
import unittest

from world.quests.compile import (
    CompiledQuest,
    QuestCompileError,
    compile_quest_blueprint,
)
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    DestinationKind,
    ObjectiveKind,
    QuestDefinitionError,
    RoomLocator,
    register_quest_definition,
    validate_definition,
)
from world.quests.tests._compile_helpers import (
    CompileRegistryIsolation,
    _acquire_payload,
    _characterized_payload,
    _defeat_payload,
)

from tools.spec_traceability import covers_requirement

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
            {
                "role": "victim",
                "tier": "civilian",
                "disposition": "frightened",
                "display_name": "受驚旅人",
                "title": "邊境商隊腳伕",
            }
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

    @covers_requirement("blueprint-portrait-policy::the-blueprint-lifecycle-preserves-the-characterization-fields")
    def test_title_only_difference_changes_the_generated_key(self):
        base = _characterized_payload()
        first = compile_quest_blueprint(base)
        changed = json.loads(json.dumps(base))
        changed["stages"][0]["npc_req"][0]["title"] = "另一段頭銜"
        second = compile_quest_blueprint(changed)
        self.assertNotEqual(first.definition.key, second.definition.key)

    @covers_requirement("blueprint-portrait-policy::the-blueprint-lifecycle-preserves-the-characterization-fields")
    @covers_requirement("npc-identity-titles::the-blueprint-author-face-enforces-occupant-name-uniqueness")
    def test_missing_or_duplicate_identity_rejects_at_compile(self):
        # Missing identity fields reject at BOTH layers with identical decisions.
        from world.ai.scenario_director import _VALIDATORS

        for field in ("display_name", "title"):
            with self.subTest(field=field):
                bad = _characterized_payload()
                del bad["stages"][0]["npc_req"][0][field]
                with self.assertRaises(QuestCompileError):
                    compile_quest_blueprint(bad)
                guardrail_errors = []
                for validator in _VALIDATORS.values():
                    guardrail_errors.extend(validator(bad))
                self.assertTrue(guardrail_errors, "guardrail rejects too")

        # Same-stage duplicate names reject (npc-identity-titles uniqueness).
        twin = _characterized_payload()
        first_entry = twin["stages"][0]["npc_req"][0]
        twin["stages"][0]["npc_req"].append(
            {
                **first_entry,
                "portrait": {"stable_key": "different_face"},
            }
        )
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(twin)

    @covers_requirement("npc-identity-titles::the-blueprint-author-face-enforces-occupant-name-uniqueness")
    def test_cross_stage_duplicate_names_reject_even_identical(self):
        base = _characterized_payload()
        second_stage = json.loads(json.dumps(base["stages"][0]))
        second_stage["index"] = 1
        second_stage["location_req"]["scene_sentence"] = "另一段不同的場景描述。"
        second_stage["npc_req"] = json.loads(
            json.dumps(base["stages"][0]["npc_req"])
        )
        base["stages"].append(second_stage)
        with self.assertRaises(QuestCompileError):
            compile_quest_blueprint(base)

    @covers_requirement("blueprint-portrait-policy::the-blueprint-lifecycle-preserves-the-characterization-fields")
    def test_restore_payload_without_title_raises_named_compile_error(self):
        from world.quests.compile import _characterization_from_payload

        payload = _characterized_payload()["stages"][0]["npc_req"][0]
        stored = {
            "display_name": payload["display_name"],
            "age": payload["age"],
            "apparent_age": payload["apparent_age"],
            "portrait_stable_key": payload["portrait"]["stable_key"],
            "background": None,
            "persona": [],
        }
        with self.assertRaisesRegex(QuestCompileError, "title"):
            _characterization_from_payload(stored)

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

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    @covers_requirement("art-stable-key-contract::the-character-portrait-keyspace-reserves-the-digit-only-region-for-player-characters")
    def test_digit_only_stable_key_rejects_at_compile(self):
        for stable_key in ("7", "42"):
            with self.subTest(stable_key=stable_key):
                bad = _characterized_payload()
                bad["stages"][0]["npc_req"][0]["portrait"] = {
                    "stable_key": stable_key
                }
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
                "title": "林間盜匪副手",
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
if __name__ == "__main__":
    unittest.main()
