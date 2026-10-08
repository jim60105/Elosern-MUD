## Why

Cut all examination surfaces to presence-first appointment requests and services schema v5. The approved human-guild design requires real runtime behavior rather than disposable/projected substitutes.

## What Changes

- Cut all examination surfaces to presence-first appointment requests and services schema v5.
- **BREAKING** where contracts change, cut over every affected caller and fixture without aliases or migrations.
- Own approved sections 7.1-7.3; 6.2 presentation; 9 coordinator/adapters; 10 browser/command/intent acceptance; non-goals and shared constraints are in design.md.

## Capabilities

### New Capabilities
- `guild-exam-requests`: Requirements defined by this change.

### Modified Capabilities
- `guild-rank-exams`: Reconcile the canonical requirements in the delta.
- `webclient-service-menus`: Reconcile the canonical requirements in the delta.
- `npc-dialogue`: Reconcile the canonical requirements in the delta.
- `webclient-action-dispatch`: Cut the allowlisted exam action to guild.exam_request.

## Impact

world/rules/guild_exams.py or request sibling; world/rules/service_view.py; world/rules/npc_intents.py; world/rules/service_messages.py; commands/combat.py; web/webclient/actions/service_actions.py; web/webclient/presentation/services.py; panel registry/constants; web/static/webclient/js/elosern/protocol/panels/services.js; web/webclient-app/ guild components and stories; browser fixtures; command docs. Focused tests, substantive traceability and affected authoring/behavior docs are in scope. No implementation is authorized by creating these artifacts.

## Batch:

depends-on: planned-npc-service-windows
depends-on: persistent-guild-exam-lifecycle
depends-on: guild-exam-schedule-hold

Code-conflict notes: world/rules/guild_exams.py or request sibling; world/rules/service_view.py; world/rules/npc_intents.py; world/rules/service_messages.py; commands/combat.py; web/webclient/actions/service_actions.py; web/webclient/presentation/services.py; panel registry/constants; web/static/webclient/js/elosern/protocol/panels/services.js; web/webclient-app/ guild components and stories; browser fixtures; command docs. Shared shard manifests and capability delta files require serialized integration. Full matrix and approved-section ownership are in shared-military-equipment/design.md.
