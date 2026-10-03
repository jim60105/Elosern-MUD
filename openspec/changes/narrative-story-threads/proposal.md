## Why

Continuity and player collaboration require durable directions rather than generated claims of world changes. This step adds one independently testable boundary of the approved story workflow.

## What Changes

- Persist factual thread lifecycle and link existing narrative channels.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `narrative-story-threads`: Persist factual thread lifecycle and link existing narrative channels.

### Modified Capabilities
None.

## Impact

`world/narrative/threads`, `events/memory/letters/dialogue linkage`, `context cache keys`.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.

## Batch:

depends-on: correspondence-memory-projection

Workstream: W3. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: context/history with narrative-context-snapshots, yohanna-memory-dialogue, correspondence-npc-replies, correspondence-memory-projection, dialogue-epochs-stable-prefixes, dream-explicit-presentation; projection progress/linkage with narrative-event-commit, narrative-owner-memory, correspondence-delivery, correspondence-memory-projection.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
