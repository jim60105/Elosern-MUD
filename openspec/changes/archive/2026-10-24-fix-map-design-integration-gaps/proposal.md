# Proposal

## Why

The completed minimap and world-map cutovers retain six integration defects affecting action identity, commission positioning, marker clearance, scale readability, discovery lifecycle and read-only room state. The world-map parent design also still says it is unimplemented despite its thirteen archived changes; this corrective proposal records the remaining work without claiming completion.

## What Changes

- Keep gateway-stub arrow and label hit regions separate for every label placement so nearby street clicks retain their original movement descriptor and native keyboard activation remains single-shot.
- Reuse one canonical tagged-place-to-enclosing-anchor lookup for registered ordinary interiors and their instance origins, restoring supported hunt destinations and off-area bearings without inventing room coordinates.
- Make overlap spreading consume the painted ordinary/gateway marker footprint from shared geometry, preserving the existing angular cap and unaffected bearings.
- Derive bounded compressed-ring candidates from the positive distance range, including metre-scale inputs, using the existing radial mapper and readability limits.
- Establish each drawer opening's world discovery baseline from its first fresh world publication, preserving real while-open discovery and session viewport memory.
- Read instance origins through the AttributeHandler without autocreating absent persistent Attributes, including area reads with empty quest logs and bound-instance destination resolution.
- On implementation completion, correct parent-design status and link this corrective work without rewriting archived evidence or reporting pending fixes as done.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-local-map`: isolated stub activation, painted-footprint overlap handling and readable compressed rings at metre scales.
- `map-quest-destinations`: canonical registered-interior origins and non-mutating instance-origin resolution.
- `webclient-area-map`: persisted read-only guarantees and registered-interior external commission markers.
- `webclient-map-drawer`: fresh per-opening world adoption through the existing request/commit lifecycle.
- `webclient-world-map-view`: discovery begins after the fresh opening baseline and never replays closed-period discoveries.

## Impact

Targets are the existing projection/renderer geometry, map destination/world-position presenters, protocol store publication metadata, app-store view and drawer host/composable/view handoff. Regressions extend existing Python, Node, Vitest, Storybook and browser owners. No implementation or main-spec synchronization belongs to this proposal. The bounded implementation is one engineer-day of local corrections and existing-owner regressions; CI execution time is outside that work estimate.

## Non-goals

No geography, balance, partition or new-content work; no automatic travel, telemetry, polling, retry queue, migration, compatibility alias, protocol/schema-version change or broad redesign. Preserve coordinate-free rooms, authoritative opaque actions, world privacy/50 km rounding, existing area precision, the approved 2,097,152-byte world transport ceiling and coarse-trail bounds. Deleted MapOverlay/cellSize/rank-compression/map_view paths remain deleted; duplicate wilderness-name suppression and current-label fallback remain intentional.

## Dependencies and conflicts

No active predecessor is required; the five minimap and thirteen world-map changes are archived. This single change has no internal batch dependency. Concurrent edits to the projection/marker geometry, canonical room origins, protocol publication metadata, drawer lifecycle, associated regressions or the two parent designs require serialization or explicit integration review.
