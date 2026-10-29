# Tasks

## 1. Shared drawing cutover

- [ ] 1.1 Extract shared SVG/raster/glyph/card/link drawing from `MapCanvas.vue` into the map-surface owner while keeping pointer/keyboard interactions and workbench overlays in the interactive host; add synthetic drawing assertions and confirm the existing focused editor browser interaction checks still establish selection, pan, zoom and one editable-mark move.
- [ ] 1.2 Add the map-only host with empty selection and no mutation/control surfaces, using existing local colors/fonts/background; add discoverable `test_map_capture_surface.py` assertions for inert hostile labels, no network fetch and map-only composition, and update `docs/development/map-editor.md` with shared-surface ownership.

## 2. Capture camera and visibility

- [ ] 2.1 Implement capture coordinate/camera helpers over existing scene builders, preserving road bends, deterministic missing-position fallback and exterior cards; add Node and real-render assertions for km/local-m/layout frames, interior Y inversion, explicit aspect expansion/centre/containment, empty/outside bounds, exact viewport dimensions and full-fit painted label/card containment.
- [ ] 2.2 Implement the complete per-view layer classification, including national borders on partition, all-on defaults, geometry-owned labels and independent links/direction indicators; add synthetic rendered visibility assertions for every layer, labels alone, all-hidden background and camera stability, and document coordinate/visibility behavior beside the developer entry description.

## 3. Offline entry and final integration

- [ ] 3.1 Add the separate `build:capture` Vite config/output and structured `renderMapCapture(payload)` Promise contract with local classic-script/CSS/font assets and font/image/layout/paint readiness; add a real file-navigation browser test proving the three views render with all HTTP traffic denied and missing/delayed assets reject or remain unready rather than falsely completing, and document build/setup commands.
- [ ] 3.2 Register every new managed browser method in `.github/browser-shards.json`; associate each new requirement with a discoverable substantive browser test using canonical IDs from the equivalent merged spec tree, recording any meaningful provisional nearest-current associations while active; completion is zero uncovered requirements after sync without guessed identifiers or data/copy/markup-pinning assertions.
- [ ] 3.3 Run the focused `frontend/tests/capture.test.mjs`, import-boundary gate, capture and normal editor builds, one affected capture browser class and the smallest existing editor interaction class; record actual inspected synthetic images and human composition/Traditional Chinese glyph review in `docs/development/map-editor.md`, then run `openspec validate map-offline-render-surface --strict` and `uv run --locked python -m tools.contract_gate` from root. Full managed-browser and complete evidence runs stay CI-owned.
