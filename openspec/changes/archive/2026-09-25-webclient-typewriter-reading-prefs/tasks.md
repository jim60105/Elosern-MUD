## 1. Preconditions

- [x] 1.1 Confirm C6a, C6b, and C6c are archived:
  - `ls web/webclient-app/components/MessageWindow.vue web/webclient-app/lib/message_pages.js` succeeds
  - `grep -n "MessageWindow" web/webclient-app/components/AppShell.vue` matches
  - `grep -n "message-log-open" web/webclient-app/components/AppShell.vue` matches
  - `grep -n "The message window's reading controls" openspec/specs/webclient-input-narrative/spec.md` matches

  Stop and report if any fails.
- [x] 1.2 Find C6a's span-preserving cut in `web/webclient-app/lib/message_pages.js` (the routine `paginate` uses to split a fragment's tokens, design D1), and C6b's "page shown" handler and `anchorOffset` in `MessageWindow.vue`. Note their names for sections 2 and 4.

## 2. Pure reveal lib

- [x] 2.1 `web/webclient-app/lib/message_pages.js`: export `splitTokensAt(tokens, n)`, returning `{ head, tail }`. Either expose the existing cut or refactor it into this function, so `paginate` and the reveal share one routine. The head closes open spans, the tail re-opens shallow copies, and `degraded` is kept on both halves. Extend `tests/message_pages.test.js` with direct cases (nested spans, a cut at a `break`, a surrogate pair). `pnpm exec vitest run web/webclient-app/tests/message_pages.test.js` is green.
- [x] 2.2 Create `web/webclient-app/lib/message_reveal.js` per design D2/D4/D7:
  - `TEXT_SPEEDS` and `TEXT_SPEED_CPS`
  - `pageUnits`, `snapUnits`, `fragmentReveal`, `offsetAtUnits`, `unitsAtOffset`
  - `autoAdvanceDelayMs`, `autoAdvanceAllowed`

  It imports nothing from Vue. The header cites design §6.3/§6.4 and this change.
- [x] 2.3 Create `web/webclient-app/tests/message_reveal.test.js`. Cover:
  - units, including breaks and a dropped-break gap between fragments
  - `fragmentReveal` at 0, mid-fragment, and at the end
  - the map-art snap
  - offset/units round-trips
  - `autoAdvanceDelayMs` (100 units gives 7200)
  - `autoAdvanceAllowed` false for `oversize` and for `mapArt`

  `pnpm exec vitest run web/webclient-app/tests/message_reveal.test.js` is green.
- [x] 2.4 `web/webclient-app/lib/narrative_line_nodes.js`: `narrativeBlockNodes(fragment, key, reveal)` per design D1.
  - With `reveal` undefined, or at least the fragment's length, the output is unchanged.
  - With `reveal` 0, it adds the `unrevealed` class.
  - Otherwise it renders the head, then `span.narrative-unrevealed` (`aria-hidden="true"`) with the tail.

  Extend `tests/narrative_line_nodes.test.js`: the unchanged output with no `reveal`, and head + tail markup equal to the unsplit markup once the wrapper is removed. `pnpm exec vitest run web/webclient-app/tests/narrative_line_nodes.test.js` is green.

## 3. Composables

- [x] 3.1 Create `web/webclient-app/composables/use-typewriter.js` per design D3:
  - the rAF clock with a 100ms frame clamp
  - `typed`, `typing`, `start`, `complete`, and `stop`
  - `armAdvance` and `disarmAdvance`, with the countdown frozen while `held()` is true
  - `Infinity` cps completing synchronously
  - the frame cancelled on stop and on unmount
- [x] 3.2 Create `web/webclient-app/composables/use-reduced-motion.js` per design D4. The override is `"on"` / `"off"` / `null`. A live `matchMedia` `change` listener is removed on unmount, and a missing `matchMedia` gives `false`. The header notes that C11 (`webclient-motion-layer`) replaces it with `motionLevel`.

## 4. MessageWindow typing

- [x] 4.1 `web/webclient-app/components/MessageWindow.vue`:
  - add the props `textSpeed` (String, default `"normal"`, validated against `TEXT_SPEEDS`), `autoAdvance` (Boolean), `reducedMotion` (`[String, null]`), and `held` (Boolean)
  - render the page through `narrativeBlockNodes(fragment, key, reveal)` with `fragmentReveal(page, typed)`
  - add the `.narrative-unrevealed, .narrative-line.unrevealed { visibility: hidden }` rules
  - add `data-typing` on the root, and `!typing` to the marker's `v-if`
  - update the header comment (this change, the reveal approach, and "the dialogue variant does not type")
