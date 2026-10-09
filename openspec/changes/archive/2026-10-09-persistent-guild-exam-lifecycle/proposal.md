## Why

Replace disposable opponents with atomic persistent-host simulation and recovery. The approved human-guild design requires real runtime behavior rather than disposable/projected substitutes.

## What Changes

- Replace disposable opponents with atomic persistent-host simulation and recovery.
- **BREAKING** where contracts change, cut over every affected caller and fixture without aliases or migrations.
- Own approved sections 1 temporary-host supersession; 4.4 start settlement recovery except schedule release; 9 lifecycle; 10 recovery/rollback; non-goals and shared constraints are in design.md.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `guild-rank-exams`: Reconcile the canonical requirements in the delta.
- `npc-profile-registry`: Reconcile the canonical requirements in the delta.
- `npc-identity-titles`: Reconcile the canonical requirements in the delta.
- `player-combat-session`: Retain persistent exam hosts on forfeit and recovery.

## Impact

world/rules/guild_exams.py; world/rules/combat_session/{battlefield,lifecycle,settlement,snapshot,records}.py; world/lore/guild.py; world/rules/guild_config/; world/rules/npc_roster_validation.py; source inventory; service assembly; synthetic guild fixtures and consumers. Focused tests, substantive traceability and affected authoring/behavior docs are in scope. No implementation is authorized by creating these artifacts.

## Batch:

depends-on: persistent-human-guild-hosts
depends-on: guild-exam-restriction-policy
depends-on: guild-exam-schedule-hold

Code-conflict notes: world/rules/guild_exams.py; world/rules/combat_session/{battlefield,lifecycle,settlement,snapshot,records}.py; world/lore/guild.py; world/rules/guild_config/; world/rules/npc_roster_validation.py; source inventory; service assembly; synthetic guild fixtures and consumers. Shared shard manifests and capability delta files require serialized integration. Full matrix and approved-section ownership are in shared-military-equipment/design.md.
