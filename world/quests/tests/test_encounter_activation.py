"""Pre-acceptance encounter activation tests (quest-scene-encounters 1.3/2.3).

The boundary must commit one durable identity with exact role bindings and no
accepted quest record, reuse bound actors instead of re-creating them, refuse
missing/dead/departed actors and wrong locators without writing, and leave the
same encounter identity invocable after a technical failure.
"""

from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import QuestIssuer
from typeclasses.rooms import AnchorRoom
from world.quests import scene_store
from world.quests.encounter_activation import (
    EncounterUnavailable,
    activate_scene_encounter,
    cancel_scene_encounter,
    committed_observations,
)
from world.quests.encounters import publish_scene_package
from world.quests.runtime import read_records
from world.quests.tests._compile_helpers import _anchor_key
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.quests.tests._scene_package_fixtures import package as _package
from world.rules.quest_issuance import QUEST_ISSUANCE_REGISTRY, resolve_issuer_key


class EncounterActivationTestBase(RegistryIsolationMixin, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="訪客")
        self.room = create_object(AnchorRoom, key="南門")
        self.room.db.anchor_key = _anchor_key()
        self.published = publish_scene_package(_package(), owner="tester")

    def _activate(self, scene_id="south_gate", **kwargs):
        kwargs.setdefault("room", self.room)
        kwargs.setdefault("tick", 5)
        return activate_scene_encounter(
            self.player, self.published.package_id, scene_id, **kwargs
        )


