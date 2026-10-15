# Proposal: Centre the combat command menu over the stage

## Why

During combat the command menu (攻擊／技能／道具／背包／防禦…, its detail card, breadcrumb, shortcut legend and the
playback cue) sits in the bottom band's right third, while every other decision the player makes on the stage
(the dialogue choice list, the wait and suggestions cards, a person's verb card) is a centred card in the stage's
`choices` anchor. The player's eye has to jump to the bottom-right corner only in combat. The user asked to move
the combat menu to the centre of the scene stage, in the same place as the other option windows, using the
dialogue choice window as the reference.

## What Changes

- In combat mode the existing `#action-dock` element (the same mounted node, never remounted) is presented as a
  **combat command card** inside the stage's `choices` anchor, framed with the shared ChoiceCard shell (gold
  frame, crest, corner brackets, focused-frame brightening). It keeps its breadcrumb, row region, detail region,
  playback waiting cue with 跳過演出, and the single shortcut legend.
- The card is horizontally centred on the stage's centre line whenever the open stage span between the player's
  stage actor and the foe line-up allows it, and otherwise shifts and narrows just enough to stay inside that span,
  so no foe, foe name/gauge, focused-target cue, the player's figure, the vitals dock, the participant frame or the
  scene caption is ever covered. Its width is at most `400px × S` and its height is fixed at
  `min(420px × S, the anchor span)` so no frame resizes it.
- In combat the companion line-up uses the compact layout dialogue already uses, clamped so no party figure stands
  right of the controlled figure's standard position; the card therefore never covers the party.
- Inside the card the detail region stacks below the row region (instead of beside it); the combat master-detail,
  the scale (威力) step, target step, disabled reasons and Forfeit confirmation keep their behaviour.
- In combat the bottom band's command region collapses (as in dialogue) and the message window spans the whole
  band; the band returns to its two-thirds/one-third split when combat ends.
- Combat entry: the flash and the foe slide-in are unchanged; the card fades in (and rises at `full`) at the
  flash's release instead of the old command-region flip. Leaving combat keeps the existing flip-back of the band
  dock. Mount, reload and reconnect render the card at rest. Focus that the move drops is re-homed to
  `#action-dock` (combat) or the exit compass (exploration).
- Unchanged: the combat menu model (`web/static/webclient/js/elosern/combat_menu.js`), the keyboard router and
  hierarchy, digit picks, Escape/back, dispatch payloads, the server protocol, telnet, the exploration dock, the
  SkillBook casting dock (`SkillUseDock`) and the dialogue choice list.
- Storybook: the `Core/AppShell` combat stories show the centred card, new AppShell stories cover the target
  step, a disabled command, playback and the master scale step, and the `Action/ActionDock` combat stories render
  the card variant (plus target and master-scale stories). No component is added, so the frozen
  `component-manifest.json` is unchanged.
- `web/webclient-app/AGENTS.md` and the AVG stage redesign doc stop describing the command panel as bottom-right
  in combat.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: adds the combat command card requirement; amends the stage-anchor, visibility-matrix,
  dock-placement, fixed-column pane, bounded master-detail, mode-transition, bottom-band, playback-cue and
  companion line-up requirements so combat no longer places the dock in the band's command region and the party
  compresses clear of the card.
- `webclient-desktop-shell`: amends "Required desktop surfaces remain visible and usable" and the pane-host
  direct-children requirement (the detail stacks below the rows inside the combat card).

## Impact

- Code: `web/webclient-app/components/HudFrame.vue` (choices anchor in combat, combat card geometry, band collapse,
  Teleport of the band-command slot, card entrance), `components/AppShell.vue` (focus re-home on entering
  combat), `components/ActionDock.vue` (`card` presentation), `components/CompanionLineup.vue` (compact edge),
  `AppClient.vue` (passes `card`, compact in combat),
  `styles/app-shell.css` (stacked pane host inside the card; `.elosern-root .skill-detail-pane*` duplicates moved
  into `SkillDetailPane.vue`).
- Tests: focused Vitest files (`tests/action/action_dock.test.js`, `tests/hud_frame.test.js`,
  `tests/mode_transitions.test.js`, `tests/core/companion_lineup.test.js`), the Node gate file
  `web/static/webclient/js/tests/ui_contract.test.js`, one new browser method in `test_browser_combat_stage.py`
  (registered in `.github/browser-shards.json`) and the combat-related browser methods in
  `test_browser_combat_menu.py`, `test_browser_mode_transitions.py` and `test_browser_contextual_hud_stage.py`,
  plus unchanged-behaviour guards. No new non-browser module, so `.github/evennia-shards.json` is unchanged.
- Stories: `stories/Core/AppShell.stories.js`, `stories/Action/ActionDock.stories.js`,
  `stories/Action/DockMenu.stories.js`.
- No server, protocol, data, telnet or player-command change; command docs are unchanged.
