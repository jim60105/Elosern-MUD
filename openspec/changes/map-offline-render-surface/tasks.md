# Tasks

## 1. Shared drawing cutover

- [x] 1.1 Extract shared SVG/raster/glyph/card/link drawing from `MapCanvas.vue` into `MapSurface.vue` while keeping pointer/keyboard interactions and workbench overlays in the interactive host; add synthetic drawing assertions and confirm the existing focused editor browser interaction checks still establish selection, pan, zoom and one editable-mark move.
  - `MapSurface.vue` owns the dot field, terrain raster, shapes, links and marks; `MapCanvas.vue` keeps the camera, chrome, pointer/wheel/keyboard handling and drag drafts and forwards `mark-select`/`mark-key`.
  - Synthetic drawing assertions are real painted geometry in `web/tests/browser/test_map_capture_surface.py`; the pure scene/layer transforms are in `tools/map-editor/frontend/tests/capture.test.mjs`. No DOM toolchain was added to the Node suite (the design assigns painted geometry to the browser assertions).
  - `MapSurfaceEditorSmokeBrowserTest.test_selection_pan_zoom_and_one_mark_move_still_work` drives selection, an exact pointer pan (nothing written), a wheel zoom with one uniform factor and one anchor, a wheel restore, and one node drag = one `move_nodes` command changing only the settlement document. The pre-existing `test_map_editor_standalone.MapEditorStandaloneBrowserTest` and `test_map_editor_geography.MapEditorGeographyBrowserTest.test_clicking_a_feature_shape_selects_it_and_shows_its_handles` still pass unchanged.
- [x] 1.2 Add the map-only host with empty selection and no mutation/control surfaces, using existing local colors/fonts/background; add discoverable `test_map_capture_surface.py` assertions for inert hostile labels, no network fetch and map-only composition, and update `docs/development/map-editor.md` with shared-surface ownership.
  - `capture/index.html`, `src/capture.js`, `src/components/CaptureApp.vue`, `src/styles/capture.css`; `docs/development/map-editor.md` §10.1.

## 2. Capture camera and visibility

- [x] 2.1 Implement capture coordinate/camera helpers over existing scene builders, preserving road bends, deterministic missing-position fallback and exterior cards; add Node and real-render assertions for km/local-m/layout frames, interior Y inversion, explicit aspect expansion/centre/containment, empty/outside bounds, exact viewport dimensions and full-fit painted label/card containment.
  - `src/lib/capture.js` (`sceneFrameBounds`, `frameBoundsOf`, `expandToAspect`, `viewOfBox`, `boxOfView`, `fitView`, `sceneExtent`, `convergeFit`).
  - Node: `tests/capture.test.mjs` (frames, aspect/centre, empty and out-of-map regions, bends/raster/cards in the extent, bounded convergence). Render: `test_the_continent_camera_converts_kilometres_and_keeps_one_scale`, `test_the_interior_camera_reports_down_positive_layout_units`, `test_a_full_fit_keeps_cards_and_measured_labels_inside_the_image`.
- [x] 2.2 Implement the complete per-view layer classification, including national borders on partition, all-on defaults, geometry-owned labels and independent links/direction indicators; add synthetic rendered visibility assertions for every layer, labels alone, all-hidden background and camera stability, and document coordinate/visibility behavior beside the developer entry description.
  - `captureScene`/`normalizedHidden` in `src/lib/capture.js`; rendered evidence in `test_every_continent_layer_hides_exactly_its_own_geometry` (every continent layer owns disjoint drawables and the camera never moves), `test_hidden_geometry_takes_only_its_own_labels`, `test_hiding_labels_keeps_cards_glyphs_and_direction_indicators`, `test_settlement_nodes_and_roads_are_independent`, `test_everything_hidden_leaves_the_background_at_the_same_camera`.
  - `docs/development/map-editor.md` §10.2 and §10.3.

## 3. Offline entry and final integration

