# Sparse settlement graphs

This page records the unit and ownership contract introduced by
`implement-sparse-settlement-graphs` (world-map-scale design §11). It is the
reference for changing settlement maps, route finding, or the grid bootstrap.
The metric cutover (`activate-metric-settlements`) landed on top of it: the
authored coordinates are now integer metres and there is no ASCII map.

## Ownership

The pure graph types, validation and routing live in the independent
`packages/map-core` package (`elosern_map_core.sparse`); the game consumes it
through the locked local dependency declared in the root `pyproject.toml`.

| Concern | Owner |
| --- | --- |
| Sparse nodes, explicit roads, validation, route planning | `packages/map-core/elosern_map_core/sparse.py` |
| Contrib `XYMap` adaptation for synthetic/builder maps | `world/maps/xymap_graph.py` |
| Authored settlement documents (nodes, roads, prototypes, options, location-relative entrances) | `content/maps/settlements/<map_id>.yaml` |
| Explicit load, cross-document validation and immutable publication | `world/maps/map_data.py` |
| Read-only registry views over the published snapshot | `world/maps/published.py` plus the owning registry modules |
| Persistent room/exit convergence | `world/maps/bootstrap.py::sync_grid` |
| Stable room identity attribute | `typeclasses/rooms.py::GridRoom.sparse_node_id` |
| Grid/anchor map knowledge bounds | `world/rules/map_knowledge.py` |
| Player `前往`/`goto` routing | `commands/localized/xyzgrid.py` |

Lore and quest modules read the declarations; they never write a graph. Only
`world/maps` applies persistent room/exit state.

## Units and identity

- A `SparseNode` has a stable authored `node_id`, an integer-metre `(x, y)`
  local-frame binding, and a room prototype. The identity, never the
  coordinate, is the matching authority.
  The document's node map key supplies an English slug such as `south_gate`
  or `quay`; the node's Chinese `key`（南門 or 碼頭埠）is the display name.
  Renaming the display key does not rename the node identity.
- A `SparseRoad` has a stable ordered endpoint pair, an authored compass
  octant, optional bend points, and a length: the sum of Euclidean segment
  lengths. The octant is authored because an irregular metre layout is almost
  never axis-aligned; deriving it from the raw delta would turn every cardinal
  street into a diagonal. The shipped settlements author straight segments.
- `SparseSettlementGraph` validates at construction: duplicate identity,
  duplicate coordinate (two identities binding one destination), unknown
  endpoint, self-loop, duplicate ordered road, duplicate outgoing compass
  direction, and identity/prototype table drift all raise
  `SparseGraphError` before a caller can persist anything.

Coordinates are the settlement's integer-metre local frame (`x` east, `y`
north); `z` stays the logical map/layer key. A coordinate move is a declaration
edit, not an identity change.

## Source discovery and publication

`content/maps/settlements/<map_id>.yaml` is discovered in sorted path order; a
document's `id` must equal the file stem, and its `location_ref` binds it to one
authored geographic location. That reference is the only reverse link: a
location's local map, anchor placement, frame anchor and wilderness gateway all
derive from it, so adding a map for an existing location is a source edit with
no Python registration and no reverse location list.

`world/maps/map_data.py` reads the documents and `content/maps/locations.yaml`,
validates every settlement's own declaration (one anchor room whose
`anchor_key` is the `location_ref`, authored gate/wilderness destinations, registered scene
archetypes) and the cross-document rules (no duplicate location binding, the
terrain-independent wilderness footprint/gate rules), then publishes one
immutable `SettlementSnapshot`. A rejected candidate raises `SettlementError`
and leaves the previously published snapshot exactly as it was; reading before
any publication raises `SettlementNotLoaded`. Nothing loads at import.

`SETTLEMENT_GRAPHS`, `KNOWN_GRID_MAP_KEYS`, `ANCHOR_PLACEMENT_REGISTRY`,
`LOCAL_FRAME_ANCHOR_REGISTRY`, `CITY_GATE_REGISTRY`,
`WILDERNESS_ENTRY_REGISTRY` and `GRID_NODE_SCENE_ARCHETYPES` are read-only views
over the published snapshot, so a replacement reaches every consumer that
already holds them. The composition roots (`world.maps.runtime` at startup, `sync_grid`, `sync_wilderness`,
`sync_all`) publish explicitly. The one-time conversion compared the emitted
documents against the retired Python declarations; that comparison is evidence
of preservation, not a permanent approval corpus.

Room and road counts belong to the authored settlement document. Its `roads`
list stores one entry per directed travel direction; a bidirectional street has
a reverse entry as well. Canonical map-knowledge IDs such as
`grid:capital_altoria:3050:150` encode the coordinate binding, not the sparse
slug or Chinese display key.

## Synchronization contract

