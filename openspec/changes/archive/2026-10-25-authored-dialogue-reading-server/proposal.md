# Proposal

## Why

The approved authored-dialogue design requires narrative-owned formal reading, delivered receipts and pure-chain synchronization. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Narrative-owned formal reading, delivered receipts and pure-chain synchronization.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- `authored-dialogue-reading`: Narrative-owned formal reading, delivered receipts and pure-chain synchronization.

### Modified Capabilities
- `exploration-affordances`: amend the complete affected contract for this slice, preserving unrelated scenarios.
- None.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

No model-generated reading writes, filesystem persistence, static-only completion gate or effect authorization from reading receipts. Both scene sources share stable owner/host_key/topic persistence.

## Batch:

depends-on: authored-dialogue-availability

Code conflicts: Owns narrative Attribute and backend receipt/pusher changes. UI locked change is independent code-wise but reading-client depends on both. Notification slice extends same Attribute after this.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. Dependencies refer to completed implementation; generated phase invalidation retires receipts while stable package-role/phase-topic reading survives save/reload.
