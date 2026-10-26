# Combat and completed skip alignment

## Why

The approved design at `docs/superpowers/specs/2026-10-25-webclient-incremental-sync-design.md` (ef054c73) requires this bounded slice. Use terminal combat and completed rest, sleep and explicit skip facts to replace settlement deltas with fresh full alignment.

## What Changes

- Use terminal combat and completed rest, sleep and explicit skip facts to replace settlement deltas with fresh full alignment.
- Deliver the exact contracts, deterministic scenarios and focused checks in design/specs/tasks within one engineer-day.
- Planning only. Implementation belongs to a subsequent explicit apply assignment.

## Capabilities

### New Capabilities

- `webclient-settlement-alignment`: Use terminal combat and completed rest, sleep and explicit skip facts to replace settlement deltas with fresh full alignment.

### Modified Capabilities

- None. Existing-spec amendments owned by other named slices are listed in design.md.

## Impact

Read design.md for exact production owners, all affected caller families, verification labels and dependency contracts. No persistent schema or command syntax changes. No compatibility layers, migrations, replay history, periodic alignment, content hashes, benchmarks, profiling or latency/no-stutter claims. Every slice owns its functional tests and implementation documentation.

## Batch:

depends-on: webclient-movement-alignment

Code conflicts: Serializes settlement fact hooks, combat_session/settlement.py, time_skip.py, sleep_control.py, ingress.py and dispatcher.py with movement/baseline. Active authored-dialogue-refresh-lifecycle touches clock.py, which this slice reads and does not change; preserve its on-commit availability publications.

Dependencies mean completed implementations, not proposal existence. The unreleased breaking wire cutover is deployed only after the complete batch; no temporary legacy wire acceptance is authorized. See `../webclient-delta-contract/design.md` for the batch matrix and approved-design traceability.
