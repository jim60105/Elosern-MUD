# Proposal: wilderness-anchor-footprint-local-map

## Why

The deterministic half of Model A (change `wilderness-anchor-footprint`) makes the world honest:
anchors own wilderness footprints, gates live on faces. The webclient local-map presenter
(`web/webclient/presentation/local_map.py`) still speaks the v1 world: it labels and identifies
gate nodes through the entry's single `wilderness_xy` and derives a gate's slot direction by
parsing the gate exit's key/aliases (falling back to `"n"`). Once the registry gains a footprint
and a second gate, that presentation layer would keep drawing the old phantom — a walkable wild
cell over the city, one gate labelled at the anchor centroid, and two identically-keyed `荒野`
gate exits silently deduplicated to one candidate on the grid layer. This change is the
presentation half of the reported bug: the map must render the boundary the provider enforces and
both gates the registry declares.

## What Changes

- The wilderness layer stops presenting footprint cells as walkable ground: provider-invalid
  directions (out of bounds OR footprint) render neither node nor walkable edge — the existing
  out-of-bounds presentation becomes the boundary presentation.
- Gate nodes become per-gate on both sides: the approach-cell side renders the gate room's
  `grid:` node; the gate-room side renders its own gate's approach cell's `wild:` node.
- **Grid-side node identity is re-derived from data, not strings**: candidate identity and label
  come from the provisioned exit's `db.gate_direction` → registry → `approach_cell(gate)`; slot
  direction comes from the exit connecting the gate room. Key/alias parsing (`_gate_direction`)
  is deleted — it cannot distinguish the two `荒野`-keyed gates.
- Browser seed switches from `entry.wilderness_xy` (deleted in v2) to a gate approach cell.
- No payload schema change: same version-1 fields, same bounds, same validators.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-local-map`: wilderness-layer payload never renders a footprint cell as walkable;
  per-gate matched node pairs on both sides; grid-side gate identity/label/slot derived from
  registry geometry and the exit object, never from key aliases.

## Impact

- Affected code: `web/webclient/presentation/local_map.py` (`_gate_direction`,
  `_grid_gate_candidates`, wilderness adjacency/label paths),
  `web/webclient/presentation/tests/test_local_map.py`, `web/tests/browser/seed.py`, and the
  local-map browser test class; `.github/evennia-shards.json` only if a test module is added
  (expected: none).
- **Depends on:** `wilderness-anchor-footprint` (registry v2 helpers, provisioned
  `db.gate_direction`, resolver per-gate behavior). Serialize strictly after it.
- **Blocks:** `webclient-map-scale-legend` (same file, same capability — must serialize after
  this change).
- No player-command surface change; no new dependencies.
