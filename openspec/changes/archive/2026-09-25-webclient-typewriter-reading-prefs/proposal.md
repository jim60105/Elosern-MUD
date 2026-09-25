## Why

After `webclient-message-window-swap` (C6c), the band's `MessageWindow` shows each page in full at once. The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §6.3, §6.4) wants three more things:

- Each page types in.
- The reader can set the typing speed.
- The reader can opt into auto-advance.

The existing reduced-motion preference must still make pages appear at once. This change (C7 in the series) adds the typewriter reveal to the paged window, the two reading preferences, and their settings controls. The layout store's version is bumped for them.

**Implementation profile:** visual — the reveal technique is specified, but reading speed and zero-reflow typing must be checked by eye.

## What Changes

- New pure module `web/webclient-app/lib/message_reveal.js` (no Vue, no DOM). It works on C6a's page and fragment shapes:
  - `TEXT_SPEEDS` (`slow`, `normal`, `fast`, `instant`) and `TEXT_SPEED_CPS` (`slow` 20, `normal` 45, `fast` 90 characters per second)
  - `pageUnits(page)`: the number of reveal units on a page. One unit is one code point of text or one hard break, the same units as C6a's fragment offsets.
  - `snapUnits(page, n)`: a box-drawing map fragment is revealed whole, so a count that falls inside one moves to its end.
  - `fragmentReveal(page, n)`: how many units of each fragment are shown.
  - `offsetAtUnits(page, n)` and `unitsAtOffset(page, offset)`: convert between a page-local count and a response offset, for the re-page anchor.
  - `autoAdvanceDelayMs(page)`: `1200 + 60 × pageUnits(page)`.
  - `autoAdvanceAllowed(page)`: false for an oversize page and for a page that holds map art.
- `web/webclient-app/lib/message_pages.js`: export `splitTokensAt(tokens, n)`. It is the span-preserving cut that `paginate` already uses (C6a design D4), exposed so the reveal can split a fragment without a second cutting routine.
- `web/webclient-app/lib/narrative_line_nodes.js`: `narrativeBlockNodes(fragment, key, reveal)` takes an optional count of revealed units.
  - The revealed head renders through the pipeline as before.
  - The unrevealed tail renders through the same pipeline inside `span.narrative-unrevealed` (`aria-hidden="true"`, `visibility: hidden`).
  - A fragment with nothing revealed gets the class `unrevealed` on its line `div`.
  - With no `reveal` argument, the output is unchanged.
- New composable `web/webclient-app/composables/use-typewriter.js`. It owns one `requestAnimationFrame` clock and drives the typed count and the auto-advance wait from it. Each frame adds at most 100ms, so time spent in a hidden tab never counts. The composable pauses the auto-advance wait while `held` is true.
- New composable `web/webclient-app/composables/use-reduced-motion.js`: the effective reduced-motion flag. It is the stored override (`"on"` / `"off"`) or, when no override is stored, `matchMedia("(prefers-reduced-motion: reduce)")`, which it follows live.
- `web/webclient-app/components/MessageWindow.vue`:
  - new props `textSpeed` (default `"normal"`), `autoAdvance` (default `false`), `reducedMotion` (`"on" | "off" | null`), and `held` (Boolean)
  - pages type in, the marker renders only once a page is fully shown, and a click or Enter/Space while typing completes the page
  - the re-page anchor moves to the typing position
  - auto-advance runs, and it stops at the response's last page
  - the root carries `data-typing="true|false"`
  - the live region still announces the whole page once, when the page starts
  - the dialogue variant does not type
- `web/webclient-app/components/AppShell.vue` and `AppClient.vue`: pass `textSpeed`, `autoAdvance`, `reducedMotion`, and `held` (`openSurfaces.length > 0`) to the window.
- Preferences:
  - `stores/elosern/preferences.js` gains `prefs.textSpeed` (`"normal"`), `prefs.autoAdvance` (`false`), `setTextSpeed`, and `setAutoAdvance`. Both are loaded, applied, and persisted with the other preferences.
  - `stores/elosern/view.js` publishes both values. `stores/elosern.js` exports both setters.
- `web/static/webclient/js/elosern/layout_store.js` (wrapped by `lib/layout_store.js`):
  - `CURRENT_LAYOUT_VERSION` becomes `2`.
  - `PREFERENCE_TYPES` gains `textSpeed` (an enum over `TEXT_SPEEDS`) and `autoAdvance` (boolean). `defaultWrapper()` carries `textSpeed: "normal"` and `autoAdvance: false`.
  - **BREAKING (internal)**: the default migration registry becomes empty. A stored version-1 wrapper is an unknown version and resets to the version-2 default. There is no migration and no shim, because there are zero users.
