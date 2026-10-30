# Proposal

## Why

Calculate ground sight and transient distant sightings from validated policy. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Calculate ground sight and transient distant sightings from validated policy.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-sight`: Calculate ground sight and transient distant sightings from validated policy.

### Modified Capabilities
None.

## Impact

world/maps/wilderness_provider.py terrain delegation; new world/rules/sight.py and rulebook/sight.yaml; schema.py/documents.py DistrictDeclaration; map_district_lighting.py exact landmark membership; new world/rules/tests/test_sight.py and existing authoring tests.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
depends-on: wilderness-elevation-runtime

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
