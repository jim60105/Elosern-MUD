## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §6.1, §6.2, §12, §13) replaces the scrolling narrative caption with a message window that shows one action's response one page at a time. The window needs two things the client does not have:

- **A reliable response boundary.** The design segments at `in` lines, but `dispatchAction` in `stores/elosern/transport.js` appends an `in` echo only when `CommandEcho.commandLine` resolves one. The declared silent actions (`explore.dialogue_leave`, `account.character.switch`, `account.character.create`, `creation.roll_name`, the `gallery.*` actions, and `options.dismiss`, all in `SILENT_PRESENTATION_CONTROLS` in `web/static/webclient/js/elosern/command_echo.js`) never produce one.
- **A pure paging function over the markup token stream.** It must fit pages to a measured box, cut only at hard breaks, sentence ends, or clause marks before falling back to a character, and keep styled spans intact across a cut.

This change is the first of three slices of design §6 (C6a in the series). It adds the pure lib and the store seams, and decouples the browser suite from the feed's DOM text. Nothing the player sees changes. `webclient-message-window-component` (C6b) builds the window on these seams, and `webclient-message-window-swap` (C6c) mounts it.

**Implementation profile:** logic — a pure paging library and store seams with no visible change; unit tests define done.

## What Changes

- New pure module `web/webclient-app/lib/message_pages.js` (no Vue, no DOM). It imports only `lib/narrative_markup.js` and exports:
  - `segmentResponses(lines, marks)`: responses start at each `in` line and at each response mark. Early and late lines join the current response. The `in` line is the response's header, never a block.
  - `responseBlocks(response)`: one block per `out` / `sys` / `err` line, carrying its stored tokens and its box-drawing flag.
  - `paginate(blocks, fits)`:
    - `fits(candidateBlocks) → boolean` is injected by the caller.
    - Packing keeps whole blocks. `sys` / `err` blocks start a new page.
    - Split order: hard break or sentence end, then clause mark, then character.
    - A split inside a span closes it and re-opens it with the same classes and style.
    - Box-drawing blocks are atomic. A block that fits no empty page gets an `oversize` page.
  - `pageIndexForOffset(pages, offset)` and `responseLength(blocks)`, which let the view keep the reader on the first unseen character.
- `stores/elosern/transport.js`:
  - Every retained line carries a monotonic `seq`.
  - `appendText` tokenizes `sys` and `err` lines as well as `out`, so the allowlist pipeline runs once per non-input line.
  - `dispatchAction` records a response mark (the next line ordinal) right after `sender.sendAction(envelope)` returns, before the echo append. An echoing dispatch and a silent one both start exactly one response.
  - Marks older than the oldest retained line are dropped in the same trim loop that enforces `MAX_NARRATIVE_LINES`.
- `stores/elosern.js`: the new `ctx.narrativeSeq` counter and the `ctx.responseMarks` ref, with `responseMarks` exposed on the store.
- `lib/narrative_line_nodes.js`:
  - `narrativeLineNodes` renders a line's stored `tokens` when present and tokenizes only as a fallback, for fixtures that carry text alone.
  - New `narrativeBlockNodes(block, key)` renders a page fragment with its line's kind and `map-art` classes.
  - `FullLogOverlay.vue` and `NarrativeFeed.vue` keep calling `narrativeLineNodes` unchanged.
  - The box-drawing predicate moves into a new Vue-free `lib/box_drawing.js` that both modules import.
- Browser suite decoupling, with no behaviour change:
  - `web/tests/browser/browser_helpers.py` gains `narrative_log_text(page)` / `narrative_log_length(page)`, which read the retained log from `window.__elosernBridge.store.narrative`.
  - `wait_for_narrative_settled` reads that log instead of `.elosern-narrative` innerText.
  - Every browser use that only waits for a reply to land, or checks that some text was logged, is re-pointed to the helpers. Uses that assert the feed's rendering (`.inp`, `.narrative-divider`, colour spans, `data-line-kind`, scroll offsets, `#narrative-unread`, rectangles) stay until C6c.
- No component, story, manifest, OOB schema, presenter, server, or persistence change.

Out of scope:
- `MessageWindow`, its measurer, its reading controls, and its live region: `webclient-message-window-component` (C6b).
- Mounting the window, the 日誌 control, and retiring `NarrativeFeed` / `UnreadIndicator` / `seenIndex`: `webclient-message-window-swap` (C6c).
- Typewriter reveal and reading preferences: `webclient-typewriter-reading-prefs` (C7).
- Paging the dialogue line: `webclient-dialogue-stage` (C10).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-input-narrative`:
  - ADDED "The narrative log is segmented into responses at each player action"
  - ADDED "A response is cut into pages that fit a measured box and never mid-sentence"
- `webclient-contextual-hud`: MODIFIED "Narrative lines carry the reference's semantic classes". The pipeline runs once per retained line, and a page fragment keeps its line's classes.

## Impact

- New:
  - `web/webclient-app/lib/message_pages.js`, `web/webclient-app/lib/box_drawing.js`
  - Vitest `web/webclient-app/tests/message_pages.test.js`
  - Vitest `web/webclient-app/tests/store/narrative_responses.test.js`
- Edited:
  - `web/webclient-app/stores/elosern/transport.js`, `web/webclient-app/stores/elosern.js`
  - `web/webclient-app/lib/narrative_line_nodes.js`
  - Vitest `tests/narrative_line_nodes.test.js`, `tests/store/store_slices.test.js`
- Python evidence: `web/webclient/tests/test_node_suite_evidence.py`. It gains one Vitest-evidence test for the two ADDED IDs and adds `narrative_line_nodes.test.js` to the semantic-classes evidence run.
- Browser:
  - `web/tests/browser/browser_helpers.py`
  - the text-only waits in `test_browser_actions.py`, `test_browser_art.py`, `test_browser_combat_panels.py`, `test_browser_exploration_dialogue.py`, `test_browser_layout.py`, `test_browser_local_map_interaction.py`, `test_browser_options_surface.py`, `test_browser_shell_command_line.py`, `test_browser_shell_dock.py`, `test_browser_shell_narrative.py`, `test_browser_shell_surfaces.py`
- Spec traceability: two new IDs are covered by the new evidence test. The modified title is unchanged.
- Dependencies:
  - Archive order: C5 (`webclient-collapsible-command-line`) → C6a (this change) → C6b → C6c.
  - None of this change's requirement blocks is touched by C1–C5.
