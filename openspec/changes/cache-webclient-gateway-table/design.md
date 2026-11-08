# Design

## Context

See `proposal.md` for the profiling evidence. Current code at `a0c1e0b7`:

- `web/webclient/presentation/local_map/gateways.py`
  - `_registered_gateways()` (line 19) walks `WILDERNESS_ENTRY_REGISTRY`
    (deferred import from `world.lore.wilderness_entry`), skips gates whose
    `entry.approach_cell(gate)` is `None`, and calls
    `settlement_node_xy(gate.destination, source=f"wilderness gate {entry.anchor_key}")`
    with no `index=`, so `world.maps.static_references.settlement_reference_index()`
    builds a full `ReferenceIndex` over every settlement node once per gate.
  - `_wilderness_gateway_at(x, y)` (line 44) and `_grid_gateway_at(x, y, z)`
    (line 54) call `_registered_gateways()` and scan linearly, returning the
    first match.
- Callers: `local_map/wilderness.py` lines 153 (`_grid_gateway_at`, per
  gateway step), 221 (`_wilderness_gateway_at`, per in-view neighbour, ≤8),
  258 (`_wilderness_gateway_at`, per remembered visited wild node);
  `local_map/grid.py` lines 203 and 249 (`_grid_gateway_at`);
  `area_map.py` line 912 (`_registered_gateways()` once per render, built into
  a dict — last row wins for duplicate approach cells, which this change does
  not touch) and line 995 (`_grid_gateway_at`).
- `WILDERNESS_ENTRY_REGISTRY` and `world.maps.map_data.SETTLEMENT_GRAPHS` are
  `world.maps.published.PublishedView` objects; `.source` is the immutable
  mapping of the currently published snapshot and changes identity exactly
  when a new snapshot is installed (`world.maps.runtime._install`, used by
  `adopt`, `publish`, `preview` and `rollback_adoption`). Provider bounds used
  by `approach_cell` come from the published geography
  (`world.maps.geography.current()`).
- `world.maps.published.SourceMemo` is the established memo for values derived
  from these views; `world.maps.wilderness_destination.find_gateway` already
  memoizes its gateway-cell map with it (`_GATEWAY_ENTRIES`, line 278).
- Tests patch `world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY` with a
  plain dict (`test_gateway_resolution.py::test_registered_gateways_yields_a_point_shape_entrys_own_anchor_cell`)
  and `world.maps.map_data.SETTLEMENT_GRAPHS` with plain dicts (several
  `world/maps/tests`), without publishing a new map world.
- Stored wilderness visit IDs are canonical: `world/rules/map_knowledge.py`
  stores wild visits in chunk records with canonical decimal keys and
  re-encodes them with `encode_wild`, so a visited approach cell's node ID is
  exactly `encode_wild(WILDERNESS_NAME, x, y)`.

## Goals / Non-Goals

**Goals:**

- One gateway-table build (and one settlement `ReferenceIndex` build) per
  published input set, shared by every local_map and area_map render.
- O(1) `_wilderness_gateway_at` / `_grid_gateway_at`.
- Remembered-gateway scan cost proportional to registered gateways, not to
  visited cells.
- Byte-identical payloads for identical inputs.

**Non-Goals:**

- Changing `area_map.py`, `local_map/grid.py`, `world/maps/static_references.py`
  or `world/maps/wilderness_destination.py` source.
- Caching `settlement_reference_index()` or `settlement_node_xy()` globally
  (the static-references module is deliberately uncached; see its docstring).
- Changing the last-wins dict built at `area_map.py:912`.
- Monster district freezing, coalescing publication during travel,
  `travel_plan` cost, or any wall-clock assertion.

## Decisions

### D1. Memoize with `SourceMemo` keyed on the published sources, not on `_map_world_identity()`

The table is pinned to the identity of three objects:
`WILDERNESS_ENTRY_REGISTRY.source`, `SETTLEMENT_GRAPHS.source` and
`world.maps.geography.current()` (each unwrapped only when it is a
`PublishedView`; a patched plain dict is used as-is).

Alternative considered: `functools.lru_cache` keyed on
`registry_index._map_world_identity()` (the `build_reference_index` pattern
named in the request). Rejected because (a) a test that patches the registry
or settlement graphs with a plain dict leaves the map-world identity unchanged,
so an identity-keyed cache would serve the previous table and break
`test_registered_gateways_yields_a_point_shape_entrys_own_anchor_cell`;
(b) `SourceMemo` already invalidates on every `_install` (adopt, publish,
preview, rollback), which covers the map-editor republish and runtime adopt
paths the request requires; (c) it is the idiom `world/maps` already uses for
this exact registry (`wilderness_destination._GATEWAY_ENTRIES`). The
user-visible outcome — rebuild exactly when a new map world is adopted — is the
same.

