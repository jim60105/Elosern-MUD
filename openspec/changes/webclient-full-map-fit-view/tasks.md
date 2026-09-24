## 1. Preconditions

- [x] 1.1 Confirm that `webclient-minimap-and-log-quick-fixes` (C1) is applied. Check each of the following, and stop and report if any fails, because this change edits C1's text and code:
  - `grep -n "canvasSize" web/webclient-app/components/MapLattice.vue` finds the prop.
  - `grep -n "fieldFill" web/webclient-app/components/MapLattice.vue` finds nothing.
  - `grep -n "map-overlay-remembered" web/webclient-app/components/MapOverlay.vue` finds the list.

## 2. Pure view math (design D1–D4)

- [x] 2.1 Create `web/webclient-app/lib/map_view.js`, a dependency-free ES module.
  - Export `FIT_INSET = 12`, `MAX_SCALE = 2`, `ZOOM_STEP = 1.25`, and `DRAG_THRESHOLD = 4`.
  - Export the pure functions over a view `{ s, x, y, fitted }` and a frame `{ vw, vh, W, H }`, as design D2 / D3 define them:
    - `fitView(frame)`: `s = min(1, (vw − 2·FIT_INSET)/W, (vh − 2·FIT_INSET)/H)`, centred, `fitted: true`
    - `scaleBounds(frame)`
    - `clampView(view, frame)`: centre an axis whose visible span is at least the canvas, otherwise clamp the origin to `[0, W − vw/s]`
    - `zoomAt(view, factor, anchorPx, frame)`: the anchor point is invariant, then clamp
    - `panBy(view, dxPx, dyPx, frame)`
    - `centreOn(view, point, frame)`
    - `revealBox(view, box, marginPx, frame)`: minimal shift at the same scale
    - `resizeView(view, oldFrame, newFrame)`: refit when fitted, otherwise keep the centre point and clamp the scale
    - `viewBoxOf(view, frame)`: returns `"x y vw/s vh/s"`
  - Every operation other than `fitView` returns `fitted: false`, except `clampView` and `resizeView`, which keep the flag.
  - The file header comment cites this change's design D1–D4.
- [x] 2.2 Create `web/webclient-app/tests/world/map_view.test.js` with these cases:
  - the fit of the 560 × 1074 street in a 1124 × 735 frame: `s ≈ 0.662`, and the whole canvas inside the frame less the inset
  - a 280 × 226 single node: `s = 1`, centred on both axes
  - `zoomAt` keeps the anchor's user point under the anchor
  - repeated zoom-out stops at the fitted scale, and repeated zoom-in stops at 2
  - `panBy` stops at each canvas edge and cannot pan an axis the canvas does not overflow
  - `centreOn` of a corner node clamps
  - `revealBox` moves the minimum distance and leaves an already-visible box untouched
  - `resizeView` refits a fitted view and preserves the centre of a touched one
  - the `fitted` flag transitions
  
  Run `pnpm exec vitest run web/webclient-app/tests/world/map_view.test.js` (repository root) green.

## 3. Renderer: fitted view, no caps, no legend (design D1, D3, D5, D6)

- [x] 3.1 Create `web/webclient-app/composables/use-map-view.js`, exporting `useMapView({ enabled, canvasWidth, canvasHeight, currentPos, nodePos, currentNodeId, viewportEl, markerScale, labelFont })`.
  - It owns a `view` ref (`null` until the viewport has a non-zero box) and a ResizeObserver on `viewportEl`, guarded where `ResizeObserver` is undefined as in jsdom.
  - It returns `viewBox` (the whole canvas `0 0 W H` while `view` is null), `canZoomIn`, `canZoomOut`, `canRecentre`, `zoomIn()`, `zoomOut()`, `recentre()`, and the handlers `onWheel`, `onPointerDown`, `onPointerMove`, `onPointerUp`, `onPointerCancel`, `onClickCapture`, and `onFocusIn`, all as design D3 specifies:
    - the wheel factor is `exp(−deltaY × 0.0015)`, normalised by `deltaMode` and clamped to [0.5, 2]
    - the drag threshold comes from `DRAG_THRESHOLD`
    - `setPointerCapture` is called on drag
    - a one-shot `suppressClick` is cleared by `setTimeout(0)`
    - `onFocusIn` reveals a `[data-node]` target's box with a 24px margin
  - It watches `[canvasWidth, canvasHeight, currentNodeId]` for the payload rules in design D4: refit when fitted, `centreOn` the new current node when the current id changed on a touched view, and clamp otherwise.
  - Remove the observer in `onBeforeUnmount`.
