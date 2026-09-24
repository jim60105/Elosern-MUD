## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §2.7, §4, §5.1, §5.5) hides the command line by default. After C4a (`webclient-avg-stage-shell`) the line is a permanent 64px row on the message region's top edge. It covers the lowest strip of the stage, including the player portrait's feet, in every mode, although most turns are played from the command panel.

The line also carries the only pointer path to five overlay and drawer openers: 技能系譜, 圖鑑, 稱號冊, 說明, and (since C3) 角色肖像圖庫. It carries a sixth, 設定, that repeats the top bar's 設定. If the line collapses, those openers need another home that is still one pointer action away.

This change makes the line collapsible and moves the utility cluster into the 48px top bar from C4b (`webclient-avg-place-card-top-bar`). The project is unreleased, so the "permanently present" contract, its tests, and the cluster's old markup are deleted, not kept behind a flag.

## What Changes

- **BREAKING (internal)**: the command line is collapsed by default.
  - `components/AppShell.vue` owns one client-local `commandLineExpanded` flag. It starts `false` on every mount, is never persisted, and is reset to `false` when the mode becomes `creation`.
  - `components/HudFrame.vue` gains a `commandLineExpanded` prop, rendered as `data-expanded` on the `command-line` anchor. A collapsed anchor is `display:none`.
  - `CommandLine` stays mounted, so `#inputfield` stays in the DOM inside `.inputfieldwrapper` (the preserved contract). While collapsed, the field is out of the layout, the accessibility tree, and the tab order.
