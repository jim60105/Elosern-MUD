## 1. Preconditions

- [ ] 1.1 Confirm C9 (`explore-talk-open-action`) and C10a (`dialogue-panel-host-portrait`) are archived:
  - `grep -n "DIALOGUE_SCHEMA_VERSION = 2" web/webclient/presentation/dialogue.py` matches
  - `ls web/webclient-app/components/MessageWindow.vue` succeeds and `grep -n "NarrativeFeed" web/webclient-app/components/AppShell.vue` returns nothing
  - `grep -n "actor-left" web/webclient-app/AppClient.vue` shows the `ReferenceArtwork` mount

  Stop and report if any fails.

## 2. StageActor

- [ ] 2.1 Create `web/webclient-app/components/StageActor.vue` per design D1 (props `portrait`, `name`, `side`, `dimmed`; root `data-testid="stage-actor"`, `data-side`, `data-speaking`; the name placeholder when `portrait` is null). Add `--actor-dim: 0.6` to `styles/tokens.css` and the `.stage-actor[data-speaking="false"]` rule. In `components/ReferenceArtwork.vue`, draw the placeholder glyph with `portraitGlyph(placeholderLabel)` from `components/character-identity.js`.
- [ ] 2.2 Add `stories/Core/StageActor.stories.js` with deterministic offline args for the player, host-image, host-pending-placeholder, host-missing-entry, speaking, and dimmed states (inline data-URI or existing fixture images; no network). Add `"Core/StageActor"` to `component-manifest.json` (keep `"frozen": true`) and to the showcase snapshots that list `Core/ReferenceArtwork` (`web/webclient/tests/test_vue_showcase_{action,data,world,overlays}_evidence.py`).
- [ ] 2.3 Add `tests/core/stage_actor.test.js` covering design D8's StageActor cases. Update `tests/core/reference_artwork.test.js` if it pins `slice(0, 1)` behaviour.

## 3. Speaker and wiring

- [ ] 3.1 `web/webclient-app/stores/elosern/view.js`: publish `dialogueSpeaker` per design D3. Add the store case to `tests/dialogue_store.test.js` (dispatch → `"player"`, handled result plus accepted revision → `"host"`, rejection → `"host"`, a `explore.dialogue_leave` dispatch → `"host"`).
- [ ] 3.2 `web/webclient-app/AppClient.vue`: compute `dialogueVm` once, `hostPortrait` per design D2, and render `StageActor` in `#actor-left` (the player, `dimmed` when mode is dialogue and the speaker is `"host"`) and `#actor-right` (the host, `v-if` dialogue and `dialogueVm`, `dimmed` when the speaker is `"player"`). The `#art` drawer slot keeps `ReferenceArtwork`. Move the `[data-anchor="actor-left"] .reference-artwork` sizing rule in `styles/app-shell.css` to cover `.stage-actor` in both anchors, with `actor-right`'s mask mirrored.

## 4. Collapse, focus home, and keys

- [ ] 4.1 `web/webclient-app/components/HudFrame.vue`: the two dialogue rules of design D4. Update the header comment's mode-gating list and `stories/Core/HudFrame.stories.js` (a dialogue-mode story showing the one-column band).
- [ ] 4.2 `web/webclient-app/components/AppShell.vue`:
  - `HIDDEN_BY_MODE.dialogue = "[data-anchor='band-command']"`
  - rename `restoreDockFocus` to `restoreFocusHome` (design D5), including `releaseCommandField`, the exposed API, and the header comment
  - add the enter-dialogue pre-flush rescue to `message-page` plus the `nextTick` `restoreFocusHome()`, and the leave-dialogue post-flush rescue

  `grep -rn "restoreDockFocus" web/webclient-app --include='*.js' --include='*.vue'` (excluding `dist/`) returns nothing after `composables/use-dock.js` `onNavigateHome` and every test are updated.
- [ ] 4.3 `web/webclient-app/stores/elosern/interaction.js` `focusPress`: the dialogue gate of design D6. Update the function's comment.

