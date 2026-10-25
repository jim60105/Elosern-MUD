# Proposal

## Why

The approved authored-dialogue design requires committed physical-condition refresh from canonical item, equipment, identity and skill writers. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Committed physical-condition refresh from canonical item, equipment, identity and skill writers.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `authored-dialogue-availability`: extend the capability introduced by an earlier dependency with this slice's named requirements.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

No static-only watcher filter, hot reload or new state writer. Committed physical-source refresh re-resolves every current scene source without exposing generated package payloads.

## Batch:

depends-on: authored-dialogue-availability

Code conflicts: Extends dialogue_availability.py and physical writers only. Progression/lifecycle refresh follows to reuse callback/owner helpers. Shared manifests need serial integration; no gameplay arithmetic changes.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. Dependencies refer to completed implementation; generated-package integration reuses these exact commit hooks.
