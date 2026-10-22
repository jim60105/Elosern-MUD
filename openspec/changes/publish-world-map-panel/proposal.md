# Proposal

## Why

The world tab needs a server-filtered exploration payload and first-landmark discovery narrative while withholding unknown world contents.

## What Changes

- Add map.view world scope and world_map with cached common/district geometry.
- Filter unlit/hidden places, RLE/downsample trail and round unknown commission markers to 50 km.
- Emit committed first-landmark discovery prose without new knowledge state.

## Capabilities

### New Capabilities
- `webclient-world-map`: Server-filtered continental panel and privacy-aware markers.
- `map-district-discovery`: Exactly-once first committed landmark arrival narrative.

### Modified Capabilities
- None.

## Impact

Touches new world presenter/schema and browser validator/allowlist, map.view handler, presentation registry, `typeclasses/exits.py` committed movement seam and focused tests. Conflicts with area/transport and final drawer in registry/protocol/state wiring; depends transitively on final landmark authoring through transport. Uses shared frozen lookup, not regeneration.

## Sizing

Estimated implementation effort: 8 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 5 presenter/narrative sub-change, after the separate 6h transport work; 4h filtered presenter/cache/trail, 2h arrival narrative and 2h focused tests/docs. No implementation is authorized by this proposal.

## Batch:

depends-on: establish-map-districts
depends-on: transport-world-map-panel
depends-on: resolve-map-quest-destinations

Code-conflict notes: Touches new world presenter/schema and browser validator/allowlist, map.view handler, presentation registry, `typeclasses/exits.py` committed movement seam and focused tests. Conflicts with area/transport and final drawer in registry/protocol/state wiring; depends transitively on final landmark authoring through transport. Uses shared frozen lookup, not regeneration.
