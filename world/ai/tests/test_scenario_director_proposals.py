"""Tests for the scenario-director proposal and blueprint-characterization types."""


import json
import unittest

from world.ai.scenario_director import (
    BlueprintFailure,
    BlueprintLocation,
    BlueprintNpcReq,
    BlueprintObjective,
    BlueprintPortrait,
    BlueprintReward,
    BlueprintStage,
    QuestBlueprint,
)
from world.ai.tests._director_helpers import _blueprint, _item

from tools.spec_traceability import covers_requirement



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
            {
                "role": "bandit",
                "tier": "bandit",
                "disposition": None,
                "display_name": "黑鬍",
                "title": "無portrait頭目",
            }
        ]
        first = compile_quest_blueprint(base_payload)

        changed = json.loads(json.dumps(base_payload))
        changed["stages"][0]["npc_req"][0].update(
            {
                "display_name": "黑鬍",
                "title": "林間盜匪首領",
                "age": 35,
                "apparent_age": 35,
                "portrait": {"stable_key": "forest_bandit_chief"},
            }
        )
        second = compile_quest_blueprint(changed)
        self.assertNotEqual(first.definition.key, second.definition.key)
