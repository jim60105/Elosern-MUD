## Context

The version-1 desktop shell (change `webclient-shell-usability-fixes`, archived 2026-08-06) landed pointer activation through a single delegated bridge on `#action-dock`, plugin-contract keydown routing, the narrative allowlist pipeline, drawer focus retention after ordinary sends, and the minimap lattice. The owner's approved layout-and-interaction design — `.superpowers/brainstorm/1320174-1785662962/content/layout-interaction-design.html`, the source of truth for this change — specifies a specific desktop look and interaction model that the landed shell does not yet match: the mockup palette (near-black page, `#151513`/`#1b1a17`/`#211c18` surfaces, `#514c43` borders, warm paper `#e5e0d5`, deep seal red `#a9322a`, ok green `#709676`, serif narrative), the header (title · location · world time · green connection dot), and the action dock (seal-red frame, guidance line, grid buttons, submenu grid + side detail pane).

Six interaction defects also remain in browser-side code only:

1. `elosern_ui.routeKeyboard` routes Enter/Escape to the drawer only while `drawer.isOpen()`; a direct pointer click into the field never sets that flag, so Enter in the textarea sends nothing unless the drawer was opened with `/` or a free-form dialogue.
2. `.inputsend` is absolutely positioned against a `calc()` width on the field, neither child uses `box-sizing: border-box`, and the textarea still carries a vestigial `form-control` class from a Bootstrap that is no longer loaded — the button overflows the wrapper and misaligns.
3. Exploration submenus (Move, Look, Interact, Wait, target affordances, scripted keywords) have no pointer-accessible way back; Escape works at depth ≤ 1 but an intermediate-depth Escape leaves the dock rendering the deeper menu's rows while the router navigates the parent (a violation of the landed "every dock renders exactly the router's current frame" contract).
4. GoldenLayout renders a tab strip whose titles are the raw `componentName` strings ("header", "narrative", …) — noise that identifies nothing.
5. `#narrative-unread` is a cryptic "未讀 N" pill that also renders as an empty vermilion pill whenever the count is zero.
6. The vermilion accent has never been checked against the approved design source of truth — and the mockup now supersedes it with a deeper seal red.

**Owner decisions recorded (from the design review).** (a) The exploration root keeps all 7 entries (Move, Look, Interact, Character, Quests, Inventory, Wait) even though the mockup draws 6 buttons; the grid therefore has 7 equal-width cells in one row. (b) The back button stays (owner exception — the mockup does not draw it) as the final cell of every exploration submenu. (c) The command input area stays a permanent bottom component (owner exception). (d) Focus follows the "stay where you acted" rule — an input-area send leaves focus in the input area, a dock-button send leaves focus in the button panel — which the current drawer requirement already implements, so no focus-behavior change is made; the mockup's "focus returns to the action dock" sentence applies to the `/`-drawer model this client does not use. (e) Submenus adopt the mockup's grid + side detail pane everywhere (exploration and combat shown in the mockup; services/creation/character adopt the same button visual language).

The project is unreleased; no backward-compatibility layer or stored-layout migration is required. The layout wrapper schema (version 1) is unchanged — `hasHeaders` is part of the *default config*, not the stored wrapper schema.

## Goals / Non-Goals

**Goals:**
- Match the mockup's visual language exactly: palette tokens, header, dock chrome, grid buttons, gauge bars, serif narrative/headings.
- Enter in the drawer textarea sends exactly one command through the single drawer-owned send path, however the field was focused.
- The drawer field/button row is visually coherent at both supported viewports with no overflow or ragged gap.
- Every exploration submenu has a final-cell back affordance for pointer users, and dock cells always match the router frame at every depth.
- The GoldenLayout tab strip disappears; panels are identified by their own content and explicit headings.
- The unread marker is a labeled, actionable control that hides when there is nothing unread.
- Record the seal-red audit: the mockup's `#a9322a` replaces `--elm-vermilion`; every use of the accent maps to an approved role.

