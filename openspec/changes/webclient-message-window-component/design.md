## Context

See proposal.md (Why). C1–C5 and C6a (`webclient-message-pages`) are assumed archived first. Facts this design relies on, checked in code or in the earlier changes:

- C6a provides the following. From `lib/message_pages.js`:
  - `segmentResponses(lines, marks)` gives responses `{ startSeq, header, blocks }`.
  - `responseBlocks`.
  - `paginate(blocks, fits)` gives pages `{ blocks: [fragment], oversize }`, where a fragment is `{ kind, seq, mapArt, first, tokens, start, end }`.
  - `pageIndexForOffset(pages, offset)`.

  From elsewhere:
  - `lib/narrative_line_nodes.js` `narrativeBlockNodes(fragment, key)`.
  - The store's `responseMarks` ref.
  - Lines carry `seq`.
- After C4a and C5, the band message region (`[data-anchor="band-message"]`) is `position: relative` and holds `NarrativeFeed`. Its padding is `10px 12px 12px 18px`, and it is 300.24px tall at 1080 (`--band-h`).
  - `AppShell` renders the ⌨ toggle (`data-testid="command-line-toggle"`) at `right: 22px; bottom: 18px`, 30×30.
  - C5 gave `.narrative-scroll` `padding-bottom: 36px`.
  - C6c adds a 日誌 button beside the toggle.
- `NarrativeFeed.vue` holds the dialogue variant:
  - `dialogueNodes(vm)`: the `.dlg` box with avatar via `portraitFor` / `portraitGlyph` / `faceObjectPosition`, the `.who` / `.who-bond` / `.say` lines, and the `.choices` with `.pick` rows (`dialogue-pick`, `dialogue-freeform`, `dialogue-exit`)
  - the anchored echo-suppression (`renderedLines`)
  - the box pin
- The document keyboard bridge (`web/webclient-app/bridge.js` `onDocumentKeydown`) sends every non-editable, non-modified key to `store.focusPress`. It skips Enter only on a focused `button` / `[role=button]`. Enter confirms the dock's focused item and Space toggles dock multi-select.
- `--prose-scale` is written on `<html>` by `stores/elosern/preferences.js`. A scale change does not resize the band, so a ResizeObserver does not see it.
- Motion: the blink uses `--motion-pulse`, which the reduced-motion blocks in `styles/tokens.css` shorten to 1ms.

## Goals / Non-Goals

**Goals:**
- A self-contained, story-documented window that reproduces design §6.2–§6.3 with instant pages (no typewriter).
- Real measurement in the browser, and a deterministic injected fit in Vitest.
- Keyboard advance that cannot collide with the dock.

**Non-Goals:**
- Mounting, the 日誌 control, and retiring the feed (C6c).
- Typewriter reveal, text speed, and auto-advance (C7). The component keeps one "page shown" moment that C7 turns into "typing started / finished".
- Paging the dialogue line and moving choices (C10).

## Decisions

### D1. Layout: a text area above a fixed control strip
The root `section.message-window` (`data-testid="message-window"`, `data-mode`, `data-variant="paged|dialogue"`) fills its host (`height: 100%`, a flex column).
- The text area `div.message-window__text` takes `flex: 1; min-height: 0`.
- A bottom strip of `var(--message-controls-h)` (36px) is left empty. The page marker sits in it, and C6c's 日誌 and C5's ⌨ occupy its right end (`right: 22px` … about 96px).
- The marker `span.message-window__marker` is absolutely placed at `right: 104px; bottom: 12px` and `aria-hidden="true"`. It never takes part in measurement.
  - `▼` (`data-state="more"`) is gold with a soft glow. It bobs 3px and dims on a period of `calc(var(--motion-pulse) / 3)` (about 1.07s), a token-derived duration that the reduced-motion blocks shorten.
  - `■` (`data-state="end"`) is smaller, static, and a darker gold.