`sync_grid()` plans every declared graph read-only before the first write. A
conflict therefore refuses with no room, tag, reference or cached coordinate
changed. It then applies all plans in one transaction:

1. Rooms are matched by tag `<map>:<node_id>` in category
   `sparse_node_identity`, falling back once to
   the old coordinate for rooms spawned before identity binding existed.
2. Coordinate tags are rewritten in place and every cached projection
   (`_xyz`, `_xyz_destination`, `_xymap`) is dropped. The room object, its
   occupants, `home` references and inbound object references are untouched.
3. Exits are matched by tag `<map>:<road_id>` in category
   `sparse_road_identity`, falling back to the
   legacy `(source room, English compass key)` pair. Source/destination
   relations and both coordinate tag sets are converged in place.
4. Unbound legacy settlement rooms/exits that are no longer declared are
   pruned only after convergence. Service interior doorways and wilderness
   gates are different typeclasses and are never part of this surface.
5. Authored prototypes are applied only when their fingerprint changes, so a
   second run over unchanged data performs no managed write. Plain
   `room_art` assignments are likewise compared before writing.
6. Every moved node contributes an old→new coordinate binding. The knowledge
   owner (`world/rules/map_knowledge.remap_grid_identities`) rewrites the
   affected players' stored `grid:` ids inside the same transaction, keeping
   first/last-seen ticks and merging collapsed ids by earliest/latest tick. It
   never records a new arrival. Wilderness chunk knowledge is preserved untouched.
   Map knowledge uses schema 2 (`{"schema_version": 2, "visited": {...}, "wilderness": {...}}`),
   with chunk-addressed wilderness observations and development reset cutover.
7. A failed transaction reloads every touched room/exit and resets the
   attribute caches of every knowledge record it journalled, so durable and
   process-local state both return to the pre-cutover values.
8. An unbound legacy room that would be pruned while occupants, a `HOME`
   reference or an inbound destination still point at it is refused before any
   write. Occupied rooms are never deleted and recreated.

`sync_settlement_graph(graph)` exposes the same convergence for one synthetic
or test graph and returns a `SyncReport(created, updated, deleted)`.

## Static references

Static map targets outside the settlement graph — city gates (虛境 bridges),
ghost-anchor placements, wilderness entry gates, place room joins and their authored exterior entrances,
district landmarks and grid scene-art associations — declare a qualified
identity (`QualifiedRef`: tagged domain, map scope, object id, or an explicitly
typed wilderness cell). They never store coordinates.

`world/maps/static_references.py` is the one game-side boundary that resolves
those identities against the current bindings (`settlement_node_xyz`,
`place_exterior_xyz`, `anchor_entrance_xyz`, `map_reference_index`,
`binding_signature`). Moving an authored node therefore moves every dependent
family without editing a target. The map-knowledge wire grammar (`grid:` /
`wild:`) is unchanged and is derived at the consumer boundary; no
coordinate-to-id alias table or fallback exists.

`validate_static_references()` resolves the complete declaration closure from
one binding snapshot. The startup catalog runs it as
the adoption gate before `sync_all` and `sync_grid`, and the direct sync
entrypoints run it before their first write, so an absent, wrong-domain or
duplicate target is rejected with the declaration and target named, leaving
prior persistent state and knowledge untouched. A valid target with no
materialized room keeps the existing warn-and-skip convergence behavior.

## Route adapter

`SparseSettlementGraph.route()` runs Dijkstra over the declared adjacency only;
work and allocation are bounded by node/road count, never by coordinate
span. `plan()` names each step's compass direction and spawned exit key;
`plan_between_coordinates()` resolves the two coordinate bindings first.

`commands/localized/xyzgrid.CmdGoto` uses the declared graph. Maps without a
sparse declaration (synthetic test grids, builder maps) are adapted for the
lifetime of the loaded `XYMap` by `world.maps.xymap_graph.graph_from_xymap()`, so the ASCII contrib
remains a compatibility surface for synthetic maps but never the routing
authority for a declared settlement. `SparseSettlementGraph.display_projection()`
gives the local-map adapter the same read-only node/link view without an ASCII
lattice.

## Display surface

There is no ASCII authoring source and no dense lattice. The settlement
declaration is the authored document's `nodes`/`roads` blocks; the
localized `地圖`/`map` command lists a declared settlement's nodes, metre
coordinates and outgoing compass exits, and still renders an ASCII map for a
synthetic/builder map loaded in the contrib. `sync_grid()` removes any
settlement id an older database still carries in `XYZGrid.db.map_data`; it
never deletes a room or exit for that cleanup.

Local-map payload bounds (`web/webclient/presentation/local_map/validate.py`)
carry integer metres and the client projects the payload at one uniform
physical scale; see `docs/development/metric-local-maps.md` and
`docs/development/metric-settlements.md`. The registered per-map extent gates
`grid:` identities.
