"""Tests for the art room-entry scene-asset hook (art-assets D7/D8)."""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import AnchorRoom, InstanceRoom
from world.art.store import ArtAssetRecord
from world.tests.synthetic_data import SYNTH_ARCHETYPES, synthetic_registries

from tools.spec_traceability import covers_requirement

# Two invented kit archetypes stand in for the shipped scene vocabulary the
# entry hook validates against.
_BAZAAR = "t_synth_bazaar"
_LODGE = "t_synth_lodge"
assert _BAZAAR in SYNTH_ARCHETYPES and _LODGE in SYNTH_ARCHETYPES


class ArtRoomEntryTests(EvenniaTestCase):
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
        with synthetic_registries("archetypes"):
            self._ensure_scene_asset_grid_room()

    def _ensure_scene_asset_grid_room(self):
        room, errors = AnchorRoom.create(key="art-anchor", xyz=(1, 1, "test_map"))
        self.assertEqual(errors, [])
        room.scene_archetype = _BAZAAR
        self._move(room)
        record = ArtAssetRecord.objects.filter(
            db_key=f"art:scene:{_BAZAAR}"
        ).first()
        self.assertIsNotNone(record)

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_entering_an_instance_room_ensures_its_asset(self):
        with synthetic_registries("archetypes"):
            self._ensure_instance_room_asset()

    def _ensure_instance_room_asset(self):
        room, errors = InstanceRoom.create(key="art-instance")
        self.assertEqual(errors, [])
        room.scene_archetype = _LODGE
        self._move(room)
        record = ArtAssetRecord.objects.filter(
            db_key=f"art:scene:{_LODGE}"
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
        with synthetic_registries("archetypes"):
            self._movement_survives_art_failure()

    def _movement_survives_art_failure(self):
        room, errors = AnchorRoom.create(key="art-failing", xyz=(3, 3, "test_map"))
        self.assertEqual(errors, [])
        room.scene_archetype = _BAZAAR
        with patch(
            "world.art.service.queue_ensure",
            side_effect=RuntimeError("art boom"),
        ):
            self._move(room)
        self.assertEqual(self.player.location, room)


if __name__ == "__main__":
    import unittest

    unittest.main()
