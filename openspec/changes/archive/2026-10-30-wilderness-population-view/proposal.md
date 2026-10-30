# Proposal

## Why

Project live and prospective population without materializing objects. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Project live and prospective population without materializing objects.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-population-view`: Project live and prospective population without materializing objects.

### Modified Capabilities
None.

## Impact

world/maps/wilderness_population.py ensure_population/population_for_coordinates/species_rule_for_coordinates and site/session branches; provider at_prepare_room; test_wilderness_population.py and test_wilderness_population_species.py.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
No prerequisite changes.

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
