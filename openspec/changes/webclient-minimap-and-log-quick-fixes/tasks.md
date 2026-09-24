## 1. Renderer: fixed square canvas (design D1, D3, D4)

- [x] 1.1 `web/webclient-app/components/MapLattice.vue`: delete the `fieldFill` prop and its comment, and add `canvasSize: { type: Number, default: null }` with a comment citing design D1. Update the header comment and the `maxWidth` / `maxHeight` / `fillWidth` prop comments so none of them mentions the island's measured height budget. Check with `grep -n "fieldFill\|height budget" web/webclient-app/components/MapLattice.vue`, which returns nothing.
- [x] 1.2 `web/webclient-app/composables/use-map-lattice-geometry.js`, lattice branch of `layoutGeometry`: when `props.canvasSize != null`, compute the pitch as design D3 specifies.
  - `pMin` is today's `max(colPitch, labelClearancePitch)`. `avail = canvasSize − 2 × (gutter > 0 ? gutter : 8)`. `pFit = floor(min(avail / cols, (avail − LABEL_BAND) / rows))`. `p = max(pMin, min(pFit, 1.5 × colPitch))`.
  - Iterate inside the existing gutter fixed-point loop.
  - Pad the field symmetrically on both axes up to the square `S = max(canvasSize, required side)`, and return `canvasWidth = canvasHeight = S`.
  - Route `effectiveColPitch` / `effectiveRowPitch`, `latticePos`, `dotCx` / `dotCy`, and the `edgeMarkersFor` call through the fitted pitch, so the dot field stays registered.
  - Delete the old `fieldFill` / `maxWidth` padding branches, including the `mY = min(mX, verticalSlack)` rule.
 [x] 1.3 Same file, graph branch: when `props.canvasSize != null`, use a square viewBox centred on `(L/2, L/2)` with side `S = max(canvasSize, L − 2 × LocalMap.RADIAL_GEOMETRY.PAD + 16)`, where `L` is the radial side × `markerScale`. Expose the viewBox origin (for example, `viewBoxX` / `viewBoxY`) and have `MapLattice.vue` bind `:viewBox` from it. The lattice origin stays `0 0`.
 [x] 1.4 Same file, `latticeStyle`: when `canvasSize` is set, return `{ width: canvasSize + "px", height: canvasSize + "px" }` and skip `widthCaps()`. Leave the no-`canvasSize` path (the overlay and bare mounts) unchanged. Bind the SVG `width` / `height` attributes to `canvasSize` when it is set.
 [x] 1.5 Rewrite the geometry cases of `web/webclient-app/tests/world/map_lattice_fidelity.test.js` for design D3 / D4.
  - "Task 2.3 … Design D5 Table" and "Task 2.4 … bounds scale <= 1" become `canvasSize: 208` fixtures that assert:
    - a 3×3 core with no gateways at pitch 59 and scale 1
    - a single node at pitch 60 and scale 1
    - the reported wilderness shape with gateways at pitch 40 and side ≈ 222.91 (scale ≈ 0.933, label ≈ 8.40 px)
    - a 2×64 lattice scaled down with no overlap
  - Add graph cases: a one-ring interior at side 212 (scale ≈ 0.98) and a current-only interior at side 208 with scale 1 and the current node at the centre.
  - Replace every `fieldFill: true` with `canvasSize: 208`.
  - "Task 2.6 overlay geometry is identical" stays unchanged.
  - Run `pnpm exec vitest run web/webclient-app/tests/world/map_lattice_fidelity.test.js` green.
- [x] 1.6 `tests/world/map_lattice_name_fit.test.js`: the island-baseline cases ("Task 1.2", "Task 4.5") mount with `canvasSize: 208` instead of `maxHeight: 296` plus field fill. Re-derive the pinned island gutter, drawn names, and stacked tspans from the new square, keeping every overlay-side figure unchanged. Run `pnpm exec vitest run web/webclient-app/tests/world/map_lattice_name_fit.test.js` green.

## 2. Island: delete the list and the budget, fix the chrome (design D1, D2, D5)

- [x] 2.1 `web/webclient-app/components/LocalMap.vue`:
  - Delete `measureCanvasBudget`, `anchorHeightBudget`, `ANCHOR_BOTTOM_CLEARANCE`, `sectionHeight`, `canvasMaxHeight`, the `metaEl` / `rememberedEl` / `detailEl` refs and their `ref=` bindings, the `onMounted` ResizeObserver, `onUpdated`, and the now-unused Vue imports.
  - Delete the long "Dynamic canvas height budget" comments, and the `.visually-hidden` exclusion comment's reference to `measureCanvasBudget()`.
  - Mount `MapLattice` with `:canvas-size="208"` and without `max-height`, `fill-width`, or `field-fill`.
  - Check: `grep -n "measureCanvasBudget\|anchorHeightBudget\|ANCHOR_BOTTOM_CLEARANCE\|canvasMaxHeight\|ResizeObserver\|field-fill" web/webclient-app/components/LocalMap.vue` returns nothing.
