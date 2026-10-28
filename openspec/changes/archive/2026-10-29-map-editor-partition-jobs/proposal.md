# Proposal

## Why

Run explicit partition jobs outside the request loop with cancellation, mutation exclusion and fingerprint-guarded output publication. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md`, its companion `2026-10-26-map-editor-frontend-requirements.md` and the approved frontend specialist deliverable `2026-10-26-map-editor-frontend-design.md`, which amends both where it says so. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Run explicit partition jobs outside the request loop with cancellation, mutation exclusion and fingerprint-guarded output publication.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-editor-generation`: Run explicit partition jobs outside the request loop with cancellation, mutation exclusion and fingerprint-guarded output publication.

### Modified Capabilities

None.

## Impact

editor background job runner/status routes and partition frontend controls; editor uv generation extra; existing session mutation guard and artifact writer

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. Visual direction, states and copy follow the approved frontend design and the `docs/design/map-editor/` prototype; fidelity is human-reviewed per scenario in `docs/design/map-editor-review.md`, and tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-partition-core-generation
depends-on: map-editor-entrance-tools

code-conflicts: Extends the same state machine/writer from workspace slices; serialize those files rather than add a job-specific mutation authority. Partition artifact remains generated/read-only.
