# Proposal

## Why

The old local_map is bounded to a small neighbourhood and cannot support whole-settlement or dungeon fog-of-war area navigation.

## What Changes

- Register on-demand map.view and area_map across all four layer families.
- Reuse upstream gateway metadata and accepted destination resolver.
- Preserve whole visited/frontier graph, metre positions and coordinate-free interiors.
- Keep maps out of automatic movement refresh.

## Capabilities

### New Capabilities
- `webclient-area-map`: On-demand area panel, truthful fog of war and adjacent movement.

### Modified Capabilities
- None.

## Impact

Touches `web/webclient/actions/registry.py`, a new map action adapter, presentation registry/coordinator and new area presenter/schema; client protocol allowlist/validator changes are included. Conflicts with world publication and transport in registry/coordinator/protocol tests, and with minimap work in shared validators/manifests. Apply after the named gateway proposal, not a re-proposal of it.

## Sizing

Estimated implementation effort: 8 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 4 panel sub-change, split after resolve-map-quest-destinations; 3h graph adapters, 2h wilderness/action integration and 3h validators/tests/docs. No implementation is authorized by this proposal.

## Batch:

depends-on: add-local-map-gateway-metadata
depends-on: compute-map-district-partition
depends-on: resolve-map-quest-destinations

Code-conflict notes: Touches `web/webclient/actions/registry.py`, a new map action adapter, presentation registry/coordinator and new area presenter/schema; client protocol allowlist/validator changes are included. Conflicts with world publication and transport in registry/coordinator/protocol tests, and with minimap work in shared validators/manifests. Apply after the named gateway proposal, not a re-proposal of it.
