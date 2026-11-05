# Design

## Context

See `proposal.md` - Why. The wilderness `area_map` body is a centred 41×41 one-kilometre RLE window (`web/webclient/presentation/area_map.py`; `WILDERNESS_WINDOW` in `web/webclient/presentation/map_panels.py`). District lighting already marks a district lit from the exact landmark visit and `revealed_in_bounds` exposes the lit district's cells inside the requested bounds. The wilderness presenter only requests the 41-cell bounds, so the rest of the lit district never reaches a client. The district partition has 120 districts; the largest region district (`north_deep_forest`) is 1,002,962 one-kilometre cells (1,992 × 725 km), while `royal_river_valley` is 35,665 cells (228 × 220 km). A one-kilometre full-district payload is not viable.

The fine window must stay at 1 km because travel planning, adjacency, gateways, live sight and entities are defined on that frame. The route preview window is also capped at the current ±20 cells (`PLAN_WINDOW_RADIUS`), so no routing behavior changes.

Two existing implementation facts shape the revised design. First, `district_outlines()` is a smoothed display layer: `_smooth` uses edge midpoints and 500 m Douglas-Peucker simplification, so its bbox can be one kilometre narrower than the exact ownership raster. Second, the travel camera is built for 1 km cells: `followCamera` centres the party in the full stage, `cellBox` subtracts a 2 px inset, `glyphScale` is floored at 18 px, and the scale bar assumes 5 km; a sub-18 px/km stop cannot reuse those assumptions unchanged.

## Goals / Non-Goals

**Goals:**

- Publish the current lit district's whole owned extent in the wilderness `area_map` body at a bounded coarse resolution.
- Keep the 41-cell one-kilometre window, its nodes, actions, entities and sightings unchanged.
- Render the coarse district in an explored grade behind the local window in the area-map drawer and the wilderness travel stage, without coarse terrain bleeding into unrevealed fine cells.
- Make the whole lit district viewable on the wilderness screen through a dedicated district-fit state, without changing movement or routing.
- Use one explored style for district-revealed and previously-walked cells outside live sight.

**Non-Goals:**

- No one-kilometre full-district payload or per-cell district rendering.
- No change to lighting, landmark resolution, knowledge writes, reveal predicates, disclosure of hidden places, or travel planning.
- No change to the world map, the local minimap, or the settlement/instance/interior layers' shapes.
- No new gameplay action, command, or persistence.
- No client-side persistence of a district overview across a committed map change.

## Decisions

### 1. A coarse district overview rides the existing wilderness body

Add a required nullable `district` field to the wilderness `area_map` body:

```json
{
  "district": {
    "key": "royal_river_valley",
    "name_zh": "王都河谷",
    "cell_km": 5,
    "window": {"min_x": 148, "min_y": 189, "width": 48, "height": 46},
    "rows": [[{"kind": "terrain", "length": 3, "terrain": "open_ground", "band": 2, "passable": true}, ...]]
  }
}
```

- `window` is in coarse cells (coarse x = km / `cell_km`); `rows` are south-to-north and cover the whole window.
- A terrain run carries exactly `terrain`, `band` (0..15) and `passable`; an unknown run is exactly `{kind, length}`. No nodes, entities, display labels, place names, or actionable descriptors are added.
- `name_zh` is bounded by `MAP_MAX_TITLE` (128), matching the top-level wilderness `district_name`, not the 256-label limit used by per-run display metadata.
- The overview is published only when the current cell's district is lit; otherwise `district` is `null`. This keeps unlit and sea/None cells under the existing fog.
- The window is aligned to the coarse grid and contains the current one-kilometre cell. It is clamped to the provider wilderness frame.

Why not expand the 41-cell window: the route window, gateway resolution, entity disclosure and client validator are defined on the centred 41-cell frame, and a full district at 1 km is millions of cells. A separate coarse layer preserves every existing invariant.

### 2. Adaptive kilometre ladder with a deterministic sample

Choose `cell_km` from `(1, 2, 5, 10, 20, 25, 50)`, finest first, subject to:

