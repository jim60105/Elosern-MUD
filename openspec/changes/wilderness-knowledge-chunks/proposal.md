# Proposal

## Why

Replace schema1 with bounded chunk-addressed wilderness observations. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Replace schema1 with bounded chunk-addressed wilderness observations.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-knowledge-chunks`: Replace schema1 with bounded chunk-addressed wilderness observations.

### Modified Capabilities
- `map-knowledge`: Update the existing contract explicitly.

## Impact

world/rules/map_knowledge.py SCHEMA_VERSION/NodeVisit/parse_knowledge/record_arrival/prune/remap; full-projection callers in lighting/discovery/local/area/world/party; test_map_knowledge_integration.py and existing pruning/discovery/presentation fixtures.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
No prerequisite changes.

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
