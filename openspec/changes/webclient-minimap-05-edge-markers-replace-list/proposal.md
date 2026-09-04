## Why

The minimap island lists `remembered` places as a stack of chips below the map, each
carrying the identical 「◆」 diamond glyph. In the reported wilderness payload that produced
**seven chips all reading 「西部丘陵與谷地」** — seven identical rows conveying nothing. The
owner's verdict: 「因為每一個都是同樣的菱形方塊，所以我完全不知道這有什麼意義…像這樣子以清單
列在小地圖下方是錯誤的，完全沒有意義，因為它無法達到我的需求。」 What is wanted instead is
「它會在地圖的邊緣有一個小的圖示，講說這一座都市在這一個位置。那我就需要有這樣子的一個圖示，
還有圖示的旁邊要有一個文字，講說它是在哪裡。」

The machinery for that already exists and already ships: `edgeMarkersFor`
(`web/static/webclient/js/elosern/local_map.js:423`) computes true-bearing markers on the
canvas border from raw payload deltas, and it already accepts a `nameWidth`/`nameHeight`
name-box geometry. The island does not use it: it passes `0`/`0` and renders the whole
marker layer `aria-hidden` with no `<text>`, because the shipped requirement makes the list
the canonical reading path and the markers "a visual duplicate" that "SHALL NOT replace the
remembered list" (`openspec/specs/webclient-local-map/spec.md:177`). This change inverts
that contract: the markers become both the presentation and — through a mirror written for
assistive technology — the reading path, and the list below the island is deleted.

The change is the fourth of the minimap series and builds on the delta text of
`webclient-minimap-03-canvas-scale-and-budget` (the canvas's single width bound and the
fixed-point height budget), `webclient-minimap-04-island-single-affordance` (the full-bleed
button and the coordinate-only readout), and `local-map-remembered-are-map-gateways`
(`remembered` on a coordinate layer now means a map boundary the player has stood on, with
authored, pairwise-distinct labels and a 16-node presenter ceiling). Those three are what
make named markers worth drawing at all: before the gateway redefinition there was nothing
distinct to name.

## What Changes

- **BREAKING** (spec-level; the project is pre-release with zero users, so there is no
  migration): on the lattice variant the island's `ul.local-map__remembered` list is
  **deleted**. `remembered` nodes on `grid`/`wilderness` payloads are presented **only** as
  named edge direction markers. The requirement clause "SHALL NOT replace the remembered
  list, which remains the complete focusable reading path" is struck.
- The island's edge direction markers gain their place name as visible text, drawn **along
  the canvas's marker gutter band** — horizontally on the top/bottom edges, as a stacked
  glyph column on the left/right edges — never as an outward box perpendicular to the edge.
  The island declares a name band of `nameHeight` only (`nameWidth: 0`) so the reserved
  gutter grows from 26.46 to 44.46 user units instead of to 83.46, and the drawn lattice
  keeps 136 of its 158 CSS px rather than collapsing to 105.
- Each visible name is fitted to its marker's own free span along the edge, with a
  head-and-tail ellipsis that preserves the disambiguating tail. A new invariant forbids the
  defect directly: **the island SHALL NOT draw two equal marker names for two markers whose
  payload labels differ** — it drops the visible name rather than drawing 「西部丘陵…」 twice.
  The node-label `labelMax` (4) does not govern marker names.
- The accessible reading path becomes a **visually-hidden, non-focusable text mirror** of
  the drawn markers, listing each remembered place's full untruncated name and its octant
  direction word (北/東北/東/…). The island keeps exactly one tab stop — change 04's
  full-bleed affordance — and gains none.
- The graph variant's hole is closed explicitly: on the coordinate-free layers
  (`interior`, `instance`) — where `local-map-remembered-are-map-gateways` deliberately keeps
  the old "previously entered node outside the field of view" meaning and where no canvas
  edge exists for a bearing to point at — the island **keeps** the bounded remembered list.
  The list is scoped to that variant, and the two variants' optional sections are mutually
  exclusive.
- The canvas height budget's section list changes: the island's laid-out sections become the
  meta row, the canvas, and **at most one** of {the graph-variant remembered list, the
  coordinate readout}, so the island has at most three sections and at most two gaps at every
  payload. The gap count is derived from the sections actually laid out rather than from the
  list's emptiness.
- `web/static/webclient/js/elosern/local_map.js` is **not** edited: the island's needs are
  expressible in the existing `edgeMarkersFor` geometry contract. The dependency-free Node
  gate gains one surface row rather than a behaviour change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-local-map`: the remembered-node presentation contract (`:177`) inverts — edge
  markers replace the list on the lattice variant and carry visible names; the focus-a-node
  reading path (`:161`) is replaced by an assistive-technology mirror; the canvas height
  budget's section list (`:167`) loses the unconditional remembered-list term; the
  coordinate-free scenario (`:216-217`) is rewritten so interior remembered nodes keep a
  presentation.
- `webclient-contextual-hud`: the island's clause that a remembered node's name "stays
  available … as its entry's visible text" no longer holds on the lattice variant, where no
  entry exists; the replacement path is stated there too.

## Impact

- `web/webclient-app/components/LocalMap.vue` — the `ul.local-map__remembered` block, its
  `rememberedEl` ref and styles become graph-variant-only; `measureCanvasBudget()`'s section
  and gap arithmetic; a new visually-hidden marker mirror; the marker-name switch passed
  down.
- `web/webclient-app/components/MapLattice.vue` — an explicit marker-name switch replacing
  the `overlayChrome` gate on `<text>`, the island's `nameHeight`-only geometry, the
  along-band name placement for left/right edges, and the per-marker fit-to-span truncation.
- `web/static/webclient/js/elosern/local_map.js` — **unchanged** (argued in design D5).
- `web/webclient/presentation/local_map.py` and both payload validators — **unchanged**: no
  payload field, bound, or visibility rule moves.
- Tests: `web/webclient-app/tests/world/map_lattice.test.js` and the island's component
  tests; `web/static/webclient/js/tests/local_map.test.js` gains an island-with-names surface
  row in the packing invariant table (still dependency-free, still `node --test`); the
  browser gates `web.tests.browser.test_browser_local_map` and `test_browser_contextual_hud`.
