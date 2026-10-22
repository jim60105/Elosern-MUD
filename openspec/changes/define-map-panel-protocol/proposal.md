# Proposal

## Why

Independent map presenters, transport and real components need one exact wire contract and on-demand storage policy before any can be implemented safely.

## What Changes

- Define exact area/world panel wire schemas and stable coordinate-frame identity.
- Amend eager snapshot semantics for separate epoch-scoped maps.
- Add bounded atomic map-part delivery for panel sizes that exceed a frame.

## Capabilities

### New Capabilities
- `webclient-map-panel-protocol`: Exact map panel schemas and bounded atomic on-demand delivery.

### Modified Capabilities
- `webclient-oob-protocol`: Separate eager snapshots from epoch-scoped explicitly requested map models.

## Impact

Owns shared Python/JS map schemas, protocol decoder/store and coordinator on-demand selection policy, plus the narrow bounded part codec. Conflicts with area/world/transport in these same files, so all consume this prerequisite. No map presenter/action is registered until its owning change.

## Sizing

Estimated implementation effort: 8 hours, including focused tests and documentation, for a gpt-luna-level worker. Review-driven §9 rows 4/5 prerequisite split: exact schemas, on-demand snapshot semantics and bounded part codec are moved here so neither 8h presenter depends on an undefined/later wire contract. Budget 3h schemas, 2h codec, 1h on-demand storage and 2h focused verification/docs. No implementation is authorized by this proposal.

## Batch:

depends-on: add-local-map-gateway-metadata

Code-conflict notes: Owns shared Python/JS map schemas, protocol decoder/store and coordinator on-demand selection policy, plus the narrow bounded part codec. Conflicts with area/world/transport in these same files, so all consume this prerequisite. No map presenter/action is registered until its owning change.
