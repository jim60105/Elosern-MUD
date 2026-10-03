## Why

Continuity should work without meeting an NPC, while delivery and knowledge remain deterministic. This letter-only step implements one boundary of the approved courier workflow.

## What Changes

- Implement fixed one-hour durable letter scheduling and atomic delivery settlement.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `correspondence-delivery`: Implement fixed one-hour durable letter scheduling and atomic delivery settlement.

### Modified Capabilities
- `world-clock`: deltas for the boundaries described below.
- `settlement-stage-order`: deltas for the boundaries described below.

## Impact

`world/narrative/correspondence`, `world/rules/clock.py`, `server startup`, `clock stage contracts`.

Main-spec reconciliation: world-clock and settlement-stage-order pin an exact stage list and declare callback surfaces. Explicitly insert correspondence_delivery and include table/cache rollback; retain existing ordering and one-day bounds. skip-safety-gate currently rejects outright, so no shortening mechanism is added.

## Batch:

depends-on: yohanna-memory-dialogue

Workstream: W2. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: projection progress/linkage with narrative-event-commit, narrative-owner-memory, correspondence-memory-projection, narrative-story-threads.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
