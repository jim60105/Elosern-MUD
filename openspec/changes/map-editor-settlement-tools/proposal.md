# Proposal

## Why

Implement complete settlement creation, node/prototype editing, directed roads and physical route inspection. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md`, its companion `2026-10-26-map-editor-frontend-requirements.md` and the approved frontend specialist deliverable `2026-10-26-map-editor-frontend-design.md`, which amends both where it says so. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Implement complete settlement creation, node/prototype editing, directed roads and physical route inspection.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-editor-settlement-graphs`: Implement complete settlement creation, node/prototype editing, directed roads and physical route inspection.

### Modified Capabilities

None.

## Impact

frontend settlement tools/prototype and road inspectors; service settlement command handlers; shared core graph preview/route endpoint

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. Visual direction, states and copy follow the approved frontend design and the `docs/design/map-editor/` prototype; fidelity is human-reviewed per scenario in `docs/design/map-editor-review.md`, and tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-editor-interaction-shell

code-conflicts: Settlement command module is separate from geography/interior modules, but footprint and cross-layer relationships use the same serialized owning-document writer. Domain slices may proceed after the shared shell without duplicated interaction state.
