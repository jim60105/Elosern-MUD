## Why

Continuity should work without meeting an NPC, while delivery and knowledge remain deterministic. This letter-only step implements one boundary of the approved courier workflow.

## What Changes

- Generate optional owner-permitted NPC letter replies with channel-specific effect gates.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `correspondence-npc-replies`: Generate optional owner-permitted NPC letter replies with channel-specific effect gates.

### Modified Capabilities
None.

## Impact

`world/ai correspondence capability`, `world/narrative/correspondence reply work`, `world/rules relationship owner`, `prompts registry/library`, `server composition`.

Main-spec reconciliation: npc-dialogue and dialogue-offer-quest permit face-to-face quest assignment and completion-time co-location checks. Their contracts remain face-to-face only; correspondence uses a distinct restricted channel and never routes offer_quest through those appliers.

## Batch:

depends-on: correspondence-player-surface

Workstream: W2. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: context/history with narrative-context-snapshots, yohanna-memory-dialogue, correspondence-memory-projection, narrative-story-threads, dialogue-epochs-stable-prefixes, dream-explicit-presentation; prompt registry/composition with yohanna-memory-dialogue, dialogue-epochs-stable-prefixes, dream-explicit-presentation, story-director-beats, scenario-beat-compilation.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
