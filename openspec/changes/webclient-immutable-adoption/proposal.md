# Immutable reference-preserving browser adoption

## Why

The approved design at `docs/superpowers/specs/2026-10-25-webclient-incremental-sync-design.md` (ef054c73) requires this bounded slice. Publish immutable committed views without unconditional complete-state cloning and preserve valid local UI state.

## What Changes

- Publish immutable committed views without unconditional complete-state cloning and preserve valid local UI state.
- Deliver the exact contracts, deterministic scenarios and focused checks in design/specs/tasks within one engineer-day.
- Planning only. Implementation belongs to a subsequent explicit apply assignment.

## Capabilities

### New Capabilities

- `webclient-immutable-presentation`: Publish immutable committed views without unconditional complete-state cloning and preserve valid local UI state.

### Modified Capabilities

- None. Existing-spec amendments owned by other named slices are listed in design.md.

## Impact

Read design.md for exact production owners, all affected caller families, verification labels and dependency contracts. No persistent schema or command syntax changes. No compatibility layers, migrations, replay history, periodic alignment, content hashes, benchmarks, profiling or latency/no-stutter claims. Every slice owns its functional tests and implementation documentation.

## Batch:

depends-on: webclient-sync-recovery

Code conflicts: Serializes protocol/store.js, elosern.js, stores/elosern/{view,transport}.js and frame-resolver reads with recovery/assembly. Active authored-dialogue-reading-client shares elosern composition/transport; unread-notices shares local UI consumers. Freeze committed data without freezing their client-local queues.

Dependencies mean completed implementations, not proposal existence. The unreleased breaking wire cutover is deployed only after the complete batch; no temporary legacy wire acceptance is authorized. See `../webclient-delta-contract/design.md` for the batch matrix and approved-design traceability.
