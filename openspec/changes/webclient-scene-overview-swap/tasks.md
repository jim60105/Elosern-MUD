## 1. Preconditions

- [ ] 1.1 Confirm C8a (`webclient-scene-overview-component`) is archived and its seams exist:
  - `grep -n "overviewMenu\|verbMenuFor" web/static/webclient/js/elosern/exploration_menu.js` matches both
  - `grep -n "sections" web/static/webclient/js/elosern/keyboard_router.js` matches
  - `web/webclient-app/components/SceneOverview.vue`, `DockVerbPopover.vue`, and `dock-exits.js` exist

  Stop and report if any is missing.

## 2. Store and resolvers

- [ ] 2.1 `web/webclient-app/stores/frame-resolvers.js`: `exploration.root` resolves `ExplorationMenu.overviewMenu(panel, {currentNode, suggestions})` through the existing panel gate and `isolate`, and `exploration.target` resolves `ExplorationMenu.verbMenuFor` (design D1). Update the header comment.
- [ ] 2.2 `web/webclient-app/stores/elosern/frames.js`: delete the exploration-root `NAVIGATION_ITEM_KEYS` filter in the `resolve` hook, drop `"exploration.target"` from the `gridCols = 1` list, and update the `rootDescriptorFor` comment (the dialogue root is the scene overview). Delete the `NAVIGATION_ITEM_KEYS` import if it becomes unused.
- [ ] 2.3 `stores/elosern/frames.js` `settleFrameStack`: add the room-change reset of design D2 (`ctx.lastRoomIdentity`, a reset only at depth > 1 on an identity change, recorded on every settle). Initialize `ctx.lastRoomIdentity = null` where the store context is composed. Add Vitest cases to `web/webclient-app/tests/store/declarative_frames.test.js`:
  - a popover, a wait frame, and a keywords frame each reset to the root when a commit changes `look.room.identity`
  - a same-room commit keeps the frame
  - the first commit after mount never resets
  - an unavailable exploration panel never resets
- [ ] 2.4 `git grep -n "exploration\.move\|exploration\.look\|exploration\.interact" web/webclient-app -- ':!dist' ':!tests'` shows only the resolver table and the `EXPLORATION_SUBMENU_PUSHES` map (C8c deletes both), and no push site.

## 3. Dock chrome and AppClient

- [ ] 3.1 `web/webclient-app/components/ActionDock.vue`, per design D3:
  - the `tabBar` prop
  - the `.action-dock__body` wrapper with the `overlay` slot
  - the `.action-dock__legend` strip (`data-testid="action-dock-description"`, unchanged text and `<kbd>` markup, shown when `mode !== 'creation'`)
  - the header comment rewritten

  `web/webclient-app/components/DockTabBar.vue`: delete the hint span, its comment, and the `.dock-tab-bar__hint` CSS. `web/webclient-app/styles/app-shell.css`: delete the `.dock-tab-bar__hint` rules (lines near 252 and 413).
- [ ] 3.2 `web/webclient-app/AppClient.vue`, per design D4:
  - import `SceneOverview` and `DockVerbPopover`
  - render the overview in the pane host and the popover in `#overlay`
  - pass `:tab-bar` to `ActionDock`
  - exclude `DockMenu` while `overviewShown`
  - bind `:show-detail="showDetail"`
  - delete the interaction workspace markup and classes, and the `portraitGlyph` / `faceObjectPosition` imports if they are unused
- [ ] 3.3 `web/webclient-app/composables/use-dock.js`:
  - add `overviewShown`, `overviewActive`, `overviewMenu`, `overviewFocusKey`
  - delete `interactionOpen`, `interactionTarget`, `interactionChoices`, `onInteractionTarget`, `focusedRowDisabled`, and the `portraitFor` import if it is unused
  - add the design-D5 `dockSource` watch calling `shellRef.value?.restoreDockFocus()`
  - update the header comment

  `web/webclient-app/composables/use-app-client.js`: pass the new members through and drop the deleted ones. `git grep -n "interactionOpen\|interactionTarget\|interactionChoices\|onInteractionTarget\|focusedRowDisabled\|interaction-workspace\|interaction-target" web/webclient-app -- ':!dist'` returns nothing once section 4 is done.
- [ ] 3.4 `web/webclient-app/styles/app-shell.css`: delete every `.interaction-*` rule and the `.dock-pane-host.interaction-workspace*` rules. Add the `.action-dock__legend` spacing if `ActionDock.vue`'s scoped CSS does not cover it.
- [ ] 3.5 Stories: in `web/webclient-app/stories/Action/ActionDock.stories.js`, add an exploration story that renders `SceneOverview` in the default slot (args from `stories/fixtures/scene_overview.js`) and one with `DockVerbPopover` in `#overlay`; the combat story passes `tabBar: true`. `stories/Action/DockTabBar.stories.js` uses combat root items only and drops the hint note. `stories/Core/AppShell.stories.js` drops any tab-root dock args. `pnpm run build-storybook` and `pnpm run showcase-coverage` are green.

## 4. Vitest

- [ ] 4.1 `web/webclient-app/tests/frame-resolvers.test.js`: the `exploration.root` cases assert the overview menu (sections, footer, no navigation keys), and the `exploration.target` cases assert the verb menu (payload order, 查看, back). The `exploration.move/look/interact` cases stay until C8c.
- [ ] 4.2 `web/webclient-app/tests/action/action_dock.test.js`:
  - the legend assertions target `.action-dock__legend` (one instance in exploration, dialogue, and combat; none in creation)
  - the tab-glyph assertions use the combat root
  - new cases: no `DockTabBar` without `tabBar`, and the `overlay` slot rendered inside `.action-dock__body`