### D2. Table contract (verbatim)

In `web/webclient/presentation/local_map/gateways.py`:

```python
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from world.maps.published import PublishedView, SourceMemo

_Gateway = tuple[tuple[int, int], tuple[tuple[int, int], str], str]


@dataclass(frozen=True, slots=True)
class _GatewayTable:
    """Every registered gateway of one published input set (design D2)."""

    rows: tuple[_Gateway, ...]
    by_approach: Mapping[tuple[int, int], _Gateway]
    by_gate_room: Mapping[tuple[tuple[int, int], str], _Gateway]


_GATEWAY_TABLE = SourceMemo()


def _unwrap(view):
    return view.source if isinstance(view, PublishedView) else view


def _build_gateway_table(entries) -> _GatewayTable:
    from world.maps.static_references import (
        settlement_node_xy,
        settlement_reference_index,
    )

    index = settlement_reference_index()
    rows: list[_Gateway] = []
    by_approach: dict[tuple[int, int], _Gateway] = {}
    by_gate_room: dict[tuple[tuple[int, int], str], _Gateway] = {}
    for entry in entries.values():
        for gate in entry.gates:
            approach = entry.approach_cell(gate)
            if approach is None:
                continue
            gate_xy = settlement_node_xy(
                gate.destination,
                index=index,
                source=f"wilderness gate {entry.anchor_key}",
            )
            row = (approach, (gate_xy, gate.z_map_key), entry.anchor_key)
            rows.append(row)
            by_approach.setdefault(approach, row)
            by_gate_room.setdefault((gate_xy, gate.z_map_key), row)
    return _GatewayTable(
        rows=tuple(rows),
        by_approach=MappingProxyType(by_approach),
        by_gate_room=MappingProxyType(by_gate_room),
    )


def _gateway_table() -> _GatewayTable:
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
    from world.maps import geography
    from world.maps.map_data import SETTLEMENT_GRAPHS

    entries = _unwrap(WILDERNESS_ENTRY_REGISTRY)
    sources = (entries, _unwrap(SETTLEMENT_GRAPHS), geography.current())
    return _GATEWAY_TABLE.resolve(
        sources, None, lambda: _build_gateway_table(entries)
    )
```

Public helpers keep their names and signatures:

```python
def _registered_gateways() -> list[_Gateway]:
    return list(_gateway_table().rows)


def _wilderness_gateway_at(x: int, y: int) -> _Gateway | None:
    return _gateway_table().by_approach.get((x, y))


def _grid_gateway_at(x: int, y: int, z: str) -> _Gateway | None:
    return _gateway_table().by_gate_room.get(((x, y), z))


def _wilderness_gateways_by_approach() -> Mapping[tuple[int, int], _Gateway]:
    """First registered gateway per approach cell, in registry order (design D3)."""
    return _gateway_table().by_approach
```

Notes binding the implementation:

- The deferred `from ... import WILDERNESS_ENTRY_REGISTRY` stays inside
  `_gateway_table()` so a `patch("world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY", ...)`
  is observed. `settlement_reference_index` is imported from the module at
  call time inside `_build_gateway_table` (not bound at gateways-module import)
  so tests can count it with
  `patch("world.maps.static_references.settlement_reference_index", wraps=...)`.
- `settlement_reference_index()` reads `SETTLEMENT_GRAPHS` itself; the table's
  `SETTLEMENT_GRAPHS` source in the memo key is what makes a moved node
  rebuild the table.
- A `ReferenceError` raised by `settlement_node_xy` propagates exactly as
  today; `SourceMemo` stores nothing on a raise, so the next call retries.
- Export `_wilderness_gateways_by_approach` from
  `web/webclient/presentation/local_map/__init__.py` next to the other
  gateway helpers (import list and `__all__`).

### D3. Inverted remembered-gateway scan

New method on `_GraphBuilder` (`web/webclient/presentation/local_map/builder.py`):

```python
def remembered_among(self, node_ids: Iterable[str]) -> list[NodeVisit]:
    """Visited nodes among ``node_ids`` not yet drawn, ordered like ``remembered``."""
    candidates = [
        self.visited[node_id]
        for node_id in set(node_ids)
        if node_id in self.visited and node_id not in self._by_id
    ]
    candidates.sort(key=lambda visit: (-visit.last_seen_tick, visit.node_id))
    return candidates
```