- [x] 3.2 `web/webclient-app/components/MapLattice.vue`:
  - Add `fitView: { type: Boolean, default: false }`, with a comment citing design D1.
  - When it is on:
    - the viewport div gets the class `local-map__viewport--fit` and a `ref`, and binds `@wheel.prevent`, `@pointerdown`, `@pointermove`, `@pointerup`, `@pointercancel`, `@click.capture`, and `@focusin` from `useMapView`
    - the SVG binds `:viewBox` from `useMapView` and keeps its `width` / `height` attributes
    - `defineExpose({ zoomIn, zoomOut, recentre, canZoomIn, canZoomOut, canRecentre })`
  - When it is off, the SVG `viewBox` stays `0 0 canvasWidth canvasHeight`, or C1's square origin on a `canvasSize` surface.
  - Delete:
    - the `maxWidth`, `maxHeight`, `fillWidth`, and `showLegend` props and their comments
    - the legend `<ul>` and its comment
    - the `local-map__viewport--canvas` class binding
    - the stale "overlay scrolls the diagram" template comment
  - Update the header comment.
- [x] 3.3 `web/webclient-app/composables/use-map-lattice-geometry.js`:
  - Delete `widthCaps()` and the `fillWidth` / cap lines of `latticeStyle`. `latticeStyle` returns C1's `canvasSize` square style, or `{ width: "100%", height: "100%" }` when `props.fitView`, or `{}`.
  - Delete the long cap comment above `widthCaps`, and remove `legend` from the returned object if nothing else reads it.
  - `web/webclient-app/composables/use-map-lattice-render.js`: delete `LEGEND_STATES` / `legendState` and their return entry.
  - Check: `grep -rn "widthCaps\|fillWidth\|fill-width\|maxHeight\|max-height=\|showLegend\|show-legend\|legendState" web/webclient-app --include='*.vue' --include='*.js'` (excluding `dist/`) finds only the `legendState` that section 4 moves into `MapOverlay.vue`.
- [x] 3.4 `web/webclient-app/components/map-lattice.css`:
  - Delete `.local-map__viewport--canvas` and `.local-map__viewport--canvas > svg`, and delete every `.local-map__legend*` rule. Those rules move in task 4.2.
  - Add `.local-map__viewport--fit { display: block; position: relative; width: 100%; height: 100%; min-height: 0; overflow: hidden; cursor: grab; touch-action: none; }`, plus a `--dragging` modifier with `cursor: grabbing`. Use no transition property.
  - Update the `.local-map__lattice` comment that mentions caps.
- [x] 3.5 `web/webclient-app/components/LocalMap.vue`: delete the `:show-legend="false"` binding and its comment. Check with `grep -n "show-legend" web/webclient-app/components/LocalMap.vue`, which returns nothing.

## 4. Overlay: fitted layout, toolbar, legend popover (design D2, D3, D5, D7)

