# Proposal

## Why

The approved authored-dialogue design requires shared manual vue scene player and synchronized stage attribution. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Shared manual Vue scene player and synchronized stage attribution.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- `authored-scene-playback`: Shared manual Vue scene player and synchronized stage attribution.

### Modified Capabilities
- `webclient-contextual-hud`: update the complete affected requirement blocks while preserving unrelated scenarios.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

Do not implement another slice, retain obsolete authored compatibility paths, change native generated/freeform authority or invent gameplay/lore. Content writing waits for its mandatory private source prerequisite at apply time.

## Batch:

depends-on: authored-dialogue-runtime

Code conflicts: Conflicts with reading-client and availability UI in AppClient, use-dialogue-choices and dialogue-view; those depend on this slice. Combat behavior must remain unchanged.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v1. This change owns only the interfaces explicitly assigned in its design. All active proposals are planning context; dependencies refer to future completed implementation, not mere proposal existence.
