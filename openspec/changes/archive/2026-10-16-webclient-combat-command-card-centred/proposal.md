# Proposal: Centre a narrow combat command card over the stage

## Why

During combat the command menu (攻擊／技能／道具／背包／防禦…, its detail, breadcrumb, shortcut legend and the
playback cue) sits in the bottom band's right third. Every other decision on the stage (the dialogue choice list,
the wait and suggestions cards, a person's verb card) is a centred card in the stage's `choices` anchor. The user
asked for the combat menu to move to the true centre of the stage, in a narrow card. `webclient-combat-formation`
now keeps a dead-centre gap clear for it at every party size and foe count.

## What Changes

- In combat, the existing `#action-dock` element (the same mounted node, never remounted) is presented as a
  **combat command card** inside the stage's `choices` anchor, framed with the shared ChoiceCard shell.
- **Geometry.**
  - The card is `264px·S` wide and centred on the stage centre in every case (no clamp or shift).
  - It is top-anchored in the `choices` anchor at `min(400px·S, anchor span)` height, and no frame resizes it.
  - The formation's gap (`264px·S + 2 × 16px·S`) guarantees it never covers a figure, plate or target marker.
- **Narrow layout.**
  - Every list frame is one column.
  - The detail folds into a fixed three-line strip under the rows.
  - The breadcrumb is one line that keeps the back control and the current frame.
  - The legend may wrap.
  - AREA tokens keep two columns and the scale step one column per scale; the keyboard cell mappings are unchanged.
- In combat the bottom band's command region collapses (`display:none`) and the message window spans the band.
- Combat entry:
  - the card fades in (rising at `full`) as the flash releases;
  - leaving combat keeps the band dock's flip-back;
  - mount, reload and reconnect render the card at rest;
  - focus that the move drops is re-homed.
- Unchanged: the combat menu model, the keyboard router and hierarchy, the digit picks, Escape/back, the dispatch
  payloads, the protocol, telnet, the exploration dock, `SkillUseDock` and the dialogue list. Target choice stays in
  the card's target frame until `webclient-combat-stage-target-picking`.
- Storybook: the combat card variants. No component is added.
- `web/webclient-app/AGENTS.md` and the AVG stage redesign doc stop describing the command panel as bottom-right in
  combat.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`:
  - adds "The combat command card stands at the stage's dead centre";
  - amends the stage-anchor, visibility-matrix, dock-placement, fixed-column pane, bounded master-detail,
    mode-transition, bottom-band and playback-cue requirements.
- `webclient-desktop-shell`: amends "Required desktop surfaces remain visible and usable" and the pane-host
  direct-children requirement (the detail strip below the rows in the card).

## Impact

- Code:
  - `components/HudFrame.vue`: the choices anchor in combat, the fixed card geometry, the band collapse, the Teleport
    of the band-command slot, the card entrance.
  - `components/AppShell.vue`: focus re-home.
  - `components/ActionDock.vue`: the `card` presentation.
  - `components/DockMenu.vue` and `components/SkillDetailPane.vue`: the `strip` variant.
  - `AppClient.vue`: passes `card`.
  - `styles/app-shell.css`: the card pane host; the `.elosern-root .skill-detail-pane*` duplicates move into
    `SkillDetailPane.vue`.
- Tests: focused Vitest, the Node gate, one new browser method (registered in `.github/browser-shards.json`), updated
  combat browser methods, and unchanged-behaviour guards.
- No server, protocol, data, telnet or player-command change.

## Batch: webclient combat stage

Final apply/archive order:

1. `webclient-combat-panel-v6`
2. `webclient-combat-formation-engine`
3. `webclient-combat-formation`
4. `webclient-combat-figure-plates`
5. `webclient-combat-defeated-foes`
6. `webclient-combat-command-card-centred`
7. `webclient-combat-stage-target-picking`
8. `webclient-combat-cross-side-confirm`

- depends-on: webclient-combat-formation
- depends-on: webclient-combat-defeated-foes
- Code conflicts and spec chaining:
  - Its MODIFIED blocks of the full-bleed stage and the visibility matrix are written on top of
    `webclient-combat-formation` and `webclient-combat-defeated-foes`.
  - It shares `HudFrame.vue`, `AppClient.vue` and the AppShell stories with them.
  - `webclient-combat-stage-target-picking` builds on this change's requirement and blocks.
