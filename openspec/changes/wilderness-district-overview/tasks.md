# Tasks

## 1. Exact bounds and server overview data

- [x] 1.1 Add an exact-ownership `district_bounds(key)` to the partition codec and `world/maps/district_partition.py` using the decoded `coarse` tiles and `exceptions` (tile-inflated, frame-clamped), never the smoothed outlines; add a data test that every owned cell in the 2,700 frame lies inside its own district bounds.
- [x] 1.2 Add the overview builder beside the wilderness presenter: cached per `(binding_signature(), frozen_partition().fingerprint, elevation.current().fingerprint, id(sight.POLICY), district_key)`, `(1,2,5,10,20,25,50)` km ladder, sample at `cell_km // 2` from the coarse origin, force the party's coarse cell to terrain, centre-cell ownership sampling, terrain/band/passable facts and merged south-to-north RLE rows.
- [x] 1.3 Publish `district` in the wilderness body only when the current cell's district is lit; publish `null` otherwise, and log `area_map_district_overview_over_bound` plus `null` if no ladder rung fits the 8,192-cell / 4,096-run / 65,536-byte bounds.
- [x] 1.4 Add the overview constants and the strict `district` record validator to `web/webclient/presentation/map_panels.py`; bump `AREA_MAP_SCHEMA_VERSION` to 4, include `district` in the wilderness field set, and reject `sea` terrain, names over 128 code points, off-frame windows and a window missing the current cell.

## 2. Wire parity and server tests

- [x] 2.1 Mirror schema 4, the overview field, the ladder, the caps, the name bound and the record rules in `web/static/webclient/js/elosern/protocol/panels/map_panels.js`, including the exact `MAP_CONSTANTS` names used by the parity test.
- [x] 2.2 Extend `web/webclient/presentation/tests/test_map_panel_protocol.py` and the Node protocol suite with schema-4 parity, accepted overviews, every malformed rejection and the intact-envelope byte fallback.
- [x] 2.3 Extend `web/webclient/presentation/tests/test_area_map.py` (and `web/tests/browser/browser_helpers.py` fixtures if needed) with lit/unlit/sea publication, boundary/current-cell containment, exact ownership, adjacent-owner and hidden-anchor cover, even-rung sampling, every-district-fits, cache invalidation on partition/elevation/policy changes, read-only behavior and the over-bound fallback; annotate the new requirements with `covers_requirement`.

## 3. Client decoding, clipping and styling

- [x] 3.1 Bump the wilderness schema constant and add the shared `decodeDistrictOverview` decoder in `web/webclient-app/lib/wilderness-grid.js`, including its bounds and rejection rules.
- [x] 3.2 Change `web/webclient-app/lib/area_map_view.js` fine-cell states to `current`/`sighted`/`explored` using `dx*dx + dy*dy <= (ground_radius + 0.5)**2`, and expose the clipped district overview to the view.
- [x] 3.3 Extend `web/webclient-app/lib/travel-grid.js` with the decoded overview and add `paintDistrictOverview` in `web/webclient-app/lib/travel-paint.js` at 2–4 samples per coarse cell, with the shared palette and `PHASE_LOOK[lightPhase]` desat/memory/wash; include `lightPhase` in its repaint signature.
- [x] 3.4 Render the overview behind the fine window in `AreaMapView.vue` via an SVG mask/clipPath that cuts out `windowDraw`, and behind the fine canvas in `TravelMap.vue` while clearing the fine-window rectangle; keep one explored style for district-revealed and previously-walked cells outside live sight.
- [x] 3.5 Add the `district` wilderness stop in `map_stops.js`/`area_map_view.js` that fits the union of the overview and the 41-cell window, keeps `openingView` on the surroundings, and leaves a payload without an overview on the existing stops and limits.

## 4. Travel camera district-fit state

- [x] 4.1 Add a symbolic `districtFit` state in `TravelMap.vue`/`travel-camera.js` that fits the union of the overview and 41-cell windows inside `measured.safe`, computes from the already-scaled safe rectangle (no `cellSize()`/`clampZoom()` double scaling) and does not clamp the fit back to 18.
- [x] 4.2 At the fit state, clamp `cellBox` width/height to `>= 0`, suppress the eight neighbour targets and single-click stepping, choose a readable 50/100 km scale-bar step, and keep the party seal as a location marker only.
- [x] 4.3 Keep `fitRouteCamera` authoritative for a locked route; reset `districtFit` to 18 when the committed overview becomes `null` or names a different district; update `webclient-travel-map` tests for fit/route precedence, reset and safe-area bounds.

## 5. Client tests, fixtures and stories

- [x] 5.1 Extend the Vitest window/travel suites and the Node decoder tests with schema-4 overview decoding, malformed sections, the sight/explored rule, clip-out compositing, light-phase repaint and the district-fit state.
- [x] 5.2 Update every schema-3 fixture and assertion named by the review: `web/webclient/presentation/tests/test_area_map.py` (`PresenterSpec`, `_largest_grid_body`), `web/tests/browser/browser_helpers.py` and `web/tests/browser/test_wilderness_travel.py` (`_area`, `_BENCH`), `web/webclient-app/stories/fixtures/travel_walk.js`, `travel_grid.js`, `area_map.js`, `web/static/webclient/js/tests/map_panel_fixtures.js`, `web/webclient-app/tests/travel/window.test.js`, and the `.is-remembered`/`.is-visited` assertions in `web/webclient-app/stories/World/AreaMapView.stories.js` and `web/webclient-app/tests/world/area_map_view.test.js`.
- [x] 5.3 Add the traceability partners: `covers_requirement` in `web/webclient/presentation/tests/test_map_panel_protocol.py`, `tests/test_map_client_contracts.py::AreaViewContracts` with a matching top-level `describe` in `web/webclient-app/tests/world/area_map_view.test.js`, and `web/tests/browser/test_wilderness_travel.py::TravelMapTests` for the overview and camera requirements.
- [x] 5.4 Add or update Storybook fixtures and play assertions for a lit-district overview behind the local window, the clipped fine window, the district-fit state and an unlit body with `district: null`; keep intact fixtures under the 64 KiB `ui_update` envelope cap or use `encode_map_parts`.

## 6. Documentation and contracts

- [x] 6.1 Amend `docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md` to record the coarse district overlay, exact bounds, clipping and the 41-cell live frame.
- [x] 6.2 Update `docs/development/map-panel-protocol.md` with schema 4, the overview record, the ladder, the sampling rule, the exact bounds, the caps and the integrity constraints.
- [x] 6.3 Update `web/webclient-app/AGENTS.md` with the two-layer wilderness rendering, the clip-out rule, the sight/explored styling and the district-fit camera state.

## 7. Verification

- [x] 7.1 Run the focused Python area-map, protocol and traceability tests plus `uv run --locked python -m tools.spec_traceability check`.
- [ ] 7.2 Run the focused Node protocol tests, the focused Vitest suites and `uv run --locked python -m tools.contract_gate`; inspect a real rendered wilderness screen with a lit district at the local, district-fit and area-map stops.
- [x] 7.3 Run `openspec validate wilderness-district-overview --strict` and update `.github/evennia-shards.json` only if a test module was added.