- [x] 4.2 In `MessageWindow.vue`, wire the reader-state table of design D5:
  - the announcement stays at the page-shown moment
  - mount completes the page
  - a flush completes the page and disarms auto-advance
  - appended lines resume typing
  - click and Enter/Space complete the page while `typing`, and advance otherwise (the key-scope and repeat rules are unchanged)
  - a speed change to `instant` or into reduced motion completes the page
- [x] 4.3 In `MessageWindow.vue`, move the re-page anchor to the typing position per design D6, replacing C6b's first-on-screen anchor.
- [x] 4.4 In `MessageWindow.vue`, implement auto-advance per design D7: arm and disarm, `held` pause, and no advance past the last, oversize, or map page. The dialogue variant (`data-variant="dialogue"`) never types or arms.
- [x] 4.5 Update the shared mount helper in `web/webclient-app/tests/message_window.test.js` to pass `textSpeed: "instant"`, so C6b's instant-page cases keep their meaning, and move its prose-scale case to the last-character anchor (design D6). Pass `textSpeed: "instant"` to the `MessageWindow` mount in `tests/full_log_overlay.test.js`. Create `web/webclient-app/tests/message_window_typing.test.js` covering the list in design D11, with fake `requestAnimationFrame` / `performance` and a mocked `matchMedia`. `pnpm exec vitest run web/webclient-app/tests/message_window.test.js web/webclient-app/tests/message_window_typing.test.js web/webclient-app/tests/message_window_dialogue.test.js` is green.
- [x] 4.6 `web/webclient-app/stories/Core/MessageWindow.stories.js`:
  - existing stories set `textSpeed: "instant"`
  - add a `Typing` story (`textSpeed: "normal"`) and an `AutoAdvance` story (`autoAdvance: true`, three pages)
  - add argTypes for the four new props

## 5. Preferences, layout store, settings

- [x] 5.1 `web/static/webclient/js/elosern/layout_store.js` per design D10:
  - `CURRENT_LAYOUT_VERSION = 2`
  - `PREFERENCE_ENUMS = { textSpeed: ["slow", "normal", "fast", "instant"] }`
  - `PREFERENCE_TYPES` gains `textSpeed: "enum"` and `autoAdvance: "boolean"`, and `normalizePreferences` gets the enum branch
  - the `defaultWrapper()` preferences
  - default `migrations` `{}`
  - export `PREFERENCE_ENUMS`, and update the comments that say "version 1" or "no layout-version bump"

  `web/webclient-app/main.js`: fix the comment "reset … to the version-1 default".
- [x] 5.2 `web/static/webclient/js/tests/layout_store.test.js`:
  - replace the literal `layout_version: 1` wrappers with `LayoutStore.CURRENT_LAYOUT_VERSION`
  - rewrite "a version-1 wrapper lacking the H5 preference keys still normalizes without a version bump" as "a version-1 wrapper resets to the version-2 default"
  - add cases for the enum (an invalid `textSpeed` is dropped while the other keys are kept) and `autoAdvance`
  - assert that `LayoutStore.PREFERENCE_ENUMS.textSpeed` equals `TEXT_SPEEDS` from `web/webclient-app/lib/message_reveal.js` (import it in the test)

  `node --test web/static/webclient/js/tests/layout_store.test.js` is green.
- [x] 5.3 `web/webclient-app/stores/elosern/preferences.js`:
  - `prefs.textSpeed`, `prefs.autoAdvance`, `ctx.setTextSpeed`, and `ctx.setAutoAdvance`
  - load validation, and persisting both keys
  - the header comment

  `stores/elosern/view.js`: publish `textSpeed` and `autoAdvance`. `stores/elosern.js`: export `setTextSpeed` and `setAutoAdvance`. Create `web/webclient-app/tests/store/reading_preferences.test.js`: defaults, a set and persist round-trip, an invalid value ignored, and a version-1 wrapper reset. `pnpm exec vitest run web/webclient-app/tests/store/reading_preferences.test.js` is green.
- [x] 5.4 `web/webclient-app/components/SettingsOverlay.vue`: add the `文字速度` segment and the `自動翻頁` toggle with the testids, labels, and descriptions of design D10, plus the props and emits, and update the header comment. `web/webclient-app/AppClient.vue` binds `:text-speed`, `:auto-advance`, `@text-speed-change="store.setTextSpeed"`, and `@auto-advance-change="store.setAutoAdvance"` on `SettingsOverlay`. Extend `tests/overlays/settings_overlay.test.js`: both controls render, the non-colour pressed indicator, and both emits.
- [x] 5.5 `web/webclient-app/stories/Overlays/SettingsOverlay.stories.js`: add the new args to `Default`, and add a `ReadingPreferences` story (`textSpeed: "fast"`, `autoAdvance: true`). Add `"overlays-settingsoverlay--reading-preferences"` to `OVERLAYS_STORY_IDS` in `web/webclient/tests/test_vue_showcase_overlays_evidence.py`.

