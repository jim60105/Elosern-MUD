# Proposal

## Why

Both map scopes need the same canonical interpretation of accepted commission destinations before they can render local markers or world bearings.

## What Changes

- Resolve the four approved destination families on the server.
- Retain local node identity separately from world anchor position.
- Expose a pure read-only result for the two panel consumers.

## Capabilities

### New Capabilities
- `map-quest-destinations`: Canonical read-only commission destination resolution.

### Modified Capabilities
- None.

## Impact

Owns proposed shared map-destination presentation helper, reading `world/quests/definitions.py`, accepted runtime records, lore anchors, wilderness regions and monster sites. Area/world presenters consume it; no quest-authoring or lifecycle edits.

## Sizing

Estimated implementation effort: 5 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 4 is split into this 5h shared destination resolver and publish-area-map-panel (8h); the combined resolver, four layer adapters and protocol tests exceed 8h. No implementation is authorized by this proposal.

## Batch:

depends-on: author-border-river-and-forest-edge

Code-conflict notes: Owns proposed shared map-destination presentation helper, reading `world/quests/definitions.py`, accepted runtime records, lore anchors, wilderness regions and monster sites. Area/world presenters consume it; no quest-authoring or lifecycle edits.