- [ ] 4.3 `web/webclient-app/tests/dialogue_dock.test.js` and `tests/dialogue_store.test.js`: replace `.dock-tab-bar__tab` lookups and `tabToRootAndConfirm("move"|"look"|"interact")` with overview chip keys and `focusItemByKey` + `focusConfirm`.
- [ ] 4.4 Re-point these files to overview chips and the `exploration.target` popover wherever they opened the tab root or `exploration.interact`, keeping each file's frameless-drawer and focus assertions:
  - `tests/store/declarative_frames.test.js`, `tests/store/declarative_surfaces.test.js`, `tests/store/frameless_bag.test.js`
  - `tests/store/hud_drawer.test.js`, `tests/store/store_dispatch_focus.test.js`
  - `tests/app_client_frameless_bag.test.js`, `tests/app_client_frameless_shop.test.js` (the shop row is the popover's `service-shop` row)
- [ ] 4.5 Add `web/webclient-app/tests/app_client_scene_overview.test.js`, mounting `AppClient` with a committed exploration panel. Cover:
  - the overview at the root and no tab bar
  - a target chip click opening the popover with the overview inert, and the popover's 查看 dispatching one `explore.look`
  - an outside press closing the popover with the chip focused
  - Escape doing the same
  - a room change closing the popover
  - `#action-dock` holding DOM focus after open and close
  - the combat root still rendering `DockTabBar`

  Run `pnpm test` green.

## 5. Browser

- [ ] 5.1 `web/tests/browser/browser_helpers.py`: add `activate_overview_chip(page, key)` (design D6). `_journey_support.py`: its fixtures keep building panels, and any tab-driven helper is switched to overview keys.
- [ ] 5.2 Re-point every tab-root or workspace use found by `git grep -n "tabToRootAndConfirm\|dock-tab-\(move\|look\|interact\|wait\|suggestions\)\|exploration\.\(interact\|target\)\|interaction-\|move-empty\|interact-empty\|dock-tab-bar__hint" web/tests/browser` in:
  - `test_browser_pointer.py`, `test_vue_foundation.py`
  - `test_browser_exploration_{frame,nav,state,tiles,dialogue,actions}.py`
  - `test_browser_shell_command_line.py`, `test_browser_input_narrative.py`, `test_vue_transport_mount.py`
  - `test_browser_art.py`, `test_browser_shell_narrative.py`, `test_browser_options_surface.py`, `test_browser_layout.py`, `test_browser_actions.py`
  - `test_browser_services_base.py`, `test_browser_local_map_rendering.py`
  - `test_browser_contextual_hud_stage.py`, `test_browser_shell_dock.py` (`.dock-tab-bar__hint` → `.action-dock__legend`), `test_browser_combat_menu.py`

  Keyboard-only acceptance journeys use arrows and Enter only. The grep returns nothing afterwards, except the combat `#dock-tab-flee` selectors.
- [ ] 5.3 `web/tests/browser/test_browser_contextual_hud_dock.py` (design D6):
  - rewrite the badge and glyph test against the combat root (skills badge equal to the combat panel's skill count, combat glyphs, no exploration tab bar)
  - point the breadcrumb test at a popover (`場景 › <name>`)
  - keep the outlet assertions through a direct `pushFrame({source: "exploration.move", params: {}})`
  - add a 1440x900 case asserting that the popover card lies inside `anchor-band-command` and that the command region's box is unchanged from the overview
- [ ] 5.4 Add to `web/tests/browser/test_browser_exploration_nav.py` a keyboard-only journey at 1920x1080:
  - arrows reach an exit chip, and Enter moves
  - the new room's overview is the only frame
  - arrows reach a person chip, Enter opens the popover, and Escape returns with that chip focused
  - opening 等待／休息 and then moving by activating a minimap node returns to the overview

## 6. Specs and traceability

- [ ] 6.1 Sync this change's deltas into the main specs. Edit the `webclient-exploration-menu` Purpose paragraph: replace "the keyboard-first exploration dock that re-homes the service submenus" with "the keyboard-first exploration dock rooted at the scene overview".
- [ ] 6.2 Re-anchor `webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus` to the new `…-and-roots-at-the-scene-overview` ID (read it from `uv run --locked python -m tools.spec_traceability list`) in:
  - `web/tests/browser/test_browser_exploration_actions.py`
  - `test_browser_exploration_nav.py` (three)
  - `test_browser_exploration_state.py`
  - `web/webclient/tests/test_node_suite_evidence.py`

  Re-anchor `webclient-contextual-hud::the-dock-s-root-frame-renders-as-an-icon-tab-bar-with-truthful-count-badges` in `test_browser_contextual_hud_dock.py` to the combat tab-bar ID. Run `uv run --locked python -m tools.spec_traceability check` green.

## 7. Validation

- [ ] 7.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.spec_traceability check`. All green.
- [ ] 7.2 Run the browser shards named in 5.2–5.4, plus `test_browser_combat_menu.py`, `test_browser_combat_panels.py`, `test_browser_combat_scales.py`, and `test_browser_combat_skills.py` (unchanged combat, with the legend strip now visible at 1280x720), through `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.<module> …` (one invocation listing every module). All green.
- [ ] 7.3 Run `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence`, green.
- [ ] 7.4 Check the live client at 1920x1080 with `agent-browser`: the overview wraps inside the command region, the popover sits inside it, and Escape returns. Close the browser afterwards.
- [ ] 7.5 Run `openspec validate webclient-scene-overview-swap --strict` and `git diff --check`. Both clean.
