# Tasks — Named Edge Markers Replace the Remembered List

> Fourth in the minimap series. It builds on `webclient-minimap-03-canvas-scale-and-budget`
> (in the working tree), `webclient-minimap-04-island-single-affordance` (the full-bleed
> affordance and the coordinate-only readout), and `local-map-remembered-are-map-gateways`
> (remembered = a stood-on map boundary, distinct authored labels, 16-node ceiling).
> `web/static/webclient/js/elosern/local_map.js` is NOT edited (design D5); only its Node
> gate's surface table gains a row.

## 1. Wave 0 — the renderer draws names on the island

- [ ] 1.1 In `web/webclient-app/components/MapLattice.vue`, add a `markerNames`
  boolean prop (default `false`) and stop deriving the marker-name geometry from
  `overlayChrome`: the `edgeMarkersFor` call passes `nameHeight: markerNames ? 16 : 0` and
  the `<text v-if>` gate becomes `markerNames`. `MapOverlay.vue` passes
  `:marker-names="true"` alongside `overlay-chrome`, so its geometry
  (`nameWidth: (labelMax + 1) * 11`, `nameHeight: 16`) and its outward name placement are
  byte-identical to today. Proof: `web/webclient-app/tests/world/map_lattice.test.js` — an
  overlay-props render still emits the same gutter and the same `<text>` positions as before
  the change.
- [ ] 1.2 In the same file, keep `nameWidth: 0` for the island (`markerNames` without
  `overlayChrome`) so the model reserves band depth only: `namePad = 18`,
  `gutter = 44.46` user units on the reported 174 × 146 shape (design D2). Proof:
  `map_lattice.test.js` — an island-props render with two remembered nodes reports
  `edgeMarkers.gutter === 2 * Math.SQRT2 * 9 + 1 + 18` and a canvas of 262.91 × 234.91.
- [ ] 1.3 In the same file, place the island's left/right marker names **along** the band as
  a stacked glyph column (one `<tspan>` per code point at the marker's `x`, `dy` = the line
  step) instead of the outward-horizontal `markerNameX() = ±markerOutset()` placement, and
  keep the top/bottom names horizontal and centred as they already are. Proof:
  `map_lattice.test.js` — a left-edge island marker's name renders as *k* `tspan`s within the
  band's depth, and an overlay left-edge marker still renders one horizontal outward `<text>`.
- [ ] 1.4 In the same file, set the island's marker-name font to 13 user units (rendering at
  ~10.2 CSS px once the 206px width bound scales the 262.91-unit canvas) and give the name
  its own class distinct from `.local-map__edge-marker-name`'s overlay sizing. Proof:
  `map_lattice.test.js` — the island's marker-name class resolves to a token-driven size and
  no draft hex or pixel literal is hardcoded.

## 2. Wave 1 — names are fitted, and never ambiguous

