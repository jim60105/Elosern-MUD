# Design

## Context

See proposal.md. Baseline `beb4584b` has one periodic stem with three passes. `_RIDGE.passes` requires at least one list item, although `TerrainDefinition` already accepts an empty tuple. The owner clarified during proposal review that the periodic curve is a simplified implementation; an arbitrary plausible nonstraight range is the intent. This design therefore replaces physical stem generation as well as adding arms. Geological plausibility stays human review.

`TerrainDeclaration`/`ContinentDocument.__post_init__` project YAML. Both `elosern_map_core.authoring.terrain_definition` and `world.maps.geography._terrain_definition` construct the runtime definition explicitly. `ridge_span` currently joins this and next periodic centres. `_ridge_walls` draws only the stem, elevation `_base_elevation` uses `_row_centres` across the full frame, and `partition_input` delegates to `is_passable_terrain`. Two row-run indexes enumerate only `ridge_span`, in `world/maps/wilderness_reachability.py::WalkableComponents.__init__` and the contract test's `_RunComponents.__init__`; updating validity alone would leave them traversing new walls.

The architectural map-YAML exception, immutable snapshots and atomic candidate adoption remain unchanged. No persistent state writer or generative consumer changes.

## Goals / Non-Goals

Physical crests are arbitrary authored northward polylines. Rasterization is deterministic; shape has no periodicity rule. Existing region and political reference geometry stays unchanged to satisfy the original geography constraints. This separates two live ownership roles, with no legacy physical fallback.

Do not change coast, waterways/fords, forest edge, region fields, locations, harbour sites, districts, footprints, movement/travel costs, gameplay/AI or effective demographic targets. No dependencies, migrations, new YAML version, frontend route controls, proposal-time main-spec sync or archive.

## Decisions

### 1. Required physical stem and optional paired arms

Keep all current ridge scalar fields. `base_x/period/step` remain solely the region/political reference axis. `min_x/max_x` remain physical stem clipping bounds. `north_limit_y` remains the exclusive physical stem end. Relax only the required `passes` list's minimum to zero, retaining typed windows and inverted-window rejection. Ship no passes; nonempty synthetic documents still establish editor mechanisms.

Add these YAML fields to `_RIDGE`:

```text
stem: list[{cell_x: integer >= 0, cell_y: integer >= 0}], min_items=2, required
branches?: mapping with exactly required keys west and east
west: list[{cell_x: integer >= 0, cell_y: integer >= 0}], min_items=2
east: list[{cell_x: integer >= 0, cell_y: integer >= 0}], min_items=2
```

Absent `branches` means an unbranched authored ridge. Missing `stem`, a present empty branch mapping, missing arm, unknown key, short route or wrong point type is a structure error. There is no default stem synthesized from `base_x/period/step`.

Add `ridge_stem: tuple[Point, ...]` to `TerrainDeclaration` and as a required non-default field to `TerrainDefinition`, before its default-valued fields. Add `ridge_branches: Mapping[str, tuple[Point, ...]]` to the declaration and as the final definition field with `field(default_factory=dict)`. Document projection supplies both, converting cells to tuples; absent arms become an empty mapping. Freeze routes and mapping using existing conventions.

Both composition functions pass `ridge_stem=terrain.ridge_stem` and `ridge_branches=terrain.ridge_branches`. Migrate every `TerrainDefinition` constructor, including `tests/test_map_geographic_sources.py`'s isolated constructor, package terrain/elevation/partition fixtures, top-level generation probes and synthetic authoring/editor workspace continent fixtures. Use graph callers and schema users to find all of them. Unbranched fixtures author a synthetic stem and may omit arms. No production physical consumer may fall back to the old periodic centre.

### 2. Row geometry and validation

The physical stem starts at row 0 and ends at `ridge_north_limit-1`. Its last authored point owns the fork's X coordinate. Branches begin exactly at that final point and end north of it. Do not author a duplicate fork row or derive the physical crotch X from the political axis.

Every route has strictly increasing Y. Require each segment `abs(dx) <= dy`, keeping at most one centre-column advance per row. Arbitrary local east/west bends, unequal segment heights and unequal bend spacing are allowed. There is no strict outward-X vertex rule. Branch tips must lie on opposite sides of the crotch. Paired arms must separate and never later cross/rejoin.

Introduce/export these core helpers from terrain.py and package `__init__.py`:

