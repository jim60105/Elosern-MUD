## 1. Drawer field: Enter always sends through the plugin contract

- [x] 1.1 In `web/static/webclient/js/plugins/elosern_ui.js`, extend `routeKeyboard` so the drawer's own field (`event.target` inside `.inputfieldwrapper`, identified as the `#inputfield` textarea) is routed exactly like the open drawer: Enter without Shift calls the single `drawer.send()` path, Escape calls `drawer.close(true)`, other keys typed in the field are claimed without `preventDefault`, and Shift+Enter is left to insert a newline. The `isEditable` early-return must not swallow the drawer field first, and the creation dock's real `<input>` fields must stay untouched.
- [x] 1.2 In `web/static/webclient/js/plugins/goldenlayout.js`, remove the vestigial `form-control` class from the drawer textarea (Bootstrap is not loaded) and update the drawer comments to state that the field routes through the plugin `onKeydown` contract even when it was focused by pointer.
- [x] 1.3 In `exploration_dock.js`'s `_bindRestKeys` capture-phase handler, add a first guard that ignores any keydown whose target lies inside `.inputfieldwrapper`, so an open rest form can never swallow keys typed in the drawer field.
- [x] 1.4 Add/extend Node contract tests asserting `elosern_ui.js` routes the drawer field through the plugin `onKeydown` (no direct document listener on the field, no second send path), that `goldenlayout.js` keeps exactly one send implementation, and that the rest-form capture handler ignores `.inputfieldwrapper` events.
- [x] 1.5 Add browser journeys in `web/tests/browser/test_browser_shell.py`: (a) click directly into `#inputfield` without `/`, type a command, press Enter — exactly one text message is sent, the field clears, focus stays in the field, and the plugin reports no unhandled keydown; (b) Shift+Enter does not send; (c) open the custom rest form, click into the drawer field, press Enter — the command is sent and no `explore.wait` is submitted.

## 2. Drawer field/button alignment

- [x] 2.1 In `web/static/webclient/css/elosern.css`, convert `.inputfieldwrapper` to a flex row with `box-sizing: border-box` on the wrapper and both children: the field becomes `flex: 1 1 auto` with its height stretched by the wrapper, and `.inputsend` becomes a fixed-width (2rem) flex item with `align-self: stretch`; delete the absolute `right/top/height:100%` rules and the `calc(100% - 2.25rem)` field width. Keep the existing hover/focus-visible states and the field focus border.
- [x] 2.2 Add a geometry browser test in `web/tests/browser/test_browser_shell.py` at 1440x900 and 1280x720: compare the field, button, and wrapper bounding rectangles — the button's right, top, and bottom edges align with the field's within a 1px tolerance, and neither child extends outside the wrapper.

## 3. Exploration submenu back navigation

- [x] 3.1 In `web/static/webclient/js/elosern/exploration_menu.js`, append an enabled `{ key: "back", label: "返回上一層", enabled: true, goBack: true }` final row in `moveItems`, `lookItems`, `interactItems`, `waitItems`, `targetMenuFor`, and `keywordMenuFor`; do not touch the root menu. Add and export `parentKeyFor(menuKey)` (`move|look|interact|wait → root`, `target-<id> → interact`, `keywords-<id> → target-<id>`, unknown → root).
- [x] 3.2 In `web/static/webclient/js/plugins/elosern_ui.js`, add `item.goBack` to the exploration branch condition in `handleSubmission` so a keyboard Enter and a pointer click on the back row reach `exploration.handleItem` instead of falling through the no-`actionId` tail.
- [x] 3.3 In `web/static/webclient/js/plugins/exploration_dock.js`, add a `goBack` branch in `handleItem`: when `_menuStack` is longer than one, pop it, set `this._currentMenuKey` from its top (falling back to `parentKeyFor`/`"root"`), then call `keyboard.popMenu()`; rely on the router's synchronous `focus` event to re-render the parent's cells, keeping an explicit `_refresh()` only as a fallback when `popMenu()` returns false.
- [x] 3.4 In `exploration_dock.js`, add the `_menuStack` of menu keys pushed on `openSubmenu`/`openTarget`/`openKeywords`; on `onRouterEvent("menu-closed")`, pop it only when its length is greater than one and re-render from the new top (the existing depth ≤ 1 services/character teardown is preserved unchanged); reset it to `["root"]` on `escape-root`, `resetToRoot`, and `_discardLocalState`.
- [x] 3.5 Update `web/static/webclient/js/tests/exploration_menu.test.js`: every submenu's item list ends with the back row, the root is unchanged, `parentKeyFor` maps every submenu key correctly, and back rows are enabled, non-submitting rows.
- [x] 3.6 Add browser journeys in `web/tests/browser/test_browser_exploration.py`: (a) pointer — click Look, click 返回上一層, assert root cells render and no `ui_action` was sent; (b) keyboard — Interact → guard → 交談 → Escape twice and assert the rendered cells track the router frame at every depth (target menu then Interact list); (c) regression — Escape from Character and from a Quests/Inventory service submenu returns cleanly without corrupting or re-rendering exploration cells.
- [x] 3.7 Re-run the existing exploration journeys to confirm the appended back row does not shift their arrow counts (they should pass unchanged).

