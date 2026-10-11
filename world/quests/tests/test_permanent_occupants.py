"""Accepted-stage permanent-destination package occupants (quest-scene-encounters 2.4).

A validated package stage that requires a named role at a permanent anchor/grid
destination reuses the existing room, leaves its description unchanged and ends
with exactly one package-owned role binding -- no second actor, no clone, no
teleport of a previously bound actor back to the stage origin. A permanent stage
without validated package-owned occupants still locates the room only, a
standalone permanent occupant is still refused, and a required actor that is
missing, dead or departed is a named failure rather than a replacement.
"""

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import AnchorRoom
from world.quests import scene_store
from world.quests.compile import QuestCompileError, compile_quest_blueprint
from world.quests.encounters import publish_scene_package
from world.quests.materializer import SceneBuilderRoleUnavailable
from world.quests.runtime import read_records
from world.quests.scene_builder import materialize_stage
from world.quests.scene_package import ScenePackageError, validate_scene_package
from world.quests.tests._compile_helpers import _anchor_key, _issuer_key
from world.quests.tests._fixtures import RegistryIsolationMixin, accept
from world.quests.tests._scene_package_fixtures import (
    package as _package,
    quest_payload,
    role,
)

DESCRIPTION = "南門前的老石板路，晨霧還沒散。"
LLM_NPC_PATH = "typeclasses.npcs.LLMNPC"


def _npc_req(role_id: str) -> dict:
    """One permanent-destination occupant entry carrying the authored identity."""
    entry = role(role_id)
    request = {"role": role_id, "tier": entry["tier"], "disposition": None}
    request.update(entry["characterization"])
    return request


def _permanent_occupant_package(source_id: str) -> dict:
    payload = _package()
    payload["source_id"] = source_id
    payload["quest"]["stages"][0]["npc_req"] = [_npc_req("mother")]
    return payload


class PermanentPackageOccupantTests(RegistryIsolationMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="旅人")
        self.room = create_object(AnchorRoom, key="南門")
        self.room.db.anchor_key = _anchor_key()
        self.room.db.desc = DESCRIPTION
        self.published = publish_scene_package(
            _permanent_occupant_package("synthetic-permanent-source"), owner="tester"
        )
        self.record = accept(self.player, self.published.definition_key)

    def _record(self):
        return next(
            record
            for record in read_records(self.player)
            if record.quest_id == self.record.quest_id
        )

    def test_a_package_stage_adopts_exactly_one_role_binding_in_the_existing_room(self):
        result = materialize_stage(self.player, self.record.quest_id)
        self.assertEqual(result.room.pk, self.room.pk)
        self.assertEqual(result.room.db.desc, DESCRIPTION)
        bindings = scene_store.list_role_bindings(self.published.package_id)
        self.assertEqual([binding.role_id for binding in bindings], ["mother"])
        actor = ObjectDB.objects.filter(id=bindings[0].npc_id).first()
        self.assertIsNotNone(actor)
        self.assertEqual(actor.location.pk, self.room.pk)
        # A permanent destination never gains a stage binding or escorted entities.
        fresh = self._record()
        self.assertIsNone(fresh.stage_room_id)
        self.assertEqual(fresh.protected_entity_ids, ())

    def test_repeat_materialization_reuses_the_same_actor(self):
        first = materialize_stage(self.player, self.record.quest_id)
        before = scene_store.get_role_binding(self.published.package_id, "mother")
        second = materialize_stage(self.player, self.record.quest_id)
        after = scene_store.get_role_binding(self.published.package_id, "mother")
        self.assertEqual(after.npc_id, before.npc_id)
        self.assertEqual(second.room.pk, first.room.pk)
        self.assertEqual(ObjectDB.objects.filter(db_typeclass_path=LLM_NPC_PATH).count(), 1)

    def test_a_missing_required_actor_is_a_named_failure_without_a_replacement(self):
        materialize_stage(self.player, self.record.quest_id)
        actor = ObjectDB.objects.filter(
            id=scene_store.get_role_binding(self.published.package_id, "mother").npc_id
        ).first()
        actor.delete()
        with self.assertRaises(SceneBuilderRoleUnavailable) as caught:
            materialize_stage(self.player, self.record.quest_id)
        self.assertIn("actor_missing", str(caught.exception))
        self.assertEqual(ObjectDB.objects.filter(db_typeclass_path=LLM_NPC_PATH).count(), 0)

    def test_a_permanent_stage_without_occupants_is_located_only(self):
        payload = _package()
        payload["source_id"] = "synthetic-locate-only-source"
        published = publish_scene_package(payload, owner="tester")
        record = accept(self.player, published.definition_key)
        result = materialize_stage(self.player, record.quest_id)
        self.assertEqual(result.room.pk, self.room.pk)
        self.assertEqual(scene_store.list_role_bindings(published.package_id), [])
        self.assertEqual(self.room.db.desc, DESCRIPTION)


class PermanentOccupantGuardTests(RegistryIsolationMixin, EvenniaTest):
    def test_a_standalone_permanent_occupant_payload_is_still_refused(self):
        payload = quest_payload(issuer=_issuer_key())
        payload["stages"][0]["npc_req"] = [_npc_req("mother")]
        with self.assertRaises(QuestCompileError) as caught:
            compile_quest_blueprint(payload)
        self.assertIn("instance-layer destination", str(caught.exception))

    def test_a_bound_defeat_at_a_permanent_destination_is_rejected(self):
        payload = _permanent_occupant_package("synthetic-bound-defeat-source")
        payload["quest"]["stages"][0]["objective"] = {"kind": "defeat", "quantity": 1}
        with self.assertRaises(ScenePackageError) as caught:
            validate_scene_package(payload)
        self.assertIn("instance-layer destination", str(caught.exception))

    def test_the_guardrail_mirrors_the_same_bounded_exception(self):
        from world.ai.scenario_director.validators import _validate_scene_bound_rules

        payload = quest_payload(issuer=_issuer_key())
        payload["stages"][0]["npc_req"] = [_npc_req("mother")]
        self.assertTrue(_validate_scene_bound_rules(payload))
        self.assertEqual(
            _validate_scene_bound_rules(payload, package_roles=frozenset({"mother"})),
            [],
        )
        # The package role set never lifts a bound-target DEFEAT at a permanent
        # destination, which could not be bound to its targets there.
        payload["stages"][0]["objective"] = {"kind": "defeat", "quantity": 1}
        self.assertTrue(
            _validate_scene_bound_rules(payload, package_roles=frozenset({"mother"}))
        )