```python
ridge_crest_center_x(definition: TerrainDefinition, crest: str, y: int) -> int | None
ridge_spans(definition: TerrainDefinition, y: int) -> tuple[tuple[int, int], ...]
```

`crest` is `stem`, `west` or `east`; unknown values raise `ValueError`. Missing known arms and rows outside a crest's inclusive route interval return `None`. Inside segment `(x0,y0)..(x1,y1)`, use integer half-up interpolation:

```python
dy = y1 - y0
x = x0 + ((x1 - x0) * (y - y0) + dy // 2) // dy
```

Negative `dx` uses the same formula. Independent synthetic `(10,10)..(8,14)` yields `[10,10,9,9,8]`. Precompute immutable per-row centre tuples on construction after validating route shape; validity performs no route search, raster construction, frame scan or mutable cache allocation.

For each active crest, its wall spans inclusively from its current centre to its next active centre. At the last row use current-to-current. `ridge_spans` includes active stem spans clipped to `min_x/max_x`, excluding pass rows, plus all active arm spans without clipping or pass exemptions. Sort/merge overlapping or adjacent intervals. Keep separated arm intervals separate; never fill the valley with an outer bounding box. `is_closed_ridge_cell` uses this union. Every full physical wall cell is impassable, including bend-closure cells.

Keep `ridge_center_x`, `ridge_span` and `ridge_polyline` signatures/algorithms unchanged as region/political reference helpers. They cease being physical-wall APIs. Update all physical callers to authored crest helpers/spans; keep reference callers in classification, nominal claims and borders on the existing axis. Remove obsolete physical-use comments. This is a role separation with two active derived views, not an alias or compatibility shim.

Validate these semantic relations through existing `terrain_inconsistent` handling: route Y/slope/start/end relations; mismatched branch crotch; opposite tips; no crossed/rejoined arms; no crotch pass; in-frame physical centres/spans; fork/arms inside forest; clipped stem reaches its crotch. For the last condition, clipped stem geometry must contain its authored terminal centre and overlap its preceding clipped row when present. Ignore intentional below-crotch pass exemptions in this geometric join check. Reject a synthetic stem ending `(33,31)` with `min_x=max_x=32`; matching arm starts cannot repair a clipped-away stem.

To validate the shared raster crotch prefix, traverse shared arm rows with `separated=False`. Require west centre <= east centre throughout. Set the flag when west span's high edge < east span's low edge. Require this strict separation thereafter and before the shorter arm ends. This admits a shared connected prefix and rejects later rejoining without a human judgment.

Existing candidate authoring diagnostics also reject arm off-land cells and collisions with full waterway raster cells, including fords, authored locations, harbour sites and resolved district landmarks. Reuse candidate locations/settlement projections/references, never the published world. Leave protected objects untouched. Existing runtime acceptance rejects those same diagnostics atomically. Stem portions south of the coast are legal; requiring every stem cell to be land would contradict the southern sea endpoint.

### 3. Shipped arbitrary stem and Y

Change only the ridge block in `content/maps/continent.yaml`:

```yaml
base_x: 1410
period: 60
step: 10
min_x: 1300
max_x: 1520
north_limit_y: 2001
mountain_corridor_half_width: 100
passes: []
stem:
  - {cell_x: 1410, cell_y: 0}
  - {cell_x: 1398, cell_y: 150}
  - {cell_x: 1418, cell_y: 380}
  - {cell_x: 1404, cell_y: 620}
  - {cell_x: 1430, cell_y: 890}
  - {cell_x: 1412, cell_y: 1130}
  - {cell_x: 1428, cell_y: 1380}
  - {cell_x: 1408, cell_y: 1660}
  - {cell_x: 1420, cell_y: 1880}
  - {cell_x: 1420, cell_y: 2000}
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

Broad non-periodic stem bends replace the repeated five-phase physical sawtooth. The political/classifier axis is unchanged. The physical stem reaches the existing sea coast, stops at row 2000 and does not run through the valley to its obsolete 2200 end. Both tips end at 2240; row 2241 has no crest.

Planning measurement used this arbitrary stem and the above arm interpolation in an independent in-memory land/water/footprint mask. It found zero stem/arm collisions with protected points or full waterway cells; all 671 arm cells were in-frame/on-land/forest. Eolas row margins were 55/70 km and nearest arm distance 51.546 km. Four-connected SciPy labeling put all 9 location targets plus 6 harbours in component 1, with footprinted anchors represented by existing gateway approaches. No active row had a fully walkable horizontal X1300..1520 band. These measurements are prospective planning evidence, not implementation tests.

Tests establish relationships, never these point lists or the 671-cell count. Eolas must be at least 30 km from each inner arm edge on its row, with no wall inside a 20 km Euclidean radius. Tips must have walkable forest immediately north. Naturalness/geological plausibility is human-reviewed against the existing `docs/development/continental-geography.md`; deterministic topology is automated.

### 4. Every physical consumer and unchanged reference consumers

Leave `region_for_coordinates`, `region_search_boxes`, `nominal_nation_for_coordinates`, `national_borders` and `ridge_polyline` algorithms unchanged. Their stem reference axis, corridor, nation shares and political point sequences stay fixed; no arm is classified as a new mountain corridor or added to political lines. The forest still wins first, Eolas remains `north_deep_forest` without an administrative nation. A synthetic comparison varying arbitrary physical stem and arms while preserving reference inputs proves identical classifiers/search boxes/claims/borders.

Update both production/test row-run indexes to enumerate every `ridge_spans` interval before filtering candidates through shared validity. Keep water/ford/footprint/extra-blocked inputs and snapshot caches. Independently label a small full mask and compare components, including arbitrary stem bend cells and arm walls that old `ridge_span` candidates would miss. Do not change movement or corner guards.

`_ridge_walls` draws authored physical stem runs and both arms from row centres with bend closure. Preserve `TerrainPreview.ridge_walls` tuple-of-polylines payload and pass marker shape. Never use periodic `ridge_polyline` to draw physical walls. Editor `snapshot._terrain_preview` and `capture_snapshot.load_capture_snapshot` already consume the preview; test both to detect dropped lines without redesigning frontend payloads.

In elevation `_base_elevation`, use the maximum of active authored stem/west/east proximity profiles, each `max(0,1-abs(x-centre)/half_width)` and zero on inactive rows. Zero half-width uses centre masks. Reuse one full-frame proximity array with row-local NumPy updates; apply configured rise once, never sum at the crotch. Keep `_row_centres` only for `_region_masks`, using the unchanged reference axis. Preserve clamps, noise, ordered shapes and forest canopy suppression. Advance `elevation_codec.ELEVATION_ALGORITHM_VERSION` 1 to 2; keep format/config and partition algorithm versions unchanged.

Elevation profiles describe centres/shoulders, while traversal blocks complete closure spans. At half-width zero or one, a non-centre closure cell can have zero contribution and still be blocked. Acceptance observes pre-clamp/pre-shape centre and shoulder rise, never positive final bands for every blocker. Sea stays zero where the southern stem enters it; water clamps and authored shapes can override relief. Include a zero-width bent-crest test proving the distinction.

`partition_input` should need no production change because it delegates core validity. Test both arbitrary physical stem and arm masks and forest reserved ownership. Displayed district ownership on blocked cells is not evidence of walkability. Preserve same-nation propagation and closed national boundaries even at synthetic passes/fords.

### 5. Hand-only physical route authoring, usable existing editor

Do not add `set_ridge_branch` / `remove_ridge_branch` or stem-route commands. Full route commands would also require selection/labels/request validation/history semantics. The bounded alternative is explicit YAML authoring plus shared serializer and preview. State this limitation in authoring docs. Existing scalar controls edit their documented reference/clipping/limit roles; changing north limit without the route endpoint is diagnosed semantic WIP, never silently moves vertices.

A synthetic zero-pass arbitrary-stem/arm document must accept existing add/set/remove pass commands below the crotch, including removal of its last pass. Each accepted command writes only the continent, leaves preview current and preserves all physical routes/comments. Test unrelated scalar edits, history exact-byte restoration and reload/restart. Unknown branch/stem-route commands reject without writes. No generic codec special case is required.

## Requirement-to-test cutover matrix

Canonical IDs were obtained with `uv run --locked --no-sync python -m tools.spec_traceability list --json-output /tmp/ridge-requirements.json`. MODIFIED titles retain IDs. The one ADDED title, `The physical ridge is a continuous forked barrier`, has no current ID. Provisionally annotate its substantive tests to the closest current terrain/political ID, report this mapping, then obtain/remount the new canonical ID from the same tool immediately after assigned CLI sync. No guessed IDs, uncovered post-sync requirement or waiver.

| Requirement / role | Discoverable matching evidence and literal annotation |
| --- | --- |
| Schema discovery | `tests/test_map_authoring_contract.py` synthetic required stem/paired arms/zero passes/type rejection; `map-authoring-documents::map-documents-are-discovered-and-schema-checked-as-a-complete-candidate` |
| Round-trip YAML | Same module, synthetic routes/empty list/comments retained; `map-authoring-documents::restricted-yaml-preserves-supported-authored-information` |
| Physical fork (ADDED) | Module-level package terrain mechanism tests plus shipped geography barrier/fork/clearance tests; provisional `wilderness-terrain::terrain-and-political-control-follow-authored-geography`, remount after sync |
| Region classifier | Synthetic changed physical-route/unchanged reference-axis comparison and corridor test; `wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map` |
| Geography/claims | Replace `test_principal_pass_is_open_mountain_trail_and_ridge_blocks_elsewhere` with complete authored wall rejection; replace `test_ridge_northern_limit_passes_and_forest_speed_are_unchanged` with fork/clearance/tips/forest relations; retain shares/anchor/border assertions; `wilderness-terrain::terrain-and-political-control-follow-authored-geography` |
| Provider | Replace `test_closed_ridge_and_water_are_impassable_with_authored_crossings` with arbitrary stem and both arm refusal, valley forest and ford acceptance; keep local-work tests; `wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup` |
| Editor | Existing `tests/test_map_editor_geography.py` process journey preserves all hand-authored routes and edits zero passes; `map-editor-geography::continental-authored-inputs-have-direct-and-explicit-editing-controls` |
| Elevation | Package synthetic max/zero-width/active authored stem/arms/canopy mechanisms plus `tests/test_elevation_contract.py::_GENERATION_PROBE` under its existing `GenerationIsGameFreeTests` entrypoint; `wilderness-elevation-generation::elevation-generation-is-deterministic-and-physically-constrained` |
| Partition | Package synthetic arbitrary-wall masks/forest/closed border and shipped `world/maps/tests/test_map_district_partition.py` consumer assertions; `map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers` |
| Incidental provider purity tuple | Replace old pass coordinate with a derived authored crest probe, preserving determinism without a new coverage claim |
| Stem-only component indexers | Full physical candidate union plus independent small-mask labeling and existing shipped target connectivity, never a stale reference-only index |

Newly annotated package pytest functions must be module-level `test_*`; the traceability tool does not accept existing `TestTerrainFeatures`-style class method placements. Normal unittest/Evennia discovery must also exercise matching tests through top-level generation and shipped consumer tests. Preserve data-contract module first-line tags and `tools/test_data_freeze.json` registration. Assert schema/identity/geometry/clearance/connectivity, not shipped coordinate/count/copy tables. Delete/replace periodic physical implementation pins; keep independently known synthetic raster arithmetic and unchanged reference-axis assertions. Existing test modules remain in their current shards; if a module is added, update its manifest.

## Risks / Trade-offs

Crotch gaps, a stem continuing through Eolas, residual periodic physical callers and stem-only component indexes are the main risks. Independently computed expected masks catch all of them. Keep next-row closure semantics, which can occupy two cells on an authored bend; no contract requires exactly one occupied column at every row.

The X1300..1520 check is a horizontal crossing on each active row plus a four-connected band crossing restricted to rows at or south of the highest tip. Globally unrestricted travel must connect through forest around the tips; global east/west disconnection would contradict target connectivity. Full-frame labeling is verification-only.

Preserving the reference axis while replacing physical crest shape keeps the user's no-region/no-political-line movement invariant. The reference axis must be documented as a classifier/political abstraction, with no claim that every displayed point is a newly rasterized physical crest cell. This role separation is explicit and testable.

## Verification and generated output

Follow tasks.md's one final serial batch. Regenerate partition/elevation through existing scripts, never by hand. The source checker must print `RESULT: game-ready as far as static checks can tell`. Preserve vector area exactly 5,000,000 km² and all 134 protected land points; 5 km lattice forest share stays 0.20 ±0.02 and national shares 0.43/0.30/0.27 ±0.015. Reference-context identity/references do not change; invoke its existing publisher only if the checker requires freshness regeneration. No network or lock update is required; `--no-sync` uses installed locked environments.

## Review resolutions

The one blocking duck review flagged unconditional elevation gain on every wall cell, which conflicted with zero-width closure cells and sea clamps. The requirements now assert profile consumption/max pre-clamp rise alongside independent blocking. Its nonblocking clipped-crotch concern is also resolved by explicit terminal/previous-row join validation. The owner's later clarification expanded physical stem authoring to arbitrary routes while retaining the original frozen reference outputs; no implementation has been performed.
