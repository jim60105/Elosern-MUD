## Why

Continuity and player collaboration require durable directions rather than generated claims of world changes. This step adds one independently testable boundary of the approved story workflow.

## What Changes

- Compact durable dialogue into explicit epochs and stable versioned prompt sections.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `dialogue-epochs`: Compact durable dialogue into explicit epochs and stable versioned prompt sections.

### Modified Capabilities
- `npc-dialogue`: deltas for the boundaries described below.

## Impact

`world/narrative/dialogue epochs`, `context renderer`, `world/ai/npc_dialogue.py`, `prompts/npc_dialogue.yaml`.

Main-spec reconciliation: npc-dialogue puts mutable location in its system prompt and uses a regenerated chat window. W1 preserves template placement; this successor delta moves location to current frames, retaining prompt-library placeholder API and persona-dialogue-injection permissions. It edits the same prompt requirement as W1 and must apply after it.

## Batch:

depends-on: yohanna-memory-dialogue

Workstream: W3. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: context/history with narrative-context-snapshots, yohanna-memory-dialogue, correspondence-npc-replies, correspondence-memory-projection, narrative-story-threads, dream-explicit-presentation; prompt registry/composition with yohanna-memory-dialogue, correspondence-npc-replies, dream-explicit-presentation, story-director-beats, scenario-beat-compilation.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
