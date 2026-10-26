# Isolated content-aware session publication

## Why

The approved design at `docs/superpowers/specs/2026-10-25-webclient-incremental-sync-design.md` (ef054c73) requires this bounded slice. Compare validated candidates against the last successfully published per-session baseline and migrate every publisher to one coordinator.

## What Changes

- **BREAKING** Compare validated candidates against the last successfully published per-session baseline and migrate every publisher to one coordinator.
- Deliver the exact contracts, deterministic scenarios and focused checks in design/specs/tasks within one engineer-day.
- Planning only. Implementation belongs to a subsequent explicit apply assignment.

## Capabilities

### New Capabilities

- `webclient-incremental-publication`: Compare validated candidates against the last successfully published per-session baseline and migrate every publisher to one coordinator.

### Modified Capabilities

- `webclient-action-dispatch`: content-aware completion and unchanged revision behavior.
- `webclient-oob-protocol`: candidate-based post-text settlement refresh.

## Impact

Read design.md for exact production owners, all affected caller families, verification labels and dependency contracts. No persistent schema or command syntax changes. No compatibility layers, migrations, replay history, periodic alignment, content hashes, benchmarks, profiling or latency/no-stutter claims. Every slice owns its functional tests and implementation documentation.

## Batch:

depends-on: webclient-delta-contract

Code conflicts: Serializes coordinator.py, dispatcher.py, ingress.py, push.py, dialogue_push.py, exploration_actions.py and test manifests with movement/settlement. Active authored-dialogue-availability, reading-server and unread-notices share dialogue_push.py/exploration_actions.py; retain their domain refresh and receipt authority.

Dependencies mean completed implementations, not proposal existence. The unreleased breaking wire cutover is deployed only after the complete batch; no temporary legacy wire acceptance is authorized. See `../webclient-delta-contract/design.md` for the batch matrix and approved-design traceability.
