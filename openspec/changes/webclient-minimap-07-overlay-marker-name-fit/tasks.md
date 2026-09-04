# Tasks — The Overlay's Marker Names Obey the Geometry That Reserves Them

> Follows `webclient-minimap-05-edge-markers-replace-list` (the named markers and
> the island's fit) and `webclient-minimap-06-draft-lattice-fidelity` (the
> coordinate margin). Unlike the previous four changes in this series, this one
> DOES edit `web/static/webclient/js/elosern/local_map.js` — one additive,
> placement-preserving field (design D6), because the renderer's second copy of
> the model's slot arithmetic is what made this defect possible.
> `LocalMap.vue`, `tokens.css`, the presenter and both validators are NOT edited.
>
> Wave 1 is the baseline capture; waves 2–4 are the change; waves 5–6 are the
> gates. Work them in order — wave 1's captured baselines are what waves 2 to 4
> are proven against.

## 1. Wave 1 — pin the pre-change baseline

- [ ] 1.1 In `web/webclient-app/tests/world/map_lattice.test.js`, add a
  baseline case that renders the overlay props against `REPORTED_WILDERNESS_PAYLOAD`
  and records, per marker, its drawn name text, its `x`/`y`/`text-anchor`, and the
  SVG's `width`/`height`/`viewBox`. Every authored label in that fixture is inside
  the overlay's eleven-glyph capacity, so this case MUST stay green unchanged all
  the way through wave 4 — it is the proof that the fitting pass is a no-op for
  names that already fit. Waves 1-2 do not touch the overlay's early-return path,
  so the real regression check lands at task 4.2, where that path is deleted.
- [ ] 1.2 Add the same baseline for the island's props (`markerNames: true`,
  no `overlayChrome`) over the same payload, capturing its drawn names, its
  stacked-column `tspan` positions, and its gutter. It MUST stay green unchanged:
  the island declares `nameWidth: 0`, so design D2's outward term is structurally
  unreachable for it. Proof: `map_lattice.test.js`.

## 2. Wave 2 — the model returns the span the renderer was re-deriving

- [ ] 2.1 In `web/static/webclient/js/elosern/local_map.js`, add `span:
  usable / group.length` to each marker object `edgeMarkersFor` pushes, inside the
  per-side loop that already computes `usable` and places each marker at
  `inset + (slot + 0.5) * usable / group.length`. Change nothing else: no
  returned coordinate, no gutter, no ordering. Proof: `node --test
  web/static/webclient/js/tests/local_map.test.js` — every existing packing
  invariant stays green, and a new assertion pins that consecutive markers on one
  side are exactly `span` apart and that the first centre is `inset + span / 2`,
  at BOTH surface geometries in the existing surface table (`island`,
  `island_with_names`, `overlay`).
- [ ] 2.2 In the same Node gate, correct the surface table's `overlay` row from
  `nw: 72` to `nw: 121` (`web/static/webclient/js/tests/local_map.test.js:622`).
  `72` is stale: `MapOverlay.vue` declares `labelMax: 10`, so production reserves
  `(10 + 1) * 11 = 121`. The proposal's whole argument — the overrun table, the
  "converges on eleven glyphs" derivation, design D5's margin — rests on 121, and
  the dependency-free packing proof currently never evaluates it. Proof: the
  three packing invariants stay green at the corrected row.
