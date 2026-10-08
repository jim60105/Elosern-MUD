## Why

Extend the existing schedule model and occurrence arithmetic to daily or weekly cycles. The approved human-guild design requires real runtime behavior rather than disposable/projected substitutes.

## What Changes

- Extend the existing schedule model and occurrence arithmetic to daily or weekly cycles.
- **BREAKING** where contracts change, cut over every affected caller and fixture without aliases or migrations.
- Own approved sections 6.1; 9 occurrence arithmetic; 10 cycle coverage; non-goals and shared constraints are in design.md.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `npc-schedule-model`: Reconcile the canonical requirements in the delta.
- `npc-schedule-runtime`: Reconcile the canonical requirements in the delta.

## Impact

world/rules/npc_schedules.py; world/rules/rulebook/npc_schedules.yaml; world/rules/tests/test_npc_schedules.py; world/rules/tests/test_npc_schedule_runtime.py. Focused tests, substantive traceability and affected authoring/behavior docs are in scope. No implementation is authorized by creating these artifacts.

## Batch:

depends-on: none

Code-conflict notes: world/rules/npc_schedules.py; world/rules/rulebook/npc_schedules.yaml; world/rules/tests/test_npc_schedules.py; world/rules/tests/test_npc_schedule_runtime.py. Shared shard manifests and capability delta files require serialized integration. Full matrix and approved-section ownership are in shared-military-equipment/design.md.
