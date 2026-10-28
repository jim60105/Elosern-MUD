# Proposal

## Why

Install and run the independent local editor service and browser workspace with bounded authenticated domain APIs. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md`, its companion `2026-10-26-map-editor-frontend-requirements.md` and the approved frontend specialist deliverable `2026-10-26-map-editor-frontend-design.md`, which amends both where it says so. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Install and run the independent local editor service and browser workspace with bounded authenticated domain APIs.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-editor-service`: Install and run the independent local editor service and browser workspace with bounded authenticated domain APIs.

### Modified Capabilities

None.

## Impact

new tools/map-editor/{pyproject.toml,uv.lock,elosern_map_editor,frontend}; packages/map-view local dependency; frontend pnpm lock; editor import-boundary check for the allowlisted game tokens/fonts/ui-scale; launch/docs/development/map-editor.md; tests/test_map_editor_service.py

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. Visual direction, states and copy follow the approved frontend design and the `docs/design/map-editor/` prototype; fidelity is human-reviewed per scenario in `docs/design/map-editor-review.md`, and tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-interior-runtime-cutover
depends-on: map-reference-context-export
depends-on: map-view-shared-foundations

code-conflicts: Serializes root/package frontend locks with shared foundations. No game GM account or app route is reused; game NPC/publication proposals do not own this independent shell.
