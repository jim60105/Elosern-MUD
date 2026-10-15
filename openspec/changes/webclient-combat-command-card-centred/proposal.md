# Proposal: Centre a narrow combat command card over the stage

## Why

During combat the command menu (攻擊／技能／道具／背包／防禦…, its detail, breadcrumb, shortcut legend and the
playback cue) sits in the bottom band's right third, while every other decision the player makes on the stage
(the dialogue choice list, the wait and suggestions cards, a person's verb card) is a centred card in the stage's
`choices` anchor. The player's eye has to jump to the bottom-right corner only in combat. The user asked to move
the combat menu to the centre of the stage, in the same place as the other option windows, and decided that:

- the card stands at the stage's true dead centre in every case (no shifting left of centre with more foes);
- the party line-up is not compressed to make room; the card is made narrower instead, and its internal layout
  is redesigned for a narrow window.

## What Changes

- In combat mode the existing `#action-dock` element (the same mounted node, never remounted) is presented as a
  **combat command card** inside the stage's `choices` anchor, framed with the shared ChoiceCard shell (gold
  frame, crest, corner brackets, focused-frame brightening).
- **Geometry.** The card's horizontal centre is the stage centre in every case. Its width is
  `clamp(240px·S, 2 × (stage centre − party edge − 16px·S), 280px·S)`, where the party edge is the controlled
  figure's right edge as the (uncompressed) companion line-up places it for the committed party size. Its top is
  the `choices` anchor's top; its bottom stands 8px·S above the foe name-plate line; its height is
  `min(400px·S, that span)` and never changes between frames. It never covers a foe name plate, gauge or
  focused-target cue; with two or more foes it stands over part of the rear foe's box — a deviation from the
  user's "only empty floor" rule that is physically forced at dead centre and **needs the user's sign-off before
  apply** (design D3 and Open Questions).
- **Narrow layout.** Every list frame is one column; the detail folds into a fixed three-line strip under the
  rows (cost and target requirement, then the description or the disabled reason, full text kept as the focused
  row's accessible description); the breadcrumb is one line that keeps the back control and the current frame
  visible; the legend keeps its text and may wrap at its separators. AREA tokens keep two columns and the scale
  step one column per scale; keyboard cell mappings are unchanged.
- In combat the bottom band's command region collapses (`display:none`) and the message window spans the band;
  the band returns to its two-thirds/one-third split when combat ends.
- Combat entry: the flash and the foe slide-in are unchanged; the card fades in (and rises at `full`) at the
  flash's release instead of the old command-region flip. Leaving combat keeps the existing flip-back of the band
  dock. Mount, reload and reconnect render the card at rest. Focus that the move drops is re-homed to
  `#action-dock` (combat) or the exit compass (exploration).
- The companion line-up is unchanged (no combat compaction).
- Unchanged: the combat menu model (`web/static/webclient/js/elosern/combat_menu.js`), the keyboard router and
  hierarchy, digit picks, Escape/back, dispatch payloads, the server protocol, telnet, the exploration dock, the
  SkillBook casting dock (`SkillUseDock`) and the dialogue choice list. Target choice stays in the card's target
  frame in this change; `webclient-combat-stage-target-picking` moves it onto the stage.
- Storybook: `Core/AppShell` combat stories show the centred card; new stories cover the party/foe matrix, the
  target step, a disabled command, playback and the master scale step; `Action/ActionDock` combat stories render
  the card variant at 240px and 280px. No component is added, so `component-manifest.json` is unchanged.
- `web/webclient-app/AGENTS.md` and the AVG stage redesign doc stop describing the command panel as bottom-right
  in combat.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: adds "The combat command card stands at the stage's dead centre"; amends the
  stage-anchor, visibility-matrix, dock-placement, fixed-column pane, bounded master-detail, mode-transition,
  bottom-band and playback-cue requirements so combat no longer places the dock in the band's command region.
- `webclient-desktop-shell`: amends "Required desktop surfaces remain visible and usable" and the pane-host
  direct-children requirement (the detail is a strip below the rows inside the combat card).

## Impact

- Code: `web/webclient-app/components/HudFrame.vue` (choices anchor in combat, card geometry, band collapse,
  Teleport of the band-command slot, card entrance), `components/AppShell.vue` (focus re-home on entering
  combat), `components/ActionDock.vue` (`card` presentation, one-line breadcrumb, legend wrap),
  `components/DockMenu.vue` and `components/SkillDetailPane.vue` (`strip` detail variant), `components/FoeLineup.vue`
  and `styles/tokens.css` (shared `--foe-plate-h` / `--foe-plate-rise` tokens), `AppClient.vue` (passes `card`,
  writes `--party-reach`), `styles/app-shell.css` (card pane host; `.elosern-root .skill-detail-pane*` duplicates
  moved into `SkillDetailPane.vue`).
- Tests: focused Vitest files, the Node gate `web/static/webclient/js/tests/ui_contract.test.js`, one new browser
  method in `test_browser_combat_stage.py` (registered in `.github/browser-shards.json`), updated combat browser
  methods, and unchanged-behaviour guards. No new non-browser module.
- Stories: `stories/Core/AppShell.stories.js`, `stories/Action/ActionDock.stories.js`,
  `stories/Action/DockMenu.stories.js`, `stories/Action/SkillDetailPane.stories.js`.
- No server, protocol, data, telnet or player-command change.

## Batch: webclient combat card and stage targeting

This change is the first of three, applied and archived in this order.

- depends-on: none
- followed by: `webclient-combat-stage-target-picking` (depends on this change),
  `webclient-combat-cross-side-confirm` (depends on `webclient-combat-stage-target-picking`).
- Code conflicts: `webclient-combat-stage-target-picking` edits the same `ActionDock.vue`, `HudFrame.vue`,
  `AppClient.vue`, `FoeLineup.vue`, `stories/Core/AppShell.stories.js` and `stories/Action/ActionDock.stories.js`,
  and its delta MODIFIES "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces" on top of
  this change's version. Apply and archive this change first; never run the two in parallel.
