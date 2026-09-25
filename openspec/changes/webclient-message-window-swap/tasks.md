## 1. Preconditions

- [x] 1.1 Confirm C6a (`webclient-message-pages`) and C6b (`webclient-message-window-component`) are archived:
  - `ls web/webclient-app/components/MessageWindow.vue web/webclient-app/lib/message_pages.js` succeeds
  - `grep -n '"Core/MessageWindow"' web/webclient-app/component-manifest.json` matches
  - the "C6c re-points these" comment block exists in `web/tests/browser/browser_helpers.py`

  Stop and report if any fails.

## 2. Mount the window and the log control

- [x] 2.1 `web/webclient-app/components/AppShell.vue`:
  - replace the `NarrativeFeed` import and mount with `MessageWindow`, passing `lines`, `marks`, `mode`, `dialogue`, `artPanel`, and `fontScale`, and forwarding `dialogue-pick`, `dialogue-freeform`, `dialogue-leave`, and `open-full-log`
  - add the `responseMarks` (Array) and `fontScale` (Number, default 1) props
  - delete the `feed` ref
  - add the `日誌` button per design D1 (`data-testid="message-log-open"`, `aria-label` / `title` `完整日誌`, `@click` emitting `open-full-log`, `@keydown.enter.stop`, `@keydown.space.stop`) between the window and the ⌨ toggle
  - rewrite the header comment (no `#narrative-unread`, no caption)
- [x] 2.2 `web/webclient-app/AppClient.vue`: bind `:response-marks="store.responseMarks"` and `:font-scale="store.view.fontScale"` on `AppShell`. `grep -n "open-full-log" web/webclient-app/AppClient.vue` still reaches `openFullLog`.
- [x] 2.3 `web/webclient-app/styles/app-shell.css`:
  - add the `.message-log-open` rule (`position: absolute; right: 58px; bottom: 18px; height: 30px; z-index: 1`, capsule treatment)
  - delete the `.elosern-root .elosern-narrative*` block, the `.m-dialogue .narrative-scroll` rules (both viewports), and C5's `[data-anchor="band-message"] .narrative-scroll` padding rule

  `grep -n "elosern-narrative\|narrative-scroll\|narrative-head\|narrative-fulllog" web/webclient-app/styles web/webclient-app/components web/webclient-app/AppClient.vue` returns nothing after section 3.
- [x] 2.4 `web/webclient-app/lib/controls-reference.js`: add Enter / Space on the focused message window advancing a page to the Enter row's detail, and add a `日誌` row ("Opens the complete log at its latest line"). Update `tests/overlays/help_overlay.test.js` if it pins row counts.

## 3. Deletions

- [x] 3.1 Delete `web/webclient-app/components/NarrativeFeed.vue`, `components/UnreadIndicator.vue`, `stories/Core/NarrativeFeed.stories.js`, `stories/Core/UnreadIndicator.stories.js`, `tests/narrative_feed.test.js`, and `tests/unread_indicator.test.js`.
  - Remove `"Core/NarrativeFeed"` and `"Core/UnreadIndicator"` from `component-manifest.json` (keep `"frozen": true`) and from the snapshots in `web/webclient/tests/test_vue_showcase_{action,data,world,overlays}_evidence.py`.
  - Update the description in `stories/Core/AppShell.stories.js`.
  - `grep -rn "NarrativeFeed\|UnreadIndicator\|narrative-unread\|narrative_feed" web/webclient-app web/webclient/tests --include='*.js' --include='*.vue' --include='*.json' --include='*.py'` (excluding `dist/`, `node_modules/`) returns nothing after section 4.
- [x] 3.2 Delete the store unread bookkeeping per design D2: `ctx.seenIndex` (`stores/elosern.js`), the trim adjustment (`stores/elosern/transport.js`), `markNarrativeSeen` / `unreadCount` (`stores/elosern/view.js`), their exports in `stores/elosern.js`, and the `unreadCount` case in `tests/store/store_slices.test.js`. `grep -rn "seenIndex\|unreadCount\|markNarrativeSeen" web/webclient-app` returns nothing.

## 4. Vitest and evidence

