# Proposal

## Why

Implement service-owned single-document autosave, overwrite guards and manual-segment undo/redo with real interior-layout operations. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md`, its companion `2026-10-26-map-editor-frontend-requirements.md` and the approved frontend specialist deliverable `2026-10-26-map-editor-frontend-design.md`, which amends both where it says so. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Implement service-owned single-document autosave, overwrite guards and manual-segment undo/redo with real interior-layout operations.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-editor-persistence`: Implement service-owned single-document autosave, overwrite guards and manual-segment undo/redo with real interior-layout operations.

### Modified Capabilities

None.

## Impact

elosern_map_editor command executor/file writer/history/session endpoints; frontend draft/persistence state; interior layout handler; content/map-editor-layouts; docs/development/map-editor.md

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. Visual direction, states and copy follow the approved frontend design and the `docs/design/map-editor/` prototype; fidelity is human-reviewed per scenario in `docs/design/map-editor-review.md`, and tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-editor-standalone-service

code-conflicts: Service command/history modules are shared with file-following and domain handlers; sequence this prerequisite, then keep domain commands in separate modules. One writer implementation only.
