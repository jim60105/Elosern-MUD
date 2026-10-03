## Why

Continuity and player collaboration require durable directions rather than generated claims of world changes. This step adds one independently testable boundary of the approved story workflow.

## What Changes

- Compile quest-seed beats through ScenarioDirector and existing atomic quest owners.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `narrative-quest-compilation`: Compile quest-seed beats through ScenarioDirector and existing atomic quest owners.

### Modified Capabilities
- `scenario-director`: deltas for the boundaries described below.

## Impact

`world/ai/scenario_director.py`, `world/narrative quest-beat orchestration`, `world/quests compile/registration read boundary`, `quest lifecycle integration`.

Main-spec reconciliation: scenario-director requires generic generate_quest_blueprint to always degrade to a compatible template. The approved beat path forbids replacement filler. Add a explicitly beat-scoped entry point with no-content degradation, preserve generic templates; do not route beats through the generic fallback. quest-progress-tracking/dialogue-offer-quest remain authoritative gameplay-only.

## Batch:

depends-on: story-director-beats

Workstream: W3. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: prompt registry/composition with yohanna-memory-dialogue, dialogue-epochs-stable-prefixes, correspondence-npc-replies, dream-explicit-presentation, story-director-beats; beat execution registry with story-director-beats.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
