"""Shared node-ID encoder tests.

Covers the byte-identical GridRoom / TerrainRoom / ordinary-room encodings
produced by ``node_id_for_location`` (the move adapter's ``stale_location``
compare and the move affordance builder share one derivation), the ``None``
case for a locationless actor, and the move adapter rejecting a payload whose
``current_node`` differs from what the encoder re-derives.
"""

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import GridRoom, Room, TerrainRoom
from web.webclient.actions.exploration_actions import (
    _current_node,
    _move_adapter,
)
from web.webclient.actions.node_ids import node_id_for_location
from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.map_knowledge import encode_grid, encode_room, encode_wild


class NodeIdEncoderTests(EvenniaTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sync_grid()

    def setUp(self):
        self.player = create_object(PlayerCharacter, key="節點測試")
        self.player.race = "human"
        self.player.apply_race_baseline()

    def test_ordinary_room_encodes_room_node(self):
        room = create_object(Room, key="城內", location=None)
        self.player.location = room
        expected = encode_room(int(room.pk))
        self.assertEqual(node_id_for_location(room), expected)
        self.assertEqual(_current_node(self.player), expected)

    def test_grid_room_encodes_grid_node(self):
        gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.assertIsNotNone(gate)
        self.player.location = gate
        expected = encode_grid(
            str(SOUTH_GATE_XYZ[2]), SOUTH_GATE_XYZ[0], SOUTH_GATE_XYZ[1]
        )
        self.assertEqual(node_id_for_location(gate), expected)
        self.assertEqual(_current_node(self.player), expected)

    def test_terrain_room_encodes_wild_node(self):
        terrain = create_object(TerrainRoom, key="荒野", location=None)
        terrain.ndb.active_coordinates = (7, 11)
        self.player.location = terrain
        expected = encode_wild(WILDERNESS_NAME, 7, 11)
        self.assertEqual(node_id_for_location(terrain), expected)
        self.assertEqual(_current_node(self.player), expected)

    def test_locationless_actor_yields_none(self):
        self.player.location = None
        self.assertIsNone(node_id_for_location(self.player.location))
        self.assertIsNone(_current_node(self.player))

    def test_coordinateless_terrain_yields_none(self):
        bare = create_object(TerrainRoom, key="霧區", location=None)
        self.assertIsNone(node_id_for_location(bare))
        self.player.location = bare
        self.assertIsNone(_current_node(self.player))

    def test_move_adapter_rejects_when_the_encoder_differs(self):
        room = create_object(Room, key="起點", location=None)
        destination = create_object(Room, key="目的地", location=None)
        from typeclasses.exits import Exit

        exit_obj = create_object(
            Exit, key="東", location=room, destination=destination
        )
        self.player.location = room
        result = _move_adapter(
            self.player,
            {
                "exit_ref": str(int(exit_obj.id)),
                "current_node": f"room:{int(room.pk) + 1}",
            },
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "stale_location")
        self.assertIs(self.player.location, room)


if __name__ == "__main__":
    unittest.main()
