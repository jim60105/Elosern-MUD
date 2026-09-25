## Context

See proposal.md (Why). The current state was checked in code. C1–C5 are assumed archived first. None of them touches the narrative store, the line renderer, or the requirements this change edits.

- `ctx.narrative` (`stores/elosern.js`) is an array of `{ kind, text, tokens }`.
  - `appendText(kind, text)` (`stores/elosern/transport.js`) validates `kind` against `NARRATIVE_KINDS` (`in`, `out`, `sys`, `err`) and sets `tokens` only for `out`.
  - It trims to `MAX_NARRATIVE_LINES` (500) with `shift()`, adjusting `seenIndex`.
- Who appends which kind:
  - `out`: the transport's `text` handler (`web/webclient-app/transport.js`).
  - `err`: `handleActionResult` (a non-success result's message).
  - `in`: `sendText` (a typed command) and `dispatchAction` (the `CommandEcho.commandLine` line, only when it is non-null).
  - `sys`: no production writer today. Fixtures and future writers use it.
- `dispatchAction` is the single mutation entry. It returns `null` when blocked and a request id otherwise. The echo is appended inside the `try` after `sender.sendAction(envelope)`.
- `lib/narrative_line_nodes.js` `narrativeLineNodes(line, index)`:
  - It re-runs `NarrativeMarkup.tokenize(text)` for every non-`in` line on every render, ignoring `line.tokens`.
  - `FullLogOverlay.vue` and `NarrativeFeed.vue` both call it.
- The token stream (`web/static/webclient/js/elosern/narrative_markup.js`) has four kinds:
  - `text` (`value`, optional `degraded`)
  - `break`
  - `open` (`tag: "span"`, `classes`, optional `style`)
  - `close`

  The tokenizer balances opens and closes. `components/narrative-renderer.js` maps tokens to vnodes with a span stack.
- The browser suite reads the feed's DOM text to learn that a reply landed:
  - `[data-testid="narrative-feed"]` innerText in the `dom_readiness` predicates and the `inner_text()` calls
  - `.elosern-narrative` innerText in `browser_helpers.wait_for_narrative_settled`

  The store is already exposed as `window.__elosernBridge.store` (`main.js`), and several tests already read `store.narrative` through it.

## Goals / Non-Goals

**Goals:**
- A pure, deterministic paging function, and a segmentation function the message window (C6b) can call on every render. Both are fully unit-testable with an injected fit test.
- A response boundary for every deliberate action, including the silent ones.
- One tokenizer run per line.
- A browser suite that no longer depends on the feed's DOM text to see a reply, so C6c's swap touches only the rendering assertions.

**Non-Goals:**
- Any rendered change. `NarrativeFeed` still renders the whole log with its unread marker.
- DOM measurement: the injected `fits` is C6b's.
- Reader state (the current page, flush on a new response): C6b.

## Decisions

### D1. Response marks record dispatches that append no echo
The store keeps `ctx.narrativeSeq` (the last assigned ordinal) and `ctx.responseMarks = ref([])`.
- `appendText` assigns `line.seq = ++ctx.narrativeSeq`.
- `dispatchAction` pushes `ctx.narrativeSeq + 1`, the ordinal the next retained line will receive, immediately after `ctx.sender.sendAction(envelope)` returns and before the echo append.
  - If the echo appends, its `seq` equals the mark, so the echo line and the mark start one response.
  - If the action is silent, the first reply line, or the result's `err` line, starts the response.
- A synchronous send failure (the `catch`) records no mark: nothing was dispatched.
- `sendText` needs no mark: its `in` line is the boundary.
- The trim loop drops marks below the oldest retained `seq`.

*Why a mark instead of an echo:* the echo requirement ("A deliberate mutation echo appears exactly once at dispatch") forbids fabricating a line for a surface with no label, and the declared silent controls are silent on purpose.

*Alternative:* segment at the in-flight request's result. Rejected. A result arrives after the reply text for some adapters, and a `stale` / reconnect path never delivers one.

*Alternative:* a `boundary` flag on the next appended line. Rejected. The line that carries the flag may belong to another event (an unrelated late line), and the flag would be written into the log itself. Marks are a separate client-local view input, never stored in the log.

### D2. Segmentation rules
`segmentResponses(lines, marks)` walks the lines once. A new response starts at line `i` when `lines[i].kind === "in"` or `marks` contains `lines[i].seq`.
- Lines before the first start form a leading response with no header (the connection notices and first room text after login).
- An `in` line is the response's `header` and is excluded from `blocks`.
- A mark whose ordinal has no line yet opens no response. C6b reads `pendingMark = marks.at(-1) > lastLine.seq` to know an action is in flight with nothing to show yet, and keeps the previous response on its last page.
- Lines without `seq` (Vitest and Storybook fixtures) are treated as unmarked, so `in` lines alone segment them.

### D3. Paging with an injected fit test
`paginate(blocks, fits)` returns `[{ blocks: [fragment…], oversize: boolean }]`. A fragment is `{ kind, seq, mapArt, first, tokens, start, end }`, where `start` / `end` are character offsets into the response. A `text` token counts its code points and a `break` counts 1.

Algorithm:
1. Take the next block. If it is `sys` or `err` and the current page is non-empty, close the page.
2. If `fits(page + block)`, append the block and continue.
3. If the block is box-drawing (`mapArt`), it is atomic:
   - On a non-empty page, close the page and retry.
   - On an empty page, emit it as an `oversize` page.
4. Otherwise find the largest prefix length `L` whose fragment fits, by binary search over code-point cuts. `fits` must be monotonic in the prefix length, which DOM height is. Then choose the cut:
   - the last *strong* boundary ≤ `L`: after a `break` token, a `\n` in text, or a sentence end
   - otherwise the last *clause* boundary ≤ `L`
   - otherwise `L` itself

   A cut never falls inside a surrogate pair.
5. If the cut is 0:
   - On a non-empty page, close the page and retry the whole block.
   - On an empty page (a box too small for one character), emit the whole remaining block as an `oversize` page.

   Otherwise emit the prefix fragment, close the page, and continue with the remainder. A remainder drops leading `break` tokens and leading `\n` at the cut.

Boundary sets:
- Sentence end: `。！？…`, plus ASCII `.!?` followed by whitespace. A run of end marks is taken whole (`……`, `！？`), followed by any run of closing quotes and brackets `」』）"'`.
- Clause: `，、；：`, plus ASCII `,;:` followed by whitespace.

*Why "hard break or sentence end" share one class:* a `<br>` inside one server message is a paragraph end. Preferring it over a later sentence end would waste most of a page when the break sits near the top. The design's order (sentence, then clause, then character) is kept, and a hard break joins the first class.

*Alternative:* a line-count capacity (`floor(textAreaHeight / lineHeight)`). Rejected. `sys` lines use 13px sans and `map-art` lines use mono at a different line height, so a single line-height constant would under- or over-fill mixed pages. The fit test compares real measured heights (C6b).

Invariants, asserted in Vitest:
- Concatenating every fragment's text reproduces the blocks' text exactly, minus only the dropped leading breaks at cuts.
- The same input and fit results give the same pages.

### D4. Splitting inside markup spans
The fragment builder walks tokens and keeps the stack of open `open` tokens.
- At a cut inside a `text` token, the prefix fragment ends with the text slice plus one `close` per open span.
- The remainder starts with shallow copies of the stacked `open` tokens (same `classes`, same `style`), followed by the rest of the text.

No token kind the pipeline does not produce is ever emitted, so the renderer's allowlist guarantee is untouched. `degraded` text keeps its flag in both halves.

### D5. One tokenizer run per line
- `appendText` stores `tokens` for `out`, `sys`, and `err` (`in` stays `null`: it never enters the pipeline).
- `narrativeLineNodes` uses `line.tokens` when it is an array and falls back to `NarrativeMarkup.tokenize(text)` for fixtures. Its output is unchanged for every line, which `narrative_line_nodes.test.js` pins.
- The new `narrativeBlockNodes(fragment, key)` renders a fragment's `tokens` in a `div.narrative-line.<kind>` with `data-line-kind`, plus `map-art` when `fragment.mapArt` is set, plus `cont` when the fragment does not begin its line (`fragment.first === false`), through `renderNarrativeTokens`. A `.narrative-line.sys.cont` rule in each consuming surface suppresses the `◈` marker on continuations. It is the page renderer C6b uses. The class vocabulary stays in this one module.
- `lib/message_pages.js` reads `line.tokens` the same way.
- The box-drawing test (`/[\u2500-\u257f]/`) moves out of `narrative_line_nodes.js` into a new Vue-free `lib/box_drawing.js` (`isBoxDrawing(text)`). Both modules import it, so `message_pages.js` stays Vue-free and the pinned D2 equivalence in `narrative_line_nodes.test.js` keeps testing the one copy.

### D6. Browser decoupling
`browser_helpers.py` gains two functions:
- `narrative_log_text(page)`: evaluates `window.__elosernBridge.store.narrative.map(l => l.text).join("\n")`
- `narrative_log_length(page)`

`wait_for_narrative_settled` polls `narrative_log_length`, and its callers compute `before` with the same helper.

Re-pointing rule for each hit of `grep -n 'narrative-feed\|elosern-narrative' web/tests/browser/*.py`:
- A predicate or `inner_text()` that only asks "did text X or more text arrive" moves to the helpers.
- An assertion about the rendered feed stays for C6c. These are selectors carrying `.inp`, `.narrative-divider`, `span[class*="color-"]`, `.out`, `[data-line-kind]`, `.option-card`, `scrollTop` / `scrollHeight`, rectangles, visibility, and the `REQUIRED_SURFACES` / `COMPONENT_SELECTORS` lists.

The store log holds the markup source (`text`), not rendered text. Waits that match plain prose keep matching, because the server wraps colour codes in `<span>` tags around words, not inside them. Where a test compares exact rendered text (`test_browser_shell_narrative.py`'s markup tests), it stays on the DOM.

### D7. Spec strategy and archive order
- `webclient-input-narrative` gains two ADDED requirements that describe the presentation functions' observable contract (segmentation and pages). The reading controls and the window come in C6b and C6c.
- `webclient-contextual-hud` "Narrative lines carry the reference's semantic classes" is MODIFIED on the main spec text (no earlier series change touches it). Its three scenario titles are kept, and two are added.
- **Archive order: C5 → C6a (this change) → C6b (`webclient-message-window-component`) → C6c (`webclient-message-window-swap`).** C6b and C6c build on this change's seams. Neither modifies this change's requirement blocks again: their wording ("every surface that renders the line", "a fragment of a line that paging has split") already covers the message window.

## Risks / Trade-offs

- [`fits` is called O(log n) times per split, which costs layout work in C6b] → The lib calls `fits` only for the block being split, and for the whole-block test once per block. A 500-character block costs about 10 calls. C6b measures only the current response.
- [Binary search assumes monotonic fit] → DOM height is monotonic in prefix length for wrapped text. A Vitest case with a non-monotonic fake documents that the result is still a valid, lossless paging, just not maximal.
- [Store-backed browser waits no longer prove that text rendered] → Rendering stays covered by the DOM-asserting tests, which are unchanged here, and by C6c's page tests.
- [The mark for a dispatch whose reply never arrives lingers] → It opens no response (D2), and the next line or mark supersedes it. Trimming bounds the list.

## Migration Plan

None. Ordinals and marks are client-local and never persisted.