- [x] 4.1 `web/webclient-app/components/MapOverlay.vue` script:
  - Delete `revealCurrentNode`, the `body` ref, `onMounted` / `watch` / `currentNodeId`, and their comment and imports.
  - Add a `latticeRef`, the `legendOpen` ref, and `legendState(index)`, moved from `use-map-lattice-render.js` with its comment.
  - Add `onKeydown(event)` on the root:
    - Escape with `legendOpen` closes the popover and calls `stopPropagation()`.
    - `+`, `=`, and `Add` with no Ctrl, Meta, or Alt call `latticeRef.value.zoomIn()` and `preventDefault()`.
    - `-`, `_`, and `Subtract` call `zoomOut()`.
  - Add `onPointerDownOutside`, which closes the popover when the target is outside the popover and its toggle and does not stop the event.
  - Update the header comment, which currently says "reused MapLattice at the overlay's own larger scale".
- [x] 4.2 Same file, template and style:
  - The root is `.map-overlay-body` with `@keydown` and `@pointerdown.capture`.
  - `.map-overlay__content` is a grid with `grid-template-rows: auto minmax(240px, 1fr) auto` at `height: 100%`.
  - The guide row keeps the hint `點選可通行的相鄰節點，繼續探索。` and the span `Tab 切換路徑 · Enter 確認移動 · 滾輪或 +／− 縮放 · 拖曳平移`, and adds `<div class="map-overlay__toolbar" role="group" aria-label="地圖檢視">` with four `<button type="button">`s:
    - `data-testid="map-overlay-zoom-out"`, `aria-label="縮小"`, showing `−`
    - `map-overlay-zoom-in`, `aria-label="放大"`, showing `+`
    - `map-overlay-recentre`, with the text `置中`
    - `map-overlay-legend-toggle`, `aria-label="圖例"`, showing `?`, with `:aria-expanded="legendOpen"` and `aria-controls` pointing at the popover id from `useId()`
  - Each view button binds `:aria-disabled` from the exposed `canZoomIn` / `canZoomOut` / `canRecentre`. None uses `disabled`.
  - The viewport cell is `position: relative`. It holds `MapLattice` with `ref="latticeRef"` and `:fit-view="true"`, and without `max-width`, `max-height`, or `fill-width`. It also holds the popover `<div v-if="legendOpen" :id … class="map-overlay__legend-popover" data-testid="map-overlay-legend-popover" role="group" aria-label="圖例">`, which contains the legend `<ul class="local-map__legend" data-testid="local-map__legend">` with the markup moved from `MapLattice.vue` (`legend` read from `localMap.legend`). The popover is absolutely positioned at the top right with `z-index: 1`, which is local to the viewport cell's stacking context.
  - C1's `map-overlay-remembered` list is the third row.
  - Move the `.local-map__legend*` chip rules from `map-lattice.css` into this file's scoped style, token-only. Delete `:deep(.local-map__viewport--canvas)`, `:deep(.local-map__legend)`, and every `max-width: 848px`.
  - Check with `grep -n "848\|scrollIntoView\|revealCurrentNode" web/webclient-app/components/MapOverlay.vue`, which returns nothing, and verify with `pnpm run build`.
- [x] 4.3 Stories:
  - `web/webclient-app/stories/Overlays/MapOverlay.stories.js`: add a `TallLattice` story bound to `LOCAL_MAP_GEOMETRY_STRESS_SAMPLE` through `localMapModelFor`, and update the header comment to say that the overlay opens fitted inside its stage.
  - `web/webclient-app/stories/World/MapLattice.stories.js`: `renderOverlayScale` drops `maxWidth` / `maxHeight` / `fillWidth`, passes `fitView: true` inside an `848 × 560` box, and says in its comment that the island-scale stories no longer set caps (C1 passes `canvasSize`).
  - Run `pnpm run build-storybook` and `pnpm run showcase-coverage` green. No story title changes, so `component-manifest.json` stays as it is.

## 5. Tests

