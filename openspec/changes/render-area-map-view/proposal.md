# Proposal

## Why

The area tab must render the whole approved area payload while retaining truthful metre spacing and dungeon fog.

## What Changes

- Add real AreaMapView for settlement, instance/interior and wilderness.
- Use metric viewport or truthful radial layout and scale-true dots/readout.
- Add server-bound adjacent 前往 selection with real-component stories.

## Capabilities

### New Capabilities
- `webclient-area-map-view`: Area geometry, fog, readable selection and adjacent-only movement.

### Modified Capabilities
- None.

## Impact

Owns new `AreaMapView.vue`, scoped view helpers, real stories and one focused component test file; shared viewport API is upstream. Conflicts with final drawer component-story manifests and app-shell styles; final drawer owns runtime tab/request integration.

## Sizing

Estimated implementation effort: 7 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 6 area-view sub-change, after its pure viewport and server panel; 4h renderer, 1h stories and 2h focused unit/visual verification. No implementation is authorized by this proposal.

## Batch:

depends-on: publish-area-map-panel
depends-on: establish-map-viewport

Code-conflict notes: Owns new `AreaMapView.vue`, scoped view helpers, real stories and one focused component test file; shared viewport API is upstream. Conflicts with final drawer component-story manifests and app-shell styles; final drawer owns runtime tab/request integration.
