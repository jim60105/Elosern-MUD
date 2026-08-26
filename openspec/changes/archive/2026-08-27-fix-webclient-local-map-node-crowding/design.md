## Context

`web/webclient-app/components/LocalMap.vue` renders the `local_map` v1 panel as an SVG lattice: each
in-view node is placed at `col * CELL + CELL/2, row * CELL + CELL/2` with `CELL = 24`, and its label is
drawn as a second `<text>` element offset `y="24"` below the node's own origin (`LocalMap.vue:75-93,
276-278`). Node markers are a 26×26 `<rect>` for the current node or a 24px-diameter `r=12` `<circle>`
for every other visibility state (`LocalMap.vue:237-268`). Because the marker's own footprint already
consumes the full 24px cell, and the label is drawn one full cell-height below the node it belongs to,
two effects compound on any room with more than one adjacent node (the common case, not an edge case):

1. Adjacent markers in the same or neighboring row touch or overlap with no visible gap.
2. A node's label lands almost exactly on top of the node (and its label) one row below, and — because
   labels are horizontally centered under a node with `text-anchor="middle"` at the same 24px column
   pitch — also bleeds into the horizontally adjacent node's label.
3. Connector edges (`<line>` elements between node centers, `LocalMap.vue:212-223`) render entirely
   underneath the touching markers, so they are visually absent even though they are correctly computed
   and present in the DOM.

This is a single shared root cause — one lattice pitch reused for column spacing, row spacing, and
marker sizing, with no reserved margin for the label — not three independent bugs, so one geometry fix
in `LocalMap.vue` addresses all three symptoms.

`MapOverlay.vue` (the "展開全地圖" full-screen surface) renders this exact same component unmodified
(`MapOverlay.vue:52-54`), so it inherits today's crowding and will inherit the fix without its own code
change. Giving the overlay a distinct, larger-scale rendering (so it isn't just a small minimap pasted
into a mostly-empty full-screen surface) is deliberately **out of scope** here — that is a separate,
larger visual-treatment change; this change only needs to make the shared lattice geometry internally
non-colliding at whatever size it renders.

## Goals / Non-Goals

**Goals:**
- Every rendered node marker's visual footprint and its label's visual footprint SHALL NOT intersect the
  footprint of any other node's marker or label, at every lattice size the model can produce (up to the
  existing 64×64 bound), in both the minimap island and the (unmodified) full-map overlay.
- Connector edges SHALL be visibly distinguishable between two node markers they connect (not fully
  occluded by the markers themselves).
- No change to `local_map.js`'s lattice column/row assignment, the OOB payload contract, or the
  `explore.move` submission path.

**Non-Goals:**
- Redesigning the full-map overlay to use extra available screen space (separate change).
- Adding pan/zoom, a terrain baseline, or any visual element beyond what today's minimap already draws
  (markers, labels, edges, legend, detail line).
- Changing the truncation rule's *behavior contract* (a label is still bounded to a fixed character
  count with an ellipsis and the full text remains reachable via the accessible name / `<title>`); only
  the pixel geometry around it changes.

## Decisions

**Decouple column pitch, row pitch, and marker size — do not reuse one `CELL` constant for all three.**
The row pitch must be large enough to fit a node's own marker radius *plus* its label's rendered line
height *plus* a minimum visible gap before the next row's marker begins; the column pitch must be large
enough that two labels centered under horizontally adjacent nodes, at the existing truncation length,
do not visually overlap. Alternatives considered:
- *Move labels to the side instead of below the node* — avoids the vertical collision but does not fix
  horizontal label-to-label crowding on a dense row, and changes the marker/label visual relationship
  the existing Storybook stories and any downstream screenshot baselines assume more than a pitch change
  does. Rejected in favor of the smaller, more local fix.
- *Shrink marker size only, keep `CELL = 24`* — reduces marker-to-marker overlap but does not reserve
  room for the label, which is the larger of the two collisions observed. Rejected as insufficient on
  its own.
- *Truncate labels more aggressively (fewer characters) instead of widening the column pitch* — makes
  already-short place names (e.g. "南門") unrecognizable and does not fix the vertical collision at all.
  Rejected as a partial fix that trades one legibility problem for another.

**Keep the fix inside `LocalMap.vue`; do not touch `local_map.js`.** The lattice's column/row
*assignment* (which node sits at which integer coordinate) is already correct and spec-governed
(`webclient-local-map`'s lattice requirement); only the *pixel geometry* used to place and size the SVG
elements at each lattice coordinate is wrong. Keeping the fix in the Vue component's rendering layer
avoids touching the dependency-free Node-tested reducer or the wire contract at all.

**Verify with a bounding-box non-intersection browser assertion, not hand-picked pixel constants as the
acceptance gate.** The roadmap's own established pattern (H2's island non-overlap check "at both
1440×900 and 1280×720") is to assert the *outcome* geometrically rather than pin exact pixel values in
the spec text — a font substitution, a locale string length change, or a future density tweak should not
silently reintroduce the bug. The new scenario in the `webclient-local-map` delta spec states the
invariant (no marker/label footprint intersects another), and the implementation picks whatever pitch
and marker-size constants satisfy it (a starting point: roughly 40–44px row pitch and 36–40px column
pitch against the existing 12px marker radius and 11px/6-character label, re-tuned as needed until the
assertion passes at the lattice's densest realistic case).

## Risks / Trade-offs

- **A wider lattice may no longer fit the island's existing `max-width: 206px` cap on a room with many
  in-view nodes** → the existing `.local-map__lattice` rule already scales the whole SVG down
  proportionally via `max-width` + `height: auto` when the natural pixel size exceeds it (`LocalMap.vue:
  430-442`); a uniformly larger lattice still scales down the same way, so extremely dense rooms shrink
  rather than overflow, exactly as today. The non-intersection assertion is checked at the SVG's own
  natural (pre-scale) geometry, since uniform scaling preserves relative non-overlap.
- **Enlarging the lattice grows the minimap island's height on rooms with many rows**, which could
  approach the H2 risk item (island stack vs. dock overlap at 1280×720, tracked in the HUD roadmap §8) →
  re-run that existing non-overlap browser check as part of this change's acceptance, not just the new
  map-internal one.
- **Visual regression in Storybook screenshots/snapshots**, if any exist, from the changed pitch/marker
  ratio → none of `LocalMap.vue`'s stories currently have a covering test (confirmed via the codebase's
  dependency graph), so there is no existing baseline to break; the new browser assertion becomes the
  first automated check of this component's rendered geometry.
