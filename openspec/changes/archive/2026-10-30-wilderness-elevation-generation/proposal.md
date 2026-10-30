# Proposal

## Why

Generate deterministic physical elevation and prominence offline. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Generate deterministic physical elevation and prominence offline.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-elevation-generation`: Generate deterministic physical elevation and prominence offline.

### Modified Capabilities
None.

## Impact

packages/map-core/elosern_map_core/terrain.py, partition.py, sources.py; new elevation.py and tests/test_elevation.py.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
depends-on: wilderness-elevation-shapes

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
