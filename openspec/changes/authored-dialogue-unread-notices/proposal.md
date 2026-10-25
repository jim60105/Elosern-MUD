# Proposal

## Why

The approved authored-dialogue design requires persistent unread markers and deferred deduplicated unlock batches. A bounded independently accepted change keeps this work implementable without transferring unresolved engine decisions to content or presentation workers.

## What Changes

- Persistent unread markers and deferred deduplicated unlock batches.
- Implement this slice's exact shared interfaces and focused acceptance with its own tests and documentation.
- Use the deterministic owner and declared dependencies; no implementation is performed by this proposal.

## Capabilities

### New Capabilities
- `authored-dialogue-unread`: Persistent unread markers and deferred deduplicated unlock batches.

### Modified Capabilities
- `webclient-dialogue-session`: update the complete affected requirement blocks while preserving unrelated scenarios.
- `webclient-exploration-menu`: update the complete affected requirement blocks while preserving unrelated scenarios.

## Impact

Target files and APIs are enumerated in design.md. This is planning on the primary branch only; future implementation is bounded to one engineer-day and task units of roughly two hours or less. No data migration, generalized scripting engine or new gameplay effects.

## Non-goals

No static-only observation gate, reconnect popup replay or model-owned state. Every current static/generated scene source shares durable unread history and ephemeral live notices.

## Batch:

depends-on: authored-dialogue-reading-client
depends-on: authored-dialogue-refresh-lifecycle

Code conflicts: Sequentially extends narrative Attribute, availability writer, pusher and frontend completion module. Existing party unlock_notices.py remains unchanged except reuse of commander_sessions discovery.

Shared contract: `../authored-dialogue-contracts/design.md`, Shared contract v2. Dependencies refer to completed implementation; narrative storage uses stable host_key while each wire batch uses its current bound physical host_id/context_id.
