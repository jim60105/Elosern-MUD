"""Tests for the art room-entry scene-asset hook (art-assets D7/D8)."""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import AnchorRoom, InstanceRoom
from world.art.store import ArtAssetRecord

from tools.spec_traceability import covers_requirement


class ArtRoomEntryTests(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="art-mover")
        self.player.age = 22
        self.player.apparent_age = 22

    def _move(self, room):
        self.player.move_to(room, quiet=True)

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_entering_a_scene_bearing_grid_room_ensures_its_asset(self):
        room, errors = AnchorRoom.create(key="art-anchor", xyz=(1, 1, "test_map"))
        self.assertEqual(errors, [])
        room.scene_archetype = "tavern_interior"
        self._move(room)
        record = ArtAssetRecord.objects.filter(
            db_key="art:scene:tavern_interior"
        ).first()
        self.assertIsNotNone(record)

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_entering_an_instance_room_ensures_its_asset(self):
        room, errors = InstanceRoom.create(key="art-instance")
        self.assertEqual(errors, [])
        room.scene_archetype = "forest_path"
        self._move(room)
        record = ArtAssetRecord.objects.filter(
            db_key="art:scene:forest_path"
        ).first()
        self.assertIsNotNone(record)

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_room_without_a_resolvable_archetype_is_a_noop(self):
        room, errors = AnchorRoom.create(key="art-plain", xyz=(2, 2, "test_map"))
        self.assertEqual(errors, [])
        self._move(room)
        self.assertEqual(ArtAssetRecord.objects.count(), 0)

    @covers_requirement("art-asset-lifecycle::queue-failure-never-rolls-back-gameplay")
    def test_art_failure_during_movement_leaves_the_move_committed(self):
        room, errors = AnchorRoom.create(key="art-failing", xyz=(3, 3, "test_map"))
        self.assertEqual(errors, [])
        room.scene_archetype = "tavern_interior"
        with patch(
            "world.art.service.queue_ensure",
            side_effect=RuntimeError("art boom"),
        ):
            self._move(room)
        self.assertEqual(self.player.location, room)


if __name__ == "__main__":
    import unittest

    unittest.main()
