# Design

## Context

See proposal.md for motivation. The baseline is `beb4584b`. The schema's `_RIDGE.passes` has `min_items=1`; `TerrainDefinition` already freezes an empty tuple successfully. `TerrainDeclaration` and `ContinentDocument.__post_init__` project YAML into typed inputs. Both `elosern_map_core.authoring.terrain_definition` and `world.maps.geography._terrain_definition` explicitly construct `TerrainDefinition`, so both must carry branches.

The current crest centre is `base_x + ((y // period) % 5 - 2) * step`. `ridge_span` joins this row's centre to the next row's centre inclusively; bends can occupy multiple cells, including the 41-cell phase wrap. `_ridge_walls` currently derives only stem polylines. Elevation `_base_elevation` currently uses `_row_centres` throughout the frame. `partition_input` already calls `is_passable_terrain` for each land cell. Two component indexers explicitly enumerate only `ridge_span`, in `world/maps/wilderness_reachability.py::WalkableComponents.__init__` and the contract test's `_RunComponents.__init__`; updating validity alone would leave both indexers incorrectly traversing arms.

The architecture's map-YAML exception and immutable snapshot publication remain intact. This change has no persistent state writer and no generative consumer.

## Goals / Non-Goals

The complete physical Y is a row-local obstacle union. Its political and region reference axis remains the existing stem-centre arithmetic, including above the physical stem's end. Hand-authored branches need no additional source or generated model.

Do not edit coast vertices, waterways/fords, forest edge, region fields, locations, harbour sites, districts, footprints, travel cost/movement, LLM or gameplay modules. Do not add migrations, aliases, a new map version, frontend branch controls or dependencies. Do not sync or archive main specs in the proposal phase.

## Decisions

### 1. Keep passes and add one paired route shape

Relax only `_RIDGE.passes.min_items` to zero. Keep the required list and its existing window typing and inverted-window validation. Empty means no exemptions. Nonempty synthetic documents remain legal for editing mechanisms; shipped content has zero windows.

Add the optional `branches` field to `_RIDGE` with this schema shape:

```text
branches?: mapping with exactly required keys west and east
west: list[{cell_x: integer >= 0, cell_y: integer >= 0}], min_items=2
east: list[{cell_x: integer >= 0, cell_y: integer >= 0}], min_items=2
```

Absent `branches` means a straight, unbranched ridge. Present empty mappings, a single arm, unknown arm keys, empty routes and wrong coordinate types are structure errors. This optional physical shape is a supported authoring state, with no legacy aliases or conversion layer.

Add `ridge_branches: Mapping[str, tuple[Point, ...]]` to `TerrainDeclaration` (explicitly supplied by the document projection) and `TerrainDefinition` (last field, `field(default_factory=dict)`). `ContinentDocument.__post_init__` projects route lists into tuples using `_cell`; absence projects an empty mapping. Freeze the model mapping and nested routes using existing mapping/point conventions. Both composition functions pass `ridge_branches=terrain.ridge_branches`. Update every real document-to-model constructor, including the isolated constructor in `tests/test_map_geographic_sources.py`; synthetic unbranched constructors may intentionally rely on the optional shape's empty default.

The fork row has one owner. Derive it as `ridge_north_limit - 1`; do not author a second `fork_y`. Both routes must begin at `(ridge_center_x(definition, fork_row), fork_row)`. Route rows strictly increase; the west route moves strictly west at its vertices and the east strictly east. Require every segment's `abs(dx) <= dy` so each centre advances by at most one column per row. Both routes must end north of the fork. These relations are semantic `terrain_inconsistent` failures through existing composition diagnostics, not schema freezes. Reject a pass covering the crotch row semantically, while passes elsewhere still exempt only the stem. Arms never receive pass exemptions.

Require fork and arm wall cells in-frame and inside `north_deep_forest`. Candidate validation must report arm cells off land or touching any full waterway raster cell (including fords). Report arm/location, harbour or resolved district-landmark collisions against the existing candidate inputs; do not move the protected object to repair a branch. Implement these checks in existing map-core authoring diagnostics, reusing candidate location, settlement projection and district references. Existing game acceptance rejects the resulting diagnostics without adding a new publication path.

### 2. Use deterministic per-row centres and a span union

