## Why

NPC dialogue currently loses long-lived shared experience when its bounded chat history is trimmed. This bounded step establishes the next real prerequisite for the Yohanna memory acceptance chain.

## What Changes

- Persist selected encounter facts and replayable projection work at gameplay commit boundaries.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `narrative-events`: Persist selected encounter facts and replayable projection work at gameplay commit boundaries.

### Modified Capabilities
None.

## Impact

`world/narrative/events`, `world/rules/action`, `world/rules/combat_session/rounds.py`, `world/rules/combat_session/settlement.py`, `server/conf`, `Django app registration`.

Main-spec reconciliation: event-log is a transient committed DTO, not a durable source. Add narrative-events without changing event-log or converting gameplay to event sourcing.

## Batch:

depends-on: narrative-subsystem-ownership

Workstream: W1. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: projection progress/linkage with narrative-owner-memory, correspondence-delivery, correspondence-memory-projection, narrative-story-threads.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
