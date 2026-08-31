# Design: webclient-map-02-layout-variants

## Context

Wave 1 (`webclient-map-01-draft-chrome`) re-chromed the island, the shared
`MapLattice.vue` renderer, and the overlay in the draft's visual language while
keeping the integer-lattice placement. The design draft now carries BOTH map
modes as its binding reference (`docs/design/elosern-redesign/index.html`
variant layers + `REDESIGN.md` §7): the island drawn as a *connected graph*
(current node centred, neighbours radiating along exit lines, labels hugging
the nodes) and a coordinate-lattice variant (dot-field, axis cross through the
current node, `北↑ 東→` header marks, knowledge-edge vignette). The committed
`local_map` payload already carries `edges` (`from`/`to`/`traversable`), `nodes`
with `visibility`, and a `layer` string; `reducePanel` in
`web/static/webclient/js/elosern/local_map.js` already computes the lattice
placement and exports `cols`/`rows`. The payload's `layer` is the format
discriminator: the presenter maps `GridRoom` → `grid` and `TerrainRoom` →
`wilderness` (both carrying validated world coordinates from xyzgrid
`XYZNode.X/Y` / the wilderness provider), and plain rooms → `interior` /
`instance` (fake `(index, 0)` layout values from `_interior_graph`).

Two truthful space models must coexist:

- settlement/interior: discrete places joined by exits → the draft's graph is
  the faithful rendering;
- wilderness (and the coordinate-bearing `grid` layer the fixtures use): exits
  embedded in coordinate space → the lattice is the faithful rendering.

## Goals / Non-Goals

**Goals:**

- One visual language (wave 1 chrome), two layouts matching the draft's two
  drawn surfaces: `graph` (radial) and `lattice` (existing geometry).
- Placement computed in the DOM-independent model for both layouts.
- Non-overlap guarantee extended to the radial variant.
- Layout resolved purely from the payload's `layer` — no player control, no
  preference, no storage (owner ruling: the format follows the world).
- Remembered places outside the drawn extent become edge direction markers on
  the lattice, computed from raw coordinates.
- Overlay and island always render the same resolved layout for the same payload.

**Non-Goals:**

- No payload/protocol change: edge lengths carry no distance claim in either
  layout, and no new payload fields are needed (remembered nodes already carry
  coordinates).
- No zoom/pan, bearing/route-line features, or any map-layout UI control
  (spec-forbidden; the earlier `.seg` switch design is withdrawn).
- No server-side anything: nothing persists client-side either.

## Decisions

### D1 — Radial placement lives in the model, not the component

`local_map.js` exports `layoutRadial(model)` returning, per in-view node,
`{ ring, slot, angle, radius, x, y }` plus the canvas size. Rationale: the main
spec already mandates model-side placement (a wave-1 unchanged clause), and Node
tests can then pin determinism without a DOM. The component only consumes
coordinates. Alternative (compute in `MapLattice.vue`): rejected — forks the
model contract and untestable in the Node gate.

Algorithm (deterministic): BFS hop distance from `current` over an UNDIRECTED
adjacency built from every committed edge (both `source→destination` and its
reverse; the panel's exit topology is physically symmetric even where the
payload serializes one direction, and ring membership must not depend on
serialization direction), traversable or not (edges are topology, not
passability). In-view nodes unreachable by any edge join the outermost ring;
for a current-only or entirely edgeless payload `current` sits alone at the
canvas centre and the canvas is a fixed positive padded square. Rings 1..R;
each ring's members sorted by first-discovery order then payload index; slots
evenly spaced, offset so ring 1 centres on the upward axis (draft look).

Explicit geometry contract (unscaled units; the island's uniform scale-down
still applies): the label footprint is the conservative box `LW × LH = 58 × 22`
(the lattice cell width as max label width, 22 to cover the label below the
marker) with centre offset `dy = 14` under the node; marker footprint is the
wave-1 circle ladder (r8 current / r5 gold / r4.5 other). Radial clearance
between consecutive rings: `G = 44` (the lattice row pitch already bounds
marker + label stacked vertically). Per-ring minimum radius for angular
separation of its `m` members: `arcMin(m) = (LW + gap) / (2·sin(π/m))` for
`m ≥ 2`, `arcMin(1) = r0` (a chosen base radius ≥ marker + label half-extent).
Ring radii follow the recurrence `R[1] = max(r0, arcMin(m1))`,
`R[k] = max(R[k−1] + G, arcMin(m_k))`. Canvas side =
`2·(R[Rmax] + LH/2 + dy + pad)` with `pad = 24`; the 64-node bound makes the
canvas bound a closed number (worst case one dense ring of 64 ≈ 1270px), which
the island scales down uniformly. This recurrence is the contract Node tests
pin — implementers MUST NOT substitute their own arc heuristic.

### D2 — Variant is a renderer parameter, not a component fork

`MapLattice.vue` takes `variant: "lattice" | "graph"`; markers/edges/labels/
legend templates stay shared (wave 1 chrome), only coordinate sourcing differs.
This preserves the "shared, parameterized, not duplicated" clause verbatim. The
non-overlap clause is amended (delta) to hold "for each variant at every
placement the model can produce".

### D3 — Layout is data-derived: one pure resolver, zero player surface

