"""Data-contract test: map bootstrap/gate data contract

Shared derived constants and cooperative bases for the split bootstrap
suites. This module holds no tests of its own.
"""

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import GridRoom
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.city_gates import CITY_GATE_REGISTRY
from world.maps.limbo import LIMBO_KEY
from world.maps.map_data import SETTLEMENT_GRAPHS
from world.maps.static_references import settlement_node_xyz
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.geography_fixture import publish_shipped_geography


publish_shipped_geography()

_CAPITAL_ENTRY = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
_VILLAGE_ENTRY = WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
SOUTH_GATE_XYZ = settlement_node_xyz(_CAPITAL_ENTRY.gate_for("n").destination)
EAST_GATE_XYZ = settlement_node_xyz(_CAPITAL_ENTRY.gate_for("w").destination)

#: The capital/village pair every cross-settlement fixture in this module needs.
#: Selector ids are settlement map ids, never entry anchor/location identities.
CAPITAL_MAP_IDS = (_CAPITAL_ENTRY.gate_for("w").destination.map_id,)
VILLAGE_MAP_IDS = (_VILLAGE_ENTRY.gate_for("n").destination.map_id,)
CAPITAL_VILLAGE_MAP_IDS = tuple(sorted({*CAPITAL_MAP_IDS, *VILLAGE_MAP_IDS}))
SELECTED_GATE_ROW_COUNT = sum(
    1
    for row in CITY_GATE_REGISTRY.values()
    if row.gate.map_id in CAPITAL_VILLAGE_MAP_IDS
)
#: The map ids the starting-room bridge rows would materialize.
CITY_GATE_MAP_IDS = tuple(
    sorted({row.gate.map_id for row in CITY_GATE_REGISTRY.values()})
)
#: The destination maps of every registered wilderness gate.
WILDERNESS_GATE_MAP_IDS = tuple(
    sorted(
        {
            gate.destination.map_id
            for entry in WILDERNESS_ENTRY_REGISTRY.values()
            for gate in entry.gates
        }
    )
)
#: The maps carrying an authored anchor placement.
ANCHOR_PLACEMENT_MAP_IDS = tuple(
    sorted({placement.zcoord for placement in ANCHOR_PLACEMENT_REGISTRY.values()})
)


def _declared_road_count(settlement_ids):
    """The authored directed-road count of the declared settlements."""

    return sum(len(SETTLEMENT_GRAPHS[map_id].edges) for map_id in settlement_ids)


def _declared_node_count(settlement_ids):
    """The authored node count of the declared settlements."""

    return sum(len(SETTLEMENT_GRAPHS[map_id].nodes) for map_id in settlement_ids)


def _approach(return_direction):
    from elosern_map_core.authoring import gate_approach_cell
    from world.maps import geography
    from world.maps.map_data import current

    document = current().settlements["capital_altoria"]
    cell = geography.current().locations.locations["capital_altoria"].cell
    return gate_approach_cell(document.wilderness_geometry(cell), return_direction)


class _GridBootstrapCase(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    """Grid bootstrap tests.

    ``at_server_start()`` runs the full startup synchronization (including
    ``sync_guild_economy()``), so the process-global registries are snapshotted
    and restored around every test.
    """

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()

    def _count_grid_rooms(self):
        return GridRoom.objects.all_family().count()

    def _count_city_exits(self):
        # all_family() counts CostedXYZExit (map-movement-clock) as well as bare
        # XYZExit, so this stays a count of intra-city exits after the wildcard
        # prototype override changes their exact typeclass.
        from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit

        return XYZExit.objects.all_family().count()

    def _bridging_exits(self):
        # A bridging exit is one that touches the starting room itself. The
        # south gate room may legitimately carry other exits once the boot
        # runs sync_wilderness() (the per-gate 荒野 gate provisioning); the
        # south gate is only resolved here as the bridge's far end, never as
        # a counting target in its own right.
        limbo = search_object(LIMBO_KEY, exact=True)
        targets = [limbo[0]] if limbo else []
        return [
            exit_obj
            for exit_obj in Exit.objects.all()
            if exit_obj.location in targets or exit_obj.destination in targets
        ]


class _WildernessBootstrapCase(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    """Wilderness bootstrap tests (``at_server_start()`` mutates the shared
    registries, so they are snapshotted and restored around every test)."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()

    def _count_grid_rooms(self):
        return GridRoom.objects.all_family().count()

    def _east_gate(self):
        return GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()

    def _south_gate(self):
        return GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()

    def _gate_exits(self, gate=None):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        gate = gate if gate is not None else self._east_gate()
        gates = [e for e in gate.exits if isinstance(e, WildernessGateExit)]
        return script, gates
