# Design: webclient-map-00-story-fidelity

## Context

The store builds the map view model as `{ ...LocalMapLogic.reducePanel(panel),
available }` (`stores/elosern.js`), and `LocalMap.vue` / `MapOverlay.vue` consume
that derived shape. The `World/MapLattice` stories already model this correctly
via a private `modelFor()`; the `LocalMap`/`MapOverlay` stories pass raw
fixtures, so the reducer's `col/row/cols/rows` fields are absent and the
renderer degenerates to a 1×1 lattice. The shared fixture module owns all
`LOCAL_MAP_*` samples.

## Goals / Non-Goals

**Goals:** one shared fixture→model helper, every map story bound to the derived
model, the derived-shape binding made a spec clause, roadmap delivery table
amended for the three map waves.

**Non-Goals:** any chrome/layout change, new manifest titles, Vitest changes
beyond what story rebinding breaks.

## Decisions

### D1 — Export `localMapModelFor` from `stories/fixtures.js`, delete the private copy

The private `modelFor` in `MapLattice.stories.js` becomes an import. Keeping two
copies is how the drift happened. The helper mirrors the store's `localMapModel`
construction verbatim — `{ ...reducePanel(fixture), available: fixture.available
!== false, reason: fixture.reason }` — so stories cannot silently diverge again,
and the unavailable form keeps rendering the registry-owned reason (an earlier
draft of this task said `reason: null`, which would have blanked the
Unavailable stories; the store never normalizes the reason to null).

The verbatim mirror also exposes a live bug the raw-fixture stories were
concealing: `LocalMap.vue` seeds its selected node from `current_node`
(a raw-payload field the reducer renames to `currentNode`), so against the real
store shape the detail line mounts blank. Wave 0 fixes the component to read
`currentNode` — a one-field correctness fix inside the story contract this wave
exists to enforce, not a chrome/layout change.

### D2 — New stories use existing fixtures; interaction claims stay honest

The actionable-node story is a STATIC derived-model story: the halo renders
unconditionally for any node carrying an `action`, SVG `<g>` nodes are not
focusable, and clicking would dispatch the move intent — so the story documents
the halo and the committed intent without a play function, and the existing
Vitest mount tests remain the interaction contract (halo present; click emits
the exact `explore.move` payload). The focused-remembered story's play function
focuses a remembered-list `li` (it is `tabindex=0`) and the docs state exactly
what the detail line renders (name, explored state, coordinates — no landmark
field, no travel affordance). The tall-lattice scale-down story binds the
existing `LOCAL_MAP_TALL_LATTICE_SAMPLE` (2×64 nodes, 116×2830px natural vs the
206/296px caps) — the D2 conditional ("existing largest-span fixture if it
already exceeds the budget") resolves to no new fixture. Its docs record the
proportional scale `min(206/W, 296/H)`; jsdom proves only the style wiring, so
the rendered scale check runs in the browser Storybook pass. The shared
`localMapModelFor` helper MUST NOT mutate, duplicate, or synthesize fixture
data — it is exactly the store-side conversion and nothing else, or it stops
being the production-shape contract wave 0 exists to enforce.

### D3 — Roadmap amendment is part of this wave

Roadmap §9 says a wave that splits/resizes the delivery order edits the roadmap
itself, and §9's tracker rule is `Planned → In-progress → Done` with `Done`
only after strict validation and the change's gates. The three map waves are
new rows (M0/M1/M2) chained H6 → M0 → M1 → M2; M0 is created `In-progress`
because it is the change being implemented, M1/M2 as `Planned`; M0 flips to
`Done` at archive time under §9's conditions, and waves 1–2 flip when they
archive. Naming them here satisfies `webclient-component-showcase`'s governance
clause before wave 2 needs it.

## Risks / Trade-offs

- [Story rebinding changes snapshots/screenshot-based checks] → none exist
  (no chromatic); `npm test` assertions are DOM-level and only get stronger.
- [Play-function stories render non-deterministically in static build] → play
  functions don't run in `build-storybook` HTML; states are asserted in Vitest,
  stories document them; accepted.
- [`currentNode` fix shifts LocalMap test mounts] → migrating the mounts to
  helper-built models is required anyway (task 1.1b); the detail-line default
  assertions keep passing because the helper carries `currentNode`.
