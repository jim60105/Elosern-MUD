"""Retained named-role transfer before instance reclamation (3.1/3.2).

A retained named story role outlives the quest: the maps-owned reclamation
transfers any role-bound actor still inside a due reclaimable instance to its
validated permanent destination, keeps it whole, and removes its ephemeral
ownership instead of deleting it. An unavailable destination keeps the room and
the actor intact and defers the reclaim.
"""

from evennia.utils.create import create_object
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, InstanceRoom
from world.maps.instance import reclaim_due_instances, register_owned_entity
from world.quests import scene_store
from world.quests.encounters import publish_scene_package
from world.quests.tests._compile_helpers import _anchor_key
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.quests.tests._scene_package_fixtures import package as _package
from world.rules.clock import ScheduledEvent
from world.rules.npc_persona import read_npc_persona


class RetainedRoleReclamationTests(RegistryIsolationMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.published = publish_scene_package(_package(), owner="tester")
        self.room = create_object(InstanceRoom, key="歸途小徑")
        self.room.db.expire_tick = 50
        self.actor = create_object(NPC, key="測試住民daughter")
        self.actor.move_to(self.room, quiet=True)
        register_owned_entity(self.room, self.actor)
        row = scene_store.read_package(self.published.package_id)
        scene_store.bind_role(
            row, "daughter", int(self.actor.pk), provenance={"kind": "test"}, tick=1
        )

    @covers_requirement(
        "persistent-story-roles::named-role-retention-survives-quest-termination"
    )
    def test_a_retained_role_is_transferred_instead_of_deleted(self):
        destination = create_object(AnchorRoom, key="南門")
        destination.db.anchor_key = _anchor_key()
        row = scene_store.read_package(self.published.package_id)
        scene_store.set_dialogue_phase(row, "daughter", "searching")
        before_persona = read_npc_persona(self.actor)
        events = reclaim_due_instances(0, 100)
        self.assertFalse(InstanceRoom.objects.filter(id=self.room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": self.room.key}),
            events,
        )
        self.actor.refresh_from_db()
        self.assertEqual(self.actor.location.pk, destination.pk)
        # Identity, persona and committed phase survive the transfer: nothing is
        # cloned, resurrected or reset.
        self.assertEqual(read_npc_persona(self.actor), before_persona)
        self.assertEqual(
            scene_store.get_dialogue_phase(self.published.package_id, "daughter").selected_phase,
            "searching",
        )
        self.assertEqual(
            scene_store.get_role_binding(self.published.package_id, "daughter").npc_id,
            int(self.actor.pk),
        )

    def test_an_unavailable_destination_keeps_the_room_and_the_actor(self):
        events = reclaim_due_instances(0, 100)
        self.assertTrue(InstanceRoom.objects.filter(id=self.room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaim_deferred", 100, {"room": self.room.key}),
            events,
        )
        self.actor.refresh_from_db()
        self.assertEqual(self.actor.location.pk, self.room.pk)
        self.assertIn(self.actor, list(self.room.db.owned_entities or []))

    @covers_requirement(
        "persistent-story-roles::named-role-retention-survives-quest-termination"
    )
    def test_a_disposable_occupant_is_still_deleted_alongside_a_retained_role(self):
        destination = create_object(AnchorRoom, key="南門")
        destination.db.anchor_key = _anchor_key()
        disposable = create_object(NPC, key="路人")
        disposable.move_to(self.room, quiet=True)
        register_owned_entity(self.room, disposable)
        disposable_pk = disposable.pk
        reclaim_due_instances(0, 100)
        self.assertFalse(NPC.objects.filter(id=disposable_pk).exists())
        self.actor.refresh_from_db()
        self.assertEqual(self.actor.location.pk, destination.pk)

    def test_a_mid_pass_transfer_failure_keeps_the_scene_and_reconciles_caches(self):
        from unittest.mock import patch

        from world.quests import retention

        destination = create_object(AnchorRoom, key="南門")
        destination.db.anchor_key = _anchor_key()
        second = create_object(NPC, key="測試住民mother")
        second.move_to(self.room, quiet=True)
        register_owned_entity(self.room, second)
        row = scene_store.read_package(self.published.package_id)
        scene_store.bind_role(
            row, "mother", int(second.pk), provenance={"kind": "test"}, tick=1
        )

        real_transfer = retention.transfer_retained_role
        calls = {"count": 0}

        def flaky(entity, record, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise retention.RetentionTransferError("injected mid-pass failure")
            return real_transfer(entity, record, **kwargs)

        with patch(
            "world.quests.retention.transfer_retained_role", side_effect=flaky
        ):
            events = reclaim_due_instances(0, 100)

        self.assertTrue(InstanceRoom.objects.filter(id=self.room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaim_deferred", 100, {"room": self.room.key}),
            events,
        )
        for entity in (self.actor, second):
            # The raw column value is the rolled-back truth; the idmapper may
            # still hold a cached instance for these rows.
            self.assertEqual(
                ObjectDB.objects.filter(pk=entity.pk)
                .values_list("db_location_id", flat=True)
                .first(),
                self.room.pk,
            )
        owned_pks = {
            obj.pk
            for obj in (self.room.db.owned_entities or [])
            if obj and obj.pk
        }
        self.assertEqual(owned_pks, {self.actor.pk, second.pk})
        # The destination the first transfer already wrote is re-read from the
        # rolled-back database, so it shows no phantom occupant.
        self.assertNotIn(
            self.actor.pk,
            {obj.pk for obj in destination.contents_cache.get() if obj and obj.pk},
        )
