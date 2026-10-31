# Proposal

## Why

Expose bounded read-only travel.plan with sequential settlement prediction. This is a bounded prerequisite of the approved sight-and-fog rules layer.

## What Changes

- Expose bounded read-only travel.plan with sequential settlement prediction.
- Add the mechanism evidence and existing developer-document updates named in design.md.
- **BREAKING** Clean prerelease cutover for any schema changed by this slice; no compatibility or migration.

## Capabilities

### New Capabilities
- `wilderness-travel-planning`: Expose bounded read-only travel.plan with sequential settlement prediction.

### Modified Capabilities
None.

## Impact

world/rules/travel_cost.py wilderness_step_cost/plan_traversal/source_present_members and fatigue.py pure prediction; new travel_plan.py; web/webclient/actions/map_actions.py read precedent, registry.py ActionSpec and dispatcher.py _publish_completion; new test_travel_plan.py/test_travel_actions.py and existing movement tests.

## Non-goals

Sub-projects2/3, authored geography/content, new roads, client travel presentation/queue, camping and compatibility. Terrain appearance and authored wording are human-reviewed against the detailed design rather than tested requirements.

## Batch:
depends-on: wilderness-area-map-reveal

Code-conflict notes: shared schema.py/documents.py edits order shapes before sight; knowledge-chunks before ground-reveal; population before area/interrupts; area then planner then interrupts serialize protocol/docs/action changes. All server slices may conflict in .github/evennia-shards.json; one integration owner serializes that manifest. Follow the dependency matrix in design.md.
