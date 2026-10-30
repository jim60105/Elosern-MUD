# Spec Delta

## Purpose

Paint the production ink map from committed decoded cells, with independent overlays, follow camera and zoom. This capability defines observable browser travel behavior and its data boundaries.

## ADDED Requirements

### Requirement: Travel painting uses disclosed cell facts
The travel map SHALL paint deterministic terrain and reveal layers from committed decoded facts, keep unknown ground transparent and update camera or overlays without repainting the terrain.

#### Scenario: Disclosure and compositing
- **WHEN** synthetic unknown, memory and live cells include bands, roads, rivers, ford, woods, districts and settlement edges
- **THEN** unknown pixels and clipped strokes remain transparent, supplied live/memory/phase facts control lighting and repeated identical input is deterministic

#### Scenario: Invalidation and repaint budget
- **WHEN** content changes at the two acceptance viewports and then only camera, zoom, aim or hover changes
- **THEN** one coalesced repaint occurs for content changes, none for transform/overlay-only changes and each warmed measured repaint takes at most50ms

### Requirement: Travel camera preserves the open stage
The travel camera SHALL follow the party or fit a locked route within measured open-stage bounds, apply bounded scaled zoom and omit glide and token breathing at off motion.

#### Scenario: Follow and fit
- **WHEN** synthetic route bounds, viewport dimensions and side-column sizes change
- **THEN** camera centres or fits within the safe rectangle with minimum14px cells for fitting and zoom18..46px in4px steps at the current UI scale

#### Scenario: Approximate edge observations
- **WHEN** bearing-only sightings have no source coordinates and open-stage exclusions change
- **THEN** cards project to its inset edge without acquiring target coordinates or covering band/header/side controls

