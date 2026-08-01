"""Integration tests for the grid and terrain room typeclasses (map-anchor-grid, map-wilderness)."""

from evennia.contrib.grid.wilderness.wilderness import WildernessRoom
from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import (
    AnchorRoom,
    GridRoom,
    Room,
    SceneArchetypeMixin,
    TerrainRoom,
)


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


class SceneArchetypeTests(EvenniaTest):
    def test_mixin_is_in_both_room_mros(self):
        self.assertIn(SceneArchetypeMixin, GridRoom.__mro__)
        self.assertIn(SceneArchetypeMixin, TerrainRoom.__mro__)
        self.assertNotIn("scene_archetype", GridRoom.__dict__)

    def test_terrain_room_mro_excludes_xyzroom(self):
        self.assertIn(WildernessRoom, TerrainRoom.__mro__)
        self.assertNotIn(XYZRoom, TerrainRoom.__mro__)

    def test_terrain_room_defaults_scene_archetype_to_none(self):
        room = create_object(TerrainRoom, key="terrain_room")
        self.assertIsNone(room.scene_archetype)
        room.scene_archetype = "arbitrary_string"
        self.assertEqual(room.scene_archetype, "arbitrary_string")

    def test_grid_and_terrain_rooms_share_identical_attribute_contract(self):
        grid = create_object(GridRoom, key="grid_room")
        terrain = create_object(TerrainRoom, key="terrain_room_2")
        self.assertIsNone(grid.scene_archetype)
        self.assertIsNone(terrain.scene_archetype)
        grid.scene_archetype = "western_hills_valleys_plains"
        terrain.scene_archetype = "western_hills_valleys_plains"
        self.assertEqual(grid.scene_archetype, terrain.scene_archetype)