## 5. Message window

- [ ] 5.1 `web/webclient-app/components/MessageWindow.vue`:
  - render the name plate per design D7 while the dialogue variant is active
  - delete the `.dlg` avatar (`.av`) and the speaker line (`.who`, `.who-bond`, `dialogue-who`) with their CSS, and the now-unused `portraitFor` / `portraitGlyph` / `faceObjectPosition` imports
  - add `defineExpose({ focusHome })`
  - dialogue-mode styles for the full-width region in `styles/app-shell.css`

  Update the dialogue state of `stories/Core/MessageWindow.stories.js` and `stories/Core/AppShell.stories.js` (a whole-band decorator and the plate).
- [ ] 5.2 `web/webclient-app/lib/controls-reference.js`: the digits and Enter rows name the dialogue behaviour (the dock is collapsed; digits pick the conversation's choices; Enter activates the focused choice). Update `tests/overlays/help_overlay.test.js` if it pins the text.

## 6. Vitest and evidence

- [ ] 6.1 Update `tests/hud_frame.test.js`, `tests/app.test.js`, `tests/message_window_dialogue.test.js`, `tests/store/digit_row_picks.test.js`, and `tests/store/store_dispatch_focus.test.js` per design D8. Rewrite `tests/dialogue_dock.test.js` as the collapse test (design D8). Run `pnpm test` (repository root); green.
- [ ] 6.2 `web/webclient/tests/test_node_suite_evidence.py`:
  - re-anchor `test_dialogue_dock_vitest_evidence_passes` from `webclient-contextual-hud::the-dock-keeps-its-regular-exploration-form-in-dialogue-mode` to `webclient-contextual-hud::the-command-region-collapses-in-dialogue-mode-and-the-message-window-spans-the-band`
  - add `test_stage_actor_vitest_evidence_passes` (runs `tests/core/stage_actor.test.js`, `tests/app.test.js`, and `tests/dialogue_store.test.js`), annotated `webclient-contextual-hud::stage-actors-present-the-player-and-the-dialogue-host-with-a-speaking-state`

## 7. Browser suite

- [ ] 7.1 `web/tests/browser/test_browser_exploration_dialogue.py`: add the 1920x1080 journey of design D8 (collapse, band width, both stage actors, speaking flip after a pick, Escape from `/` returning to the first pick, focus never on `body` across both mode changes, dock back at the overview after 結束對話). Annotate it with both new IDs. Re-point any assertion on `dialogue-who` to `message-name-plate`.
- [ ] 7.2 `test_browser_contextual_hud_stage.py` (band height and split in dialogue), `test_browser_contextual_hud_anchors.py` (`actor-right` geometry in dialogue), `test_browser_layout.py` and `browser_helpers.py` (`REQUIRED_SURFACES` does not expect `#action-dock` in dialogue).
- [ ] 7.3 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_browser_contextual_hud_stage web.tests.browser.test_browser_contextual_hud_anchors web.tests.browser.test_browser_layout web.tests.browser.test_browser_shell_command_line web.tests.browser.test_browser_input_narrative`; all green.

## 8. Specs and traceability

- [ ] 8.1 Sync this change's deltas into the main specs. Confirm both new IDs with `uv run --locked python -m tools.spec_traceability list`. `grep -rn "the-dock-keeps-its-regular-exploration-form-in-dialogue-mode" web tests` returns nothing. Run `uv run --locked python -m tools.spec_traceability check`; green.

## 9. Validation

- [ ] 9.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check`, and `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_evidence web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence`; all green.
- [ ] 9.2 Drive the live client at 1920x1080 with `agent-browser`: open a conversation with a scripted host, and check both portraits stand on the band, the host is lit and the player dimmed, the band is one message window with the name plate, a pick lights the player until the reply, and 結束對話 brings the dock back. Close the browser afterwards.
- [ ] 9.3 Run `openspec validate webclient-dialogue-stage-actors --strict` and `git diff --check`; both clean.
