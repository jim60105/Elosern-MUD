# Proposal

## Why

Paint the production ink map from committed decoded cells, with independent overlays, follow camera and zoom. This delivers the approved browser travel interface without duplicating the sight/reveal rules batch.

## What Changes

- Paint the production ink map from committed decoded cells, with independent overlays, follow camera and zoom.
- Add the focused behavior, production fixture/story and browser/server evidence specified in design.md and tasks.md.
- **BREAKING** Any schema cutover described in design.md replaces its prior prerelease form, with no migration or compatibility path.

## Capabilities

### New Capabilities
- `webclient-travel-map`: Paint the production ink map from committed decoded cells, with independent overlays, follow camera and zoom.

### Modified Capabilities
- `webclient-map-drawer`: Amend existing exact contracts for this travel slice.

## Impact

TravelMap.vue is the working stage wrapper introduced by the base change. Existing lib/area_map_view.js and AreaMapView.vue remain the drawer renderer; do not redesign them. The approved prototype supplies appearance only. lib/travel-grid.js is the single cell-grid input. Shared glyph sources are MapNodeGlyph.vue, WorldMapGlyph.vue, WorldHatchPattern.vue and styles/area-map-ink.css; the band ornament is shared HUD chrome.

## Non-goals

No new server travel mode, client-side rules/routing, authored geography, new art, camping rules/cards, dialogue/combat redesign, compatibility or database migrations. Visual style, copy and prototype fidelity are human-reviewed against the approved interface design rather than tested as normative qualities.

## Batch:
depends-on: wilderness-travel-interface

Code-conflict notes: use this change's design.md matrix. Only direct prerequisites are machine dependencies; shared AppClient/store/protocol/docs and shard-manifest edits require serialized integration. Base adapter-path changes1-5 can ship before sub-project1; changes6-8 consume its protocols. A Batch without depends-on lines is an independent root.