## 4. Remove the GoldenLayout tab strip

- [x] 4.1 In `web/static/webclient/js/elosern/layout_store.js`, set `settings.hasHeaders: false` in `DEFAULT_LAYOUT_CONFIG`; leave the wrapper schema, `dimensions`, and `REQUIRED_COMPONENTS` untouched.
- [x] 4.2 In `web/static/webclient/css/goldenlayout.css`, delete the dead `.lm_header`, `.lm_tab`, `.lm_tab.lm_active`, `.lm_title`, and `.lm_close_tab` rules; keep `.lm_content` and `.lm_splitter`.
- [x] 4.3 Add a browser assertion in `web/tests/browser/test_browser_layout.py` (or the shell suite): the mounted shell renders zero `.lm_header` elements while every required component is present, and the layout persistence/reset tests still pass.

## 5. Unread marker: labeled, actionable, hidden when empty

- [x] 5.1 In `web/static/webclient/js/plugins/goldenlayout.js`, restructure the marker: a `.narrative-unread` wrapper with `role="status"`/`aria-live="polite"`/`aria-atomic="true"` containing a real `<button>` labeled "↓ N 則新訊息（點擊返回最新）"; at count 0 the wrapper is hidden (`data-count="0"`/empty state). Keep the sticky position, the click-to-jump behavior, the scroll-to-bottom clear, and `updateUnread` as the single writer. Give the narrative root `tabindex="-1"` and, on keyboard activation of the marker, move focus to the narrative pane before the marker hides (pointer activation leaves focus untouched).
- [x] 5.2 In `web/static/webclient/css/elosern.css`, style the marker in the mockup's seal-red accent — border, hover state, `:focus-visible` focus ring, pointer cursor — and `display: none` when the count is zero.
- [x] 5.3 Update `web/tests/browser/test_browser_shell.py`'s unread test: assert the marker is absent while the count is zero, appears as a labeled button when unread, clicking it jumps to the bottom, clears the count, hides the marker, and keyboard activation leaves focus on a visible element (the narrative pane).

## 6. Adopt the mockup palette (visual language)

- [x] 6.1 In `web/static/webclient/css/elosern.css`, replace the `:root` tokens with the mockup families: page `#0d0d0c`; panels `#151513` (narrative), `#1b1a17` (status/map), `#211c18` (dock), `#171715` (header); borders `#514c43` / dim `#3c3933` / art `#5b574f`; paper `#e5e0d5` / dim `#aaa395` / cursor `#d4c9b5`; vermilion `#a9322a`; HP `#b3483e`; warning `#b97c73`; ok `#709676`; art gradient `#273028 → #73593e`; portrait gradient `#756b61 → #292722`. Replace the old tokens at every usage site in `elosern.css` and `goldenlayout.css` (a stale token must not survive).
- [x] 6.2 Set the focus-ring token to a lighter vermilion (starting near `#e89a6b`) and verify it stays ≥ 3:1 on both the ink surfaces and the `#a9322a` fill; adjust if needed.
- [x] 6.3 Move narrative prose and panel headings to a serif stack (Noto Serif TC / PMingLiU fallback) while keeping a monospace-first stack for the narrative's box/ASCII map art alignment; controls keep the existing UI face. Re-run the wide-row soft-wrap and map-alignment browser tests.
- [x] 6.4 Grep `web/static/webclient/` for `--elm-vermilion` uses and confirm each maps to an approved role (focus, current map position, critical/harmful/combat/disguise warnings, confirm actions, action-result live region); document any exceptions in the task result and fix stray off-role uses.
- [x] 6.5 Enforce the seal-red token-role split: the deep seal-red token is restricted to fills, borders, and large/bold text; small red text on dark surfaces uses the text-safe tokens (`--elm-warn: #b97c73` etc.). Add a repository contract test (following the `ui_contract.test.js` source-scan pattern) that fails if a dark-surface small-text CSS selector uses the deep seal-red token or its raw hex.
- [x] 6.6 Record the seal-red audit (deep token ≈2.9:1 text-on-dark → fill/border/large-text roles only; ≈5.2:1 paper-on-fill) in the design document and keep the pairing rule that seal red never carries meaning alone.

## 7. Header: location · world time · connection dot

- [x] 7.1 In `goldenlayout.js`'s `registerHeader`, render the mockup bar: letter-spaced game title on the left; on the right the current location (from `state.panels.status.actor.location.label`, "位置：--" while unsynced), the world date/time (existing `serverTime` payload), and the connection state as a dot + label using the ok-green token when connected ("● 已連線") with a shape/border-paired non-ok state. Remove the mode label.
- [x] 7.2 Update `web/tests/browser/test_browser_shell.py`'s header test: assert the header shows the location label, the world time, and the connected dot, and that no raw mode label is rendered; keep the status-presentation coverage intact.

