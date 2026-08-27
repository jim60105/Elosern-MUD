# Tasks — fix-webclient-hud-dock-exploration-grid-width

## 1. Outlet pane layout (DockMenu.vue)

- [ ] 1.1 Change `paneGridStyle` in `web/webclient-app/components/DockMenu.vue` so the `outlet` pane emits no inline `grid-template-columns` (return `{}` for `paneKind === 'outlet'`), and change the `.dock-menu__outlet` CSS class rule from `repeat(auto-fill, minmax(150px, 1fr))` to `repeat(auto-fit, minmax(150px, 1fr))` so empty tracks collapse and the tiles fill the pane's full width (including 1-exit and 2-exit frames); keep `nav` panes on their fixed-column content-sized tracks.
- [ ] 1.2 Remove the `max-width: 220px` cap from `.dock-menu__outlet-tile` (keep `min-width: 0` + `overflow-wrap: break-word`) so tiles stretch with their `1fr` tracks and fill the available horizontal space.

## 2. Move menu keyboard geometry (exploration_menu.js)

- [ ] 2.1 In `web/static/webclient/js/elosern/exploration_menu.js` `buildMenus`, set the move menu's `gridCols` from `2` to `null` (keep `grid: true` and the `back` row) so the keyboard router navigates the move frame as a single-column list.

## 3. Update Vitest suite

- [ ] 3.1 Update `web/webclient-app/tests/action/dock_menu_panes.test.js`: the "outlet/nav panes emit content-sized tracks" test — the outlet case now expects an empty inline `gridTemplateColumns` on `.dock-menu__outlet` (the CSS `auto-fit` rule governs); the "long destination and affordance labels wrap" test drops the `max-width: 220px` CSS assertion.
- [ ] 3.2 Run `npm test` (Vitest) until green.

## 4. Update Node gate suite

- [ ] 4.1 Update `web/static/webclient/js/tests/exploration_menu.test.js`: the "menu models carry the mockup grid geometry" test now asserts `model.menus.move.gridCols === null` (look/interact/wait keep `2`, root keeps `items.length`).
- [ ] 4.2 Run `node --test web/static/webclient/js/tests/*.test.js` until green.

## 5. Update managed browser suite (CI)

- [ ] 5.1 In `web/tests/browser/test_browser_exploration.py`, replace the `assert_not_stretched(".dock-menu__outlet-tile", ".dock-menu__outlet")` check with a stretched-to-fill assertion: the outlet tiles together occupy the pane's full width — verify the 1-exit and 2-exit cases (`auto-fit` collapses the empty tracks, each tile gets a full-width share) and the multi-exit case (tiles fill the width in N columns of at least 150px). Update the post-ArrowRight focus assertion: in the move frame ArrowRight is a no-op (focus stays on the current item; ArrowUp/ArrowDown cycle the exit rows and then the `back` row).
- [ ] 5.2 Run the single focused browser test class locally (within the 10-minute budget); the full managed browser suite and `tools.spec_traceability verify --evidence` stay CI-owned.

## 6. Traceability and validation

- [ ] 6.1 Run `uv run --locked python -m tools.spec_traceability check` and keep it green (the modified requirements keep their substantively matching tests).
- [ ] 6.2 Run `openspec validate fix-webclient-hud-dock-exploration-grid-width --strict` and fix any delta-spec formatting issues.
