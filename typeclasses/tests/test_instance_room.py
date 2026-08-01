"""Integration tests for the InstanceRoom typeclass (map-instance, tasks 2.4-2.8)."""

from tools.spec_traceability import covers_requirement

from evennia.contrib.grid.wilderness.wilderness import WildernessRoom
from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import InstanceRoom, SceneArchetypeMixin


class InstanceRoomTypeclassTests(EvenniaTest):
    def test_mro_includes_mixin_and_excludes_coordinate_bases(self):
        self.assertIn(SceneArchetypeMixin, InstanceRoom.__mro__)
        self.assertNotIn(XYZRoom, InstanceRoom.__mro__)
        self.assertNotIn(WildernessRoom, InstanceRoom.__mro__)
        self.assertFalse(hasattr(InstanceRoom, "xyz"))

    @covers_requirement("instance-room-typeclass::instanceroom-carries-no-coordinate-and-adopts-scenearchetypemixin")
    @covers_requirement("grid-room-typeclasses::instanceroom-is-not-forward-declared-by-this-change")
    def test_scene_archetype_seam_matches_sibling_rooms(self):
        room = create_object(InstanceRoom, key="instance")
        self.assertIsNone(room.scene_archetype)
        room.scene_archetype = "cave_chamber"
        refetched = InstanceRoom.objects.get(id=room.id)
        self.assertEqual(refetched.scene_archetype, "cave_chamber")

    def test_freshly_created_room_has_no_location(self):
        room = create_object(InstanceRoom, key="floating")
        self.assertIsNone(room.location)

    def test_six_persistent_attributes_default_correctly(self):
        room = create_object(InstanceRoom, key="defaults")
        self.assertIsNone(room.db.expire_tick)
        self.assertFalse(room.db.named)
        self.assertFalse(room.db.interacted)
        self.assertEqual(room.db.pin_reasons, [])
        self.assertEqual(room.db.owned_entities, [])
        self.assertIsNone(room.db.origin_room)

    @covers_requirement("instance-room-typeclass::instanceroom-persists-expire-tick-named-interacted-pin-reasons-owned-entities-and-origin-room")
    def test_six_attributes_persist_across_refetch(self):
        room = create_object(InstanceRoom, key="persist")
        room.db.expire_tick = 12345
        room.db.named = True
        room.db.interacted = True
        room.db.pin_reasons = ["quest:1:stage:0"]
        room.db.owned_entities = [self.obj1]
        room.db.origin_room = self.room1
        refetched = InstanceRoom.objects.get(id=room.id)
        self.assertEqual(refetched.db.expire_tick, 12345)
        self.assertTrue(refetched.db.named)
        self.assertTrue(refetched.db.interacted)
        self.assertEqual(refetched.db.pin_reasons, ["quest:1:stage:0"])
        self.assertEqual(refetched.db.owned_entities, [self.obj1])
        self.assertEqual(refetched.db.origin_room, self.room1)

    @covers_requirement("instance-room-typeclass::at-object-receive-sets-interacted-to-true-the-first-time-a-playercharacter-enters")
    def test_at_object_receive_sets_interacted_for_player_only(self):
        room = create_object(InstanceRoom, key="receive")

        npc = create_object(NPC, key="npc_recv")
        room.at_object_receive(npc, self.room1)
        self.assertFalse(room.db.interacted)

        monster = create_object(Monster, key="monster_recv")
        room.at_object_receive(monster, self.room1)
        self.assertFalse(room.db.interacted)

        room.at_object_receive(self.char1, self.room1)
        self.assertTrue(room.db.interacted)

    def test_interacted_never_unsets_once_true(self):
        room = create_object(InstanceRoom, key="sticky")
        room.db.interacted = True
        room.at_object_receive(self.char1, self.room1)
        self.assertTrue(room.db.interacted)

    @covers_requirement("instance-room-typeclass::at-object-delete-refuses-deletion-while-a-playercharacter-is-present-or-the-room-is-pinned")
    def test_deletion_refused_while_pinned(self):
        room = create_object(InstanceRoom, key="pinned")
        room.db.pin_reasons = ["quest:1:stage:0"]
        result = room.delete()
        self.assertFalse(result)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())

    def test_deletion_refused_while_player_character_present(self):
        room = create_object(InstanceRoom, key="occupied")
        self.char1.move_to(room, quiet=True)
        result = room.delete()
        self.assertFalse(result)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())

    def test_deletion_not_refused_for_npc_or_monster_alone(self):
        for typeclass, key in ((NPC, "npc_only"), (Monster, "monster_only")):
            with self.subTest(key=key):
                room = create_object(InstanceRoom, key=key)
                occupant = create_object(typeclass, key=key + "_occupant")
                occupant.move_to(room, quiet=True)
                result = room.delete()
                self.assertTrue(result)
                self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())

    def test_deletion_succeeds_when_unpinned_and_unoccupied(self):
        room = create_object(InstanceRoom, key="empty")
        result = room.delete()
        self.assertTrue(result)
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
