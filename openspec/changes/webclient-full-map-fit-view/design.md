## Context

See proposal.md (Why). This change builds on `webclient-minimap-and-log-quick-fixes` (C1), and the state below is the tree after C1 is applied.

Current state, verified in code:

- `MapOverlay.vue` mounts `MapLattice` inside `.map-overlay__content`, a centred flex column with `gap: 20px`. It passes `:col-pitch="280" :row-pitch="212" :label-max="10" :label-font="14" :marker-scale="2.2" :max-width="848" :max-height="null" :fill-width="true" :overlay-chrome="true" :marker-names="true" :marker-name-font="11"`. Its layout is:
  - The guide row (`.map-overlay__guide`, `order: -2`) and the MapLattice legend (`:deep(.local-map__legend)`, `order: -1`, a padded card) sit above the canvas, and both are capped at `max-width: 848px`.
  - `revealCurrentNode()` runs `scrollIntoView({ block: "center" })` on `[data-visibility="current"]` inside `.local-map__viewport`. It runs from `onMounted` and from `watch(currentNodeId, …, { flush: "post" })`.
  - C1 adds `ul.map-overlay__remembered` (`map-overlay-remembered`) after `MapLattice` on the graph variant, also capped at 848px.
- `MapLattice.vue` wraps the SVG in `div.local-map__viewport`.
  - That div is `display: contents`, except under `overlayChrome`, where `.local-map__viewport--canvas` makes it a block with `overflow: auto`.
  - The SVG's `width` / `height` attributes and its `viewBox` are the geometry's `canvasWidth` / `canvasHeight`. Its inline style comes from `latticeStyle`: after C1, the island's `canvasSize` branch, or the `fillWidth` / `widthCaps()` branch for everything else.
  - The legend `<ul>` is a second root node, mounted when `showLegend` is set (default on). Its chip class comes from `legendState(i)` in `composables/use-map-lattice-render.js`, and its CSS is at the end of `components/map-lattice.css`.
  - The island (`LocalMap.vue`) passes `:show-legend="false"`.
- `OverlayHost.vue` is the modal surface.
  - It is `position: fixed` between the top bar and the command line. The body (`.overlay-host__body`) is `flex: 1`, `max-width: 1180px`, `padding: 28px`, and `overflow-y: auto`.
  - At 1920 × 1080 the body's content box is about 1124 × 783 CSS px, and after the guide row about 1124 × 735 remain for the map.
  - `onKeydown` on the `<section>` closes on Escape (with `stopPropagation`), stops propagation of every non-Tab key, and routes Tab to the shared focus trap.
- Node activation is `@click` / `@keydown.enter` / `@keydown.space` on each `g.local-map__node`, which is `role="button"` and `tabindex="0"` under `overlayChrome` when the node has a move action (`activateNode` in `use-map-lattice-render.js`).
- Reduced motion is applied at the token level: `styles/tokens.css` collapses every `--motion-*` token to `1ms` under `prefers-reduced-motion` (unless `html[data-reduced-motion="off"]`) and under `html[data-reduced-motion="on"]`.

## Goals / Non-Goals

**Goals:**
- The full-map overlay opens with the whole drawing (nodes, labels, and edge-marker gutter) visible inside its body at any committed payload.
- Zoom (wheel, `+` / `-`, buttons), drag-pan, and `置中` work, and keyboard node travel is unchanged.
- The legend no longer takes vertical space.
- Delete every code path that existed only for the scrolling overlay or for width caps.

**Non-Goals:**
- Changing the overlay's declared geometry (pitch, marker scale, type sizes) or the render model.
- Arrow-key panning. Keyboard users move by Tab (with focus reveal), `+` / `-`, and `置中`. Arrow keys stay unbound, as they are today.
- Touch pinch gestures (the client is desktop-only, design §2.2).
- Persisting the zoom level or the popover state, or restoring them across openings.
- The island (C1) and the shell anchors (C4).

## Decisions

### D1. Zoom is a `viewBox` window over the unchanged drawing, not a CSS transform
With `fitView` on, the SVG is laid out at `width: 100%; height: 100%` of a clipped viewport box (`overflow: hidden`). Its `viewBox` is `x y (vw / s) (vh / s)`, where:
- `(vw, vh)` is the viewport's content box in CSS px
- `s` is the scale in CSS px per user unit
- `(x, y)` is the window origin in user units.

The `viewBox` has the viewport's own aspect ratio, so the default `preserveAspectRatio` meets it exactly and never letterboxes. The `width` / `height` attributes keep the canvas size, and the style overrides them, so every existing test that reads those attributes on a bare mount keeps its pinned figure.

