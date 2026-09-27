## Why

Present the unchanged combat hierarchy as a vertical command window with truthful contextual detail. The UI/UX review identifies this bounded surface as a source of inconsistent reading or interaction. This change is one engineer-day of implementation and focused verification; related redesign work has separate owners in the batch plan.

**Implementation profile:** visual.

## What Changes

- Present the unchanged combat hierarchy as a vertical command window with truthful contextual detail.
- Apply the concrete decisions in `design.md`, preserving server authority, offline play and existing action payloads unless the explicit creation-schema cutover says otherwise.
- Update affected stories and behavioral acceptance checks; implementation tasks remain unchecked in this proposal.

## Capabilities

### New Capabilities

None; extend the existing main capabilities rather than create a parallel UI specification.

### Modified Capabilities

- `webclient-contextual-hud`: Modify existing contracts and add the observable requirements below.
- `webclient-combat-menu`: Modify existing contracts and add the observable requirements below.

## Impact

- Application-time edit surface: `DockTabBar.vue cutover, ActionDock.vue, DockMenu.vue, SkillDetailPane.vue, AppClient.vue, combat_menu.js and frame resolver/store focus derivation`.
- No application code, assets, generation, migrations, compatibility layers or main-spec edits are part of proposing this change.
- Source and report evidence, scope exclusions and runtime verification are in `design.md` and `tasks.md`.

## Batch:

depends-on: webclient-message-typesetting

Code-conflict notes: follow the serial UI chain in `../webclient-type-scale-tokens/review-plan.md`. Shared `AppClient.vue`, shell/token styles, component stories and main capability files make these integration conflicts even where runtime features are independent. ANSI and static-art preparation may run independently as that matrix states. Dependency means applied prerequisites, not a requirement to archive them.
