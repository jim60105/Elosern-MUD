## Why

NPC dialogue currently loses long-lived shared experience when its bounded chat history is trimmed. This bounded step establishes the next real prerequisite for the Yohanna memory acceptance chain.

## What Changes

- Persist owner cognition with immutable provenance and recoverable revisions.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `narrative-memory`: Persist owner cognition with immutable provenance and recoverable revisions.

### Modified Capabilities
None.

## Impact

`world/narrative/memory`, `event projection progress`, `Django models`.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.

## Batch:

depends-on: narrative-event-commit

Workstream: W1. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: projection progress/linkage with narrative-event-commit, correspondence-delivery, correspondence-memory-projection, narrative-story-threads.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
