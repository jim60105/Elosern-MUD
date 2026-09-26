## 1. Preconditions

- [x] 1.1 Confirm C8b (`webclient-scene-overview-swap`) is archived: `grep -n "overviewMenu" web/webclient-app/stores/frame-resolvers.js` matches, and `openspec/specs/webclient-exploration-menu/spec.md` contains "The exploration dock is keyboard-first and roots at the scene overview". Stop and report otherwise.

## 2. Model, resolvers, store

- [x] 2.1 Prove the frames are unreachable. `git grep -n "exploration\.move\|exploration\.look\|exploration\.interact\|openSubmenu: \"\(move\|look\|interact\)\"" web/webclient-app web/static/webclient/js -- ':!dist' ':!*/tests/*'` shows only the resolver entries and `EXPLORATION_SUBMENU_PUSHES`. Stop and report if there is a push site.
- [x] 2.2 `web/static/webclient/js/elosern/exploration_menu.js` (design D1):
  - delete `rootItems`, `interactItems`, `parentKeyFor`, and `openItem`
  - reduce `buildMenus` to `wait` and `suggestions`
  - strip the back row, the `move-empty` placeholder, and the `（無法通行）` suffix from `moveItems`, and the back row from `lookItems`
  - drop `overviewMenu`'s stripping code
  - trim the export list and header comment
- [x] 2.3 `web/webclient-app/stores/frame-resolvers.js`: delete the `exploration.move`, `exploration.look`, and `exploration.interact` entries and update the header comment. `web/webclient-app/stores/elosern/frames.js`: `EXPLORATION_SUBMENU_PUSHES` keeps `wait` and `suggestions`.
- [x] 2.4 `web/webclient-app/stores/elosern/interaction.js` `focusPress` (design D3):
  - digits `1`–`9`
  - no outlet filter; delete the `classifyPane` import
  - update the comments that cite the 1–4 legend and the outlet rule
- [x] 2.5 Node tests:
  - `web/static/webclient/js/tests/exploration_menu.test.js`: delete the `parentKeyFor` test and the root/move/look/interact `buildMenus` assertions. Keep the `targetMenuFor`, `keywordMenuFor`, `wait`, and `suggestions` cases, re-pointed at `buildMenus`' remaining menus or `overviewMenu`, with synthesized fixtures only.
  - `hud_dock_menus.test.js`: replace the `ExplorationMenu.rootItems` suggestion-entry cases with `overviewMenu` footer cases. The `moveItems` case asserts the plain chip shape.

  Run `node --test web/static/webclient/js/tests/*.test.js` and `uv run --locked python -m tools.test_data_lint check`. Both green.

## 3. Components

- [x] 3.1 `web/webclient-app/components/DockMenu.vue`: delete the outlet pane, `outletRows`, `outletSpanCol`, the outlet grid-style branch, the outlet `aria-activedescendant` and detail clauses, and the `dock-exits.js` import. Update the header comment's pane-kind list. `web/webclient-app/components/dock-panes.js`: delete the `outlet` kind and the `interact` / `suggestions` badge branches, and update the comments. `web/webclient-app/styles/app-shell.css` carries no outlet rule and no outlet comment (a repo-wide case-sensitive search finds none), so there is nothing to delete there.
- [x] 3.2 `web/webclient-app/composables/use-dock.js`: drop the `direction` / `destination` normalization in the exploration branch of `dockItems`. `git grep -n "\.direction\|\.destination" web/webclient-app/components/DockMenu.vue` returns nothing.
- [x] 3.3 `web/webclient-app/components/DockBreadcrumb.vue`: delete `focusedKey` and `dock-crumb__back--focused` (design D4). `ActionDock.vue` stops passing it. `stories/Action/DockBreadcrumb.stories.js` drops a focused-back story or arg if present.
- [x] 3.4 `web/webclient-app/components/ActionDock.vue`: the legend reads `數字鍵 1–9 · <kbd>Enter</kbd> 執行 · <kbd>Esc</kbd> 返回`.

## 4. Vitest

- [x] 4.1 Delete `web/webclient-app/tests/action/dock_menu_outlet.test.js`. In `tests/components/dock_panes.test.js`, delete the outlet classification and the interact/suggestions badge cases; the skills badge cases stay. In `tests/action/dock_menu_panes.test.js`, delete any outlet case.
- [x] 4.2 `web/webclient-app/tests/frame-resolvers.test.js`: replace the `exploration.move/look/interact` cases with one table-driven case asserting each resolves to `{unresolvable: true, reason: null}` (design D2).
- [x] 4.3 `web/webclient-app/tests/store/digit_row_picks.test.js`:
  - `5`–`9` on the overview pick chips in reading order
  - `9` on a nine-chip overview picks the ninth chip, and `9` on a six-chip overview is unclaimed
  - a combat skill frame's `6`th row
  - a dialogue variant at its panel-owned bound (four picks) answering `4`, with `5` unclaimed
  - held repeats suppressed
  - no outlet case

  `tests/action/action_dock.test.js`: the legend reads `1–9`. Run `pnpm test` green.

## 5. Browser

- [x] 5.1 `web/tests/browser/test_browser_exploration_tiles.py` (design D5): convert the narrow-viewport test to the overview chip-wrap test and split off the nav-pane case, then delete `test_outlet_last_row_never_leaves_blank_space_at_a_narrower_viewport`. `test_browser_contextual_hud_dock.py`: replace the direct outlet push with overview assertions. `test_browser_shell_dock.py`: the legend text reads `1–9`. Re-point the move-frame pushes in `test_browser_exploration_frame.py` and `test_browser_exploration_state.py` at the scene overview, and delete the now-unused `push_exploration_frame` helper in `browser_helpers.py`. Remove outlet mentions in `test_browser_exploration_{dialogue,frame,nav}.py`. `git grep -n "outlet\|dock-crumb__back--focused" web/tests/browser` returns nothing.

## 6. Specs and traceability

- [x] 6.1 Sync this change's deltas into the main specs. Re-anchor `webclient-contextual-hud::a-fixed-column-count-dock-pane-sizes-its-columns-to-content-never-stretching-to-fill-the-panel` in `test_browser_exploration_tiles.py`: to `webclient-contextual-hud::a-fixed-column-dock-pane-sizes-its-columns-to-content` for the nav-pane test, and to `webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-roots-at-the-scene-overview` for the chip-wrap test. Confirm the IDs with `uv run --locked python -m tools.spec_traceability list`, then run `uv run --locked python -m tools.spec_traceability check` green.

## 7. Validation

- [x] 7.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.spec_traceability check`. All green.
- [ ] 7.2 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_exploration_tiles web.tests.browser.test_browser_contextual_hud_dock web.tests.browser.test_browser_shell_dock web.tests.browser.test_browser_exploration_nav web.tests.browser.test_browser_exploration_frame web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_browser_combat_menu web.tests.browser.test_browser_pointer`, and `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence`. All green.
- [x] 7.3 Run `openspec validate webclient-retire-exploration-submenus --strict` and `git diff --check`. Both clean.
