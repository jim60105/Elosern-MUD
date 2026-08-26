## Context

`LocalMap.vue` today does three jobs in one component: (1) the island chrome — title/meta row,
orientation legend, the "展開全地圖" expand button, the bounded remembered-node list; (2) the SVG
lattice — nodes, markers, connector edges, per-node labels, click/hover interaction; (3) the shared
selection state (`selectedId`/`hoveredId`), the state legend, and the hovered/selected-node detail line,
which reads from *both* the lattice's in-view nodes and job (1)'s remembered-node list
(`activeNode`, `LocalMap.vue:126-135`, searches both collections; the remembered `<li>` calls
`selectNode` directly, `LocalMap.vue:296-297`). `MapOverlay.vue` needs only job (2), rendered at a
different scale, but today it can only get it by rendering `<LocalMap>` whole, inheriting job (1)'s
island-sized chrome and job (2)'s island-sized `206px` canvas cap along with it.
`fix-webclient-local-map-node-crowding` (proposed separately, landing first) fixes job (2)'s internal
geometry so markers/labels/edges never collide at the minimap's scale; this change makes job (2)
reusable at a second, larger scale without duplicating its logic — and, because job (3)'s selection
state spans both the lattice and the remembered list, job (3) stays with `LocalMap.vue` rather than
following job (2) into the new component.

## Goals / Non-Goals

**Goals:**
- The full-map overlay renders the same in-view nodes, edges, and legend the minimap renders, sized to
  actually use the overlay body's available space (up to its existing 900px cap), instead of the
  minimap's fixed 206px canvas centered in empty space.
- No duplication of the lattice-*rendering* logic (`nodePos`, `edgeGeoms`, `truncatedLabel`, the
  marker/edge SVG template) between the minimap and the overlay — one component, two callers, two scale
  configurations.
- The minimap island's own rendered output and interaction (including the remembered-node list driving
  the shared detail line) are unchanged by this refactor — this change only adds a second consumer of
  the lattice-rendering piece, at a different scale.

**Non-Goals:**
- Pan, zoom, or drag-to-scroll interactivity on the overlay's lattice.
- A terrain baseline, background texture, or any visual element beyond nodes/edges/legend/labels — the
  same visual vocabulary the minimap already uses, just larger.
