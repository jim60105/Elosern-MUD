# Remembered Nodes Are Map Gateways, Not Visited Ground

## Why

`remembered` currently means "every node I have ever entered that is not drawn
right now", and on the wilderness layer that produces a readout with no
information in it.

1. **Seven identical entries.** `_GraphBuilder.remembered()`
   (`web/webclient/presentation/local_map.py:333`) returns every visited node
   not already in the payload. `_wilderness_layer`'s remembered loop
   (`local_map.py:843`) then labels each remembered `wild:` cell with
   `WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)].display_name_zh`.
   A region is a coarse integer partition of the 224 × 224 continent
   (`world/maps/wilderness_provider.py:72`) and every cell in it shares one
   display name, so **every cell the player has ever walked becomes an
   indistinguishable entry**. The reported screenshot shows seven chips all
   reading 「西部丘陵與谷地」; a player who walks a region for an hour accumulates
   dozens, bounded only by the 64-node payload cap. The grid layer has the same
   shape of defect with less duplication: `local_map.py:477` emits every visited
   `grid:` room outside visual range.

2. **The list is not what the feature is for.** The origin of the remembered
   set is the edge direction marker (spec `:177`, REDESIGN §7.2): standing in
   the wilderness, know that a city lies east-north-east and a cave to the
   south-west — the **ways into other maps**, marked on the canvas border at
   their true bearing. A log of visited terrain answers a question nobody
   asked, and it crowds out the answer to the one that was.

3. **The domain already models the real thing.** `WildernessEntryPoint`
   (`world/lore/wilderness_entry.py:63`) carries an authored footprint mask, an
   `anchor_key` into `ANCHOR_REGISTRY`, and its `WildernessGate`s; a single-`#`
   mask is documented in that file as cave semantics and a larger mask is a city
   footprint. `approach_cell(gate)` gives the gateway's wilderness-side cell and
   `gate.grid_xy`/`gate.z_map_key` its grid-side room. The grid layer already
   reads that registry for its in-view gate nodes
   (`_grid_gate_candidates()`, `local_map.py:497`). Nothing new has to be
   modelled or stored — only interpreted.

## What Changes

- **BREAKING** (spec text; pre-release, zero users): on the coordinate-bearing
  layers (`grid`, `wilderness`) `remembered` stops meaning "a previously entered
  node outside the current field of view" and starts meaning **a map boundary
  the player has stood on**: a node whose traversal takes the player onto a
  different map. The coordinate-free layers (`instance`, `interior`) keep the
  shipped meaning — they draw no bearing geometry and their remembered set is a
  single interior's rooms.
- The gateway predicate is resolved at presentation time against
  `WILDERNESS_ENTRY_REGISTRY`, per layer:
  - wilderness — a visited `wild:` cell that equals `entry.approach_cell(gate)`
    for some registered entry and gate;
  - grid — a visited `grid:` room whose `(x, y, z_map_key)` equals some
    registered gate's `(grid_xy, z_map_key)`.
  An `AnchorRoom` alone does **not** qualify: the capital's plaza is an in-map
  landmark, not a way off the map, and it already has the `landmark` flag.
- **BREAKING**: a remembered gateway is carried at **its coordinates in the
  layer being drawn** — the approach cell's wilderness coordinates on the
  wilderness layer, the gate room's grid coordinates on the grid layer — so the
  edge marker's raw-coordinate-delta ray (spec `:177`) is computed inside one
  coordinate space. A gateway with no coordinate in the drawn layer (a gate onto
  a different `z_map_key` while the grid layer draws this one) is **omitted**,
  never plotted at a fabricated position.
- **BREAKING**: a remembered gateway is named by the **place its traversal
  reaches**, from the lore registries — `ANCHOR_REGISTRY[...].display_name_zh`
  on the wilderness layer (「聖潔王都」), the far-side wilderness region's display
  name on the grid layer — never by the terrain registry of the cell it sits on.
  Where two remembered gateways in one payload would carry the same far-side
  name (two gates of one city onto one region), each is qualified with the
  canonical name of the boundary node it carries, so the payload can never
  repeat a label.
- Remembering a gateway requires having **entered the node the drawn layer
  carries it as** — the approach cell for the wilderness layer, the gate room
  for the grid layer — checked against the stored `map_knowledge` visit record
  by exactly the canonical ID the payload emits. A player who has never been
  there never sees it.
- Remembered gateways are bounded by a declared cap of 16 and by the payload's
  remaining node budget, ordered most-recent `last_seen_tick` first then
  ascending node ID — the shipped deterministic order, unchanged. The natural
  bound is far smaller: at most one node per registered gate per layer (two
  today).
- A remembered gateway carries `landmark: true` (it is exactly what the gold
  landmark treatment is for), `anchor: false`, and `action: null` — the
  no-travel rule is untouched.
- **Owner has not ruled on this — strike it in review if unwanted.** A separate
  ADDED requirement kills the same duplication *inside* the field of view: the
  3 × 3 wilderness lattice currently labels all nine cells with one region name.
  (a) An in-view wilderness cell that is a registered gate approach cell is
  labelled with the far-side anchor's display name instead of its region name;
  (b) the shared renderer draws no visible label text for an in-view node whose
  label is identical to the `current` node's label, keeping the full label as
  the node's accessible name. This is its own requirement and its own task wave
  so removing it is a clean cut.