- `web/webclient-app/components/SettingsOverlay.vue`: the 閱讀設定 section gains a 文字速度 segmented control (慢 / 標準 / 快 / 瞬間) and a 自動翻頁 toggle. It has new props and emits `text-speed-change` and `auto-advance-change`. The story gains a `ReadingPreferences` story.
- `web/webclient-app/lib/controls-reference.js`: the message-window entry says that Enter or Space first completes a typing page and then advances.
- Tests:
  - Vitest for the reveal lib, both composables, the window's typing behaviour, the settings controls, and the preference slice
  - node tests for the layout store's version 2
  - browser journeys for typing and for the preferences
  - C6b's and C6c's instant-page tests pinned to `textSpeed: "instant"`, or made to complete typing first
- No OOB schema, presenter, server, allowlist, or component-manifest change. No component is added or deleted.

Out of scope:
- The dialogue stage (the paged dialogue line that types, the name plate, choices over the stage): `webclient-dialogue-stage` (C10). Until then the dialogue variant stays unpaged and untyped.
- `motionLevel` (full / reduced / off), the presentation queue, and transitions: `webclient-motion-layer` (C11). C11 replaces the `reducedMotion` override, and with it this change's reduced-motion rule for typing, with `motionLevel`. It also replaces `use-reduced-motion.js`.
- Combat beat playback: `webclient-combat-beat-playback` (C13).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-input-narrative`:
  - MODIFIED "The message window's reading controls advance pages and a new action flushes unread pages", on C6c's text. A press while typing completes the page. The re-page anchor is the typing position. A flush shows the last page complete.
  - ADDED "A page types in at the reader's text speed and auto-advance is opt-in"
- `webclient-contextual-hud`:
  - MODIFIED "The message window presents the current response one page at a time in the band's message region", on C6c's text. The marker shows only on a fully shown page.
  - MODIFIED "Narrative prose scale is a client-local preference the settings surface owns", on the main spec. A setting applies to what it governs, and the message window replaces the caption in the text.
  - ADDED "Text speed and auto-advance are client-local reading preferences the settings surface owns"
- `webclient-desktop-shell`: MODIFIED "Browser persistence is versioned and presentation-only", on the main spec. The current version is 2, and an earlier version with no registered migration resets.

## Impact

- New:
  - `web/webclient-app/lib/message_reveal.js`
  - `web/webclient-app/composables/use-typewriter.js`, `web/webclient-app/composables/use-reduced-motion.js`
  - Vitest `web/webclient-app/tests/message_reveal.test.js`, `web/webclient-app/tests/message_window_typing.test.js`, `web/webclient-app/tests/store/reading_preferences.test.js`
- Edited:
  - `web/webclient-app/lib/message_pages.js`, `web/webclient-app/lib/narrative_line_nodes.js`
  - `web/webclient-app/components/MessageWindow.vue`, `web/webclient-app/components/AppShell.vue`, `web/webclient-app/AppClient.vue`, `web/webclient-app/components/SettingsOverlay.vue`
  - `web/webclient-app/stores/elosern/preferences.js`, `web/webclient-app/stores/elosern/view.js`, `web/webclient-app/stores/elosern.js`
  - `web/static/webclient/js/elosern/layout_store.js`, `web/webclient-app/main.js` (comment)
  - `web/webclient-app/lib/controls-reference.js`
  - `web/webclient-app/stories/Core/MessageWindow.stories.js`, `web/webclient-app/stories/Overlays/SettingsOverlay.stories.js`
- Tests edited:
  - Vitest: `tests/message_pages.test.js`, `tests/narrative_line_nodes.test.js`, `tests/message_window.test.js`, `tests/full_log_overlay.test.js`, `tests/overlays/settings_overlay.test.js`, `tests/overlays/help_overlay.test.js` (it pins the text)
  - node: `web/static/webclient/js/tests/layout_store.test.js`
  - Python: `web/webclient/tests/test_node_suite_evidence.py`, `web/webclient/tests/test_vue_showcase_overlays_evidence.py` (story id)
  - Browser: `web/tests/browser/browser_helpers.py` (`wait_for_page_shown`), `test_browser_input_narrative.py`, `test_browser_layout.py` (its stored-wrapper literals), and the C6c message-page assertions in `test_browser_shell_narrative.py`, `test_browser_exploration_actions.py`, and `test_browser_shell_command_line.py`
- Spec traceability: two new IDs, covered by the new evidence test and browser tests. Three modified titles are unchanged, so their IDs do not move.
- Dependencies:
  - Archive order: C6a → C6b → C6c → C7 (this change).
  - Blocks are written on C6c (the reading-controls and message-window requirements) and on the main spec (prose scale, browser persistence).
  - C10 (`webclient-dialogue-stage`) and C11 (`webclient-motion-layer`) build on this change's typing requirement.
  - Hot-spot files shared with C6c, C8, and C10: `AppShell.vue`, `AppClient.vue`, `MessageWindow.vue`.