Why a `viewBox` rather than a CSS transform:
- `use-map-lattice-geometry.js` and `use-map-lattice-render.js` stay untouched.
  - Every placement, gutter, marker-name fit, and pitch derivation still works in the same user units.
  - A `viewBox` change is a uniform scale plus a translation, which is exactly the "uniform scale" under which the spec's non-overlap invariant already holds.
  - Nothing in the geometry has to know that zoom exists.
- Text and strokes re-rasterise crisply at every scale. A scaled bitmap layer from a CSS transform is blurred until the compositor re-rasterises it.
- Hit-testing, focus rings, and `getBoundingClientRect` in the browser tests follow the zoom without extra work.
- The `mapcanvas` background and 1px border stay on the SVG element, so they frame the viewport at every zoom, and there is no second frame to keep in sync.

*Alternative:* `transform: translate() scale()` on the SVG inside an `overflow: hidden` box. Rejected for the reasons above. It would also need `transform-origin` bookkeeping, and the pin's hairline stroke would scale with it.

### D2. Scale bounds and the fit rule
Constants in `lib/map_view.js`: `FIT_INSET = 12` (CSS px), `MAX_SCALE = 2`, `ZOOM_STEP = 1.25`, `DRAG_THRESHOLD = 4` (CSS px).

- **Fitted scale:** `sFit = min(1, (vw − 2 × FIT_INSET) / W, (vh − 2 × FIT_INSET) / H)`, where `W × H` is the full canvas, including the edge-marker gutter.
  - The cap at 1 means a small payload opens at its declared overlay size and is never magnified. A single node therefore does not open at 3× (today `fill-width` stretches a 280-unit canvas to 848px).
  - This follows the same philosophy as C1's island.
- **Bounds:** the minimum is `sFit`, so zooming out never goes past the whole-map view. The maximum is `max(MAX_SCALE, sFit)`, which is 2 in practice. At the maximum, a node label draws at 28px, and every overlay figure can be reached at or above its declared size.
- **Clamp:** on each axis, if the visible span `vw / s` is at least `W`, the window is centred on the canvas, so no pan is possible on that axis. Otherwise the origin is clamped to `[0, W − vw / s]`, so no empty space appears beyond a canvas edge.

Worked figures at 1920 × 1080 (viewport about 1124 × 735):
- A two-column, five-row street (560 × 1074) opens at `s ≈ 0.662`, drawn at 371 × 711 px, with labels at about 9.3px. Today it is 848px wide and scrolls.
- The 5 × 5 wilderness with named edge markers (about 1894 × 1568) opens at `s ≈ 0.453`, with labels at about 6.3px. The overview is legible as shape and state, and `+` or the wheel brings text to reading size.
- The pinned 3 × 1 overlay sample in `map_lattice_renderer.test.js` (1333.90 × 719.90) opens at about `s = 0.825`.

*Alternative:* a legibility floor on the fitted scale, such as 0.6. Rejected, because §11 asks for the whole known map on open, and a floor brings back a hidden part of the map with no scrollbar to hint at it.

### D3. Input model: wheel, keys, buttons, drag, focus reveal
Every operation is a pure function in `lib/map_view.js`: `fitView`, `clampView`, `zoomAt(view, factor, anchorPx)`, `panBy(view, dxPx, dyPx)`, `centreOn(view, point)`, `revealBox(view, box, marginPx)`, and `viewBoxOf(view)`. Each takes a view state `{ s, x, y, fitted }` together with `{ vw, vh, W, H }`. `composables/use-map-view.js` binds them to the DOM.

- **Wheel** (`@wheel.prevent` on the viewport, non-passive):
  - The factor is `exp(−deltaY × 0.0015)`. `deltaY` is normalised for `deltaMode` 1 (×16) and 2 (×vh), and the factor is clamped to [0.5, 2] per event.
  - The zoom is anchored at the pointer: the user point under the cursor stays under the cursor.
  - `ctrlKey` wheel (trackpad pinch) takes the same path.
- **Keys:** `MapOverlay.vue` handles `keydown` on its root.
  - `+`, `=`, and `Add` zoom in by `ZOOM_STEP` about the viewport centre, and `-`, `_`, and `Subtract` zoom out.
  - A key with Ctrl, Meta, or Alt held is ignored, so browser page zoom still works.
  - The overlay has no text input, so no typed character is swallowed.
  - The root handler runs before `OverlayHost`'s section handler in bubble order. OverlayHost already stops non-Tab keys at the section, so the document keyboard router never sees them.
