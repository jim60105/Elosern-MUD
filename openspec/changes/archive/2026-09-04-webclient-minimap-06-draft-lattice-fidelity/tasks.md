# Tasks — Draft Lattice Fidelity

> Fifth and last in the minimap series. It builds on the delta text of
> `webclient-minimap-03-canvas-scale-and-budget` (the single width bound and the fixed-point
> height budget), `webclient-minimap-04-island-single-affordance` (the full-bleed affordance
> and the coordinate-only readout), `local-map-remembered-are-map-gateways` (remembered =
> a stood-on map boundary, plus the flagged label-suppression rule this change's field pitch
> depends on — design D11 states the fallback if it is struck), and
> `webclient-minimap-05-edge-markers-replace-list` (the named edge markers and their
> 44.46-unit gutter band).
>
> `web/static/webclient/js/elosern/local_map.js` is NOT edited (design D10), and neither is
> `web/webclient-app/components/MapOverlay.vue` (design D9) or
> `web/webclient-app/styles/tokens.css` (design D2 — the layers reuse `--ink-edge` and
> `--map-canvas-lo`). Waves 1 and 2 are independent of each other; wave 3 depends on both.

## 1. Wave 1 — the three coordinate-field layers

- [x] 1.1 In `web/webclient-app/components/MapLattice.vue`, add the `<defs>` for the
  coordinate dot field: a `<pattern patternUnits="userSpaceOnUse">` whose `width` is the
  effective column pitch and `height` the effective row pitch, holding one `<circle>` of
  radius `1.15 * markerScale` filled with `var(--ink-edge)` at `fill-opacity: 0.85`, whose
  `cx`/`cy` are `(pitch / 2 + originOffset) mod pitch` on each axis so a dot lands exactly on
  every node centre. Paint it as the FIRST child of the SVG — one `<rect>` covering the whole
  canvas, `pointer-events: none`, `aria-hidden="true"`, carrying neither
  `local-map__marker` nor `local-map__node-label`. Gate it on the lattice variant, not on a
  prop. Proof: `web/webclient-app/tests/world/map_lattice.test.js` — the pattern's tile equals
  the drawn pitch on both axes, and for every drawn node `(nodeX - cx) % pitch === 0` and
  `(nodeY - cy) % pitch === 0`.
- [x] 1.2 In the same file, add the knowledge-edge vignette behind a `fogVignette` boolean
  prop (default `false`): one full-canvas `<rect>` filled from a `<radialGradient>` centred on
  the canvas, keeping the draft's stop offsets (0.5 / 0.78 / 1) with opacities
  **0 / 0.26 / 0.50** over `var(--map-canvas-lo)`, drawn after the dot field and before the
  connector edges, `pointer-events: none`, `aria-hidden="true"`, neither audited class. Proof:
  same suite — exactly one vignette element, its outer stop opacity ≤ 0.5, and it renders only
  when the prop is set.
- [x] 1.3 In the same file, add the axis cross behind a `showAxis` boolean prop
  (default `false`): one `<g stroke="var(--ink-edge)" stroke-width="1.5" opacity="0.8">`
  holding a full-width and a full-height `<line>` through the current node's drawn position,
  drawn after the vignette and before the node groups, `pointer-events: none`,
  `aria-hidden="true"`, neither audited class, and rendered only on the lattice variant and
  only when the prop is set. A payload with no on-canvas current node draws no axis. Proof:
  same suite — the two lines span the canvas and cross at the current node's translate, and a
  graph-variant or prop-off render emits none.
- [x] 1.4 Add the scoped styles for the three layers and confirm no declaration animates or
  transitions anything, so the reduced-motion block has nothing to disable. Proof: same suite
  asserts the three layers carry `pointer-events: none` and `aria-hidden`, and
  `web/webclient-app/tests/world/map_layout_variants.test.js` asserts a graph-variant render
  emits no dot field and no axis.

## 2. Wave 2 — the derived pitch, the label type size, and the retired upscale

