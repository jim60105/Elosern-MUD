# Proposal

## Why

Implement complete cross-layer entrance editing, navigation and reference-safe deletion from a single owning relationship. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Implement complete cross-layer entrance editing, navigation and reference-safe deletion from a single owning relationship.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-editor-relationships`: Implement complete cross-layer entrance editing, navigation and reference-safe deletion from a single owning relationship.

### Modified Capabilities

None.

## Impact

frontend qualified selector/entrance inspectors/cross-map navigation; service settlement/interior relationship handlers; existing core reference rules; no new persistent game writer

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-editor-continent-tools
depends-on: map-editor-settlement-tools
depends-on: map-editor-interior-tools

code-conflicts: Relationship handlers extend settlement/interior domain modules after those slices; serialize these edits and shared selector/navigation modules. No mirrored reverse owner or second deletion validator.
