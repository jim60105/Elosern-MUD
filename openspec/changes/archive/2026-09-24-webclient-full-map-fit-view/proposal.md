## Why

The requester cannot see the whole map on one screen (design `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §1, §11). `MapOverlay.vue` mounts `MapLattice` at column pitch 280, row pitch 212, `markerScale` 2.2, `max-width` 848, `max-height` null, and `fill-width`. Its scale is therefore set by width alone. The canvas is always drawn 848px wide (or as wide as the body is), whatever its height, so a narrow, tall payload is magnified and runs down the overlay body, which scrolls. For example, a two-column, five-row street is 560 × 1074 user units before any gutter; drawn at 848px wide it is about 1.5× and roughly 1626px tall. `revealCurrentNode()` then calls `scrollIntoView` to bring the current node on screen, so the player never sees the whole map. The state legend (`ul.local-map__legend`) is mounted above the canvas as a padded card, and every legend entry takes more of the height the map needs. The project is unreleased, so the scroll-and-reveal path and the width-cap path are deleted, not kept as options.

## What Changes

- **Fitted view.** `MapLattice.vue` gains a `fitView` prop, which only the overlay passes. With it on:
  - the SVG fills a clipped viewport box, and its `viewBox` becomes a window onto the unchanged drawing
  - the window opens fitted: the whole canvas, including the edge-marker gutter, is inside the viewport, at a scale of at most 1 CSS px per user unit
  - the pure view math lives in a new `web/webclient-app/lib/map_view.js`: fit, clamp, zoom about an anchor, pan, centre on a point, and reveal a box
  - the Vue binding lives in a new `web/webclient-app/composables/use-map-view.js`: a viewport ResizeObserver, wheel, pointer drag, and focus reveal. It exposes `zoomIn`, `zoomOut`, and `recentre` through `defineExpose`.
- **Zoom and pan.** Zoom runs from the fitted scale up to 2 CSS px per user unit.
  - The wheel zooms about the pointer. `+` / `=` and `-` zoom about the viewport centre in steps of 1.25×.
  - A primary-button drag pans. A drag longer than 4 CSS px suppresses the click that follows it, so it never submits a node's move.
  - Tab focus on a node that lies outside the window pans just enough to show it.
  - Nothing animates.
  - The view is never persisted.
- **Overlay toolbar.** `MapOverlay.vue` adds a toolbar to its guide row with four buttons:
  - `縮小` (−), `data-testid="map-overlay-zoom-out"`
  - `放大` (+), `map-overlay-zoom-in`
  - `置中`, `map-overlay-recentre`, which centres the current node and keeps the zoom
  - `圖例` (`?`), `map-overlay-legend-toggle`, which is a disclosure button
  
  The guide text names the new gestures. On a new current node, the view refits while it is untouched, and otherwise recentres at the same zoom.
- **BREAKING (internal)**: the legend moves into a `?` popover.
  - The legend markup (`ul.local-map__legend`, testids `local-map__legend` and `local-map__legend-item--N`), the `legendState` helper, and the chip CSS move from `MapLattice.vue`, `composables/use-map-lattice-render.js`, and `components/map-lattice.css` into `MapOverlay.vue`.
  - The legend renders inside `data-testid="map-overlay-legend-popover"`, which is mounted only while the popover is open and floats over the top-right of the map viewport.
  - Escape closes the popover and nothing else. So do a second activation of the `?` button and a pointer press outside the popover.
  - `MapLattice`'s `showLegend` prop is deleted, and so is `LocalMap.vue`'s `:show-legend="false"`.
- **BREAKING (internal)**: delete the scroll-and-reveal path.
  - In `MapOverlay.vue`: `revealCurrentNode`, the `body` ref, the `onMounted` / `watch(currentNodeId)` reveal, and the `max-width="848"`, `max-height`, and `fill-width` props.
  - In `MapLattice.vue`: the `maxWidth`, `maxHeight`, and `fillWidth` props.
  - In `composables/use-map-lattice-geometry.js`: `widthCaps()` and its cap branch of `latticeStyle`.
  - In `map-lattice.css`: `.local-map__viewport--canvas`, which scrolls.
  - After this change and C1, every product surface declares either the 208px square canvas (island) or the fitted view (overlay), and a bare mount draws at natural size.
- C1's graph-variant remembered list (`map-overlay-remembered`) stays below the viewport. Its `max-width: 848px` cap and the guide row's cap are dropped, and the viewport takes whatever height is left, so a 16-entry list never pushes the map out of the body.
- `OverlayHost.vue` is unchanged. Its section-level Escape handler still closes the overlay, because the popover's handler runs first in bubble order and stops propagation only while the popover is open.
- Spec deltas:
  - `webclient-local-map`: restate the minimap rendering requirement on top of C1's text, for the fitted view, the deleted width caps, and the legend's move out of the shared renderer.
  - `webclient-local-map`: restate the info-chip legend requirement for the popover.
  - `webclient-local-map`: add the fit-view requirement.
  - `webclient-contextual-hud`: restate the full-screen overlay requirement so an overlay's own open popover is the topmost Escape level.
  - `webclient-contextual-hud`: restate "The map, settings, and help surfaces are reachable from the live client". Its clause "no zoom or pan affordance" becomes this change's view controls.
- No OOB schema, presenter, server, render-model (`web/static/webclient/js/elosern/local_map.js`), store, or persistence change.

Out of scope:
- The minimap island's fixed square canvas, pitch-fit, mirror, and the overlay's remembered list are owned by `webclient-minimap-and-log-quick-fixes` (C1), which this change builds on.
- Moving the minimap to the `map` anchor and the shell rewrite are owned by `webclient-avg-stage-shell` (C4).
- Motion levels and transitions are owned by `webclient-motion-layer` (C11). This change adds no animation for C11 to gate.
- The overlay's declared geometry (pitch 280 / 212, `markerScale` 2.2, label and name type sizes) is unchanged. Fitting is a view transform, not a geometry change.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-local-map`:
  - "The browser minimap renders states without relying on color alone" (MODIFIED on top of C1):
    - the full-map surface declares a fitted view
    - the width-cap rule is removed
    - the legend is no longer part of the shared canvas renderer and renders only in the overlay's popover
    - the non-overlap guarantee is stated to hold at every zoom
  - "The legend renders beyond-state entries as neutral info chips" (MODIFIED): the popover is the one legend surface.
  - ADDED "The full-map surface opens fitted to its body and offers zoom, pan, and recentre".
- `webclient-contextual-hud`: "A full-screen overlay is one focus-trapped surface, and only one is open at a time" (MODIFIED): a popover open inside the overlay takes Escape before the overlay does.
- `webclient-contextual-hud`: "The map, settings, and help surfaces are reachable from the live client" (MODIFIED, based on the current main spec). The map surface offers exactly the fit-view controls and names them in its guide row. It shows no zoom-level figure and persists nothing. The scenario "The map surface advertises no zoom or pan" keeps its title, and its body is rewritten to pin the allowed controls.

## Impact

- New files: `web/webclient-app/lib/map_view.js`, `web/webclient-app/composables/use-map-view.js`, `web/webclient-app/tests/world/map_view.test.js`
- Edited components and styles:
  - `web/webclient-app/components/MapLattice.vue`, `MapOverlay.vue`, `LocalMap.vue` (one prop binding), `map-lattice.css`
  - `web/webclient-app/composables/use-map-lattice-geometry.js`, `use-map-lattice-render.js`
- Stories: `web/webclient-app/stories/World/MapLattice.stories.js`, `stories/Overlays/MapOverlay.stories.js`. No story title is added or removed, and `component-manifest.json` is unchanged.
- Vitest:
  - `tests/overlays/map_overlay.test.js`
  - `tests/world/map_lattice_renderer.test.js`
  - `tests/world/map_lattice_legend_labels.test.js`
  - `tests/world/map_lattice_fidelity.test.js`
  - `tests/world/map_lattice_name_fit.test.js`
  - `tests/world/map_layout_variants.test.js`
  - `tests/world/map_lattice_support.js`
- Browser tests:
  - `web/tests/browser/test_browser_local_map_interaction.py`: legend opened through the popover, plus a new fit / zoom / pan / recentre test
  - `test_browser_local_map_rendering.py`: legend opened through the popover
  - `test_browser_local_map_lattice.py`: overlay marker-name test re-run
  - `test_browser_contextual_hud_stage.py`: an Escape-precedence assertion
- Spec traceability: one new ID, `webclient-local-map::the-full-map-surface-opens-fitted-to-its-body-and-offers-zoom-pan-and-recentre`, is covered by the new browser test. Every modified title is unchanged, so no annotation is re-anchored.
- Dependencies: builds on C1 (`webclient-minimap-and-log-quick-fixes`) and must be archived after it. Both change `MapLattice.vue`, `MapOverlay.vue`, `use-map-lattice-geometry.js`, `LocalMap.vue`, and the same `webclient-local-map` requirement, so run them one after the other and never in parallel worktrees.