- [x] 5.1 `web/webclient-app/tests/overlays/map_overlay.test.js`:
  - In "renders the shared lattice in the overlay body…", assert that there is no `local-map__legend` before the toggle is clicked, and that there is one after.
  - In "renders the draft overlay chrome…", open the popover before asserting `.local-map__legend-chip--current`.
  - Add these cases:
    - the four toolbar buttons with their accessible names
    - `aria-expanded` toggling
    - Escape with the popover open closes it and does not propagate. Mount inside a parent that records keydown, and assert that no Escape reaches it.
    - Escape with the popover closed propagates
    - a pointer press outside the popover closes it
    - `+` / `-` call the exposed `zoomIn` / `zoomOut`. Spy through the `MapLattice` component instance.
    - the `MapLattice` child receives `fitView: true` and no `maxWidth` prop
  - Move the three legend cases from `tests/world/map_lattice_legend_labels.test.js` into this file, mounting `MapOverlay` and opening the popover: "pairs every legend entry with a dot chip at both scales" (overlay scale only), "renders a fifth beyond-state entry as a neutral info chip, text intact", and "styles every entry beyond the fourth as info, for any payload".
  - Run the file green.
- [x] 5.2 `web/webclient-app/tests/world/map_lattice_renderer.test.js`:
  - Delete "mounts no legend element when the legend switch is off", and drop the `local-map__legend-item--` count from both "renders identical node/edge/legend content…" cases.
  - In the overlay case, replace the `width: 100%` / `maxWidth: 848px` style assertions with an unstyled natural-size assertion.
  - Add "fitView fills its viewport and windows the whole canvas before layout": the style is `width: 100%` and `height: 100%`, the `viewBox` is `0 0 canvasWidth canvasHeight`, and the viewport carries `local-map__viewport--fit`.
  - Add "a drag past the threshold never emits move": dispatch `pointerdown` on an actionable node, `pointermove` by 12px, `pointerup`, then `click`, and assert that no `move` event is emitted. A 2px move followed by a click emits `move` once.
  - `web/webclient-app/tests/world/map_lattice_legend_labels.test.js`: delete the three moved legend cases, and update the header comment.
