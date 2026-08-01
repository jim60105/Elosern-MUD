"""Resolution checks for the module-level room prototypes (map-anchor-grid)."""

import unittest

from evennia.utils.utils import class_from_module

from world.prototypes import ANCHOR_ROOM, GRID_ROOM


class PrototypeResolutionTests(unittest.TestCase):
    def test_grid_room_prototype_resolves_to_grid_room_typeclass(self):
        self.assertEqual(GRID_ROOM["typeclass"], "typeclasses.rooms.GridRoom")
        typeclass = class_from_module(GRID_ROOM["typeclass"])
        self.assertEqual(typeclass.__name__, "GridRoom")

    def test_anchor_room_prototype_resolves_to_anchor_room_typeclass(self):
        self.assertEqual(ANCHOR_ROOM["typeclass"], "typeclasses.rooms.AnchorRoom")
        typeclass = class_from_module(ANCHOR_ROOM["typeclass"])
        self.assertEqual(typeclass.__name__, "AnchorRoom")