- No storage change. `world/rules/map_knowledge.py` stores
  `{node_id: {first_seen_tick, last_seen_tick}}` and `parse_knowledge` returns
  exactly that; `NodeVisit` carries no layer, landmark, or gateway flag and
  gains none. Every existing record keeps working because the change is in how
  the presenter interprets the same visited IDs, not in what is stored — a
  player who visited a cell before it became a registered gateway simply gains
  the gateway, which is the correct behaviour for a registry-resolved predicate.
- No payload schema change: no field is added, removed, or re-typed, so the
  Python/JavaScript validator parity contract and the dependency-free Node gate
  are untouched.

Out of scope — one line each, each owned by another change in this series:

- Removing the island's remembered list and moving the names onto the edge
  markers → `webclient-minimap-05-edge-markers-replace-list`; this change alters
  *what is remembered*, that one alters *how it is presented*.
- The island's single full-map affordance and its coordinate-only readout →
  `webclient-minimap-04-island-single-affordance`.
- The lattice's draft visual fidelity (dot field, fog vignette, axis cross,
  pitch and font ratios) → `webclient-minimap-06-draft-lattice-fidelity`.

Not in scope at all: the `map_knowledge` record and its writers, the wilderness
entry registry's authored data, the traversal resolver, the instance/interior
remembered set, and the shared validators' bounds. The project is pre-release
with zero users, so there is no backward-compatibility surface and no migration
path to design.

## Capabilities

### New Capabilities

<!-- None. -->

### Modified Capabilities

- `webclient-local-map`: this is the capability that owns the presenter. Its
  spec registers the panel, both coordinate layer adapters, the visibility
  states, and the minimap renderer; `map-knowledge` owns only the persisted
  visit record (unchanged here) and `wilderness-gateway` owns the registry, the
  gate exits, and `sync_wilderness()` (also unchanged here). Three requirements:
  - MODIFIED "Visibility states are current, visible_unvisited, visible_visited,
    and remembered" — the definition of `remembered` becomes layer-scoped: a
    stood-on map boundary on the coordinate-bearing layers, resolved against the
    entry registry, named by its far side, bounded and deterministically
    ordered.
  - MODIFIED "local_map is a read-only version-1 presentation panel" — the node
    geometry clause gains the coordinate-space rule for remembered nodes (a
    remembered node's `x`/`y` are its own coordinates in the drawn layer, and a
    node with no coordinate in that layer is omitted rather than positioned).
  - ADDED "The map surfaces state a place name only where it adds information" —
    the flagged, strikeable in-view duplicate-label rule.

  Not modified: "The browser minimap renders states without relying on color
  alone" needs no delta — its edge-marker clause already computes the ray from
  the **raw payload coordinate delta**, and this change makes that delta sound
  by guaranteeing both endpoints live in one coordinate space. "Only currently
  traversable Exits receive movement descriptors" needs no delta — a remembered
  gateway still carries `action: null`. "The minimap gate nodes match traversal
  in both directions" needs no delta — it governs the in-view gateway pair,
  which this change leaves exactly as shipped.

## Impact

- Affected code: `web/webclient/presentation/local_map.py` only —
  `_GraphBuilder.remembered()` (the candidate filter), a new registry-backed
  gateway resolver and far-side namer, the remembered loops in `_grid_layer`
  (`:477`) and `_wilderness_layer` (`:843`), and a new
  `MAX_REMEMBERED_GATEWAYS` module constant (a presenter bound, not a payload
  bound, so it is not mirrored in the JS validator). `_interior_graph`'s
  remembered loop is untouched. If the flagged in-view requirement survives
  review, `_wilderness_layer`'s neighbour loop and
  `web/webclient-app/components/MapLattice.vue`'s node-label text are also
  touched.
- Affected tests: `web/webclient/presentation/tests/test_local_map.py` —
  `test_visited_cells_beyond_adjacency_become_remembered` (`:1050`) pins the
  behaviour being replaced and is rewritten; `test_remembered_nodes_carry_no_action`
  (`:954`) and `test_graph_builder_remembered_bounds_by_last_seen` (`:652`) stay
  valid, the latter because the builder keeps its ordering contract;
  `test_wilderness_payload_uses_provider_bounds_and_terrain_labels` (`:1004`)
  asserts every node label is non-empty and stays valid under the label rules
  chosen here. New cases cover the four failure modes the delta scenarios name.
  `web/tests/browser/test_browser_local_map.py` seeds and reads the remembered
  list and needs its seed to produce a gateway.
- No client validator change, no protocol change, no OOB envelope change, no
  world/lore data change, no player-facing command change
  (`docs/game/commands.md` untouched).
- Both modified requirement titles are modified in place with no rename, so
  every existing `@covers_requirement` anchor on
  `webclient-local-map::visibility-states-are-current-visible-unvisited-visible-visited-and-remembered`
  and
  `webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel`
  stays valid.
