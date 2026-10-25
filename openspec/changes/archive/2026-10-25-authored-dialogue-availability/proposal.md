# Proposal

## Why

The approved authored-dialogue design requires server-qualified topic disclosure and committed-state refresh. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Server-qualified topic disclosure and committed-state refresh for static YAML and generated package scenes through one projection.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- `authored-dialogue-availability`: Server-qualified topic disclosure and committed-state refresh.

### Modified Capabilities
- `exploration-affordances`: amend the complete affected contract for this slice, preserving unrelated scenarios.
- None.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

Do not implement another slice, retain obsolete compatibility paths, invent gameplay/lore, or change existing phase/service/effect authority. Shared features cover static YAML and generated package scenes; freeform generation remains native. Content writing waits for its mandatory source prerequisite at apply time.

## Batch:

depends-on: authored-dialogue-progression-conditions

Code conflicts: Shared backend projection, action/command ingress and pusher conflict with reading/notification hooks. Reading server follows this; UI availability can run independently once server projection and playback exist.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. This change owns only the interfaces explicitly assigned in its design. Dependencies refer to completed implementation. Its projection is source-neutral, including generated scenes supplied by authored-dialogue-generated-packages.
