## Why

Remove English/raw-key leaks from help, combat labels, conditions, codex and gallery copy. The UI/UX review identifies this bounded surface as a source of inconsistent reading or interaction. This change is one engineer-day of implementation and focused verification; related redesign work has separate owners in the batch plan.

**Implementation profile:** logic.

## What Changes

- Remove English/raw-key leaks from help, combat labels, conditions, codex and gallery copy.
- Apply the concrete decisions in `design.md`, preserving server authority, offline play and existing action payloads unless the explicit creation-schema cutover says otherwise.
- Update affected stories and behavioral acceptance checks; implementation tasks remain unchecked in this proposal.

## Capabilities

### New Capabilities

None; extend the existing main capabilities rather than create a parallel UI specification.

### Modified Capabilities

- `webclient-contextual-hud`: Add bounded observable presentation requirements.

## Impact

- Application-time edit surface: `lib/controls-reference.js, lib/condition_label.js, ConditionChips.vue, HelpOverlay.vue, SkillDetailPane.vue, PartyDrawer.vue, GalleryPanel.vue and gallery formatting helper, presentation/gallery.py, lore codex read-model label owner`.
- No application code, assets, generation, migrations, compatibility layers or main-spec edits are part of proposing this change.
- Source and report evidence, scope exclusions and runtime verification are in `design.md` and `tasks.md`.

## Batch:

depends-on: webclient-full-log-frame

Code-conflict notes: follow the serial UI chain in `../webclient-type-scale-tokens/review-plan.md`. Shared `AppClient.vue`, shell/token styles, component stories and main capability files make these integration conflicts even where runtime features are independent. ANSI and static-art preparation may run independently as that matrix states. Dependency means applied prerequisites, not a requirement to archive them.
