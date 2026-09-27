## 1. Preconditions

- [x] 1.1 Confirm C11a and C11b are archived. Stop and report if any check fails:
  - `ls web/webclient-app/lib/transition_hooks.js` succeeds
  - `grep -n -- "--motion-panel\|--motion-actor\|--motion-flash-peak\|--motion-stagger" web/webclient-app/styles/tokens.css` shows every token
  - `grep -n "A leaving element is out of reach while it animates out" openspec/specs/webclient-contextual-hud/spec.md` matches
- [x] 1.2 Record where C10b put the dialogue band rules (`grep -n 'data-elosern-mode="dialogue"' web/webclient-app/components/HudFrame.vue web/webclient-app/styles/app-shell.css`), and every test that asserts the collapsed region's `display:none`: `grep -rn "band-command" web/webclient-app/tests web/tests/browser | grep -i "display\|hidden"`.

## 2. Stage frame

- [x] 2.1 `web/webclient-app/components/HudFrame.vue` per design D1:
  - replace the dialogue `display:none` rule on `[data-anchor="band-command"]` with the absolute, translated, faded, delayed-`visibility` state
  - add the shared transition, `.stage-band { overflow: hidden }`, and `:inert="mode === 'dialogue'"` on the anchor

  Keep the one-column dialogue grid. (Done without `.stage-band { overflow: hidden }`, design D1: the stage root already clips the slide, and the band must not clip the verb popover. `inert` binds `|| null`.)
- [x] 2.2 `HudFrame.vue` per design D2:
  - the non-immediate `modeChange` watcher and `data-mode-change`
  - the `.stage-flash` layer and its rule
  - the always-rendered, `aria-hidden` veil with its opacity transition, and the pulse moved to `::before`
  - the flip rules on `[data-anchor="band-command"] > *`

  `web/webclient-app/styles/tokens.css`: add `elosern-stage-flash`, `elosern-panel-flip-in`, and `elosern-panel-flip-out`. Update the header comments. (The hook is computed from the raw mode in `composables/use-mode-change.js` and passed through `AppShell` as `HudFrame`'s `modeChange` prop, design D2.)
- [x] 2.3 `web/webclient-app/tests/hud_frame.test.js`: the dialogue case asserts `inert` and the one-column band, and the veil case asserts rendering in every mode. Add `HudFrame.stories.js` stories `DialogueEnter` and `CombatEnter` (args toggling `mode`). `pnpm exec vitest run web/webclient-app/tests/hud_frame.test.js` is green.

## 3. Host, plate, choices

- [x] 3.1 `web/webclient-app/AppClient.vue` per design D3: wrap the `#actor-right` `StageActor` in `<Transition name="actor-enter" v-bind="inertWhileLeaving">`, keyed by the host identity, with its CSS on `--motion-actor`, `--motion-shift-lg`, and `--motion-travel`. Also per design D5, wrap `#choices`' `DialogueChoices` in `<Transition name="choices-card">` with an enter fade only. (Superseded by design D5: the card's fade is a CSS entrance on the list itself, gated by the new `entrance` prop; no wrapper.)
- [x] 3.2 `web/webclient-app/components/MessageWindow.vue` per design D4: wrap the name plate in `<Transition name="plate" v-bind="inertWhileLeaving">`, with the leave positioned absolutely.
- [x] 3.3 `web/webclient-app/components/DialogueChoices.vue` per design D5 (CSS keyframes, not a `TransitionGroup`, as the revised D5 records): the rows carry `--row-index`, the rows' scroller is keyed by the view and clips during the entrance, and the entrance CSS uses `--motion-reveal`, `--motion-shift-sm`, `--motion-travel`, and `--motion-stagger`. Add a `Stagger` story to `stories/Core/DialogueChoices.stories.js`. `pnpm exec vitest run web/webclient-app/tests/dialogue_choices.test.js` stays green.
- [x] 3.4 `web/webclient-app/components/AppShell.vue`: confirm the leaving-dialogue post-flush rescue still lands on `#action-dock` now that the region is not `display:none` (design D6), and update its comment. Create `web/webclient-app/tests/mode_transitions.test.js` covering design D8's Vitest cases. `pnpm exec vitest run web/webclient-app/tests/mode_transitions.test.js web/webclient-app/tests/app.test.js` is green.
- [x] 3.5 `grep -rnE "(transition|animation)[a-z-]*:[^;]*[0-9]m?s" web/webclient-app/components/{HudFrame,MessageWindow,DialogueChoices}.vue web/webclient-app/AppClient.vue` returns nothing, and `pnpm exec vitest run web/webclient-app/tests/motion_tokens.test.js` stays green.

## 4. Browser and evidence

- [x] 4.1 Create `web/tests/browser/test_browser_mode_transitions.py` with the six journeys of design D8. `test_combat_enter_and_leave_full` also re-enters combat once and asserts the flash animates again. Annotate the journeys as design D8 lists, and add the methods to a shard in `.github/browser-shards.json`.
- [x] 4.2 Update the collapsed-region `display:none` assertions found in 1.2 (`test_browser_exploration_dialogue.py`, `test_browser_contextual_hud_stage.py`, `test_browser_layout.py`) to assert hidden and `inert`. Also `test_browser_contextual_hud_anchors.py`, whose overlap check now skips the `visibility: hidden` region (design D8).
- [x] 4.3 `web/webclient/tests/test_node_suite_evidence.py`: add `test_mode_transitions_vitest_evidence_passes`, which runs `tests/mode_transitions.test.js` and is annotated `webclient-contextual-hud::mode-changes-transition-at-the-motion-level`.
- [x] 4.4 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_mode_transitions web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_browser_contextual_hud_stage web.tests.browser.test_browser_contextual_hud_combat web.tests.browser.test_browser_combat_menu web.tests.browser.test_browser_layout web.tests.browser.test_browser_contextual_hud_drawers`. All green. (Run 2026-09-27 in batches within the local budget, plus `test_browser_scene_transitions`, `test_browser_contextual_hud_anchors`, `test_browser_contextual_hud_dock`, and `test_browser_shell_surfaces`: all green. `test_engage_transitions_to_combat` failed once on a `stale` action result from a server race and passed on rerun.)

## 5. Specs and traceability

- [x] 5.1 Sync this change's deltas into `openspec/specs/webclient-contextual-hud/spec.md`. Confirm the new ID with `uv run --locked python -m tools.spec_traceability list`. `uv run --locked python -m tools.spec_traceability check` is green.

## 6. Validation

- [x] 6.1 Run these from the repository root. All green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_evidence`
- [x] 6.2 Drive the live client at 1920×1080 with `agent-browser` at `完整`:
  - Open and leave a conversation, and check the panel slide, the host entrance, the plate, and the stagger.
  - Start and finish a fight, and check the flash, the veil, and the flip.
  - Repeat at `減少` (fades only, no flash) and `關閉` (instant), and check that a drawer opens instantly at `減少`.

  Close the browser afterwards.

  (Done 2026-09-27 against the real `AppClient` and store in Storybook's new `Core/AppShell` `ModeJourney` story at 1920×1080, 1440×900, and 1280×720, at all three levels, with the tokens slowed 8–32× to read mid-transition frames. The live-server path is covered by `test_browser_mode_transitions.py`.)
- [x] 6.3 Run `openspec validate webclient-mode-transitions --strict` and `git diff --check`. Both clean.
