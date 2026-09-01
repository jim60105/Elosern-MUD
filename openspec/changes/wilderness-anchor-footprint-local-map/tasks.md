# Tasks: wilderness-anchor-footprint-local-map

## 1. Presenter rework (web/webclient)

- [x] 1.1 `web/webclient/presentation/local_map.py`: delete key/alias-based `_gate_direction`
      inference; derive grid-side gate candidate identity + label from the exit's
      `db.gate_direction` → registry `approach_cell(gate)` → `encode_wild(approach)` + region
      display name; slot direction = the connecting exit's direction (design D2).
- [x] 1.2 Verify (do not special-case) that wilderness adjacency emits no node/edge for
      provider-invalid directions — footprint cells included — and that gateway directions
      render the resolved `grid:` node per gate on both sides.

## 2. Tests

- [x] 2.1 Extend `web/webclient/presentation/tests/test_local_map.py`: footprint never appears
      as a walkable `wild:` node; both gates render independently on both sides; gate identity
      survives identical `荒野` keys and rewritten aliases (each gate room shows its OWN
      approach cell); pinning test per gate (activation vs actual arrival); crowded gate-room
      slot/capacity behavior with two gates.
- [x] 2.2 `web/tests/browser/seed.py`: replace `entry.wilderness_xy` with a gate approach cell
      (north gate `(60, 103)`); update the local-map browser test class to assert the footprint
      is absent and per-gate nodes render (full managed browser suite is CI-owned; run the one
      class locally).
- [x] 2.3 Audit Vitest fixtures/stories that pin gate-node labels or the legend/state list for
      now-impossible single-gate payloads; `npm test` green.

## 3. Traceability + gates

- [x] 3.1 Annotate requirement-owning tests with `covers_requirement` literal IDs from
      `uv run --locked python -m tools.spec_traceability list`; run `check` until clean.
      Register any new test module in exactly one shard of `.github/evennia-shards.json`
      (expected: none).
- [x] 3.2 Focused runs green: `web.webclient` presentation tests; no player-command surface
      change expected (confirm `tests/test_command_docs.py` untouched).