**Non-Goals:**
- No change to the `services`, `character`, `combat`, or `creation` docks' navigation models (they keep their own back/cancel patterns; only exploration menus gain the back row).
- No change to the keyboard router core (its `popMenu`/`escape`/`notifyFocus` and the existing `grid`/`gridCols` geometry are sufficient; the defect was in the dock's bookkeeping, and the grid geometry was simply unused).
- No new layout version, no wrapper schema change, no server payload or adapter change.
- No removal of the landed minimap lattice, art renderer, or numeric resource text (the mockup's ASCII map and bars are decorative; the lattice, the real art renderer, and the spec-mandated numeric values stay, restyled).
- No change to the command input area's presence or focus semantics.

## Decisions

### D1 — Drawer-field routing: extend the plugin-contract condition, never bind a second listener

**Decision.** In `routeKeyboard`, replace the single `drawer.isOpen()` gate with `drawer.isOpen() || isDrawerField(event.target)`, where `isDrawerField` matches the drawer's own textarea (`id === "inputfield"`, i.e. a `.inputfieldwrapper` descendant). The existing branches then apply unchanged: Enter without Shift → `drawer.send()`; Escape → `drawer.close(true)`; all other keys typed in the field are claimed (without `preventDefault`) so the plugin handler reports no unhandled keydown; Shift+Enter falls through to a newline. `send()` already keeps the field focused after an ordinary send and releases any borrowed free-form reference, so no send-path change is needed.

**Rationale.** The shell spec ("keyboard-routing-is-menu-first-and-submission-safe" and "the-command-drawer-preserves-ordinary-text-control") requires key events to be dispatched through the plugin `onKeydown` contract, claimed exactly when the router consumed them, with exactly one send implementation owning the field. Binding a keydown listener directly on the textarea would create a second send path and bypass the plugin contract; widening the *routing gate* in the one existing handler keeps a single owner and a single claim point. The check must be specific to the drawer field: the creation dock renders real `<input>` elements whose typing must stay untouched, so a generic `isEditable` match would be wrong.

**Alternative considered.** A focus listener in `goldenlayout.js` that flips `drawerOpen = true` whenever the field gains focus. Rejected: it silently changes the meaning of `drawer.isOpen()` for every consumer (browser tests assert `isOpen()` semantics after `/`), and the field's focus state is already observable at the routing site.

**Capture-phase forms must yield the field.** The exploration dock's custom rest-duration form binds a `document`-level **capture-phase** keydown handler (`_bindRestKeys`, `addEventListener(..., true)`) that `stopPropagation()`s digits, Backspace, Enter, and Escape — it fires before Evennia's document-level bubble-phase plugin dispatch. If that form is open and the player clicks into the drawer field, typed keys and Enter would be swallowed by the rest form and never reach `routeKeyboard`. The capture handler therefore gains a first line that ignores any event whose target lies inside `.inputfieldwrapper` (the drawer field), so the drawer's plugin-contract routing always wins; a regression test covers "rest form open → click drawer → Enter sends".

### D2 — Drawer row layout: flex, not absolute positioning

**Decision.** Make `.inputfieldwrapper` a flex row with `box-sizing: border-box` on the wrapper and both children. The field becomes `flex: 1 1 auto` (its `height: 100%` rule moves to the wrapper's flex alignment so both children stretch to the same height), and the button keeps a fixed `2rem` width as a flex item with `align-self: stretch` — no absolute `right/top/height:100%`, no `calc(100% - 2.25rem)`. Remove the `form-control` class from the textarea (dead Bootstrap styling; the project template deliberately removed Bootstrap). Keep the existing hover/focus states and the `resize: none` rule.

**Rationale.** The current rules fight three CSS facts at once: default `box-sizing: content-box` makes `height: 100%` + 1px borders overflow the wrapper; the field's `calc(100% - 2.25rem)` against a 2rem button leaves a 0.25rem ragged gap plus border overlap; and the button has no bottom-anchoring relationship to the field. A flex row with border-box makes height, width, and borders agree by construction and degrades gracefully at 1280x720 (the drawer is a fixed-height surface; a 2rem button is unchanged at both viewports).

**Alternative considered.** Keep absolute positioning and correct the arithmetic (`calc(100% - 2rem - 2px)` plus `box-sizing: border-box` on both). Rejected: the width math would remain a magic-number pair that drifts the moment either border or button width changes.

**Acceptance.** Rather than eyeballing, a browser test compares the three bounding rectangles at 1280x720 (and 1440x900): the button's right, top, and bottom edges align with the field's within a 1px tolerance, and neither child extends outside the wrapper's rectangle.

### D3 — Exploration back navigation: model-owned back row plus a dock navigation-key stack

**Decision.** Two coordinated changes:

- **Model** (`exploration_menu.js`): every submenu builder — `moveItems`, `lookItems`, `interactItems`, `waitItems`, `targetMenuFor`, `keywordMenuFor` — appends one item `{ key: "back", label: "返回上一層", enabled: true, goBack: true }` as the final cell. `buildMenus`'s `root` stays unchanged (a root back row would be a dead control; Escape at root already emits `escape-root`). A new exported `parentKeyFor(menuKey)` maps `move|look|interact|wait → root`, `target-<identity> → interact`, `keywords-<identity> → target-<identity>`, and anything unknown → `root`.

  **Back-row position (last, not first).** The services dock's confirmation menus already place the negative action last (`confirmMenu` puts 取消 after 確認), so last-row is the established project convention. It also keeps the primary action of every submenu in its existing first cell — 查看房間 stays the first Look cell, exits stay first in Move, the guard stays the first Interact target — so the common keyboard flow (open submenu → Enter) is unchanged and existing journeys keep their arrow counts. The back row is reachable by keyboard through the router's wrap-around (one ArrowUp from the first cell) and by pointer click, while Escape remains the fast path; it exists primarily as the pointer affordance the user reported missing.

- **Dispatch gate** (`elosern_ui.js`): `handleSubmission`'s exploration branch condition must gain `item.goBack`, or a keyboard Enter and a pointer click on the back row would fall through the exploration gate and die silently at the no-`actionId` tail. This is the single wiring point that makes the back row reachable at all, so it ships with the model change and its own test.

- **Dock mechanics** (`exploration_dock.js`): the dock keeps a `_menuStack` (array of menu keys mirroring the router's frame stack) pushed on `openSubmenu`/`openTarget`/`openKeywords`. The `goBack` branch in `handleItem` synchronously pops `_menuStack` (when longer than the root), sets `this._currentMenuKey` from its top, and then calls `keyboard.popMenu()`. No reliance on the router's `menu-closed` event for the pointer path: `popMenu()` emits only a synchronous `focus` notification, which drives the existing `onRouterEvent("focus")` → `_refresh()` render — so the parent's cells render exactly once from the already-correct `_currentMenuKey`; an explicit `_refresh()` is kept only as a fallback when `popMenu()` returns false. For the keyboard Escape path, `onRouterEvent("menu-closed")` pops `_menuStack` **only when its length is greater than one** and re-renders from the new top; the existing depth ≤ 1 services/character teardown is preserved unchanged. The length guard is load-bearing: `services_dock` and `character_dock` push their own frames onto the same router stack (verified: `services_dock.js` lines 102/409/414/434, `character_dock.js` line 118), so Escape from a re-homed service submenu or the character view must never pop exploration bookkeeping — at that moment `_menuStack` is `["root"]`, the pop no-ops, and no exploration cell re-render occurs (the services/character dock owns the action-dock DOM, so `_refresh`'s `.exploration-menu` lookup would no-op anyway; both guards are cheap and both stay). `_menuStack` resets to `["root"]` on `escape-root`, `resetToRoot`, and `_discardLocalState`.

  Regression tests must cover the shared-router cases: Escape from Character, and Escape from a Quests/Inventory service submenu, must not corrupt or re-render exploration cells.

**Rationale.** The back row is a normal row, so it inherits the entire landed pointer path (delegated bridge → `focusItemByKey` → pointer-sourced `confirm` → `handleItem`), the disabled/explanation gate, and the in-flight lock for free. Keeping the parent mapping in the model keeps the DOM-independent module testable in Node (the dock's stack bookkeeping is thin glue). The `_menuStack` exists because the router exposes no "current menu key" getter — the dock's `_currentMenuKey` was previously only correct at depth ≤ 1, which is exactly the reported and pre-existing intermediate-depth mismatch.

**Alternative considered.** Deriving the parent from the router frame each time (`keyboard.depth()` + a stack in the dock rebuilt on demand). Rejected: the router's `currentItem()` returns the focused item, not the frame's menu identity, so the dock must mirror the pushes itself; doing it at push sites is the simplest faithful mirror.

### D4 — Remove the GoldenLayout tab strip

**Decision.** Set `settings.hasHeaders: false` in `DEFAULT_LAYOUT_CONFIG` (`layout_store.js`). Remove the `.lm_header`, `.lm_tab`, `.lm_tab.lm_active`, `.lm_title`, and `.lm_close_tab` rules from `goldenlayout.css`; keep `.lm_content` and `.lm_splitter` (still live). Keep the `header` component (the redesigned custom `.elosern-header` bar, see D7) and the `dimensions.headerHeight` entry (harmless once no header renders, and it keeps `stateChanged`-driven dimension persistence stable). No wrapper-schema change: stored wrappers only carry `layout_version`, `dimensions`, `tabs`, `preferences`; `hasHeaders` is a property of the version-1 *default config*, which is what `buildConfig` clones.

**Rationale.** Verified in the vendored GoldenLayout 1.x source: the stack header is shown only when `settings.hasHeaders === true` (Stack constructor: `show: n.settings.hasHeaders === !0 && e.hasHeaders !== !1`), and `setSize` reserves `headerHeight` only when `this._header.show` is truthy — so `hasHeaders: false` removes the strip without leaving reserved space. No test references `.lm_header`/`.lm_tab`/`.lm_title`; the layout acceptance tests count *components* in the config tree, which is unaffected. The requirement "Layout version 1 SHALL provide required header, narrative, … components" is untouched — components remain, only the tab chrome disappears.

**Alternative considered.** Giving each component a real title (e.g. "敘事", "場景"). Rejected: with `reorderEnabled: false`, `isClosable: false`, and no stacking, tabs are pure noise; a title would also need per-component config changes and would still render a strip that can be resized/dragged accidentally.

### D5 — Unread marker: labeled button inside a polite live region, hidden when empty

**Decision.** In `registerNarrative` (goldenlayout.js), the marker becomes a wrapper `<div class="narrative-unread" role="status" aria-live="polite" aria-atomic="true">` containing a real `<button>` whose label is "↓ N 則新訊息（點擊返回最新）" when N > 0; the wrapper gets `data-count="0"` (or the button is emptied and the wrapper hidden) so no empty pill renders. Clicking the button (and the existing scroll-to-bottom path) clears the count and hides the wrapper. Because hiding the marker while it holds keyboard focus would drop focus into the void, the narrative pane becomes programmatically focusable (`tabindex="-1"` on the narrative root) and keyboard activation moves focus there; pointer activation leaves focus untouched. CSS: button-style surface in the mockup's seal-red accent — border, hover state, `:focus-visible` focus ring, pointer cursor; the sticky positioning and z-index stay; the wrapper is `display: none` at count 0.

**Rationale.** The live region preserves the "new output is announced" property (the previous element was a `role="status"` element too), while the inner button gives the jump action a real accessible control with a self-explanatory name — addressing "user have no idea what's that" without losing the spec's unread-indicator contract. Hidden-at-zero fixes the always-visible empty pill, which reads as a decoration, not a state.

**Alternative considered.** Dropping the live region and keeping a single button. Rejected: the announcement of "new messages arrived" while reading scrollback is the accessibility value of the marker; a wrapper keeps both without nesting interactive semantics inside a live region *directly* (the live region announces the button's label when the count changes).

### D6 — Adopt the mockup palette and audit the seal-red accent

**Decision.** The palette tokens in `elosern.css` move to the mockup's exact families:

| Token | Old | New (mockup) | Role |
|---|---|---|---|
| page / ink | `#171512` | `#0d0d0c` | near-black page |
| narrative panel | `#1f1c18` | `#151513` | primary reading surface |
| status/map panel | `#1f1c18` | `#1b1a17` | raised panels |
| action dock / dock surface | `#1f1c18` | `#211c18` | command surface |
| header bar | `#1f1c18` | `#171715` | header strip |
| border | `#3a342c` | `#514c43` | warm gray-brown borders |
| dim border | — | `#3c3933` | disabled cells |
| art border | — | `#5b574f` | art panel frame |
| paper | `#ece7db` | `#e5e0d5` | warm paper text |
| paper dim | `#9c958a` | `#aaa395` | secondary text |
| cursor | — | `#d4c9b5` | input cursor / prompt |
| **vermilion** | `#e05c3a` | **`#a9322a`** | deep seal red accent |
| hp fill | — | `#b3483e` | HP gauge fill |
| warning red | — | `#b97c73` | modifier warnings (命中 −15) |
| ok green | — | `#709676` | connection-ok indicator |
| art placeholder | — | `#273028 → #73593e` | scene placeholder gradient |
| portrait | — | `#756b61 → #292722` | portrait placeholder gradient |

The focus-ring token becomes a lighter vermilion, tuned during implementation to keep ≥ 3:1 contrast on both the ink surfaces and the `#a9322a` button fill (a value near `#e89a6b` is the starting point). Typography: narrative and headings move to a serif face (Noto Serif TC / PMingLiU stack) per mockup and design doc §5.2; controls keep the legible UI face.

**Audit.** `#a9322a` on `#0d0d0c` measures ≈ 2.9:1 and on `#151513` ≈ 2.8:1 — below the 3:1 small-text threshold, so the deep seal-red token is restricted by role: **fills and borders** (focused button fill, dock frame, portrait frame, current map node, unread marker) and **large/bold text and symbols** (room names, headings, the map diamond, the `▶` prefix). Small seal-red text on dark surfaces is not used; where a small red text need exists, the text-safe tokens apply (`--elm-hp: #b3483e` for the HP fill, `--elm-warn: #b97c73` for small warning text such as "命中 −15"). Seal-red **fills** pair with paper text at ≈ 5.2:1 (passes AA) and always carry a shape/glyph companion (the `▶` focus prefix, the room-name bold weight, the map diamond `◆`). The theme requirement's pairing rule ("focus and status never rely on color alone") is preserved by construction: focus is a fill + `▶` glyph + border, connection is a dot + label text, disabled is dimmer border + dimmer text. The token-role split is enforced by a repository contract test that scans the project CSS and fails if a dark-surface small-text selector uses the deep seal-red token or its raw hex. Every current and new use maps to an approved role: focus (button fill + focus ring), current map position (current node), critical/harmful/combat/disguise warnings, confirm actions, action-result live region, and the unread marker. If a later change needs small seal-red text on dark panels, it must introduce a text-safe lighter token explicitly.

### D7 — Header: title · location · world time · connection dot

**Decision.** `registerHeader` (goldenlayout.js) renders the mockup's bar: game title on the left (letter-spaced bold); on the right, the **current location** label (from `state.panels.status.actor.location.label`, "北境森林" in the mockup; "位置：--" while unsynced), the **world date/time** (existing `state.serverTime` payload: season + day + HH:MM), and the **connection state** as a colored dot + label — ok-green `#709676` "● 已連線" when connected; the disconnected state keeps a dot + border + label pairing (never color alone). The "模式：exploration" label is removed; the mode remains observable through the dock's own content.

**Rationale.** The mockup and design doc §5.1 ("game title, location, world date/time, and connection state") agree; the current header's mode field is neither requested nor self-explanatory. Location comes from the already-synced status panel — no new server payload. The ok-green dot introduces the palette's first semantic "good" color; it is always paired with the text label.

**Alternative considered.** Keeping the mode label next to the location. Rejected: the mockup has no mode field, and the dock already identifies the mode (探索/戰鬥/創建 surfaces).

### D8 — Action dock chrome: seal-red frame, guidance line, grid buttons, submenu grid + detail pane

**Decision.** Dock-wide visual contract (all five docks adopt it; exploration and combat additionally adopt the mockup's split-pane submenu layout):

- **Chrome.** The action dock surface is `#211c18` with a 1px seal-red (`#a9322a`) frame; a guidance line (11px, `#aaa395`) names the shortcuts: "方向鍵選擇・Enter 確認・Esc 返回・/ 開啟指令" (per-surface prefix, e.g. "附近動作" in exploration).
- **Buttons.** Items render as equal-width grid cells (`gap: 7px`, centered text, mockup padding): focused cell = seal-red fill + `▶` glyph prefix; unfocused = `#514c43` border; disabled = `#3c3933` border + `#716d65` text, still focusable for its explanation. The listbox/option composite-widget pattern (single container tab stop, `aria-activedescendant`) is preserved; the grid is visual.
- **Disabled reasons stay programmatically associated.** `DockSurface.renderRows` gains the missing `aria-describedby` wiring: every disabled row gets a stable, text-safe description element (the reason text) referenced by `aria-describedby`, in addition to `aria-disabled` and the（無法使用）suffix. When the dock shows a visible detail pane, the same reason text is mirrored there; at the exploration root — where the mockup draws no detail pane — the description elements remain visually hidden so the association contract holds at every depth.
- **Grid geometry.** Menu models set `grid: true` + `gridCols`: exploration root `7` (a seven-column row; the number of rendered items varies from 5 to 7 because Quests/Inventory are omitted when the services capability is absent), exploration submenus `2`, combat root `5`, combat submenus `2`. The keyboard router's already-tested `menu.grid`/`gridCols` path is exercised for the first time; `gridCols` must equal the CSS `repeat()` count so router geometry and visual cells agree (a mismatch would break WYSIWYG focus). For a 2-column submenu with an odd item count the final cell lands in the left column of the last row (the router's empty-cell guard returns false without moving); the back cell is therefore "the final cell — bottom-left for odd counts" and remains reachable by ArrowUp wrap from the first cell, by `focusItemByKey`, and by pointer click. The full arrow-transition matrix for odd-count grids is covered by Node tests.
- **Space repeat.** The router currently suppresses repeated Enter but not repeated Space; with AREA target grids now rendered, holding Space could flip a candidate repeatedly. The router's `press()` gains the same repeat guard for Space (emit `repeat-suppressed`, return true), with a Node test, and the AREA browser journey asserts one toggle per deliberate press and the final payload.
- **Submenu split (all docks).** The dock body becomes the mockup's `≈1.35fr / 0.9fr` grid: left = the item grid, right = a **detail pane** naming the focused item, its availability/cost (combat skills show "火球術　MP 20"), and the next key action ("Enter → 選擇目標"). The existing combat-detail/exploration-detail/services-detail/creation-detail wiring is kept and restyled; services, creation, and character submenu item lists adopt the same 2-column grid + detail split as exploration and combat (their forms, quantity fields, and confirmations keep their existing structures). At the exploration root the detail pane is absent — the mockup root is hint line + buttons only.
- **Back cell.** The exploration back row is a normal cell in the submenu grid (the final cell) — it inherits the pointer bridge, the disabled gate, and the in-flight lock like any other cell.

**Rationale.** The mockup's interaction model (方向鍵選擇・Enter 確認・Esc 返回) is exactly the landed router; only the *presentation* of items changes. Using the existing grid geometry instead of a new focus model keeps keyboard tests meaningful. The split-pane layout matches both mockups (exploration root, combat skills) and the existing per-dock detail panes. Uniform grid adoption across docks removes the ambiguity between the desktop-shell contract ("submenus render as an item grid beside a detail pane") and the implementation scope.

**Alternative considered.** Rendering items as full-width rows in the new colors (option offered in the design review, rejected by the owner: the mockup's grid look is the requirement).

### D9 — Status gauge bars, panel headings, art placeholder

**Decision.** `renderStatus` (goldenlayout.js) adds the "角色狀態" heading and HP/MP/SP gauge bars: a bar cell per resource with the mockup's fill colors (HP `#b3483e`; MP/SP derive from the palette), rendered as accessible elements whose width reflects current/maximum — numeric text stays alongside ("HP 700/1000" + bar), because the theme requirement mandates numeric resource values. The minimap panel gains the "附近地圖" heading and the `#1b1a17`/`#514c43` panel styling; the landed lattice, legend, and remembered-node list are unchanged. The art panel's truthful placeholder adopts the `#273028 → #73593e` gradient with the scene label bottom-left (mockup), and the contextual portrait overlay keeps its 3:4 card but with the mockup's 2px seal-red frame (`#a9322a`).

**Rationale.** The mockup draws bars, headings, and the art gradients explicitly; the landed behavior (lattice, real art renderer, numeric values) is preserved per the non-goals. Bars are decorative complements to the mandated numbers, not replacements.

### D10 — Focus semantics confirmed unchanged ("stay where you acted")

**Decision.** No change. An ordinary text send from the input area clears the field and keeps focus in the field (current requirement: "remain open, and retain focus"); a dock-button submission keeps focus in the dock (the router never moves focus out of the action dock). This matches the owner's decision ("設計為保留在送出前的地方，方便接續下一個同樣的動作") and is already implemented, so the delta only restates it; the mockup's "送出或取消後，焦點回到動作面板" belongs to the `/`-drawer model this client does not use.

## Risks / Trade-offs

- [The pointer-bridge `event.detail === 1` gate and the back row's push-pop timing] → The back row pops a frame on click; the landed stale-row guard already protects rapid double-activations of navigation rows, and the back row is a navigation row by the same definition — no new race is introduced; the browser journey asserts exactly one menu-level change per click.
- [`hasHeaders: false` could interact with the stock layout-migration/restore paths] → `restoreRequiredComponents` and `extractDimensions` operate on the component tree, not the tab strip; the layout tests (persistence, reset, malformed wrappers) already re-mount the shell after every reload and will be re-run; the new "no tab strip" assertion guards the regression.
- [Grid geometry activation could surface latent router-grid bugs now that a real menu uses it] → The router's grid path is already Node-tested (focus geometry, `focusItemByKey` by row/column); the new grid menus add dedicated Node tests, and the browser journeys exercise arrow navigation across the root row and the 2-column submenus at both viewports.
- [Direct-focus Enter could double-send if the stock Evennia input path ever binds the same field] → The stock webclient input field is a different DOM element (the project replaces the stock `#inputfield`); the drawer remains the only bind on its own textarea, and the plugin-contract claim (`return true`) stops anything below it. The existing "one key press sends exactly one command" browser journey covers it.
- [Row-order change (the new final back cell) could shift arrow-count navigation in existing journeys] → The back cell is appended last, so Enter-on-first-cell journeys are unaffected; the new back journeys are added explicitly, and the Node tests assert the exact item lists including the final back cell.
- [Seal-red small text on dark panels sits below 3:1 contrast] → Restricted to large/bold text and symbols per the audit; the theme requirement's pairing rule keeps shape/border companions on every seal-red element; the browser theme test re-checks the pairing (no color-alone states).
- [The serif narrative face could misalign the server's box/ASCII map art] → The narrative keeps a monospace-first stack for box-drawing glyphs and applies the serif face to prose via the markup pipeline's class rules; the wide-row soft-wrap browser test is re-run to catch regression.

## Migration Plan

None required. The project is unreleased; stored layout wrappers are schema-unchanged (version 1) and, being unknown or malformed, already reset to the approved default. The default config change (`hasHeaders: false`) applies to every fresh mount and to every reset; existing localStorage wrappers from the current version carry no `hasHeaders` field and keep working (the field lives in the cloned default, not the wrapper). The palette is CSS-only and applies on next load. Rollback is a revert of the JS/CSS edits; no data is affected.

## Open Questions

None.