Introduce these public core helpers, exported from terrain.py and package `__init__.py`:

```python
ridge_branch_center_x(definition: TerrainDefinition, branch: str, y: int) -> int | None
ridge_spans(definition: TerrainDefinition, y: int) -> tuple[tuple[int, int], ...]
```

Unknown branch keys raise `ValueError`. A known branch returns `None` outside its inclusive route row interval. Inside a segment `(x0,y0)..(x1,y1)`, use integer half-up interpolation:

```python
dy = y1 - y0
x = x0 + ((x1 - x0) * (y - y0) + dy // 2) // dy
```

The same rule applies for negative `dx`, without floats. Precompute two immutable per-row centre tuples during `TerrainDefinition` construction; no route search, raster construction, frame scan or dynamic cache allocation on the validity hot path. Each arm's independent vertices determine its own bends. A known hand-computed synthetic case, `(10,10)..(8,14)`, has centres `[10,10,9,9,8]`.

Keep `ridge_center_x`, `ridge_span` and `ridge_polyline` as stem-reference geometry; their signatures and political use remain unchanged. `ridge_spans` is the active physical wall union. For each row, include the stem only for `0 <= y < ridge_north_limit` outside passes, and each arm only over its route rows. Join each crest's current centre to its next active centre inclusively; at its terminal row join the centre to itself. Sort and merge overlapping or adjacent spans. Never replace two separated arms with their outer bounding interval, which would fill the valley. At the crotch all three share their current centre, and spanning toward the next arm rows leaves no diagonal gap. The wall is a one-cell crest with the same bend-closure semantics as the stem, not a widened mountain corridor.

`is_closed_ridge_cell` tests membership in this union. Stem `min_x/max_x` clipping applies only to the stem; never use that early rejection to discard arms in other valid documents. All arms remain blocked even with a stem pass at another row. Add spans to both row-run component candidate enumerators, retaining water/footprint/extra-blocked inputs and snapshot-scoped caching. Do not change `wilderness_neighbor` or movement rules.

### 3. Ship this measured geometry

Change only the ridge block of `content/maps/continent.yaml`:

```yaml
base_x: 1410
period: 60
step: 10
min_x: 1300
max_x: 1520
north_limit_y: 2001
mountain_corridor_half_width: 100
passes: []
branches:
  west:
    - {cell_x: 1420, cell_y: 2000}
    - {cell_x: 1390, cell_y: 2050}
    - {cell_x: 1355, cell_y: 2150}
    - {cell_x: 1320, cell_y: 2240}
  east:
    - {cell_x: 1420, cell_y: 2000}
    - {cell_x: 1445, cell_y: 2050}
    - {cell_x: 1480, cell_y: 2150}
    - {cell_x: 1510, cell_y: 2240}
```

The physical stem ends at row 2000; it must not continue through the valley to the old 2200 limit. The stem's southern end already runs into the sea, so there is no coast edit. The arms' last occupied row is 2240, and row 2241 has no physical crest.

An in-memory independent prospective raster with the above interpolation produced 671 distinct arm wall cells, all on land/in-frame/forest, no protected-point or full-waterway collisions, row-2150 margins of 55 km west and 70 km east, and nearest arm distance 51.546 km from Eolas. With zero passes and footprints excluded, independent SciPy four-connected labeling put all 9 location targets plus 6 harbours in component 1. Footprinted anchors used existing gateway approaches. No active row had a fully walkable horizontal band from X1300 to X1520. These are planning measurements, not executed tests of a future implementation.

Acceptance uses relationships rather than these route coordinates or the 671-cell count. At Eolas's row, the west span's eastern edge is at least 30 km west of the village and the east span's western edge at least 30 km east. No physical wall cell is within a 20 km Euclidean radius. Each tip has walkable forest immediately north, and all protected points stay clear. Human visual review uses `docs/development/continental-geography.md` as its review document; visual/narrative quality does not become a requirement.

### 4. Preserve regions and political lines; propagate physical relief

Leave `region_for_coordinates`, `region_search_boxes`, `nominal_nation_for_coordinates`, `national_borders` and `ridge_polyline` algorithms unchanged. The forest wins before the stem corridor, so arm cells are forest and Eolas keeps no administrative nation. Add a synthetic paired/unpaired comparison across the frame proving identical region keys, nominal claims, search boxes and political border points.

