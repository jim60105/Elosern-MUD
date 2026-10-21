# Sparse settlement graphs

This page records the unit and ownership contract introduced by
`implement-sparse-settlement-graphs` (world-map-scale design §11). It is the
reference for changing settlement maps, route finding, or the grid bootstrap
before the metric-coordinate cutover (`activate-metric-settlements`) lands.

## Ownership

| Concern | Owner |
| --- | --- |
| Sparse nodes, explicit roads, validation, route planning | `world/maps/sparse_graph.py` |
| Settlement identity tables (`NODE_IDS`, `ROADS`) and rooms' prototypes | `world/maps/altoria_capital.py`, `world/maps/village_ciaran.py` |
| Shared assembly (`SETTLEMENT_GRAPHS`, `KNOWN_GRID_MAP_KEYS`) | `world/maps/map_data.py` |
| Persistent room/exit convergence | `world/maps/bootstrap.py::sync_grid` |
| Stable room identity attribute | `typeclasses/rooms.py::GridRoom.sparse_node_id` |
| Grid/anchor map knowledge bounds | `world/rules/map_knowledge.py` |
| Player `前往`/`goto` routing | `commands/localized/xyzgrid.py` |

Lore and quest modules read the declarations; they never write a graph. Only
`world/maps` applies persistent room/exit state.

## Units and identity

- A `SparseNode` has a stable authored `node_id`, an integer `(x, y)` binding,
  and a room prototype. The identity, never the coordinate, is the matching
  authority.
- A `SparseRoad` has a stable ordered endpoint pair, optional bend points, and
  a physical length: the sum of Euclidean segment lengths. Untouched segments
  are straight, exactly as the current two settlements are authored.
- `SparseSettlementGraph` validates at construction: duplicate identity,
  duplicate coordinate (two identities binding one destination), unknown
  endpoint, self-loop, duplicate ordered road, duplicate outgoing compass
  direction, and identity/prototype table drift all raise
  `SparseGraphError` before a caller can persist anything.

The current coordinates keep their existing integer settlement scale. The
metric-coordinate change rewrites the same identity tables; nothing in this
contract assumes a meter lattice, so a coordinate move is a declaration edit,
not an identity change.

## Synchronization contract

`sync_grid()` plans every declared graph read-only before the first write. A
conflict therefore refuses with no room, tag, reference or cached coordinate
changed. It then applies all plans in one transaction:

1. Rooms are matched by tag `sparse_node_<map>:<node_id>`, falling back once to
   the old coordinate for rooms spawned before identity binding existed.
2. Coordinate tags are rewritten in place and every cached projection
   (`_xyz`, `_xyz_destination`, `_xymap`) is dropped. The room object, its
   occupants, `home` references and inbound object references are untouched.
3. Exits are matched by tag `sparse_road_<map>:<road_id>`, falling back to the
   legacy `(source room, English compass key)` pair. Source/destination
   relations and both coordinate tag sets are converged in place.
4. Unbound legacy settlement rooms/exits that are no longer declared are
   pruned only after convergence. Service interior doorways and wilderness
   gates are different typeclasses and are never part of this surface.
5. Authored prototypes are applied only when their fingerprint changes, so a
   second run over unchanged data performs no managed write. Plain
   `room_art` assignments are likewise compared before writing.

`sync_settlement_graph(graph)` exposes the same convergence for one synthetic
or test graph and returns a `SyncReport(created, updated, deleted)`.

## Route adapter

`SparseSettlementGraph.route()` runs Dijkstra over the declared adjacency only
— work and allocation are bounded by node/road count, never by coordinate
span. `plan()` names each step's compass direction and spawned exit key;
`plan_between_coordinates()` resolves the two coordinate bindings first.

`commands/localized/xyzgrid.CmdGoto` uses the declared graph. Maps without a
sparse declaration (synthetic test grids, builder maps) are adapted for the
lifetime of the loaded `XYMap` by `graph_from_xymap()`, so the ASCII contrib
remains a display/compatibility surface but never the routing authority for a
declared settlement.

## Transitional dense surface

`XYMAP_DATA_LIST` and the ASCII `MAPSTR` remain registered with the `XYZGrid`
script **only for display**: the localized `地圖`/`map` command, the
`evennia xyzgrid` CLI, the contrib's room appearance hook, and synthetic test
maps. `sync_grid()` stores that data without calling `reload()` or `spawn()`;
it never parses ASCII. The metric-coordinate cutover removes the ASCII source
and this display path together.

Local-map payload bounds (`web/webclient/presentation/local_map/validate.py`)
are intentionally unchanged here: the shipped coordinates still fit the
existing protocol window, and the viewport/projection contract is owned by
`project-metric-local-maps`. Do not silently widen the protocol in this change.
