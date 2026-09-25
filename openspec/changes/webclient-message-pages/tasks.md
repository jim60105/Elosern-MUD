## 1. Preconditions

- [x] 1.1 Confirm C1–C5 (`webclient-minimap-and-log-quick-fixes` … `webclient-collapsible-command-line`) are archived: `ls openspec/changes/archive | grep -c "webclient-collapsible-command-line"` returns 1. Confirm that `grep -n "tokens: kind === \"out\"" web/webclient-app/stores/elosern/transport.js` still matches the append path this change edits. Stop and report if either fails.

## 2. Pure lib

- [x] 2.1 Create `web/webclient-app/lib/box_drawing.js` exporting `BOX_DRAWING = /[\u2500-\u257f]/` and `isBoxDrawing(text)`. Make `lib/narrative_line_nodes.js` import it in place of its local constant. `pnpm exec vitest run web/webclient-app/tests/narrative_line_nodes.test.js` stays green, including the D2 literal-glyph equivalence case, re-pointed to the new module.
- [x] 2.2 Create `web/webclient-app/lib/message_pages.js`. It has no Vue or DOM import and depends only on `lib/narrative_markup.js` and `lib/box_drawing.js`. It exports `segmentResponses(lines, marks)`, `responseBlocks(response)`, `paginate(blocks, fits)`, `pageIndexForOffset(pages, offset)`, and `responseLength(blocks)`, as specified in design D2–D4. Include the file header comment naming the design doc §6.1–§6.2 and this change. Verify with `grep -n "from \"vue\"\|document\.\|window\." web/webclient-app/lib/message_pages.js`, which returns nothing.
- [x] 2.3 Create `web/webclient-app/tests/message_pages.test.js`. The fake `fits` counts code points per line (for example, 10 characters per line and 3 lines per page, with a `break` ending a line). Cover:
  - `in` line and mark boundaries
  - mark-plus-echo counting as one response
  - a pending mark with no line
  - a leading headerless response
  - late lines
  - seq-less fixtures
  - whole-block packing
  - `sys` / `err` forcing a new page
  - hard-break, sentence-end, and closing-quote cuts
  - `……` and `！？` runs
  - clause fallback, character fallback, and a surrogate-pair guard
  - a cut inside nested spans re-opening identical `classes` / `style`, with `degraded` text keeping its flag
  - `map-art` atomicity and the oversize page
  - a one-character-too-small box giving an oversize page
  - losslessness over a randomized corpus with a fixed seed
  - determinism
  - `pageIndexForOffset` before and after re-paging with a narrower fake
  - a non-monotonic fake still paging losslessly

  `pnpm exec vitest run web/webclient-app/tests/message_pages.test.js` is green.
- [x] 2.4 `lib/narrative_line_nodes.js`: `narrativeLineNodes` renders `line.tokens` when it is an array and falls back to `NarrativeMarkup.tokenize(text)` otherwise. Add `narrativeBlockNodes(fragment, key)`, which renders `div.narrative-line.<kind>` with `data-line-kind`, plus `map-art` and `cont` per design D5. Extend `tests/narrative_line_nodes.test.js` with:
  - stored tokens rendering identically to the fallback
  - a fragment carrying its kind and `map-art` classes
  - a `sys` continuation carrying `cont`

  The file is green.

## 3. Store seams

- [x] 3.1 `web/webclient-app/stores/elosern.js`: add `ctx.narrativeSeq = 0` and `ctx.responseMarks = ref([])`, and expose `responseMarks` in the store's returned object next to `narrative`.
- [x] 3.2 `web/webclient-app/stores/elosern/transport.js`:
  - `appendText` assigns `seq = ++ctx.narrativeSeq` and tokenizes `out`, `sys`, and `err` (`in` keeps `tokens: null`).
  - The trim loop also drops `responseMarks` entries below the new oldest `seq`.
  - `dispatchAction` pushes `ctx.narrativeSeq + 1` onto `responseMarks` right after `ctx.sender.sendAction(envelope)` returns and before the echo append. Nothing is pushed on the blocked early return or in the `catch`.
  - Update the comments naming the response boundary (design D1).