- **Buttons:** `縮小` / `放大` call the exposed `zoomOut` / `zoomIn`, and `置中` calls `recentre`.
  - At a bound, or with no current node for `置中`, a button carries `aria-disabled="true"` and does nothing. It is never `disabled`, so a focused button never drops focus out of the trap.
- **Drag:**
  - `pointerdown` with the primary button records the start.
  - After more than `DRAG_THRESHOLD` px of movement, the gesture becomes a drag: the viewport calls `setPointerCapture`, `panBy` follows the pointer, and the cursor becomes `grabbing`.
  - On `pointerup`, a drag sets a one-shot `suppressClick` flag, which is cleared by `setTimeout(0)`. A capture-phase `click` listener on the viewport consumes the next click (`stopPropagation` + `preventDefault`) while the flag is set, so a drag that ends on a node never reaches `activateNode` and never emits `move`.
  - A press that moves 4px or less is an ordinary click, so node travel by pointer is unchanged.
- **Focus reveal:**
  - `focusin` from a `[data-node]` element calls `revealBox` on that node's drawn box.
  - The box is the node position ± `HALO_R × markerScale` horizontally, and from `−HALO_R × markerScale` above to the label baseline plus `labelFont` below.
  - The margin is 24 CSS px, the scale is kept, and the window moves only as far as it must.
  - This replaces `scrollIntoView` for keyboard users.
- **`fitted` flag:** the view is `fitted: true` when it opens and after a refit. Any zoom, pan, `置中`, or reveal sets it to `false`.

### D4. Payload updates, resizes, and the no-persistence rule
- **Viewport resize** (a ResizeObserver on the viewport box): if the view is fitted, it refits. Otherwise the user point at the viewport centre stays at the centre, and the scale is clamped to the new bounds.
- **A new committed payload with a different current-node id** (travel): if the view is fitted, it refits. Otherwise the window centres the new current node at the same scale (clamped). This keeps today's rule: "recenter only on opening or actual travel".
- **Any other payload replacement:** clamp only, so a reader panning through the map is not interrupted.
- **Opening the overlay** mounts a fresh `MapOverlay`, and the view starts fitted. Nothing is written to preferences, `localStorage`, or the store.
- **jsdom fallback:** where the viewport box has no size yet, which is the case in jsdom and before the first ResizeObserver callback, the view is `null` and the `viewBox` is the whole canvas (`0 0 W H`). Under `meet` that is also a fitted rendering. This keeps component tests free of layout, and `lib/map_view.js` is tested directly.

### D5. The legend leaves the shared renderer for a `?` popover
The island never mounts the legend, and the overlay is the only surface that does, so a `showLegend` switch on the shared renderer has one real value per surface.

The change:
- The legend markup, `legendState`, and the `.local-map__legend*` CSS move into `MapOverlay.vue`, and `showLegend` is deleted.
- Classes and testids are kept (`local-map__legend`, `local-map__legend-item--N`, `local-map__legend-chip--{state|info}`), so selectors in existing tests keep working once the popover is open.

The popover:
- **Toggle:** a `<button data-testid="map-overlay-legend-toggle" aria-label="圖例" aria-expanded aria-controls>` showing `?`.
- **Panel:** `<div id=… data-testid="map-overlay-legend-popover" role="group" aria-label="圖例">`, mounted with `v-if` while open.
  - It is absolutely positioned under the toggle, over the top-right of the map viewport. It takes no layout space.
  - It holds no focusable content. Focus stays on the toggle, following the disclosure pattern.
- **Closing:**
  - Escape while it is open closes it and calls `stopPropagation`, so `OverlayHost` does not close the overlay. A second Escape closes the overlay.
  - A second activation of the toggle closes it.
  - A `pointerdown` inside the overlay but outside both the popover and the toggle closes it without consuming the event, so a drag or a node click still works.
- **Initial state:** closed every time the overlay opens.

*Alternative:* a new `MapLegend.vue` component. Rejected. `component-manifest.json` is frozen, and the spec requirement "The frozen component set grows only through a governed redesign wave" governs additions, which would be ceremony for a list with one consumer.

*Alternative:* let Escape close the whole overlay even while the popover is open. Rejected, because a disclosure that Escape does not close surprises keyboard users. The `webclient-contextual-hud` overlay requirement is modified so that an overlay's own open popover is the topmost Escape level.

### D6. Deleting the width-cap path
After C1 the island declares `canvasSize`, and after this change the overlay declares `fitView`. No product surface passes `maxWidth`, `maxHeight`, or `fillWidth`, so these are deleted:
- the three props
- `widthCaps()`
- the cap branch of `latticeStyle`, which now returns the C1 square style, `{ width: "100%", height: "100%" }` for `fitView`, or `{}`
- `.local-map__viewport--canvas`