- coarse cells ≤ 8,192,
- encoded runs ≤ 4,096,
- overview section JSON ≤ 65,536 bytes.

Measured worst cases with centre-cell sampling fit comfortably: `royal_river_valley` at 5 km is 48 × 46 = 2,208 cells / 431 runs / ~31 KiB; `north_deep_forest` at 50 km is 42 × 17 = 714 cells / 286 runs / ~22 KiB; `oak_knolls` at 5 km is 55 × 54 = 2,970 cells / 575 runs / ~42 KiB. If no rung fits (future content), the server logs `area_map_district_overview_over_bound` and publishes `null`; the visible window still publishes.

Each coarse cell samples the one-kilometre cell at `(cx * cell_km + cell_km // 2, cy * cell_km + cell_km // 2)`. The integer floor is the exact rule for every rung, including even `cell_km`. To prevent a one-cell hole under the party at a boundary, the coarse cell containing the current one-kilometre cell is always terrain when the current cell's district is the published district. A data test asserts every shipped district produces at least one terrain run at its selected rung.

The encoder is a small generalisation of `encode_rows` that accepts the coarse width/height and the reduced fact set. Adjacent equal runs merge; unknown runs carry no fact.

### 3. Exact ownership bounds and a complete cache key

`district_bounds(key)` MUST come from the exact ownership raster in `frozen_partition()` (`coarse` tiles plus `exceptions`), not from the smoothed `district_outlines()`. The bounds are the tile-inflated box of every coarse tile carrying the district's owner code, clamped to the 0..2,700 frame. Inflating by a tile is deliberate: the box only has to contain every owned cell; the per-cell overview scan then keeps other owners unknown. A data test asserts that for every cell in the frame with `district_at(cell) is not None`, the cell lies inside `district_bounds(district_at(cell))`.

The overview depends only on the district, the committed partition, the elevation artifact, the sight policy and the static binding signature. Cache it with `@cache` keyed by `(binding_signature(), frozen_partition().fingerprint, elevation.current().fingerprint, id(sight.POLICY), district_key)`, mirroring `_TerrainOracle`'s dependency key. `binding_signature()` alone is insufficient because it does not hash the partition, elevation or sight policy, and tests mock those while the binding signature stays constant.

### 4. Area schema 4 with strict mirrored validation

Bump `AREA_MAP_SCHEMA_VERSION` from 3 to 4 in `web/webclient/presentation/map_panels.py` and `web/static/webclient/js/elosern/protocol/panels/map_panels.js`. The wilderness field set gains `district`; grid/instance/interior bodies keep their current shape under the new version. Both validators reject:

- an overview with unknown fields, an off-ladder `cell_km`, a `name_zh` over 128 code points, a window that does not contain the current cell, or a window outside `0..2700 // cell_km`,
- an unmerged or zero-length run, a wrong row count, a run total other than the window width,
- an unknown band, an out-of-vocabulary terrain class (including `sea`, which no owned cell can be), a non-boolean `passable`, or a section over 8,192 cells / 4,096 runs / 65,536 bytes.

The bidirectional parity test pins the constants and the new record shape. Old schema-3 wilderness bodies are rejected as before.

### 5. Client decoding, clipping and one explored grade

- `web/webclient-app/lib/wilderness-grid.js` reads schema 4 and gains `decodeDistrictOverview(area)`, returning the coarse origin, size, `cellKm`, and frozen runs in world coarse coordinates.
- `area_map_view.js` keeps `decodeWindow` for the fine window. Its fine `state` becomes `current` / `sighted` / `explored`: `sighted` uses the exact server disc `dx * dx + dy * dy <= (ground_radius + 0.5) ** 2`; every other revealed cell is `explored`, regardless of visit history. Node rows still carry `visited` for the trail and inspection, but they no longer brighten terrain.
- **Clipping:** the overview layer is cut out of the 41×41 fine-window rectangle in world coordinates. Without that clip, a 5–50 km coarse cell whose centre belongs to the lit district can bleed into a fine cell the server marked `unknown`, and two semi-transparent terrain layers plus the window fog would double-blend. The area map uses an SVG mask/clipPath on `windowDraw`; the travel overview canvas clears the fine window rectangle. The fine window keeps painting its own cells and fog.
- `AreaMapView.vue` draws the clipped overview before the window and uses the same `t-<terrain>` fills at the explored opacity; fine `sighted` cells use the bright opacity.
- `travel-grid.js` carries the decoded overview. `TravelMap.vue` adds an overview canvas behind the fine canvas inside the same world layer. `paintDistrictOverview` uses 2–4 samples per coarse cell (not 12), the same palette, and the same `PHASE_LOOK[lightPhase]` `desat`/`memory`/`wash` as the fine painter. Its repaint signature includes `lightPhase`; otherwise the district stays daytime-lit at night and no longer matches explored fine cells. The fine painter keeps its existing outside-sight desaturation, so both layers share one grade.
- The overview canvas repaints only when the overview content or `lightPhase` changes; camera, zoom and overlays move it with the world layer exactly as the fine canvas does.

