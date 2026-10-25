# Proposal

## Why

The approved authored-dialogue design requires lawful possessed authored conversations with owner-correct relationships. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Lawful possessed authored conversations with owner-correct relationships.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- `authored-dialogue-possession`: Lawful possessed authored conversations with owner-correct relationships.

### Modified Capabilities
- `webclient-dialogue-session`: amend the complete affected contract for this slice, preserving unrelated scenarios.
- `webclient-possession-presentation`: update the complete affected requirement blocks while preserving unrelated scenarios.
- `webclient-exploration-menu`: update the complete affected requirement blocks while preserving unrelated scenarios.
- `exploration-affordances`: update the complete affected requirement blocks while preserving unrelated scenarios.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

Do not implement another slice, retain obsolete authored compatibility paths, change native generated/freeform authority or invent gameplay/lore. Content writing waits for its mandatory private source prerequisite at apply time.

## Batch:

depends-on: authored-dialogue-runtime
depends-on: authored-dialogue-playback

Code conflicts: Touches shared backend context/adapters and browser fixture with condition/reading changes; sequence accordingly. No economy.py modification permitted.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v1. This change owns only the interfaces explicitly assigned in its design. All active proposals are planning context; dependencies refer to future completed implementation, not mere proposal existence.
