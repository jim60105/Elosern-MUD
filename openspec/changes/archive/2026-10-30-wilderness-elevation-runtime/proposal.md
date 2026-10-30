# Proposal

## Why

Publish bounded fingerprinted elevation tiles and runtime lookup. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Publish bounded fingerprinted elevation tiles and runtime lookup.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-elevation-runtime`: Publish bounded fingerprinted elevation tiles and runtime lookup.

### Modified Capabilities
None.

## Impact

new elosern_map_core/elevation_codec.py, world/maps/elevation.py; world/maps/runtime.py compose/adopt; authoring skill check_map_sources.py and regenerate_partition.py precedent; runtime/codec tests.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
depends-on: wilderness-elevation-generation

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
