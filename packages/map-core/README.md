# elosern-map-core

Pure, deterministic map calculations for Elosern: the typed authoring documents
and their restricted round-trip YAML codec, sparse settlement graphs and their
shortest-path routing, the explicit-input cell/local/world metric transforms,
the wilderness terrain rules, and the district partition's lightweight artifact
codec with the offline generator behind an optional `generation` extra. The
package imports no game code, Evennia, Django, HTTP client or UI state, so it
can be imported, tested and reasoned about outside the MUD.

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

### `elosern_map_core` authoring surface

- `schema()` — deep copy of the complete machine-readable version-1 domain
  schema (document kinds, every nested field including room prototype fields,
  typed value constraints, list identities and cross-field rules).
- `SourceDocument(relative_path, text, fingerprint)`,
  `make_source_document(...)`, `discover_source_paths(root)`,
  `discover_source_documents(root)` — the sorted world source set
  (`content/maps/{continent,locations,districts}.yaml`,
  `content/maps/settlements/*.yaml`, `content/maps/interiors/*.yaml`). Layouts
  and generated artifacts are never discovered as world inputs.
- `parse_document(relative_path, text)` — restricted YAML 1.2 parse returning
  typed values, one-based field provenance and the comment-preserving
  round-trip tree.
- `document_from_data(relative_path, data)` — validate a programmatic candidate
  and build its typed document.
- `serialize_document(document, retained_tree=None)` — merge the candidate into
  a copy of the retained tree, emit readable YAML and re-parse its own output;
  a failed or lossy candidate returns no text and never mutates the baseline.
- `load_authoring_world(source_documents)` — one structurally complete
  `AuthoringWorld` (or an `AuthoringError` carrying every source-located
  diagnostic). Unfinished maps load and record semantic work-in-progress
  diagnostics.
- `diagnose_world(world, *, partition_freshness=None)` — the saveable semantic
  diagnostics; supplied freshness can add `stale_partition`.
- `compile_runtime(world, authoritative_external_result, partition_freshness)` —
  the immutable `RuntimeMapSnapshot`, or a `RuntimeRejection`. It requires a
  diagnostic-free world, an explicit authoritative external result bound to
  this world's fingerprint and a current partition signature.

The codec rejects duplicate keys (before mappings are constructed), explicit or
custom tags, anchors, aliases, merge keys, timestamps, non-finite numbers,
non-decimal integer literals, sets/binary, multiple documents, empty documents,
non-string keys, unknown fields, unsupported versions/kinds and value-type
coercions. Integer fields never accept booleans, fractions or numeric strings.

Read-only inspection:

```console
uv run --locked python -m elosern_map_core schema
uv run --locked python -m elosern_map_core inspect <workspace-root>
```

See `docs/development/map-authoring-documents.md` for the complete field and
diagnostic reference.

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
`terrain_definition(continent)` builds the definition from a continent
document, and `terrain_preview(definition, max_side=90)` samples the same rules
on a bounded grid (region and surface codes from `PREVIEW_SURFACES`), with the
closed ridge walls between pass windows, the pass centres and the derived
national borders. The map editor draws it as read-only derived output.

Settlement previews: `road_lengths(settlement)` returns the physical polyline
length in metres of every declared road (source node, authored bends,
destination node), keyed by its ordered `(source, destination)` identity, and
exists even for an empty or unfinished map. `settlement_route(settlement_id,
settlement, source, destination)` returns a `RoutePreview` (`route`,
`no_route`, `unknown_node` or `unavailable` with the core's reason) from the
same planner the game uses, with each step's authored direction and length.
`polyline_length(points)` is the shared length rule.

The forest edge must be X-increasing and the border river X-decreasing; both are
validated at construction because their per-column row tables are single-valued.
`region_flavors` must cover every region key in `REGION_KEYS`.

### `elosern_map_core.partition_codec`

The runtime half of the frozen district partition (standard library only, no
generation dependency):

- `decode_partition(document, is_land=...)` — the decoded ownership, tile runs,
  exception tiles and outline rings; the land rule is the caller's boundary.
- `read_partition_metadata(document)` — `PartitionMetadata` (format version,
  `PARTITION_ALGORITHM_VERSION`, `source_signature`, raster `fingerprint`)
  without expanding any raster.
- `partition_source_signature(documents)` — the conservative digest over the
  authored sources ownership depends on (`continent`, `locations`, `districts`,
  `settlement`); interiors and layouts are excluded.
  `partition_source_signature_from_fingerprints({path: fingerprint})` signs a
  published snapshot's retained source set with the same rule.
- `partition_freshness(metadata, source_signature, algorithm_version=...)` —
  the `PartitionFreshness` result; a missing current signature is never current.
- `FORMAT_VERSION`, `MIXED`, `PARTITION_ALGORITHM_VERSION`,
  `PARTITION_SOURCE_KINDS`, `DistrictPartition`, `PartitionDocumentError`.

### `elosern_map_core.partition` (the `generation` extra)

The offline generator, imported only by the game's thin generator adapter
and the map editor's partition-job worker. It needs NumPy and SciPy:

```console
uv sync --extra generation
uv run --locked --extra generation python -m pytest tests
```

- `PartitionInputSnapshot` — the explicit immutable inputs: a
  `TerrainDefinition`, the declared nation and region identifiers, anchor
  footprint cells, resolved `DistrictSeed`s and the source signature.
- `world_snapshot(world)` — bind one loaded `AuthoringWorld` into that
  snapshot from its documents alone (terrain, `NATION_KEYS`, the declared
  regions, settlement footprints, district seeds with their routed gate
  approaches and containing footprint, `world.partition_signature`); an
  interior-room landmark cannot seed (`PartitionError`).
- `partition_input(snapshot)` — rasterize the snapshot into a `PartitionInput`.
- `generate_partition(input)` — partition, encode and serialize the complete
  artifact text (`version`, `algorithm_version`, `source_signature`,
  `fingerprint`, tile runs, exception tiles and outlines).
- `compute_partition`, `compute_outlines`, `encode`, `serialize`, `fingerprint`
  — the individual stages, for focused assertions.

### `elosern_map_core.elevation` (the `generation` extra)

The offline deterministic elevation and prominence generator. It needs NumPy
and SciPy; the runtime surface above never imports it:

- `ElevationConfig` — the one immutable versioned record for every seed,
  octave, wavelength, amplitude, ring radius, prominence threshold and cluster
  minimum; `DEFAULT_ELEVATION_CONFIG`, `ELEVATION_CONFIG_VERSION`.
- `generate_elevation(terrain, shapes, config)` — `ElevationRasters(bands,
  tiers)`, both `[y, x]` `uint8` arrays over the explicit `TerrainDefinition`.
  Sea is band 0, river cells never exceed their immediate land banks, sea /
  canopy / `no_prominence` cells are tier 0, and repeat calls return identical
  bytes.
- `fractal_noise(width, height, config)` — the domain-warped multi-octave value
  noise field, for the residual-autocorrelation assertion.
- `region_amplitudes(terrain, config)` — the per-cell region noise amplitude.
- `shape_weight(shape, width, height)` — the linear feather weight of one
  authored shape.
- `ELEVATION_BAND_MAX`, `PROMINENCE_TIER_MAX`, `CANOPY_REGIONS`.

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

The partition and elevation generator tests need the extra (CI uses this form):
`uv run --locked --extra generation python -m pytest tests`.

The game project consumes this package through its own `uv.lock`; the package
keeps independent metadata and lock.