## 6. Shell wiring and help text

- [x] 6.1 `web/webclient-app/components/AppShell.vue`: add the props `textSpeed`, `autoAdvance`, and `reducedMotion`, and pass them with `:held="openSurfaces.length > 0"` to `MessageWindow`. `web/webclient-app/AppClient.vue`: bind `:text-speed="store.view.textSpeed"`, `:auto-advance="store.view.autoAdvance"`, and `:reduced-motion="store.view.reducedMotion"` on `AppShell`. `grep -n "held\|text-speed\|auto-advance" web/webclient-app/components/AppShell.vue` shows the bindings.
- [x] 6.2 `web/webclient-app/lib/controls-reference.js`: the message-window note on the Enter row reads that Enter or Space on the focused message window first shows a typing page in full, then advances. Update `tests/overlays/help_overlay.test.js` only if it pins that text. `pnpm test` (repository root) is green.

## 7. Evidence and browser

- [x] 7.1 `web/webclient/tests/test_node_suite_evidence.py`: add `test_message_window_typing_vitest_evidence_passes`, which runs `tests/message_window_typing.test.js` and `tests/message_reveal.test.js`, annotated `webclient-input-narrative::a-page-types-in-at-the-reader-s-text-speed-and-auto-advance-is-opt-in`.
- [x] 7.2 `web/tests/browser/browser_helpers.py`: add `wait_for_page_shown(page, timeout=15000)`, which waits for `[data-testid="message-window"][data-typing="false"]`. For each `message-page` assertion that reads `inner_text()`, `text_content()`-based visible text, or `is_visible()`, call the helper first (or press Enter on `message-page` to complete, where the journey already advances). The search is `grep -n "message-page" web/tests/browser/test_browser_shell_narrative.py web/tests/browser/test_browser_exploration_actions.py web/tests/browser/test_browser_input_narrative.py web/tests/browser/test_browser_shell_command_line.py`. In C6c's paging journeys, each advance becomes "complete, then advance" where the page is typing.
- [x] 7.3 `web/tests/browser/test_browser_layout.py`: the stored-wrapper literals (`"layout_version": 1` in `test_known_layout_version_persists_across_reload` and in the oversized-wrapper step, and the two `== 1` assertions) become 2. The migration probe keeps its explicit `currentVersion: 1` / `migrations: {0: …}`. Add to `test_unknown_malformed_layout_resets` a version-1 wrapper step that asserts the reset to version 2. Leave the snapshot-envelope `layout_version` literals elsewhere untouched (design Context).
- [x] 7.4 `web/tests/browser/test_browser_input_narrative.py`: add `test_message_page_types_and_completes`, `test_reduced_motion_pages_are_instant`, and `test_reading_preferences_persist` per design D11. Annotate the first two with the new input-narrative ID, and the third with `webclient-contextual-hud::text-speed-and-auto-advance-are-client-local-reading-preferences-the-settings-surface-owns`. Add the three test methods to the shard in `.github/browser-shards.json` that already lists `test_browser_input_narrative`'s methods.
- [x] 7.5 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_input_narrative web.tests.browser.test_browser_shell_narrative web.tests.browser.test_browser_exploration_actions web.tests.browser.test_browser_shell_command_line web.tests.browser.test_browser_layout web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_vue_transport_mount`. All green.

## 8. Specs and traceability

- [x] 8.1 Sync this change's deltas into `openspec/specs/webclient-input-narrative/spec.md`, `openspec/specs/webclient-contextual-hud/spec.md`, and `openspec/specs/webclient-desktop-shell/spec.md`. Confirm both new IDs with `uv run --locked python -m tools.spec_traceability list`, and run `uv run --locked python -m tools.spec_traceability check`, which is green.

## 9. Validation

- [x] 9.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check`, and `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_overlays_evidence web.webclient.tests.test_vue_showcase_evidence`. All green.
- [x] 9.2 Drive the live client at 1920×1080 with `agent-browser`. Check:
  - `look` in a long room types page 1 with no marker, a click completes it and shows `▼`, and a second click advances
  - at `瞬間` pages appear whole
  - with `自動翻頁` on, pages advance and stop at `■`
  - opening `日誌` holds the auto-advance

  Close the browser afterwards.

  Done against the built Storybook's `Core/MessageWindow` `Typing` and `AutoAdvance` stories (real layout and measurer, no game server): mid-typing with no marker, click to complete, click to advance, and auto-advance to `■`. The browser journeys of 7.4 cover the live client (typing, Enter completing, unchanged line boxes, reduced motion, persisted preferences, and auto-advance after a reload), and Vitest covers the `held` pause.
- [x] 9.3 Run `openspec validate webclient-typewriter-reading-prefs --strict` and `git diff --check`. Both clean.
