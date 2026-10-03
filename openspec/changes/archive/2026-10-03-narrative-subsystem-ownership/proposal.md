## Why

The approved architecture adds a persistent deterministic narrative owner that the existing authority lists do not yet name. Explicit authorization must land before feature implementation.

## What Changes

- Explicitly authorize world/narrative as the owner of persistent narrative data.
- Encode the approval at `docs/superpowers/specs/2026-10-03-narrative-memory-cognition-design.md` (approved commits 2c216f0e and 41a61572), not the superseded temporary handoff.
- Preserve deterministic ownership, knowledge-before-retrieval, offline playability and existing infrastructure; no compatibility or data-migration work.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None.

Documentation-only amendment: `skip_specs: true`; no behavioral delta is invented.

## Impact

`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, `AGENTS.md`.

Main-spec reconciliation: AI engine design and AGENTS.md enumerate maps and quests but omit narrative. This explicit amendment resolves that architecture gap; no main capability spec is changed.

## Batch:

depends-on: none

Workstream: W0. Scope target: one engineer-day; one responsibility, with its focused tests/docs. Prerequisites refer to completed implementations, not merely proposal commits.

Code-conflict notes: No domain-code overlap beyond predecessor interfaces.