- [ ] 2.1 In `MapLattice.vue`, compute each marker's free span along its own edge from the
  marker set `edgeMarkersFor` returns (distance to the neighbouring slot centre on the same
  side, or to the band's end), and truncate the drawn name to that span with a head-and-tail
  ellipsis that allocates the tail first (design D3). The node-label `labelMax` MUST NOT
  govern it. Proof: `map_lattice.test.js` — a lone marker on an edge draws
  西部丘陵與谷地（南門） whole; two markers on one edge draw names within their spans.
- [ ] 2.2 In the same file, enforce the anti-ambiguity invariant: if fitting would make two
  drawn names equal while their payload labels differ, the visible name of the marker that
  cannot be distinguished is omitted while its diamond, its bearing, its landmark ring, and
  its text-alternative entry stay. Proof: `map_lattice.test.js` — with
  西部丘陵與谷地（南門） and 西部丘陵與谷地（北門） crowded on one edge, the set of drawn
  names contains no duplicate and both markers still render.
- [ ] 2.3 Add the untruncated payload label as each island marker group's `<title>`, as the
  marker's accessible name. Do NOT describe it as a tooltip: the marker layer is
  `pointer-events: none` (design D7), so no hover disclosure can fire on it for any user —
  the sighted, no-AT reader's path to a name the island truncated or dropped is the full-map
  overlay (design D8), not this element. Proof: `map_lattice.test.js`.
- [ ] 2.4 Pin the overlay disclosure path (design D8): assert that under `overlayChrome` the
  shared renderer still draws every edge marker's name as visible text and as its accessible
  name, at the overlay's own scale, for the same crowded payload whose island rendering
  omitted a name in 2.2 — so the ambiguity rule can never make a place reachable only through
  assistive technology. Proof: `map_lattice.test.js` and `overlays/map_overlay.test.js`.

## 3. Wave 2 — the island loses the list and gains the text alternative

- [ ] 3.1 In `web/webclient-app/components/LocalMap.vue`, render `ul.local-map__remembered`
  **only when the resolved layout variant is `graph`**, and drop `tabindex="0"`, the
  `@click`/`@focus` handlers and the now-dead `selectNode` path from its items so the entries
  are plain, non-focusable text. Proof:
  `web/webclient-app/tests/world/local_map.test.js` — a wilderness payload renders no
  `[data-testid="local-map-remembered"]`; an interior payload renders it with one entry per
  remembered node and no element carrying `tabindex`.
- [ ] 3.2 In the same file, pass `:marker-names="true"` to `MapLattice` and render a
  `ul.visually-hidden` sibling of the canvas (the clip-rect pattern already used by
  `DockMenu.vue`/`ActionDock.vue` — never `display: none`), labelled 已知的地圖出入口, with
  one `<li>` per drawn marker reading `<untruncated label>，<octant word>`, ordered by octant
  then payload index. The octant words are 北/東北/東/東南/南/西南/西/西北 from the model's
  own `octant`. Proof: `local_map.test.js` — one hidden entry per drawn marker, carrying the
  untruncated label, with no `tabindex` anywhere in the island but the affordance.
- [ ] 3.3 In the same file, keep the island's SVG marker layer `aria-hidden="true"` and
  `pointer-events: none` so nothing is announced twice and a click over a marker still opens
  the full map through the island body. Proof: `local_map.test.js` — clicking an edge marker
  emits exactly one `open-map`.

## 4. Wave 3 — the height budget counts what it lays out

- [ ] 4.1 In `LocalMap.vue`, replace `measureCanvasBudget()`'s
  `gapCount = 2 + (remembered.length > 0 ? 1 : 0)` and its fixed three-term `others` with a
  derivation over the sections actually laid out: meta, canvas, and at most one of the
  graph-variant list and the readout, with `gapCount = laidOutSections - 1` (design D6). The
  budget source (`floor(dockTop - anchorTop - 12)`), the 25px fixed chrome, and the
  `[40, 296]` clamp are unchanged. Proof: `local_map.test.js` — on change 03's 1280×720
  fixture shape the lattice variant yields `424 - 31 - 16 - 25 = 352 → 296`, the graph variant
  with no remembered nodes yields `424 - 15 - 8 - 25 = 376 → 296`, and a 16-entry graph list
  yields 144.
- [ ] 4.2 Add a regression asserting the gutter cannot breach the cap: a lattice payload whose
  markers crowd one edge (gutter grown well past `gutterMin`) still renders a canvas whose
  height is at most the measured cap, and the settled island re-measures to the same cap.
  Proof: `local_map.test.js`.

## 5. Wave 4 — the gates

- [ ] 5.1 In `web/static/webclient/js/tests/local_map.test.js`, change the packing-invariant
  surface table's island row to `{ cw: 90, ch: 58, mh: 9, nw: 0, nh: 16 }` and keep the
  existing name-free row, so both island geometries are covered. The three invariants
  (pairwise L1 disjointness, no L1 tip inside the canvas rect, marker plus name box inside the
  outer rect) are unchanged, and no production line of
  `web/static/webclient/js/elosern/local_map.js` is edited. Proof:
  `node --test web/static/webclient/js/tests/*.test.js` stays green and dependency-free.
- [ ] 5.2 Update `web/tests/browser/test_browser_local_map.py`: assert the wilderness island
  renders named edge markers and no remembered list, the interior island renders the list, the
  island exposes exactly one tab stop, and the hud-right anchor has no scrollbar at 1440×900
  and 1280×720. Proof: `web.tests.browser.test_browser_local_map`.
- [ ] 5.3 Update `web/tests/browser/test_browser_contextual_hud.py` for the island's keyboard
  path: tabbing into the island reaches the full-map affordance and nothing else, on both
  layout variants. Proof: `web.tests.browser.test_browser_contextual_hud`.
- [ ] 5.4 Run the full set — `npx vitest run`, `node --test web/static/webclient/js/tests/*.test.js`,
  `web.tests.browser.test_browser_local_map`, `test_browser_contextual_hud`,
  `test_browser_layout`, `test_browser_shell` — and record the counts in the change's
  verification note.

## 6. Wave 5 — documentation

- [ ] 6.1 Update `docs/design/elosern-redesign/REDESIGN.md` §7.2's "Accessibility floor"
  bullet, which still states that the island's remembered list "remains the complete,
  focusable reading path" and that the markers "duplicate it visually". Replace it with the
  contract this change ships: named markers are the presentation on the lattice, a
  non-focusable text alternative is the reading path, and the list survives on the graph
  variant only. Proof: review — the note no longer contradicts
  `openspec/specs/webclient-local-map/spec.md`.
