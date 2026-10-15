# Tasks

Prerequisites: `webclient-combat-figure-plates`, `webclient-combat-defeated-foes` and
`webclient-combat-command-card-centred` are archived (this change's deltas MODIFY their requirements). Mind the
Styling pitfall in `web/webclient-app/AGENTS.md`. Scope: presentation and input routing only — `web/static/webclient/js/elosern/combat_menu.js`, the
keyboard router source, item order, dispatch payloads, the protocol and telnet stay untouched. Paths are relative to
`web/webclient-app/` unless they start with `web/` or `.github/`.

Testing rules (root `AGENTS.md` "Testing"): focused commands only, browser output captured to a scratch file and read
from there, no loops over browser files, no CI shard commands. Before changing an existing assertion, record its
role and the defect it detects in the commit body and replace it with the stage-target assertion that detects the
same class of defect.

## 1. The step model and the arrow claim (≈2.5 h)

- [ ] 1.1 Create `stores/elosern/stage_targets.js` with `stageTargetModel(...)` and its helpers (design D1): step
  detection, positions per form, stage order from the formation's `formationOrder` (design D1), undrawn (fled) members, group and confirm
  positions, lit/selectable/selected sets, digits, and the announcement strings. AppClient publishes `formationOrder` from the `formation` object to the store.
- [ ] 1.2 In `stores/elosern/view.js` publish `stageTarget` (null outside a step or while `beatLocked()`); in
  `stores/elosern/interaction.js` claim the four arrow keys in `focusPress` while `stageTarget` is non-null
  (design D2); in `stores/elosern/combat.js` add `stageTargetPointer(key, action)` (design D5).
- [ ] 1.3 Add `tests/store/stage_target_step.test.js` with fixed panels: SINGLE (ally + two foes; positions in stage
  order; Right/Down/Left/Up wrap; Attack opens on the first foe; Enter emits one `combat.cast` byte-identical to the
  card-row payload); SELF (one position on the controlled identity; arrows no-op; payload has no target field); AREA
  (members then `shorthand-*` then `area-confirm`; Space toggles; group lit sets for `all-enemies`, `all-allies`,
  `all`; confirm lit = selection, then = chosen shorthand; payloads unchanged); NONE and a disabled skill (no step,
  arrows reach the router); a knocked-out foe and a knocked-out companion candidate on stage with their fallen look; a listed
  fled participant as the only undrawn position; a panel replacement removing the focused candidate (focus repaired, lit set follows);
  `beatLocked` (null model, arrows unclaimed); digits still address server order; an arrow from a back-row focus goes to the first/last position; the exact
  announcement templates (and the token suffix for duplicate names) for member,
  ally, off-stage, group and confirm. Run `pnpm test -- web/webclient-app/tests/store/stage_target_step.test.js
  web/webclient-app/tests/store/combat_command_window.test.js web/webclient-app/tests/store/digit_row_picks.test.js`
  and verify it passes.

## 2. Figures, markers and prompt (≈2.5 h)

- [ ] 2.1 `components/FoeLineup.vue` and `components/CompanionLineup.vue`: the `targeting` prop, the dim expression
  through StageActor's `dimmed`, the marker and hit-area elements, `data-target-focus`, the pulse keyframes and the
  reduced/off/`prefers-reduced-motion` static ring and underline (design D4); marker/pulse tokens in
  `styles/tokens.css`. `StageActor.vue` stays unchanged.
- [ ] 2.2 `components/HudFrame.vue` plates layer: render the markers at the formation marker slots (design D4); AppClient
  bumps `plateTooltipClose` when a step starts.
- [ ] 2.3 `components/ActionDock.vue`: the target prompt, the hidden row region, the focus move to `#action-dock`,
  the AREA chips and the polite live region (design D3); `components/HudFrame.vue`: the step's `height: auto;
  max-height: 136px·S` card rule; chips are `tabindex="-1"` buttons that return DOM focus to `#action-dock`. `AppClient.vue`: pass `targeting`/`stageTarget` from
  `store.view.stageTarget` and wire the hit areas and chips to `stageTargetPointer`.
- [ ] 2.4 Extend `tests/core/foe_lineup.test.js` and `tests/core/companion_lineup.test.js` (lit vs dimmed
  `data-speaking`, markers only on selectable slots with the right `data-state`, digit and ✓, hit areas only while
  `targeting` is non-null, no box/z change, the reduced-motion rule present), `tests/action/action_dock.test.js`
  (prompt content per form, hidden row region, live-region text, chips emit the pointer entry) and `tests/core/figure_plate.test.js` (plates never dimmed in a step). Run
  `pnpm test -- web/webclient-app/tests/core/foe_lineup.test.js web/webclient-app/tests/core/companion_lineup.test.js web/webclient-app/tests/action/action_dock.test.js
  web/webclient-app/tests/core/figure_plate.test.js`, and verify they pass.

## 3. Live-client browser verification (≈2 h)

Build once: `pnpm run build`.

- [ ] 3.1 Add to `web/tests/browser/test_browser_combat_stage.py` `CombatStageBrowserTest`:
  `test_targets_are_picked_on_the_stage` (1451x790 and 1600x900; four-figure party, three foes; Attack: the card
  collapses to ≤ 136px·S at the same centre/width/top and intersects no marker (also with an AREA skill's chips); every non-focused figure has
  `data-speaking="false"`, the focused foe `"true"`; markers only on candidates; the member order by marker `left`
  equals the stage order; ArrowLeft/Right move along it; a pointer click on a foe hit area sends exactly one
  `combat.cast` equal to the keyboard payload; Escape restores every figure's `data-speaking` to a snapshot taken before the step and removes every marker;
  an AREA chip click followed by ArrowRight and Enter activates the focused position, not the chip) and
  `test_area_targets_light_groups_on_the_stage` (an AREA skill: Space selects two foes with ✓ markers; the
  `all-allies` position lights every party candidate; confirm sends `target_shorthand`; under `reduced` motion the
  focused figure's computed `animation-name` is `none` and the underline is present; a knocked-out foe candidate shows its
  fallen look plus the arrow; starting a step closes an open plate tooltip). Annotate both with existing IDs they establish (confirm spellings with
  `uv run --locked python -m tools.spec_traceability list`). Register both in `.github/browser-shards.json` beside
  `CombatStageBrowserTest.test_foes_stand_opposite_the_player`. Run
  `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_combat_stage.CombatStageBrowserTest.test_targets_are_picked_on_the_stage web.tests.browser.test_browser_combat_stage.CombatStageBrowserTest.test_area_targets_light_groups_on_the_stage`
  and verify both pass.
- [ ] 3.2 Migrate the methods that click or read the in-card target rows. Find them with
  `grep -n "target-\|area-\|shorthand-\|self-confirm" web/tests/browser/test_browser_combat_menu.py web/tests/browser/test_browser_combat_panels.py web/tests/browser/test_browser_combat_scales.py web/tests/browser/test_browser_combat_skills.py web/tests/browser/test_browser_contextual_hud_dock.py web/tests/browser/test_browser_pointer.py web/tests/browser/test_browser_proportional_ui_scale.py`;
  keyboard paths stay valid (items unchanged), pointer clicks on target rows move to `stage-target-hit` or prompt
  chips, and row-DOM assertions in a target frame move to markers/lit state. Run, one file per command:
  `…test_browser_combat_menu.CombatMenuBrowserTest.test_attack_flow_submits_basic_attack_once …test_single_skill_target_flow …test_self_skill_submits_no_target_field …test_skill_frame_refreshes_on_panel_update`,
  `…test_browser_combat_panels.CombatMenuBrowserTest.test_area_explicit_multi_selection …test_combat_renders_at_minimum_viewport`,
  `…test_browser_combat_scales.CombatMenuBrowserTest.test_area_space_selects_once_even_when_held …test_master_scale_step_casts_at_the_chosen_magnitude …test_combat_dock_renders_mockup_grid_and_detail_at_both_viewports`,
  `…test_browser_contextual_hud_dock.ContextualHudBrowserTest.test_digit_keys_pick_the_rows_of_the_current_frame`,
  `…test_browser_proportional_ui_scale.ProportionalUiScaleBrowserTest.test_resize_keeps_pointer_targets_live`,
  plus every other method the grep names (each prefixed `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.`),
  and verify all pass.

## 4. Storybook (≈0.75 h)

- [ ] 4.1 Add the fixtures and the stories of design D7 (`Core/AppShell` eight target stories; `Core/FoeLineup` and
  `Core/CompanionLineup` `Targeting`). Run `pnpm run build-storybook` then `pnpm run showcase-coverage` and verify
  both succeed with `component-manifest.json` unchanged; screenshot `core-appshell--target-single-foe`,
  `--target-area-all-foes` and `--target-reduced-motion` at 1451x790 and confirm the dim, markers and prompt.

## 5. Documentation and gates (≈0.5 h)

- [ ] 5.1 Add the stage target step to `web/webclient-app/AGENTS.md` (combat section: targets are picked on the stage;
  arrows in stage order; digits in server order).
- [ ] 5.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate`,
  and with a `MUD_TEST_SETTINGS=1` env file
  `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract`;
  then `openspec validate webclient-combat-stage-target-picking --strict`. Verify all pass.

## Workflow follow-up

- At archive, add the new IDs of "Combat targets are picked on the stage figures" and "The stage target step presents
  the targets on the stage figures" to the two new browser methods (and `stage_target_step.test.js` where the
  traceability guide allows Vitest annotations) before `tools.spec_traceability check`.
