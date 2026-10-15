# Tasks

Scope: presentation only. `web/static/webclient/js/elosern/combat_menu.js`, `lib/combat_menu.js`, the keyboard
router, dispatch payloads, the server protocol and telnet stay untouched. Paths below are relative to the repository
root; webclient sources live under `web/webclient-app/`.

Testing rules (root `AGENTS.md` "Testing"): run only the focused commands listed here, capture every browser run's
output to a scratch file (e.g. `> "$SCRATCH/<name>.log" 2>&1`) and read the file instead of re-running, never loop
over browser files, never run CI shard commands or full suites. Before changing an existing assertion, note its role
and the defect it detects in the commit message body; replace a stale band-geometry assertion with the card-geometry
assertion that detects the same class of defect, never delete it outright. Obtain requirement IDs with
`uv run --locked python -m tools.spec_traceability list --json-output <scratch>/ids.json`; MODIFIED requirements
keep their IDs.

## 1. Stage: the card anchor, the Teleport and focus (≈2 h)

- [ ] 1.1 In `components/HudFrame.vue`: give the `choices` anchor an `id` from `useId()`; wrap the `band-command`
  slot in `<Teleport :to="'#' + choicesId" defer :disabled="mode !== 'combat'">` (design D1); show the `choices`
  anchor in combat (extend the `:not([data-elosern-mode="dialogue"]):not([data-card-open="true"])` gate); declare
  `--stage-open-left` / `--stage-open-right` on `.elosern-stage` and the combat `width`/`left` rule with its glide
  transition (design D3); collapse the band in combat (`.stage-band` one column, `band-command` `display:none`,
  design D2); stop setting `data-flip` for `*-combat` changes and delete the `-combat` flip-in rule (keep
  `combat-exploration`); add the `elosern-combat-card-in` keyframes and the entrance rule keyed on
  `[data-mode-change$="-combat"]` (design D6); set `--companion-compact-edge: var(--stage-open-left)` under
  `[data-elosern-mode="combat"]` (design D4). Update the header comment's anchor/band description. Add a comment
  beside the caption rule in `styles/app-shell.css` and beside the new properties that both copies of the open-span
  expression must stay in step. Verify with 1.3.
- [ ] 1.2 In `components/AppShell.vue`: after the flush of a mode change into combat, call `restoreFocusHome()` when
  `focusIsLost(document.activeElement)` (design D7); update the header comment (the preserved `#action-dock` now
  stands in the `choices` anchor in combat). Verify with 1.3.
- [ ] 1.3 Extend `web/webclient-app/tests/hud_frame.test.js` (mount `AppShell` with `attachTo`, as the file does):
  in combat the slot's root element is inside `[data-anchor="choices"]`, not inside `band-command`, and it is the
  same DOM node before and after exploration → combat → exploration and combat → dialogue; a mount directly in
  combat places it in the anchor; the CSS gate shows the anchor in combat; the combat anchor rule uses
  `--stage-open-left`/`--stage-open-right` with `min(400px * var(--ui-scale), …)` and `clamp(…)`; the band rule
  collapses `band-command` with `display: none` in combat; focus on a dock descendant before entering combat ends on
  `#action-dock` (not `document.body`) after `nextTick`. Update `web/webclient-app/tests/mode_transitions.test.js`:
  `data-flip` is not set for `exploration-combat`, still set for `combat-exploration`, and the card entrance rule is
  keyed on `[data-mode-change$="-combat"]` with `var(--motion-flash)` as its delay. Run
  `pnpm test -- web/webclient-app/tests/hud_frame.test.js web/webclient-app/tests/mode_transitions.test.js` and
  verify it passes.

## 2. The dock as a card, stacked detail (≈1.5 h)

- [ ] 2.1 In `components/ActionDock.vue` add the `card` prop (design D5): root classes
  `action-dock--card choice-card choice-card--still`, a decorative `choice-card__corners` span (`aria-hidden`),
  the scoped `::after` focus mark limited to `:not(.action-dock--card)`, the focused-frame brightening under
  `:has(:focus-visible)`, and the card sizing (`width: 100%; height: min(100%, calc(420px * var(--ui-scale)));
  max-width: none; margin: 0`). Update the header comment. In `AppClient.vue` pass
  `:card="store.view.mode === 'combat'"`. Verify with 2.3.
