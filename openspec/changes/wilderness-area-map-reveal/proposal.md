# Proposal

## Why

Publish a filtered41-cell RLE window through existing map transport. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Publish a filtered41-cell RLE window through existing map transport.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-area-map-reveal`: Publish a filtered41-cell RLE window through existing map transport.

### Modified Capabilities
- `webclient-area-map`: Update the existing contract explicitly.
- `webclient-map-panel-protocol`: Update the existing contract explicitly.

## Impact

area_map.py _wilderness_area; map_panels.py WILDERNESS_WINDOW/AREA_MAX_BYTES and mirrored JS protocol/panels/map_panels.js; map_parts codecs; lib/area_map_view.js and AreaMapView.vue; test_area_map.py/test_map_panel_protocol.py and existing Node/Vitest area-map tests.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
depends-on: wilderness-ground-reveal
depends-on: wilderness-population-view
depends-on: wilderness-map-disclosure

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. wilderness-map-disclosure lands before this map stops assuming an unchanged ExitCompass for unknown neighbours; both touch frozen map/protocol audits. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
