# The Lattice Finally Looks Like the Drawing It Was Designed From

## Why

Four changes into the minimap series the island's *chrome* matches the redesign
draft and its *lattice* still does not. The owner, after the first four:
「還有網格地圖的渲染本身仍沒有達到和設計稿相同的設計，包含字體比例，格點數量比例，
四週遠處的淺色格點」 — the font proportion, the proportion of grid cells across
the canvas, and the faint far-field dots.

Measured against `docs/design/elosern-redesign/index.html`'s `.lay-grid` SVG,
four things are missing or inverted:

1. **The coordinate dot field is not drawn at all.** The draft paints
   `<pattern id="mgrid" width="24" height="24">` with one `r=1.15` dot per cell
   over the whole canvas, and `REDESIGN.md` §7.4 pins its meaning: the dot pitch
   *is* one coordinate cell, so the field shows the coordinate space the lattice
   claims. The shipped renderer paints a flat `--ink-860` rectangle: **zero
   dots**. §7.4 is explicit that this layer "must not be invisible" and that
   "implementation waves pin their presence and contrast" — no wave has.
2. **The fog vignette is not drawn.** The draft's `<radialGradient id="mfog">`
   darkens the canvas edges, and §7.1's table names it exactly: the **knowledge
   edge, not terrain**.
3. **The axis cross is not drawn.** The draft runs a full-width and full-height
   line through the current node at 1.5px / 0.65 opacity — the visual form of the
   same claim the island's header states in words as 「北↑ 東→」. The shipped
   requirement already *refers* to it: an edge direction marker "SHALL be
   positioned deterministically so that markers never overlap each other or any
   node marker, label, or axis". The invariant has been quoting a line nothing
   ever draws.
4. **The type and cell-count proportions are inverted.** The draft's node labels
   are `font-size="8"` on a 180-unit canvas — 4.44% of the canvas width — with
   ~7.5 cells across it, rendering at 7.64 CSS px inside `.mini svg
   { max-width: 172px }` against the island's own 10px chrome. The shipped island
   draws `font-size: 11` at `colPitch 58`, and `webclient-minimap-03-canvas-scale-and-budget`
   fills the island's width by scaling the whole SVG through the viewBox, capped
   at `maxUpscale: 2`. Because the scale is uniform, a **sparse payload renders
   its labels at ~22 CSS px — larger than the island's own 10px title — while
   still truncated to four glyphs**. On the reported wilderness payload the
   canvas is 262.91 × 234.91 user units drawn at 206px (scale 0.784): 4.53 cells
   across, labels at 8.62 CSS px, and the node core occupying 66% of a canvas
   whose draft equivalent occupies 40%. Change 03's design D7 records that its
   viewBox upscale "is expected to be superseded" here.

The fifth and last change of the series closes that gap.

## What Changes

- **The lattice gains a coordinate dot field**: one dot per coordinate cell,
  registered to the node lattice so a dot sits exactly where a node marker for
  that cell would sit, at the draft's own `r=1.15` scaled with the marker ladder.
  Its pitch is the drawn cell pitch on each axis, so one dot spacing is exactly
  one coordinate cell — the field's meaning, not a texture. It renders on the
  lattice variant on **both** surfaces (the claim belongs to the drawing, not to
  a surface) and never on the radial graph, which has no coordinate cells.
- **The lattice gains a knowledge-edge vignette.** Each surface paints exactly
  one: the island draws the draft's radial wash over the coordinate field and
  beneath every marker, edge, and label; the full-map overlay keeps the
  `mapcanvas` CSS gradient it already has and draws no second wash. The vignette
  is a single full-canvas gradient — never a per-cell fill, a region fill, or any
  shape tracing a terrain feature.
- **BREAKING** (spec text): the vignette's outer opacity is **capped below the
  draft's**. At the draft's 0.72 outer stop the far-field dots the owner asked
  for measure **1.07:1** against the fogged ground — they are the thing the fog
  erases. Capped at 0.50 they measure **1.15:1**, and the un-fogged inner field
  measures **1.42:1**. The requirement pins presence and contrast as a band, as
  §7.4 demands.
