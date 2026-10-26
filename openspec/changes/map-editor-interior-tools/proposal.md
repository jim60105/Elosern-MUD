# Proposal

## Why

Implement coordinate-free permanent interior room/connection editing and separately persisted layout controls. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Implement coordinate-free permanent interior room/connection editing and separately persisted layout controls.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-editor-interiors`: Implement coordinate-free permanent interior room/connection editing and separately persisted layout controls.

### Modified Capabilities

None.

## Impact

frontend interior room/connection/layout tools; service interior handlers; content/maps/interiors and content/map-editor-layouts; existing move_interior_layout route

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-editor-interaction-shell

code-conflicts: Reuses the initial layout handler rather than replacing it. Serialize shared schema/selector components through interaction shell; no source conflict with separately owned settlement handler.