- [x] 5.3 Fixture churn: delete the `maxWidth` / `maxHeight` / `fillWidth` / `showLegend` keys from these files:
  - `web/webclient-app/tests/world/map_lattice_support.js`
  - `map_layout_variants.test.js`, where you also drop the two `local-map__legend-item--` count assertions in "draws the same committed content in both layouts"
  - `map_lattice_fidelity.test.js`, where "Task 2.4" becomes a natural-size assertion with no `max-width` style, and "Task 1.1" / "Task 2.6" keep their pinned widths and heights
  - `map_lattice_name_fit.test.js`
  - `local_map.test.js` (C1's rewritten cases)
  
  Check with `grep -rn "maxWidth\|maxHeight\|fillWidth\|showLegend" web/webclient-app/tests web/webclient-app/stories`, which returns nothing. Run `pnpm test` green.
- [ ] 5.4 Browser tests:
  - `web/tests/browser/test_browser_local_map_rendering.py` (around line 104): click `map-overlay-legend-toggle` before reading `local-map__legend`.
  - `web/tests/browser/test_browser_local_map_interaction.py`, `test_overlay_renders_scale_note_as_neutral_info_entry`: click the toggle before collecting `local-map__legend-item--*`.
  - `web/tests/browser/test_browser_local_map_lattice.py`: re-run `test_crowded_edge_overlay_marker_names_stay_separated_and_outside_canvas`. If it pins an absolute pixel box, scale that figure by the SVG's `getScreenCTM().a` rather than restoring width caps.
  - Run the three modules with `uv run --locked python -m unittest web.tests.browser.<module>` green.
- [ ] 5.5 Add `test_full_map_opens_fitted_zooms_pans_and_recentres` to `web/tests/browser/test_browser_local_map_interaction.py`, decorated `@covers_requirement("webclient-local-map::the-full-map-surface-opens-fitted-to-its-body-and-offers-zoom-pan-and-recentre")`. Use `logged_in_page(viewport=(1920, 1080))`, inject a two-column, five-row grid payload through `_inject_panel`, and open the map with `store.openOverlay('map')`. The test asserts:
  - Every `[data-node]` box and every `.local-map__edge-marker` box is inside the `.local-map__viewport--fit` box, and `overlay-host-body` has `scrollHeight <= clientHeight + 1`.
  - `page.mouse.wheel(0, -400)` over the current node grows its box and keeps its centre within 2px of the pointer.
  - Pressing `-` until `map-overlay-zoom-out` has `aria-disabled="true"` returns every node inside the viewport.
  - A drag from an actionable node by 120px moves the node boxes and sends no `explore.move`. Record sends with `install_outbound_recorder` / `sent_action_count` from `browser_helpers`, as `test_adjacent_traversable_node_submits_explore_move` does.
  - After panning the current node out of view, `map-overlay-recentre` puts its centre within 2px of the viewport centre, or as close as the clamp allows.
  - Tabbing to an off-window actionable node brings its box inside the viewport.
  - The popover opens with an unchanged viewport box, the first Escape closes only the popover, and the second closes the overlay.
  - Reopening the map shows the fitted view with the popover closed.
  
  Run the module green.
- [ ] 5.6 In `web/tests/browser/test_browser_contextual_hud_stage.py`, `test_h5_overlay_triggers_exclusion_and_focus_restoration`, which is already annotated for the overlay requirement: add the two-Escape precedence check with the map overlay's legend popover open. The test is also annotated `webclient-contextual-hud::the-map-settings-and-help-surfaces-are-reachable-from-the-live-client`, so in its map-overlay step also assert that the open map surface's only view controls are `map-overlay-zoom-out`, `map-overlay-zoom-in`, `map-overlay-recentre`, and `map-overlay-legend-toggle`, each with its accessible name, that the guide row names the gestures, and that no text on the surface matches a zoom-level or scale figure (`/\d+\s*%|×\s*\d/`). Both IDs are unchanged, so no annotation is re-anchored. Run the module green.
- [ ] 5.7 `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js`: map zoom and pan are no longer deferred.
  - Delete the `/\bZoom\b/i` and `/\bPan\b/i` entries from `DEFERRED_TITLE_PATTERNS`, and delete the comment line "map zoom/pan (the map surface ships no zoom or pan affordance)".
  - Add a one-line note, in the style of the retired `\bBag\b` case, saying that `webclient-full-map-fit-view` retired the map zoom/pan deferral.
  - Run `pnpm exec vitest run web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js` green.

## 6. Spec sync and validation

- [ ] 6.1 After C1 has been archived, sync this change's deltas into `openspec/specs/webclient-local-map/spec.md` and `openspec/specs/webclient-contextual-hud/spec.md`. Then run `uv run --locked python -m tools.spec_traceability check` green. The only new ID is the fit-view requirement, which task 5.5 covers, and every modified title is unchanged.
- [ ] 6.2 Run these gates, all green:
  - `node --test web/static/webclient/js/tests/*.test.js` (no model change is expected)
  - `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root)
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - the browser modules `test_browser_local_map_interaction`, `test_browser_local_map_rendering`, `test_browser_local_map_lattice`, `test_browser_local_map_layout_variants`, `test_browser_local_map_geometry`, `test_browser_contextual_hud_stage`, and `test_browser_contextual_hud_anchors` via `uv run --locked python -m unittest web.tests.browser.<module>`
- [ ] 6.3 Take 1920 × 1080 screenshots of the full map on the guild hall (interior, with remembered rooms), a two-column, five-row street, and a wilderness cell with named edge markers. In each, confirm that the whole map is visible on open with no body scrollbar and that the legend shows only in the `?` popover. Then run `openspec validate webclient-full-map-fit-view --strict` and `git diff --check`, both clean.
