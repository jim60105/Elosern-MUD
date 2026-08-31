# Tasks: webclient-map-02-layout-variants

Depends on `webclient-map-01-draft-chrome` being implemented first (shares
`MapLattice.vue`, `LocalMap.vue`, `MapOverlay.vue`).

## 1. Model: radial placement pass

- [x] 1.1 In `web/static/webclient/js/elosern/local_map.js`, add `layoutRadial(model)`: BFS hop rings from `current` over an UNDIRECTED adjacency built from every committed edge in both directions (traversable or not); unreachable in-view nodes to the outermost ring in payload order; current-only or entirely edgeless payload renders the centre node alone on a fixed positive padded canvas; first-discovery + payload-index ordering.
- [x] 1.2 Implement design D1's exact geometry contract — marker half-extent 9, renderer-true label box 58×23 spanning y∈[+3,+26], diagonal footprint-pair span constant `ARC = 67`, clearances `R0 = G = 72` (amended from the disproved 44 before implementation), `arcMin(m) = ARC / (2·sin(π/m))` (`arcMin(1) = R0`), recurrence `R[k] = max(R[k−1] + G, arcMin(m_k))`, canvas side `2·(R[Rmax] + 26 + 24)` — as named constants with an English comment citing design D1; no ad-hoc heuristic.
- [x] 1.3 Export the radial placement alongside the lattice on the model (`radial: { nodes: [...ring/slot/x/y], width, height }`) without changing existing lattice fields; extend `reducePanel` output only additively.
- [x] 1.4 Node tests in `web/static/webclient/js/tests/local_map.test.js`: ring assignment on chain/cluster fixtures; byte-identical determinism; unreachable-node outermost ring; current-only and edgeless payloads (centre + fixed canvas); cycle / parallel-edge / reversed-serialization topologies produce identical rings; marker+label footprint non-intersection for adversarial 64-node distributions (one node per ring, dense outer vs sparse inner, one dense ring).

## 2. Shared renderer variant

- [x] 2.1 `MapLattice.vue`: add `variant` prop (`"lattice" | "graph"`); source coordinates from the matching placement; keep wave-1 marker/edge/label/legend templates, activation, focus, accessible names shared and unchanged; the overlay pin (wave-1 D4 ownership) follows the active placement's current node automatically.
- [x] 2.2 Verify the island's uniform scale-down applies to the radial canvas (it sizes from `radial.width/height`), keeping the non-overlap invariant scale-invariant.

## 3. Data-derived layout resolution

- [x] 3.1 `local_map.js`: add the pure resolver `variantForLayer(layer)` (`"grid"`/`"wilderness"` → `"lattice"`, anything else → `"graph"`) with an English comment naming the closed coordinate-layer contract (presenter `grid:`/`wild:` map-ID prefixes); `reducePanel` exports the resolved value as `layoutVariant`. NO preference, NO `stores/elosern.js` change, NO storage of any kind.
- [x] 3.2 Node tests: `variantForLayer("grid"|"wilderness")` → lattice; `"interior"|"instance"|unknown layer` → graph; `model.layoutVariant` follows the committed payload's layer with nothing else able to influence it.

## 4. Edge direction markers (lattice, coordinate payloads only)

