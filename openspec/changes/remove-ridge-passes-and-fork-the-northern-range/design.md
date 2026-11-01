# Design

## Context

Baseline `beb4584b` has a periodic stem and three passes. `_RIDGE.passes` requires at least one item; `TerrainDefinition` already accepts an empty tuple. The owner ruled that the formula was a simplified implementation, not intent. The entire authored crest now drives physical shape and all derived consumers. The earlier proposal's separate reference axis is superseded and must not be implemented.

Observed owners are `schema.py::_RIDGE`, `documents.py::TerrainDeclaration`/`ContinentDocument.__post_init__`, both `authoring.terrain_definition` and `world.maps.geography._terrain_definition`, terrain lookups/preview, elevation `_row_centres`/`_region_masks`/`_base_elevation`, and partition input validity. Production `WalkableComponents.__init__` and the geography contract's `_RunComponents.__init__` enumerate only `ridge_span`, so both must enumerate the full fork.

Editor `geography.py::_feature/_points` dispatches existing move/insert/remove point commands. Frontend `continent.js::parseContinentRef/commandFeature/featurePoints`, `objects.js::continentEntries`, `map_scene.js::continentScene` and `ContinentInspector.vue` already provide selection, dragging, numeric controls and history. Extending these is simpler than retaining formula controls or adding a second route-command family.

## Goals / Non-Goals

One authored stem plus optional paired arms is the shape authority. Determinism belongs to interpolation and rasterization. All derived terrain/claim/political outputs follow this same stem; no old formula or separate axis remains.

Do not change coastline, waterways/fords, forest edge, region declarations, harbours, locations, districts, footprints, movement/travel rules, gameplay/AI or effective demographic targets. Region/claim/border coordinates may change as the owner directed, but area, protected points, shares, Eolas independence and target connectivity remain invariant. No migration, compatibility layer, dependency or new YAML version. Proposal work never syncs or archives main specs.

## Decisions

### 1. Replace obsolete ridge parameters with authored routes

The new `_RIDGE` schema is:

```text
stem: list[{cell_x: integer >= 0, cell_y: integer >= 0}], min_items=2, required
branches?: mapping with exactly required keys west and east
west: list[{cell_x: integer >= 0, cell_y: integer >= 0}], min_items=2
east: list[{cell_x: integer >= 0, cell_y: integer >= 0}], min_items=2
mountain_corridor_half_width: integer >= 0, required
passes: list[{y_min: integer, y_max: integer}], min_items=0, required
```

Remove `base_x`, `period`, `step`, `min_x`, `max_x`, `north_limit_y` and their typed/model fields. Endpoints/frame validation/derived row extents replace their purposes, so retaining them would create conflicting sources. Unknown old fields reject through the existing strict schema. Missing stem, short routes, wrong types, unknown arms or a present incomplete branch pair are structure errors. Absent branches mean an unbranched authored range, not a formula fallback.

Add required `ridge_stem: tuple[Point, ...]` to `TerrainDeclaration` and `TerrainDefinition`. Add `ridge_branches: Mapping[str, tuple[Point, ...]]` to the declaration and as the final definition field with `field(default_factory=dict)`. Project/freeze points and nested mapping using existing conventions. Both composition functions pass those exact fields. Migrate every constructor, isolated subprocess probe and synthetic continent fixture; do not preserve old constructor aliases or default periodic stems.

### 2. Single-valued row centres and closed spans

Each ordered route must have strictly increasing Y and segments with `abs(dx) <= dy`. The owner's single-valued-in-Y constraint gives one centre X for each active row, while local east/west bends and unequal spacing remain legal. It does not require globally monotone X. The stem begins at row 0; its last vertex owns its northern end and the crotch. Branches begin exactly at that vertex and end north of it. Both tips lie on opposite sides of the crotch. Fork/arm wall cells lie in-frame, on land and in deep forest.

Use integer half-up interpolation inside `(x0,y0)..(x1,y1)`:

```python
dy = y1 - y0
x = x0 + ((x1 - x0) * (y - y0) + dy // 2) // dy
```

The same rule applies for negative dx. Independent synthetic `(10,10)..(8,14)` has centres `[10,10,9,9,8]`. Precompute immutable centre tuples during TerrainDefinition construction. Point validity must not search routes, construct rasters, scan the frame or allocate mutable caches.

Public contracts are:

```python
ridge_center_x(definition: TerrainDefinition, y: int) -> int
ridge_crest_center_x(definition: TerrainDefinition, crest: str, y: int) -> int | None
ridge_span(definition: TerrainDefinition, y: int) -> tuple[int, int] | None
ridge_spans(definition: TerrainDefinition, y: int) -> tuple[tuple[int, int], ...]
ridge_polyline(definition: TerrainDefinition, y_start: int, y_end: int) -> tuple[Point, ...]
```