- The window draws no card of its own. The band behind it is the frame: its gradient and hairline top edge already run under both regions, and a second card inside the band would double the frame. A 1px ink rule runs down the window's left edge and turns into a 2px gold rule while the page surface has keyboard focus (`:has(.message-window__page:focus-visible)`). This is the surface's focus indicator.
- There is no head row. The mode label moves out of the band, as the design's reference geometry shows no caption head. The dialogue box carries its own speaker line.

Page text inside the text area:
- `font-size: calc(var(--message-text) * var(--prose-scale))`, `line-height: var(--message-line-height)`, and the serif reading face.
- The page surface is a centred column, `max-width: calc(42em + 48px)`, with `padding: 0 24px` and no vertical padding. The 42em text measure holds, and every vertical pixel goes to the line budget. The line's own half-leading (0.2em) plus the region's 10px padding give the top breathing room.
- Consecutive lines are separated by `0.2em`. The measurer sees the same margin.
- In CJK one character is one em, so the measure is at most 42 characters whatever the width.
- `--message-text` is `clamp(20px, 2.593vh, 38px)`: 28.0px at 1080, 23.3px at 900, 20px at 720, and 37.3px at 1440.
- `.narrative-line.sys` uses `0.75em` sans with the `◈` marker; `.sys.cont` hides the marker.
- `.narrative-line.map-art` uses the mono stack at `0.6em`, `white-space: pre`, and `line-height: 1.15`, so vertical box strokes join.
- `.err` keeps the seal colour and italic.

Resulting capacity at the default scale:
- 1920×1080: the region is 1280px wide, 1250px after padding, and the 42em cap makes the text 1176px wide. Height is 300 − 22 − 36 = 242px, and 242 ÷ 39.2 gives 6 lines. Measured in the story at 1920×1080, the surface is 241px tall and a 6-line block fits.
- 1280×720: about 823px wide (41 characters), and 260 − 22 − 36 = 202px ÷ 28 gives 7 lines.

*Alternative:* keep today's 14px feed size. Rejected, because the design fixes 28px at the reference size and the ≤42 measure.

### D2. Measurement: a hidden twin of the text area and Vue's `render()`
`useMessageMeasure(surfaceRef)` creates one measurer on mount, next to the page surface inside the text area:
- The measurer is `div.message-window__page.message-window__measure`. It carries the page's own class, so it gets the same font, width cap, and padding.
- The compound selector `.message-window__page.message-window__measure` overrides the page's `height: 100%` with `position: absolute; top: 0; left: 0; right: 0; height: auto; overflow: visible; visibility: hidden; pointer-events: none`. The measurer is `aria-hidden="true"`.
- The measurer nests the fragments one level deeper than the live page, inside an unstyled `div.message-window__measure-flow`. The window's CSS therefore uses no child combinators.

`fits(fragments)`:
1. calls `render(h("div", { class: "message-window__measure-flow" }, fragments.map(narrativeBlockNodes)), measurer)`, which is synchronous
2. returns `measurer.getBoundingClientRect().height <= surface.getBoundingClientRect().height + 0.5`. Both are fractional layout heights; the 0.5px slack absorbs sub-pixel rounding.
3. `clear()` (`render(null, measurer)`) empties it after each paging pass

The composable is called before the window registers its own `onMounted`, so the measurer exists before the first paging pass.

The composable exposes:
- `ready`: false until `document.fonts.ready` resolves, or immediately true when `document.fonts` is absent
- `boxKey`: the surface's rounded `${width}x${height}`, updated by a `ResizeObserver` on the surface (disconnected on unmount)
- `fits`

`MessageWindow` re-pages when any of `boxKey`, `ready`, the variant, or the displayed response's key, blocks, or awaiting state change (one post-flush watcher). A `fontScale` change re-pages one tick later, so the new `--prose-scale` on `<html>` is in effect. A generation counter drops that deferred pass when a newer pass has already run.

