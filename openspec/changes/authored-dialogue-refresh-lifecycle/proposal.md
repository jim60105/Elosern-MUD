# Proposal

## Why

The approved authored-dialogue design requires committed owner progression, companion presence, world-time and control refresh. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Committed owner progression, companion presence, world-time and control refresh.
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

Do not implement another slice, retain obsolete authored compatibility paths, change native generated/freeform authority or invent gameplay/lore. Content writing waits for its mandatory private source prerequisite at apply time.

## Batch:

depends-on: authored-dialogue-refresh-physical

Code conflicts: Follows physical callback helper and touches lifecycle writers only. Notification observation depends on this slice so no first-unlock source is missed. Shared source conflicts with possession/reading are already ordered by upstream availability dependencies.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v1. This change owns only the interfaces explicitly assigned in its design. All active proposals are planning context; dependencies refer to future completed implementation, not mere proposal existence.
