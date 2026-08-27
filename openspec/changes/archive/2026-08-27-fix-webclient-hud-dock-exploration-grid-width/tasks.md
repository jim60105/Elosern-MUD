# Tasks — fix-webclient-hud-dock-exploration-grid-width

## 1. Outlet pane layout (DockMenu.vue)

- [x] 1.1 Change `paneGridStyle` in `web/webclient-app/components/DockMenu.vue` so the `outlet` pane emits no inline `grid-template-columns` (return `{}` for `paneKind === 'outlet'`), and change the `.dock-menu__outlet` CSS class rule to `repeat(auto-fit, minmax(min(150px, 100%), 1fr))` so empty tracks collapse, the tiles fill the pane's full width (including 1-exit and 2-exit frames), and the track floor shrinks to the pane's own width when the pane is narrower than 150px (no horizontal overflow); keep `nav` panes on their fixed-column content-sized tracks.
- [x] 1.2 Remove the `max-width: 220px` cap from `.dock-menu__outlet-tile` (keep `min-width: 0` + `overflow-wrap: break-word`) so tiles stretch with their `1fr` tracks and fill the available horizontal space.
- [x] 1.3 Give the breadcrumb's back control a focused state: pass `:focused-key` from `ActionDock` to `DockBreadcrumb`, and when `focusedKey === "back"` render the back control with a background fill + border swap (the non-color-alone treatment) so the non-rendered `back` row keeps a visible focus carrier.

## 2. Move menu keyboard geometry (exploration_menu.js)

- [x] 2.1 In `web/static/webclient/js/elosern/exploration_menu.js` `buildMenus`, set the move menu's `gridCols` from `2` to `null` (keep `grid: true` and the `back` row) so the keyboard router navigates the move frame as a single-column list.

## 3. Update Vitest suite

- [x] 3.1 Update `web/webclient-app/tests/action/dock_menu_panes.test.js`: the "outlet/nav panes emit content-sized tracks" test — the outlet case now expects an empty inline `gridTemplateColumns` on `.dock-menu__outlet` (the CSS `auto-fit` rule governs); the "long destination and affordance labels wrap" test drops the `max-width: 220px` CSS assertion.
- [x] 3.2 Run `npm test` (Vitest) until green.

## 4. Update Node gate suite

- [x] 4.1 Update `web/static/webclient/js/tests/exploration_menu.test.js`: the "menu models carry the mockup grid geometry" test now asserts `model.menus.move.gridCols === null` (look/interact/wait keep `2`, root keeps `items.length`).
- [x] 4.2 Run `node --test web/static/webclient/js/tests/*.test.js` until green.

## 5. Update managed browser suite (CI)

- [x] 5.1 In `web/tests/browser/test_browser_exploration.py`, replace the `assert_not_stretched(".dock-menu__outlet-tile", ".dock-menu__outlet")` check with a stretched-to-fill assertion: verify the first tile's left edge and the last tile's right edge align with the pane's content edges (the 8px gap between tiles is part of the occupied span), covering the 1-exit, 2-exit (`auto-fit` collapses the empty tracks), and multi-exit (tiles fill the width in N columns of at least 150px) cases. Update the post-ArrowRight focus assertion: in the move frame ArrowRight is a no-op (focus stays on the current item; ArrowUp/ArrowDown cycle the exit rows and then the `back` row). Add a breadcrumb back-focus assertion: when focus moves to the `back` row, the breadcrumb's back control renders the focused state, and Enter pops exactly one level.
- [x] 5.2 Run the single focused browser test class locally (within the 10-minute budget); the full managed browser suite and `tools.spec_traceability verify --evidence` stay CI-owned.

## 6. Traceability and validation

- [x] 6.1 Run `uv run --locked python -m tools.spec_traceability check` and keep it green (the modified requirements keep their substantively matching tests).
- [x] 6.2 Run `openspec validate fix-webclient-hud-dock-exploration-grid-width --strict` and fix any delta-spec formatting issues.
