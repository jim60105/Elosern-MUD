# Proposal

## Why

Validate ordered elevation shapes before authored-map publication. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Validate ordered elevation shapes before authored-map publication.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-elevation-authoring`: Validate ordered elevation shapes before authored-map publication.

### Modified Capabilities
None.

## Impact

packages/map-core/elosern_map_core/schema.py (_DOCUMENT_KINDS), documents.py (ContinentDocument), authoring.py; packages/map-core/tests/test_authoring.py and test_yaml_codec.py.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
No prerequisite changes.

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
