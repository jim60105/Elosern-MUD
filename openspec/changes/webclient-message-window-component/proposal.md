## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §5.1, §5.2, §6.2, §6.3, §12) replaces `NarrativeFeed` with a `MessageWindow`:

- It shows the current response one page at a time, at a reading size of 28px at 1080 with at most 42 CJK characters per line.
- Click, Enter, or Space advances to the next page.
- It marks more pages with `▼` and the last page with `■`.
- It flushes unread pages when a new action begins a response.
- It announces each page once.
- It re-pages on resize or a `fontScale` change without losing the reader's place.

`webclient-message-pages` (C6a) provides the pure segmentation and paging functions and the store's response marks. This change (C6b) builds the component that measures real layout and holds the reader's state, together with its story, tests, and manifest entry. It does not mount the component. The component-showcase governance ("a component SHALL NOT be wired into the live application before its story exists") makes build-then-mount the intended order, and it keeps the swap (`webclient-message-window-swap`, C6c) small.

## What Changes

- New governed component `web/webclient-app/components/MessageWindow.vue`. It is a band-message surface that fills its host.
  - **Props:**
    - `lines` (the narrative log) and `marks` (the store's `responseMarks`)
    - `mode`, `dialogue` (the dialogue view model), `artPanel`
    - `fontScale` (a re-page trigger)
    - `pageFit`: an injected measurement seam for Vitest. The live wiring passes none, and the DOM measurer is used.
  - **Emits:** `dialogue-pick`, `dialogue-freeform`, `dialogue-leave`, `open-full-log`.
  - **Paged presentation:**
    - The page surface (`data-testid="message-page"`, `tabindex="0"`) renders the current page's fragments through C6a's `narrativeBlockNodes`.
    - An oversize page scrolls inside the surface (`data-oversize="true"`).
    - A decorative marker (`data-testid="message-page-marker"`) reads `▼` while more pages remain, and blinks through the motion tokens. It reads `■` on the last page.
  - **Reading controls:**
    - A click on the window advances unless the pointer landed on a control or text is selected.
    - Enter or Space advances only while focus is on the page surface itself. The handler stops propagation, so the document keyboard bridge never sees the key.
    - Scrolling up over a non-scrollable page emits `open-full-log`.
  - **Reader state:**
    - A new response starts on page 1.
    - A response mark with no line yet keeps the previous response on its last page.
    - A mount shows the last page of the last response, fully read.
    - A re-page (ResizeObserver on the text area, a `fontScale` change, or `document.fonts.ready`) keeps the reader on the page holding the first character that was on screen.
    - Until fonts are ready, the window shows the current response's first block unpaged.
  - **Live region:** a visually hidden polite region (`data-testid="message-live"`, `role="status"`, `aria-atomic="true"`) announces each shown page's text once, and never again on a re-page.
  - **Dialogue variant:** while mode is `dialogue` and the panel is available, the window renders today's dialogue box (avatar, speaker line, reply), the current response's residual lines, the pick rows, the free-dialogue row, and the exit row. They are ported from `NarrativeFeed.vue` with its echo-suppression match, unpaged and scrolling inside the text area. No page marker is shown and Enter/Space are not intercepted.
- New composable `web/webclient-app/composables/use-message-measure.js`. It owns:
  - the hidden measurer (same width, classes, and font as the text area)
  - the DOM `fits`, which renders candidate fragments with Vue's `render()` and compares heights
  - the ResizeObserver and the `document.fonts.ready` gate
- `web/webclient-app/styles/tokens.css`: `--message-text: clamp(20px, 2.593vh, 38px)` (28px at 1080), `--message-line-height: 1.4`, and `--message-controls-h: 36px`.
- New story `web/webclient-app/stories/Core/MessageWindow.stories.js` with deterministic args: one page, several pages (`▼`), last page (`■`), an error page, an oversize map, a pending action, and the dialogue variant.
- `component-manifest.json` gains `Core/MessageWindow`, and the four showcase-evidence manifest snapshots gain it too.
- `NarrativeFeed` and `UnreadIndicator` stay mounted and unchanged. No store, OOB schema, presenter, server, or persistence change.

Out of scope:
- Mounting the window in `band-message`, the 日誌 control beside ⌨, deleting `NarrativeFeed` / `UnreadIndicator` / the store's unread members, and the reading-behaviour requirements: `webclient-message-window-swap` (C6c).
- Typewriter reveal, `textSpeed`, and `autoAdvance`: `webclient-typewriter-reading-prefs` (C7).
- Paging the dialogue line, the name plate, and moving choices over the stage: `webclient-dialogue-stage` (C10).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-component-showcase`: "Every required UI component is a Vue SFC with a documented Storybook story", on C4b's text. The required manifest adds the message window.

## Impact

- New:
  - `web/webclient-app/components/MessageWindow.vue`
  - `web/webclient-app/composables/use-message-measure.js`
  - `web/webclient-app/stories/Core/MessageWindow.stories.js`
  - Vitest `web/webclient-app/tests/message_window.test.js`
- Edited:
  - `web/webclient-app/component-manifest.json`, `web/webclient-app/styles/tokens.css`
  - `web/webclient/tests/test_vue_showcase_{action,data,world,overlays}_evidence.py`
  - `web/webclient/tests/test_node_suite_evidence.py`, which runs `message_window.test.js` inside the existing semantic-classes evidence test
- Spec traceability: no ID changes.
- Dependencies:
  - Archive order: C5 → C6a (`webclient-message-pages`) → C6b (this change) → C6c.
  - This change imports C6a's `lib/message_pages.js`, `narrativeBlockNodes`, and `store.responseMarks`.
  - Its showcase block is written on C4b (`webclient-avg-place-card-top-bar`), and C6c modifies it again.
