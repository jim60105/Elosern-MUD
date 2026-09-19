"""Exact schema-version-1 ``local_map`` panel and presenter (map-knowledge-minimap).

The presenter serializes a read-only local minimap from canonical room, map,
and knowledge data. It is registered beside ``status`` and ``context_actions``
in the production registry and never mutates knowledge, traits, clock, or
location.

The payload shape and the exact shared bounds (design D10a) are mirrored by the
client validator in ``web/static/webclient/js/elosern/protocol.js`` and guarded
by a dual-direction parity test.

This package splits the former single module along its seams:

- :mod:`.validate` -- the wire contract: schema version, exact shared bounds,
  closed vocabularies, legend labels, and the fail-closed payload validator.
- :mod:`.builder` -- the shared bounded node/edge accumulator and exit helpers.
- :mod:`.gateways` -- the registered-gateway lookup shared by both map layers.
- :mod:`.grid` -- the grid/anchor layer adapter and its XYMap geometry helpers.
- :mod:`.wilderness` -- the wilderness layer adapter.
- :mod:`.interior` -- the coordinate-free instance/interior layer adapter.
- :mod:`.presenter` -- the presenter assembling one layer and validating it.

Import cheapness is preserved: every typeclasses/world-lore import stays
function-local inside the adapters, and this facade imports the presenter
module (which itself defers the heavy imports to call time).
"""

from web.webclient.presentation.local_map.builder import (
    _GraphBuilder,
    _exit_ref,
    _known_node_id,
    _traversable,
    _visited_map,
)
from web.webclient.presentation.local_map.gateways import (
    _gateway_far_side_label,
    _grid_gateway_at,
    _registered_gateways,
    _wild_region_label,
    _wilderness_gateway_at,
)
from web.webclient.presentation.local_map.grid import (
    _free_slot,
    _grid_coord_is_anchor,
    _grid_direction_label,
    _grid_exit_action,
    _grid_gate_candidates,
    _grid_layer,
    _grid_node_in_map,
    _grid_nodes_in_range,
    _grid_room_label,
    _trim_visible,
)
from web.webclient.presentation.local_map.interior import _interior_graph, _room_by_id
from web.webclient.presentation.local_map.presenter import local_map_presenter
from web.webclient.presentation.local_map.validate import (
    ACTION_KINDS,
    COORD_MAX,
    COORD_MIN,
    GRID_MODES,
    LAYERS,
    LEGEND_LABELS,
    LOCAL_MAP_SCHEMA_VERSION,
    MAX_EDGES,
    MAX_EXIT_REF_CHARS,
    MAX_GRID_VISUAL_RANGE,
    MAX_LEGEND,
    MAX_NODE_ID_CHARS,
    MAX_NODES,
    MAX_REMEMBERED_GATEWAYS,
    MAX_STRING_CODE_POINTS,
    MAX_TITLE_CODE_POINTS,
    VISIBILITIES,
    WILD_DIRECTIONS,
    LocalMapError,
    _require_coord,
    _require_exit_ref,
    _require_node_id,
    _validate_action,
    _validate_edge,
    _validate_node,
    validate_local_map,
)
from web.webclient.presentation.local_map.wilderness import _wilderness_layer

__all__ = [
    "ACTION_KINDS",
    "COORD_MAX",
    "COORD_MIN",
    "GRID_MODES",
    "LAYERS",
    "LEGEND_LABELS",
    "LOCAL_MAP_SCHEMA_VERSION",
    "MAX_EDGES",
    "MAX_EXIT_REF_CHARS",
    "MAX_GRID_VISUAL_RANGE",
    "MAX_LEGEND",
    "MAX_NODE_ID_CHARS",
    "MAX_NODES",
    "MAX_REMEMBERED_GATEWAYS",
    "MAX_STRING_CODE_POINTS",
    "MAX_TITLE_CODE_POINTS",
    "VISIBILITIES",
    "WILD_DIRECTIONS",
    "LocalMapError",
    "_GraphBuilder",
    "_exit_ref",
    "_free_slot",
    "_gateway_far_side_label",
    "_grid_coord_is_anchor",
    "_grid_direction_label",
    "_grid_exit_action",
    "_grid_gate_candidates",
    "_grid_gateway_at",
    "_grid_layer",
    "_grid_node_in_map",
    "_grid_nodes_in_range",
    "_grid_room_label",
    "_interior_graph",
    "_known_node_id",
    "_registered_gateways",
    "_require_coord",
    "_require_exit_ref",
    "_require_node_id",
    "_room_by_id",
    "_traversable",
    "_trim_visible",
    "_validate_action",
    "_validate_edge",
    "_validate_node",
    "_visited_map",
    "_wild_region_label",
    "_wilderness_gateway_at",
    "_wilderness_layer",
    "local_map_presenter",
    "validate_local_map",
]
