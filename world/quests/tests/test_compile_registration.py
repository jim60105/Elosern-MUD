"""Quest publication and registry tests (RegisterGeneratedQuestTests family).

Covers ``register_generated_quest`` all-or-nothing publication with preflight
and rollback, the scene-requirement registry entries, and the shared payload
contract with the ``scenario_director`` guardrail. Shared isolation and
payload helpers come from ``_compile_helpers``.
"""

from unittest.mock import patch
import unittest

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
    QuestStage,
    QuestType,
    register_quest_definition,
    validate_definition,
)
from world.quests.tests._compile_helpers import (
    CompileRegistryIsolation,
    _defeat_payload,
)
from world.rules.guild_offers import GUILD_OFFER_REGISTRY, GuildQuestOffer, QuestReward

from tools.spec_traceability import covers_requirement

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
            {
                "role": "bandit",
                "tier": "bandit",
                "disposition": None,
                "display_name": "黑鬍",
                "title": "林間盜匪首領",
            }
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
            {
                "role": "bandit",
                "tier": "bandit",
                "disposition": None,
                "display_name": "黑鬍",
                "title": "林間盜匪首領",
            }
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
if __name__ == "__main__":
    unittest.main()
