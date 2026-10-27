# elosern-map-core

Pure, deterministic map calculations for Elosern: sparse settlement graphs and
their shortest-path routing, the explicit-input cell/local/world metric
transforms, and the wilderness terrain rules. The package has **no runtime
dependencies** and imports no game code, Evennia, Django, HTTP client or UI
state, so it can be imported, tested and reasoned about outside the MUD.

## Units

| Value | Unit |
| --- | --- |
| Wilderness cell | logical one-kilometre area (`TerrainDefinition.frame_cells` per axis) |
| Cell centre | absolute metres, `E = 1000 * X + 500`, `N = 1000 * Y + 500` |
| Settlement node / road point | integer metres east/north in the settlement's local frame |
| Road length | physical polyline length in metres (`RouteStep.length`) |
| World position | absolute metres east/north; the settlement's `z` is a logical layer, never elevation |
| Boundary / region coordinates | absolute kilometres |

`local_to_world_m(anchor_cell, local_anchor_m, local_position_m)` is
`cell_center_m(anchor_cell) + local_position_m - local_anchor_m`: the authored
local anchor point is the settlement position that sits on the wilderness
anchor cell's centre.

## API

### `elosern_map_core.geometry`

- `cell_center_m(cell)` — representative centre of a wilderness cell, in metres.
- `local_to_world_m(anchor_cell, local_anchor_m, local_position_m)` — the
  cross-layer transform. Interior locations carry no physical coordinate at all;
  callers must not synthesise one.
- `is_within_frame(frame_cells, cell)` — frame membership.
- `polygon_area_km2(boundary)`, `is_on_mainland(boundary, east_km, north_km)` —
  explicit-ring polygon helpers; boundary points count as land.

### `elosern_map_core.sparse`

- `SparseNode(node_id, x, y, prototype, physical=None)`,
  `SparseRoad(road_id, source_id, destination_id, bend_points=(), direction_hint=None, prototype={})`.
- `SparseSettlementGraph(map_id, nodes, roads, *, options=None, exit_prototype=None)`
  — construction is the validation boundary: duplicate identities, duplicate
  coordinates, unknown endpoints, self-loops, duplicate ordered roads and
  duplicate outgoing compass directions all raise `SparseGraphError` before a
  caller can persist or cache anything.
- `route(source_id, destination_id)` — Dijkstra over the declared adjacency
  only, so work and allocation are bounded by graph size, never coordinate
  span; `None` when unreachable, `()` for the same identity.
- `plan(source_id, destination_id)` / `plan_between_coordinates(start, end)` —
  the route as exit-named `RouteStep`s (authored compass direction, spawned exit
  key, metre length).
- `display_projection()` — the read-only `XYMap`-shaped display surface
  (`Z`, `options`, `node_index_map`, `get_node_from_coord`, `max_X`, `max_Y`).
- `build_sparse_graph(map_id=..., prototypes=..., node_ids=..., roads=..., ...)`
  — assembles the graph from coordinate-keyed authored tables and rejects
  identity/prototype or physical-position table drift.
- `compass_direction(dx, dy)`, `exit_spawn_names(direction)`.

### `elosern_map_core.terrain`

`TerrainDefinition` carries every authored terrain input (frame, mainland ring,
forest edge, waterway routes and fords, ridge base/period/step/limits, pass
windows, coastal band, corridor width, per-region flavour variants). Functions
take the definition first: `region_for_coordinates`, `nominal_nation_for_coordinates`,
`is_closed_ridge_cell`, `is_inland_water_cell`, `is_land_cell`,
`is_passable_terrain`, `is_walkable_cell`, `is_valid_wilderness_cell(defn,
footprint_cells, cell)`, `forest_edge_row`, `border_river_row`,
`terrain_description`, `national_borders`, `region_search_boxes`
(`definition.region_search_boxes`), plus the rasterizer helpers.

The forest edge must be X-increasing and the border river X-decreasing; both are
validated at construction because their per-column row tables are single-valued.
`region_flavors` must cover every region key in `REGION_KEYS`.

## Cache ownership

Derived tables belong to the definition instance that produced them:
per-column forest-edge and border-river rows, the rasterized waterway cell set,
the region search boxes and the derived national borders. Two definitions never
share a table, so classifying world B can never reuse a world-A value. The live
anchor-footprint set is a caller input, never package state.

Graph objects cache only their own derived adjacency and coordinate index.

## Checks

```console
uv run --locked python -m pytest          # inside this directory
```

The game project consumes this package through its own `uv.lock`; the package
keeps independent metadata and lock.
