## Context

See proposal.md (Why). C1–C5, C6a (`webclient-message-pages`), and C6b (`webclient-message-window-component`) are assumed archived first. State after them:

- `components/MessageWindow.vue` exists with its story, manifest title, and Vitest (C6b), and it is not mounted.
  - Props: `lines`, `marks`, `mode`, `dialogue`, `artPanel`, `fontScale`, `pageFit`.
  - Emits: `dialogue-pick`, `dialogue-freeform`, `dialogue-leave`, `open-full-log`.
  - Its root carries `data-testid="message-window"`, and the page surface carries `message-page`. It reserves a 36px control strip whose right end (`right: 22px` … about 96px) is empty for shell controls.
- `store.responseMarks` and line `seq` exist (C6a). The browser suite reads logged text through `narrative_log_text` / `narrative_log_length`. The rendering assertions still addressing the feed are listed at the top of `web/tests/browser/browser_helpers.py`.
- `AppShell.vue` mounts `NarrativeFeed` in HudFrame's `#band-message` slot and, after it, the ⌨ toggle (`command-line-toggle`, `right: 22px; bottom: 18px`, 30×30) from C5.
  - It forwards `open-full-log` from the feed's `完整日誌` capsule to `AppClient`'s `openFullLog` (`composables/use-overlays.js`), which captures the opener for focus restore.
- The store still carries `seenIndex` / `unreadCount` / `markNarrativeSeen`, used only by `tests/store/store_slices.test.js`. `transport.js`'s trim adjusts `seenIndex`.
- `#narrative-unread` is listed in `tests/preserved_contract.test.js` and in `AppShell.vue`'s header comment.

## Goals / Non-Goals

**Goals:**
- The live client reads the narrative through the paged window, and the full log is one control away.
- Every trace of the scrolling caption and its unread machinery is gone from code, tests, stories, manifest, and specs.
- The browser suite asserts the new reading journeys.

**Non-Goals:**
- Any change to `MessageWindow`'s internals (C6b), paging (C6a), or `FullLogOverlay`.
- The requirements that still say "bounded caption" in passing (desktop-shell "Required desktop surfaces remain visible and usable", browser-verification "Browser acceptance covers foundation recovery and layout behavior"). Their claims (a bounded box, the complete log one action away, dialogue rows reachable by scrolling inside it) remain true of the window. Restating them would add two large blocks that C10 rewrites again.

## Decisions