In `_wilderness_layer` (`local_map/wilderness.py` lines 248–268) the loop
header and gateway lookup change; everything after the
`gateway is None` check stays as is:

```python
by_approach = _wilderness_gateways_by_approach()
approach_ids = {
    encode_wild(WILDERNESS_NAME, ax, ay): (ax, ay) for ax, ay in by_approach
}
gateway_candidates: list[tuple[str, int, int, str, str]] = []
for visit in builder.remembered_among(approach_ids):
    gx, gy = approach_ids[visit.node_id]
    if abs(gx - x) <= 1 and abs(gy - y) <= 1:
        continue  # still inside the drawn field of view
    _, (grid_xy, z_map_key), anchor_key = by_approach[(gx, gy)]
    gate_node = encode_grid(z_map_key, *grid_xy)
    if not disclosure.gateway_disclosed(anchor_key, gate_node):
        continue
    far_label = _gateway_far_side_label("wilderness", (gx, gy), anchor_key)
    boundary_name = _grid_room_label(grid_xy, z_map_key)
    gateway_candidates.append((visit.node_id, gx, gy, far_label, boundary_name))
```

Equivalence argument (why the payload is identical):

- `remembered(len(visited))` returns every visited node not yet drawn with a
  `grid:`/`wild:`/`room:` prefix, sorted by `(-last_seen_tick, node_id)`, and
  the old loop kept only `wild:` IDs whose decoded cell is a registered
  approach cell. `remembered_among(approach_ids)` selects exactly that subset
  (stored wild IDs are canonical — see Context) and sorts it with the same
  total key, so the candidate order is identical.
- The old per-cell lookup returned the first registered row for that cell;
  `by_approach` holds the first row per cell (D2 `setdefault`).
- Field-of-view skip, disclosure filter, `remembered_budget` truncation
  (still computed after the loop), and label-collision qualification are
  untouched.
- `encode_wild` cannot raise for a table row: `approach_cell` only returns
  cells inside the provider rectangle.

The in-view neighbour lookup at line 221 and the gateway-step lookup at line
153 keep calling `_wilderness_gateway_at` / `_grid_gateway_at` (now O(1)).
Remove `decode_node` from the wilderness module imports only if no other use
remains (it is still used at line 137, so it stays).

### D4. Tests are call counts and payload equality

- Count table builds by patching
  `web.webclient.presentation.local_map.gateways._build_gateway_table` with
  `wraps=` the original.
- Count settlement index builds by patching
  `world.maps.static_references.settlement_reference_index` with `wraps=`.
- Reset the memo between tests by assigning a fresh
  `gateways._GATEWAY_TABLE = SourceMemo()` under `patch.object`, never by
  sleeping or timing.
- Synthetic entries are `WildernessEntryPoint` values whose gates reuse
  destinations probed from the live registry (the existing
  `_city_gate_row_for(_NORTH_FACE).gate` idiom); no shipped gate count, name
  or coordinate literal is asserted.
- The exploration-independence test counts calls to
  `web.webclient.presentation.local_map.wilderness._wilderness_gateway_at`
  (the module binding the layer uses) across two renders of the same
  position with different numbers of visited ordinary cells.

## Risks / Trade-offs

- [A test patches provider bounds without publishing a new geography] → the
  table keeps the previous approach cells. Only `test_schema.py` patches
  `WILDERNESS_MAX_X/Y`, and it validates payload envelopes without gateway
  lookups; acceptable and documented here.
- [A test mutates a published registry mapping in place] → impossible for
  published snapshots (`MappingProxyType`); a test that patches with a plain
  dict and mutates it mid-test would see a stale table. No such test exists;
  grep in task 1.4 confirms.
- [Memo holds three source objects] → it holds only the current ones and
  drops them on the next publication; memory is one tuple of ~130 rows.
- [Duplicate approach cells differ between `area_map.py` (last wins) and the
  lookups (first wins)] → pre-existing behavior, preserved on both sides.

## Migration Plan

None: pre-release, in-process memo only, no persistent state. Rollback is a
revert of the implementation commit.

## Live observation (non-blocking)

After implementation, an operator may repeat the container travel from the
proposal and note step latency in the change's commit message or PR text.
This is an observation, not an acceptance gate, and no test asserts time.
