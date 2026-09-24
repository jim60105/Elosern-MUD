## Why

After `webclient-message-pages` (C6a) and `webclient-message-window-component` (C6b), the paged `MessageWindow` exists with its story and tests, but the band message region still mounts the scrolling `NarrativeFeed`. That feed carries its caption head, its `完整日誌` capsule, and the `UnreadIndicator`. This change completes design §6.1–§6.3 (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md`) and the §5.1 control strip `[日誌] [⌨]`:

- It mounts the window.
- It adds the `日誌` control beside C5's ⌨ toggle.
- It retires the feed, the unread indicator, and the store's unread bookkeeping.
- It moves the reading contracts into the specs.

The project is unreleased, so the replaced components, their tests, stories, manifest entries, preserved-contract id, and requirements are deleted outright.

## What Changes

- `web/webclient-app/components/AppShell.vue`:
  - `#band-message` renders `MessageWindow` with `lines`, `marks` (`store.responseMarks`), `mode`, `dialogue`, `artPanel`, and `fontScale`, forwarding its `dialogue-*` and `open-full-log` emits.
  - A new `日誌` button (`data-testid="message-log-open"`, `aria-label="完整日誌"`, `title="完整日誌"`) sits beside the ⌨ toggle. It emits `open-full-log` and has the toggle's `@keydown.enter.stop` / `@keydown.space.stop` guards.
  - New props `responseMarks` and `fontScale`.
  - The header comment drops `#narrative-unread` and the caption description.
- `web/webclient-app/AppClient.vue`: binds `:response-marks="store.responseMarks"` and `:font-scale="store.view.fontScale"` on `AppShell`. The full-log opener is unchanged: `FullLogOverlay` still renders `store.narrative` and opens at its latest line (C1).
- `web/webclient-app/styles/app-shell.css`:
  - places the `日誌` button at `right: 58px; bottom: 18px`, 30px tall
  - deletes the `.elosern-root .elosern-narrative*` overrides, the `.m-dialogue .narrative-scroll` rules, and C5's `[data-anchor="band-message"] .narrative-scroll { padding-bottom: 36px }`, since the window reserves its own control strip
- **BREAKING (internal)**: delete `components/NarrativeFeed.vue`, `components/UnreadIndicator.vue`, and their stories. Delete Vitest `tests/narrative_feed.test.js` and `tests/unread_indicator.test.js`, and re-point `tests/dialogue_feed.test.js` to `MessageWindow` as `tests/message_window_dialogue.test.js`. Remove `Core/NarrativeFeed` and `Core/UnreadIndicator` from `component-manifest.json` and from the four showcase-evidence snapshots.
- **BREAKING (internal)**: delete the store's `seenIndex`, `unreadCount`, and `markNarrativeSeen` (`stores/elosern.js`, `stores/elosern/view.js`, the trim adjustment in `stores/elosern/transport.js`) and their `store_slices.test.js` case. Remove `narrative-unread` from the preserved DOM contract (`tests/preserved_contract.test.js`).
- `lib/controls-reference.js`: the Enter row notes that Enter or Space on the focused message window advances a page. A new row names the `日誌` control.
- Re-point the remaining rendering assertions in the browser suite (the list C6a left in `browser_helpers.py`). Unread and scroll-keep journeys become paging journeys, `narrative-fulllog-control` becomes `message-log-open`, `narrative-feed` rectangles and visibility become `message-window`, and the `.inp` / divider / colour-span checks read the full-log surface or the page surface.
- Spec deltas:
  - The caption requirement is replaced by a message-window requirement, and a reading-controls requirement is added.
  - The dialogue variant, the visibility matrix, the echo requirement, and the input-line requirement are restated.
  - The narrative-output requirement is replaced, and the showcase manifest drops the feed and the unread indicator.
- No OOB schema, presenter, server, or persistence change.

Out of scope:
- Typewriter reveal, `textSpeed`, and `autoAdvance`: `webclient-typewriter-reading-prefs` (C7).
- The dialogue stage (paged dialogue line, name plate, choices over the stage, collapsed command panel): `webclient-dialogue-stage` (C10).
- The message window's clear-fade on location change: `webclient-motion-layer` (C11).
- The desktop-shell "Required desktop surfaces remain visible and usable" and browser-verification texts, which still say "bounded caption". They stay true of the window: it is a bounded surface, and the complete log is one action away through `日誌`. C10 restates them when the dialogue stage changes the band.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED "Surface visibility is gated by the committed game mode", on C5's text: a message-window row and a log-control row.
  - MODIFIED "The feed presents the dialogue variant from the committed panel", on C4a's text: hosted by the message window, unpaged, current response only.
  - REMOVED "The narrative is a bounded caption whose complete log is reachable in one action" (last modified by C4a).
  - ADDED "The message window presents the current response one page at a time in the band's message region".
- `webclient-input-narrative`:
  - MODIFIED "A deliberate mutation echo appears exactly once at dispatch", on C5's text: the echo heads its response and is never paged.
  - ADDED "The message window's reading controls advance pages and a new action flushes unread pages".
- `webclient-desktop-shell`:
  - MODIFIED "Player input lines are part of the narrative stream with a divider".
  - REMOVED "Narrative output remains the authoritative text surface".
  - ADDED "Narrative output remains the authoritative text surface and is read page by page".
- `webclient-component-showcase`: MODIFIED "Every required UI component is a Vue SFC with a documented Storybook story", on C6b's text: the feed and the unread indicator leave the manifest.

## Impact

- Edited:
  - `web/webclient-app/components/AppShell.vue`, `AppClient.vue`, `styles/app-shell.css`, `lib/controls-reference.js`
  - `stores/elosern.js`, `stores/elosern/view.js`, `stores/elosern/transport.js`
  - `component-manifest.json`, `stories/Core/AppShell.stories.js` (description)
- Deleted: `components/NarrativeFeed.vue`, `components/UnreadIndicator.vue`, `stories/Core/NarrativeFeed.stories.js`, `stories/Core/UnreadIndicator.stories.js`, `tests/narrative_feed.test.js`, `tests/unread_indicator.test.js`.
- Vitest: `tests/dialogue_feed.test.js` (renamed `message_window_dialogue.test.js`), `tests/full_log_overlay.test.js`, `tests/overlays/deferred_surfaces_absent.test.js`, `tests/preserved_contract.test.js`, `tests/app.test.js`, `tests/hud_frame.test.js`, `tests/store/store_slices.test.js`, `tests/narrative_line_nodes.test.js` (header comment).
- Python:
  - `web/webclient/tests/test_node_suite_evidence.py` (dialogue and semantic-classes evidence file lists; new reading-controls evidence)
  - `test_vue_showcase_{action,data,world,overlays}_evidence.py`, `test_vue_showcase_evidence.py`
- Browser: `web/tests/browser/browser_helpers.py`, `test_browser_input_narrative.py`, `test_browser_shell_command_line.py`, `test_browser_exploration_dialogue.py`, `test_browser_layout.py`, `test_browser_shell_narrative.py`, `test_browser_contextual_hud_stage.py`, `test_browser_contextual_hud_anchors.py`, `test_browser_shell_dock.py`, `test_browser_shell_surfaces.py`, `test_browser_reconnect.py`, `test_browser_actions.py`, `test_browser_options_surface.py`, `test_browser_exploration_actions.py`, `test_browser_art.py`, `test_browser_local_map_interaction.py`, `test_browser_creation_viewport_pointer.py`, `test_browser_combat_menu.py`, `test_vue_foundation.py`, `.github/browser-shards.json` (renamed tests).
- Spec traceability (design D7): two IDs are replaced and nine annotations re-anchored. Two new IDs are covered.
- Dependencies:
  - Archive order: C5 → C6a → C6b → C6c (this change).
  - Blocks are written on C5 (visibility, echo), C4a (dialogue variant, the removed caption), C6b (showcase), and the main spec (desktop-shell).
  - C7 (`webclient-typewriter-reading-prefs`) and C10 (`webclient-dialogue-stage`) build on this change's window and reading-controls requirements.
  - Hot-spot files shared with C4a–C5 and C8/C10: `AppShell.vue`, `AppClient.vue`, `app-shell.css`.
