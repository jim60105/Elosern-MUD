# Proposal

## Why

The approved authored-dialogue design requires memory-only completion retry and pure-chain progression. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Memory-only completion retry and pure-chain progression.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `authored-dialogue-reading`: extend the capability introduced by an earlier dependency with this slice's named requirements.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

Do not implement another slice, retain obsolete authored compatibility paths, change native generated/freeform authority or invent gameplay/lore. Content writing waits for its mandatory private source prerequisite at apply time.

## Batch:

depends-on: authored-dialogue-reading-server
depends-on: authored-dialogue-locked-ui

Code conflicts: Touches player composable, choices, transport and AppClient after locked UI. Notifications depend on this return-to-choices boundary; no separate durable client storage.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v1. This change owns only the interfaces explicitly assigned in its design. All active proposals are planning context; dependencies refer to future completed implementation, not mere proposal existence.
