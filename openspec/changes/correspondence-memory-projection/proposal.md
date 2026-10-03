## Why

Continuity should work without meeting an NPC, while delivery and knowledge remain deterministic. This letter-only step implements one boundary of the approved courier workflow.

## What Changes

- Project delivered/read correspondence into owner cognition with claims kept distinct from facts.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `correspondence-memory`: Project delivered/read correspondence into owner cognition with claims kept distinct from facts.

### Modified Capabilities
None.

## Impact

`world/narrative/memory projectors`, `correspondence delivery/read/reply composition`, `context tests`.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.

## Batch:

depends-on: correspondence-npc-replies

Workstream: W2. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: context/history with narrative-context-snapshots, yohanna-memory-dialogue, correspondence-npc-replies, narrative-story-threads, dialogue-epochs-stable-prefixes, dream-explicit-presentation; projection progress/linkage with narrative-event-commit, narrative-owner-memory, correspondence-delivery, narrative-story-threads.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
