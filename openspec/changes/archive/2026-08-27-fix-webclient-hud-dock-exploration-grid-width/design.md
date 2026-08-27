## Context

The H3 webclient HUD redesign aligned the action-dock area with `docs/design/elosern-redesign/index.html`. The exploration move frame renders as the "outlet" pane: one tile per exit, each carrying the direction glyph plus the destination's display name (or the exit's own label when the destination is unknown/disabled).

Current state of the outlet pane:

- `DockMenu.vue` `paneGridStyle` (components/DockMenu.vue:132-140): when a `gridCols` value is passed and the pane kind is `outlet` (or `nav`), the pane element gets an inline `grid-template-columns: repeat(N, minmax(0px, max-content))`.
- The move menu model (`web/static/webclient/js/elosern/exploration_menu.js:644-650) carries `grid: true` and `gridCols: 2`, which the keyboard router uses for row/col geometry.
- The CSS class rule `.dock-menu__outlet` (DockMenu.vue:469-473) already declares `repeat(auto-fill, minmax(150px, 1fr))`, but the inline style from `paneGridStyle` overrides it.
- `.dock-menu__outlet-tile` (DockMenu.vue:474-488) carries a `max-width: 220px` cap, so even inside a wider track the tile does not fill the track.

The design draft's `.outlet` grid is `repeat(auto-fill, minmax(150px, 1fr))` (index.html:324). The user requirement: the outlet must not be limited to two columns; it must fill the available horizontal space. To fully fill the pane when only a few exits exist, the outlet grid uses `repeat(auto-fit, minmax(150px, 1fr))`: `auto-fit` collapses the empty tracks that `auto-fill` would keep, so a 1- or 2-exit frame renders one or two full-width tracks that consume the whole pane.

The keyboard router (`web/static/webclient/js/elosern/keyboard_router.js:63-70, 128-190) derives cell indices from `menu.gridCols`. With a width-adaptive rendered grid, the router cannot know the rendered column count, so the move frame's keyboard model becomes a single-column list (the router already handles `gridCols: null` menus as lists — `itemAt` falls back to `menu.items[row]` when `menu.grid && menu.gridCols > 0` is false).

Constraints:

- The move frame's row region SHALL receive the pane's full available width (existing `webclient-contextual-hud` requirement, "Dock panes render a per-kind vocabulary from backed fields only").
- The submitted `explore.move` payload SHALL be unchanged.
- No backward-compatibility layers (project unreleased, zero users).
- The nav pane keeps its fixed-column content-sized behavior; this change is scoped to the outlet pane only.

## Goals / Non-Goals

**Goals:**

- The exit-outlet grid fills the pane's available horizontal space: column count = `floor(availableWidth / 150px)` (auto-fill), tracks are `1fr`, tiles stretch with their tracks.
- Keyboard navigation of the move frame stays deterministic (single-column list) and consistent with a width-adaptive rendering.
- Existing behavior preserved: glyph + destination-name presentation, focused-tile treatment, disabled-row markers, `explore.move` payload.

**Non-Goals:**

- Changing the nav pane (look/interact/wait) grid geometry.
- Changing the combat panes (skills/targets/scales/confirm) track functions.
- Changing the submitted `explore.move` payload or the exit row model (`exit-*` keys, `direction`, `destination`).
- Adding viewport-width-aware keyboard geometry (the router stays DOM-independent by design).

## Decisions

### D1: The outlet pane emits no inline `grid-template-columns`; the class rule becomes `auto-fit`

`paneGridStyle` in `DockMenu.vue` currently special-cases `outlet` and `nav` with content-sized tracks. Change it so the `outlet` pane returns `{}` (no inline template), and change the `.dock-menu__outlet` class rule from the draft's `repeat(auto-fill, minmax(150px, 1fr))` to `repeat(auto-fit, minmax(150px, 1fr))` so the rendered tiles — not reserved empty tracks — consume the pane's full width even with one or two exits.

Rationale: `auto-fill` reserves as many columns as fit in the available width and keeps empty tracks, so a 2-exit frame in a wide pane would still leave a large blank region — the very symptom being fixed. `auto-fit` collapses those empty tracks: the column count becomes `min(exit_count, max_fitting_columns)`, and the `1fr` tracks stretch to fill the width.

Alternatives considered:

