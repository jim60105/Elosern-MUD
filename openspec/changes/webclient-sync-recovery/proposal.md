# Bounded complete synchronization recovery

## Why

The approved design at `docs/superpowers/specs/2026-10-25-webclient-incremental-sync-design.md` (ef054c73) requires this bounded slice. Lock obsolete views and coalesce exact-base, validation, assembly and action-result recovery without automatic retry loops.

## What Changes

- **BREAKING** Lock obsolete views and coalesce exact-base, validation, assembly and action-result recovery without automatic retry loops.
- Deliver the exact contracts, deterministic scenarios and focused checks in design/specs/tasks within one engineer-day.
- Planning only. Implementation belongs to a subsequent explicit apply assignment.

## Capabilities

### New Capabilities

- `webclient-sync-recovery`: Lock obsolete views and coalesce exact-base, validation, assembly and action-result recovery without automatic retry loops.

### Modified Capabilities

- `webclient-oob-protocol`: bounded whole-presentation repair and graphical locks.

## Impact

Read design.md for exact production owners, all affected caller families, verification labels and dependency contracts. No persistent schema or command syntax changes. No compatibility layers, migrations, replay history, periodic alignment, content hashes, benchmarks, profiling or latency/no-stutter claims. Every slice owns its functional tests and implementation documentation.

## Batch:

depends-on: webclient-publication-assembly

Code conflicts: Serializes protocol/store.js, app bridge.js, transport.js, stores/elosern/transport.js and use-resync.js with assembly/adoption. Active authored-dialogue-reading-client owns reading callbacks in the same transport store, requiring serial integration.

Dependencies mean completed implementations, not proposal existence. The unreleased breaking wire cutover is deployed only after the complete batch; no temporary legacy wire acceptance is authorized. See `../webclient-delta-contract/design.md` for the batch matrix and approved-design traceability.
