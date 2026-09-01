# Design: wilderness-anchor-footprint-local-map

## Context

Upstream change `wilderness-anchor-footprint` ships registry v2: `footprint_cells`,
`anchor_cell`, `approach_cell(gate)`, provider-invalid footprints, per-gate provisioned exits
tagged `db.anchor_key` + `db.gate_direction` (all keyed `荒野`). This change moves the webclient
presenter onto that ground truth. Presentation only — the presenter stays read-only.

## Decisions

### D1 — Boundary falls out of resolver honesty

The wilderness layer already omits directions whose neighbor does not resolve. With
`wilderness_neighbor` made provider-validity-aware upstream, footprint cells simply stop
appearing; no new "wall" concept or legend entry is introduced (absent ground is the map's
established "cannot go there" language, identical to today's outer edge).

### D2 — Grid-side gate identity from objects, not strings

`_grid_gate_candidates` today dedupes candidates by `encode_wild(entry.wilderness_xy)` and
`_gate_direction` infers the slot direction from the gate exit's key/aliases with a `"n"`
fallback. Both break under two `荒野`-keyed gates. Replacement chain, purely data-driven:

1. Candidate gate exit carries `db.anchor_key` + `db.gate_direction` (guaranteed usable by the
   upstream sync requirement).
2. `entry = WILDERNESS_ENTRY_REGISTRY[db.anchor_key]`, `gate = entry.gate_for(db.gate_direction)`
   → `approach_cell(gate)` → `encode_wild(approach)` for identity and the `wild:` label
   (`WILDERNESS_REGION_REGISTRY[region_for_coordinates(*approach)].display_name_zh`).
3. Slot direction = the direction of the exit object connecting the gate room (the candidate
   exit itself), not a parse of its key/aliases.

Key/alias parsing is deleted, not deprecated: after the cutover nothing may depend on aliases as
identity (the upstream sync requirement fixes the alias policy as display-only).

### D3 — Per-gate rendering reuses the existing per-direction path

Old code had exactly one hardcoded gate; the delta scenarios ("Both gates of one anchor render
independently on both sides", crowded-slot/capacity pins) all exercise the existing per-direction
gateway branch twice with different (approach, direction, gate-room) triples. Expected presenter
delta is small: label/identity sources (D2) plus tests. If a footprint-adjacent cell would render
a remembered node inside the footprint, provider invalidity (upstream) already removed it from
the known-adjacency set — verify, don't special-case.

## Risks / Trade-offs

- Vitest/browser fixtures pinning v1 labels/coordinates (`web/tests/browser/seed.py` uses
  `entry.wilderness_xy`, which no longer exists) fail loudly at type/attribute level — desired.
- The grid-layer label changes from anchor-centroid region label to per-approach-cell region
  label; for the shipped capital both resolve to `western_hills_valleys`, so visible text is
  unchanged today.

## Migration Plan

No persisted presentation state exists. Revert = revert commits. Browser seed and Storybook
fixtures updated in the same change; no compatibility branch for v1 registry payloads.
