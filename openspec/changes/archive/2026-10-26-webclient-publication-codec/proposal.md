# Bounded general publication encoding

## Why

The approved design at `docs/superpowers/specs/2026-10-25-webclient-incremental-sync-design.md` (ef054c73) requires this bounded slice. Prevalidate intact or byte-fragmented snapshots and deltas without changing generic or scoped map limits.

## What Changes

- **BREAKING** Prevalidate intact or byte-fragmented snapshots and deltas without changing generic or scoped map limits.
- Deliver the exact contracts, deterministic scenarios and focused checks in design/specs/tasks within one engineer-day.
- Planning only. Implementation belongs to a subsequent explicit apply assignment.

## Capabilities

### New Capabilities

- `webclient-publication-delivery`: Prevalidate intact or byte-fragmented snapshots and deltas without changing generic or scoped map limits.

### Modified Capabilities

- `webclient-oob-protocol`: general part command and distinct frame/logical bounds.

## Impact

Read design.md for exact production owners, all affected caller families, verification labels and dependency contracts. No persistent schema or command syntax changes. No compatibility layers, migrations, replay history, periodic alignment, content hashes, benchmarks, profiling or latency/no-stutter claims. Every slice owns its functional tests and implementation documentation.

## Batch:

depends-on: webclient-publication-baseline

Code conflicts: Serializes coordinator.py, protocol.py and protocol constants with delta/baseline/assembly. No dialogue domain ownership; preserve available-dialogue scoped allowance.

Dependencies mean completed implementations, not proposal existence. The unreleased breaking wire cutover is deployed only after the complete batch; no temporary legacy wire acceptance is authorized. See `../webclient-delta-contract/design.md` for the batch matrix and approved-design traceability.
