## Why

Stabilize top-navigation placement and polish the place card without changing visibility rules. The UI/UX review identifies this bounded surface as a source of inconsistent reading or interaction. This change is one engineer-day of implementation and focused verification; related redesign work has separate owners in the batch plan.

**Implementation profile:** visual.

## What Changes

- Stabilize top-navigation placement and polish the place card without changing visibility rules.
- Apply the concrete decisions in `design.md`, preserving server authority, offline play and existing action payloads unless the explicit creation-schema cutover says otherwise.
- Update affected stories and behavioral acceptance checks; implementation tasks remain unchecked in this proposal.

## Capabilities

### New Capabilities

None; extend the existing main capabilities rather than create a parallel UI specification.

### Modified Capabilities

- `webclient-desktop-shell`: Add the stable top-navigation placement and shared tool-tooltip requirement; the tool-group requirement names the visible tooltip and the shared tool model.
- `webclient-contextual-hud`: The place-card requirement gains its two-level hierarchy (gold rule, no leading separator, tabular numeral-face time).

## Impact

- Application-time edit surface: `DesktopNavigation.vue`, new `nav-tools.js` (the shared tool model, also read by `OverlayHost.vue`), `PlaceCard.vue`, `styles/app-shell.css` (brand), stories and tests. `TopBar.vue` markup and `dock-icons.js` glyph keys are unchanged (A10 already shares the glyph keys with DrawerHeader).
- No application code, assets, generation, migrations, compatibility layers or main-spec edits are part of proposing this change.
- Source and report evidence, scope exclusions and runtime verification are in `design.md` and `tasks.md`.

## Batch:

depends-on: webclient-map-legibility

Code-conflict notes: follow the serial UI chain in `../webclient-type-scale-tokens/review-plan.md`. Shared `AppClient.vue`, shell/token styles, component stories and main capability files make these integration conflicts even where runtime features are independent. ANSI and static-art preparation may run independently as that matrix states. Dependency means applied prerequisites, not a requirement to archive them.