### D1. The `日誌` control is shell chrome beside ⌨
`AppShell`'s `#band-message` template becomes `MessageWindow`, then the `日誌` button, then the ⌨ toggle.
- `日誌` sits at `right: 58px; bottom: 18px`, which puts the pair `[日誌] [⌨]` in the window's reserved strip in design §5.1's order.
- It is a text button (`日誌`, 12px sans, 30px tall, capsule treatment inherited from the retired `.narrative-fulllog-control`).
- `aria-label` and `title` are `完整日誌` (the surface's name). It emits `open-full-log`.
- The `.stop` Enter/Space guards match the toggle, so the document bridge never routes its keys into the dock.

*Why AppShell, not MessageWindow:* C5 set the rule that controls tied to shell state live beside, not inside, the swappable content. `openFullLog` captures `document.activeElement` as the opener, so focus returns to `日誌` on close, which is what the full-log requirement demands.

`MessageWindow`'s own `open-full-log` (wheel-up) is forwarded to the same emit.

### D2. Store unread bookkeeping is deleted
- `ctx.seenIndex`, the trim loop's `seenIndex` adjustment, `ctx.markNarrativeSeen`, `ctx.unreadCount`, and their store exports are deleted.
- Paging replaces the concept: a page marker tells the reader more remains, and the flush rule moves unread pages to the log explicitly.
- The only consumer was the `store_slices.test.js` case "unreadCount…", which is deleted. That file's line-shape projection tests stay.

### D3. Tests follow the component
- `tests/dialogue_feed.test.js` is renamed `tests/message_window_dialogue.test.js` and mounts `MessageWindow` with a code-point `pageFit`. Its assertions on `.dlg` / picks / exit / echo suppression carry over. Its `.narrative-line.inp` assertions change: input lines no longer render in the window, so the case asserts the response's blocks only.
- `tests/full_log_overlay.test.js`: the parity block that mounted `NarrativeFeed` to compare renderers now compares `FullLogOverlay` lines against `MessageWindow` page fragments for the same `sys` / `out` lines. The class and `data-line-kind` parity is kept.
- `tests/overlays/deferred_surfaces_absent.test.js`: the `NarrativeFeed` mount becomes `MessageWindow`.
- `tests/app.test.js` and `tests/hud_frame.test.js`: `[data-testid="narrative-feed"]` becomes `[data-testid="message-window"]`, with the dialogue-mode lookups following.
- `tests/preserved_contract.test.js`: drop `narrative-unread`. Add `message-log-open` only if the file lists shell test ids; otherwise leave it.
- `web/webclient/tests/test_node_suite_evidence.py`:
  - `test_dialogue_feed_vitest_evidence_passes` runs `message_window_dialogue.test.js` and `dialogue_view_model.test.js`.
  - `test_choicepoint_block_node_suite_passes` drops `narrative_feed.test.js`.
  - A new `test_message_window_vitest_evidence_passes` runs `message_window.test.js` and covers the ADDED reading-controls ID. Browser tests cover it too (D4).

### D4. Browser re-pointing
From the list C6a left in `browser_helpers.py`:
- **Unread and scroll-keep journeys** (`test_browser_shell_command_line.py` unread / scroll cases, `test_browser_input_narrative.py` "scrolled above the bottom" cases) become paging journeys:
  - inject a multi-page response (`store.appendText('out', …)` through the bridge, as those tests already do)
  - assert the `▼` marker, advance with Enter on `message-page`, and assert `■`
  - assert that a dock Enter does not advance
  - dispatch a move and assert page 1 of the new response
- **Input-line rendering** (`.inp`, `.narrative-divider`, script-injection checks): open the full log (`message-log-open`) and assert inside `[data-testid="fulllog-overlay"]` (the testid `FullLogOverlay.vue` renders).
- **Colour-span and `.out` checks** (`test_browser_shell_narrative.py`): assert on `message-page`, which renders the same pipeline.
- **Geometry** (`test_browser_layout.py`, `test_browser_contextual_hud_stage.py`, `test_browser_contextual_hud_anchors.py`, `test_browser_combat_menu.py`, `test_browser_art.py`, `test_browser_local_map_interaction.py`, `test_browser_shell_surfaces.py`, `test_vue_foundation.py`, `browser_helpers.REQUIRED_SURFACES`): `narrative-feed` becomes `message-window`.
- **Full-log opener** (`test_browser_shell_dock.py`, `test_browser_contextual_hud_stage.py`, `test_browser_layout.py`, `test_browser_reconnect.py`): `narrative-fulllog-control` becomes `message-log-open`.
- **Dialogue** (`test_browser_exploration_dialogue.py`): the `narrative-feed` / `narrative-head` scroll-pin checks become the `message-window` text-area pin. The head row is gone, so the "no content above the head" check becomes "the box top is inside the text area".
- **Error lines** (`test_browser_exploration_actions.py`): `[data-line-kind="err"]` is asserted in `message-page`. An `err` block begins its own page, and the response is short.
- **Option cards** (`test_browser_options_surface.py:585`): a negative assertion that the narrative never renders degraded suggestion cards. It becomes `[data-testid="message-window"] .option-card` with count 0.

New browser coverage, in `test_browser_input_narrative.py`:
- `test_message_window_pages_and_flushes` at 1920×1080: font size 28px, at most 42 characters per rendered line, `▼`/`■`, Enter on the surface, no advance from the dock, flush on a move, and the log keeping the unread page.
- `test_message_window_repages_on_resize`: resize to 1280×720 and keep the anchor character on screen.

### D5. Spec strategy, traceability, and archive order
Each MODIFIED block is written on the latest series text:

| Requirement | Written on |
|---|---|
| contextual-hud "Surface visibility is gated by the committed game mode" | C5 `webclient-collapsible-command-line` |
| contextual-hud "The feed presents the dialogue variant from the committed panel" | C4a `webclient-avg-stage-shell` |
| input-narrative "A deliberate mutation echo appears exactly once at dispatch" | C5 (on C3's ADDED text) |
| component-showcase "Every required UI component…" | C6b `webclient-message-window-component` |
| desktop-shell "Player input lines are part of the narrative stream with a divider" | main spec (no series change touches it) |

Every scenario title of a MODIFIED block is kept. The dialogue-variant title keeps the word "feed"; its body names the message window. The title is kept so its three annotations stay valid, and C10 replaces the requirement.

Replaced IDs (REMOVED + ADDED) and their annotations:

| Old ID | New ID | Annotations to re-anchor |
|---|---|---|
| `webclient-contextual-hud::the-narrative-is-a-bounded-caption-whose-complete-log-is-reachable-in-one-action` | `…::the-message-window-presents-the-current-response-one-page-at-a-time-in-the-band-s-message-region` | `test_browser_layout.py:576`, `test_browser_contextual_hud_anchors.py:44`, `test_browser_shell_dock.py:229`, `test_browser_shell_command_line.py:170`, `test_browser_contextual_hud_stage.py:184` |
| `webclient-desktop-shell::narrative-output-remains-the-authoritative-text-surface` | `…::narrative-output-remains-the-authoritative-text-surface-and-is-read-page-by-page` | `test_browser_actions.py:148`, `test_browser_shell_dock.py:226`, `test_browser_shell_command_line.py:167`, `:245` |

The new `webclient-input-narrative::the-message-window-s-reading-controls-advance-pages-and-a-new-action-flushes-unread-pages` is covered by D3's evidence test and D4's new browser tests. Confirm every ID with `uv run --locked python -m tools.spec_traceability list` after syncing.

`openspec validate` reports that archive would refuse the input-narrative MODIFIED block until C3 is archived. That is expected.

**Archive order: C5 → C6a → C6b → C6c (this change).** If any of those blocks changes before archive, re-sync this change's block for that requirement, keeping only this change's edits.

## Risks / Trade-offs

- [The browser re-pointing is the bulk of the day (about 60 DOM assertions in 19 files)] → C6a already moved every text-only wait to the store helpers, so what remains is rendering-specific. D4 gives each category one mechanical rule.
- [Players lose the at-a-glance scroll history on the stage] → This is the design's decision (§6). The full log is one click or one wheel-up away and opens at the latest line (C1).
- [Removing `#narrative-unread` breaks a documented preserved id (`2026-08-25-webclient-hud-redesign-roadmap-design.md`)] → The project is unreleased. The roadmap doc is historical, and only the test contract is authoritative. It is updated here.

## Migration Plan

None. Nothing is persisted.
