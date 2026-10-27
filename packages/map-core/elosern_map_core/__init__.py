"""Pure deterministic map core for the Elosern map layers.

The package owns the authored-map calculations that must run without a game
environment: sparse settlement graphs and their shortest-path routing, the
explicit-input cell/local/world metric transforms, and the deterministic
wilderness terrain rules.

Every entry point takes its inputs explicitly -- a terrain definition, a graph,
or plain integer values -- and returns plain immutable values. There are no
imports of ``world``, Evennia, Django, HTTP or UI state, and no module-level
mutable cache that could leak one world's values into another.
"""

from .geometry import (
    CELL_CENTER_OFFSET_M,
    METRES_PER_WILDERNESS_CELL,
    cell_center_m,
    is_on_mainland,
    is_within_frame,
    local_to_world_m,
    polygon_area_km2,
)
from .sparse import (
    RouteStep,
    SparseEdge,
    SparseGraphError,
    SparseNode,
    SparseDisplayMap,
    SparseDisplayNode,
    SparseRoad,
    SparseSettlementGraph,
    build_sparse_graph,
    compass_direction,
    exit_spawn_names,
)
from .terrain import (
    REGION_KEYS,
    RIDGE_BEND_PHASES,
    NationalBorder,
    TerrainDefinition,
    border_river_row,
    forest_edge_row,
    is_closed_ridge_cell,
    is_inland_water_cell,
    is_land_cell,
    is_passable_terrain,
    is_valid_wilderness_cell,
    is_walkable_cell,
    nominal_nation_for_coordinates,
    rasterize_routes,
    rasterize_segment,
    region_for_coordinates,
    ridge_center_x,
    ridge_polyline,
    ridge_span,
    route_row_at,
    terrain_description,
)

__all__ = [
    "CELL_CENTER_OFFSET_M",
    "METRES_PER_WILDERNESS_CELL",
    "NationalBorder",
    "REGION_KEYS",
    "RIDGE_BEND_PHASES",
    "RouteStep",
    "SparseDisplayMap",
    "SparseDisplayNode",
    "SparseEdge",
    "SparseGraphError",
    "SparseNode",
    "SparseRoad",
    "SparseSettlementGraph",
    "TerrainDefinition",
    "border_river_row",
    "build_sparse_graph",
    "cell_center_m",
    "compass_direction",
    "exit_spawn_names",
    "forest_edge_row",
    "is_closed_ridge_cell",
    "is_inland_water_cell",
    "is_land_cell",
    "is_on_mainland",
    "is_passable_terrain",
    "is_valid_wilderness_cell",
    "is_walkable_cell",
    "is_within_frame",
    "local_to_world_m",
    "nominal_nation_for_coordinates",
    "polygon_area_km2",
    "rasterize_routes",
    "rasterize_segment",
    "region_for_coordinates",
    "ridge_center_x",
    "ridge_polyline",
    "ridge_span",
    "route_row_at",
    "terrain_description",
]