`_ridge_walls` produces stem wall runs and both branch wall polylines, including crotch and tips; do not feed the stem-only `ridge_polyline` to draw an arm. Use the same per-row centres and bend joins. `TerrainPreview.ridge_walls` retains its tuple-of-polylines shape; `passes` becomes empty for shipped data. The existing editor `snapshot._terrain_preview` and `capture_snapshot.load_capture_snapshot` already consume the core preview. Verify both preserve the added lines with synthetic payload tests; no frontend payload redesign is needed.

In `elevation._base_elevation`, replace the physical ridge proximity field with the pointwise maximum of active stem/west/east profiles. Each profile is `max(0, 1 - abs(x-centre)/half_width)` on its active rows, zero elsewhere; when half-width is zero it is the centre mask. Use the existing configured ridge rise once, never sum overlapping profiles at the fork. Keep `_row_centres` for `_region_masks`; truncating the physical stem must not truncate the region reference corridor. Reuse one full-frame proximity array and row-local NumPy updates for arms. Preserve sea/river clamps, noise, ordered shapes and forest prominence suppression. Advance `ELEVATION_ALGORITHM_VERSION` in `elevation_codec.py` from 1 to 2 because generator semantics changed; do not change the format version or configuration. Preserve `PARTITION_ALGORITHM_VERSION`, since partition propagation already consumes core validity and the authored source signature changes.

`partition.partition_input` should need no production change; it already delegates validity. Add a small synthetic input test that sees both arms blocked while their between-arm forest retains region-district ownership and unchanged nominal borders. Do not confuse a displayed owner on blocked land with traversability.

### 5. Keep branch authoring by hand

Do not add `set_ridge_branch` / `remove_ridge_branch`. A command pair would also need editor selection, control labeling, request validation and history semantics; hand-authored paired routes plus existing serializer/preview cover this bounded change. The tradeoff is that branches cannot be adjusted in the inspector. Technical authoring docs must state this explicitly.

Test the existing pass commands from a synthetic zero-pass branch document. `add_ridge_pass(y_min,y_max)` returns one successful continent write; `set_ridge_pass(index,y_min,y_max)` still works; removal of the last pass succeeds and returns to `[]` with a current preview. Choose a row below the crotch. Arm blockers/lines survive every operation and reload. An unrelated `set_terrain_parameter` write preserves branch values and retained comments; undo/redo restores the exact bytes using existing history. Reject attempts to submit branch command names as unknown without writes. The generic serializer needs no special-case changes.

## Requirement-to-test cutover matrix

Obtain canonical IDs with `uv run --locked --no-sync python -m tools.spec_traceability list --json-output /tmp/ridge-requirements.json`. Existing MODIFIED titles retain IDs. The only ADDED title, `The physical ridge is a continuous forked barrier`, has no current ID. Before sync, annotate its behavior tests with the closest current terrain/political requirement below and report that provisional mapping; after CLI sync, obtain its new canonical ID from the same tool and remount those tests. Never guess its ID or leave it uncovered after archive.

