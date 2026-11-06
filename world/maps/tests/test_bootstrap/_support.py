"""Shared fixtures and helpers for the bootstrap test package.

Not discovered as tests (the file is not named ``test*``): it holds the
synthetic graphs, spies and constants the grid and settlement modules share.
"""

from tools.spec_traceability import covers_requirement

import inspect
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaTest

from server.conf.at_server_startstop import at_server_start
from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import AnchorRoom, GridRoom, Room
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.maps.city_gates import CITY_GATE_REGISTRY, CityGateDef
from world.maps.bootstrap import SyncReport, sync_grid, sync_limbo, sync_wilderness
from world.maps.limbo import LIMBO_ALIAS, LIMBO_DESC, LIMBO_KEY, LIMBO_LEGACY_KEY
from world.maps.map_data import SETTLEMENT_GRAPHS
from world.maps.static_references import (
    StaticReferenceError,
    anchor_entrance_xyz,
    place_exterior_xyz,
    settlement_node_xyz,
)
from elosern_map_core.references import settlement_node_ref
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.geography_fixture import (
    publish_shipped_geography,
    selected_startup_settlements,
    sync_test_settlements,
    sync_test_wilderness,
)
from world.maps.tests._bootstrap_fixtures import (
    ANCHOR_PLACEMENT_MAP_IDS,
    CAPITAL_MAP_IDS,
    CAPITAL_VILLAGE_MAP_IDS,
    CITY_GATE_MAP_IDS,
    EAST_GATE_XYZ,
    SELECTED_GATE_ROW_COUNT,
    SOUTH_GATE_XYZ,
    VILLAGE_MAP_IDS,
    WILDERNESS_GATE_MAP_IDS,
    _GridBootstrapCase,
    _WildernessBootstrapCase,
    _approach,
    _declared_node_count,
    _declared_road_count,
)


SYNTHETIC_MAP_KEY = "t_sparse_settlement"


def _synthetic_node(node_id, coordinate, key):
    from elosern_map_core.sparse import SparseNode

    return SparseNode(
        node_id=node_id,
        x=coordinate[0],
        y=coordinate[1],
        prototype={"prototype_parent": "grid_room", "key": key},
    )


def _synthetic_graph(start_coordinate, north_coordinate):
    from elosern_map_core.sparse import SparseRoad, SparseSettlementGraph

    return SparseSettlementGraph(
        SYNTHETIC_MAP_KEY,
        [
            _synthetic_node("start", start_coordinate, "測試起點"),
            _synthetic_node("north", north_coordinate, "測試北端"),
        ],
        [
            SparseRoad("start>north", "start", "north"),
            SparseRoad("north>start", "north", "start"),
        ],
        exit_prototype={
            "prototype_parent": "xyz_exit",
            "typeclass": "typeclasses.exits.CostedXYZExit",
        },
    )


def _synthetic_graph_for(map_id, start_coordinate, north_coordinate):
    """One invented sparse graph in its own map coordinate space."""

    from elosern_map_core.sparse import SparseRoad, SparseSettlementGraph

    return SparseSettlementGraph(
        map_id,
        [
            _synthetic_node("start", start_coordinate, f"測試{map_id}起點"),
            _synthetic_node("north", north_coordinate, f"測試{map_id}北端"),
        ],
        [
            SparseRoad("start>north", "start", "north"),
            SparseRoad("north>start", "north", "start"),
        ],
        exit_prototype={
            "prototype_parent": "xyz_exit",
            "typeclass": "typeclasses.exits.CostedXYZExit",
        },
    )


class _SynchronizerSpy:
    """Record which graphs reach the real planner and writer, keeping them real."""

    def __enter__(self):
        from world.maps import bootstrap

        self._bootstrap = bootstrap
        self._real_plan = bootstrap._plan_settlement_graph
        self._real_apply = bootstrap._apply_graph_plan
        self.planned = []
        self.applied = []

        def plan(graph):
            self.planned.append(graph.map_id)
            return self._real_plan(graph)

        def apply(plan, knowledge_journal=None):
            self.applied.append(plan.graph.map_id)
            return self._real_apply(plan, knowledge_journal)

        self._plan_patch = patch.object(
            bootstrap, "_plan_settlement_graph", side_effect=plan
        )
        self._apply_patch = patch.object(
            bootstrap, "_apply_graph_plan", side_effect=apply
        )
        self._plan_patch.start()
        self._apply_patch.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self._apply_patch.stop()
        self._plan_patch.stop()
        return False


OLD_COORDINATES = {
    "capital_altoria": {
        "south_gate": (3, 0),
        "quay": (1, 1),
        "riverbank_road": (2, 1),
        "south_avenue": (3, 1),
        "inn_lane": (4, 1),
        "bath_forecourt": (5, 1),
        "old_wall_ruins": (2, 2),
        "north_avenue": (3, 2),
        "craft_alley": (1, 3),
        "market_street": (2, 3),
        "central_plaza": (3, 3),
        "guild_forecourt": (4, 3),
        "east_market": (5, 3),
        "east_gate": (6, 3),
        "training_ground": (2, 4),
        "holy_steps": (3, 4),
        "great_temple": (4, 4),
        "noble_quarter": (3, 5),
        "upper_gate": (4, 5),
        "academy": (5, 5),
        "palace_forecourt": (4, 6),
    },
    "village_ciaran": {
        "hidden_path": (0, 1),
        "village_plaza": (1, 1),
        "stream_path": (1, 0),
        "stream_bend": (2, 0),
        "training_clearing": (2, 1),
        "herb_garden": (3, 1),
        "old_tree_north": (1, 2),
        "elder_tree": (1, 3),
        "weaving_slope": (2, 2),
        "silver_leaf_slope": (2, 3),
    },
}


def _plaza_key():
    x, y = SETTLEMENT_GRAPHS["capital_altoria"].node("central_plaza").coordinate
    return f"grid:capital_altoria:{x}:{y}"


ALPHA = "t_selected_alpha"
BETA = "t_selected_beta"
GAMMA = "t_selected_gamma"
DELTA = "t_selected_delta"


def _synthetic_registry(*graphs):
    return {graph.map_id: graph for graph in graphs}