## 8. Action dock chrome: seal-red frame, guidance line, grid buttons, submenu grid + detail pane

- [x] 8.1 In `elosern.css`, style the action dock as the mockup's command surface: `#211c18` surface, 1px seal-red frame, guidance line (11px dim) naming "方向鍵選擇・Enter 確認・Esc 返回・/ 開啟指令" (per-surface prefix like 附近動作/技能), and grid cells — `gap: 7px`, centered text, focused cell seal-red fill + `▶` glyph, unfocused bordered `#514c43`, disabled `#3c3933` border + `#716d65` text.
- [x] 8.2 In `web/static/webclient/js/plugins/dock_surface.js`, add a grid rendering mode to `renderRows` (container becomes a CSS grid whose `repeat()` count matches the menu's `gridCols`; listbox/option composite-widget pattern, container tab stop, and `aria-activedescendant` are preserved) and wire the missing disabled-reason association: every disabled row gets a stable, text-safe description element referenced by `aria-describedby` (mirrored in the visible detail pane when one exists, visually hidden otherwise), keeping the theme requirement's programmatic-association contract at every depth.
- [x] 8.3 Set grid geometry on the menu models: exploration root `gridCols: 7` (a seven-column row; rendered items vary 5–7 because Quests/Inventory are omitted when the capability is absent), exploration submenus `gridCols: 2`, combat root `gridCols: 5`, combat submenus `gridCols: 2`, and the services/creation/character submenu item lists `gridCols: 2`. Add Node tests covering the full ArrowUp/Down/Left/Right transition matrix for odd-count 2-column grids (7 items: the final cell sits bottom-left; empty cells return false without moving) and `focusItemByKey` by row/column.
- [x] 8.4 Restructure the exploration, combat, services, creation, and character dock DOM to the mockup split: dock body `≈1.35fr / 0.9fr` grid with the item grid on the left and the existing detail pane (exploration-detail / combat-detail / services-detail / creation-detail) on the right; the exploration root shows hint line + 7-column cell row with no visible detail pane (disabled rows keep their visually hidden description elements). Submenu detail panes name the focused item, its availability/cost, and the next key action ("Enter → 選擇目標").
- [x] 8.5 Services, creation, and character docks adopt the grid + detail split for their submenu item lists while keeping their existing forms, quantity fields, and confirmation structures; the character panel's display-only rows render as grid cells without submission.
- [x] 8.6 In `web/static/webclient/js/elosern/keyboard_router.js`, extend the existing repeated-Enter suppression to Space (held Space must not repeatedly toggle AREA candidates), with Node tests; keep `confirm()` semantics unchanged.
- [x] 8.7 Add Node tests for `dock_surface` grid rendering and disabled-reason `aria-describedby` wiring, and browser assertions in `test_browser_shell.py` / `test_browser_combat.py`: dock frame, guidance line, grid cells, seal-red focused cell with `▶`, dimmed disabled cells, submenu detail pane at 1440x900 and 1280x720, plus an AREA journey — move across the 2-column target grid, press Space once (selection marker visible), press Enter, assert the final payload and that held Space toggles at most once.

## 9. Status gauge bars, panel headings, art placeholder

- [x] 9.1 In `goldenlayout.js`'s `renderStatus`, add the "角色狀態" heading and HP/MP/SP gauge bars (HP fill `#b3483e`; MP/SP derived from the palette) rendered as accessible width-based elements, keeping the numeric "current / maximum" text.
- [x] 9.2 Add the "附近地圖" heading and mockup panel styling to the local-map surface; keep the landed lattice, legend, and remembered-node list.
- [x] 9.3 Restyle the art surface: truthful placeholder adopts the `#273028 → #73593e` gradient with the scene label bottom-left; the contextual portrait overlay keeps its 3:4 card with a 2px seal-red frame.
- [x] 9.4 Update `test_browser_shell.py` status assertions (bars + numbers still present) and the art placeholder journey.

## 10. Spec evidence

- [x] 10.1 Add one subprocess bridge test in `web/webclient/tests/test_node_suite_evidence.py` per new or modified JS-verified requirement from this change (drawer always-send, no-tab-strip, header location/connection, dock grid + detail, unread marker labeling, exploration back rows), following the file's existing pattern.

## 11. Validation and handoff

- [x] 11.1 Run the Node suite (`node --test web/static/webclient/js/tests/*.test.js`) and fix failures.
- [x] 11.2 Run the affected browser suites (`test_browser_shell.py`, `test_browser_exploration.py`, `test_browser_layout.py`, `test_browser_combat.py`) and fix failures.
- [x] 11.3 Run `uv run --locked python -m tools.spec_traceability check` and attach `covers_requirement` to every new or modified main requirement covered by a discoverable `test_*`.
- [x] 11.4 Run `openspec validate webclient-ui-polish --strict`, confirm `git diff --check` is clean, and run the full non-browser Evennia suite for the affected ownership domains.