- [x] 2.2 Same file:
  - Delete the `<ul class="local-map__remembered" data-testid="local-map-remembered">` block, `showsRememberedList`, and the `.local-map__remembered*` and `.local-map__node-label` CSS.
  - Add the graph-variant mirror `<ul v-if="isGraph && remembered.length" class="visually-hidden" aria-label="記得的地點" data-testid="local-map-remembered-mirror">`, with one `<li>` per remembered node in payload order giving `node.label`.
  - Update the header comment and the `onIslandClick` comment, which currently mention remembered-list items.
  - Check: `grep -rn "local-map-remembered\"\|local-map__remembered" web/webclient-app --include='*.vue' --include='*.js' --include='*.css'` (excluding `dist/`) returns only test files that section 4 rewrites.
- [x] 2.3 Island chrome:
  - In `LocalMap.vue` `<style>`:
    - `.local-map` gets `padding: var(--sp-1)`, `width: auto`, and `align-self: flex-end`, and keeps its single `border: var(--line)`, panel fill, blur, radius, and shadow.
    - `.local-map :deep(.local-map__lattice)` gets `border: 0`.
    - `.local-map__detail--empty` uses `visibility: hidden` instead of `display: none`.
    - Rewrite the stale comments about claiming the anchor's column.
  - `web/webclient-app/styles/app-shell.css`: `.elosern-root .local-map` keeps only its border colours, and `max-width: none` is removed.
  - `web/webclient-app/components/map-lattice.css`: update the `.local-map__lattice` comment that describes the island's measured height budget.
  - Verify with `pnpm run build` (repository root).

## 3. Overlay list and full log (design D5, D6)

- [x] 3.1 `web/webclient-app/components/MapOverlay.vue`: when `localMap.layoutVariant === 'graph'` and `localMap.remembered` is non-empty, render `<ul class="map-overlay__remembered" data-testid="map-overlay-remembered" aria-label="記得的地點">` after `MapLattice`.
  - Each `<li>` pairs an `aria-hidden` remembered diamond SVG (the markup moved from the island) with the full label as text.
  - No `tabindex`, no role, no click handler.
  - Scoped CSS uses tokens only, and the container is capped at `max-width: 848px` like the guide row.
  - `web/webclient-app/stories/Overlays/MapOverlay.stories.js`: add an interior story carrying remembered rooms.
- [x] 3.2 `web/webclient-app/components/FullLogOverlay.vue`: in `focusSelf()`, after `trap.enter()`, set `overlayEl.value.scrollTop = overlayEl.value.scrollHeight`. Update the header comment to name the open-at-latest-line rule. Add no watcher on `lines`.
- [x] 3.3 `web/webclient-app/tests/full_log_overlay.test.js`: add cases with 80 lines. After `focusSelf()`, `scrollTop` is set to `scrollHeight` (stub `scrollHeight` on the element, which jsdom does not lay out). Appending a line while open leaves `scrollTop` unchanged. Run `pnpm exec vitest run web/webclient-app/tests/full_log_overlay.test.js` green.

## 4. Vitest updates

