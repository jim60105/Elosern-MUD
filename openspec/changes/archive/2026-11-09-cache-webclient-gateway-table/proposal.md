# Proposal

## Why

Wilderness travel stalls about 6.5 s per step: py-spy inside the running
container attributes ~93% of main-thread time during a real multi-step travel
to `local_map_presenter → _wilderness_layer → _wilderness_gateway_at →
_registered_gateways → settlement_node_xy → settlement_reference_index →
ReferenceIndex.build` (and ~2% to the same chain under `area_map_presenter`).
`_registered_gateways()` rebuilds a settlement `ReferenceIndex` once per
registered gate on every call (measured ≈48 ms per call with 127 gates), and
the wilderness layer calls it once per in-view neighbour and once per
remembered visited wild node, so each render costs O(visits × gates ×
settlement nodes) and grows with every explored cell.

## What Changes

- `web/webclient/presentation/local_map/gateways.py`: the registered-gateway
  rows are built once per published input set (wilderness entry registry,
  settlement graphs, geography snapshot) through the existing
  `world.maps.published.SourceMemo` idiom, with ONE settlement
  `ReferenceIndex` passed as `index=` to `settlement_node_xy`. The cached table
  also carries first-match lookup maps `approach_cell → gateway` and
  `(grid_xy, z_map_key) → gateway`, so `_wilderness_gateway_at` and
  `_grid_gateway_at` become dictionary lookups. `_registered_gateways()` keeps
  its signature, registry ordering and skip-on-`None` behavior, and returns a
  fresh list each call.
- `web/webclient/presentation/local_map/wilderness.py`: the remembered-gateway
  scan iterates only visited nodes whose canonical `wild:` ID is a registered
  approach cell (new `_GraphBuilder.remembered_among`), instead of decoding and
  probing every remembered visit. Ordering, field-of-view skip, disclosure
  filter, filter-then-bound budget and label-collision qualification are
  unchanged; payloads are identical for identical inputs.
- `web/webclient/presentation/area_map.py` and `local_map/grid.py` need no
  source edit: they already call `_registered_gateways()` / `_grid_gateway_at`
  and inherit the cached table.
- Regression tests by call counts only (no wall-clock assertions): one table
  build and one settlement `ReferenceIndex` build per published input set,
  rebuild after a new input set is published, first-match preserved for
  duplicate cells, and the per-render gateway lookup count in the wilderness
  layer independent of how many cells the character has visited.

Out of scope: freezing monster population outside the player's district,
coalescing presentation publication during multi-step travel, `travel_plan`
routing cost, and any other `settlement_node_xy` caller outside the two map
presenters.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-local-map`: two ADDED requirements — the registered-gateway table
  is built once per published map world and invalidated on a new publication,
  and the wilderness remembered-boundary scan does not probe every visited cell.

## Impact

- Code: `web/webclient/presentation/local_map/gateways.py`,
  `web/webclient/presentation/local_map/wilderness.py`,
  `web/webclient/presentation/local_map/builder.py`.
- Tests: new methods in the existing modules
  `web/webclient/presentation/tests/test_local_map/test_gateway_resolution.py`
  and `web/webclient/presentation/tests/test_local_map/test_wilderness.py`
  (no new test module, so `.github/evennia-shards.json` is untouched).
- Dependencies, persistent state, wire payloads, browser code: none.
- Human-reviewed: nothing. Every requirement is established by call-count and
  payload-equality tests; travel latency in the live container is recorded as
  a non-blocking observation only.

## Batch:

single change; no other change is in flight under `openspec/changes/`.
