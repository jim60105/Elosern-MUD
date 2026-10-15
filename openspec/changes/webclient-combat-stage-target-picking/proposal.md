# Proposal: Pick combat targets on the stage figures

## Why

After `webclient-combat-command-card-centred` the combat command menu is a narrow card at the stage's dead centre,
but choosing a target still means reading a list of names inside that card while the figures the names refer to
stand beside it. The user asked to pick targets on the stage itself: the stage darkens like a dialogue's listeners,
an arrow marks every figure the action may target, and the focused one is lit and pulses.

## What Changes

- **Stage target step.** While the current frame is the target frame of an enabled SINGLE, SELF or AREA skill
  (Attack included), the card collapses to a one- or two-line **target prompt** (action, 選擇目標, the focused
  target and side or group and size, `Esc 返回`; AREA adds group/confirm chips) and the targets are chosen on the
  stage. NONE and disabled-skill frames keep their card rows.
- **Presentation.** Every stage figure (controlled figure, companions, foes) takes the existing dialogue listener dim
  (`StageActor`'s `dimmed` → `data-speaking="false"`, `--actor-dim`), except the focused position's lit set. An arrow
  marker stands above each selectable figure (filled and larger when focused, outlined otherwise, with the item's
  digit; a check for an AREA member already selected). The lit figure pulses at `full`; at `reduced`/`off`/OS
  reduced motion it carries a static brighter ring plus an underline under the arrow. A polite live region in the
  card announces the focused target, its side, and a group's size.
- **Positions per real TargetSpec.** SINGLE: one per candidate. SELF: one, on the controlled figure. AREA: one per
  candidate (Space/Enter toggle), one per approved shorthand (`all-enemies`, `all-allies`, `all`; the whole group
  lit, focus moves between groups, never members), then the confirm position (lit = the current selection). There
  is no area-centre form in the TargetSpec, so none is presented. Candidates no figure draws (a fourth/fifth foe, a
  knocked-out foe, an undrawn party participant) are off-stage positions cued on the participant frame row.
- **Input.** Arrow keys move the frame's focus in stage order (Right/Down next, Left/Up previous, wrapping)
  through the router's existing `focusItemByKey`; Enter, Space, the digits (server order) and Escape keep their
  meaning; pointer hover focuses and click activates through the router's confirm. The UMD combat menu model, the
  keyboard router source, item order, dispatch payloads and the protocol are unchanged.
- **Reconnect/replacement.** A target step present at mount, reload, reconnect or panel replacement renders at rest;
  the existing selection repair drives the lit set; playback suspends the step.
- Storybook stories for every form (single, AoE explicit, AoE whole group, all-allies, all-foes, self,
  off-stage, reduced motion) on `Core/AppShell`, plus `Core/FoeLineup` and `Core/CompanionLineup` targeting stories.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-combat-menu`: adds "Combat targets are picked on the stage figures"; amends "The combat action dock
  follows the approved keyboard hierarchy" (target frames are chosen on the stage; the participant frame scenario).
- `webclient-contextual-hud`: adds "The stage target step presents the targets on the stage figures"; amends "The
  combat command card stands at the stage's dead centre" (collapse in the step; the arrow-key claim), "The WebClient
  renders a full-bleed cinematic stage with anchored HUD surfaces" (pointer hit areas during the step), "Foes stand
  opposite the player during combat", "The combat participant frame presents the session's participants and their
  portraits" and "Companion standing portraits line up behind the controlled character in the actor-left anchor".

## Impact

- Code (all under `web/webclient-app/`): new pure module `stores/elosern/stage_targets.js` (positions, stage order,
  lit sets, announcement text); `stores/elosern/interaction.js` (arrow claim in `focusPress`); `stores/elosern/view.js`
  (`view.stageTarget`); `stores/elosern/combat.js` (pointer focus/activate entry); `AppClient.vue` (props to the
  line-ups, the participant frame and the dock); `components/FoeLineup.vue`, `components/CompanionLineup.vue`
  (lit set, markers, hit areas; `StageActor.vue` is reused unchanged); `components/ParticipantFrame.vue`
  (`data-target-cue`); `components/ActionDock.vue` (target prompt, live region); `components/HudFrame.vue` (the
  collapsed card height); `styles/tokens.css` (marker and pulse tokens).
- Tests: a new Vitest file `tests/store/stage_target_step.test.js`, extended component tests, two new browser
  methods (registered in `.github/browser-shards.json`) and updates to the browser methods that click or read the
  in-card target rows.
- No server, protocol, data, telnet or player-command change.

## Batch: webclient combat card and stage targeting

- depends-on: webclient-combat-command-card-centred
- followed by: `webclient-combat-cross-side-confirm` (depends on this change).
- Code conflicts: with `webclient-combat-command-card-centred` — `ActionDock.vue`, `HudFrame.vue`, `AppClient.vue`,
  `FoeLineup.vue`, `CompanionLineup.vue`, `stories/Core/AppShell.stories.js`, `stories/Action/ActionDock.stories.js`;
  this change's MODIFIED blocks for "The combat command card stands at the stage's dead centre" and "The WebClient
  renders a full-bleed cinematic stage…" are written on top of that change's versions, so it must be archived
  first. With `webclient-combat-cross-side-confirm` — it reads this change's
  `stores/elosern/stage_targets.js` and `view.stageTarget`, and edits `AppClient.vue`, `components/ActionDock.vue` and
  `stories/Core/AppShell.stories.js`. Apply strictly in order.
