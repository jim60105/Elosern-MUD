# Proposal

## Why

The approved authored-dialogue design requires cut over all authored backend/text delivery and version-3 protocol. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Cut over all authored backend/text delivery and version-3 protocol.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- **BREAKING**: replace old authored shapes/payloads and version-2 mirrors without aliases or compatibility support.

## Capabilities

### New Capabilities
- `authored-dialogue-selection`: Cut over all authored backend/text delivery and version-3 protocol.

### Modified Capabilities
- `webclient-oob-protocol`: amend the complete affected contract for this slice, preserving unrelated scenarios.
- `scripted-dialogue`: update the complete affected requirement blocks while preserving unrelated scenarios.
- `webclient-dialogue-session`: update the complete affected requirement blocks while preserving unrelated scenarios.
- `webclient-exploration-menu`: update the complete affected requirement blocks while preserving unrelated scenarios.
- `exploration-affordances`: update the complete affected requirement blocks while preserving unrelated scenarios.
- `webclient-contextual-hud`: update the complete affected requirement blocks while preserving unrelated scenarios.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

No compatibility paths, new game effects or freeform/phase authority changes. Static and generated scenes share the source-neutral runtime; generated-packages supplies the production generated provider in its bounded cutover. Content writing waits for the mandatory source prerequisite.

## Batch:

depends-on: authored-dialogue-contracts
depends-on: authored-dialogue-yaml-loader

Code conflicts: Highest backend blast radius. Conflicts with possession, availability, reading in dialogue.py, exploration_actions.py, protocol and presenter; dependent order is mandatory. Registry mechanical conversion precedes every prose slice.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. This change migrates every static Python table directly to scanner-discovered profile-key YAML and removes obsolete modules. Generated-package cutover later uses these complete shared interfaces without a second scene runtime.
