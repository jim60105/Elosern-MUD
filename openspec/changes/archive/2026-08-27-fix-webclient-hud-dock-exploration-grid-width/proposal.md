## Why

The action dock's exit-outlet pane (the exploration move frame) currently renders as a fixed two-column grid: `DockMenu` applies an inline `grid-template-columns: repeat(2, minmax(0px, max-content))` for the outlet pane, so the exit tiles are content-sized and the pane's remaining horizontal space stays empty. The redesign draft (`docs/design/elosern-redesign/index.html`, `.outlet` uses `repeat(auto-fill, minmax(150px, 1fr))` with tiles that stretch with their tracks) calls for the outlet to fill the available horizontal space, not to be limited to two columns. To fully fill the pane's horizontal space when few exits are present, the outlet grid SHALL use `repeat(auto-fit, minmax(150px, 1fr))`: unlike the draft's `auto-fill`, `auto-fit` collapses the empty tracks, so the rendered tiles alone consume the whole pane width.

## What Changes

- The outlet pane stops emitting an inline `grid-template-columns` override, so the CSS class rule takes over: `repeat(auto-fit, minmax(150px, 1fr))` on `.dock-menu__outlet` (a deliberate deviation from the draft's `auto-fill`: `auto-fit` collapses empty tracks, so even a 1- or 2-exit frame fills the pane's full width with no large blank region).
- The `max-width: 220px` cap on `.dock-menu__outlet-tile` is removed so tiles stretch with the `1fr` tracks and fill the available horizontal space; long labels still wrap inside the track (`min-width: 0` + `overflow-wrap: break-word` stay).
- The move frame's keyboard geometry becomes a single-column list: the move menu model's `gridCols` changes from `2` to `null`, so `keyboard_router` navigates the move frame's items vertically (Up/Down cycle through the exit rows and the `back` row; Left/Right are no-ops). The visual layout does NOT drive the keyboard geometry: the focus key and the `explore.move` payload stay stable across window resizes.
- Affected tests are updated to the new contract: the Vitest pane test (no inline grid template for the outlet pane), the Node exploration-menu test (move `gridCols` is `null`), and the Playwright exploration test (outlet tiles are stretched to fill the pane; ArrowRight is a no-op in the move frame).

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `webclient-contextual-hud`: the fixed-column-count requirement is amended so the exit-outlet pane is exempt — it uses a width-adaptive `auto-fit` grid whose tiles fill the pane's available width (empty tracks collapse); the per-kind pane-vocabulary requirement is amended so the move frame's row region fills the pane's full width and tiles stretch with their tracks.
- `webclient-exploration-menu`: the keyboard-first requirement is amended so the move submenu is navigated as a single-column list (vertical only, cycling the exit rows and the `back` row), because the rendered outlet column count follows the pane width and the DOM-independent router cannot know it.

## Impact

- `web/webclient-app/components/DockMenu.vue`: `paneGridStyle` skips the inline `grid-template-columns` for the outlet pane; the `.dock-menu__outlet` class rule changes from the draft's `auto-fill` to `auto-fit`; the `.dock-menu__outlet-tile` rule drops its `max-width` cap.
- `web/static/webclient/js/elosern/exploration_menu.js`: `buildMenus` sets the move menu's `gridCols` to `null`.
- `web/static/webclient/js/elosern/keyboard_router.js`: no code change — with `grid: true` and `gridCols: null` it already falls back to list navigation.
- Tests: `web/webclient-app/tests/action/dock_menu_panes.test.js` (outlet pane carries no inline `grid-template-columns`; tile CSS rule has no `max-width`), `web/static/webclient/js/tests/exploration_menu.test.js` (move `gridCols` is `null`), and `web/tests/browser/test_browser_exploration.py` (the `assert_not_stretched` check flips to a stretched-to-fill assertion: the outlet tiles together occupy the pane's full width, including the 1-exit and 2-exit cases where `auto-fit` collapses the empty tracks; ArrowRight is a no-op in the move frame; ArrowUp/Down cycle the exit rows and the `back` row).
- Player-facing command surface is unchanged (no command added, removed, renamed, or re-aliased), so `docs/game/commands.md` / `docs/game/command-reference.md` and `tests/test_command_docs.py` need no update.
- Spec-test traceability: the two modified requirements keep their substantively matching tests (updated Vitest/Node/browser tests); `tools.spec_traceability check` must stay green.