- [x] 4.1 `local_map.js`: add the pure helper `remoteDirection(current, remote)` → `{ dx, dy, octant }` from RAW payload coordinates (`+y = 北`, eight octants, half-open sector bounds; comment cites design D3b). It MUST NOT read `col`/`row`.
- [x] 4.2 `local_map.js`: export `edgeMarkers` — one per `remembered` node STRICTLY outside the in-view coordinate bounding box (zero-delta and in-view nodes never mark), placed where the current→remote ray crosses the canvas rect and slotted along that edge inside a computed gutter `g` per design D3b's closed-form packing policy (explicit `{canvasWidth, canvasHeight, current}` geometry inputs — never an assumed pitch; deterministic order; markers mutually disjoint and outside the canvas rect, hence clear of node markers, labels, and axes); empty array for coordinate-free payloads and for the graph layout.
- [x] 4.3 `MapLattice.vue` (lattice variant): render the marker decoration layer — memory diamond (gold landmark treatment when flagged), optional faint ray segment, and place-name text at the overlay scale (the island keeps its remembered list as the canonical reading path); markers carry no activation; overlay-scale markers carry the name as accessible name.
- [x] 4.4 Node tests for D3b: octant correctness for due E/N and all four diagonals AND the half-open boundary vectors (a sector-edge bearing resolves to its declared octant); `(100,1)` and `(1,100)` resolve to their near-axis octants, NOT the diagonal (a compressed-rank implementation fails here); negative-coordinate deltas; a payload whose in-view span triggers rank compression still yields raw-coordinate directions; a remote coincident with the current node and an extent-interior remembered node produce no marker; interior/instance payloads export zero markers; gutter packing keeps marker footprints mutually disjoint at the 64-node bound for the all-on-one-edge worst distribution and randomized count splits at both shipped surface geometries.

## 5. Island and overlay wiring

- [x] 5.1 `LocalMap.vue` + `MapOverlay.vue`: both consume `model.layoutVariant` (and `edgeMarkers`); render NO layout control of any kind — no `.seg`, no button, no menu item (the withdrawn switch design must leave no residue); orientation marks follow `layoutVariant === "lattice"`; remove the `(x, y)` coordinate pair from `detailParts` (design D3) and update the Vitest assertions and `FocusedRemembered` story annotation that pinned it.
- [x] 5.2 Contrast pin: keep wave-1's lattice dot-field/axis tokens and confirm rendered contrast (dot fill-opacity ≥ 0.85, axis ≥ 1.5px at ≥ 0.65 over the map background) in the component tests.

## 6. Storybook sync

- [ ] 6.1 `MapLattice.stories.js`: pass the explicit `variant` prop per story (renderer takes a parameter; stories stay truthful); add a lattice story with edge markers on a coordinate fixture.
- [ ] 6.2 `LocalMap.stories.js`: fixtures for both resolved layouts (interior room-graph payload → radial; wilderness/grid payload → lattice with remembered-off-extent nodes showing markers); no story renders a layout control.
- [ ] 6.3 `MapOverlay.stories.js`: add the graph-layout story; keep the required-set manifest green (`npm run build-storybook`, `npm run showcase-coverage`).

## 7. Tests

- [ ] 7.1 Vitest: layout rendering parity (same nodes/edges/legend/actions in both layouts, model-selected), pin follows current node in both layouts (one pin, shared x, above y), overlay follows the model field on payload replacement (interior payload live-swaps to radial), orientation marks positive on coordinate layers / negative on interior+instance, edge markers render only on lattice payloads with the off-extent remembered set, and an absence assertion: the map chrome DOM contains no layout-control element.
- [ ] 7.2 Browser (mandatory, not CI-deferred): one class asserting the new public behavior — grid/wilderness fixture renders the lattice with edge markers on island and overlay; interior fixture renders the radial graph on both; no layout control exists in either surface; no outbound envelope beyond existing flows.
- [ ] 7.3 Focused gates: `npm test`, `node --test web/static/webclient/js/tests/local_map.test.js`, `uv run --locked python -m tools.spec_traceability check`, `openspec validate webclient-map-02-layout-variants --strict`.

## 8. Traceability

- [ ] 8.1 Re-annotate the delta requirements' owner tests (headings unchanged → IDs stable: `webclient-local-map::…renders-states-without-relying-on-color-alone`, `webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention`, `webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully`): the annotations live on the new/extended **Python browser** methods in `web/tests/browser/` (the traceability tool only discovers Python `test_*` AST decorators — JS tests are behavior evidence, never traceability claims); confirm `tools.spec_traceability check` green.
