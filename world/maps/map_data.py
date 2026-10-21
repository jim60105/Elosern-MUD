"""Shared settlement declarations: display map data and sparse graphs.

Two representations live here for one bounded transition:

``XYMAP_DATA_LIST`` keeps the dense ASCII declarations that the xyzgrid
contrib still needs for its display/builder surfaces (``地圖``, the
``evennia xyzgrid`` CLI, ``XYZRoom.return_appearance``). It is no longer the
spawn input: ``sync_grid()`` never parses it.

``SETTLEMENT_GRAPHS`` is the authoritative spawn, identity and route
declaration. Each graph binds stable node identities and explicit roads from
the settlement module's ``NODE_IDS``/``ROADS`` tables. Route finding and
synchronization read only this mapping, so memory/work scale with the graph
rather than the coordinate span (world-map-scale design §11). The later
metric-coordinate cutover replaces the ASCII authoring source; nothing here
needs a second authoritative map in the meantime because the graphs and the
ASCII table are pinned to each other by the topology regression tests.

Consumers must read through :func:`settlement_graph` (or
:data:`SETTLEMENT_GRAPHS`); never rebuild a graph from a single settlement
module.
"""

from types import MappingProxyType

from world.maps.altoria_capital import NODE_IDS as _CAPITAL_NODE_IDS
from world.maps.altoria_capital import (
    PHYSICAL_NODE_POSITIONS as _CAPITAL_PHYSICAL_POSITIONS,
)
from world.maps.altoria_capital import ROADS as _CAPITAL_ROADS
from world.maps.altoria_capital import XYMAP_DATA as _CAPITAL_XYMAP_DATA
from world.maps.sparse_graph import build_sparse_graph
from world.maps.village_ciaran import NODE_IDS as _VILLAGE_NODE_IDS
from world.maps.village_ciaran import (
    PHYSICAL_NODE_POSITIONS as _VILLAGE_PHYSICAL_POSITIONS,
)
from world.maps.village_ciaran import ROADS as _VILLAGE_ROADS
from world.maps.village_ciaran import XYMAP_DATA as _VILLAGE_XYMAP_DATA

XYMAP_DATA_LIST = [_CAPITAL_XYMAP_DATA, _VILLAGE_XYMAP_DATA]


def _build_graph(map_data, node_ids, roads, physical_positions):
    return build_sparse_graph(
        map_id=str(map_data["zcoord"]),
        prototypes=map_data["prototypes"],
        node_ids=node_ids,
        roads=roads,
        options=map_data.get("options"),
        exit_prototype=map_data["prototypes"].get(("*", "*", "*"), {}),
        physical_positions=physical_positions,
    )


SETTLEMENT_GRAPHS = MappingProxyType(
    {
        str(_CAPITAL_XYMAP_DATA["zcoord"]): _build_graph(
            _CAPITAL_XYMAP_DATA,
            _CAPITAL_NODE_IDS,
            _CAPITAL_ROADS,
            _CAPITAL_PHYSICAL_POSITIONS,
        ),
        str(_VILLAGE_XYMAP_DATA["zcoord"]): _build_graph(
            _VILLAGE_XYMAP_DATA,
            _VILLAGE_NODE_IDS,
            _VILLAGE_ROADS,
            _VILLAGE_PHYSICAL_POSITIONS,
        ),
    }
)

KNOWN_GRID_MAP_KEYS = frozenset(SETTLEMENT_GRAPHS)


def settlement_graph(map_id: str):
    """Return the declared sparse graph for ``map_id``, or ``None``."""

    return SETTLEMENT_GRAPHS.get(map_id)