- **The lattice gains the axis cross**, drawn beneath every node marker at the
  connector-edge ink token, 1.5 units wide at 0.8 opacity (**1.39:1**, against
  the connector edge's own 1.53:1 — decoration below topology, never above it).
  It renders only on a surface that states the axis convention in words, which
  today is the island alone; the overlay states no orientation marks, so it draws
  no axis and asserts none.
- **BREAKING**: the island's node label drops from 11 to **9 user units**
  (4.37% of the 206-unit canvas, against the draft's 4.44%), and the uniform
  scale can no longer exceed 1, so the drawn label is **at most 9 CSS px — below
  the island's own 10px chrome type step** at every payload. It renders at
  8.87 px on the reported payload, up from 8.62 px, and at 9 px on the sparse
  payload that today renders 22 px. `labelMax` stays **4**: this change does not
  truncate labels harder — the archived crowding fix rejected that lever
  outright, and the lever used here is the pitch and the type size.
- **BREAKING**: the island's lattice pitch becomes **square at 40 units** on both
  axes, derived rather than asserted, and the column pitch's shipped `58` becomes
  a *conditional* requirement rather than a constant. `58` exists only because
  "the column pitch must clear two truncated node labels … centered under
  horizontally adjacent nodes with a strictly-positive visible gap"
  (`2026-08-27-fix-webclient-local-map-node-crowding`), whose worst case is
  `(labelMax + 1) × 11 = 55` units. `local-map-remembered-are-map-gateways` now
  draws no visible label for an in-view node whose label repeats the current
  node's, so on a wilderness payload **most neighbouring cells carry no label at
  all** and no adjacent labelled pair exists to clear. The pitch therefore becomes
  a function of what actually needs clearing: the label term binds only when two
  horizontally adjacent **drawn** labels exist, and the bare term (two actionable
  halos plus a visible connector segment, and a label box clear of the next row's
  marker) is what binds otherwise. Two square values result — **40** in the field
  case and **48** (`(4 + 1) × 9 + 3`) when an adjacent labelled pair appears —
  both satisfying the non-overlap invariant at every placement the model can
  produce.
- **BREAKING**: the island's width fill stops being a magnification and becomes
  **coordinate margin**. The canvas's drawn extent is padded to the surface's
  width cap at the designed pitch, symmetrically around the node core, with the
  edge-marker band remaining the canvas's outermost band; the leftover is
  coordinate space that the dot field paints. The uniform scale is then **1
  whenever the drawing fits its caps and below 1 only when it does not** — never
  above. A sparse payload reads *airy* instead of *magnified*: one marker at its
  designed size, centred in a five-cell-wide dot field, its label at 9 px.
- **BREAKING**: `maxUpscale` is **retired**. It existed to bound a magnification
  that no longer happens; the single width bound loses its third term and becomes
  `min(maxWidth, maxHeight × canvasWidth / canvasHeight)`. `MapOverlay.vue` never
  passed the prop, so removing it cannot touch the overlay.
- `.mini svg { max-width: 172px }` is **not** adopted. 172 is the draft's own
  natural canvas width (`viewBox="0 0 180 150"` less its 8-unit safe border), not
  a designed bound for our derived canvas; the island keeps `maxWidth: 206`, which
  sits just inside its 210px content box, and 206 is now also the field-padding
  target — one knob, not two.
- Resulting proportions on the reported wilderness payload (3 × 3 in-view,
  remembered gateways present, so the 44.46-unit name band of
  `webclient-minimap-05-edge-markers-replace-list` applies):

  | | shipped | this change | draft |
  | --- | --- | --- | --- |
  | canvas (user units) | 262.91 × 234.91 | 208.91 × 222.91 | 180 × 150 |
  | uniform scale | 0.784 | 0.986 | — |
  | cells across the canvas | 4.53 | **5.22** | 7.50 |
  | dots drawn | **0** | ~29 | ~47 |
  | node label (CSS px) | 8.62 | **8.87** | 7.64 |
  | node label vs 10px chrome | 8.62, or 22 when sparse | ≤ 9 always | 7.64 |
  | node core / canvas width | 66% | **57%** | 40% |

  The draft's 7.5 cells across is **not** reached, and design D4 shows why with
  the arithmetic: a legible label drawn below a marker, clear of the next row's
  actionable halo, floors the pitch at 36 units, so a 206-unit canvas cannot carry
  more than 5.7 cells. The draft reaches 7.5 by letting its labels collide with
  each other and with their own marker — which this change refuses (design D8).
- Every new colour resolves to an existing design token: the dot field and the
  axis to `--ink-edge` (which *is* the draft's `#3a3344`), the vignette to
  `--map-canvas-lo` (within 3/255 per channel of the draft's `#0e0b13`). **No
  token is added and no draft hex literal appears anywhere**, as the shipped
  requirement already demands: "every marker, edge, label, and legend colour SHALL
  come from a design token … and no component SHALL hardcode a draft hex value".
- All three new layers are **decoration**: `pointer-events: none`, outside the
  accessibility tree, carrying neither the `local-map__marker` class the browser
  geometry audit pairs every box of nor the `local-map__node-label` class it pairs
  alongside it. They are static, so `prefers-reduced-motion` has nothing to
  disable; they encode no state, so the four-state ladder, its non-colour
  redundancy, the colourblind override, and every focus treatment are untouched.
  The state legend gains no entry for them — the beyond-state note rule keeps the
  legend's four states closed, and the dot field must never read as a fifth node
  state.
- `web/static/webclient/js/elosern/local_map.js` is **not** edited: the field
  padding is expressed by telling the existing `edgeMarkersFor` helper the padded
  field rect instead of the bare node rect, which its contract already accepts.
  The dependency-free Node gate keeps its behaviour.
- `MapOverlay.vue` is **not** edited and cannot regress: its `colPitch 280 /
  rowPitch 212 / labelMax 10 / markerScale 4.83 / maxWidth 848` all stand, the
  conditional label term (`(10 + 1) × 11 + 3 = 124`) is below both its pitches so
  it never binds, `labelFont` defaults to 11, the field padding and the axis are
  opt-in switches it does not pass, and the prop it never passed is the one being
  removed. It gains exactly one thing: the dot field, because that is a property
  of the lattice variant.

Out of scope — one line each, each owned by another change in this series:

- What counts as `remembered` → `local-map-remembered-are-map-gateways`.
- The island's single affordance and its coordinate readout →
  `webclient-minimap-04-island-single-affordance`.
- The edge markers' name geometry and their accessible mirror →
  `webclient-minimap-05-edge-markers-replace-list`.

Not in scope at all: the `local_map` v1 payload, the server presenter, both
validators, the preserved UMD render model and its Node gate, tap-to-move, and
the overlay's focus-restore contract. The project is pre-release with **zero
users**, so there is no backward-compatibility surface and no migration path to
design.

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `webclient-local-map`: "The browser minimap renders states without relying on
  color alone" — the requirement gains the coordinate dot field (its pitch's
  meaning, its registration to the placement, its presence-and-contrast band, and
  its ban on reading as a fifth node state), the knowledge-edge vignette (one per
  surface, no fabricated terrain, an outer-opacity cap that keeps the far field
  above the visibility floor), and the axis cross (drawn only where the convention
  is stated in words); its lattice-pitch clause becomes a derivation from what
  actually needs clearing rather than a constant; its node-label clause gains the
  type-proportion rule and the "never larger than the surface's own chrome"
  bound; and its fill clause replaces the bounded viewBox upscale with coordinate
  margin, retiring the upscale term from the single width bound.
- `webclient-contextual-hud`: "The minimap island states only its own drawing
  convention" — the header's `北↑ 東→` marks and the drawn axis cross become one
  claim stated twice, so a surface SHALL draw the axis only where it states the
  convention in words, and the island's marks are what license its axis.

## Impact

- Affected code: `web/webclient-app/components/MapLattice.vue` (the `<defs>`
  pattern and gradient, the two decoration rects and the axis group, the
  `labelFont` / `fieldFill` / `showAxis` / `fogVignette` props, the effective-pitch
  derivation, the field-rect padding passed to `edgeMarkersFor`, the label
  baseline, the removal of `maxUpscale` and of its term in `widthCaps()`, and the
  scoped styles for the three layers) and
  `web/webclient-app/components/LocalMap.vue` (the props the island declares).
  `web/webclient-app/stories/World/MapLattice.stories.js` gains the field/fog/axis
  stories at island and overlay scale.
- Not edited: `web/webclient-app/components/MapOverlay.vue`,
  `web/webclient-app/styles/tokens.css` (no new token),
  `web/static/webclient/js/elosern/local_map.js`,
  `web/webclient/presentation/local_map.py`, and both payload validators.
- Affected tests: `web/webclient-app/tests/world/map_lattice.test.js` (the field's
  registration to the placement, the pitch derivation in both cases, the label
  size and scale bounds, the layers' class/aria/pointer-events exclusions, and the
  overlay's unchanged geometry), `web/webclient-app/tests/world/local_map.test.js`
  (the island's declared props and the retired upscale),
  `web/webclient-app/tests/world/map_layout_variants.test.js` (the graph variant
  draws no field and no axis), and the browser gates
  `web.tests.browser.test_browser_local_map` (the ≥2px geometry audit at both
  pitches, the drawn-dot count, and the resolved contrast of each layer against the
  canvas ground) and `test_browser_contextual_hud`.
- No server, protocol, store, or payload change; the Python/JS validator parity
  contract and the dependency-free Node gate are untouched.
- Both modified requirement titles are modified in place with no rename, so every
  existing `@covers_requirement` anchor on
  `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone`
  and
  `webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention`
  stays valid.
- No player-facing command changes; `docs/game/commands.md` untouched.