*Why render real vnodes:* the fit must see exactly the markup the page will render, including span classes, `<br>`, sys sizing, and map-art `pre`. A string-width estimate would drift from the renderer.

*Alternative:* a canvas `measureText`. Rejected, because it ignores wrapping rules, inline spans, and CSS.

`pageFit` (prop) replaces `fits` when provided. Vitest and nothing else passes it. It is documented as a test seam in the component header.

### D3. Reader state
The state is:
- `responseKey`: the displayed response's `s<startSeq>`, or `i<index>` when it has no numeric `startSeq` (the headerless leading response, and fixtures without `seq`)
- `pageIndex`
- `anchorOffset`: the response offset of the first character of the page on screen

Transitions:
- **Mount:** open the last response on its last page. Nothing is announced: that text was already read or announced before the component mounted. This is also the resync rule in design §12. The log survives a reconnect in the store, so a remount shows the last page, fully shown.
- **New response** (`responseKey` changes to a newer start): `pageIndex = 0`. The earlier response's unread pages are simply no longer presented and remain in the full log. This is the flush in design §6.3.
- **Awaiting a reply** (the reader acted, and nothing of the reply is on the log yet). This covers two cases:
  - A pending mark: the store's last mark is greater than the last line's `seq`, so a dispatch is out and no line has arrived.
  - A header-only response: the action's `in` echo has landed, which starts a response with no blocks, but no reply line has arrived yet. The echo's `seq` equals the mark, so the pending test alone would already be false here.

  In both cases the displayed response is the latest response that has blocks, and it jumps to its last page. The unread pages are flushed at once, and the window never blanks between an action and its reply. The first reply line gives the new response its blocks, and it opens on page 1.
- **Lines appended to the current response:** keep `pageIndex`. New pages appear behind it and the marker turns `▼`.
- **Re-page** (box, scale, or fonts change): `pageIndex = pageIndexForOffset(pages, anchorOffset)`.

*Why the anchor is the first character on screen:* with instant pages, everything on screen is shown at once. Anchoring to that page's first character guarantees that nothing the reader may still be reading leaves the screen. C7 moves the anchor to the typing position.

- **Advance:** if `pageIndex < pages.length − 1`, increment it, update `anchorOffset`, and announce. On the last page it is a no-op.
- **Before fonts are ready:** the window shows the current response's first block as one oversize-style scrolling page, and the marker is hidden.

