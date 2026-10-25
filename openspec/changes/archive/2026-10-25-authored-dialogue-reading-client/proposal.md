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

No durable browser queue, optimistic protected unlock or generated-specific acknowledgement path. Static and generated scene IDs are opaque through the same completion state machine.

## Batch:

depends-on: authored-dialogue-reading-server
depends-on: authored-dialogue-locked-ui

Code conflicts: Touches player composable, choices, transport and AppClient after locked UI. Notifications depend on this return-to-choices boundary; no separate durable client storage.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. Dependencies refer to completed implementation; retain exact generated IDs in memory and request validation without truncation.
