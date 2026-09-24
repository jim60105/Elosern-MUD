## 1. Preconditions

- [ ] 1.1 Confirm C10b (`webclient-dialogue-stage-actors`) is archived:
  - `ls web/webclient-app/components/StageActor.vue` succeeds
  - `grep -n "restoreFocusHome" web/webclient-app/components/AppShell.vue` matches
  - `grep -n "message-name-plate" web/webclient-app/components/MessageWindow.vue` matches
  - `grep -n "handleCaptionDialoguePick" web/webclient-app/stores/elosern/interaction.js` still matches (deleted here)

  Stop and report if any fails.

## 2. Message window

- [ ] 2.1 `web/webclient-app/components/MessageWindow.vue`: delete the dialogue variant per design D1 (branch, render function, echo suppression, box pin, `dialogue-*` emits, `.dlg` / `.say` / `.choices` / `.pick*` CSS, and any now-unused imports). Keep the name plate. Add `readingComplete` and the `reading-change` emit per design D3. `focusHome()` focuses the page surface. `grep -n "dialogue-pick\|dialogue-freeform\|dialogue-leave\|pinDialogueBox\|data-variant=\"dialogue\"" web/webclient-app/components/MessageWindow.vue` returns nothing.
- [ ] 2.2 Rewrite `tests/message_window_dialogue.test.js` (paged dialogue under the plate, `reading-change` flips, no rows) and flip the dialogue case in `tests/message_window_typing.test.js` to typing. Update the dialogue state in `stories/Core/MessageWindow.stories.js` to a paged page with the plate.

## 3. Choice list

- [ ] 3.1 Create `web/webclient-app/components/DialogueChoices.vue` per design D5, with its CSS per design D6 (card treatment, 44px rows, active-row fill and `▸`). Exit rows use `components/dock-exits.js` for the glyph and destination.
- [ ] 3.2 Add `stories/Core/DialogueChoices.stories.js` with deterministic offline args (picks, no-picks, move-exits, disabled-exit, overflowing), bound through the shared dialogue fixture helper the MessageWindow stories use (the showcase derived-shape rule). Add `"Core/DialogueChoices"` to `component-manifest.json` (keep `"frozen": true`) and to the showcase snapshots in `web/webclient/tests/test_vue_showcase_{action,data,world,overlays}_evidence.py` that list `Core/StageActor`.
- [ ] 3.3 Add `tests/dialogue_choices.test.js` covering design D10's component cases.

## 4. Stage anchor, wiring, and focus

- [ ] 4.1 `web/webclient-app/components/HudFrame.vue`: the `choices` anchor and CSS of design D6; the header comment and `stories/Core/HudFrame.stories.js` (dialogue story with a card in the anchor).
- [ ] 4.2 `web/webclient-app/components/AppShell.vue`:
  - forward the `choices` slot and the window's `reading-change`
  - delete the `dialogue-pick` / `dialogue-freeform` / `dialogue-leave` forwarding
  - expose `focusMessagePage()`
  - make `restoreFocusHome()` prefer the rendered list in dialogue (design D7)
  - add `[data-anchor='choices']` to the leave-dialogue rescue
  - pass `:accepting` to `CommandLine`
- [ ] 4.3 `web/webclient-app/AppClient.vue`:
  - `readingComplete`, `choicesShown` (design D4), and `dialogueExits` (design D8)
  - render `DialogueChoices` in `#choices` with the four emits wired as in proposal.md, plus the `beforeActivate` callback
  - the show-time focus watch (design D7)
- [ ] 4.4 `web/webclient-app/stores/elosern/interaction.js`: delete `handleCaptionDialoguePick`, `ctx.captionDialoguePresented`, and the digit retarget branch. In dialogue mode `focusPress` claims only `/`. Drop the matching exports in `stores/elosern.js`. `grep -rn "captionDialoguePresented\|handleCaptionDialoguePick" web/webclient-app --include='*.js' --include='*.vue'` (excluding `dist/`) returns nothing after section 6.
- [ ] 4.5 `web/webclient-app/lib/controls-reference.js`: the digits and Enter rows describe the choice list (digits pick a choice, Enter activates the focused row, Escape leaves `↦ 移動…`). Update `tests/overlays/help_overlay.test.js` if it pins the text.