### D4. Reading controls and key scope
- **Pointer.** `@click` on the root advances, except when `event.target.closest("button, a, [role=button]")` matches (the dialogue rows, C6c's controls), or when `window.getSelection()` holds a non-collapsed range inside the window. The second rule lets players copy text. After advancing, the page surface takes focus with `preventScroll`.
- **Keyboard.** The page surface `div.message-window__page` has `tabindex="0"`, `aria-label="訊息"`, and `aria-describedby` pointing at a hidden `第 N／M 頁` label. Its `@keydown` acts only when `event.target === surface`, the key is Enter or Space, and no modifier is held. It then calls `preventDefault()` and `stopPropagation()`, and advances unless `event.repeat` is set.
  - Component listeners fire in bubble order before the document listener, so the bridge never routes the key to the dock.
  - A key repeat never skips pages. It is still claimed, so a held key never leaks through to the dock.
  - When focus is on `#action-dock` or anywhere else, Enter and Space keep their dock meaning, so a dock Enter never also advances a page.
- **Wheel.** `@wheel` with `deltaY < 0` emits `open-full-log` when the page is not scrollable, or is an oversize page already at `scrollTop === 0`. It does not fire in the dialogue variant.

*Why not a global or stage-wide key:* the bridge already owns Enter (dock confirm) and Space (dock multi-select) for every non-editable target, and the stage has no focusable element. A global advance key would steal dock keys. The design doc's "or the stage" is therefore narrowed to the window's surface.

### D5. The live region announces each page once
A visually hidden `div` (`role="status"`, `aria-live="polite"`, `aria-atomic="true"`, `data-testid="message-live"`) receives plain text.
- When a page is shown (mount excluded), the region is set to the page's text with the `◈` markers excluded.
- A watermark, `announcedEnd`, holds the response offset up to which the region has spoken. A page shown by a new response or an advance announces all its fragments and raises the watermark to the page's end.
- Lines appended to the page on screen announce only the fragments whose `start` is at or after the watermark.
  - Paging is greedy, so an append never re-cuts a fragment that was already on screen. Whole-fragment filtering is therefore exact, and nothing is sliced.
- Mount and flush set the watermark to the response's length and announce nothing. A re-page announces nothing.
  - *Why offsets, not fragment keys (`${seq}:${start}`):* a re-page at another width moves every cut and produces new keys. Response offsets do not depend on where the cuts fall.
- Announcing the same text twice in a row clears the region first, then sets the text on the next tick, so the repeat is still heard.
- The page surface itself is not a live region. It changes on advance, and announcing it too would double-speak.

### D6. The dialogue variant is ported, unpaged
While `mode === "dialogue"` and `dialogue` is non-null, `data-variant="dialogue"`. The text area then renders, in a scroll region:
- the current response's blocks, whole, with the last `out` line passed through the ported anchored echo match (the `<host>說：<reply>` / verbatim-reply rules and residual hint)
- the `.dlg` box
- the `.choices` rows

The box pin is ported: on a reply change, scroll so the box's top is 8px below the region top. No page marker renders, clicks do not advance, and Enter/Space are not intercepted, so a focused pick's native Enter still activates it (the bridge already skips buttons). The live region announces each new committed reply once, as the existing dialogue-variant requirement demands. The CSS for `.dlg`, `.av`, `.who`, `.say`, `.choices`, `.pick`, and `.pick-exit` moves with the variant, scaled to the window's text size.

*Why unpaged:* the picks must stay reachable in the fixed band. Paging the reply while the picks stay visible would put choices in front of unread text. C10 pages the line and moves the choices over the stage.

### D7. Story and tests
- The story file uses the real DOM measurer, since Storybook has layout, inside a decorator box of 1280×300 (the band message region at 1080). Its args carry `seq`'d fixture lines and marks.
- `tests/message_window.test.js` passes a code-point `pageFit` and mocks `ResizeObserver` and `document.fonts`.
- The component-showcase coverage gate requires the story and the manifest title together. Both land here.

### D8. Spec strategy and archive order
- The only delta is the showcase manifest requirement, MODIFIED on C4b's text (the latest series text: C4c and C5 do not touch it), to add the message window beside the narrative feed.
- The window's behaviour requirements land with the mount in C6c, because until then no player-reachable surface shows it. The Vitest file is wired into evidence now (the semantic-classes evidence test gains it), so C6c only adds annotations.
- **Archive order: C5 → C6a → C6b (this change) → C6c (`webclient-message-window-swap`).** C6c modifies the same showcase requirement again, on this change's text.

## Risks / Trade-offs

- [Measuring with real vnodes costs layout on every re-page] → Only the current response is paged, and each split is a binary search (about 10 fits for a 500-character block). Re-pages are driven by box, scale, and font changes, not by every render.
- [jsdom has no layout, so the DOM `fits` itself is untested in Vitest] → The DOM path is exercised by the story build (`pnpm run build-storybook`) here and by C6c's browser tests. Vitest pins the state machine through `pageFit`.
- [28px text changes the feel of long room descriptions: 6 lines per page at 1080] → This is the design's decision. The full log (C1's bottom-opening surface) remains one control away.
- [A click to focus the window also advances] → The first click on page 1 advances only if more pages exist. The design names click as the advance gesture.

## Migration Plan

None. The component is not mounted until C6c.