A bare mount, such as a story or a test, draws at the canvas's natural size.

The spec's width-bound rule and the C1-restated scenario "The height budget is spent as an equivalent width bound" become statements that no cap exists. The scenario title is kept, because a MODIFIED block must not drop an existing scenario name. Its body pins the new behaviour.

### D7. Layout of the overlay body
`.map-overlay__content` becomes a column grid, `grid-template-rows: auto minmax(240px, 1fr) auto`, filling the body's height. The rows are:
1. the guide row: the hint on the left, the toolbar on the right, full width
2. the viewport
3. C1's remembered list (graph variant only), full width, wrapping, no scroll of its own

Because the viewport takes the remainder, the fit is always computed against the room actually left, so a 16-entry remembered list shrinks the fitted scale instead of pushing the map below the fold. Every 848px cap is deleted.

The guide text becomes `點選可通行的相鄰節點，繼續探索。` with the hint `Tab 切換路徑 · Enter 確認移動 · 滾輪或 +／− 縮放 · 拖曳平移`.

### D8. Reduced motion
The view has no animation: zoom, pan, `置中`, reveal, refit, and the popover all apply in one frame. The reduced-motion preference therefore has nothing to disable, and the reduced-motion rendering is identical to the default one, with no information lost. Adding eased transitions is left to `webclient-motion-layer` (C11), which owns motion levels.

### D9. Spec deltas and archive order
- `webclient-local-map` "The browser minimap renders states without relying on color alone" is MODIFIED on top of C1's text (`openspec/changes/webclient-minimap-and-log-quick-fixes/specs/webclient-local-map/spec.md`). Every C1 scenario title is kept. The bodies change for these scenarios:
  - "The island mounts no state legend"
  - "The full-map overlay renders the same lattice at a larger scale"
  - "The full-map overlay omits the remembered-node list and the readout line"
  - "The full-map overlay lists a graph payload's remembered rooms"
  - "The height budget is spent as an equivalent width bound"
  - "The overlay keeps its geometry and gains only the coordinate field"
  - "The graph variant draws no coordinate field and no axis"
- `webclient-local-map` "The legend renders beyond-state entries as neutral info chips" is MODIFIED against the main spec, which C1 does not touch.
- `webclient-local-map` gains the ADDED requirement "The full-map surface opens fitted to its body and offers zoom, pan, and recentre".
- `webclient-contextual-hud` "A full-screen overlay is one focus-trapped surface, and only one is open at a time" is MODIFIED against the main spec. No change in this series that already exists touches it. A later series change that modifies it must write on top of this one.
- `webclient-contextual-hud` "The map, settings, and help surfaces are reachable from the live client" is MODIFIED against the current main spec.
  - Only the map clause changes: "no zoom or pan affordance" becomes the fit-view controls, and the surface shows no zoom-level figure.
  - The scenario title "The map surface advertises no zoom or pan" is kept, because validate rejects a dropped scenario name, and its body now pins the allowed controls.
  - `webclient-retire-redundant-hud` (C3) also modifies this requirement and rebases its block on this one. **Archive order: C1 → C2 → C3.**
  - The unit test `deferred_surfaces_absent.test.js` drops its Zoom / Pan deferral patterns (task 5.7).

**This change must be archived after `webclient-minimap-and-log-quick-fixes` (C1).**

## Risks / Trade-offs

- [Large maps open with small text (about 6px labels for a 5 × 5 wilderness with named markers)] → This is the requested trade: the whole map on open. The wheel, `+`, and `放大` reach 2×, and Tab focus reveal keeps keyboard travel readable.
- [Wheel `preventDefault` needs a non-passive listener] → Vue's `@wheel.prevent` registers a non-passive listener. The body never scrolls inside the map, so no page scroll is lost.
- [Pointer capture changes the click target in some engines] → The capture-phase suppression on the viewport ancestor catches the click whatever element it targets.
- [Browser geometry tests read overlay boxes that now depend on the fitted scale] → `test_crowded_edge_overlay_marker_names_stay_separated_and_outside_canvas` compares boxes against each other and against the canvas rect, not absolute sizes. Task 5.3 re-runs it, and adjusts any absolute pixel figure it finds by the fitted scale.
- [C1 and this change edit the same files] → Apply C1 first. Task 1.1 checks that C1 has been applied.

## Migration Plan

None. The client is unreleased, and nothing is stored.