- [x] 4.1 `web/webclient-app/tests/world/local_map.test.js`:
  - Delete the budget cases: "budgets the canvas from the reduced island sections, not a legend", "Task 4.1: derives canvas height budget…", "Task 4.2: gutter enlargement cannot breach canvas height cap…", "budgets against the anchor's room…", and "keeps the assistive-technology mirror out of the island's flex flow" (its premise was the budget's section count).
  - Rewrite "Task 3.1 & 3.2" to assert that the graph variant renders `local-map-remembered-mirror` with one entry per remembered node and no `local-map-remembered`.
  - Rewrite the remembered-item click case (around line 342) to click an edge marker instead.
  - Rewrite "fills the island's width…" and "spends width fill as coordinate margin…" to assert `canvasSize` 208, an SVG width and height of 208, and the fitted pitch.
  - Rewrite "Task 2.5: declares island geometry…" to expect `canvasSize` 208 instead of `fieldFill`.
  - Run `pnpm exec vitest run web/webclient-app/tests/world/local_map.test.js` green.
- [x] 4.2 `tests/world/map_layout_variants.test.js`: the island case at about line 198 asserts the mirror instead of the absence of the island list. `tests/overlays/map_overlay.test.js`: replace the "no `local-map-remembered`" assertion with the D5 contract. `map-overlay-remembered` is present with one non-focusable entry per remembered node on a graph payload and absent on a lattice payload. `tests/world/map_lattice_legend_labels.test.js`: reword the line 86 comment that mentions the island list. Stories:
  - `web/webclient-app/stories/World/LocalMap.stories.js`: the `Interior` story shows the list gone.
  - `web/webclient-app/stories/World/MapLattice.stories.js`: the island-scale stories pass `canvasSize: 208` instead of `fieldFill` and the 206 / 296 caps, and the "five-cell" sparse comment is updated.
  - Run `pnpm test`, `pnpm run build-storybook`, and `pnpm run showcase-coverage` green. `component-manifest.json` needs no change, because no component is added or removed.

## 5. Browser tests and traceability

- [x] 5.1 `web/tests/browser/test_browser_local_map_geometry.py`:
  - `test_minimap_content_stays_inside_its_island` asserts that the lattice SVG box is 208 × 208 and that the island box is identical before and after injecting a graph payload with remembered rooms.
  - `test_island_type_ladder_stays_under_its_own_chrome_step` keeps its ladder, with the node label ≤ 9 px, and re-derives any pinned scale from design D3.
  - Replace `test_marker_mirror_is_out_of_the_island_height_budget` with a test that both mirrors are clipped, non-focusable, and do not change the island box.
  - Run `uv run --locked python -m unittest web.tests.browser.test_browser_local_map_geometry` green.
- [x] 5.2 `web/tests/browser/test_browser_local_map_lattice.py`: rename `test_tall_lattice_with_long_remembered_list_stays_within_the_island` to `test_long_remembered_list_never_resizes_the_island`, keeping its annotation. The test asserts:
  - no `local-map-remembered`
  - a mirror entry count equal to the remembered count
  - a 208 × 208 canvas
  - an island box equal to that of the same payload without remembered nodes

  `test_densely_populated_lattice_scales_down_without_reintroducing_overlap` asserts the 208 canvas and a scale below 1. Run `uv run --locked python -m unittest web.tests.browser.test_browser_local_map_lattice` green.
- [x] 5.3 `web/tests/browser/test_browser_local_map_rendering.py` (around lines 152 and 233) and `test_browser_contextual_hud_stage.py` (around line 503): wait for `local-map-remembered-mirror` instead of `local-map-remembered`, and assert the list is absent. In the rendering test, open the full map and assert that `map-overlay-remembered` lists the room. Run both modules green.
- [x] 5.4 In `test_browser_contextual_hud_stage.py`, add `test_full_log_opens_at_latest_line`, decorated `@covers_requirement("webclient-input-narrative::the-full-log-surface-opens-at-its-latest-line")`. It appends 80 `out` lines through `window.__elosernBridge.store.appendText`, opens the log through `narrative-fulllog-control`, and asserts `scrollTop + clientHeight >= scrollHeight - 1` and that the last line's box is inside the overlay box. It then scrolls to the top, appends a line, and asserts `scrollTop` is unchanged. Finally it closes the log, reopens it, and asserts the log is back at the bottom. Run `uv run --locked python -m unittest web.tests.browser.test_browser_contextual_hud_stage` green.
- [x] 5.5 Sync this change's deltas into the main specs, then run `uv run --locked python -m tools.spec_traceability check` green. No requirement title changes, so no existing annotation is re-anchored. Only the new input-narrative ID needs the 5.4 test.

## 6. Validation

- [x] 6.1 Run these gates, all green:
  - `node --test web/static/webclient/js/tests/*.test.js` (no model change is expected)
  - `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root)
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - the browser modules `test_browser_local_map_geometry`, `test_browser_local_map_lattice`, `test_browser_local_map_rendering`, `test_browser_local_map_layout_variants`, `test_browser_local_map_interaction`, `test_browser_contextual_hud_stage`, and `test_browser_shell_surfaces` via `uv run --locked python -m unittest web.tests.browser.<module>`
- [x] 6.2 Take a 1920×1080 screenshot of the guild hall (interior) and of a wilderness cell. Confirm the island is 218px wide with a single 1px frame, no chip list, and a drawing that fills the canvas. Then run `openspec validate webclient-minimap-and-log-quick-fixes --strict` and `git diff --check`, both clean.
