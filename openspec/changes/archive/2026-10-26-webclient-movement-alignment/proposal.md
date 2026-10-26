# Authoritative movement alignment checkpoints

## Why

The approved design at `docs/superpowers/specs/2026-10-25-webclient-incremental-sync-design.md` (ef054c73) requires this bounded slice. Collect committed semantic settlement facts and freshly align on area or instance transitions across graphical and text paths.

## What Changes

- Collect committed semantic settlement facts and freshly align on area or instance transitions across graphical and text paths.
- Deliver the exact contracts, deterministic scenarios and focused checks in design/specs/tasks within one engineer-day.
- Planning only. Implementation belongs to a subsequent explicit apply assignment.

## Capabilities

### New Capabilities

- `webclient-event-alignment`: Collect committed semantic settlement facts and freshly align on area or instance transitions across graphical and text paths.

### Modified Capabilities

- None. Existing-spec amendments owned by other named slices are listed in design.md.

## Impact

Read design.md for exact production owners, all affected caller families, verification labels and dependency contracts. No persistent schema or command syntax changes. No compatibility layers, migrations, replay history, periodic alignment, content hashes, benchmarks, profiling or latency/no-stutter claims. Every slice owns its functional tests and implementation documentation.

## Batch:

depends-on: webclient-publication-settlements

Code conflicts: Serializes dispatcher.py, ingress.py, server/conf/inputfuncs.py and movement_settlement.py with baseline/settlement. Active authored-dialogue-refresh-lifecycle owns clock/control/NPC callbacks, which remain separate; this slice must not replace their availability refresh.

Dependencies mean completed implementations, not proposal existence. The unreleased breaking wire cutover is deployed only after the complete batch; no temporary legacy wire acceptance is authorized. See `../webclient-delta-contract/design.md` for the batch matrix and approved-design traceability.
