"""Scene-package publication, validation, and read-boundary tests.

Covers the new deterministic contracts: whole-package validation before any
write, immutable persistence with database-enforced identity, source replay and
conflict behavior, symbolic versus guild-branch commission publication, the
read-only role lookup, and startup restore. Behavior tests resolve game data
through the shared synthetic builders; no shipped key is named literally.
"""

import unittest

from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from world.quests import scene_store
from world.quests.bootstrap import restore_scene_packages
from world.quests.compile import SCENE_REQUIREMENT_REGISTRY, scene_requirements_for
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.encounters import (
    ScenePackageNotFound,
    SceneRoleNotFound,
    lookup_story_role,
    publish_scene_package,
)
from world.quests.scene_package import ScenePackageError, validate_scene_package
from world.quests.tests._compile_helpers import _issuer_key
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.quests.tests._scene_package_fixtures import (
    dialogue as _dialogue,
    package as _package,
    phase as _phase,
    quest_payload as _quest_payload,
    role as _role,
)
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.quest_issuance import QUEST_ISSUANCE_REGISTRY


class ScenePackageValidationTests(EvenniaTestCase):
    """Whole-package validation rejects every invalid reference before writes."""

    def test_a_valid_package_normalizes_and_reports_its_identity(self):
        definition = validate_scene_package(_package())
        self.assertTrue(definition.package_id.startswith("pkg_"))
        self.assertEqual(definition.role_ids(), frozenset({"mother", "daughter"}))
        self.assertEqual(
            [commission.role_id for commission in definition.commissions], ["mother"]
        )
        self.assertIsNone(definition.guild_branch)

    def test_unknown_encounter_role_is_rejected(self):
        package = _package()
        package["encounters"][0]["role_ids"] = ["stranger"]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("stranger", str(caught.exception))

    def test_unknown_place_is_rejected_without_substitution(self):
        package = _package()
        package["encounters"][0]["locator"]["anchor_key"] = "no_such_anchor"
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("no_such_anchor", str(caught.exception))

    @covers_requirement(
        "persistent-story-roles::reusable-roles-bind-exact-actor-identities"
    )
    def test_a_name_based_existing_npc_reference_is_rejected(self):
        package = _package()
        package["roles"][1]["existing_npc"] = {"kind": "key", "value": "測試住民daughter"}
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("existing_npc", str(caught.exception))

    def test_reciprocal_relationship_is_rejected(self):
        package = _package()
        package["relationships"].append(
            {"from_role": "daughter", "to_role": "mother", "kind": "parent_child"}
        )
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("reciprocal", str(caught.exception))

    def test_a_shared_visibility_knowledge_grant_is_rejected(self):
        package = _package()
        package["knowledge"][0]["provenance"] = {"kind": "world", "ref": "mother"}
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("provenance", str(caught.exception))

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_overlapping_phase_selection_is_rejected(self):
        package = _package()
        dialogue = package["dialogue"][0]
        dialogue["phases"][1]["conditions"] = [{"abandoned": True}, {"abandoned": True}]
        dialogue["phases"].append(_phase("duplicate", [{"abandoned": True}, {"abandoned": True}]))
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("overlap", str(caught.exception))

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_a_guarded_reunion_observation_is_rejected(self):
        package = _package()
        package["dialogue"][0]["phases"][1]["conditions"] = [{"reunion": True}]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("reunion", str(caught.exception))

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_a_missing_default_phase_is_rejected(self):
        package = _package()
        package["dialogue"][0]["phases"][0]["conditions"] = [{"separation": True}]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("default", str(caught.exception))

    def test_a_private_commission_carrying_merit_is_rejected(self):
        package = _package(quest=_quest_payload(issuer="mother", merit=25))
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("merit", str(caught.exception))

    def test_an_unknown_top_level_field_is_rejected(self):
        package = _package()
        package["permissions"] = []
        with self.assertRaises(ScenePackageError):
            validate_scene_package(package)