- [x] 4.1 Rename `tests/dialogue_feed.test.js` to `tests/message_window_dialogue.test.js` and mount `MessageWindow` with a code-point `pageFit`, per design D3. Re-point `tests/full_log_overlay.test.js`'s parity block, `tests/overlays/deferred_surfaces_absent.test.js`, `tests/app.test.js`, `tests/hud_frame.test.js`, and `tests/preserved_contract.test.js`. Fix the header comment in `tests/narrative_line_nodes.test.js`. Run `pnpm test` (repository root), which is green.
- [x] 4.2 `web/webclient/tests/test_node_suite_evidence.py`:
  - `test_dialogue_feed_vitest_evidence_passes` runs `message_window_dialogue.test.js` + `dialogue_view_model.test.js`
  - `test_choicepoint_block_node_suite_passes` drops `narrative_feed.test.js`
  - add `test_message_window_vitest_evidence_passes` (runs `tests/message_window.test.js`), annotated `webclient-input-narrative::the-message-window-s-reading-controls-advance-pages-and-a-new-action-flushes-unread-pages`

## 5. Browser suite

- [x] 5.1 Re-point every rendering assertion listed in the `browser_helpers.py` "C6c re-points these" block, category by category per design D4, then delete that comment block. Update `REQUIRED_SURFACES` / `COMPONENT_SELECTORS` (`test_browser_layout.py`) and `test_vue_foundation.py`'s testid list. After this, `grep -rn "narrative-feed\|narrative-unread\|narrative-fulllog-control\|narrative-head\|narrative-mode-label\|elosern-narrative" web/tests/browser` returns nothing.
- [x] 5.2 Rewrite the unread and scroll-keep journeys in `test_browser_shell_command_line.py` and `test_browser_input_narrative.py` as paging journeys (design D4). Add `test_message_window_pages_and_flushes` and `test_message_window_repages_on_resize` to `test_browser_input_narrative.py`, annotated with the new reading-controls ID and the new message-window ID. Rename any test in `.github/browser-shards.json` whose method name changed (for example, one naming "unread").
- [x] 5.3 Re-anchor the annotations in design D5's table:
  - five annotations to `webclient-contextual-hud::the-message-window-presents-the-current-response-one-page-at-a-time-in-the-band-s-message-region`
  - four to `webclient-desktop-shell::narrative-output-remains-the-authoritative-text-surface-and-is-read-page-by-page`

  `grep -rn "the-narrative-is-a-bounded-caption\|narrative-output-remains-the-authoritative-text-surface\"" web tests` returns nothing.
- [x] 5.4 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_input_narrative web.tests.browser.test_browser_shell_command_line web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_browser_layout web.tests.browser.test_browser_shell_narrative web.tests.browser.test_browser_contextual_hud_stage web.tests.browser.test_browser_contextual_hud_anchors web.tests.browser.test_browser_shell_dock web.tests.browser.test_browser_shell_surfaces web.tests.browser.test_browser_reconnect web.tests.browser.test_browser_actions web.tests.browser.test_browser_options_surface web.tests.browser.test_browser_exploration_actions web.tests.browser.test_browser_art web.tests.browser.test_browser_local_map_interaction web.tests.browser.test_browser_creation_viewport_pointer web.tests.browser.test_browser_combat_menu web.tests.browser.test_vue_foundation`. All green.

## 6. Specs and traceability

- [x] 6.1 Sync this change's deltas into the main specs. Edit the `webclient-contextual-hud` Purpose paragraph if it still names a "narrative caption" or "unread" element. Confirm every new ID with `uv run --locked python -m tools.spec_traceability list`, and run `uv run --locked python -m tools.spec_traceability check`, which is green.

## 7. Validation

- [x] 7.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check`, and `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_showcase_evidence web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence web.webclient.tests.test_node_suite_evidence`. All green.
- [ ] 7.2 Drive the live client at 1920×1080 with `agent-browser`:
  - `look` in a long room shows `▼`, and clicking advances to `■`
  - Enter on the dock activates the dock and does not advance
  - `日誌` opens the full log at its bottom, and Escape returns focus to `日誌`

  Close the browser afterwards.
- [ ] 7.3 Run `openspec validate webclient-message-window-swap --strict` and `git diff --check`. Both clean.
