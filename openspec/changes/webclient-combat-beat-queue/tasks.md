## 1. Preconditions

- [ ] 1.1 Confirm C12 and C13a are archived. Stop and report if any check fails:
  - `grep -n '"combat_beats"' web/webclient-app/stores/elosern/shared.js` matches
  - `ls web/static/webclient/js/elosern/protocol/panels/combat_beats.js web/webclient-app/components/FoeLineup.vue` succeeds
  - `grep -n "Foes stand opposite the player during combat" openspec/specs/webclient-contextual-hud/spec.md` matches
  - `grep -n "readMotionMs\|--motion-beat" -r web/webclient-app --include='*.js' --include='*.css' --include='*.vue'` finds nothing yet
- [ ] 1.2 Re-confirm design.md Context:
  - `emit_settlement` still sends one message per EventLog: `grep -n "actor.msg" world/rules/combat_result.py`
  - `dispatchAction` still pushes the response mark right after `sendAction`: `grep -n "responseMarks" web/webclient-app/stores/elosern/transport.js`
  - the MessageWindow reader state still names `responseKey`: `grep -n "responseKey" web/webclient-app/components/MessageWindow.vue`

## 2. Token reader and token

- [ ] 2.1 Create `web/webclient-app/lib/motion_tokens.js` with `readMotionMs` (design D1) and `web/webclient-app/tests/motion_tokens_reader.test.js`.
- [ ] 2.2 `web/webclient-app/styles/tokens.css`: add `--motion-beat` to the `:root` block (400ms), the `:root[data-motion="reduced"]` block (400ms), the `:root[data-motion="off"]` block (0ms), and the OS fallback block (400ms), with a comment naming design §10.2 and this change. Add `--motion-beat` to the required-token list in `web/webclient-app/tests/motion_tokens.test.js`. `pnpm exec vitest run web/webclient-app/tests/motion_tokens.test.js web/webclient-app/tests/motion_tokens_reader.test.js` is green.

## 3. The queue

- [ ] 3.1 Create `web/webclient-app/lib/beat_queue.js`: `planRound`, `beatReducer`, `displayHpFor`, `beatBlocks`, and `tailBlocks`, per design D3, D4, and D6. The beat block's tokens are one `text` token built directly, never passed through `NarrativeMarkup.tokenize`. Header comment names design §10.2 and C12's payload.
- [ ] 3.2 Create `web/webclient-app/tests/beat_queue.test.js` with design D9's cases. `pnpm exec vitest run web/webclient-app/tests/beat_queue.test.js` is green.

## 4. Store slice and lock

- [ ] 4.1 Create `web/webclient-app/stores/elosern/beats.js` (`applyBeats`) per design D5: `syncBeatRound`, `beatShown`, `skipBeats`, `flushBeats`, `resetBeats`, `beatLocked`, and the one pause timer. Compose it in `web/webclient-app/stores/elosern.js` before `applyView`, and export `beatShown` and `skipBeats` on the store.
- [ ] 4.2 `web/webclient-app/stores/elosern/transport.js`:
  - `dispatchAction` refuses while `ctx.beatLocked()`, and records `responseMark` on the in-flight record
  - `sendText` calls `ctx.flushBeats()` before appending its `in` line
  - `handleTransportLifecycle` calls `ctx.resetBeats()` on a generation change and on detach

  `web/webclient-app/stores/elosern/creation.js` `syncRouterGates`: `setMutationInFlight(!!ctx.inFlight || ctx.beatLocked())`.
- [ ] 4.3 `web/webclient-app/stores/elosern/view.js`:
  - `publishView` captures `const flight = ctx.inFlight` before `releaseIfReady` and calls `ctx.syncBeatRound(prev, rs, flight)` after it
  - `buildView` publishes `beatPlayback`, `displayHp`, and `dispatch.beatLocked`

  Keep `dispatch.inFlight`'s two-field shape.
