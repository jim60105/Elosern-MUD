# Proposal

## Why

The approved map drawer needs one pure metric viewport model instead of the old overlay-specific lattice bounds.

## What Changes

- Add pure projection, inverse projection, anchored zoom, pan, fit, scope stops and edge clamping.
- Define units and aspect-aware continent fitting for the real area/world views.
- Defer old-overlay deletion to the final consumer cutover.

## Capabilities

### New Capabilities
- `webclient-map-viewport`: Pure metric projection and drawer-aware map navigation.

### Modified Capabilities
- None.

## Impact

Owns new `web/webclient-app/lib/map_viewport.js` and a single focused unit file. Area/world views consume it; final drawer change absorbs and deletes `lib/map_view.js` and old composable consumers. No edits to minimap auto-scale projection.

## Sizing

Estimated implementation effort: 5 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 6 is split into viewport (5h), area view (7h), world view (8h), and final drawer integration (8h), since the complete row exceeds 8h. No implementation is authorized by this proposal.

## Batch:

depends-on: none

Code-conflict notes: Owns new `web/webclient-app/lib/map_viewport.js` and a single focused unit file. Area/world views consume it; final drawer change absorbs and deletes `lib/map_view.js` and old composable consumers. No edits to minimap auto-scale projection.
