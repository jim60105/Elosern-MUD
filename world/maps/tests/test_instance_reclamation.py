"""Integration tests for reclaim_due_instances routing and entity resolution
(map-instance tasks 7.4-7.14)."""

from tools.spec_traceability import covers_requirement

import json
from unittest.mock import patch

from django.conf import settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.entities import LivingEntity
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import InstanceRoom
from world.maps.instance import (
    reclaim_due_instances,
    register_owned_entity,
)
from world.rules.clock import ScheduledEvent

BLOCKING_PIN = "quest:1:stage:0"


def _due_room(key, *, tick=100, named=False, interacted=False):
    room = create_object(InstanceRoom, key=key)
    room.db.expire_tick = tick
    room.db.named = named
    room.db.interacted = interacted
    return room


class ReclaimRoutingTests(EvenniaTest):
    def test_player_present_defers_room(self):
        room = _due_room("occupied", tick=50)
        self.char1.move_to(room, quiet=True)
        events = reclaim_due_instances(0, 100)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertEqual(room.db.expire_tick, 50)
        self.assertIn(
            ScheduledEvent("instance_reclaim_deferred", 100, {"room": room.key}),
            events,
        )

    @covers_requirement("instance-reclamation::reclaim-due-instances-defers-only-rooms-with-a-playercharacter-present-or-an-active-pin")
    def test_pinned_due_room_defers_identically_to_player_present(self):
        room = _due_room("pinned_due")
        room.db.pin_reasons = [BLOCKING_PIN]
        events = reclaim_due_instances(0, 100)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertEqual(room.db.expire_tick, 100)
        self.assertIn(
            ScheduledEvent("instance_reclaim_deferred", 100, {"room": room.key}),
            events,
        )

    def test_npc_only_room_is_not_deferred_for_npc_presence_alone(self):
        room = _due_room("npc_alone")
        npc = create_object(NPC, key="civilian")
        npc.move_to(room, quiet=True)
        events = reclaim_due_instances(0, 100)
        # Not deferred: routed to promotion (not named) either way, so it must
        # have been reclaimed in this same call.
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )

    @covers_requirement("instance-reclamation::reclaim-due-instances-promotes-rooms-that-are-both-named-and-interacted")
    def test_named_and_interacted_due_room_is_promoted_not_deleted(self):
        room = _due_room("promotable", named=True, interacted=True)
        npc = create_object(NPC, key="resident")
        npc.move_to(room, quiet=True)
        events = reclaim_due_instances(0, 100)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIsNone(room.db.expire_tick)
        self.assertIn(
            ScheduledEvent("instance_promoted", 100, {"room": room.key}),
            events,
        )
        # Promotion leaves the NPC in place -- neither despawned nor relocated.
        self.assertIn(npc, [o for o in room.contents if isinstance(o, LivingEntity)])

    def test_promotion_leaves_attach_exit_pair_untouched(self):
        from typeclasses.exits import Exit

        origin = create_object(__import__("typeclasses.rooms", fromlist=["Room"]).Room, key="origin_promote")
        from world.maps.instance import spawn_instance_room

        room = spawn_instance_room(
            origin,
            {"prototype_parent": "instance_room", "key": "promote_exit"},
            exit_key="in",
            return_key="out",
            ttl_seconds=10,
            named=True,
        )
        room.db.interacted = True
        before_exits = list(Exit.objects.all())
        events = reclaim_due_instances(0, 100)
        self.assertIn(
            ScheduledEvent("instance_promoted", 100, {"room": room.key}),
            events,
        )
        self.assertEqual(list(Exit.objects.all()), before_exits)

    def test_named_alone_does_not_promote(self):
        room = _due_room("named_only", named=True)
        events = reclaim_due_instances(0, 100)
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )

    def test_interacted_alone_does_not_promote(self):
        room = _due_room("interacted_only", interacted=True)
        events = reclaim_due_instances(0, 100)
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )

    @covers_requirement("instance-reclamation::reclaim-due-instances-deletes-rooms-that-are-due-unblocked-and-not-promotable")
    def test_unnamed_unoccupied_due_room_is_reclaimed(self):
        room = _due_room("plain_due")
        events = reclaim_due_instances(0, 100)
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )

    def test_dropped_item_survives_reclamation_relocated_not_destroyed(self):
        room = _due_room("item_room")
        item = create_object(self.object_typeclass, key="dropped_ring", location=room)
        events = reclaim_due_instances(0, 100)
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertTrue(item.pk and item.location is not None)
        self.assertNotEqual(item.location, room)

    def test_npc_only_room_is_reclaimed_within_single_call(self):
        room = _due_room("npc_reclaim")
        npc = create_object(NPC, key="left_behind")
        npc.move_to(room, quiet=True)
        events = reclaim_due_instances(0, 100)
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )

    def test_owned_npc_despawned_and_unowned_npc_relocated_on_reclaim(self):
        room = _due_room("mixed_npc")
        owned = create_object(NPC, key="scene_npc")
        owned.move_to(room, quiet=True)
        register_owned_entity(room, owned)
        unowned = create_object(NPC, key="passerby")
        unowned.move_to(room, quiet=True)

        events = reclaim_due_instances(0, 100)
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )
        # Owned NPC was deleted.
        self.assertFalse(NPC.objects.filter(id=owned.id).exists())
        # Unowned NPC was relocated to DEFAULT_HOME, not destroyed.
        self.assertTrue(NPC.objects.filter(id=unowned.id).exists())
        self.assertEqual(unowned.location.dbref, settings.DEFAULT_HOME)

    def test_monster_routing_follows_owned_registry_not_entity_type(self):
        # The despawn-vs-relocate rule depends only on owned_entities
        # membership, never on entity type (instance-reclamation delta spec).
        room = _due_room("mixed_monster")
        owned = create_object(Monster, key="scene_monster")
        owned.move_to(room, quiet=True)
        register_owned_entity(room, owned)
        unowned = create_object(Monster, key="wandering_monster")
        unowned.move_to(room, quiet=True)

        events = reclaim_due_instances(0, 100)
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )
        self.assertFalse(Monster.objects.filter(id=owned.id).exists())
        self.assertTrue(Monster.objects.filter(id=unowned.id).exists())
        self.assertEqual(
            unowned.location.dbref,
            settings.DEFAULT_HOME,
        )

    @covers_requirement("instance-reclamation::reclaim-due-instances-despawns-owned-entities-and-relocates-unowned-ones-before-reclaiming-a-room")
    @covers_requirement("instance-reclamation::register-owned-entity-marks-an-entity-for-despawn-not-relocation-on-reclaim")
    def test_reclaimed_room_clears_entities_before_own_delete(self):
        # Both a registered and an unregistered NPC have left the room's
        # contents by the time the room's own delete runs -- observed by the
        # typeclass safety net never seeing a still-present NPC.
        room = _due_room("clear_order")
        owned = create_object(NPC, key="owned_npc")
        owned.move_to(room, quiet=True)
        register_owned_entity(room, owned)
        unowned = create_object(NPC, key="unowned_npc")
        unowned.move_to(room, quiet=True)

        with patch("typeclasses.rooms.InstanceRoom.at_object_delete", return_value=True) as guard:
            reclaim_due_instances(0, 100)
            guard.assert_called()
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertFalse(NPC.objects.filter(id=owned.id).exists())
        self.assertTrue(NPC.objects.filter(id=unowned.id).exists())

    def test_promoted_room_skipped_on_subsequent_call(self):
        room = _due_room("once_promoted", named=True, interacted=True)
        first = reclaim_due_instances(0, 100)
        self.assertIn(
            ScheduledEvent("instance_promoted", 100, {"room": room.key}),
            first,
        )
        second = reclaim_due_instances(0, 100)
        self.assertNotIn(room.key, [event.payload.get("room") for event in second])

    def test_returned_events_have_json_compatible_payloads(self):
        rooms = [_due_room(f"payload_room_{i}") for i in range(3)]
        rooms[1].db.pin_reasons = [BLOCKING_PIN]
        rooms[2].db.named = True
        rooms[2].db.interacted = True
        events = reclaim_due_instances(0, 100)
        for event in events:
            json.dumps({"payload": event.payload, "kind": event.kind, "due": event.due_tick})

    def test_delete_refused_by_safety_net_emits_deferred_not_raise(self):
        room = _due_room("stubborn")
        with patch("typeclasses.rooms.InstanceRoom.at_object_delete", return_value=False):
            events = reclaim_due_instances(0, 100)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaim_deferred", 100, {"room": room.key}),
            events,
        )

    def test_delete_refused_by_safety_net_leaves_entities_and_owned_registry_intact(self):
        # The defense-in-depth hook can refuse even a due, unpinned,
        # unoccupied room. A refused delete must defer with no entity clearing:
        # the pre-flight at_object_delete() check runs before any NPC is
        # despawned or relocated, so deferral is side-effect-free (rubber-duck
        # review).
        room = _due_room("stubborn_owned")
        owned = create_object(NPC, key="owned_npc_deferred")
        owned.move_to(room, quiet=True)
        register_owned_entity(room, owned)
        unowned = create_object(NPC, key="unowned_npc_deferred")
        unowned.move_to(room, quiet=True)

        with patch("typeclasses.rooms.InstanceRoom.at_object_delete", return_value=False):
            events = reclaim_due_instances(0, 100)
        self.assertIn(
            ScheduledEvent("instance_reclaim_deferred", 100, {"room": room.key}),
            events,
        )
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertTrue(NPC.objects.filter(id=owned.id).exists())
        self.assertTrue(NPC.objects.filter(id=unowned.id).exists())
        self.assertIn(owned, [o for o in room.contents if isinstance(o, LivingEntity)])
        self.assertIn(unowned, [o for o in room.contents if isinstance(o, LivingEntity)])
        self.assertIn(owned, room.db.owned_entities)


class ReclaimDeferredReevalTests(EvenniaTest):
    def test_deferred_room_is_reevaluated_once_unblocked(self):
        room = _due_room("deferred_then_free")
        self.char1.move_to(room, quiet=True)
        first = reclaim_due_instances(0, 100)
        self.assertIn(
            ScheduledEvent("instance_reclaim_deferred", 100, {"room": room.key}),
            first,
        )
        # The player leaves before the next pass; no pin, unnamed -> reclaimed.
        self.char1.move_to(self.room1, quiet=True)
        second = reclaim_due_instances(0, 100)
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            second,
        )