`variantForLayer(layer)` is a pure function in `local_map.js`:
`layer === "grid" || layer === "wilderness"` → `"lattice"`; anything else →
`"graph"`. `reducePanel` stores its result on the model as `layoutVariant`; the
island and overlay consume that one field. There is no segmented control, no
`mapLayout` preference, no `stores/elosern.js` change, no localStorage — an
earlier revision of this change specified a three-segment `.seg`
(`自動`/`連線圖`/`網格圖`) with a client-local preference; the owner overturned
it (the world's format is not a taste setting), and every artifact here
reflects the ruling. Tests pin the ABSENCE: the map chrome exposes no
layout-control element.

The coordinate-bearing set is a **closed contract mirrored across layers**:
`grid`/`wilderness` correspond one-to-one to the presenter's canonical map-ID
prefixes (`grid:` from xyzgrid, `wild:` from the wilderness contrib) and to the
`_grid_layer`/`_wilderness_layer` presenter branches that are the only
producers of real coordinates. A future layer with validated coordinates MUST
amend presenter + payload schema + this spec together; the client resolver
never guesses from payload shape.

Consequences pinned by tests: the `北↑ 東→` orientation marks render exactly
when `layoutVariant === "lattice"` (a graph draws no axis, so the graph header
omits them — which on current payloads coincides with coordinate-free layers,
keeping wave 1's behavior a special case of this rule, not a duplicate rule);
the island's outer footprint is identical for both layouts.

### D3b — Edge direction markers: raw-coordinate rays, list stays canonical

`reducePanel` additionally exports `edgeMarkers`: for each `remembered` node
whose coordinates fall outside the drawn lattice extent, one entry
`{ id, name, landmark, dx, dy, octant, x, y }`, where `remoteDirection(current,
remote)` computes `dx = remote.x − current.x`, `dy = remote.y − current.y` from
the **raw payload coordinates** — never from the lattice's compressed `col`/`row`
ranks, because rank compression preserves order, not ratios (`(100,1)` must not
render as 45°). `octant` uses `+y = 北` with half-open sector bounds so boundary
vectors are deterministic. Placement: the marker sits where the ray from the
current node crosses the canvas's marker-safe border, slotted deterministically
so markers never overlap each other, node markers, labels, or the axes; the
payload's 64-node bound makes the count finite and the layout closed-form.

Rationale for raw coordinates: `compressAxis` in `local_map.js` is for in-view
spacing only; the direction claim belongs to the world delta, and the presenter
already emits remembered nodes with their true coordinates (grid: cells beyond
`MAX_GRID_VISUAL_RANGE`; wilderness: non-adjacent remembered nodes). The
renderer draws the existing memory diamond (gold ring when landmark) plus an
optional faint ray segment — direction is the only claim. The island's
remembered list is UNCHANGED and remains the complete focusable reading path
(existing contract; markers are additive); in the overlay (no list) each marker
carries its place name as visible text and accessible name. Coordinate-free
payloads produce no markers at all — reading an `_interior_graph` index `(n,0)`
as a direction would fabricate a place.

### D5 — Overlay follows the model's resolved layout

Both surfaces read `model.layoutVariant` (D3), so divergence is impossible by
construction — there is no preference channel through which they could drift.
Neither surface carries any layout control. The overlay re-renders when a newly
committed payload resolves differently (e.g. leaving the wilderness for an
interior swaps lattice → radial graph live).

## Risks / Trade-offs

- [Radial labels can collide] → the D1 recurrence (ring-to-ring clearance +
  per-ring arc minimum) is the contract; Node tests pin footprint
  non-intersection at the 64-node bound for adversarial distributions (one
  node per ring, dense outer next to sparse inner, one dense ring,
  cycle/parallel/reversed-edge topologies); the canvas grows and the island's
  existing uniform scale-down applies (scale-invariant invariant).
- [Browser tests pin lattice geometry] → the browser fixture payload is
  `layer: "grid"` → the resolver picks lattice → existing assertions hold
  unchanged (edge markers are a decoration layer outside the node-placement
  invariant); the graph layout gets its own mandatory browser case (interior
  payload renders radial on both surfaces: new public behavior, covered in this
  change, not deferred to CI).
- [Island/overlay disagreement] → structurally impossible: one model field
  (`layoutVariant`), no preference channel, no component-local state (D5).
- [Markers misread as travel targets] → markers carry no activation, duplicate
  the remembered list's nodes (never replace it), and the direction helper is
  pure + octant-tested; a compressed-rank bug changes octants for `(100,1)`-style
  deltas and fails the Node tests.
- [Marker crowding on one canvas edge] → deterministic per-edge slotting inside
  the marker-safe border (D3b); the 64-node payload bound caps density, and
  non-overlap with node markers/labels/axes is a Node-test invariant.
- [Lattice chrome too faint to carry its geometry claim] → wave 1's dot-field
  and axis contrast are pinned (dot fill-opacity ≥ 0.85, axis ≥ 1.5px at ≥ 0.65
  over the map background) alongside the existing token rules.
- [One-workday sizing] → mitigated by keeping the browser cases narrow (layout
  resolution is a pure-function Node test; the DOM only checks presence/absence
  and follow-through) and the geometry contracts in the model where Node tests,
  not DOM tests, do the heavy pinning.