- [x] 2.1 In `MapLattice.vue`, add a `labelFont` number prop (default `11`, so the overlay is
  unchanged), drive `.local-map__node-label`'s `font-size` from it, and lower the label
  baseline from `LABEL_ANCHOR_HALF * markerScale + 13` to the derivation in design D4
  (widest drawn footprint 11 + a 2-unit gap + the label's ascent), which is 22 units at
  `labelFont 9`, `markerScale 1`. Proof:
  `web/webclient-app/tests/world/map_lattice.test.js` — the drawn label size and baseline for
  the island's props, and the overlay's props still producing `font-size: 11` at the shipped
  baseline.
- [x] 2.2 In `MapLattice.vue`, compute the effective pitch per axis as
  `max(declaredPitch, adjacentDrawnLabelPair ? (labelMax + 1) * labelFont + 3 : 0)`, where
  `adjacentDrawnLabelPair` is true when two horizontally adjacent cells of the drawn placement
  both draw visible label text, and use the effective pitch everywhere the pitch is consumed
  (node positions, the canvas size, the dot pattern tile, the axis). `labelMax` is NOT
  changed. Proof: same suite — the island's props give 40 on a payload with no adjacent drawn
  label pair and 48 on one with a pair, both axes equal in each case, and the overlay's
  `280 / 212` are returned unchanged because its label term is 124.
- [x] 2.3 In `MapLattice.vue`, add the `fieldFill` boolean prop (default `false`) and the
  coordinate-margin padding of design D5: pass `edgeMarkersFor` the padded field rect
  (`max(core, maxWidth - 2 * gutter)`) and the current node's position within it instead of the
  bare node rect, offset the node core by the resulting margin plus the gutter, and cap the
  vertical margin at both the horizontal margin and `maxHeight`. Proof: same suite — the six
  rows of design D5's table (canvas extent, margins, scale, rendered label, cells across),
  including the tall-lattice row taking zero vertical margin.
- [x] 2.4 In `MapLattice.vue`, delete the `maxUpscale` prop and its term in `widthCaps()`, so
  the single bound is `min(maxWidth, maxHeight * canvasWidth / canvasHeight)` floored to two
  decimals. Proof: same suite — no upscale prop is accepted, the emitted bound has two terms,
  and the resolved uniform scale is ≤ 1 for every fixture including the single-node payload.
- [x] 2.5 In `web/webclient-app/components/LocalMap.vue`, declare the island's geometry on the
  `MapLattice` mount — `:col-pitch="40" :row-pitch="40" :label-font="9" :field-fill="true"
  :show-axis="true" :fog-vignette="true"` — and remove `:max-upscale="2"`. Proof:
  `web/webclient-app/tests/world/local_map.test.js` — the island's declared props, the absence
  of the upscale prop, and the rendered label at ≤ 9 CSS px against the header's 10px step.
- [x] 2.6 Confirm `web/webclient-app/components/MapOverlay.vue` needs no edit and assert it:
  its `colPitch 280 / rowPitch 212 / labelMax 10 / markerScale 4.83 / maxWidth 848` are
  unchanged, it declares neither `fieldFill`, `showAxis`, nor `fogVignette`, it gains the dot
  field, and its emitted geometry is identical to the pre-change baseline. Proof:
  `web/webclient-app/tests/world/map_lattice.test.js` — an overlay-props render compared
  attribute-by-attribute against the shipped geometry, plus one assertion that its dot field
  exists.

## 3. Wave 3 — the visual and geometric gates

- [x] 3.1 Extend `web/tests/browser/test_browser_local_map.py`'s island geometry audit
  (`test_minimap_content_stays_inside_its_island`) so it still passes at the new pitch, and add
  the drawn-dot assertion: the dot field element exists, its resolved fill differs from the
  canvas ground, and the canvas spans roughly five coordinate cells across at the island's
  width cap.
- [x] 3.2 In the same file, add a contrast gate: compute the resolved composite colour of a
  dot and of the axis against the canvas ground at the canvas centre and near a corner, and
  assert the band from the spec — at least 1.15:1 everywhere, at least 1.35:1 in the vignette's
  un-darkened inner field, and never above the connector-edge ink's own ratio against the same
  ground.
- [x] 3.3 In the same file, assert the audit's own exclusions hold: the collected
  `.local-map__marker` and `.local-map__node-label` box lists gain no entry from the three new
  layers, and the island still exposes exactly one tab stop.
- [x] 3.4 Re-run `test_densely_populated_lattice_scales_down_without_reintroducing_overlap`
  and `test_tall_lattice_with_long_remembered_list_stays_within_the_island` unchanged as the
  ≥2-unit gap and height-budget regression gates at the new pitch and baseline.
- [x] 3.5 Re-run `web.tests.browser.test_browser_contextual_hud` unchanged, and add one case
  for the axis/words coupling: the island draws the axis exactly where it states `北↑ 東→`,
  and the full-map surface draws none.
- [x] 3.6 Add the island- and overlay-scale stories to
  `web/webclient-app/stories/World/MapLattice.stories.js` covering the sparse payload (one
  marker in a five-cell field), the reported three-by-three wilderness payload, the
  adjacent-labelled-pair payload at the 48-unit pitch, and the overlay's unchanged geometry
  with its dot field.
- [x] 3.7 Run the full gates and record the counts: `npx vitest run`, `node --test
  web/static/webclient/js/tests/*.test.js` (expected unchanged — `local_map.js` is not
  edited), and the browser suites `test_browser_local_map`, `test_browser_contextual_hud`,
  `test_browser_layout`, `test_browser_shell`.
