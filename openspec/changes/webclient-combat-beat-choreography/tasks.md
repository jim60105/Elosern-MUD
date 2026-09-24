## 1. Preconditions

- [ ] 1.1 Confirm C13a and C13b are archived. Stop and report if any check fails:
  - `grep -n "A combat round plays beat by beat" openspec/specs/webclient-combat-menu/spec.md` matches
  - `grep -n "Foes stand opposite the player during combat" openspec/specs/webclient-contextual-hud/spec.md` matches
  - `grep -n "readMotionMs\|--motion-beat" web/webclient-app/lib/motion_tokens.js web/webclient-app/styles/tokens.css` shows the reader and the token
  - `grep -n "beatPlayback\|displayHp" web/webclient-app/stores/elosern/view.js` matches
  - `grep -n "data-portrait-ref" web/webclient-app/components/FoeLineup.vue` matches
- [ ] 1.2 Record the veil rules C11c left in `HudFrame.vue` (`grep -n "stage-combat-veil" web/webclient-app/components/HudFrame.vue`) and the trail tokens in `tokens.css` (`grep -n -- "--motion-trail" web/webclient-app/styles/tokens.css`).

## 2. Tokens and keyframes

- [ ] 2.1 `web/webclient-app/styles/tokens.css` per design D1:
  - `--motion-beat-step`, `--motion-beat-hit`, `--motion-beat-float`, and `--motion-beat-defeat` in all three level blocks and the OS fallback block
  - `--motion-beat-lunge`, `--motion-beat-shake`, and `--motion-beat-rise`
  - `--motion-trail-delay: 300ms` at `full`
  - the five `elosern-beat-*` keyframes

  Add the four duration tokens to `tests/motion_tokens.test.js`. `pnpm exec vitest run web/webclient-app/tests/motion_tokens.test.js` is green.

## 3. Queue and store

- [ ] 3.1 `web/webclient-app/lib/beat_queue.js` per design D2 and D3: the `act` phase with `acted`, HP applied at act start, `actMs(step)` over `readMotionMs`, `stageFor`, and the hold flag. Extend `tests/beat_queue.test.js` with the act row, and create `tests/beat_choreography.test.js` with design D7's cases. `pnpm exec vitest run web/webclient-app/tests/beat_queue.test.js web/webclient-app/tests/beat_choreography.test.js` is green.
- [ ] 3.2 `web/webclient-app/stores/elosern/beats.js`: schedule `acted` after `actMs`, keeping one timer handle, and clear it on skip, flush, and reset. `stores/elosern/view.js`: publish `beatStage` and `beatHold`. Extend `tests/store/beat_playback.test.js` with the act timer and the hold for a terminal round. `pnpm exec vitest run web/webclient-app/tests/store` is green.

## 4. Stage

- [ ] 4.1 `web/webclient-app/components/StageActor.vue` per design D4:
  - the `gesture`, `gestureKey`, and `floatAmount` props
  - the keyed `.stage-actor__beat` wrapper with `data-beat`
  - the side-aware lunge, the hit, the defeat, and the float, with CSS on tokens only

  Extend `tests/core/stage_actor.test.js`, and add `BeatLunge`, `BeatHit`, and `BeatDefeat` to `stories/Core/StageActor.stories.js`.
- [ ] 4.2 `web/webclient-app/components/FoeLineup.vue` per design D5:
  - the `stage` and `displayHp` props
  - the pre-round roster during a round
  - per-slot gestures
  - the decorative gauge with fill and ghost on `--motion-slow`, `--motion-trail`, and `--motion-trail-delay`

  Extend `tests/core/foe_lineup.test.js`, and add a `RoundInProgress` story.
- [ ] 4.3 `web/webclient-app/components/HudFrame.vue` and `web/webclient-app/AppClient.vue` per design D6:
  - the `beatHold` prop and `data-beat-hold`, and the held-veil rule
  - the line-up rendered while `mode === 'combat' || beatHold`, `inert` while held
  - the player's gesture from `beatStage.gestures[status.actor.identity]`

  Extend `tests/hud_frame.test.js`, and add a `TerminalRoundHold` story to `stories/Core/HudFrame.stories.js`.
- [ ] 4.4 `grep -rnE "(transition|animation)[a-z-]*:[^;]*[0-9]m?s" web/webclient-app/components/{StageActor,FoeLineup,HudFrame}.vue web/webclient-app/AppClient.vue` returns nothing. `pnpm exec vitest run web/webclient-app/tests/core web/webclient-app/tests/hud_frame.test.js web/webclient-app/tests/motion_tokens.test.js` is green.

## 5. Browser and evidence

- [ ] 5.1 Create `web/tests/browser/test_browser_combat_choreography.py` with design D7's four journeys, reusing C13b's isolated-server helpers. For the terminal journeys, pick the defeat setup the way `test_browser_combat_panels.py` reaches a terminal outcome (`grep -n "defeat\|victory\|terminal" web/tests/browser/test_browser_combat_panels.py`). Annotate the journeys as D7 lists, and add them to a shard in `.github/browser-shards.json`.
- [ ] 5.2 `web/webclient/tests/test_node_suite_evidence.py`: add `test_beat_choreography_vitest_evidence_passes`, which runs `tests/beat_choreography.test.js` and is annotated with the new ID.
- [ ] 5.3 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_combat_choreography web.tests.browser.test_browser_combat_beats web.tests.browser.test_browser_combat_stage web.tests.browser.test_browser_mode_transitions web.tests.browser.test_browser_combat_panels`. All green.

## 6. Specs and traceability

- [ ] 6.1 Sync this change's deltas into `openspec/specs/webclient-contextual-hud/spec.md` and `openspec/specs/webclient-combat-menu/spec.md`. Confirm the new ID with `uv run --locked python -m tools.spec_traceability list`. `uv run --locked python -m tools.spec_traceability check` is green.

## 7. Validation

- [ ] 7.1 Run these from the repository root. All green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_evidence`
- [ ] 7.2 Drive the live client at 1920×1080 with `agent-browser` at `完整`:
  - Fight a group, and check the lunge, the shake and flash, the rising number, the gauge and trailing bar 300ms behind, and a foe dropping out on its own beat.
  - Win the fight, and check that the veil and the foes stay behind the final beats while the minimap is already back, and leave on the last beat or on a click.
  - Repeat at `減少` (fades only) and `關閉` (text only, nothing held).

  Close the browser afterwards.
- [ ] 7.3 Run `openspec validate webclient-combat-beat-choreography --strict` and `git diff --check`. Both clean.
