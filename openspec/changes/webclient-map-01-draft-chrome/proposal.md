# Proposal: webclient-map-01-draft-chrome

## Why

The redesign draft (`docs/design/elosern-redesign/index.html`, `.mini` island and
`#ov-map` overlay) defines the target visual language for the map surfaces: a
seal-red current-node circle, small ink node dots, gold landmark dots, warm
tiered labels, a parchment-dark `mapcanvas` overlay body, and dot-chip legends.
The shipped `LocalMap`/`MapLattice`/`MapOverlay` still render the old
amber-square/monospace chrome, so the map surfaces are the largest remaining
visual divergence from the approved draft. This change re-chromes them to the
draft while keeping every existing behavioural contract (lattice model,
non-overlap, shared renderer, no-bearing rule, focus restore, combat hiding).

## What Changes

- Re-skin the minimap island to the draft `.mini`: draft header treatment
  (`局部地圖` title with the draft's letterspaced small-caps style and the
  coordinate-layer orientation marks `北↑`/`東→`), draft surface radius/border,
  and the draft's tiered label palette.
- Replace the lattice markers' draft-critical geometry in the shared
  `MapLattice` renderer (both island and overlay consume it): current node is a
  seal-red filled circle with a lighter seal stroke; `visible_visited` is a
  small filled ink circle; `visible_unvisited` is a small hollow circle;
  `remembered` keeps a distinct shape (rotated square) inside its existing
  out-of-canvas list; actionable halo restyled to the draft glow. State remains
  distinguishable by shape/size/label in addition to colour.
- Restyle connector edges to the draft strokes (traversable solid ink sw2,
  blocked dashed, unknown faint) and drop the visible edge-label text
  behaviour contract unchanged (accessible name only, as today).
- Re-chrome the full-map overlay body to the draft `mapcanvas`: radial-gradient
  dark terrain background, radius-12 ink border frame, and a teardrop location
  pin riding above the current-node circle. No fabricated terrain paths: the
  background is pure CSS, no invented geography.
- Restyle both legends to draft dot-chips (11px square chip + 11px muted label)
  and keep the state legend's text labels as the non-colour indicator.
- Make the whole island surface pointer-clickable as a convenience for opening
  the full map (draft affordance), while the existing labelled `expand` sibling
  control remains the keyboard-operable path with unchanged focus-restore.
- Add the draft palette values the tokens file lacks (seal deep `#a52c31`, seal
  light `#e06b6b`, ink edge `#3a3344`, label tiers) as new tokens in
  `web/webclient-app/styles/tokens.css`; components consume tokens, never raw
  hex.
- Deliberately omitted (no read model exists and main specs forbid them;
  recorded here so their absence is never mistaken for a gap): the draft's
  compass bearing (`北 324°`), the `滾輪縮放 · 拖曳平移` hint, and the gold
  dashed tracked-route line. The whole-island click never becomes a wrapper
  around the lattice because the labelled control stays a sibling.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `webclient-local-map`: the shared renderer's marker/edge/legend chrome,
  overlay `mapcanvas` styling, and island header adopt the draft visual
  language; the lattice model, non-overlap, shared-parameterized renderer,
  no-bearing, remembered-list, and edge rules are restated unchanged.
- `webclient-contextual-hud`: the minimap island requirement adopts the draft
  header/orientation-mark presentation and the pointer-click convenience on the
  island surface.

### Removed Capabilities

(None.)

## Impact

- Code: `web/webclient-app/components/MapLattice.vue` (marker/edge/legend
  templates + scale params), `LocalMap.vue` (island chrome, header, click
  convenience), `MapOverlay.vue` (mapcanvas body, pin, legend),
  `web/webclient-app/styles/tokens.css` (new draft tokens).
- Tests: Vitest selector/geometry updates in
  `web/webclient-app/tests/world/local_map.test.js`,
  `world/map_lattice.test.js`, `overlays/map_overlay.test.js`; stories
  `stories/World/LocalMap.stories.js`, `stories/Overlays/MapOverlay.stories.js`
  re-screenshot states (no new manifest entries in this change).
- Browser contract: `web/tests/browser/test_browser_contextual_hud.py`
  expand/focus-restore flow must pass unchanged (labels and ids preserved).
- No server, protocol, OOB, presenter, or store changes; no data migration.
