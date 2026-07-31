"""Integration tests for the grid room typeclasses (map-anchor-grid)."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import AnchorRoom, GridRoom, Room


class GridRoomTypeclassTests(EvenniaTest):
    def test_grid_room_create_exposes_xyz_and_default_scene_archetype(self):
        room, errors = GridRoom.create(key="test", xyz=(9, 9, "test_map"))
        self.assertEqual(errors, [])
        self.assertEqual(room.xyz, (9, 9, "test_map"))
        self.assertIsNone(room.scene_archetype)

    def test_scene_archetype_set_without_registry_lookup_and_persists(self):
        room, _ = GridRoom.create(key="test", xyz=(9, 9, "test_map"))
        room.scene_archetype = "tavern_interior"
        refetched = GridRoom.objects.get(id=room.id)
        self.assertEqual(refetched.scene_archetype, "tavern_interior")

    def test_anchor_room_inherits_grid_room_behavior(self):
        anchor, errors = AnchorRoom.create(key="test", xyz=(8, 8, "test_map"))
        self.assertEqual(errors, [])
        self.assertEqual(anchor.xyz, (8, 8, "test_map"))
        self.assertIsNone(anchor.scene_archetype)
        self.assertIsNone(anchor.anchor_key)
        self.assertIsInstance(anchor, GridRoom)

    def test_anchor_room_does_not_validate_anchor_key(self):
        anchor, _ = AnchorRoom.create(key="test", xyz=(8, 8, "test_map"))
        anchor.anchor_key = "does_not_exist"
        self.assertEqual(anchor.anchor_key, "does_not_exist")

    def test_stock_room_is_unchanged(self):
        room = create_object(Room, key="stock_room")
        self.assertNotIsInstance(room, GridRoom)
        self.assertFalse(hasattr(room, "scene_archetype"))
        self.assertFalse(hasattr(room, "anchor_key"))