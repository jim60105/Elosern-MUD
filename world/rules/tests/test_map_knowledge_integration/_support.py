"""Shared fixture for the map-knowledge test package."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.exits import WildernessGateExit
from typeclasses.rooms import GridRoom, Room
from world.tests.geography_fixture import sync_test_settlements, sync_test_wilderness
from world.maps import wilderness_provider
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.maps.static_references import settlement_node_xyz
from world.rules.map_knowledge import KnowledgeError, parse_knowledge
from .._knowledge_probes import live_city_gate_registry, live_map_key, live_wilderness_entry_registry


def _entry_with_west_gate_on(map_key: str):
    """The wilderness entry whose west-returning gate lands on ``map_key``."""
    for entry in live_wilderness_entry_registry().values():
        gate = entry.gate_for("w")
        if gate is not None and gate.z_map_key == map_key:
            return entry, gate
    raise AssertionError(f"no wilderness entry gate returns to map {map_key!r}")


def _grid_node(room) -> str:
    """The canonical grid node ID of a booted GridRoom, from its own xyz."""
    x, y, z = room.xyz
    return f"grid:{z}:{x}:{y}"


def _knowledge(character):
    try:
        return parse_knowledge(character)
    except KnowledgeError:
        return []


def _node_ids(character):
    return {visit.node_id for visit in _knowledge(character)}

class _MapKnowledgeFixture(EvenniaTest):
    """One provisioned map world per seam journey."""
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key="虛境", location=None)
        # Resolve the map vocabulary before provisioning: every journey here
        # crosses the one map's own gates, so only that settlement and its
        # wilderness ground carry an initial population.
        self.map = live_map_key()
        sync_test_settlements((self.map,))
        sync_test_wilderness((self.map,))
        self.gate_row = live_city_gate_registry()[self.map]
        # The city-gate row's own identity is the south gate room's
        # coordinate — read from the live registry, not a shipped constant.
        self.south_gate_xyz = settlement_node_xyz(self.gate_row.gate)
        entry, west_row = _entry_with_west_gate_on(self.map)
        self.east_gate_xyz = settlement_node_xyz(west_row.destination)
        self.entry_xy = entry.approach_cell(west_row)
        self.wild = getattr(wilderness_provider, "WILDERNESS_NAME")
        self.east_gate = GridRoom.objects.filter_xyz(xyz=self.east_gate_xyz).first()
        self.south_gate = GridRoom.objects.filter_xyz(xyz=self.south_gate_xyz).first()
        self.gate = [e for e in self.east_gate.exits if isinstance(e, WildernessGateExit)][0]
    def _exit(self, direction):
        return [e for e in self.char1.location.exits if e.key == direction][0]
