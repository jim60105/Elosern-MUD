## Why

The exploration dock's move/look/interact frames render far fewer, far wider tiles/rows than
`docs/design/elosern-redesign/index.html`'s `.outlet`/`.ngrid` grids — reproduced live at 1440x900: a
4-exit room renders exactly two ~450px-wide tiles per row instead of a compact, content-sized wrap.

Root cause, verified by direct inspection and a live `getComputedStyle` check (forcing the same rule via
`!important` reproduces the correct 5-column layout, proving the CSS class itself is not the problem):
`exploration_menu.js`'s `buildMenus()` sets `grid: true, gridCols: 2` for the `move`, `look`, and
`interact` sub-menus (`exploration_menu.js:644-663`; `wait` also sets `gridCols: 2` but is unaffected —
see below). This `gridCols` value serves two different, unrelated purposes today: (1)
`keyboard_router.js`'s `move()` uses it as the row/col divisor for `ArrowLeft/Right/Up/Down` geometry,
and (2) `DockMenu.vue`'s `paneGridStyle` computed feeds the *same* number straight into
`grid-template-columns: repeat(2, 1fr)` as an inline style on the pane's row container — overriding that
pane's own CSS class (`.dock-menu__outlet`, `.dock-menu__nav`), which already defines the correct
responsive rule (`repeat(auto-fill, minmax(150px, 1fr))` etc., matching the reference). The `1fr` track
function stretches each of the 2 forced columns to fill half the available width, producing the oversized
tiles.

**`wait`'s menu is not affected and is out of this change's scope.** `wait`'s items classify to the
`plain` pane kind (`dock-panes.js:classifyPane()`, verified by elimination), which renders through
`.dock-menu__plain` — a container with **no `display: grid` rule at all** (verified: no CSS block exists
for this class anywhere in `DockMenu.vue`; only its single template usage). `grid-template-columns` has
no effect on a non-grid container, so the inline override has always been inert there. Confirmed live:
the 等待/休息 frame already renders six compact, correctly-sized buttons per row today, with no width
defect. An earlier draft of this proposal incorrectly generalized the `outlet`/`nav` defect to `wait` by
pane-kind analogy without reproducing it independently; this revision corrects that.

The `gridCols: 2` **keyboard geometry** is intentional and load-bearing, not a bug: at least ten existing
Playwright assertions across `test_browser_exploration.py` and `test_browser_contextual_hud.py` press
`ArrowRight` and expect it to move focus to "the second grid column" for exactly these menus. Changing
the column *count*, or the router's grid model, would break that tested, real keyboard-navigation
contract and is out of this change's scope. The defect is narrower than that: the same number is also
driving *visual track width* for the two pane kinds that are actual CSS grids, which it was never meant
to do — `keyboard_router.js` only ever reads `gridCols` as a plain integer divisor for index math; it has
no opinion on how wide a track renders.

## What Changes

- In `DockMenu.vue`'s `paneGridStyle` computed, when the active pane kind is `outlet` or `nav` (the
  exploration move/look/interact frames — the two pane kinds that are actual CSS grid containers among
  `exploration_menu.js`'s affected `gridCols: 2` menus), change the inline override's track-sizing
  function from `1fr` to `minmax(0, max-content)`: `grid-template-columns: repeat(2, minmax(0, max-content)`.
  The column **count** (and therefore every keyboard row/col computation) is completely unchanged; only
  how wide each of those 2 columns renders changes — each now sizes to its own tile's natural content
  width instead of stretching to fill half the dock. The `min` of `0` lets the tracks compress (not
  overflow) when the pane is narrower than the combined content width, which matters at the minimum
  supported 1280x720 viewport where the dock's available width can be squeezed by the detail aside.
- Add a `max-width` safety cap plus `min-width: 0` and `overflow-wrap: break-word` on
  `.dock-menu__outlet-tile` (220px) and `.dock-menu__nav-row` (320px), and add a `min-width: 0;
  overflow-wrap: break-word;` rule on `.dock-menu__nav-text`, so an unusually long server-authored
  destination name or joined affordance-label list wraps within the bounded tile/row instead of pushing
  the layout past the pane's available width (the flex text block's automatic min-content size would
  otherwise let a long string break the 320px row cap).
- Leave `paneGridStyle`'s behavior for every other pane kind (`affordance`, `cards`, `skills`, `targets`,
  `scales`, `confirm`, `plain` — the suggestions, combat, and every service/creation/wait frame) exactly
  as it is today. None of those is a CSS grid container whose inline override is doing anything visible
  today except `outlet`/`nav` (verified: `plain` has no `display: grid` rule at all, and several
  `plain`-classified menus outside exploration — `service_menu.js`'s `guild`/`board`/`quests`/`shop`/
  `stock`/`sell`/`inventory` and `creation_menu.js`'s `presets`, all `gridCols: 2` — share that same
  inert-override status, so they are correctly out of scope by construction, not by omission).
- **BREAKING**: none. No change to `exploration_menu.js`, `keyboard_router.js`, the store, any prop,
  event, DOM id, `data-testid`, dispatch, or protocol contract. The rendered tile width and the pane's
  remaining empty space are the only observable differences; every existing keyboard-navigation
  assertion's item-to-cell mapping is unaffected because the column count never changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`: gains a new requirement that a dock pane's forced-column-count layout
  (used where the keyboard router needs a fixed grid geometry) sizes each column to its content, never
  stretching a narrow-content row or tile to fill the panel's remaining width, and compresses the fixed
  columns (min track size 0) when the pane is narrower than the combined content width instead of
  overflowing it.

## Impact

- **Code**: `web/webclient-app/components/DockMenu.vue` (`paneGridStyle` computed; the `max-width` +
  `min-width: 0` + `overflow-wrap: break-word` safety caps on `.dock-menu__outlet-tile` and
  `.dock-menu__nav-row`, plus the new `.dock-menu__nav-text` rule).
- **Tests**: a new Vitest assertion on the pane element's inline `grid-template-columns` per pane kind
  (verifying the `outlet`/`nav` branch emits `minmax(0, max-content)` and every other pane kind —
  including `plain` — still emits `1fr`, unchanged); a rendering test with a long destination/affordance
  label confirming the tile wraps within its `max-width` cap rather than overflowing; a new Playwright test
  at the minimum supported 1280x720 viewport (`test_browser_exploration.py`) confirming the outlet tiles
  and nav rows stay within the pane's width, that `ArrowRight` still moves focus to the second grid
  column, and that the 等待/休息 (plain) pane stays a non-grid block container; registered in
  `.github/browser-shards.json` so the CI shard-ownership contract keeps passing. No existing
  Playwright keyboard-navigation assertion needs to change, since column count and item-to-cell mapping
  are untouched — task-tracked confirmation, not merely assumed.
- **Docs**: none.
- **No protocol, read-model, dispatch, keyboard-router, or `exploration_menu.js` changes.**
