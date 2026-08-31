# Proposal: webclient-map-00-story-fidelity

## Why

The map stories are lying. `stories/World/LocalMap.stories.js` and
`stories/Overlays/MapOverlay.stories.js` feed the components the raw
`LOCAL_MAP_*` payload fixtures, but both components consume the reduced render
model (`LocalMap.reducePanel(panel)` output: `col`/`row`/`cols`/`rows`/
`remembered`), exactly like `stores/elosern.js` wires in production. Verified in
the running Storybook: `World/LocalMap — FullLattice` renders a 58×58 viewBox
containing one node inside the 230×318 island instead of the 9-node lattice the
fixture describes. The showcase contract says a story "is bound to
representative prop values and exposes at least its primary states" — a
degenerate 1-cell render is neither. The wave-1/2 map redesign builds on these
stories as its visual acceptance surface, so the fixture plumbing must be fixed
first.

This is the leading wave of the three-wave map redesign (00 → 01 draft chrome →
02 layout variants); it precedes them because it owns the story/fixture
contract they will extend.

## What Changes

- `stories/fixtures.js`: add `localMapModelFor(fixture)` — the exact store-side
  shape (`{ ...LocalMapModel.reducePanel(fixture), available, reason:
  fixture.reason }`, byte-identical to the `localMapModel` construction
  `stores/elosern.js` performs; `stories/World/MapLattice.stories.js` currently
  keeps a near-copy privately) — exported once and reused by every map story of
  the LocalMap/MapOverlay families. The helper performs the store conversion and
  nothing else: it never mutates or synthesizes fixture data. The verbatim
  mirror exposes a real bug the raw-fixture stories concealed — `LocalMap.vue`
  seeds its selection from `current_node`, which the reducer renames to
  `currentNode`, so against the live store shape the detail line mounts blank;
  this wave fixes the component to read `currentNode` (a one-field correctness
  fix, not a chrome/layout change).
- New stories exercising states that exist in code but have no story: the island
  actionable (traversable-adjacent) node emphasis state (a static derived-model
  story — the halo renders for any node with a committed `move` action; SVG node
  groups are not focusable and stories never dispatch), the focused-remembered
  detail line (play function focuses a remembered-list item; the detail renders
  name, explored state, and coordinates — the component carries no landmark
  field), and a tall-lattice story proving the scale-down path from the existing
  64-row fixture.
- Governance groundwork this repo requires for the two follow-on waves: add the
  three map waves (`webclient-map-00-story-fidelity`,
  `webclient-map-01-draft-chrome`, `webclient-map-02-layout-variants`) as rows
  M0–M2 of the HUD redesign roadmap's delivery table (`docs/superpowers/specs/
  2026-08-25-webclient-hud-redesign-roadmap-design.md` §6), so the later waves'
  manifest additions satisfy "grows only through a change named in the roadmap's
  delivery table". Per §9's tracker rule M0 lands `In-progress`, M1/M2
  `Planned`; M0 flips to `Done` at archive time.
- No component behaviour beyond the `currentNode` fix, no chrome, no layout
  changes — visual output for the currently-stated states stays identical
  except for being correct now.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `webclient-component-showcase`: the story-binding requirement gains an
  explicit clause that a component consuming a derived render model SHALL be
  story-bound to that same derived shape (raw payload args for a model-consuming
  component are a contract violation, not a style choice).

### Removed Capabilities

(None.)

## Impact
- Code: `web/webclient-app/stories/fixtures.js`,
  `stories/World/MapLattice.stories.js` (shared import replaces its private
  copy), `stories/World/LocalMap.stories.js`,
  `stories/Overlays/MapOverlay.stories.js`,
  `stories/Overlays/OverlayHost.stories.js` (its MapSurface story binds the
  same family), and the one-field `currentNode` fix in `components/LocalMap.vue`.
- Docs: roadmap §6 delivery table (three new rows; §9 tracker rule governs the
  Status flips).
- Tests: `npm test` (story/fixture contracts plus a new helper-vs-store parity
  case), `tests/world/local_map.test.js` mounts migrate to helper-built models,
  `npm run build-storybook` + `npm run showcase-coverage` stay green (no
  manifest change in this wave: the coverage check fails on stories WITHOUT a
  manifest entry, and the new stories live under already-listed titles);
  `deferred_surfaces_absent.test.js` untouched.
- No store, protocol, or server change; the only production-component change is
  the `currentNode` field fix.
