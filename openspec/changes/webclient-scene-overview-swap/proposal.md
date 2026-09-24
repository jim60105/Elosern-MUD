## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §1, §7) makes the exploration root one scene overview:

- Exits, people, and objects share one frame.
- A person opens a verb popover inside the panel.
- The panel returns to the overview after every move.

Today the player picks a tab (`移動 / 查看 / 互動 / 等待/休息 / 建議`), and then, for people, walks a two-step "1 選擇互動對象 / 2 選擇對話或行動" workspace. `webclient-scene-overview-component` (C8a) built the model, the router geometry, and the two components without mounting them. This change mounts them and deletes the interaction workspace. That workspace keys on the `exploration.target` frame, which becomes the popover, so it cannot outlive the swap. The project is unreleased, so the old root is replaced, not kept as an option.

## What Changes

- **BREAKING (internal)**: the `exploration.root` resolver in `web/webclient-app/stores/frame-resolvers.js` returns `ExplorationMenu.overviewMenu(...)` (C8a), and the `exploration.target` resolver returns `ExplorationMenu.verbMenuFor(...)`.
  - The root frame has no 移動 / 查看 / 互動 entries.
  - No production path pushes `exploration.move`, `exploration.look`, or `exploration.interact` any more. Those sources stay registered but unreachable until C8c deletes them.
- `web/webclient-app/stores/elosern/frames.js`:
  - The resolve hook drops the exploration-root `NAVIGATION_ITEM_KEYS` filter; the overview carries no such key.
  - `exploration.target` leaves the `gridCols = 1` override list.
  - `settleFrameStack` gains the return-to-overview rule. When the committed `exploration.look.room.identity` differs from the identity seen at the previous settle, and the stack is deeper than the root, the stack resets to the exploration root. This covers dock, minimap, and typed movement alike.
- `web/webclient-app/components/ActionDock.vue`:
  - Renders `DockTabBar` only for the combat root (new `tabBar` prop).
  - Wraps the scrolling pane in a positioned `.action-dock__body` with a new `overlay` slot for the popover.
  - Owns the shortcut legend as one `.action-dock__legend` strip (`data-testid="action-dock-description"`) in every non-creation mode. The wording is unchanged (`數字鍵 1–4 · Enter 執行 · Esc 返回`); C8c changes the digits.
- `web/webclient-app/components/DockTabBar.vue` loses the hint span and its CSS. `styles/app-shell.css` loses `.dock-tab-bar__hint` and the combat hint-hiding rule.
- `web/webclient-app/AppClient.vue`:
  - At `exploration.root`, the pane host renders `SceneOverview` bound to `store.view.combatMenu`.
  - At `exploration.target`, it renders `SceneOverview` inactive over `store.view.rootMenu`, plus `DockVerbPopover` in the dock's `overlay` slot, with `@back` routed to `onDockBack`.
  - `DockMenu` renders for every other frame, as today.
  - Deleted: the interaction workspace markup (`.interaction-targets`, `.interaction-target-grid`, the step headings, `.interaction-prompt`), its `dock-pane-host` classes, and the imports `portraitGlyph` / `faceObjectPosition` once they are unused.
- `web/webclient-app/composables/use-dock.js` deletes `interactionOpen`, `interactionTarget`, `interactionChoices`, and `onInteractionTarget`. `showDetail` no longer suppresses the detail pane for the workspace. `focusedRowDisabled` is deleted if it is left unused.
- The dock element keeps DOM focus across the popover. When the popover opens or closes while focus is inside the dock (or on the body), `restoreDockFocus()` re-focuses `#action-dock`.
- `web/webclient-app/styles/app-shell.css` deletes every `.interaction-*` rule and the `.dock-pane-host.interaction-workspace` rules.
- Browser and Vitest tests that walked the tab root, clicked `#dock-tab-{move,look,interact,wait,suggestions}`, or used `onInteractionTarget` are re-pointed to overview chips and the popover. Tests that read `.dock-tab-bar__hint` read `.action-dock__legend`.
- Spec deltas restate the exploration dock, the combat tab bar, the legend's placement, the command region's chrome, the keyboard root, the desktop-surface text, the pointer current-frame rule, the direct-children rule, the dialogue-mode dock, and the suggestions entry for the overview.
- No OOB schema, presenter, server, or persistence change. No component is added or deleted: C8a added the two components, and `DockTabBar` stays for combat.

