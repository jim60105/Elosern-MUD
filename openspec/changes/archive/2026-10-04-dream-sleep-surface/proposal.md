## Why

Continuity and player collaboration require durable directions rather than generated claims of world changes. This step adds one independently testable boundary of the approved story workflow.

## What Changes

- Connect optional dreams to sleep and complete browser/text confirm-draft-awaken surfaces.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
- `dream-sleep-surface`: Connect optional dreams to sleep and complete browser/text confirm-draft-awaken surfaces.

### Modified Capabilities
- `webclient-action-dispatch`: the production registry gains the four dream
  collaboration adapters `dream.say`, `dream.draft`, `dream.confirm`, and
  `dream.awaken`, so the requirement's exact production-registry enumeration is
  extended by this change.

## Impact

`commands/skip.py`, `web/webclient explore sleep adapter`, `dream presentation/action surface`, `docs/game/commands.md`, `docs/game/command-reference.md`.

Main-spec reconciliation: time-skip-commands remains no-duration sleep with existing regeneration calculation; skip-safety-gate currently rejects outright. The optional post-settlement dream is additive and must not reinterpret either rule. world-clock converse remains unwired; dreams do not advance it.

## Batch:

depends-on: dream-explicit-presentation

Workstream: W3. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: authoring lifecycle with dream-authoring-records, dream-session-lifecycle, dream-explicit-presentation, story-director-beats.
All feature changes also touch shared shard ownership, traceability annotations, and potentially the observability catalog; serialize/reconcile those small shared surfaces even for independent domain work. These are code conflicts, not artificial runtime prerequisites.
