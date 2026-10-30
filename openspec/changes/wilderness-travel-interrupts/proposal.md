# Proposal

## Why

Attach stateless commit-qualified interrupt flags to wilderness moves. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Attach stateless commit-qualified interrupt flags to wilderness moves.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-travel-interrupts`: Attach stateless commit-qualified interrupt flags to wilderness moves.

### Modified Capabilities
None.

## Impact

exploration_actions.py validate_move_payload/_move_adapter and publication-group data; movement_settlement.py settle_movement/MovementSnapshot; new travel_interrupts.py/test_travel_interrupts.py; existing test_exploration_actions/test_move_and_look.py and dispatcher data-slot tests.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
depends-on: wilderness-travel-planning

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
