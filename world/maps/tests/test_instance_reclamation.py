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


class ReclaimKnowledgePruneTests(EvenniaTest):
    """Map-knowledge pruning inside the reclaim transaction (map-knowledge-minimap D4)."""

    def _due_room(self, key):
        room = create_object(InstanceRoom, key=key)
        room.db.expire_tick = 50
        room.db.named = False
        room.db.interacted = False
        return room

    def _knowledge(self, character):
        from world.rules.map_knowledge import KnowledgeError, parse_knowledge

        try:
            return {visit.node_id for visit in parse_knowledge(character)}
        except KnowledgeError:
            return set()

    @covers_requirement("instance-reclamation::reclaim-due-instances-deletes-rooms-that-are-due-unblocked-and-not-promotable")
    def test_reclaim_removes_room_node_from_affected_player_in_same_transaction(self):
        room = self._due_room("prune_transaction")
        self.char1.attributes.add(
            "map_knowledge",
            {
                "schema_version": 1,
                "visited": {
                    f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20},
                    f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30},
                },
            },
        )
        events = reclaim_due_instances(0, 100)
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )
        self.assertNotIn(f"room:{room.id}", self._knowledge(self.char1))
        self.assertIn(f"room:{self.room1.id}", self._knowledge(self.char1))

    def test_unrelated_players_are_untouched_by_reclaim_prune(self):
        room = self._due_room("prune_unrelated")
        self.char1.attributes.add(
            "map_knowledge",
            {
                "schema_version": 1,
                "visited": {
                    f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30}
                },
            },
        )
        reclaim_due_instances(0, 100)
        self.assertNotIn(f"room:{room.id}", self._knowledge(self.char1))
        self.assertIn(f"room:{self.room1.id}", self._knowledge(self.char1))

    def test_character_without_knowledge_attribute_stays_without_one(self):
        room = self._due_room("prune_no_attr")
        self.assertFalse(self.char1.attributes.has("map_knowledge"))
        reclaim_due_instances(0, 100)
        self.assertFalse(self.char1.attributes.has("map_knowledge"))

    @covers_requirement("instance-reclamation::reclaim-due-instances-deletes-rooms-that-are-due-unblocked-and-not-promotable")
    def test_promoted_room_retains_visited_identity(self):
        room = self._due_room("prune_promoted")
        room.db.named = True
        room.db.interacted = True
        self.char1.attributes.add(
            "map_knowledge",
            {
                "schema_version": 1,
                "visited": {
                    f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20}
                },
            },
        )
        events = reclaim_due_instances(0, 100)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIsNone(room.db.expire_tick)
        self.assertIn(
            ScheduledEvent("instance_promoted", 100, {"room": room.key}),
            events,
        )
        self.assertIn(f"room:{room.id}", self._knowledge(self.char1))

    def test_prune_runs_before_entity_or_room_mutation(self):
        from typeclasses.npcs import NPC

        room = self._due_room("prune_order")
        npc = create_object(NPC, key="left_behind")
        npc.move_to(room, quiet=True)
        self.char1.attributes.add(
            "map_knowledge",
            {
                "schema_version": 1,
                "visited": {f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20}},
            },
        )
        from world.rules import map_knowledge as map_knowledge_module

        order = []

        def recording_prune(room_id):
            order.append("prune")

        def recording_clear(room_obj):
            order.append("clear")
            # Mirror the real clearing so the room can still be deleted.
            from typeclasses.entities import LivingEntity

            for entity in list(room_obj.contents):
                if isinstance(entity, LivingEntity):
                    entity.delete()

        def recording_delete(self_obj):
            if self_obj is room:
                order.append("delete")
            return True

        with patch.object(
            map_knowledge_module, "prune_reclaimed_room", side_effect=recording_prune
        ), patch(
            "world.maps.instance._clear_non_player_entities", side_effect=recording_clear
        ), patch(
            "evennia.objects.objects.DefaultObject.delete", recording_delete
        ):
            events = reclaim_due_instances(0, 100)
        self.assertEqual(order, ["prune", "clear", "delete"])
        self.assertIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )

    @covers_requirement("instance-reclamation::reclaim-due-instances-deletes-rooms-that-are-due-unblocked-and-not-promotable")
    def test_prune_failure_rolls_back_delete_and_defers_room(self):
        room = self._due_room("prune_failure")
        from world.rules.map_knowledge import KnowledgePruneError

        def boom(room_id):
            raise KnowledgePruneError("injected persistence failure")

        with patch(
            "world.rules.map_knowledge.prune_reclaimed_room", side_effect=boom
        ):
            events = reclaim_due_instances(0, 100)
        # The transaction rolled back before any entity/room mutation.
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaim_deferred", 100, {"room": room.key}),
            events,
        )
        self.assertNotIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )

    @covers_requirement("instance-reclamation::reclaim-due-instances-deletes-rooms-that-are-due-unblocked-and-not-promotable")
    def test_real_write_failure_restores_player_knowledge_in_memory(self):
        # A genuine write failure (not a mocked prune) inside the reclaim
        # transaction must leave the player's in-memory knowledge consistent
        # with the pre-reclaim value after the rollback. Evennia's Attribute
        # ``value`` setter assigns ``db_value`` in-memory before ``save()``
        # runs, so the prune module's own snapshot restore repairs the cache
        # even when the restore save also fails -- the idmapper never diverges
        # from the rolled-back database (design D4).
        room = self._due_room("prune_real_failure")
        before = {
            "schema_version": 1,
            "visited": {
                f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20},
                f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30},
            },
        }
        self.char1.attributes.add("map_knowledge", before)
        from evennia.typeclasses.attributes import Attribute

        def disk_full(*args, **kwargs):
            raise RuntimeError("disk full")

        with patch.object(Attribute, "save", disk_full):
            events = reclaim_due_instances(0, 100)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaim_deferred", 100, {"room": room.key}),
            events,
        )
        self.assertNotIn(
            ScheduledEvent("instance_reclaimed", 100, {"room": room.key}),
            events,
        )
        self.assertEqual(self.char1.attributes.get("map_knowledge"), before)