- [ ] 2.3 In `web/webclient-app/components/MapLattice.vue`, delete
  `fittedEdgeMarkers`'s local `namePad` / `inset` / `slotMinH` / `slotMinV` block
  and its `bySide` / `spanBySide` grouping, and read `m.span` instead. Those
  literals are the model's formulas evaluated at `nameWidth: 0` — correct for the
  island, and 105 units of `inset` wrong for the overlay (design D6's table), so
  they MUST NOT simply be parameterized. Proof: wave 1's island baseline stays
  green, which is the proof that the model's span and the deleted arithmetic
  agreed for the surface where the copy was correct.

## 3. Wave 3 — the overlay declares its name step

> This wave comes BEFORE the fitting pass on purpose: wave 4 derives the reserved
> outward name box from `markerNameFont`, so the overlay must declare that prop
> first. Doing it the other way round would evaluate `(labelMax + 1) *
> markerNameFont` at the prop's default of 10, silently moving the reserved box
> from 121 to 110 units and with it the gutter the whole canvas is sized from.

- [ ] 3.1 In `web/webclient-app/components/MapOverlay.vue`, add
  `:marker-name-font="11"` to the `MapLattice` mount. `11` is the value
  `.local-map__edge-marker-name` hardcodes today, so no drawn glyph changes size.
  Proof: `web/webclient-app/tests/overlays/map_overlay.test.js` — the overlay's
  declared props, with `colPitch 280 / rowPitch 212 / labelMax 10 /
  markerScale 4.83 / maxWidth 848` unchanged beside it.
- [ ] 3.2 In `MapLattice.vue`, bind `:style="{ fontSize: `${markerNameFont}px` }"`
  on the overlay's `<text class="local-map__edge-marker-name">` and delete
  `font-size: 11px` from that rule, leaving it the shared font token and the
  `--paper-500` tier — the treatment the island's rule already has. Proof:
  `map_lattice.test.js` — the overlay marker name's inline size is 11px and the
  rule declares no `font-size` of its own.

## 4. Wave 4 — one fitting pass, parameterized by what the surface declares

- [ ] 4.1 In `MapLattice.vue`, replace the bare `11` in `layoutGeometry`'s
  `const nameWidth = props.overlayChrome ? (props.labelMax + 1) * 11 : 0`
  (line ~246) with `props.markerNameFont`, then lift that whole expression into
  a single computed that BOTH the `edgeMarkersFor` call and the fit budget read.
  The literal is a third independent copy of the overlay's glyph step, agreeing
  with the CSS rule and with `MapOverlay.vue`'s declared prop only by
  coincidence; leaving it would satisfy the letter of the "one number" invariant
  and miss its point (design D3). With wave 3 landed the value stays 121, so no
  reserved geometry moves. Proof: `map_lattice.test.js` — the computed outward box
  equals `(labelMax + 1) * markerNameFont`, equals the `nameWidth`
  `edgeMarkersFor` receives, and re-rendering the overlay with a different
  `markerNameFont` moves the reserved gutter with it.
- [ ] 4.2 In `MapLattice.vue`, delete the
  `if (props.overlayChrome) { ... return ... }` early return from
  `fittedEdgeMarkers` so both surfaces run one pass. Keep the existing
  `!props.markerNames` early return (a surface that draws no names still gets
  name-free markers). Proof: wave 1's two baselines stay green — this is the task
  they were captured for.
- [ ] 4.3 In the same function, replace `budget` with design D2's two-term
  form: `min(floor(span / markerNameFont), drawsOutward ? floor(outwardBox /
  markerNameFont) : Infinity)`, where `drawsOutward` is
  `outwardBox > 0 && (m.side === "left" || m.side === "right")` — derivable from
  the declared box and the marker the model returned, needing no new state, and
  matching the sides on which `markerNameX`/`markerNameAnchor` already place the
  name perpendicular to its edge. Proof: `map_lattice.test.js` — a 14-glyph label
  on a lone overlay `left` marker fits to eleven glyphs with an overflow
  indicator, while the same label on a lone overlay `top` marker (span 840) draws
  whole; the island's budget for both orientations is unchanged from wave 1.
- [ ] 4.4 Confirm the anti-ambiguity pass now covers the overlay because it sits
  after the branch removed in 4.2, and add no second implementation. It is live
  code, not dead code: design D4 closes the parenthesised branch through the
  presenter's qualifier rule but explicitly does NOT close the generic
  head-and-tail branch. Proof: `map_lattice.test.js` — two overlay `left` markers
  whose 14-glyph labels differ only in their middle and fit to the same eleven
  glyphs keep their diamonds, their landmark rings and their `aria-label`s, and
  neither draws a visible name.
- [ ] 4.5 Assert design D5's monotonicity directly: for the same payload, the
  overlay's per-marker glyph budget is strictly greater than the island's on every
  edge that carries a marker. Proof: `map_lattice.test.js` — both surfaces
  rendered over `REPORTED_WILDERNESS_PAYLOAD`, budgets compared per marker id.

## 5. Wave 5 — the browser gate

- [ ] 5.1 In `web/tests/browser/test_browser_local_map.py`, add a crowded-edge
  overlay case under
  `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone`:
  inject a payload placing several long-labelled remembered gateways through one
  overlay canvas edge, open the full map, and assert that no two
  `.local-map__edge-marker-name` boxes intersect and that every name box lies
  outside the canvas rect. Register nothing new in
  `.github/browser-shards.json` — `LocalMapBrowserTest` and
  `LayoutVariantsBrowserTest` are owned whole-class, so a new method inherits its
  shard; confirm with
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [ ] 5.2 Re-run `web.tests.browser.test_browser_local_map` unchanged otherwise,
  including the island geometry audit and the island type-ladder gate, as the
  regression proof that the shared renderer's island path did not move.

## 6. Wave 6 — verification

> Waves 1-4 are a day's work; waves 5-6 are where a single day most often slips,
> because authoring a crowded-edge browser case and running the full gates are
> both wall-clock heavy. Treat the wave 4/5 boundary as the checkpoint: the
> change is coherent and reviewable there even if the browser gate lands the
> following morning.

- [ ] 6.1 `npx vitest run` green, and `web/webclient-app/tests/world/map_lattice.test.js`,
  `tests/world/local_map.test.js`, `tests/world/map_layout_variants.test.js` and
  `tests/overlays/map_overlay.test.js` green individually.
- [ ] 6.2 `node --test web/static/webclient/js/tests/*.test.js` green and still
  dependency-free, with the span assertions from task 2.1 added. The
  packing-invariant surface table needs no new row: `span` is asserted over the
  rows already there.
- [ ] 6.3 `npm run build-storybook && npm run showcase-coverage` green — no new
  components, manifest unchanged. Add no story: the overlay's existing
  `MapLattice`/`MapOverlay` stories already cover the surface, and a crowded-edge
  story would be a fixture, not a component.
- [ ] 6.4 `uv run --locked python -m tools.spec_traceability check` green — the
  requirement is MODIFIED in place with no rename, so every existing
  `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone`
  anchor stays valid.
- [ ] 6.5 `openspec validate webclient-minimap-07-overlay-marker-name-fit --strict`
  green.
