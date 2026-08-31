# Proposal: webclient-map-02-layout-variants

## Why

The game map has two fundamentally different shapes of space, and the payload
already says which one it carries: `interior`/`instance` payloads come from
plain Evennia room/exit graphs where node `x` is a layout index and no world
coordinate exists, while `grid`/`wilderness` payloads come from Evennia's
xyzgrid/wilderness sources where node `x`/`y` are validated world coordinates
(`XYZNode.X/Y`, wilderness provider coordinates). One rendering cannot be
truthful for both: forcing wilderness into a radial graph invents distances,
and forcing a shop cluster into a coordinate grid implies spatial facts the
payload does not carry. The design draft draws BOTH faithful renderings as its
binding reference (`REDESIGN.md` §7 + the island/overlay layers in
`index.html`): a radial connected-node graph and a coordinate lattice with a
dot-field, an axis cross through the current node, `北↑ 東→` header marks, a
knowledge-edge vignette, and — for coordinate payloads — **edge direction
markers** that place remembered-but-off-canvas places (a trade city, an
underground cavern) on the canvas rim at the direction of their true
coordinates. Wave 1 made both surfaces speak the draft's visual language; this
change ships the *layout* duality: the layout is a pure function of the
payload's layer, never a player choice.

## What Changes

- New DOM-independent layout pass in `web/static/webclient/js/elosern/local_map.js`:
  `layoutRadial(model)` places the current node at the centre and arranges each
  connected in-view node on rings by exit-hop distance from current (BFS over
  an UNDIRECTED adjacency built from every committed edge, so ring membership
  never depends on edge serialization direction; in-view nodes unreachable by
  any edge take the outermost ring ordered by payload order; a current-only or
  edgeless payload renders the centre node on a fixed padded canvas), with
  deterministic ring slots so the same payload always renders identically.
  Exported as part of the render model (placement stays in the model, never in
  a component).
- `MapLattice.vue` (renamed conceptually to the shared map renderer, file name
  kept) gains a `variant` parameter: `"lattice"` renders the existing
  integer-lattice geometry; `"graph"` renders the radial geometry — same
  markers, edges, labels, legend, activation, and non-overlap guarantees in
  both variants. The radial non-overlap guarantee follows design D1's explicit
  geometry contract (label/marker footprint boxes, ring-to-ring clearance,
  per-ring arc minimum, cumulative radius recurrence, fixed canvas padding),
  pinned by adversarial-distribution Node tests — not a heuristic.
- Layout resolution is **data-derived with no player control**: a shared pure
  resolver `variantForLayer(layer)` maps the closed coordinate-bearing set
  (`grid`, `wilderness`) to `lattice` and everything else to `graph`; the model
  exports the resolved `layoutVariant` and both surfaces consume it, so they
  can never disagree. There is NO segmented switch, NO preference, NO storage of
  any kind — an earlier design with a three-segment `.seg` and a `mapLayout`
  preference is explicitly overturned by the owner ruling: the format follows
  the world, not taste. A future coordinate-bearing layer must amend presenter,
  schema, and spec together; the UI never guesses.
- Coordinate payloads gain **edge direction markers**: the model exports one
  marker per remembered node whose coordinates fall outside the drawn extent,
  positioned by the pure helper `remoteDirection(current, remote)` from the
  **raw payload delta** (never compressed `col`/`row` ranks; `+y = 北`, eight
  octants with half-open sector bounds) where the ray from the current node
  crosses the canvas's marker-safe border. The renderer draws the memory diamond
  (gold landmark treatment when flagged) with an optional faint ray segment —
  direction only, never a distance, angle, or coordinate figure — deterministically
  slotted so markers never overlap each other, node markers, labels, or the
  axes, and with no activation of their own. The island's existing remembered
  list remains the complete, focusable reading path; in surfaces without the
  list (the overlay) each marker carries its place name as visible text and as
  its accessible name. Coordinate-free payloads render no markers (their `x` is
  a layout index, not a place).
- The island's orientation marks (`北↑ 東→`, per the draft's lattice header) show
  only under the lattice layout — the layout that draws its own axis cross —
  and the graph header omits them, making the two layouts' truth claims
  explicit.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `webclient-local-map`: the model SHALL export a second (radial graph)
  placement alongside the lattice; the shared renderer SHALL render either
  placement under one chrome with the non-overlap guarantee holding for both;
  the variant SHALL be resolved once from the payload's `layer` by the shared
  resolver, with no player-facing control, preference, or storage; coordinate
  payloads SHALL export edge direction markers for off-extent remembered nodes
  under a raw-coordinate direction contract; and the node `x`/`y` semantics
  clause is amended from a blanket "renderer-local geometry" claim to the
  layer-scoped two-meaning contract (validated world coordinates on
  `grid`/`wilderness`, layout indices elsewhere) — numeric readouts stay banned
  everywhere.
- `webclient-contextual-hud`: the minimap island SHALL NOT present any map
  layout control (the draft-era segmented switch is superseded); the island and
  the full-map surface render the same data-resolved layout, and the
  orientation marks follow the resolved layout.
- `webclient-component-showcase`: the map surface's truthful-render clause names
  both layouts and the layer-driven resolution explicitly, forbidding invented
  distance, bearing, or terrain geometry in either.

### Removed Capabilities

(None.)

## Impact

- Code: `web/static/webclient/js/elosern/local_map.js` (radial pass,
  `variantForLayer` resolver, `remoteDirection` helper, model export of
  `layoutVariant` + `edgeMarkers`), `web/webclient-app/components/MapLattice.vue`
  (variant rendering + marker decoration layer), `LocalMap.vue` /
  `MapOverlay.vue` (variant wiring, no controls added).
- Storybook sync (truthfulness gate): `MapLattice.stories.js` passes the
  explicit `variant` prop per story, `LocalMap.stories.js` gains coordinate- and
  coordinate-free-layer fixtures exercising both resolved layouts,
  `MapOverlay.stories.js` gains the graph story; `npm run build-storybook` and
  `npm run showcase-coverage` stay green.
- Tests: Node tests for `layoutRadial` determinism, the D1 geometry contract,
  `variantForLayer`, `remoteDirection` octants, and adversarial 64-node
  distributions in `web/static/webclient/js/tests/`; Vitest layout-rendering
  parity, marker geometry, absence-of-control, and pin-follow tests; browser
  contract (mandatory in this change): a coordinate-layer payload renders the
  lattice with edge markers on both surfaces, no layout control exists anywhere
  in the map chrome, and the overlay follows the island's resolved layout.
- Depends on `webclient-map-01-draft-chrome`: both waves edit
  `MapLattice.vue`/`LocalMap.vue`/`MapOverlay.vue`; wave 2 consumes wave 1's
  marker/edge/legend chrome. Sequential implementation required.
- No server, protocol, presenter, or payload changes; nothing persists anywhere.