- [x] 3.3 Create `web/webclient-app/tests/store/narrative_responses.test.js` against the real store with a stub sender. Cover:
  - a typed `sendText("look")` followed by two `out` lines forming one response
  - a silent `explore.dialogue_leave` dispatch followed by an `out` line forming a new headerless response
  - an echoing `explore.move` giving exactly one response (the mark equals the echo's `seq`)
  - a blocked dispatch (in flight) recording no mark
  - a throwing `sendAction` recording no mark
  - a 510-line flood keeping `seq` monotonic and dropping marks below the oldest line
  - `sys` / `err` lines carrying tokens and `in` lines not

  Update `tests/store/store_slices.test.js` where it projects line shapes (it compares `{kind, text}` only, so assert `seq` is present). Run `pnpm test` (repository root), which is green.

## 4. Browser suite decoupling

- [x] 4.1 `web/tests/browser/browser_helpers.py`: add `narrative_log_text(page)` and `narrative_log_length(page)`, which read `window.__elosernBridge.store.narrative`. Switch `wait_for_narrative_settled` to poll `narrative_log_length`, and update its docstring.
- [x] 4.2 Re-point, per design D6, every hit of `grep -n "narrative-feed\|elosern-narrative" web/tests/browser/*.py` that only waits for, or compares, logged text: the `inner_text()` reads and innerText-length `dom_readiness` predicates in `test_browser_actions.py`, `test_browser_art.py`, `test_browser_combat_panels.py`, `test_browser_exploration_dialogue.py`, `test_browser_layout.py`, `test_browser_local_map_interaction.py`, `test_browser_options_surface.py`, `test_browser_shell_command_line.py`, `test_browser_shell_dock.py`, `test_browser_shell_narrative.py`, and `test_browser_shell_surfaces.py`.
  - Every `before` passed to `wait_for_narrative_settled` is computed with `narrative_log_length`.
  - Leave the rendering assertions listed in design D6 untouched, and list them in a comment block at the top of `browser_helpers.py` as "C6c re-points these".
- [x] 4.3 Run the touched browser modules with `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_actions web.tests.browser.test_browser_art web.tests.browser.test_browser_combat_panels web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_browser_layout web.tests.browser.test_browser_local_map_interaction web.tests.browser.test_browser_options_surface web.tests.browser.test_browser_shell_command_line web.tests.browser.test_browser_shell_dock web.tests.browser.test_browser_shell_narrative web.tests.browser.test_browser_shell_surfaces`. All green.

## 5. Specs and traceability

- [x] 5.1 `web/webclient/tests/test_node_suite_evidence.py`:
  - Add `test_message_pages_vitest_evidence_passes`. It runs `tests/message_pages.test.js` and `tests/store/narrative_responses.test.js` through `npx --no-install vitest run`, like `test_dialogue_feed_vitest_evidence_passes`, and is annotated `@covers_requirement("webclient-input-narrative::the-narrative-log-is-segmented-into-responses-at-each-player-action", "webclient-input-narrative::a-response-is-cut-into-pages-that-fit-a-measured-box-and-never-mid-sentence")`.
  - Add `tests/narrative_line_nodes.test.js` to the file list of `test_choicepoint_block_node_suite_passes` (the `narrative-lines-carry-the-reference-s-semantic-classes` evidence).
  - Confirm both IDs with `uv run --locked python -m tools.spec_traceability list` after syncing the deltas.
- [x] 5.2 Sync this change's deltas into the main specs and run `uv run --locked python -m tools.spec_traceability check`, which is green.

## 6. Validation

- [x] 6.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check`, and `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence`. All green.
- [x] 6.2 Run `openspec validate webclient-message-pages --strict` and `git diff --check`. Both clean.
