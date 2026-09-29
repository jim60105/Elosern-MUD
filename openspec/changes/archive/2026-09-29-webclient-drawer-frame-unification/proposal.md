## Why

Unify reference drawer and overlay framing without moving their modal boundary. The UI/UX review identifies this bounded surface as a source of inconsistent reading or interaction. This change is one engineer-day of implementation and focused verification; related redesign work has separate owners in the batch plan.

**Implementation profile:** visual.

## What Changes

- Unify reference drawer and overlay framing without moving their modal boundary.
- One presentational `DrawerHeader` (registry glyph, serif title, subtitle, 36px close) for drawers, overlays and the gallery; opaque panels over a scrim; navigation glyphs moved into the shared registry so headers and navigation agree.
- Apply the concrete decisions in `design.md`, preserving server authority, offline play and existing action payloads unless the explicit creation-schema cutover says otherwise.
- Update affected stories and behavioral acceptance checks; implementation tasks remain unchecked in this proposal.

## Capabilities

### New Capabilities

None; extend the existing main capabilities rather than create a parallel UI specification.

### Modified Capabilities

- `webclient-contextual-hud`: Add the shared opaque reference-surface frame; restate the drawer and overlay workspace bounds to the shipped geometry (covering the band and command-line row, above the band's lowest control strip).

## Impact

- Application-time edit surface: `OverlayHost.vue, HudDrawer.vue, GalleryPanel.vue header, AppClient.vue overlay title/icon mapping, shared DrawerHeader component and styles`.
- No application code, assets, generation, migrations, compatibility layers or main-spec edits are part of proposing this change.
- Source and report evidence, scope exclusions and runtime verification are in `design.md` and `tasks.md`.

## Batch:

depends-on: webclient-combat-command-window

Code-conflict notes: follow the serial UI chain in `../webclient-type-scale-tokens/review-plan.md`. Shared `AppClient.vue`, shell/token styles, component stories and main capability files make these integration conflicts even where runtime features are independent. ANSI and static-art preparation may run independently as that matrix states. Dependency means applied prerequisites, not a requirement to archive them.
