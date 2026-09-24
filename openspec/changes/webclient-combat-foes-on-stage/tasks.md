## 1. Preconditions

- [ ] 1.1 Confirm C11c and C12 are archived. Stop and report if any check fails:
  - `grep -n "Mode changes transition at the motion level" openspec/specs/webclient-contextual-hud/spec.md` matches
  - `grep -n '"combat_beats"' web/webclient-app/stores/elosern/shared.js` matches
  - `ls web/webclient-app/components/StageActor.vue web/webclient-app/lib/transition_hooks.js` succeeds
  - `grep -n 'actor-enter' web/webclient-app/AppClient.vue` shows C11c's host transition
- [ ] 1.2 Record every test that asserts an empty `actor-right` or "no participant content" there: `grep -rn "actor-right" web/webclient-app/tests web/tests/browser`.

## 2. The line-up component

- [ ] 2.1 Create `web/webclient-app/components/FoeLineup.vue` per design D1–D3:
  - the `foes` and `artPanel` props, the cap of three, and `entryFor`
  - the `TransitionGroup name="foe"` bound to `inertWhileLeaving`, or to explicit hook listeners if the prop binding does not reach it
  - `data-testid="foe-lineup"`, `data-count`, the `foe-slot` wrappers with `--foe-index` and `data-portrait-ref`
  - the `--foe-scale` geometry
  - the `foe-enter`, `foe-leave`, and `foe-move` classes, on `--motion-actor`, `--motion-shift-lg`, `--motion-travel`, `--ease-enter`, and `--ease-exit` only

  A header comment names design §4 and this change.
- [ ] 2.2 Create `web/webclient-app/tests/core/foe_lineup.test.js` with design D7's component cases. `pnpm exec vitest run web/webclient-app/tests/core/foe_lineup.test.js` is green.
- [ ] 2.3 Create `web/webclient-app/stories/Core/FoeLineup.stories.js` with `OneFoe`, `ThreeFoes`, `FiveFoesCapped`, `PendingPlaceholder`, and `MissingEntry`. Use a 446×670 decorator box right-aligned in a 1920-wide frame, and build args from the shared story fixtures (`stories/fixtures.js`). Add `"Core/FoeLineup"` to `web/webclient-app/component-manifest.json`.

## 3. Stage wiring

- [ ] 3.1 `web/webclient-app/AppClient.vue`:
  - add `combatFoes`: `contextActionsPanel.participants` filtered to `team === "foes" && state === "active"`, in order
  - render `<Transition name="foes-enter" v-bind="inertWhileLeaving"><FoeLineup v-if="store.view.mode === 'combat' && combatFoes.length" …/></Transition>` in `#actor-right` beside the host branch, with the `foes-enter` CSS (design D3)
- [ ] 3.2 `web/webclient-app/components/HudFrame.vue`: in combat mode, `[data-anchor="actor-right"]` gets `overflow: visible`, and the header comment names the line-up. If the portrait rules live in `styles/app-shell.css` (`grep -n 'actor-right' web/webclient-app/styles/app-shell.css`), put the rule there.
- [ ] 3.3 Extend `web/webclient-app/tests/app_client_stage_actor.test.js` and `tests/hud_frame.test.js` with design D7's cases. Add a line-up to the `CombatEnter` story in `stories/Core/HudFrame.stories.js`. `pnpm exec vitest run web/webclient-app/tests/app_client_stage_actor.test.js web/webclient-app/tests/hud_frame.test.js` is green.
- [ ] 3.4 `grep -rnE "(transition|animation)[a-z-]*:[^;]*[0-9]m?s" web/webclient-app/components/FoeLineup.vue web/webclient-app/AppClient.vue` returns nothing, and `pnpm exec vitest run web/webclient-app/tests/motion_tokens.test.js` stays green.

## 4. Browser and evidence

- [ ] 4.1 Create `web/tests/browser/test_browser_combat_stage.py` with design D7's five journeys, using `_journey_support._combat_panel()` (participants replaced per case), `_art_panel`, `inject_snapshot`, and `inject_update`. Annotate them as D7 lists, and add the methods to a shard in `.github/browser-shards.json`.
- [ ] 4.2 Update the assertions found in 1.2:
  - `test_browser_contextual_hud_combat.py::test_combat_participant_frame_presents_participants_and_portraits` asserts that `actor-right` holds `foe-lineup` and no `participant-frame` descendant
  - any empty-in-combat assertion in `test_browser_contextual_hud_stage.py`
- [ ] 4.3 `web/webclient/tests/test_node_suite_evidence.py`: add `test_foe_lineup_vitest_evidence_passes`, which runs `tests/core/foe_lineup.test.js` and `tests/app_client_stage_actor.test.js` and is annotated `webclient-contextual-hud::foes-stand-opposite-the-player-during-combat`. Add `Core/FoeLineup` to the showcase snapshot lists in `web/webclient/tests/test_vue_showcase_*_evidence.py` that already list `Core/StageActor` (`grep -ln "Core/StageActor" web/webclient/tests`).
- [ ] 4.4 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_combat_stage web.tests.browser.test_browser_contextual_hud_combat web.tests.browser.test_browser_contextual_hud_stage web.tests.browser.test_browser_combat_menu web.tests.browser.test_browser_mode_transitions web.tests.browser.test_browser_art`. All green.

## 5. Specs and traceability

- [ ] 5.1 Sync this change's deltas into `openspec/specs/webclient-contextual-hud/spec.md`, `openspec/specs/webclient-component-showcase/spec.md`, and `openspec/specs/webclient-art-panel/spec.md`. Confirm the new ID with `uv run --locked python -m tools.spec_traceability list`. `uv run --locked python -m tools.spec_traceability check` is green.

## 6. Validation

- [ ] 6.1 Run these from the repository root. All green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_evidence`
- [ ] 6.2 Drive the live client at 1920×1080 and 1280×720 with `agent-browser` at `完整`. Engage one foe and then a group, and check the row's overlap, its scale, that it stays clear of the player, the slide-in beside the flash, a defeated foe fading out, and the fade on victory. Repeat at `減少` and `關閉`. Close the browser afterwards.
- [ ] 6.3 Run `openspec validate webclient-combat-foes-on-stage --strict` and `git diff --check`. Both clean.