class ScenePackagePublicationTests(RegistryIsolationMixin, EvenniaTestCase):
    """Publication persists an immutable package and registers its views."""

    @covers_requirement(
        "persistent-story-roles::published-packages-separate-immutable-definitions-from-runtime-bindings"
    )
    def test_publication_registers_definition_and_requirements_without_issuance(self):
        published = publish_scene_package(_package(), owner="tester", tick=7)
        self.assertTrue(published.created)
        core = published.definition.quest
        self.assertEqual(QUEST_DEFINITION_REGISTRY[core.definition.key], core.definition)
        self.assertEqual(scene_requirements_for(core.definition.key), core.stage_requirements)
        self.assertEqual(QUEST_ISSUANCE_REGISTRY, {})
        row = scene_store.read_package(published.package_id)
        self.assertIsNotNone(row)
        self.assertEqual(row.owner_id, "tester")
        self.assertEqual(row.created_tick, 7)

    @covers_requirement(
        "persistent-story-roles::published-packages-separate-immutable-definitions-from-runtime-bindings"
    )
    def test_replaying_the_same_source_returns_the_stored_package(self):
        first = publish_scene_package(_package(), owner="tester")
        second = publish_scene_package(_package(), owner="tester")
        self.assertFalse(second.created)
        self.assertEqual(second.package_id, first.package_id)
        self.assertEqual(len(scene_store.list_packages()), 1)

    @covers_requirement(
        "persistent-story-roles::published-packages-separate-immutable-definitions-from-runtime-bindings"
    )
    def test_a_differing_payload_for_one_source_conflicts(self):
        publish_scene_package(_package(), owner="tester")
        changed = _package(display_name="另一場相遇")
        with self.assertRaises(scene_store.ScenePackageConflictError):
            publish_scene_package(changed, owner="tester")
        self.assertEqual(len(scene_store.list_packages()), 1)

    def test_a_symbolic_package_publishes_an_unregistered_grant(self):
        published = publish_scene_package(_package(), owner="tester")
        grants = scene_store.list_commission_grants(published.package_id)
        self.assertEqual(len(grants), 1)
        self.assertFalse(grants[0].registered)
        self.assertEqual(grants[0].npc_id, 0)
        self.assertEqual(grants[0].issuer_key, "npc:story_mother")

    def test_a_guild_branch_package_registers_its_offer(self):
        package = _package(
            quest=_quest_payload(issuer=_issuer_key()),
            commissions=[],
        )
        published = publish_scene_package(package, owner="tester")
        self.assertEqual(published.definition.commissions, ())
        self.assertEqual(len(GUILD_OFFER_REGISTRY), 1)
        self.assertEqual(scene_store.list_commission_grants(published.package_id), [])

    @covers_requirement(
        "persistent-story-roles::reusable-roles-bind-exact-actor-identities"
    )
    def test_an_exact_existing_npc_pk_reference_is_accepted(self):
        from evennia.utils.create import create_object

        from typeclasses.npcs import NPC

        npc = create_object(NPC, key="測試住民daughter")
        package = _package()
        package["roles"][1]["existing_npc"] = {"kind": "pk", "value": npc.pk}
        definition = validate_scene_package(package)
        self.assertEqual(definition.role("daughter").existing_npc_pk, npc.pk)


class StoryRoleLookupTests(RegistryIsolationMixin, EvenniaTestCase):
    """The role lookup is read-only and reports exact binding status."""

    def test_an_unmaterialized_role_reports_unavailable(self):
        published = publish_scene_package(_package(), owner="tester")
        found = lookup_story_role(published.package_id, "mother")
        self.assertFalse(found.bound)
        self.assertIsNone(found.npc_id)
        self.assertEqual(found.availability, "unmaterialized")
        self.assertEqual(found.commission_issuer_key, "npc:story_mother")

    def test_an_unknown_package_or_role_is_a_named_failure(self):
        published = publish_scene_package(_package(), owner="tester")
        with self.assertRaises(ScenePackageNotFound):
            lookup_story_role("pkg_missing", "mother")
        with self.assertRaises(SceneRoleNotFound):
            lookup_story_role(published.package_id, "stranger")


class ScenePackageRestoreTests(RegistryIsolationMixin, EvenniaTestCase):
    """Startup restore republishes definition views, never symbolic authority."""

    def test_restore_reregisters_definitions_only(self):
        published = publish_scene_package(_package(), owner="tester")
        key = published.definition.quest.definition.key
        QUEST_DEFINITION_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.clear()
        restore_scene_packages()
        self.assertIn(key, QUEST_DEFINITION_REGISTRY)
        self.assertIn(key, SCENE_REQUIREMENT_REGISTRY)
        self.assertEqual(QUEST_ISSUANCE_REGISTRY, {})

    def test_restore_reregisters_only_an_activated_grant(self):
        from evennia.utils.create import create_object

        from typeclasses.npcs import NPC

        published = publish_scene_package(_package(), owner="tester")
        row = scene_store.read_package(published.package_id)
        grant = scene_store.list_commission_grants(published.package_id)[0]
        actor = create_object(NPC, key="測試住民mother")
        scene_store.bind_role(row, grant.role_id, actor.pk)
        scene_store.assign_grant_actor(
            row, grant.role_id, grant.definition_key, actor.pk
        )
        scene_store.set_grant_registered(
            row, grant.role_id, grant.definition_key, True
        )
        QUEST_DEFINITION_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.clear()
        restore_scene_packages()
        from world.rules.quest_issuance import resolve_issuance

        self.assertIsNotNone(
            resolve_issuance(grant.definition_key, grant.issuer_key)
        )
        self.assertIsNotNone(row)

    def test_restore_refuses_a_registered_grant_without_an_actor(self):
        published = publish_scene_package(_package(), owner="tester")
        grant = scene_store.list_commission_grants(published.package_id)[0]
        from world.quests.models import StoryCommissionGrant

        StoryCommissionGrant.objects.filter(pk=grant.pk).update(registered=True)
        with self.assertRaises(scene_store.SceneStoreError):
            restore_scene_packages()