### 6. A symbolic district-fit state, not a sub-18 zoom rung

The travel camera keeps its 18..46 px per one-kilometre cell ladder for local navigation and adds a separate symbolic `districtFit` state when an overview exists:

- The fit uses the **union of the overview window and the 41-cell window** and fits it inside `measured.safe` (not `stage`, so the vitals/medallions column and place card never hide district edges).
- The fit cell size is computed from the already-scaled safe rectangle and is not passed through `cellSize()`/`clampZoom()`, so `uiScale` is not applied twice and a fit value below 18 is not clamped back.
- At the fit state, the eight neighbour targets and single-click neighbour stepping are suppressed; `cellBox` clamps width/height to `>= 0`; the scale bar chooses a readable 50/100 km step; the party seal remains a location marker only.
- A locked route keeps `fitRouteCamera` authoritative; the district-fit state is the unlocked overview. Leaving fit returns to `ZOOM.min = 18`.
- A committed change to `district: null` or a different district key resets the state to 18 (or recomputes the fit) so no orphaned zoom survives a border crossing.
- The area-map drawer gains a `district` stop only when an overview is present: `wildernessStops`/`areaStops` fit the union of the overview and the 41-cell window, while the opening view stays on the surroundings. The existing `spanLimits` max is widened only for that stop.

### 7. Docs and design amendment

The sight-and-fog design says the area map publishes a 41-cell window; this change explicitly amends it to add the coarse district overlay while keeping the 41-cell live frame. `docs/development/map-panel-protocol.md` records schema 4, the overview record, the ladder, the sampling rule, the exact bounds and the caps. `web/webclient-app/AGENTS.md` records the two-layer wilderness rendering, the clip-out rule and the sight/explored rule.

## Risks / Trade-offs

- **Coarse resolution varies by district.** A region district uses 50 km cells while a capital district uses 5 km. The overview is far-context terrain, not a survey; the fine window and world map keep their roles. `cell_km` is on the wire so the client never guesses.
- **Boundary coarse cells are approximate.** A 5–50 km cell is terrain if its deterministic sample cell is owned; the clip-out of the fine window prevents that approximation from overwriting unrevealed fine cells. The coarse district silhouette can be one coarse cell generous or stingy at the border.
- **Fit state is a new camera mode.** It must not disturb follow/fit-route, pointer mapping, zoom chips, neighbour actions or the 50 ms repaint budget. Tests pin the union fit, the suppressed controls, the reset on district change and the fit/route precedence.
- **Cache invalidation.** The overview cache now includes the partition, elevation and sight-policy fingerprints; a change in any of them rebuilds the overview. The cache remains process-local and read-only.
- **Payload growth.** The overview adds at most ~65 KiB and the area body remains under the 384 KiB logical cap. The adaptive ladder and the omit-with-diagnostic fallback keep a future district bounded. Intact `ui_update` test helpers cap the whole envelope at 64 KiB, so near-ceiling fixtures travel through `encode_map_parts` instead.
- **Fog model changes inside the 41-window.** Previously, visited cells outside the sight disc were bright; now they are explored-grade. That is the requested model (walked memory and district reveal share one style) and does not change any action, entity or disclosure rule.