- [ ] 2.2 In `styles/app-shell.css` add the `.action-dock--card .dock-pane-host--bounded` column rules (row region
  `flex: 1 1 auto` with a three-row minimum; `.dock-detail` / `.skill-detail-pane` `flex: 0 1 auto; max-height: 50%;
  align-self: stretch`; both scroll) next to the existing bounded rules, unprefixed. Grep `app-shell.css` for
  `.elosern-root` rules on `action-dock`, `dock-menu`, `dock-detail`, `skill-detail-pane` and `choices`: move the
  `.elosern-root .skill-detail-pane*` typography rules into `components/SkillDetailPane.vue`'s scoped style (same
  values) and delete them from `app-shell.css`; leave the `[data-anchor="band-command"]` detail rules (exploration
  SkillUseDock). Verify with 2.3 and the Node gate in 2.4.
- [ ] 2.3 Extend `web/webclient-app/tests/action/action_dock.test.js`: with `card` the root carries the three
  classes and one `choice-card__corners` with `aria-hidden="true"`, the legend, breadcrumb and playback cue still
  render inside the root, and without `card` none of the card classes or corners render. Run
  `pnpm test -- web/webclient-app/tests/action/action_dock.test.js web/webclient-app/tests/action/skill_detail_pane.test.js web/webclient-app/tests/store/combat_command_window.test.js`
  and verify it passes (the last file is the unchanged store guard).
- [ ] 2.4 Run `node --test web/static/webclient/js/tests/ui_contract.test.js` (it scans `app-shell.css` and
  `AppClient.vue`) and verify it passes.

## 3. The party line-up stays left of the card (≈0.5 h)

- [ ] 3.1 In `components/CompanionLineup.vue` read the compact edge from `--companion-compact-edge` with today's
  `max(30vw, 50vw - 280px * var(--ui-scale))` as the fallback; in `AppClient.vue` pass `:compact` true in dialogue
  and in combat (design D4). Add a case to `web/webclient-app/tests/core/companion_lineup.test.js` asserting the
  compact rule reads `var(--companion-compact-edge, …)` and to `tests/hud_frame.test.js` asserting the combat stage
  sets it to `var(--stage-open-left)`. Run
  `pnpm test -- web/webclient-app/tests/core/companion_lineup.test.js web/webclient-app/tests/hud_frame.test.js` and
  verify it passes.

## 4. Live-client browser verification (≈2.5 h)

Build the bundle once first: `pnpm run build`. Each bullet is one short command with output captured to a scratch
file.