class ScenePackageCancellationTests(RegistryIsolationMixin, EvenniaTestCase):
    """Cancellation retires an unactivated definition without rewriting it."""

    @covers_requirement(
        "persistent-story-roles::named-role-retention-survives-quest-termination"
    )
    def test_cancellation_transitions_once(self):
        published = publish_scene_package(_package(), owner="tester")
        self.assertTrue(scene_store.cancel_package(published.package_id))
        self.assertFalse(scene_store.cancel_package(published.package_id))
        row = scene_store.read_package(published.package_id)
        self.assertEqual(row.status, scene_store.PACKAGE_STATUS_CANCELLED)
        self.assertEqual(row.payload, _package())

    @covers_requirement(
        "persistent-story-roles::published-packages-separate-immutable-definitions-from-runtime-bindings"
    )
    def test_payload_rewrite_is_still_refused(self):
        from world.quests.models import ScenePackage

        published = publish_scene_package(_package(), owner="tester")
        with self.assertRaises(ValueError):
            ScenePackage.objects.filter(package_id=published.package_id).update(
                payload={}
            )


class SceneStoreRuntimeContractTests(RegistryIsolationMixin, EvenniaTestCase):
    """The runtime store refuses stale revisions and unassigned authority."""

    def _published_with_phase(self):
        published = publish_scene_package(_package(), owner="tester")
        row = scene_store.read_package(published.package_id)
        scene_store.set_dialogue_phase(row, "mother", "searching")
        return row

    def test_a_stale_phase_revision_is_refused(self):
        row = self._published_with_phase()
        advanced = scene_store.advance_dialogue_phase(
            row, "mother", "everyday", expected_revision=0
        )
        self.assertEqual(advanced.selected_phase, "everyday")
        self.assertEqual(advanced.revision, 1)
        stale = scene_store.advance_dialogue_phase(
            row, "mother", "searching", expected_revision=0
        )
        self.assertIsNone(stale)
        self.assertEqual(
            scene_store.get_dialogue_phase(row.package_id, "mother").revision, 1
        )

    def test_a_grant_cannot_be_registered_before_its_actor(self):
        published = publish_scene_package(_package(), owner="tester")
        row = scene_store.read_package(published.package_id)
        grant = scene_store.list_commission_grants(published.package_id)[0]
        with self.assertRaises(scene_store.SceneStoreError):
            scene_store.set_grant_registered(
                row, grant.role_id, grant.definition_key, True
            )

    def test_a_grant_cannot_authorize_an_unbound_actor(self):
        from evennia.utils.create import create_object

        from typeclasses.npcs import NPC

        published = publish_scene_package(_package(), owner="tester")
        row = scene_store.read_package(published.package_id)
        grant = scene_store.list_commission_grants(published.package_id)[0]
        stranger = create_object(NPC, key="陌生人")
        with self.assertRaises(scene_store.SceneStoreError):
            scene_store.assign_grant_actor(
                row, grant.role_id, grant.definition_key, stranger.pk
            )


class ScenePackageAmbiguityTests(EvenniaTestCase):
    """Static phase selection is unambiguous or the package is refused."""

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_intersecting_non_default_phases_are_rejected(self):
        package = _package()
        package["dialogue"][0]["phases"].append(
            _phase("closed_again", [{"closure": True}])
        )
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("overlap", str(caught.exception))

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_a_contradictory_condition_is_rejected(self):
        package = _package()
        package["dialogue"][0]["phases"][1]["conditions"] = [
            {"closure": True},
            {"closure": False},
        ]
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(package)
        self.assertIn("unsatisfiable", str(caught.exception))

    @covers_requirement(
        "story-phase-dialogue::packages-declare-complete-finite-dialogue-phases"
    )
    def test_an_unhashable_role_reference_is_rejected(self):
        package = _package()
        package["relationships"] = [
            {"from_role": ["mother"], "to_role": "daughter", "kind": "parent_child"}
        ]
        with self.assertRaises(ScenePackageError):
            validate_scene_package(package)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