- Three paths expand the line and focus the field:
  - `/` outside an editable control (the existing bridge → router `toggle-drawer` → `drawerRequest` → `use-shell-focus.js` → `focusCommandField` route)
  - a new ⌨ disclosure button (`data-testid="command-line-toggle"`, `aria-label="指令列"`, `aria-expanded`, `aria-controls` naming the bar), which `AppShell` renders at the bottom-right of the `band-message` region
  - the free-form dialogue borrow (`freeformTarget` set by `borrowDialogueCommand` or the dock's freeform item, then `explore.talk_freeform` on send), which already goes through `drawerRequest`

  `focusCommandField` now expands first and focuses after the DOM update.
- Two paths collapse the line and return focus to `#action-dock`:
  - Escape in the field. The unsent draft is kept for the next expansion.
  - A send the field accepts. `CommandLine` emits a new `sent` event at the same point where it clears the draft. The borrowed path's existing `drawerCloseRequest` signal also collapses the line.

  Focus moves to the dock before the row hides. A rejected send keeps the text, keeps focus, and keeps the line open. A send is rejected when the client is offline, mutations are locked, or a mutation is in flight. Activating the ⌨ toggle while the line is open collapses it and leaves focus on the toggle.
- History, Tab completion, the hint cluster, and the single send path do not change.
- **BREAKING (internal)**: the expanded row is 44px. `--command-line-h` in `styles/tokens.css` becomes `44px`, and `.cmdline` fills the anchor. Every consumer of the token follows it: the anchor, `--stage-content-bottom`, `HudDrawer`'s top inset, `OverlayHost`'s inset, `--workspace-bottom`, and `ToastQueue`.
- **BREAKING (internal)**: the utility cluster moves to the top bar.
  - `CommandLine.vue` deletes `span.cmdutil` and its five buttons (`command-line-lineage`, `command-line-lore`, `command-line-codex`, `command-line-settings`, `command-line-help`), plus C3's gallery button, the `open-overlay` / `open-drawer` emits, and C3's `galleryAvailable` prop.
  - `components/DesktopNavigation.vue` gains a labelled tool group after 設定 (`role="group"`, `aria-label="工具"`). It holds icon-only buttons: 技能系譜 (`nav-tool-lineage`), 圖鑑 (`nav-tool-lore`), 稱號冊 (`nav-tool-codex`), 角色肖像圖庫 (`gallery-opener`, kept, rendered only while the `gallery` panel is available), and 說明 (`nav-tool-help`). Each has an `aria-label` and a matching `title`.
  - The existing 設定 button gains `data-testid="nav-settings"`, and the command line's duplicate 設定 is deleted.
  - Openers keep their existing paths: `AppClient`'s `onOpenOverlay` (lineage, codex, gallery, help) and a new `@drawer` binding to `onOpenDrawer('lore')`.
  - `galleryAvailable` moves from `AppShell`/`CommandLine` to `DesktopNavigation`.
- `lib/controls-reference.js`: the `/`, Enter, and Esc rows describe expanding and collapsing the line.
- Spec deltas:
  - The permanent-bar and permanent-field requirements are replaced by collapsible ones.
  - The visibility matrix gains the collapsed row and the toggle.
  - The top navigation bar gains the tool group.
  - The requirements that justify behaviour by "the field is permanently present" are restated.
  - The codex-opener requirement moves to the top bar.
- No OOB schema, presenter, server, store-state, router, or persistence change. No component is added or deleted, so the component manifest is unchanged.

Out of scope:
- The paged message window, its 日誌 button, and its reading controls are owned by `webclient-message-paging` (C6). The ⌨ toggle is an `AppShell` sibling of the band-message content, so C6 replaces `NarrativeFeed` without moving it.
- The dialogue stage (the centred choice list with the `⌨ 自由對話` row, the collapsed command panel, and the full-width message window) is owned by `webclient-dialogue-stage` (C10). This change only makes the existing borrow path expand the line.
- Expand and collapse motion is owned by `webclient-motion-layer` (C11). Here the row appears and disappears instantly.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED "Surface visibility is gated by the committed game mode", on C4c's text: the command line is collapsed until opened, and the ⌨ toggle row is added.
  - REMOVED "The command line is a permanently present bar in the stage's command-line anchor" (last modified by C4a).
  - ADDED "The command line is a collapsible row docked on the message region's top edge".
  - MODIFIED "The map, settings, and help surfaces are reachable from the live client", on C3's text: settings and help open from the top navigation bar.
- `webclient-desktop-shell`:
  - MODIFIED "Required desktop surfaces remain visible and usable", on C4b's text: the toggle is always visible, the field is one action away, and the bar carries the tool group.
  - MODIFIED "Keyboard routing is menu-first and submission-safe": `/` expands the collapsed line.
  - REMOVED "The command drawer preserves ordinary text control" (last modified by C3).
  - ADDED "The collapsible command line preserves ordinary text control".
  - ADDED "The top navigation bar carries the tool group".
- `webclient-input-narrative`: MODIFIED "A deliberate mutation echo appears exactly once at dispatch", on C3's ADDED text: a completed borrow collapses the line.
- `webclient-pointer-activation`: MODIFIED "Keyboard input is dispatched through the WebClient plugin contract": field ownership follows focus, whether or not the line is expanded.
- `webclient-browser-verification`: MODIFIED "Browser acceptance covers foundation recovery and layout behavior": the shell journey opens the line with `/`.
- `webclient-lore-codex-panel`:
  - REMOVED "The codex opens from the command-line utility strip, not from the quest drawer"
  - ADDED "The codex opens from the top navigation bar, not from the quest drawer"

## Impact

- Edited components and client code:
  - `web/webclient-app/components/CommandLine.vue`, `AppShell.vue`, `HudFrame.vue`, `DesktopNavigation.vue`
  - `web/webclient-app/AppClient.vue`
  - `composables/use-shell-focus.js` (comments; the watchers keep their calls)
  - `lib/controls-reference.js`, `styles/tokens.css`, `styles/app-shell.css`
  - comments only: `stores/elosern/frames.js`, `stores/elosern/interaction.js`, `stores/elosern/transport.js`, `HudDrawer.vue`
- Edited stories: `stories/Core/CommandLine.stories.js`, `AppShell.stories.js`, `DesktopNavigation.stories.js`, `HudFrame.stories.js`, `HudDrawer.stories.js` (description text).
- Vitest:
  - `tests/command_line.test.js`, `tests/app.test.js`, `tests/preserved_contract.test.js`, `tests/bridge/app_shell_bridge.test.js`, `tests/app_client_completion.test.js`
  - `tests/hud_frame.test.js`, `tests/hud_drawer.test.js`, `tests/desktop_navigation.test.js` (from C4b)
  - `tests/app_client_gallery.test.js`, `tests/overlays/lineage_panel.test.js`, `tests/overlays/title_codex_panel.test.js`, `tests/overlays/deferred_surfaces_absent.test.js`, `tests/overlays/help_overlay.test.js`
- Python evidence: `web/webclient/tests/test_node_suite_evidence.py` (annotations only).
- Browser tests:
  - `web/tests/browser/browser_helpers.py`: a new `open_command_line(page)` helper, and `REQUIRED_SURFACES` names the toggle
  - `test_browser_shell_command_line.py`, `test_browser_input_narrative.py`, `test_browser_layout.py`, `test_browser_contextual_hud_stage.py`, `test_browser_shell_surfaces.py`, `test_browser_shell_narrative.py`, `test_browser_actions.py`, `test_browser_art.py`, `test_browser_exploration_dialogue.py`, `test_vue_foundation.py`, `test_browser_contextual_hud_drawers.py`, `test_browser_title_codex.py`, `test_browser_lineage.py`
  - `.github/browser-shards.json`
- Spec traceability: four requirement IDs are replaced, and their annotations are re-anchored (design D9). One new ID is covered by a new Vitest evidence case and a browser test.
- Dependencies:
  - Archive order C1 → C2 → C3 → C4a → C4b → C4c → C5 (this change).
  - This change's blocks are written on C4c (visibility), C4a (the removed command-line bar), C4b (required desktop surfaces), and C3 (the removed command drawer, "map, settings, and help", and the echo requirement). It must be archived after all of them.
  - C6 (`webclient-message-paging`) and C10 (`webclient-dialogue-stage`) build on the ⌨ toggle's position and on the expand path.
  - The hot-spot files `AppShell.vue`, `HudFrame.vue`, `AppClient.vue`, and `app-shell.css` are shared with C4a–C4c and C6, so these changes run one after another, never in parallel worktrees.
