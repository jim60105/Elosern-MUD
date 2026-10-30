# Proposal

## Why

Record maximum settled sight and derive permanent reveal without read writes. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Record maximum settled sight and derive permanent reveal without read writes.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-ground-reveal`: Record maximum settled sight and derive permanent reveal without read writes.

### Modified Capabilities
- `map-knowledge`: Update the existing contract explicitly.

## Impact

map_knowledge.py record_arrival; typeclasses/exits.py after_successful_movement; movement_settlement.py MovementSnapshot/settle_movement; time_skip.py advance_wait and sleep_control.py; clock snapshot/transaction; new tests/test_ground_reveal.py and existing movement/sleep tests.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
depends-on: wilderness-knowledge-chunks
depends-on: wilderness-sight-rules

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
