"""Canonical package proposal schema and symbolic publication (4.4).

The ScenarioDirector's structural schema and the deterministic semantic
contract describe the same payload: a schema-valid synthetic package publishes
without creating an actor, accepting a quest or registering a runtime
commission, round-trips immutably, and an ESCORT objective stays refused.
"""

from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from world.ai.scenario_director.packages import (
    PACKAGE_PAYLOAD_SCHEMA,
    package_schema_errors,
)
from world.quests import scene_store
from world.quests.encounters import publish_scene_package
from world.rules.quest_issuance import QUEST_ISSUANCE_REGISTRY
from world.quests.scene_package import ScenePackageError, validate_scene_package
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.quests.tests._scene_package_fixtures import (
    anchor_locator,
    dialogue as _dialogue,
    package as _package,
    quest_payload,
    role,
)


class PackageProposalSchemaTests(EvenniaTest):
    @covers_requirement(
        "scenario-director::scene-package-proposals-share-the-canonical-bounded-contract"
    )
    def test_a_valid_synthetic_package_passes_the_canonical_schema(self):
        self.assertEqual(package_schema_errors(_package()), ())

    @covers_requirement(
        "scenario-director::scene-package-proposals-share-the-canonical-bounded-contract"
    )
    def test_an_unknown_top_level_key_is_a_structural_failure(self):
        package = _package()
        package["permissions"] = []
        errors = package_schema_errors(package)
        self.assertTrue(errors)
        self.assertIn("Additional properties are not allowed", errors[0])

    @covers_requirement(
        "scenario-director::scene-package-proposals-share-the-canonical-bounded-contract"
    )
    def test_an_out_of_vocabulary_effect_verb_is_a_structural_failure(self):
        package = _package()
        package["dialogue"][0]["phases"][0]["topics"] = [
            {
                "keyword": "怪招",
                "response": "測試文字",
                "effect_verb": "grant_reward",
                "effect_reference": "ai_deadbeef",
            }
        ]
        errors = package_schema_errors(package)
        self.assertTrue(errors)
        self.assertIn("effect_verb", errors[0])

    @covers_requirement(
        "scenario-director::scene-package-proposals-share-the-canonical-bounded-contract"
    )
    def test_the_schema_declares_the_closed_top_level_contract(self):
        self.assertFalse(PACKAGE_PAYLOAD_SCHEMA["additionalProperties"])
        self.assertEqual(
            set(PACKAGE_PAYLOAD_SCHEMA["properties"]),
            {
                "display_name",
                "source_id",
                "quest",
                "roles",
                "relationships",
                "knowledge",
                "encounters",
                "dialogue",
                "commission",
            },
        )


class PackageProposalPublicationTests(RegistryIsolationMixin, EvenniaTest):
    @covers_requirement(
        "scenario-director::scene-package-proposals-share-the-canonical-bounded-contract"
    )
    def test_symbolic_publication_creates_no_actor_acceptance_or_authority(self):
        from typeclasses.npcs import NPC

        published = publish_scene_package(_package(), owner="director", tick=3)
        self.assertEqual(NPC.objects.all_family().count(), 0)
        self.assertEqual(QUEST_ISSUANCE_REGISTRY, {})
        grants = scene_store.list_commission_grants(published.package_id)
        self.assertEqual(len(grants), 1)
        self.assertFalse(grants[0].registered)

    @covers_requirement(
        "scenario-director::scene-package-proposals-share-the-canonical-bounded-contract",
        "persistent-story-roles::published-packages-separate-immutable-definitions-from-runtime-bindings",
    )
    def test_a_published_payload_round_trips_immutably(self):
        published = publish_scene_package(_package(), owner="director")
        row = scene_store.read_package(published.package_id)
        reloaded = validate_scene_package(row.payload)
        self.assertEqual(reloaded.package_id, published.package_id)
        self.assertEqual(reloaded.quest.definition.key, published.definition_key)

    def test_an_escort_objective_stays_refused(self):
        escort = _package(
            quest=quest_payload(issuer="mother"),
            commission=None,
            roles=[role("mother")],
            relationships=[],
            knowledge=[],
            encounters=[
                {
                    "scene_id": "south_gate",
                    "role_ids": ["mother"],
                    "locator": anchor_locator(),
                    "prerequisites": [],
                }
            ],
            dialogue=[_dialogue("mother")],
        )
        escort["quest"]["stages"][0]["objective"] = {
            "kind": "escort",
            "quantity": 1,
        }
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(escort)
        self.assertIn("ESCORT", str(caught.exception))