## 1. Preconditions

- [x] 1.1 Confirm C6a (`webclient-message-pages`) is archived and its seams exist:
  - `grep -n "export function paginate\|export function segmentResponses\|export function pageIndexForOffset" web/webclient-app/lib/message_pages.js` returns three lines
  - `grep -n "narrativeBlockNodes" web/webclient-app/lib/narrative_line_nodes.js` matches
  - `grep -n "responseMarks" web/webclient-app/stores/elosern.js` matches

  Stop and report if any is missing.

## 2. Tokens and measurement

- [x] 2.1 `web/webclient-app/styles/tokens.css`: add `--message-text: clamp(20px, 2.593vh, 38px)`, `--message-line-height: 1.4`, and `--message-controls-h: 36px`, with a comment citing design §5.1 (28px at 1080, ≤ 42 CJK characters per line). `pnpm run build` is green.
- [x] 2.2 Create `web/webclient-app/composables/use-message-measure.js` per design D2:
  - the hidden measurer inside the text area
  - `fits(fragments)` through Vue's `render()` and `narrativeBlockNodes`, cleared with `render(null, …)` after each pass
  - `ready` gated on `document.fonts.ready`, true when `document.fonts` is absent
  - `boxKey` from a `ResizeObserver` on the page surface, disconnected on unmount
  - the measurer carries the page's own class, overridden to content height by the compound `.message-window__page.message-window__measure` rule

## 3. Component

- [x] 3.1 Create `web/webclient-app/components/MessageWindow.vue`:
  - props `lines`, `marks`, `mode`, `dialogue`, `artPanel`, `fontScale`, and `pageFit`; emits `dialogue-pick`, `dialogue-freeform`, `dialogue-leave`, `open-full-log`
  - the layout, text size, and 36px control strip of design D1, and the marker (`data-testid="message-page-marker"`, `▼` blinking on `--motion-pulse`, `■` on the last page)
  - an oversize page with `data-oversize="true"` and `overflow-y: auto`
  - the header comment names the design doc §6, this change, the `pageFit` test seam, and the key scope rule
- [x] 3.2 In `MessageWindow.vue`, implement the reader state of design D3: mount on the last page, a new response on page 1, a pending mark flushing to the previous response's last page, appended lines keeping the page, re-page by the anchor offset, and the first block unpaged before fonts are ready.
- [x] 3.3 In `MessageWindow.vue`, implement the reading controls of design D4:
  - click to advance, except on buttons and links and with a non-collapsed selection
  - Enter/Space on the page surface only, with `preventDefault` + `stopPropagation` and repeats ignored
  - wheel-up emitting `open-full-log`
  - the hidden `第 N／M 頁` description
- [x] 3.4 In `MessageWindow.vue`, implement the live region of design D5 (`data-testid="message-live"`), announcing once per fragment and never on mount or re-page.
- [x] 3.5 In `MessageWindow.vue`, port the dialogue variant from `components/NarrativeFeed.vue` per design D6: the `dialogueNodes` markup and test ids (`dialogue-box`, `dialogue-who`, `dialogue-bond`, `dialogue-say`, `dialogue-choices`, `dialogue-pick`, `dialogue-freeform`, `dialogue-exit`), the anchored echo match and residual, the box pin, and the variant CSS. `NarrativeFeed.vue` is left untouched (C6c deletes it).

## 4. Story, manifest, tests

- [x] 4.1 Create `web/webclient-app/stories/Core/MessageWindow.stories.js` (title `Core/MessageWindow`). It has a 1280×300 decorator box, `seq`'d fixture lines and marks, and the stories `SinglePage`, `MorePages`, `LastPage`, `ErrorPage`, `OversizeMap`, `PendingAction`, and `Dialogue`, with the dialogue args bound through `dialogueViewModel` from `stores/dialogue-view.js`, as the showcase derived-shape rule requires. The component docs description names the controls and the key scope.
- [x] 4.2 `web/webclient-app/component-manifest.json`: add `"Core/MessageWindow"` after `"Core/UnreadIndicator"` (keep `"frozen": true`). Add the title to the manifest snapshots in `web/webclient/tests/test_vue_showcase_action_evidence.py`, `test_vue_showcase_data_evidence.py`, `test_vue_showcase_world_evidence.py`, and `test_vue_showcase_overlays_evidence.py`, and fix any comment stating a manifest count. Run `pnpm run showcase-coverage`, which is green.
- [x] 4.3 Create `web/webclient-app/tests/message_window.test.js` with a code-point `pageFit` and mocked `ResizeObserver` / `document.fonts`. Cover:
  - the first page and its marker (`▼` versus `■`)
  - click advance, with no advance on a dialogue button or with a selection
  - Enter and Space on the surface advancing, while a document-level `keydown` spy sees nothing
  - Enter with focus outside the surface doing nothing
  - repeat ignored
  - a new response opening on page 1
  - a pending mark jumping to the previous response's last page
  - an `in` echo that lands before any reply line keeping the previous response on its last page (never blank)
  - mount on the last page with no announcement
  - appended lines keeping the page
  - a `fontScale` change and a box change re-paging to the anchor's page
  - unready fonts showing the first block unpaged
  - the live region naming each page once and nothing on re-page
  - an oversize page with `data-oversize="true"`
  - wheel-up emitting `open-full-log`
  - the dialogue variant: box, speaker and bond, reply once, picks, free and exit rows, emits, echo suppression and residual hint, no marker, no Enter interception

  `pnpm exec vitest run web/webclient-app/tests/message_window.test.js` is green.
- [x] 4.4 `web/webclient/tests/test_node_suite_evidence.py`: add `tests/message_window.test.js` to the file list of `test_choicepoint_block_node_suite_passes`, the `narrative-lines-carry-the-reference-s-semantic-classes` evidence. The window renders lines through the same classes.

## 5. Specs

- [x] 5.1 Sync this change's showcase delta into `openspec/specs/webclient-component-showcase/spec.md`. Run `uv run --locked python -m tools.spec_traceability check`, which is green (no ID changes).

## 6. Validation

- [x] 6.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check`, and `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence web.webclient.tests.test_node_suite_evidence`. All green.
- [x] 6.2 Open the `Core/MessageWindow` stories in the built Storybook (`pnpm run serve-storybook`, or `.storybook-out`) with `agent-browser`. Check that `MorePages` shows `▼`, that clicking advances to `■`, and that `OversizeMap` scrolls internally. Close the browser afterwards.
- [x] 6.3 Run `openspec validate webclient-message-window-component --strict` and `git diff --check`. Both clean.
