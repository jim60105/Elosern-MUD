## Why

`MapOverlay.vue` (the "展開全地圖" full-screen surface, reached from the minimap island's expand
button) renders `<LocalMap :local-map="localMap" />` unmodified inside a plain centering wrapper
(`MapOverlay.vue:52-54`, `.map-overlay__content { display: flex; justify-content: center; }`). Its
host, `OverlayHost.vue`, gives the overlay body up to `max-width: 900px` and the remaining viewport
height (`OverlayHost.vue:254-262`) — but `LocalMap.vue`'s own `.local-map__lattice` rule caps the
rendered canvas at `max-width: 206px` (`LocalMap.vue:436`), because that constant is sized for the
230px-wide minimap island (`LocalMap.stories.js:22`, `width: 230px`), not for a full-screen surface.
The result, verified by screenshotting the running client at 1440×900: opening "展開全地圖" produces
the exact same small, cramped lattice as the corner minimap, centered in an otherwise empty ~900×700px
dark rectangle — the single largest visual gap against `docs/design/elosern-redesign/index.html`'s
equivalent surface, which renders its map at the full available canvas size with generously spaced
nodes, visible connector lines, and un-truncated place-name labels beside each node.

This is a distinct problem from `fix-webclient-local-map-node-crowding` (already proposed separately):
that change fixes the *shared* lattice geometry so markers/labels/edges never collide at the minimap's
own small scale; this change gives the full-map *surface* a scale appropriate to the space it actually
has, so opening it is worth doing. Both changes touch `LocalMap.vue`'s rendering internals and should
land in the order proposed (crowding fix first) so this change's larger-scale lattice inherits already
non-colliding geometry rather than a second, independent set of spacing constants to get right.

## What Changes

- Extract the SVG lattice (nodes, markers, connector edges, per-node labels, node
  hover/select/activate interaction) plus the legend and detail line out of `LocalMap.vue` into a new
  shared component, `MapLattice.vue`, parameterized by an explicit column-pitch/row-pitch/marker-size
  scale rather than the fixed constants `LocalMap.vue` uses today. `LocalMap.vue` becomes the island
  chrome (title/meta row, orientation legend, expand button, remembered-node list) composing
  `<MapLattice>` at its existing (post-crowding-fix) small scale — no behavior change for the minimap.
- `MapOverlay.vue` composes the same `<MapLattice>` at a larger scale that fills the overlay body's
  available width (up to the existing 900px cap) and height, with a taller label truncation threshold
  (or none, given the extra room) so place names read in full where they fit.
- **Explicitly out of scope (non-goals, deferred to a future change):** pan/zoom interactivity, a
  terrain baseline graphic, and displaying the `remembered` remote-node list inside the overlay — the
  overlay renders exactly the same in-view node/edge/legend data the minimap already renders, just at a
  larger scale. No new data is requested, invented, or displayed.
- **BREAKING**: none. `LocalMap.vue`'s public props/emits, every `data-testid="local-map__*"` hook, the
  `#action-dock`-independent DOM contract, and the `local_map` payload contract are all unchanged; the
  extraction is an internal refactor of one component into two.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-local-map`: the "browser minimap renders states without relying on color alone"
  requirement gains an explicit scenario that the full-map overlay renders the same lattice content at
  a larger scale proportionate to its available surface, rather than at the minimap island's fixed small
  scale.

## Impact

- **Code**: new `web/webclient-app/components/MapLattice.vue` (extracted rendering logic);
  `web/webclient-app/components/LocalMap.vue` (slimmed to island chrome, composes `MapLattice`);
  `web/webclient-app/components/MapOverlay.vue` (composes `MapLattice` at overlay scale instead of the
  whole `LocalMap`).
- **Stories**: add `World/MapLattice` stories at both the minimap scale and the overlay scale (reusing
  the existing `LOCAL_MAP_SAMPLE`/`LOCAL_MAP_WILDERNESS_SAMPLE` fixtures); update
  `World/LocalMap.stories.js` and `Overlays/MapOverlay.stories.js` only if their rendering wrapper needs
  adjustment — their existing fixtures and args stay valid since the payload contract is unchanged.
  Extend `component-manifest.json`'s required-set with `MapLattice` (an internal building block, not a
  player-facing surface addition, but the manifest tracks every shipped component).
- **Tests**: a component-level test that `MapLattice` renders identical node/edge/legend content at two
  different scale props (regression guard for the extraction itself), plus a browser-level check that
  `MapOverlay`'s rendered canvas width scales with the overlay body's available width rather than
  staying pinned at the minimap's 206px cap.
- **No protocol, read-model, or OOB payload changes.** `local_map.js`'s reducer/lattice-assignment logic
  is untouched.
- **Depends on** `fix-webclient-local-map-node-crowding` landing first (shared file: `LocalMap.vue`'s
  lattice-geometry constants move into the new `MapLattice.vue` during this change's extraction, so
  extracting *before* the crowding fix lands would mean re-deriving the same pitch/marker-size decision
  twice). Because both changes carry a `MODIFIED` delta against the same `webclient-local-map`
  requirement, this change's spec delta must be refreshed to include the crowding fix's landed
  scenarios before this change is archived (see design.md's Risks and tasks.md task 1.2) — the delta as
  currently drafted reflects the spec text on disk today, not the post-crowding-fix state.