- *Keep the inline `repeat(N, minmax(0, max-content)) and only widen the min*: still a fixed column count — the rendered column count would not track the pane width.
- *Keep the draft's `auto-fill`*: simpler, but leaves blank space for short exit lists; rejected because the requirement is to fill the available horizontal space.
- *Apply `auto-fit` inline on the pane element*: duplicates the class rule; keeping the CSS class rule as the single source of truth avoids drift.

### D2: Move menu `gridCols` becomes `null` (list keyboard geometry)

`exploration_menu.js` `buildMenus` sets `menus.move` to `{ items, focusKey: null, grid: true, gridCols: null, title: "移動" }`. The keyboard router then treats the move frame as a vertical list: Up/Down cycle through the move frame's items — the exit rows in order, followed by the `back` row (the list branch iterates the full `menu.items`, `keyboard_router.js:116-123, 172-188`); Left/Right are no-ops (`keyboard_router.js:134-146`). The `back` row is a navigation cell (the breadcrumb chevron owns the visible close control), so cycling onto it is consistent with the existing back-row contract: activating it pops one level.

Rationale: the rendered column count is width-adaptive, so no fixed count can describe it; a single-column list is the only DOM-independent geometry that cannot disagree with the rendering. The visual layout does NOT drive the keyboard geometry: across a window resize the focus key and the submitted `explore.move` payload stay stable. The `explore.move` payload and the exit row model are untouched.

Alternatives considered:

- *Keep `gridCols: 2`*: deterministic but diverges from the rendering on wide panes (auto-fit could yield 3–8 columns), so arrow keys would move focus in the wrong cells.
- *Width-aware column count*: requires the DOM-independent router to read viewport width — violates its DOM-independence contract.
- *Skip the `back` row in the list cycle*: would require a router change (`filter(i => i.key !== "back")` in the list branch); rejected — the back row is a legitimate navigation item and the router's list branch already handles it.

### D3: Outlet tiles stretch with their tracks (drop the `max-width` cap)

Remove `max-width: 220px` from `.dock-menu__outlet-tile` (DockMenu.vue:474-488), keeping `min-width: 0` and `overflow-wrap: break-word` so long destination names wrap inside the track. The tile then fills the `1fr` track and the row region truly receives the pane's full available width.

Rationale: with the cap, a wide track leaves the tile content-sized in the left part of the track; the requirement "the row region SHALL receive the pane's full available width" is only met when the tile spans its track.

Alternatives considered:

- *Keep the cap*: tiles stay 220px wide and the right part of wide tracks stays empty — the very symptom reported.

### D4: Tests follow the new contract

- `web/webclient-app/tests/action/dock_menu_panes.test.js`: the "outlet/nav panes emit content-sized tracks" test — the outlet case now expects an empty inline `gridTemplateColumns` (the CSS auto-fill rule governs); the "long destination labels wrap" test drops the `max-width: 220px` assertion.
- `web/static/webclient/js/tests/exploration_menu.test.js`: "menu models carry the mockup grid geometry" — `move` now asserts `gridCols === null` (look/interact/wait keep `2`).
- `web/tests/browser/test_browser_exploration.py`: replace `assert_not_stretched` for `.dock-menu__outlet-tile` with a stretched assertion (tile width equals its track: at the 1280x720 viewport the pane is ~1140px, so ~7 columns of ~150px+; tile width ≈ pane_width / column_count), and the ArrowRight no-op assertion for the move frame.
- `web/tests/browser/test_browser_contextual_hud.py`: the outlet-tile presentation checks (glyph, destination name, focused state) are unchanged; only the layout assertions move.

## Risks / Trade-offs

- [Risk] The rendered column count varies with window width (auto-fit collapses tracks for short lists, but many-exit frames still reflow across resizes). → Mitigation: D2 makes the keyboard model a single-column list, so the focus key and the `explore.move` payload are stable across resizes; the visual layout does not drive the keyboard geometry (an accepted interaction trade-off: with many exits, ArrowDown moves to the next item in DOM order, which may be the tile to the right in the rendering).
- [Risk] Dropping the tile's `max-width` cap could let a very long destination name dominate a wide track. → Mitigation: `min-width: 0` + `overflow-wrap: break-word` wraps the bold label inside the track; the browser test `assert_long_label_wraps` covers this.
- [Risk] The `nav` pane keeps the fixed-column content-sized behavior while the outlet is auto-filled — a reader could expect symmetry. → Mitigation: the design draft treats them differently (`.outlet` is auto-fill `1fr`, `.ngrid` is auto-fill `minmax(200px,1fr)` but the nav keyboard geometry keeps a fixed count); the delta specs state the exemption explicitly.
- [Risk] Browser tests are CI-owned; local runs use a single class within the 10-minute budget. → Mitigation: update the assertions in place; run the single focused browser test class locally, and leave the full suite to CI.
- [Trade-off] The move frame's keyboard model is now a list, losing the 2D arrow-key grid for exits. This is acceptable: the exit list is fundamentally a list of destinations, and the 2D grid was only a visual layout detail.

## Migration Plan

The project is unreleased with zero users — no backward compatibility or migration is required. Rollback is a simple revert of the four touched files.

## Open Questions

- None: the design draft already pins the auto-fill rule, and the keyboard-list decision follows directly from D2.
