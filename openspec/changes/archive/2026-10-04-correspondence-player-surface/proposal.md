## Why

Continuity should work without meeting an NPC, while delivery and knowledge remain deterministic. This letter-only step implements one boundary of the approved courier workflow.

## What Changes

- Expose branch send/collect and portable collected-letter reading.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `correspondence-player-surface`: Expose branch send/collect and portable collected-letter reading.

### Modified Capabilities
None.

## Impact

`commands correspondence`, `web/webclient actions/presentation`, `webclient letter surface`, `branch service data`, `docs/game/commands.md`, `docs/game/command-reference.md`.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.

## Batch:

depends-on: correspondence-delivery

Workstream: W2. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: No domain-code overlap beyond predecessor interfaces.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