class EncounterActivationTests(EncounterActivationTestBase):
    def test_activation_binds_exact_roles_without_accepting_a_quest(self):
        result = self._activate()
        self.assertTrue(result.activated)
        self.assertTrue(result.created)
        self.assertEqual(set(result.role_bindings), {"daughter"})
        bound = scene_store.get_role_binding(self.published.package_id, "daughter")
        self.assertEqual(bound.npc_id, result.role_bindings["daughter"])
        self.assertEqual(bound.availability, "bound")
        self.assertEqual(read_records(self.player), [])
        self.assertEqual(self.room.db.desc, None)

    def test_either_encounter_activates_first_and_both_preserve_the_relationship(self):
        first = self._activate("south_gate")
        second = self._activate("market")
        self.assertTrue(first.activated)
        self.assertTrue(second.activated)
        self.assertNotEqual(
            first.role_bindings["daughter"], second.role_bindings["mother"]
        )
        self.assertEqual(read_records(self.player), [])

    def test_repeat_activation_reuses_the_committed_identity(self):
        first = self._activate()
        second = self._activate()
        self.assertFalse(second.created)
        self.assertEqual(second.role_bindings, first.role_bindings)
        self.assertEqual(
            ObjectDB.objects.filter(
                db_key="測試住民daughter", db_typeclass_path="typeclasses.npcs.LLMNPC"
            ).count(),
            1,
        )

    def test_a_wrong_locator_is_named_and_writes_nothing(self):
        other = create_object(AnchorRoom, key="別處")
        other.db.anchor_key = "not_the_encounter_anchor"
        result = self._activate(room=other)
        self.assertFalse(result.activated)
        self.assertEqual(result.reason, "wrong_locator")
        self.assertEqual(scene_store.list_role_bindings(self.published.package_id), [])
        self.assertIsNone(
            scene_store.get_encounter(
                self.published.package_id, "south_gate", int(self.player.pk)
            )
        )

    def test_a_missing_bound_actor_is_named_without_a_repair_actor(self):
        first = self._activate()
        npc = ObjectDB.objects.filter(id=first.role_bindings["daughter"]).first()
        npc.delete()
        result = self._activate()
        self.assertFalse(result.activated)
        self.assertEqual(result.reason, "actor_missing")
        self.assertEqual(
            scene_store.get_role_binding(
                self.published.package_id, "daughter"
            ).availability,
            "actor_missing",
        )

    def test_a_dead_bound_actor_is_named(self):
        first = self._activate()
        npc = ObjectDB.objects.filter(id=first.role_bindings["daughter"]).first()
        npc.traits.hp.base = 0
        npc.traits.hp.current = 0
        result = self._activate()
        self.assertFalse(result.activated)
        self.assertEqual(result.reason, "actor_dead")

    def test_cancellation_prevents_activation(self):
        self.assertTrue(
            cancel_scene_encounter(
                self.player, self.published.package_id, "south_gate", tick=5
            )
        )
        result = self._activate()
        self.assertFalse(result.activated)
        self.assertEqual(result.reason, "cancelled")
        self.assertFalse(
            cancel_scene_encounter(
                self.player, self.published.package_id, "south_gate", tick=5
            )
        )

    def test_a_fabricated_observation_mapping_is_refused(self):
        with self.assertRaises(EncounterUnavailable):
            self._activate(observations={"closure": True})

    def test_the_issuer_role_is_provisioned_and_its_commission_registered(self):
        self._activate("market")
        actor = ObjectDB.objects.filter(
            id=scene_store.get_role_binding(self.published.package_id, "mother").npc_id
        ).first()
        self.assertTrue(actor.components.has(QuestIssuer.name))
        key = resolve_issuer_key(actor)
        self.assertEqual(key, "npc:story_mother")
        self.assertIn((self.published.definition_key, key), QUEST_ISSUANCE_REGISTRY)
        grant = scene_store.list_commission_grants(self.published.package_id)[0]
        self.assertTrue(grant.registered)
        self.assertEqual(grant.npc_id, int(actor.pk))

    def test_the_initial_phase_is_initialized_for_each_materialized_role(self):
        result = self._activate()
        runtime = scene_store.get_dialogue_phase(self.published.package_id, "daughter")
        self.assertEqual(runtime.selected_phase, "searching")
        self.assertEqual(runtime.revision, 0)
        self.assertTrue(result.activated)

    def test_committed_observations_report_the_pre_closure_state(self):
        self._activate()
        facts = committed_observations(self.published.package_id)
        self.assertTrue(facts["separation"])
        self.assertTrue(facts["unresolved"])
        self.assertFalse(facts["closure"])

    def test_a_failure_after_creation_rolls_back_and_reuses_the_identity(self):
        with patch(
            "world.quests.scene_store.mark_encounter_activated",
            side_effect=RuntimeError("injected post-creation failure"),
        ):
            with self.assertRaises(RuntimeError):
                self._activate()
        self.assertEqual(
            ObjectDB.objects.filter(db_key="測試住民daughter").count(), 0
        )
        self.assertEqual(scene_store.list_role_bindings(self.published.package_id), [])
        result = self._activate()
        self.assertTrue(result.activated)
        self.assertEqual(
            ObjectDB.objects.filter(db_key="測試住民daughter").count(), 1
        )

    def test_a_failure_after_component_configuration_rolls_back(self):
        with patch(
            "world.rules.quest_issuance.provision_scoped_issuer",
            side_effect=RuntimeError("injected configuration failure"),
        ):
            with self.assertRaises(RuntimeError):
                self._activate("market")
        self.assertEqual(ObjectDB.objects.filter(db_key="測試住民mother").count(), 0)
        self.assertEqual(scene_store.list_role_bindings(self.published.package_id), [])
        self.assertEqual(QUEST_ISSUANCE_REGISTRY, {})

    def test_a_failure_after_commission_registration_rolls_back(self):
        with patch(
            "world.quests.compile.registration.register_quest_issuance",
            side_effect=RuntimeError("injected registration failure"),
        ):
            with self.assertRaises(RuntimeError):
                self._activate("market")
        self.assertEqual(QUEST_ISSUANCE_REGISTRY, {})
        self.assertEqual(scene_store.list_role_bindings(self.published.package_id), [])
        grant = scene_store.list_commission_grants(self.published.package_id)[0]
        self.assertFalse(grant.registered)
        self.assertEqual(grant.npc_id, 0)
