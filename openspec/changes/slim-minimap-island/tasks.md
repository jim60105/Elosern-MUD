# Tasks — Slim Minimap Island

## 1. Shared renderer switch

- [x] 1.1 Add `showLegend: { type: Boolean, default: true }` to `MapLattice.vue`; render the legend `<ul data-testid="local-map__legend">` under `v-if="showLegend"` (DOM absent when false, not hidden).
- [x] 1.2 Pass `:show-legend="false"` from `LocalMap.vue`'s `<MapLattice>`; leave `MapOverlay.vue` untouched (default on).

## 2. Island chrome removal + budget

- [x] 2.1 In `LocalMap.vue` `measureCanvasBudget()`, remove the `legendEl` lookup and its `sectionHeight` term, and re-derive the gap count/slack for the remaining sections (meta, canvas, remembered?, detail); update the section-count comment.
- [x] 2.2 Confirm no island CSS/selectors reference the legend anymore (remove now-dead `.local-map` rules only if they targeted the island-side legend container).

## 3. Coordinate readout

- [x] 3.1 In `LocalMap.vue`, make `detailParts` append `座標 <x>,<y>` from the active node's payload `x`/`y` only when the active node is the `current` node and `layer` is `grid` or `wilderness`; keep existing content otherwise (graph layers and non-current nodes unchanged).
- [x] 3.2 Keep the header `北↑ 東→` marks gated on `layoutVariant === "lattice"` (no change needed; verify per amendment wording it now also carries the bearing statement).

## 4. Component + story updates

- [x] 4.1 Update Vitest `web/webclient-app/tests/world/local_map.test.js`: island renders no `local-map__legend`; budget arithmetic pins the reduced section list; detail line shows `座標 x,y` for current node on grid/wilderness, hides it for hovered non-current nodes and on graph layers.
- [x] 4.2 Update `web/webclient-app/tests/world/map_lattice.test.js`, `world/map_layout_variants.test.js`, `overlays/map_overlay.test.js` for the `showLegend` default (legend still rendered by default and by the overlay; add one mount asserting `show-legend=false` mounts no legend).
- [x] 4.3 Update stories `web/webclient-app/stories/World/LocalMap.stories.js` and `World/MapLattice.stories.js` so showcase stories exercise both switch positions (Storybook showcase-coverage manifest unchanged: no new components).

## 5. Browser contract updates

- [x] 5.1 In `web/tests/browser/test_browser_local_map.py`, flip island legend-presence assertions to island-absent/overlay-present, update the island-viewport budget scenario (title, orientation marks, remembered list, detail line — no state legend), and update the "island contains state legend" scenario per the amended requirement; keep the `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone` anchors on the shape-ladder assertions.
- [x] 5.2 Add/extend a browser assertion under `webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention`: on a grid payload the island header shows the orientation marks and the detail line shows `座標 <x>,<y>` matching the committed current node's payload coordinates; on an interior payload neither appears.

## 6. Verification

- [x] 6.1 `npm test` green (Vitest suites above).
- [x] 6.2 `npm run build-storybook && npm run showcase-coverage` green.
- [x] 6.3 Managed browser class for `test_browser_local_map.py` green locally within the one-class budget (or defer full run to CI per repo policy if it exceeds budget). All five changed/affected test methods ran green locally (~3.5 min across two managed-server batches); the remaining unchanged class methods defer to CI per the one-class budget.
- [x] 6.4 `uv run --locked python -m tools.spec_traceability check` green (no ID renames; anchors still on substantively-matching tests).
- [x] 6.5 `openspec validate slim-minimap-island --strict` green.