- [ ] 4.4 Create `web/webclient-app/tests/store/beat_playback.test.js` with design D9's store cases, built on `tests/store/protocol_fixtures.js` and a `combat_beats` fixture that passes `validateCombatBeatsPanel`. Extend `tests/store/store_dispatch_focus.test.js` with the lock refusal. `pnpm exec vitest run web/webclient-app/tests/store` is green.

## 5. Window and HP display

- [ ] 5.1 `web/webclient-app/components/MessageWindow.vue` per design D6:
  - the `beatPlayback` prop
  - the beat and tail page list for the bound response
  - auto pacing, with the in-beat page pause from `readMotionMs("--motion-beat")`
  - `beat-shown` / `beat-skip`, the hidden marker and disarmed auto-advance during auto playback, the move to the first tail page on `done`, and `off` as ordinary pages

  `components/AppShell.vue` forwards the prop and the emits. `web/webclient-app/AppClient.vue` binds `store.view.beatPlayback` and wires `@beat-shown="store.beatShown"` and `@beat-skip="store.skipBeats"`.
- [ ] 5.2 Create `web/webclient-app/tests/message_window_beats.test.js` with design D9's window cases. Add a `CombatRound` story to `stories/Core/MessageWindow.stories.js` (auto playback mid-round, and `off`). `pnpm exec vitest run web/webclient-app/tests/message_window_beats.test.js web/webclient-app/tests/message_window.test.js web/webclient-app/tests/message_window_typing.test.js` is green.
- [ ] 5.3 `components/VitalsTrack.vue` and `components/StatusPanel.vue` gain `displayHp`, and `components/ParticipantFrame.vue` gains `displayHp` (design D7). `AppClient.vue` binds both. Extend `tests/data/vitals_track.test.js` and `tests/combat/participant_frame.test.js`, and add `DisplayedHp` stories to `stories/Data/VitalsTrack.stories.js` and `stories/Data/ParticipantFrame.stories.js`. `pnpm exec vitest run web/webclient-app/tests/data web/webclient-app/tests/combat` is green.

## 6. Browser and evidence

- [ ] 6.1 Create `web/tests/browser/test_browser_combat_beats.py` with design D9's three journeys on an isolated managed server, reusing `test_browser_combat_panels.py`'s engage and key helpers (import or share them through `_journey_support.py`). Annotate the journeys as D9 lists, and add them to a shard in `.github/browser-shards.json`.
- [ ] 6.2 `grep -n "message-page" web/tests/browser/test_browser_combat_*.py`. Update each post-round text read to page through with Enter or to use `narrative_log_text`.
- [ ] 6.3 `web/webclient/tests/test_node_suite_evidence.py`: add `test_beat_queue_vitest_evidence_passes` (design D9).
- [ ] 6.4 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_combat_beats web.tests.browser.test_browser_combat_panels web.tests.browser.test_browser_combat_menu web.tests.browser.test_browser_combat_skills web.tests.browser.test_browser_combat_rejection web.tests.browser.test_browser_input_narrative web.tests.browser.test_browser_combat_stage`. All green.

## 7. Specs and traceability

- [ ] 7.1 Sync this change's deltas into `openspec/specs/webclient-combat-menu/spec.md`, `openspec/specs/webclient-contextual-hud/spec.md`, and `openspec/specs/webclient-input-narrative/spec.md`. Confirm the new ID with `uv run --locked python -m tools.spec_traceability list`. `uv run --locked python -m tools.spec_traceability check` is green.

## 8. Validation

- [ ] 8.1 Run these from the repository root. All green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence`
- [ ] 8.2 Drive the live client at 1920×1080 with `agent-browser`:
  - At `完整`, fight one foe and watch the beats type and pause, the HP step, the dock stay locked, and a click end the round.
  - At `減少`, check instant pages with pauses.
  - At `關閉`, page the beats by hand.
  - Win a fight, and check that the final beats play while the minimap is already back.

  Close the browser afterwards.
- [ ] 8.3 Run `openspec validate webclient-combat-beat-queue --strict` and `git diff --check`. Both clean.
