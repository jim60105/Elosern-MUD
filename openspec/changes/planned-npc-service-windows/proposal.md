## Why

Expose read-only planned service-capable NPC presence intervals. The approved human-guild design requires real runtime behavior rather than disposable/projected substitutes.

## What Changes

- Expose read-only planned service-capable NPC presence intervals.
- **BREAKING** where contracts change, cut over every affected caller and fixture without aliases or migrations.
- Own approved sections 6.2; 9 reader; 10 availability coverage; non-goals and shared constraints are in design.md.

## Capabilities

### New Capabilities
- `npc-service-availability`: Requirements defined by this change.

### Modified Capabilities
None.

## Impact

world/rules/npc_schedules.py or focused sibling reader; world/rules/service_gate.py; world/rules/clock.py read seam; schedule reader tests. Focused tests, substantive traceability and affected authoring/behavior docs are in scope. No implementation is authorized by creating these artifacts.

## Batch:

depends-on: weekly-npc-schedule-cycles

Code-conflict notes: world/rules/npc_schedules.py or focused sibling reader; world/rules/service_gate.py; world/rules/clock.py read seam; schedule reader tests. Shared shard manifests and capability delta files require serialized integration. Full matrix and approved-section ownership are in shared-military-equipment/design.md.