- Rendering the `remembered` remote-node list inside the overlay. It stays a minimap-only, bounded,
  focusable list (`LocalMap.vue`'s own template, not extracted); the overlay shows only the in-view
  lattice, matching what "expand" conceptually expands — the visible local map, not the remembered-node
  index.
- The hover/select detail line (`local-map-detail`) inside the overlay. Selection state
  (`selectedId`/`hoveredId`) has no visual effect on the SVG itself in today's implementation — it only
  feeds that text line — so the overlay can render the lattice without adopting the parent's selection
  state at all; a future change may add an overlay-local detail line if wanted, out of scope here.
- Any change to the `local_map` OOB payload, the reducer in `local_map.js`, or the `explore.move`
  submission path.

## Decisions

**Extract only the lattice's rendering (SVG nodes/markers/edges/labels) plus the stateless state legend
into `MapLattice.vue`; keep selection state (`selectedId`, `hoveredId`, `activeNode`, `detailParts`) and
the detail-line paragraph in `LocalMap.vue`.** `MapLattice.vue` emits `hover(node)`, `leave()`, and
`move(payload)` on the underlying node interactions instead of owning `selectNode`/`hoverNode`/
`clearHover` itself; `LocalMap.vue` listens to those events to update its own `selectedId`/`hoveredId`
and re-render its (unmoved) detail line and remembered-node list exactly as before — the remembered
list's existing `@click="selectNode(node)"` needs no change at all, since `selectNode` never left
`LocalMap.vue`'s scope. `MapOverlay.vue` only wires `MapLattice`'s `move` event through to its existing
`handleMove`; it does not need to listen to `hover`/`leave` at all, matching the Non-Goals decision to
omit a detail line from the overlay. Take scale as an explicit prop (or a small set of pitch/marker-size
props) rather than reading a CSS class name or viewport size. Alternatives considered:
- *Give `MapOverlay.vue` its own independent lattice-rendering template*, duplicating `LocalMap.vue`'s
  SVG-building logic with different constants — rejected: two independently-maintained copies of the
  same node/edge/label geometry logic is exactly the kind of drift this review is trying to close (it is
  how `--dock-h` ended up referenced by zero, then some, but not all, of its intended consumers in the
  sibling `fix-webclient-scene-backdrop-placeholder-overlap` change).
- *Have `MapOverlay.vue` render `<LocalMap>` but pass a "scale" prop through to it, having `LocalMap.vue`
  conditionally suppress its own chrome when scaled* — rejected: conflates "am I the minimap island" with
  "what scale am I" in one component's conditional logic, whereas the overlay and the island are simply
  two different callers of the same lattice-rendering primitive with two different surrounding chromes.
  The extraction keeps each component's responsibility singular.
- *Scale the existing small lattice up with CSS `transform: scale()`* — rejected: this enlarges the
  already-crowded (pre-fix) or already-fixed (post-fix) minimap geometry uniformly, including its
  truncated 6-character labels; it does not let the overlay show more of each place name in the extra
  room it has, which is the actual visual gap being closed.

**Take pitch/marker-size as props with the minimap's current values as their defaults**, so
`LocalMap.vue`'s call site needs no changes beyond passing the data props it already has, and
`MapOverlay.vue`'s call site is the only place that opts into the larger scale. This keeps the crowding
fix's chosen constants (landing first) as the single source of the minimap's default geometry — this
change does not re-decide them, only parameterizes them.

**Keep the remembered-node list and the "展開全地圖" trigger in `LocalMap.vue`, not `MapLattice.vue`.**
Both are conceptually island chrome (a focusable disclosure list; a button that opens a sibling surface)
rather than lattice-rendering, and neither has an analog inside the overlay it opens (per the Non-Goals
above).

## Risks / Trade-offs

- **This change's `specs/webclient-local-map/spec.md` delta was authored against the spec text on disk
  today, before `fix-webclient-local-map-node-crowding` archives** → OpenSpec's archive step replaces a
  `MODIFIED` requirement's on-disk text with the delta's full block and fails if the on-disk requirement
  (at archive time) carries a scenario the incoming block omits. Since the crowding fix (landing first)
  adds three new scenarios to this same requirement, archiving this change afterward with an unchanged
  delta will fail that check. This change's delta MUST be refreshed to include the crowding fix's
  landed scenarios before this change is archived (task added to tasks.md) — do not archive on the
  originally-drafted delta text.
- **Extraction risk to existing minimap behavior** → the crowding fix (landing first) already needs to
  touch and verify every piece of geometry logic this change moves; extracting it into a new component
  immediately afterward, with the minimap's call site passing the exact same values as defaults, is a
  mechanical move with a low behavioral-regression surface, verified by re-running the existing
  `webclient-local-map` browser/Vitest coverage unchanged (same testids, same DOM shape from the
  minimap's perspective).
- **The overlay's larger scale could still overflow at 1280×720 on a dense, many-row payload** →
  `MapLattice.vue`'s canvas keeps the same `max-width`/`height:auto` proportional scale-down rule the
  minimap uses today (verified safe under uniform scaling by the crowding fix's own risk analysis), just
  with a larger cap; the overlay body's own `overflow-y: auto` (`OverlayHost.vue:261`) is the existing
  fallback for anything still too tall.
- **Un-truncating or lengthening labels at the overlay's scale could still crowd on a very dense
  lattice** (many short-pitch nodes with long names) → keep a truncation threshold at the overlay scale
  too, just a higher one than the minimap's 6 characters; the crowding fix's non-intersection assertion
  pattern (bounding-box check per marker/label pair) is reused here at the overlay's scale as the actual
  gate, not a hand-picked character count.
