## Why

Implement reducing-only exam accessories and shared skill/stat restriction consumers. The approved human-guild design requires real runtime behavior rather than disposable/projected substitutes.

## What Changes

- Implement reducing-only exam accessories and shared skill/stat restriction consumers.
- **BREAKING** where contracts change, cut over every affected caller and fixture without aliases or migrations.
- Own approved sections 4.1-4.3; 9 restriction policy; 10 consumer coverage; non-goals and shared constraints are in design.md.

## Capabilities

### New Capabilities
- `guild-exam-restrictions`: Requirements defined by this change.

### Modified Capabilities
None.

## Impact

world/rules/equipment.py; world/rules/action.py; world/rules/traits.py; world/rules/combat_modifiers.py; world/rules/combat.py; world/skills/ read consumers; world/rules/combat_view.py; world/rules/rulebook/; item registry; restriction tests. Focused tests, substantive traceability and affected authoring/behavior docs are in scope. No implementation is authorized by creating these artifacts.

## Batch:

depends-on: shared-military-equipment

Code-conflict notes: world/rules/equipment.py; world/rules/action.py; world/rules/traits.py; world/rules/combat_modifiers.py; world/rules/combat.py; world/skills/ read consumers; world/rules/combat_view.py; world/rules/rulebook/; item registry; restriction tests. Shared shard manifests and capability delta files require serialized integration. Full matrix and approved-section ownership are in shared-military-equipment/design.md.