Out of scope:
- Deleting the unreachable `moveItems` / `lookItems` / `interactItems` / `rootItems` builders, the `exploration.move/look/interact` resolvers and push entries, the move outlet pane, and the exploration badge branches; digits 1–9 and the legend wording: `webclient-retire-exploration-submenus` (C8c).
- 交談 opening the dialogue stage (`explore.talk_open`): `explore-talk-open-action` (C9). Here 交談 keeps today's scripted-keyword frame and freeform borrow.
- The dialogue-mode dock collapse: `webclient-dialogue-stage` (C10).
- Combat: its root and choice tree are unchanged.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-exploration-menu`:
  - REMOVED "The exploration dock is keyboard-first and re-homes the service submenus" (C4a's text).
  - ADDED "The exploration dock is keyboard-first and roots at the scene overview".
- `webclient-contextual-hud`:
  - REMOVED "The dock's root frame renders as an icon tab bar with truthful count badges".
  - ADDED "The combat dock's root frame renders as an icon tab bar with a truthful skills badge".
  - MODIFIED:
    - "The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance": the legend is the dock's own strip, and the digits address chips.
    - "The action dock fills the band's command region at a fixed size", on C4a's text: the chrome is the combat tab bar or none, plus the legend; the popover overlays the region.
    - "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces", on C4c's text: the fixed-band scenario walks the overview and the popover.
    - "The dock keeps its regular exploration form in dialogue mode": the scene overview.
- `webclient-desktop-shell`, both on C5's text:
  - MODIFIED "Required desktop surfaces remain visible and usable".
  - MODIFIED "Keyboard routing is menu-first and submission-safe": the overview is the exploration keyboard root.
  - MODIFIED "The action dock's row region and detail panes are direct children of its pane host": the overview and popover exemption.
- `webclient-pointer-activation`: MODIFIED "Every action-dock surface renders exactly the keyboard router's current menu frame": the chip and verb-row forms, and the inert overview under the popover.
- `webclient-options-surface`: MODIFIED "The exploration dock renders the suggestions section from the validated v5 panel": it is reached from the footer chip `建議 (N)`.
- `webclient-context-actions-suggestions`: MODIFIED "The dock suggestion pane is the single suggestion surface": the footer chip names the card count.

## Impact

- Edited source:
  - `web/webclient-app/stores/frame-resolvers.js`, `stores/elosern/frames.js`
  - `web/webclient-app/components/ActionDock.vue`, `DockTabBar.vue`
  - `web/webclient-app/AppClient.vue`, `composables/use-dock.js`, `composables/use-app-client.js` (drops the deleted members)
  - `web/webclient-app/styles/app-shell.css`
  - Stories `stories/Action/ActionDock.stories.js`, `DockTabBar.stories.js`, `stories/Core/AppShell.stories.js`
- Vitest:
  - `tests/frame-resolvers.test.js`, `tests/action/action_dock.test.js`, `tests/dialogue_dock.test.js`, `tests/dialogue_store.test.js`
  - `tests/app_client_frameless_bag.test.js`, `tests/app_client_frameless_shop.test.js`
  - `tests/store/{declarative_frames,declarative_surfaces,frameless_bag,hud_drawer,store_dispatch_focus}.test.js`
- Browser:
  - `web/tests/browser/test_browser_pointer.py`, `test_vue_foundation.py`
  - `test_browser_exploration_{frame,nav,state,tiles,dialogue,actions}.py`
  - `test_browser_shell_command_line.py`, `test_browser_input_narrative.py`, `test_browser_contextual_hud_{dock,stage}.py`, `test_vue_transport_mount.py`
  - `test_browser_art.py`, `test_browser_shell_narrative.py`, `test_browser_options_surface.py`, `test_browser_layout.py`, `test_browser_actions.py`
  - `test_browser_services_base.py`, `test_browser_local_map_rendering.py`, `test_browser_shell_dock.py`
  - `_journey_support.py`, `browser_helpers.py`
- Node evidence: `web/webclient/tests/test_node_suite_evidence.py` (annotation re-anchor).
- Spec traceability:
  - `webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus` re-anchors to `…-and-roots-at-the-scene-overview` in `test_browser_exploration_actions.py`, `test_browser_exploration_nav.py` (three), `test_browser_exploration_state.py`, and `test_node_suite_evidence.py`.
  - `webclient-contextual-hud::the-dock-s-root-frame-renders-as-an-icon-tab-bar-with-truthful-count-badges` re-anchors to `…::the-combat-dock-s-root-frame-renders-as-an-icon-tab-bar-with-a-truthful-skills-badge` in `test_browser_contextual_hud_dock.py`. The test is rewritten against the combat root.
  - The `webclient-exploration-menu` Purpose paragraph ("the keyboard-first exploration dock that re-homes the service submenus") is edited in the main spec at sync.
- Dependencies:
  - Archive order: C7 → C8a (`webclient-scene-overview-component`) → C8b (this change) → C8c (`webclient-retire-exploration-submenus`).
  - Written on these earlier series texts:
    - C4a (the exploration dock, the command region)
    - C4c (the stage requirement)
    - C5 (both desktop-shell requirements)
  - C9 (`explore-talk-open-action`) changes the popover's 交談 row and depends on this change.
  - The hot-spot files are `AppClient.vue` and `app-shell.css`, so the series runs these changes sequentially.
