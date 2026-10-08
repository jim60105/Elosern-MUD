## Why

Defer active examiner schedules and replay held departures once after settlement. The approved human-guild design requires real runtime behavior rather than disposable/projected substitutes.

## What Changes

- Defer active examiner schedules and replay held departures once after settlement.
- **BREAKING** where contracts change, cut over every affected caller and fixture without aliases or migrations.
- Own approved sections 4.4 movement deferral and held interval; 6.2 hold query seam; 9 deferral/release; 10 crossed departure; non-goals and shared constraints are in design.md.

## Capabilities

### New Capabilities
- `guild-exam-schedule-hold`: Requirements defined by this change.

### Modified Capabilities
- `npc-schedule-runtime`: Honor persisted examination holds in the existing clock source.

## Impact

world/rules/npc_schedules.py or occurrence sibling; world/rules/guild_exams.py; world/rules/combat_session/settlement.py; startup recovery composition root; schedule-hold tests. Focused tests, substantive traceability and affected authoring/behavior docs are in scope. No implementation is authorized by creating these artifacts.

## Batch:

depends-on: weekly-npc-schedule-cycles

Code-conflict notes: world/rules/npc_schedules.py or occurrence sibling, clock snapshot hooks and schedule-hold tests are owned here. Lifecycle owns guild_exams/combat_session activation and release wiring against these APIs. Shared shard manifests and capability delta files require serialized integration. Full matrix and approved-section ownership are in shared-military-equipment/design.md.
