# Proposal

## Why

Filter eager wilderness map facts while preserving opaque directional movement. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Filter eager wilderness map facts while preserving opaque directional movement.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-map-disclosure`: Filter eager wilderness map facts while preserving opaque directional movement.

### Modified Capabilities
- `webclient-local-map`: Update the existing contract explicitly.
- `webclient-exploration-menu`: Update the existing contract explicitly.
- `webclient-exit-compass`: Update the existing contract explicitly.

## Impact

web/webclient/presentation/local_map/wilderness.py _wilderness_layer; exploration.py _move_rows and mirrored exploration validator; shared move-entry projection and dialogue exit consumers; ExitCompass target model; local-map/exploration/compass tests and frozen protocol audits.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
depends-on: wilderness-ground-reveal

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. This change also lands before wilderness-travel-interrupts: both modify webclient-exploration-menu and the exploration move-row payload, so the schema5->6 nullable-destination cutover is integrated first and the optional walk field is added on top of it. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