- [ ] 4.1 Add `test_combat_command_card_stands_centred_over_the_stage` to
  `web/tests/browser/test_browser_combat_stage.py` `CombatStageBrowserTest` (reuse `_combat_panels(count)`, the
  `_COMMIT_AND_READ` pattern and `_party_panel(4)` from `test_browser_shell_surfaces.py`; read `#action-dock`,
  the `choices` anchor, the player's stage actor, every foe slot, every `companion-figure`, the `vitals`/`map`/
  command-line anchors, the scene caption plate and `band-command`): at 1451x790 and 2560x1440, with one foe the
  card's centre is the stage centre (±1px) and its width is `400 × ui_scale` (±1px); with three foes (and with the
  attack target frame open via the store's router keys) the card lies within the open span (16px·S gutters) and
  intersects no foe slot, foe gauge, player actor, `vitals`, `map` or command-line anchor; with four companions and
  three foes no companion box extends right of the controlled figure's standard box and none intersects the card;
  `band-command` is `display:none` and the message region spans the band; the card box is identical (±1px) across
  root → Skills → category → skill frame. Annotate it with the existing IDs it establishes
  (`webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode`,
  `webclient-contextual-hud::the-action-dock-fills-the-band-s-command-region-at-a-fixed-size`,
  `webclient-contextual-hud::companion-standing-portraits-line-up-behind-the-controlled-character-in-the-actor-left-anchor`;
  confirm spellings with `list`). Register the method in `.github/browser-shards.json` in the same shard list as
  `CombatStageBrowserTest.test_foes_stand_opposite_the_player`. Run
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_combat_stage.CombatStageBrowserTest.test_combat_command_card_stands_centred_over_the_stage web.tests.browser.test_browser_combat_stage.CombatStageBrowserTest.test_foes_stand_opposite_the_player`
  and verify both pass.
- [ ] 4.2 Update `web/tests/browser/test_browser_combat_menu.py`
  `CombatMenuBrowserTest.test_dock_and_participant_frame_geometry_at_both_desktop_viewports`: the dock lies inside
  `[data-anchor="choices"]` (not `anchor-band-command`) and inside the viewport; keep the participant-frame and
  confirm-control assertions. Run
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_combat_menu.CombatMenuBrowserTest.test_dock_and_participant_frame_geometry_at_both_desktop_viewports web.tests.browser.test_browser_combat_menu.CombatMenuBrowserTest.test_focus_stays_on_action_dock_in_combat web.tests.browser.test_browser_combat_menu.CombatMenuBrowserTest.test_crumb_absent_at_depth_one_present_at_depth_two_and_back_pops_one_level web.tests.browser.test_browser_combat_menu.CombatMenuBrowserTest.test_pointer_root_row_click_activates_once`
  and verify all pass.
- [ ] 4.3 Update `web/tests/browser/test_browser_mode_transitions.py`: the reader takes the dock animations from
  `#action-dock` (wherever it stands) and reports whether it is inside the `choices` anchor and the active element;
  `test_combat_enter_and_leave_full` expects `elosern-combat-card-in` (250ms, 120ms delay) on entry with the dock in
  the anchor and focus not on `body`, and `elosern-panel-flip-out` on leaving with the dock back in `band-command`;
  `test_reload_in_combat_plays_nothing` expects no dock animation; `test_mode_transitions_reduced` expects the card
  entrance ≤150ms with 0s delay; `test_mode_transitions_off` expects the card at rest. Run
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_mode_transitions.ModeTransitionsBrowserTest.test_combat_enter_and_leave_full web.tests.browser.test_browser_mode_transitions.ModeTransitionsBrowserTest.test_reload_in_combat_plays_nothing web.tests.browser.test_browser_mode_transitions.ModeTransitionsBrowserTest.test_mode_transitions_reduced web.tests.browser.test_browser_mode_transitions.ModeTransitionsBrowserTest.test_mode_transitions_off web.tests.browser.test_browser_mode_transitions.ModeTransitionsBrowserTest.test_no_stage_ancestor_scrolls_horizontally_full`
  and verify all pass.
- [ ] 4.4 Update `web/tests/browser/test_browser_contextual_hud_stage.py`
  `ContextualHudBrowserTest.test_band_height_is_fixed_across_frames_and_modes`: the combat states assert the band
  box unchanged, the message region spanning the band and `band-command` `display:none` (instead of the
  exploration boxes). Run
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_contextual_hud_stage.ContextualHudBrowserTest.test_band_height_is_fixed_across_frames_and_modes web.tests.browser.test_browser_contextual_hud_stage.ContextualHudBrowserTest.test_surface_visibility_gated_by_committed_game_mode`
  and verify both pass.
