# Proposal

## Why

The world tab must show permitted exploration geography at several scales without reconstructing secrets or reducing label readability.

## What Changes

- Add real WorldMapView with approved layer order and inclusive LOD thresholds.
- Render approximate quest circles and accessible lit/unlit distinction.
- Animate newly lit districts for 600 ms with instant reduced motion and readable selection.

## Capabilities

### New Capabilities
- `webclient-world-map-view`: Filtered world layering, precision-aware LOD and district reveal presentation.

### Modified Capabilities
- None.

## Impact

Owns `WorldMapView.vue`, narrow render helpers, its real stories and focused tests. Shares viewport upstream; final drawer owns shell/control/list/details composition. Conflicts with final drawer story coverage/style manifests and with minimap motion work only in shared motion tokens; do not edit minimap animation ownership.

## Sizing

Estimated implementation effort: 8 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 6 world-view sub-change, budgeted as 4h layered renderer/LOD, 2h animation/accessibility and 2h focused story/visual/unit verification. No implementation is authorized by this proposal.

## Batch:

depends-on: publish-world-map-panel
depends-on: establish-map-viewport

Code-conflict notes: Owns `WorldMapView.vue`, narrow render helpers, its real stories and focused tests. Shares viewport upstream; final drawer owns shell/control/list/details composition. Conflicts with final drawer story coverage/style manifests and with minimap motion work only in shared motion tokens; do not edit minimap animation ownership.
