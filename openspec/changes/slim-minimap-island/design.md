# Design — Slim Minimap Island

## Context

`MapLattice.vue` is the shared renderer for both minimap surfaces: the HUD
island (`LocalMap.vue`, right rail, canvas capped by a dynamically measured
height budget) and the full-screen overlay body (`MapOverlay.vue`, ~848 px
wide, scroll fallback). The lattice root is an `svg + legend` fragment, so the
legend `<ul data-testid="local-map__legend">` is mounted on whichever surface
mounts the lattice — today both. `LocalMap.vue` measures the island's other
sections (meta row, remembered list, legend, detail line) and subtracts them
from the hud-right anchor's height budget to cap the canvas.

Two current spec clauses stand in the way of the request:
`webclient-local-map` ("The browser minimap renders states without relying on
color alone") requires both legends to render as dot-chips and ends with "No
surface SHALL render a bearing, a compass angle, a distance, or a coordinate
figure in any form, on any layer", and `webclient-contextual-hud` ("The minimap
island states only its own drawing convention") repeats the ban for the island.
The amendments below are therefore part of the change, not an implementation
detail — spec and code land together.

## Goals / Non-Goals

**Goals**

- Island renders the map canvas only (plus the title/orientation/expand header
  and the remembered-list + detail-line reading path they anchor).
- Overlay keeps the state legend exactly as it is.
- Coordinate layers (`grid`, `wilderness`) state direction (the existing
  `北↑ 東→` header marks) and the current node's world coordinates on the
  island.
- Graph layers render no bearing and no coordinate figure (ban intact).

**Non-Goals**

- No payload/protocol/server change — `legend` stays in the payload; the
  island just stops rendering it.
- No change to tap-to-move, focus restore, remembered-list keyboard path, the
  click-body-opens-overlay convenience, or the overlay's chrome (the overlay's
  own no-bearing/no-coordinate clause in
  `the-map-settings-and-help-surfaces-are-reachable-from-the-live-client` is
  untouched — the readout is island-only by requirement, and the overlay keeps
  `showLegend` defaulting true).
- No removal of the detail line or remembered list: they are the island's
  accessible reading path (and `MapLattice`'s edge direction markers consume
  the remembered list), not legend chrome.

## Decisions

### D1 — `showLegend` prop on MapLattice; island opts out

`MapLattice.vue` gains `showLegend: { type: Boolean, default: true }`. When
false the legend `<ul>` is not rendered at all — `v-if`, not a CSS hide, so DOM
assertions are unambiguous and the island's budget measurement can never see a
stray legend. `LocalMap.vue` passes `:show-legend="false"`; `MapOverlay.vue` is
unchanged (default true). Default-true keeps every existing call site
(stories, tests mounting the lattice bare) rendering the legend without edits.

**Alternative rejected**: CSS `display:none` at the island — leaves stale DOM
that the budget comment already had to scope around once.

### D2 — Coordinate readout rides the existing detail line; bearing stays the header marks

The payload's node `x`/`y` on coordinate layers are validated world
coordinates (the spec's own layer-scoped-semantics clause). When the active
detail node is the *current* node and the layer is `grid` or `wilderness`,
`detailParts` appends `座標 <x>,<y>`. Hovering/selecting another node keeps the
current behavior (that node's label + state, no coordinates — the ban outside
the current node stays so the island never becomes a coordinate inspector for
arbitrary nodes… and, decisively, a non-current node's coordinates are as
easily misread as a claim about *distance from here*, which stays banned).
Graph layers never append the part.

The bearing statement is the header's existing `北↑ 東→` orientation marks:
on a north-up lattice renderer that *is* the bearing convention, already
scoped to the lattice variant (`showsOrientation` keys off
`layoutVariant === "lattice"`, which the render model resolves from `layer`
exactly for `grid`/`wilderness`). No second compass glyph. The amendment turns
"MAY state" into the required reading pair: marks + coordinate figure.

**Alternative rejected**: in-SVG corner glyphs — the canvas is
geometry-measured and capped; header/detail text reuses measured chrome and
costs the canvas nothing.

### D3 — Island budget drops the legend term

`measureCanvasBudget()` removes the `legendEl` lookup and its
`sectionHeight` term, and the island's section/gap constants are re-derived
(meta + canvas + remembered? + detail): `gapCount` becomes
`2 + (remembered.length > 0 ? 1 : 0)` minus one fewer inter-item gap, with the
slack constant re-pinned against the remaining sections. The legend's height
(~28 px with its gap) returns to the canvas. Vitest pins the arithmetic against
the reduced section list.

### D4 — Traceability: MODIFY in place, no rename

Both requirements keep their titles, so all existing
`@covers_requirement` literals (`webclient-local-map::the-browser-minimap-…`,
`webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention`)
stay valid. Tests whose assertions *established the old legend/ban behavior*
get their assertions updated (legend absent on the island, present on the
overlay; coordinate figure present on coordinate layers, absent on graph
layers) under the same anchors. `tools.spec_traceability check` must stay green
in the same commit.

## Risks / Trade-offs

- [Island loses the legend's non-color state reminder] → The node shape ladder
  (large stroked circle / solid / hollow / diamond) is itself the non-color
  encoding the requirement protects, and it is unchanged; the legend remains on
  the overlay one click away. The amendment keeps "State distinction does not
  depend on color alone" satisfied via shapes on the island.
- [Budget constants drift after the legend term is removed] → D3 re-pins them
  and Vitest measures the arithmetic.
- [Browser tests assert legend presence inside the island] → Updated in this
  change (`web/tests/browser/test_browser_local_map.py` names them by test-id).
- [Coordinate figures misread as distance/safety semantics] → The figure is
  only ever the current node's own two integers, never a delta, never on graph
  layers, never on the overlay; the amendments keep the distance and compass
  bans verbatim.

## Migration Plan

Single-commit cutover (no shipped users): components + Vitest + stories, then
the browser-suite assertion flips, then `spec_traceability check` + both
`openspec validate`. Revert = revert the commit; nothing persists.

## Open Questions

None blocking. (Whether the detail line should *also* show the zone for grid
nodes — the payload title already carries it; not added.)