`ridge_center_x` evaluates the authored stem centre, extending its endpoint X constantly outside its Y interval so the region/nominal classifier remains total over the bounded frame. This is derivation from the same authored endpoint, never a separate axis or source. `ridge_crest_center_x` accepts stem/west/east; unknown keys raise ValueError, missing known arms and inactive rows return None. `ridge_span` returns the active stem closure span or None outside stem rows, independent of pass exemptions. Migrate callers to its optional result; consumers needing all physical walls use `ridge_spans`.

Each wall span joins current and next active centre inclusively; the terminal row joins current to itself. `ridge_spans` omits stem spans in authored pass rows, includes both arms without pass exemptions, sorts/merges overlap or adjacency, and never fills separated arms with their outer bounding interval. The shared crotch cannot be a pass. Removing clipping parameters eliminates the review's clipped-away-crotch failure. Sea-side southern stem portions remain legal; every physical wall cell blocks traversal even where land validity already fails.

Paired arms must separate without later crossing/rejoining. Walk shared rows with `separated=False`, requiring west centre <= east centre throughout. Set the flag when west span high < east span low; require that strict span separation thereafter and before the shorter route ends. This admits an initial connected raster crotch prefix. Validate route relations as semantic `terrain_inconsistent` WIP, while shape/type defects freeze as structure errors. Existing candidate diagnostics also reject arm/full-waterway collisions (including fords), protected location/harbour/resolved district-landmark collisions and off-land arms, using candidate inputs only. Runtime atomically rejects the same diagnostics without moving protected content.

`ridge_polyline` clips the authored stem route to the requested inclusive Y interval, emitting interpolated boundary centres plus interior authored vertices and deduplicating equal endpoints. Return an empty tuple for no intersection. This keeps displayed political lines tied to authored vertices, with no periodic substitute or arm segments. Physical wall previews use raster closure centres/spans, since political polylines are continuous presentation geometry.

### 3. Concrete shipped ridge

Replace only the ridge block in `content/maps/continent.yaml`:

```yaml
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

The southern stem already intersects the existing sea coast. It stops at the crotch at row2000 rather than continuing through Eolas. Arms end at2240 inside forest; row2241 has no physical wall. Broad unequal bends replace the periodic sawtooth. Keep every other authored source byte unchanged.

Independent in-memory planning calculations using these routes and the new endpoint-derived nominal split found shares Grandia0.429393, Altoria0.299939, Valhalla0.270669 and forest0.200554 on the5km lattice, all within acceptance. There were no stem/arm collisions with protected points/full waterways; all671 arm cells were in-frame/on-land/forest. Eolas row margins were55/70km and minimum arm distance51.546km. Four-connected labeling placed all9 location targets and6harbours in component1, using gateway approaches for footprinted anchors. No active row had a fully walkable X1300..1520 band. These are prospective planning measurements, not executed implementation tests.

Do not pin these route lists/counts in tests. Assert at least30km between Eolas and each inner arm edge on its row, no wall inside a20km Euclidean radius, forest immediately north of inland tips, and one target component. A plausible mountain range is a human-review property against `docs/development/continental-geography.md`, not an automated visual/geological assertion. Add that review note to the geography document and continent authoring reference during implementation.

### 4. Derived consumers follow the same authored stem

`region_for_coordinates` keeps forest-first precedence and the existing corridor test `abs(x-ridge_center_x(y)) <= mountain_corridor_half_width`; the centre now comes from the authored stem. Arms remain forest barriers without creating corridors. `nominal_nation_for_coordinates` flips at that same stem centre, including its endpoint-derived forest continuation. Eolas must retain no administrative nation, but its previous literal nominal-Grandia assertion is incidental old geometry and must be replaced by total nominal-classification plus independence, never re-pinned to another nation.

`region_search_boxes` derives the mountain window X bounds from min/max authored stem centre rows, widened by the authored half-width and clipped to frame bounds, keeping the existing forest-edge Y bound. Remove `RIDGE_BEND_PHASES` and all bend-extent arithmetic. Other search windows retain their existing derivations. Synthetic full-frame checks establish that every classified cell fits its search window.

`national_borders` uses authored `ridge_center_x` for the river-source junction and `ridge_polyline` for the two east/west borders. Clip political ranges to the active stem and below the local forest edge, preserving the existing south land-entry and river linkage rules. Political coordinates may change; they must be derived from the same crest. No arm/forest political segments appear. Tests retain derivation relationships. Junction equals authored centre at the source row, border equals clipped authored stem, neighbours flip nations and corridor follows the crest.

Both row-run component indexers enumerate all `ridge_spans` candidates; retain water/ford/footprint/extra-blocked semantics and snapshot caches. Compare a small independent full mask with production components using stem cells outside former formula spans and arm probes. Movement/corner guards remain unchanged.

`_ridge_walls` draws authored stem wall runs and both arm closure polylines. Preserve TerrainPreview wall/pass payload shapes, and test editor/capture consumers do not drop any crest. Editor raw control points are separate derived payload values, never an alternate source.

In elevation, `_row_centres` now uses the authored stem for `_region_masks`, matching the game classifier. `_base_elevation` takes the maximum active stem/west/east profile, `max(0,1-abs(x-centre)/half_width)` with centre masks at zero width and zero on inactive rows. Reuse one full-frame proximity array plus row-local NumPy updates. Apply configured rise once; preserve sea/river clamps, noise, ordered shapes and canopy-tier suppression. Advance elevation algorithm1to2, keeping format/config unchanged. Profiles raise centres/shoulders before clamps/shapes; closure-only cells may have zero contribution at width0or1 yet remain blockers. Never require positive final bands on every wall, especially the sea-side stem.

Partition input already calls core validity/classifiers. Add authored wall mask/forest ownership/narrow-obstacle tests; no production propagation change should be needed. Keep national borders closed even at synthetic passes/fords. Keep partition algorithm version unchanged because propagation is unchanged and source signatures/input rasters carry the new geometry; regenerate its artifact.

### 5. Extend existing editor control-point features

Use existing command names, not `set_ridge_branch`/`remove_ridge_branch`:

```json
{"name":"move_control_point","arguments":{"feature":{"kind":"ridge_route","route":"stem"},"index":1,"point":[1400,150]}}
{"name":"insert_control_point","arguments":{"feature":{"kind":"ridge_route","route":"west"},"index":1,"point":[1400,2020]}}
{"name":"remove_control_point","arguments":{"feature":{"kind":"ridge_route","route":"east"},"index":1}}
```

Existing document/fingerprint/session envelopes remain unchanged. Add ridge_route to backend `_FEATURE_KINDS`; `_feature` requires exactly kind/route with route stem/west/east. `_points` resolves stem or the named existing arm, rejecting an absent arm without creating one. Point units are wilderness cells. Generic insert/remove minimums/indices/rejection and single-document history remain. Below-minimum removal is422validation_failed with no write. At a paired crotch, moving stem's last point or either arm's first point updates all three shared points atomically in the same continent command. Removing a shared crotch point is409deletion_refused with no write; insertion before an arm's crotch or beyond a paired stem's crotch is refused rather than silently detaching the fork. Interior points remain ordinary move/insert/remove. Invalid monotone/collision geometry is saveable diagnosed WIP under existing editor semantics.

Keep `continent:ridge` as the group holding corridor width and pass controls, not a deprecated alias. Add point-feature refs `continent:ridge_route:stem|west|east` and `#<index>`. `continent.js` handles parsing/feature dispatch/points; `objects.js` catalogs each route and point; `map_scene.js` makes authored routes selectable with ridge-layer handles while complete physical wall rendering still comes from preview. `ContinentInspector.vue` reuses frame-labelled point numeric/insert/remove controls and removes obsolete formula-field inputs. `world_index.js::continentRecord` shows route point context; App.vue's generic point-drag path already delegates through commandFeature and needs only any actual classification integration changes.

In `snapshot.py`'s existing continent projection, keep `ridge` as raw authored data and add:

```text
ridge_routes: {stem: [[x,y],...], west?: [[x,y],...], east?: [[x,y],...]}
ridge_routes_m: same keys/indices, [[1000*x+500,1000*y+500],...]
```

Both use the candidate typed routes. featurePoints reads these maps. Capture reuses the same snapshot and draws all crests without editor sessions. No schema/runtime/LLM ownership change.

Keep `set_terrain_parameter` for corridor half-width/coastal_y_max/border_river_key only. Removed periodic field requests reject as invalid_command without writes. Existing add/set/remove_ridge_pass commands work from/to zero windows; below-crotch stem exemptions do not open arms. Test serializer/comment retention, one-write commands, exact undo/redo/reload, atomic crotch movement, shared-point guards, selectable route handles, numeric controls and independent preview/capture geometry. Extend existing browser method `MapEditorGeographyBrowserTest.test_derived_borders_have_no_handles_at_the_large_viewport` to replace its obsolete ridge-base_x edit with stem/arm route controls; derived political lines remain handle-free. Do not add a new browser method or shard entry just to duplicate this journey.

## Requirement-to-test cutover matrix