## 5. Command line accept rule

- [ ] 5.1 `web/webclient-app/stores/elosern/view.js`: publish `freeformBound` and `commandAccepts` (design D9). `stores/elosern/transport.js` `sendText`: keep `ctx.freeformTarget` when `dispatchAction` returns `null`, and update the comment block at the borrowed branch.
- [ ] 5.2 `web/webclient-app/components/CommandLine.vue`: the `accepting` prop gates the clear and `sent` in `submit()`. Update `stories/Core/CommandLine.stories.js` args and `tests/command_line.test.js`. Update `tests/app_client_completion.test.js` if it mounts `CommandLine` with the old predicate props.

## 6. Vitest and evidence

- [ ] 6.1 Update `tests/app.test.js`, `tests/hud_frame.test.js`, `tests/dialogue_store.test.js`, `tests/dialogue_dock.test.js`, and `tests/store/digit_row_picks.test.js` per design D10. Run `pnpm test` (repository root); green.
- [ ] 6.2 `web/webclient/tests/test_node_suite_evidence.py`:
  - the dialogue evidence test runs `message_window_dialogue.test.js`, `dialogue_choices.test.js`, and `dialogue_view_model.test.js`
  - re-anchor its `webclient-contextual-hud::the-feed-presents-the-dialogue-variant-from-the-committed-panel` annotation to `…::dialogue-choices-appear-centred-over-the-stage-after-the-line-is-fully-read`
  - re-anchor the two `webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control` annotations (lines near 77 and 200) to `…::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow`

## 7. Browser suite

- [ ] 7.1 `web/tests/browser/test_browser_exploration_dialogue.py`: add the keyboard-only 1920x1080 journey of the browser-verification scenario "The dialogue stage journey completes by keyboard", annotated with the choices ID and `webclient-browser-verification::browser-acceptance-covers-foundation-recovery-and-layout-behavior`. Re-point every `dialogue-pick` / `dialogue-exit` / `dialogue-freeform` lookup to the list inside `[data-anchor="choices"]`, waiting for `data-typing="false"` and the last page first.
- [ ] 7.2 `test_browser_contextual_hud_anchors.py`: the `choices` anchor geometry at 1920x1080 and 1280x720. `test_browser_shell_command_line.py`: the borrow cases use the list's free row, and a new case covers a borrowed send in a non-active phase. `browser_helpers.py`: an `open_dialogue_choices(page)` helper (complete typing, advance to the last page, wait for `[data-testid="dialogue-choices"]`).
- [ ] 7.3 Re-anchor the nine browser annotations of `webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control` (`test_browser_input_narrative.py` ×3, `test_browser_shell_command_line.py` ×5, `test_browser_exploration_dialogue.py` ×1) to the new ID, and every `the-feed-presents-the-dialogue-variant-from-the-committed-panel` annotation to the choices ID. After this, `grep -rn "the-feed-presents-the-dialogue-variant\|the-collapsible-command-line-preserves-ordinary-text-control\"" web tests` returns nothing.
- [ ] 7.4 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_browser_contextual_hud_anchors web.tests.browser.test_browser_shell_command_line web.tests.browser.test_browser_input_narrative web.tests.browser.test_browser_contextual_hud_stage web.tests.browser.test_browser_layout`; all green.

## 8. Specs and traceability

- [ ] 8.1 Sync this change's deltas into the main specs. Confirm the two new IDs with `uv run --locked python -m tools.spec_traceability list`, and run `uv run --locked python -m tools.spec_traceability check`; green.

## 9. Validation

- [ ] 9.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check`, and `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_evidence web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence`; all green.
- [ ] 9.2 Drive the live client at 1920x1080 with `agent-browser`:
  - 交談 with a scripted host: the greeting types under the plate with no choices, the choices appear centred over the stage once the last page is shown, and `1` sends a pick
  - `⌨ 自由對話` sends a line, and the list returns after the reply
  - `↦ 移動…` shows the exits and Escape returns
  - `✕ 結束對話` ends the conversation

  Close the browser afterwards.
- [ ] 9.3 Run `openspec validate webclient-dialogue-choices-overlay --strict` and `git diff --check`; both clean.
