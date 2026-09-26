## Why

After `webclient-scene-overview-swap` (C8b), the exploration root is the scene overview and nothing pushes the Move, Look, or Interact frames. What remains of the tab-root dock is unreachable code:

- the tab-root builders `rootItems` and `interactItems`, and `parentKeyFor`
- the `move` / `look` / `interact` / `root` entries of `buildMenus`
- the `exploration.move/look/interact` resolvers and push-map entries
- the move frame's exit-outlet pane in `DockMenu`
- the `focusPress` outlet slot exception
- the breadcrumb's focus state for the outlet's non-rendered `back` cell
- the exploration branches of the badge helper

Keeping them leaves contracts no player can reach (the outlet grid rules, the move frame's single-column geometry) and tests that exercise only themselves.

`exploration.navigation` and `ExplorationMenu.navigationItems` are NOT part of that dead path: the top
navigation bar reads them as its sole keyboard-visible entry set (C8b), so the builder and its resolver
source stay while the tab root that also consumed them is deleted.

The design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §7) also binds digits 1–9 to the first nine chips in reading order. Today only 1–4 are bound. This change widens the digit rule for every dock frame and for the dialogue picks, and updates the legend in the same change, as the legend requirement demands. The project is unreleased, so the dead path is deleted, not kept for compatibility.

**Implementation profile:** logic — dead-code deletion and digit-binding widening; tests define done.

## What Changes

- **BREAKING (internal)**: `web/static/webclient/js/elosern/exploration_menu.js`:
  - Deletes `rootItems`, `interactItems`, `parentKeyFor`, `openItem`, and the `root` / `move` / `look` / `interact` menus of `buildMenus`. `buildMenus` keeps `wait` and `suggestions`.
  - `moveItems` and `lookItems` become the overview's plain chip builders: no back row, no `move-empty` placeholder, no `（無法通行）` suffix. `overviewMenu` stops stripping them.
  - The export list and header comment shrink to match.
- `web/webclient-app/stores/frame-resolvers.js` deletes the `exploration.move`, `exploration.look`, and `exploration.interact` sources, so they resolve to the unregistered marker. `stores/elosern/frames.js` `EXPLORATION_SUBMENU_PUSHES` keeps `wait` and `suggestions`.
- `web/webclient-app/components/DockMenu.vue` deletes the outlet pane:
  - `outletRows`, `outletSpanCol`, the outlet grid-style branch, the outlet template, and the outlet `aria-activedescendant` and detail-suppression clauses
  - the `dock-exits.js` import (the helper stays for `SceneOverview`)
- `web/webclient-app/components/dock-panes.js`:
  - `classifyPane` loses the `outlet` kind.
  - `badgeCount` loses its `interact` and `suggestions` branches. Only the combat `skills` badge remains.
- `web/webclient-app/composables/use-dock.js` drops the outlet-only `direction` / `destination` normalization fields.
- `web/webclient-app/components/DockBreadcrumb.vue` deletes the `focusedKey` prop and the `dock-crumb__back--focused` state. Every `back` cell now renders as a row of its frame. `ActionDock.vue` stops passing the prop.
- `web/webclient-app/stores/elosern/interaction.js`:
  - `focusPress` binds digits `1`–`9`, addressing the current frame's first nine entries in rendered (reading) order, and the dialogue picks through `handleCaptionDialoguePick`.
  - The outlet slot exception and the `classifyPane` import are deleted.
- `web/webclient-app/components/ActionDock.vue` legend reads `數字鍵 1–9 · Enter 執行 · Esc 返回`.
- Deleted tests: `web/webclient-app/tests/action/dock_menu_outlet.test.js`, the outlet cases of `tests/components/dock_panes.test.js`, the `rootItems` / `parentKeyFor` / move-look-interact cases of `web/static/webclient/js/tests/exploration_menu.test.js` and `hud_dock_menus.test.js`, and the three resolver-source cases of `tests/frame-resolvers.test.js`, which become one "unregistered" case.
- Rewritten tests:
  - `web/tests/browser/test_browser_exploration_tiles.py`: the outlet-grid tests become overview chip-wrap tests at 1280x720.
  - `test_browser_contextual_hud_dock.py`: the direct-push outlet assertions become overview chip assertions.
  - The digit tests (`tests/store/digit_row_picks.test.js`) cover `5`–`9`.
