## Why

Continuity and player collaboration require durable directions rather than generated claims of world changes. This step adds one independently testable boundary of the approved story workflow.

## What Changes

- Implement durable six-exchange session accounting and confirm-or-draft departure.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `dream-session-lifecycle`: Implement durable six-exchange session accounting and confirm-or-draft departure.

### Modified Capabilities
None.

## Impact

`world/narrative/authoring session state`, `durable response delivery progress`, `session lifecycle tests`.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.

## Batch:

depends-on: dream-authoring-records

Workstream: W3. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: authoring lifecycle with dream-authoring-records, dream-explicit-presentation, dream-sleep-surface, story-director-beats.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