Canonical IDs come from `uv run --locked --no-sync python -m tools.spec_traceability list --json-output /tmp/ridge-requirements.json`. Existing MODIFIED titles retain IDs. The one ADDED physical-ridge title provisionally mounts to the current terrain/political ID until assigned CLI sync; obtain/remount its new canonical ID immediately afterward. No guessed IDs, uncovered archive requirement or waiver.

| Requirement / assertion role | Matching discoverable evidence and literal ID |
| --- | --- |
| Schema discovery | Existing `tests/test_map_authoring_contract.py`: required authored stem, optional paired arms, zero passes and retired-field/type rejection; `map-authoring-documents::map-documents-are-discovered-and-schema-checked-as-a-complete-candidate` |
| YAML preservation | Same module: arbitrary routes/empty list/comments parse-edit-serialize-reparse; `map-authoring-documents::restricted-yaml-preserves-supported-authored-information` |
| Physical fork ADDED | Module-level package terrain mechanisms and shipped geography full-wall/fork/clearance tests; provisional `wilderness-terrain::terrain-and-political-control-follow-authored-geography`, remount after sync |
| Classifier | Synthetic authored-crest corridor/claim/window derivation and existing corridor test; `wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map` |
| Geography/claims | Replace principal-pass and northern-limit/pass tests with authored full-wall/fork/clearance/tips; update old Eolas nominal-nation and border-coordinate pins to authored derivation; retain shares/independence/connectivity; `wilderness-terrain::terrain-and-political-control-follow-authored-geography` |
| Provider | Replace old pass-crossing assertion and incidental purity coordinate; assert authored stem/both arms refusal, valley forest/ford acceptance and bounded work; `wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup` |
| Editor | Existing top-level process test plus updated browser method establishes move/insert/remove/atomic crotch/zero passes/history; `map-editor-geography::continental-authored-inputs-have-direct-and-explicit-editing-controls` |
| Elevation | Package synthetic maximum/authored classifier/width0/active rows/canopy plus top-level `tests/test_elevation_contract.py::_GENERATION_PROBE` under GenerationIsGameFreeTests; `wilderness-elevation-generation::elevation-generation-is-deterministic-and-physically-constrained` |
| Partition | Package authored wall mask/forest/closed-border mechanisms and shipped partition integration; `map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers` |
| Component candidates | Full physical spans plus independent small-mask labeling and shipped target connectivity; never a formula-only expectation or stale index |

Preserve tagged data-contract modules and freeze registration. Mechanisms use synthetic fixtures and independently known results; shipped tests establish identity/schema/topology/derivation relationships, not copied route/count/copy/markup values. Delete/replace periodic physical implementation pins, never repin them to new coordinates. Newly annotated package pytest tests are module-level because existing TestTerrainFeatures-style classes are not traceability-eligible. Normal unittest/Evennia/browser discovery also executes substantively matching tests. Existing module/method names keep shard ownership; additions require manifest updates.

The direct constructor in `tests/test_map_core_contract.py` must also migrate and remain covered by the final unittest batch. Update `docs/development/map-editor.md`'s continental command/snapshot section, whose table currently names all retired periodic fields and omits ridge_route selectors. Update the route controls, units, shared-crotch refusals and payload fields there. Preserve explicitly dated historical synthetic review evidence rather than recasting it as a new automated acceptance; mark any current shipped three-pass capture description superseded by the authored zero-pass Y.

## Risks / Trade-offs

One single-valued authored centre table must feed every consumer; residual formula/reference-axis code would violate the owner's ruling. Crotch gaps, old stem continuation through the valley, missed arm candidates and frontend selector/handle omissions are the main risks. Independent masks and end-to-end editor commands detect them.

The band probe checks horizontal crossings on every active row and four-connected edge-to-edge crossings restricted to rows at or south of the highest tip. Global traversal must connect around the forest tips; global east/west disconnection would contradict acceptance. Full-mask labeling belongs only to verification, not runtime movement.

Control-point reuse keeps this within one change. No branch-pair creation/deletion tool is added; paired shape membership is authored YAML, while every existing route is editable through standard point tools. Geological plausibility stays human review.

## Verification and review

Follow tasks.md's one final serial batch, regenerate partition/elevation and require `RESULT: game-ready as far as static checks can tell`. Keep exact vector area5,000,000km², all134 protected land points, forest0.20±0.02 and nation0.43/0.30/0.27±0.015 shares, Eolas forest/no-administration and one target component. Reference-context publisher is used only if existing freshness checking requires it.

The earlier duck review's all-wall elevation contradiction is addressed by centre-profile/max-before-clamp semantics. Removing clipping parameters also removes its detached-crotch cause. The owner subsequently superseded the separate axis and hand-only editing decisions; this revision has one authored crest authority and normal point controls. No implementation has been performed.