- Spec deltas:
  - restate the legend, the pane vocabulary (exit chips instead of the outlet), the breadcrumb, the pointer current-frame form list, and the direct-children scenario
  - replace the fixed-column requirement with one that has no outlet exemption and scopes its content-sized track rule to the nav pane (the combat panes are flex forms that never followed it)
- No player-visible change other than digits 5–9 and the legend text. No server, OOB schema, or persistence change. No component is added or deleted.

Out of scope:
- The 交談 affordance's `explore.talk_open` mapping: `explore-talk-open-action` (C9a).
- The dialogue stage's own digit rows: `webclient-dialogue-stage` (C10). This change only widens the existing dialogue-pick digit range.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED, on C8b's text: "The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance". Digits 1–9; no outlet exception.
  - MODIFIED:
    - "Dock panes render a per-kind vocabulary from backed fields only": exit chips replace the move outlet.
    - "A breadcrumb derived from the router names the player's position at depth": no outlet `back` focus carrier.
  - REMOVED "A fixed-column-count dock pane sizes its columns to content, never stretching to fill the panel".
  - ADDED "A fixed-column dock pane sizes its columns to content", scoped to the nav pane.
- `webclient-pointer-activation`: MODIFIED, on C8b's text, "Every action-dock surface renders exactly the keyboard router's current menu frame". The form list loses the exit outlet cell.
- `webclient-desktop-shell`: MODIFIED, on C8b's text, "The action dock's row region and detail panes are direct children of its pane host". The full-width example is no longer the exit outlet.

## Impact

- Edited source:
  - `web/static/webclient/js/elosern/exploration_menu.js`
  - `web/webclient-app/stores/frame-resolvers.js`, `stores/elosern/frames.js`, `stores/elosern/interaction.js`
  - `web/webclient-app/components/DockMenu.vue`, `dock-panes.js`, `DockBreadcrumb.vue`, `ActionDock.vue`
  - `web/webclient-app/composables/use-dock.js`
  - `web/webclient-app/styles/app-shell.css` (the outlet rules, if any)
  - Stories `stories/Action/DockMenu.stories.js`, `DockBreadcrumb.stories.js` (outlet or focused-back args)
- Deleted: `web/webclient-app/tests/action/dock_menu_outlet.test.js`.
- Edited tests:
  - Node: `web/static/webclient/js/tests/exploration_menu.test.js`, `hud_dock_menus.test.js`
  - Vitest: `web/webclient-app/tests/frame-resolvers.test.js`, `tests/components/dock_panes.test.js`, `tests/store/digit_row_picks.test.js`, `tests/action/action_dock.test.js`, `tests/action/dock_menu_panes.test.js`
  - Browser: `web/tests/browser/test_browser_exploration_tiles.py`, `test_browser_contextual_hud_dock.py`, `test_browser_shell_dock.py`, and the outlet mentions in `test_browser_exploration_{dialogue,frame,nav}.py`
  - Browser (the two files the first draft missed): `web/tests/browser/test_browser_exploration_frame.py` and `test_browser_exploration_state.py` mount the retired move frame by a direct push too, so their framework is re-pointed at the scene overview; `browser_helpers.py`'s `push_exploration_frame` helper is deleted with its last caller.
- Spec traceability: `webclient-contextual-hud::a-fixed-column-count-dock-pane-sizes-its-columns-to-content-never-stretching-to-fill-the-panel` (`test_browser_exploration_tiles.py`) re-anchors to `…::a-fixed-column-dock-pane-sizes-its-columns-to-content` for the nav-pane test, and to `webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-roots-at-the-scene-overview` for the chip-wrap test.
- Dependencies: archive order C7 → C8a → C8b (`webclient-scene-overview-swap`) → C8c (this change). The legend, pointer-activation, and direct-children blocks are written on C8b's text.
