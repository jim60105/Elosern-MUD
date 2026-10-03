## Why

NPC dialogue currently loses long-lived shared experience when its bounded chat history is trimmed. This bounded step establishes the next real prerequisite for the Yohanna memory acceptance chain.

## What Changes

- Connect durable cognition to NPC dialogue and demonstrate Yohanna shared-experience recall.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `npc-dialogue`: deltas for the boundaries described below.

## Impact

`typeclasses/npcs.py`, `world/ai/npc_dialogue.py`, `world/narrative/dialogue`, `Yohanna authored NPC data`, `NPC integration tests`.

Main-spec reconciliation: npc-dialogue requires destructive bounded per-character history and pre-persona byte-identical user payloads. Replace these with durable pair turns/bounded views and rendering-version-relative persona omission; retain all intent, offline, schedule, thinking and stale-persona scenarios. W3 later replaces prompt placement, not these safety contracts.

## Batch:

depends-on: narrative-context-snapshots

Workstream: W1. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: context/history with narrative-context-snapshots, correspondence-npc-replies, correspondence-memory-projection, narrative-story-threads, dialogue-epochs-stable-prefixes, dream-explicit-presentation; prompt registry/composition with dialogue-epochs-stable-prefixes, correspondence-npc-replies, dream-explicit-presentation, story-director-beats, scenario-beat-compilation.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
