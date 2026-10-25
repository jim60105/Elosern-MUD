# Atomic general publication assembly

## Why

The approved design at `docs/superpowers/specs/2026-10-25-webclient-incremental-sync-design.md` (ef054c73) requires this bounded slice. Route and assemble bounded general parts, validate the complete logical state and adopt once with explicit teardown.

## What Changes

- **BREAKING** Route and assemble bounded general parts, validate the complete logical state and adopt once with explicit teardown.
- Deliver the exact contracts, deterministic scenarios and focused checks in design/specs/tasks within one engineer-day.
- Planning only. Implementation belongs to a subsequent explicit apply assignment.

## Capabilities

### New Capabilities

- `webclient-publication-assembly`: Route and assemble bounded general parts, validate the complete logical state and adopt once with explicit teardown.

### Modified Capabilities

- None. Existing-spec amendments owned by other named slices are listed in design.md.

## Impact

Read design.md for exact production owners, all affected caller families, verification labels and dependency contracts. No persistent schema or command syntax changes. No compatibility layers, migrations, replay history, periodic alignment, content hashes, benchmarks, profiling or latency/no-stutter claims. Every slice owns its functional tests and implementation documentation.

## Batch:

depends-on: webclient-publication-codec

Code conflicts: Serializes protocol store/envelope/constants, app transport and fixtures with recovery/adoption. Active authored-dialogue-reading-client shares stores/elosern/transport.js only if integration touches that file; preserve its completion queue.

Dependencies mean completed implementations, not proposal existence. The unreleased breaking wire cutover is deployed only after the complete batch; no temporary legacy wire acceptance is authorized. See `../webclient-delta-contract/design.md` for the batch matrix and approved-design traceability.