- [ ] 4.5 Run the unchanged behaviour guards (update only comments that say "list left, detail right"):
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_contextual_hud_dock.ContextualHudBrowserTest.test_action_dock_fills_the_band_command_region_across_modes web.tests.browser.test_browser_contextual_hud_dock.ContextualHudBrowserTest.test_combat_dock_root_vertical_list_truthful_skills_count web.tests.browser.test_browser_contextual_hud_dock.ContextualHudBrowserTest.test_digit_keys_pick_the_rows_of_the_current_frame`,
  then
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_contextual_hud_combat.ContextualHudBrowserTest.test_command_window_scrolls_its_rows_and_details_the_current_frame web.tests.browser.test_browser_contextual_hud_combat.ContextualHudBrowserTest.test_combat_skills_bounded_master_detail web.tests.browser.test_browser_contextual_hud_combat.ContextualHudBrowserTest.test_destructive_combat_confirmation_two_step_panel`,
  then
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_combat_scales.CombatMenuBrowserTest.test_combat_dock_renders_mockup_grid_and_detail_at_both_viewports web.tests.browser.test_browser_combat_scales.CombatMenuBrowserTest.test_master_scale_step_casts_at_the_chosen_magnitude web.tests.browser.test_browser_combat_scales.CombatMenuBrowserTest.test_area_space_selects_once_even_when_held`,
  then
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_combat_beats.CombatBeatsBrowserTest.test_round_plays_and_skips_reduced`,
  and verify every method passes.

## 5. Storybook (≈1 h)

- [ ] 5.1 `stories/Core/AppShell.stories.js`: add a `combatKeys` arg replayed through `store.focusPress(key, false)`
  after the snapshot commits; add `CombatTargetStep`, `CombatSkillDetail`, `CombatDisabledCommand`,
  `CombatMasterScale` (a skill with `freeform_scales`, following `stories/fixtures/skills.js`) and
  `CombatFullParty` (`populated`, four companions, three foes); keep the existing combat stories. Update the file's
  combat comments (card, not band).
- [ ] 5.2 `stories/Action/ActionDock.stories.js`: render the combat stories with `card: true` in a 400×414 host and
  the stacked pane host; add `CombatTargets` and `CombatMasterScale` (with `SkillDetailPane` beside `DockMenu`
  under the host); `CombatPlayback` shows the cue inside the card. `stories/Action/DockMenu.stories.js`: render
  `TargetFrame` and `FixedGridFrame` in a 400px-wide host.
- [ ] 5.3 Run `pnpm run build-storybook` then `pnpm run showcase-coverage` and verify both succeed with
  `component-manifest.json` unchanged; then run
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_proportional_ui_scale.ProportionalUiScaleBrowserTest.test_resize_keeps_pointer_targets_live`
  (it clicks 攻擊 and a foe row in `core-appshell--combat-participant-polish`) and verify it passes. Open
  `core-appshell--combat-hud`, `--combat-one-foe`, `--combat-full-party` and `--dialogue-selector` at 1600x900 in
  the built Storybook and confirm by screenshot that the combat card sits over the stage centre clear of the foes.

## 6. Documentation (≈0.25 h)

- [ ] 6.1 Amend `web/webclient-app/AGENTS.md` "Layout" (bottom band = message window 2/3 + command panel 1/3
  outside combat; in combat the command menu is a centred card in the `choices` anchor and the message window spans
  the band) and the combat lines of `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md`
  (surface table "Command panel" combat cell, the anchors paragraph and the `ActionDock + DockMenu` component row).
  Verify by `grep -n "bottom-right\|band-command" web/webclient-app/AGENTS.md` showing no combat claim of the
  bottom-right panel.

## 7. Gates (≈0.5 h)

- [ ] 7.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate`,
  and, with a file containing `MUD_TEST_SETTINGS=1` passed as `--env-file=<file>`,
  `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract`;
  then `openspec validate webclient-combat-command-card-centred --strict`. Verify all pass.

## Workflow follow-up

- At archive, after the delta sync, obtain the new ID of "The combat command card stands centred over the stage"
  with `uv run --locked python -m tools.spec_traceability list` and add it to
  `CombatStageBrowserTest.test_combat_command_card_stands_centred_over_the_stage` (and to
  `ModeTransitionsBrowserTest.test_combat_enter_and_leave_full` for the entrance scenarios) before running
  `tools.spec_traceability check` and `tools.contract_gate` again.
- Re-run `tests.test_evennia_test_optimization_contract` right before merge if `.github/browser-shards.json` changed
  on master meanwhile.
