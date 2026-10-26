# Real incremental synchronization functional smoke

## Why

The approved design at `docs/superpowers/specs/2026-10-25-webclient-incremental-sync-design.md` (ef054c73) requires this bounded slice. Exercise the integrated production socket and browser paths for deltas, checkpoints, oversized delivery and bounded recovery.

## What Changes

- Exercise the integrated production socket and browser paths for deltas, checkpoints, oversized delivery and bounded recovery.
- Deliver the exact contracts, deterministic scenarios and focused checks in design/specs/tasks within one engineer-day.
- Planning only. Implementation belongs to a subsequent explicit apply assignment.

## Capabilities

### New Capabilities

- `webclient-incremental-sync-verification`: Exercise the integrated production socket and browser paths for deltas, checkpoints, oversized delivery and bounded recovery.

### Modified Capabilities

- None. Existing-spec amendments owned by other named slices are listed in design.md.

## Impact

Read design.md for exact production owners, all affected caller families, verification labels and dependency contracts. No persistent schema or command syntax changes. No compatibility layers, migrations, replay history, periodic alignment, content hashes, benchmarks, profiling or latency/no-stutter claims. Every slice owns its functional tests and implementation documentation.

## Batch:

depends-on: webclient-settlement-alignment
depends-on: webclient-immutable-adoption

Code conflicts: Runs after every batch runtime change. Shared browser/Python shard and traceability manifests require one integration owner; active dialogue test additions serialize these manifests. Content-only dialogue YAML/generated-package edits have no direct source conflict.

Dependencies mean completed implementations, not proposal existence. The unreleased breaking wire cutover is deployed only after the complete batch; no temporary legacy wire acceptance is authorized. See `../webclient-delta-contract/design.md` for the batch matrix and approved-design traceability.