- [x] 3.1 Add the separate `build:capture` Vite config/output and structured `renderMapCapture(payload)` Promise contract with local classic-script/CSS/font assets and font/image/layout/paint readiness; add a real file-navigation browser test proving the three views render with all HTTP traffic denied and missing/delayed assets reject or remain unready rather than falsely completing, and document build/setup commands.
  - `vite.capture.config.js` (capture root, relative `base`, IIFE entry, `cssCodeSplit: false`, and a `generateBundle` step that drops the module type and CORS markers a `file://` page cannot honour), `package.json` `build:capture`, `.gitignore`.
  - `test_each_view_renders_from_a_file_page_with_network_denied`, `test_readiness_waits_for_fonts_and_layout`, `test_a_delayed_local_font_holds_readiness_until_it_arrives`, `test_a_page_whose_script_is_missing_never_reports_readiness`, `test_malformed_requests_reject_without_a_partial_render`; `docs/development/map-editor.md` §1.2.
- [x] 3.2 Register every new managed browser method in `.github/browser-shards.json`; associate each new requirement with a discoverable substantive browser test using canonical IDs from the equivalent merged spec tree, recording any meaningful provisional nearest-current associations while active; completion is zero uncovered requirements after sync without guessed identifiers or data/copy/markup-pinning assertions.
  - Both classes are registered once, in shard 1 `files_a`; `tests.test_evennia_test_optimization_contract.TestOwnershipContractTests.test_browser_method_labels_preserve_exact_ownership` passes.
  - Canonical-ID association is deliberately deferred to the archive step: `map-offline-rendering` has no canonical requirement IDs until the archive syncs the main spec, and this change adds no `covers_requirement` annotation. The provisional association is recorded below instead of guessed into code.
- [x] 3.3 Run the focused `frontend/tests/capture.test.mjs`, import-boundary gate, capture and normal editor builds, one affected capture browser class and the smallest existing editor interaction class; record actual inspected synthetic images and human composition/Traditional Chinese glyph review in `docs/development/map-editor.md`, then run `openspec validate map-offline-render-surface --strict` and `uv run --locked python -m tools.contract_gate` from root. Full managed-browser and complete evidence runs stay CI-owned.
  - `node --test tests/capture.test.mjs` 15/15; `pnpm test` 118/118; `node scripts/import-boundary.mjs` 51 sources, 0 violations; `pnpm run build` and `pnpm run build:capture` clean; `test_map_capture_surface` 16/16; `MapEditorStandaloneBrowserTest` + the geography selection method pass; `openspec validate --strict` valid; `tools.contract_gate` passed all six stages.
  - Human review recorded in `docs/development/map-editor.md` §10.5.

## Provisional requirement association (for the archive step)

No `covers_requirement` annotation is attached while this change is active. When the archive step creates the canonical `map-offline-rendering` requirement IDs, associate them with:

| Delta requirement | Discoverable substantive owner |
| --- | --- |
| Offline map rendering is isolated and map only | `web.tests.browser.test_map_capture_surface.MapCaptureSurfaceBrowserTest.test_each_view_renders_from_a_file_page_with_network_denied`, `...test_authored_text_and_url_like_names_stay_inert`, `web.tests.browser.test_map_capture_surface.MapSurfaceEditorSmokeBrowserTest.test_selection_pan_zoom_and_one_mark_move_still_work` |
| Capture cameras preserve coordinate frames and requested extent | `...MapCaptureSurfaceBrowserTest.test_the_continent_camera_converts_kilometres_and_keeps_one_scale`, `...test_the_interior_camera_reports_down_positive_layout_units`, `...test_a_full_fit_keeps_cards_and_measured_labels_inside_the_image` |
| Capture visibility is view scoped and independent | `...MapCaptureSurfaceBrowserTest.test_every_continent_layer_hides_exactly_its_own_geometry`, `...test_hidden_geometry_takes_only_its_own_labels`, `...test_hiding_labels_keeps_cards_glyphs_and_direction_indicators`, `...test_settlement_nodes_and_roads_are_independent`, `...test_everything_hidden_leaves_the_background_at_the_same_camera` |
