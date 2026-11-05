"""Shared wilderness fixture for the area-map test package."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.rooms import Room
from world.tests.geography_fixture import sync_test_settlements, sync_test_wilderness
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import record_arrival
from ..test_local_map._support import EAST_APPROACH, _live
from ._support import _render, _wilderness_fixture_maps, _knowledge


class _WildernessFixture(EvenniaTest):
    """One provisioned wilderness world per test; the subclasses carry the journeys."""

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        declared = _wilderness_fixture_maps()
        sync_test_settlements(declared)
        sync_test_wilderness(declared)
        get_world_clock()
    def _at_wild(self, coordinates):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

        name = _live("world.maps.wilderness_provider", "WILDERNESS_NAME")
        self.assertTrue(enter_wilderness(self.char1, coordinates=coordinates, name=name))
        record_arrival(self.char1)
    def _pin(self, visits, visited_grid=()):
        from world.rules.map_knowledge import KNOWLEDGE_ATTR

        self.char1.attributes.add(KNOWLEDGE_ATTR, _knowledge(visits, visited_grid))
    def _away(self):
        ex, ey = EAST_APPROACH
        return (ex + 10, ey + 5)
    def _lit_overview(self, start, radius=2):
        from world.lore import map_districts

        district_at = _live("world.maps.district_partition", "district_at")
        key = district_at(start)
        self.assertIsNotNone(key)
        landmark = map_districts.landmark_node_ids()[key]
        self._pin({start: radius}, visited_grid=(landmark,))
        return key, _render(self.char1)
