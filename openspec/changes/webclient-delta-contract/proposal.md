# Exact-base atomic presentation deltas

## Why

The approved design at `docs/superpowers/specs/2026-10-25-webclient-incremental-sync-design.md` (ef054c73) requires this bounded slice. Replace newer-only update admission with exact-base deltas, explicit eager removals and metadata-only adoption.

## What Changes

- **BREAKING** Replace newer-only update admission with exact-base deltas, explicit eager removals and metadata-only adoption.
- Deliver the exact contracts, deterministic scenarios and focused checks in design/specs/tasks within one engineer-day.
- Planning only. Implementation belongs to a subsequent explicit apply assignment.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `webclient-oob-protocol`: exact delta shape, removals, admission and dialogue candidate coupling.

## Impact

Read design.md for exact production owners, all affected caller families, verification labels and dependency contracts. No persistent schema or command syntax changes. No compatibility layers, migrations, replay history, periodic alignment, content hashes, benchmarks, profiling or latency/no-stutter claims. Every slice owns its functional tests and implementation documentation.

## Batch:

Code conflicts: Serializes protocol.py, protocol/{constants,core,envelope,store}.js, coordinator.py and all update fixture producers with baseline/codec/assembly/recovery/adoption. Active authored-dialogue-reading-server edits constants.js; merge that action allowlist additively without changing dialogue schema/budgets.

Dependencies mean completed implementations, not proposal existence. The unreleased breaking wire cutover is deployed only after the complete batch; no temporary legacy wire acceptance is authorized. See `../webclient-delta-contract/design.md` for the batch matrix and approved-design traceability.