class ReclaimRollbackCacheTests(EvenniaTest):
    """A rolled-back advance restores reclaimed-room state (F5).

    ``reclaim_due_instances`` deletes a due room, prunes ``map_knowledge``,
    and relocates unowned occupants; when a later persist fails, the
    ``instance_reclamation`` contract restores every surface in cache and
    storage, and a relocated occupant points back into the re-fetched
    (rolled-back) room rather than at a deleted object or ``None``.
    """

    def setUp(self):
        super().setUp()
        import world.rules.clock as clock_module

        self._sources = dict(clock_module._EVENT_SOURCES)

    def tearDown(self):
        import world.rules.clock as clock_module

        clock_module._EVENT_SOURCES.clear()
        clock_module._EVENT_SOURCES.update(self._sources)
        super().tearDown()

    def _raw_attribute(self, obj, key):
        row = (
            obj.db_attributes.through.objects.filter(
                objectdb_id=obj.pk, attribute__db_key=key
            )
            .values_list("attribute__db_value", flat=True)
            .first()
        )
        return None if row is None else row

    @covers_requirement("world-clock::a-rolled-back-advance-restores-every-callback-owned-surface-not-just-caller-entities")
    def test_failing_persist_restores_reclaimed_room_knowledge_and_occupants(self):
        from evennia.utils.search import search_script
        from world.maps.instance import register_instance_reclamation
        from world.rules.clock import AdvanceSource, get_world_clock

        room = create_object(InstanceRoom, key="rollback_reclaim")
        room_id = int(room.pk)
        room.db.expire_tick = 50
        room.db.named = False
        room.db.interacted = False
        # An NAttribute makes ``at_idmapper_flush`` refuse the deleted
        # instance's eviction, so the restore must flush the stale entry
        # before the next fetch re-reads the rolled-back rows.
        room.ndb.survivor = "kept across the rolled-back delete"
        npc = create_object(NPC, key="relocated_on_rollback")
        npc.move_to(room, quiet=True)
        before_knowledge = {
            "schema_version": 1,
            "visited": {
                f"room:{room_id}": {"first_seen_tick": 10, "last_seen_tick": 20},
                f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30},
            },
        }
        self.char1.attributes.add("map_knowledge", before_knowledge)
        before_surfaces = {
            "expire_tick": room.db.expire_tick,
            "named": room.db.named,
            "interacted": room.db.interacted,
            "pin_reasons": room.db.pin_reasons,
            "owned_entities": room.db.owned_entities,
        }
        self.char1.race = "human"
        self.char1.apply_race_baseline()

        register_instance_reclamation()
        clock = get_world_clock()
        before_tick = clock.tick
        script = search_script("world_clock")[0]

        def failing_persist(tick):
            script.db.tick = tick
            raise RuntimeError("simulated persist failure")

        clock._persist = failing_persist
        with self.assertRaises(RuntimeError):
            clock.advance(100, AdvanceSource.SKIP, [self.char1])

        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(script.db.tick, before_tick)
        # The deleted-then-rolled-back room re-fetches as a live object.
        self.assertTrue(InstanceRoom.objects.filter(id=room_id).exists())
        refetched = InstanceRoom.objects.get(id=room_id)
        self.assertIsNot(refetched, room)
        # Every surface matches its pre-advance value in cache and in the raw
        # Attribute rows (defaulted surfaces never gained a row).
        self.assertEqual(refetched.db.expire_tick, before_surfaces["expire_tick"])
        self.assertEqual(self._raw_attribute(refetched, "expire_tick"), before_surfaces["expire_tick"])
        self.assertEqual(refetched.db.named, before_surfaces["named"])
        self.assertEqual(self._raw_attribute(refetched, "named"), before_surfaces["named"])
        self.assertEqual(refetched.db.interacted, before_surfaces["interacted"])
        self.assertEqual(self._raw_attribute(refetched, "interacted"), before_surfaces["interacted"])
        self.assertEqual(refetched.db.pin_reasons, before_surfaces["pin_reasons"])
        self.assertEqual(self._raw_attribute(refetched, "pin_reasons"), before_surfaces["pin_reasons"])
        self.assertEqual(refetched.db.owned_entities, before_surfaces["owned_entities"])
        self.assertEqual(self._raw_attribute(refetched, "owned_entities"), before_surfaces["owned_entities"])
        # The pruned player knowledge is restored in cache and storage.
        self.assertEqual(self.char1.attributes.get("map_knowledge"), before_knowledge)
        self.assertEqual(self._raw_attribute(self.char1, "map_knowledge"), before_knowledge)
        # The relocated occupant points back into the re-fetched room.
        self.assertEqual(npc.location.pk, room_id)
        self.assertNotEqual(npc.location.dbref, settings.DEFAULT_HOME)
        self.assertIn(npc, refetched.contents)

    @covers_requirement("world-clock::a-rolled-back-advance-restores-every-callback-owned-surface-not-just-caller-entities")
    def test_successful_advance_commits_reclamation_with_tick(self):
        from world.maps.instance import register_instance_reclamation
        from world.rules.clock import AdvanceSource, get_world_clock

        room = create_object(InstanceRoom, key="committed_reclaim")
        room_id = int(room.pk)
        room.db.expire_tick = 50
        register_instance_reclamation()
        clock = get_world_clock()
        before_tick = clock.tick
        events = clock.advance(100, AdvanceSource.SKIP, [])
        self.assertIn(
            ScheduledEvent("instance_reclaimed", before_tick + 100, {"room": room.key}),
            events,
        )
        self.assertEqual(clock.tick, before_tick + 100)
        self.assertFalse(InstanceRoom.objects.filter(id=room_id).exists())
