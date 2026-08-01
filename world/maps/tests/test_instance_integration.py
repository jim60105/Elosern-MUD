"""End-to-end integration tests for the full instance lifecycle
(map-instance tasks 10.1-10.3)."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC
from typeclasses.rooms import InstanceRoom, Room
from world.maps.instance import (
    pin_instance_room,
    register_instance_reclamation,
    register_owned_entity,
    spawn_instance_room,
    unpin_instance_room,
)
from world.rules import clock as clock_module
from world.rules.clock import AdvanceSource, get_world_clock

BLOCKING_PIN = "quest:1:stage:0"


class InstanceLifecycleIntegrationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        clock_module._EVENT_SOURCES.pop("instance_reclamation", None)
        register_instance_reclamation()
        self.origin_room = create_object(Room, key="origin")

    def tearDown(self):
        clock_module._EVENT_SOURCES.pop("instance_reclamation", None)
        super().tearDown()

    def _spawn(self, *, named, ttl_seconds=10, key="scenery"):
        return spawn_instance_room(
            self.origin_room,
            {"prototype_parent": "instance_room", "key": key},
            exit_key="into the mist",
            return_key="back",
            ttl_seconds=ttl_seconds,
            named=named,
        )

    def _enter_and_leave(self, room):
        forward = [e for e in self.origin_room.exits if e.key == "into the mist"][0]
        self.char1.move_to(forward.destination)
        self.assertIs(self.char1.location, room)
        backward = [e for e in room.exits if e.key == "back"][0]
        self.char1.move_to(backward.destination)
        self.assertIs(self.char1.location, self.origin_room)

    def _advance_to(self, room):
        clock = get_world_clock()
        needed = room.db.expire_tick - clock.tick + 1
        clock.advance(needed, AdvanceSource.COMMAND, [])

    def test_named_interacted_room_is_promoted_after_full_lifecycle(self):
        room = self._spawn(named=True)
        self._enter_and_leave(room)
        self.assertTrue(room.db.interacted)
        self._advance_to(room)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIsNone(room.db.expire_tick)

    def test_unnamed_room_is_reclaimed_and_origin_exit_removed(self):
        room = self._spawn(named=False)
        self._enter_and_leave(room)
        forward = [e for e in self.origin_room.exits if e.key == "into the mist"][0]
        self._advance_to(room)
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        # Evennia's clear_exits() removes the exit at origin pointing at it too.
        self.assertFalse(
            any(e.destination == room for e in self.origin_room.exits)
        )

    def test_pinned_room_with_npc_survives_until_unpin_then_reclaims(self):
        room = self._spawn(named=False)
        npc = create_object(NPC, key="scene_spawn")
        npc.move_to(room, quiet=True)
        register_owned_entity(room, npc)
        pin_instance_room(room, BLOCKING_PIN)

        # First advance: pinned and NPC present (no PlayerCharacter) -> deferred.
        self._advance_to(room)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertEqual(room.db.pin_reasons, [BLOCKING_PIN])

        # Stage completion: unpin, then a second advance reclaims and despawns.
        unpin_instance_room(room, BLOCKING_PIN)
        clock = get_world_clock()
        clock.advance(1, AdvanceSource.COMMAND, [])
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertFalse(NPC.objects.filter(id=npc.id).exists())