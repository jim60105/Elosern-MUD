"""Shared settlement declarations: the authoritative sparse graphs.

Each settlement module declares integer-metre node coordinates, stable node
identities, explicit roads and room prototypes. This module assembles them
once into ``SETTLEMENT_GRAPHS`` -- the single authoritative spawn, identity
and route declaration. Route finding and synchronization read only this
mapping, so memory and work scale with the graph rather than the coordinate
span (world-map-scale design §11). There is no ASCII authoring source: a metre
lattice is never parsed or allocated.

Consumers must read through :func:`settlement_graph` (or
:data:`SETTLEMENT_GRAPHS`); never rebuild a graph from a single settlement
module.
"""

from types import MappingProxyType

from world.maps.altoria_capital import NODE_IDS as _CAPITAL_NODE_IDS
from world.maps.altoria_capital import ROADS as _CAPITAL_ROADS
from world.maps.altoria_capital import XYMAP_DATA as _CAPITAL_XYMAP_DATA
from world.maps.sparse_graph import build_sparse_graph
from world.maps.village_ciaran import NODE_IDS as _VILLAGE_NODE_IDS
from world.maps.village_ciaran import ROADS as _VILLAGE_ROADS
from world.maps.village_ciaran import XYMAP_DATA as _VILLAGE_XYMAP_DATA


def _build_graph(map_data, node_ids, roads):
    return build_sparse_graph(
        map_id=str(map_data["zcoord"]),
        prototypes=map_data["prototypes"],
        node_ids=node_ids,
        roads=roads,
        options=map_data.get("options"),
        exit_prototype=map_data["prototypes"].get(("*", "*", "*"), {}),
    )


SETTLEMENT_GRAPHS = MappingProxyType(
    {
        str(_CAPITAL_XYMAP_DATA["zcoord"]): _build_graph(
            _CAPITAL_XYMAP_DATA,
            _CAPITAL_NODE_IDS,
            _CAPITAL_ROADS,
        ),
        str(_VILLAGE_XYMAP_DATA["zcoord"]): _build_graph(
            _VILLAGE_XYMAP_DATA,
            _VILLAGE_NODE_IDS,
            _VILLAGE_ROADS,
        ),
    }
)

KNOWN_GRID_MAP_KEYS = frozenset(SETTLEMENT_GRAPHS)


def settlement_graph(map_id: str):
    """Return the declared sparse graph for ``map_id``, or ``None``."""

    return SETTLEMENT_GRAPHS.get(map_id)
