# Proposal

## Why

The completed panel and view slices need the approved option-A shell, session refresh workflow and a clean replacement of the obsolete full-map overlay.

## What Changes

- Compose MapDrawer and MapEdgePointers inside OverlayHost with two ARIA tabs and floating option-A controls.
- Wire on-demand requests and committed-move active-scope refresh.
- Add keyboard/text accessibility, real-component scenarios and live walk.
- **BREAKING**: delete old MapOverlay/lattice-only paths after minimap cutover.

## Capabilities

### New Capabilities
- `webclient-map-drawer`: Area/world shell, request lifecycle, floating controls and clean map cutover.

### Modified Capabilities
- None.

## Impact

Touches `AppClient.vue`, `OverlayHost.vue`, map store/intents/keyboard bindings, new MapDrawer/MapEdgePointers, old MapOverlay/map lattice composables/helpers and component/story/browser manifests. Conflicts with both panel/view changes and minimap cutover on shared map files/styles. Explicitly waits for the complete minimap chain through animate-minimap-scale-transitions before deletion; no new minimap proposal.

## Sizing

Estimated implementation effort: 8 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 6 final integration sub-change, after viewport and the two real views; 4h shell/request/pointer wiring, 2h story/keyboard work and 2h focused live walk/removal/docs. No implementation is authorized by this proposal.

## Batch:

depends-on: publish-area-map-panel
depends-on: publish-world-map-panel
depends-on: render-area-map-view
depends-on: render-world-map-view
depends-on: animate-minimap-scale-transitions

Code-conflict notes: Touches `AppClient.vue`, `OverlayHost.vue`, map store/intents/keyboard bindings, new MapDrawer/MapEdgePointers, old MapOverlay/map lattice composables/helpers and component/story/browser manifests. Conflicts with both panel/view changes and minimap cutover on shared map files/styles. Explicitly waits for the complete minimap chain through animate-minimap-scale-transitions before deletion; no new minimap proposal.
