## 1. Preconditions

- [x] 1.1 Confirm C11c and C12 are archived. Stop and report if any check fails:
  - `grep -n "Mode changes transition at the motion level" openspec/specs/webclient-contextual-hud/spec.md` matches
  - `grep -n '"combat_beats"' web/webclient-app/stores/elosern/shared.js` matches
  - `ls web/webclient-app/components/StageActor.vue web/webclient-app/lib/transition_hooks.js web/webclient-app/composables/use-mode-change.js` succeeds
  - `grep -n 'actor-enter' web/webclient-app/AppClient.vue` shows C11c's host transition
- [x] 1.2 Record every test that asserts an empty `actor-right` or "no participant content" there: `grep -rn "actor-right" web/webclient-app/tests web/tests/browser`. Rebuild this change's delta blocks on the current main text (C10b, C10c, C11c, and the caption fix 33c83461 changed them after this change was written).

## 2. The line-up component

- [x] 2.1 Create `web/webclient-app/components/foe-lineup.js` (the scales, the exposed share, the lift, `foeSlots`, `foeLineupSpan`, `activeFoes`, `foeHpPercent`) and `web/webclient-app/components/FoeLineup.vue` per design D1–D3 and D5:
  - the `foes`, `artPanel`, and `motionLevel` props, the cap of three, and `entryFor`
  - the `TransitionGroup name="foe"` with `:css="motionLevel !== 'off'"`, bound to `inertWhileLeaving`
  - `data-testid="foe-lineup"`, `data-count`, `aria-hidden`, the `foe-slot` wrappers with `--foe-index`, `--foe-scale`, `--foe-lift`, and `data-portrait-ref`
  - the depth geometry and the row inset from `--foe-face-clear` and the front foe's scale
  - the decorative gauge (fill and trailing bar) on the scene caption's baseline
  - the `foe-enter`, `foe-leave`, and re-slotting transitions, on the motion tokens only

  A header comment names design §4, §10.2, and this change.
- [x] 2.2 Create `web/webclient-app/tests/core/foe_lineup.test.js` with design D9's component and geometry cases. `pnpm exec vitest run web/webclient-app/tests/core/foe_lineup.test.js` is green.
- [x] 2.3 Create `web/webclient-app/stories/Core/FoeLineup.stories.js` with `OneFoe`, `TwoFoes`, `ThreeFoes`, `FiveFoesCapped`, `PendingPlaceholder`, and `MissingEntry` on a stage frame drawn from the shared tokens, with args from `stories/fixtures/combat_stage.js` (exported through `stories/fixtures.js`). Add `"Core/FoeLineup"` to `web/webclient-app/component-manifest.json`.

## 3. Stage wiring

- [x] 3.1 `web/webclient-app/AppClient.vue`:
  - add `combatFoes` (`activeFoes` of the committed combat panel) and `foesOnStage`
  - render `<Transition name="foes-enter" :css="hostTransitionCss" v-bind="inertWhileLeaving" @after-leave="onFoeLineupGone"><FoeLineup v-if="foesOnStage" …/></Transition>` in `#actor-right` beside the host, with the `foes-enter` CSS (design D3)
  - bind `--foe-lineup-span` and `--foe-front-scale` on `.elosern-root`, released after a leaving row has faded (design D6)
- [x] 3.2 `web/webclient-app/components/HudFrame.vue`: in combat, `[data-anchor="actor-right"]` gets `overflow: visible`, and the header comment names the line-up. `styles/tokens.css` gains `--foe-face-clear` (and its short-viewport value).
- [x] 3.3 `styles/app-shell.css`: the scene caption's right side clears the row and glides with it; `SceneBackdrop.vue`: the label gives way last.
- [x] 3.4 Visual refinements (design D4, D5, D7): the `StageActor.vue` mask reaches zero at the box's edges; foes use a tighter mask; the participant frame's product rules in `styles/app-shell.css` are denser, ellipsise long names, and gain a compact short-viewport variant.
- [x] 3.5 Extend `tests/app_client_stage_actor.test.js`, `tests/mode_transitions.test.js`, `tests/hud_frame.test.js`, and `tests/overlays/objective_tracker_integration.test.js` with design D9's cases. Show a line-up in the `Core/HudFrame` combat stories and three foes in `Core/AppShell` `CombatHud`, add `CombatOneFoe`, `CombatFiveFoes`, and the `ModeJourney` `defeat` step. The four Vitest files are green.
- [x] 3.6 `grep -rnE "(transition|animation)[a-z-]*:[^;]*[0-9]m?s" web/webclient-app/components/FoeLineup.vue web/webclient-app/AppClient.vue` returns nothing, and `pnpm exec vitest run web/webclient-app/tests/motion_tokens.test.js` stays green.

## 4. Browser and evidence

- [x] 4.1 Create `web/tests/browser/test_browser_combat_stage.py` with design D9's journeys (served portrait routes, injected snapshots with their own participants). Annotate them as D9 lists, and add the methods to shards in `.github/browser-shards.json`.
- [x] 4.2 Update `test_browser_contextual_hud_combat.py::test_combat_participant_frame_presents_participants_and_portraits`: `actor-right` holds `foe-lineup` and no `participant-frame` descendant or numeral.
- [x] 4.3 `web/webclient/tests/test_node_suite_evidence.py`: add `test_foe_lineup_vitest_evidence_passes`, which runs `tests/core/foe_lineup.test.js`, `tests/app_client_stage_actor.test.js`, and `tests/mode_transitions.test.js` and is annotated `webclient-contextual-hud::foes-stand-opposite-the-player-during-combat`. Add `Core/FoeLineup` to the showcase snapshot lists in `web/webclient/tests/test_vue_showcase_*_evidence.py` that already list `Core/StageActor`.
- [x] 4.4 Run `uv run --locked python -m web.tests.browser.unittest_driver` on `test_browser_combat_stage`, `test_browser_contextual_hud_combat`, `test_browser_contextual_hud_anchors`, `test_browser_contextual_hud_stage`, `test_browser_combat_menu`, `test_browser_mode_transitions`, and `test_browser_art` (in batches within the local time limit). All green.

## 5. Specs and traceability

- [x] 5.1 Sync this change's deltas into `openspec/specs/webclient-contextual-hud/spec.md`, `openspec/specs/webclient-component-showcase/spec.md`, and `openspec/specs/webclient-art-panel/spec.md`. Confirm the new ID with `uv run --locked python -m tools.spec_traceability list`. `uv run --locked python -m tools.spec_traceability check` is green.
- [x] 5.2 Adjust `webclient-combat-beat-choreography` (C13c): the gauge ships in this change; C13c feeds it the displayed value and keeps its pre-round roster and hold.

## 6. Validation

- [x] 6.1 Run these from the repository root. All green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence tests.test_evennia_test_optimization_contract`
- [x] 6.2 Drive Storybook and the live client at 1920×1080, 1440×900, and 1280×720 with `agent-browser` at `完整`: one foe, a group, and five foes; the depth, the scale, the gauges, the caption, clearance from the player and the frame; slowed frame sequences of the slide-in beside the flash, a defeated foe fading out, and the fade on leaving. Repeat at `減少` and `關閉`. Close the browser afterwards.
- [x] 6.3 Run `openspec validate webclient-combat-foes-on-stage --strict` and `git diff --check`. Both clean.