| Delta requirement / assertion role | Discoverable evidence and annotation |
| --- | --- |
| Map documents are discovered and schema checked as a complete candidate | Synthetic empty-pass and paired-route schema tests in existing `tests/test_map_authoring_contract.py`; literal `map-authoring-documents::map-documents-are-discovered-and-schema-checked-as-a-complete-candidate` |
| Restricted YAML preserves supported authored information | Synthetic branch/empty-list/comment parse-serialize-reparse test in the same module; literal `map-authoring-documents::restricted-yaml-preserves-supported-authored-information` |
| Continuous forked barrier (ADDED) | Synthetic centre/span/blocker/crotch/tip tests in existing `packages/map-core/tests/test_terrain.py`, plus shipped relationship tests in `world/maps/tests/test_wilderness_geography_contract.py`; provisional literal `wilderness-terrain::terrain-and-political-control-follow-authored-geography`, remount new canonical ID after sync |
| region_for_coordinates is a pure, deterministic function covering the whole bounded map | Synthetic unchanged classifier comparison and existing corridor test; literal `wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map` |
| Terrain and political control follow authored geography | Replace `test_principal_pass_is_open_mountain_trail_and_ridge_blocks_elsewhere` with no-exemption full physical crest rejection. Replace `test_ridge_northern_limit_passes_and_forest_speed_are_unchanged` with fork/clearance/inland-tip and walkable-forest relations. Retain other meaningful shares/anchor/claim/border checks. Literal `wilderness-terrain::terrain-and-political-control-follow-authored-geography` |
| The continent remains virtual with bounded local lookup | Replace provider `test_closed_ridge_and_water_are_impassable_with_authored_crossings` with stem and both-arm refusal, ordinary between-arm forest acceptance and unchanged ford acceptance. Keep bounded-work test. Literal `wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup` |
| Continental authored inputs have direct and explicit editing controls | Add process-level zero-pass/branch-preservation test in `tests/test_map_editor_geography.py`; literal `map-editor-geography::continental-authored-inputs-have-direct-and-explicit-editing-controls` |
| Elevation generation is deterministic and physically constrained | Synthetic max-not-sum crotch, branch rise, inactive-row and canopy tests in `packages/map-core/tests/test_elevation.py`, plus the same assertions in `tests/test_elevation_contract.py::_GENERATION_PROBE` executed by its existing discoverable `GenerationIsGameFreeTests` test; literal `wilderness-elevation-generation::elevation-generation-is-deterministic-and-physically-constrained` |
| Offline partition assigns every land cell once without crossing barriers | Synthetic input mask/forest ownership and no-corner-cutting test in `packages/map-core/tests/test_partition.py`; literal `map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers` |
| Provider `test_functions_are_pure`, incidental old pass coordinate | Replace the old pass tuple with a derived current crest probe; preserve the determinism role. No extra annotation claim |
| `_RunComponents`, production `WalkableComponents` | Add all physical spans to candidates; synthetic component-vs-independent-full-mask check plus existing shipped reachability test. Never use a stale stem-only index as evidence |

Existing data-contract modules keep their first-line classification and `tools/test_data_freeze.json` registration. Shipped tests assert identity/geometry/clearance/topology, not exact arm route lists, pass coordinates, cell counts, copy, markup or regenerated bytes as a substitute for behavior. Mechanism tests use synthetic data. No new test modules means no shard ownership change; if a module is added despite this plan, update its appropriate manifest. Do not repin mountain speeds or incidental limits; preserve relevant forest-walkability and corridor assertions under their actual requirement.

For package pytest evidence, put newly annotated synthetic tests at module level. `tools.spec_traceability` accepts module-level `test_*` functions; it does not recognize the existing `TestTerrainFeatures`-style pytest class names as eligible classes. Do not add invalid method annotations. Keep the top-level generation probe and shipped partition integration assertions substantively matched to the changed behavior so normal CI-owned unittest/Evennia discovery exercises the requirement as well as optional package pytest runs.

## Risks / Trade-offs

The gap at the crotch, the old stem through the valley and the two stem-only component indexes are the primary correctness risks. Independent raster evidence must catch all three. Integer interpolation plus next-row closure permits short two-cell bend joins; claiming every row is exactly one cell would contradict the existing stem mechanism.

The X1300..1520 probe means a horizontal west-to-east crossing within each active row, and a separate restricted-height four-connected crossing test through the entire band at rows 0 through the highest tip. A globally unrestricted route can and must go around the tips inside the forest. It is impossible to demand global east/west disconnection while simultaneously demanding one anchor/harbour component; do not encode that contradiction.

Full-frame component labeling is verification-only. Runtime validity stays bounded local work. Offline generation remains in the locked map-editor environment with NumPy/SciPy; use `--no-sync` offline. The exact user contract-gate command without `--no-sync` is expected to work from the already-synchronized lock; if it attempts unavailable networking, report the environment failure and also run its offline-equivalent command without changing dependencies.

## Verification and generated output

Implementation final verification, from the repo root, is the tasks.md batch. Regenerate partition and elevation via the existing skill scripts, never by hand. `check_map_sources.py` must finish with `RESULT: game-ready as far as static checks can tell`. Inspect existing reference-index freshness before deciding whether its standard regeneration is needed; no identity/reference change is planned. Source geometry, all 134 protected land points, 5,000,000 km² vector area, forest share 0.20 ±0.02 and national shares 0.43/0.30/0.27 ±0.015 remain acceptance conditions.
