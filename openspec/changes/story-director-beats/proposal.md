## Why

Continuity and player collaboration require durable directions rather than generated claims of world changes. This step adds one independently testable boundary of the approved story workflow.

## What Changes

- Generate and idempotently schedule at most one validated executable beat per decision.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `story-director-beats`: Generate and idempotently schedule at most one validated executable beat per decision.

### Modified Capabilities
None.

## Impact

`world/ai story director`, `world/narrative/director orchestration`, `beat work storage`, `owner routing`, `prompts library/registry`.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.

## Batch:

depends-on: narrative-attention
depends-on: dream-sleep-surface

Workstream: W3. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: prompt registry/composition with yohanna-memory-dialogue, dialogue-epochs-stable-prefixes, correspondence-npc-replies, dream-explicit-presentation, scenario-beat-compilation; authoring lifecycle with dream-authoring-records, dream-session-lifecycle, dream-explicit-presentation, dream-sleep-surface; beat execution registry with scenario-beat-compilation.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
