## Context

See proposal.md (Why). The current state was checked in code, with C1 to C8a assumed archived.

- `stores/frame-resolvers.js`:
  - `exploration.root` resolves `model.menus.root`, the tab root.
  - `exploration.target` resolves `ExplorationMenu.targetMenuFor`.
  - `exploration.keywords`, `exploration.wait`, and `exploration.suggestions` resolve their frames.
  - `exploration.move/look/interact` resolve the three submenus.
- `stores/elosern/frames.js`:
  - The router `resolve` hook filters `NAVIGATION_ITEM_KEYS` out of the exploration root. It forces `gridCols = 1` on `exploration.suggestions/target/keywords` and `gridCols = 3` on `exploration.wait`.
  - `EXPLORATION_SUBMENU_PUSHES` maps `move/look/interact/wait/suggestions`.
  - `settleFrameStack` re-homes the root on a panel-family switch and clears a sub-dock after a cascade pop. Nothing resets the stack when the room changes: a player who moves from the minimap while a frame is open stays in it.
- `stores/elosern/interaction.js` `handleExplorationItem` already handles every intent the overview and popover carry:
  - `openTarget` pushes `exploration.target`.
  - `openSubmenu` handles `wait` and `suggestions`.
  - `openKeywords`, `freeform`, `openDrawer`, `goBack`, and `actionId` behave as before.
  - `focusPress` digits address `menu.items`, except the outlet `back` cell.
- `components/ActionDock.vue`:
  - renders `DockTabBar` whenever `rootItems.length > 0`, and the breadcrumb
  - renders one `.action-dock__pane` (`flex: 1; overflow-y: auto`) holding the default slot
  - the legend is `DockTabBar`'s `.dock-tab-bar__hint` (`data-testid="action-dock-description"`), and `app-shell.css:413` hides it in combat
- `AppClient.vue`'s pane host holds:
  - the waiting screen (`waitOpen`)
  - the interaction workspace (`interactionOpen` = the dock source is `exploration.interact`, `.target`, or `.keywords`), with target buttons and portraits, step headings, and a prompt
  - `DockMenu` (hidden at depth 1 when the pane kind is `plain`)
  - `SkillDetailPane`
- `composables/use-dock.js` owns the workspace computeds and `onInteractionTarget`. `AppShell.vue` exposes `restoreDockFocus()`, which focuses `#action-dock`.
- C8a delivered `overviewMenu`, `verbMenuFor`, the router `sections` geometry, `SceneOverview.vue`, `DockVerbPopover.vue`, and `dock-exits.js`.

## Goals / Non-Goals

**Goals:**
- The overview is the exploration and dialogue root, and the popover is the `exploration.target` frame. Wait, suggestions, and keywords stay child frames.
- The dock returns to the overview whenever the room changes.
- The combat dock is visually and behaviourally unchanged, except that the legend strip now also shows in combat.
- The interaction workspace is gone, and so is every test that pinned the tab root.

**Non-Goals:**
- Deleting the now-unreachable builders, resolvers, push entries, outlet pane, badge branches, and the `focusPress` outlet exception (C8c).
- Digits 1–9 and the legend wording (C8c).
- Any server or protocol change.

## Decisions

### D1. Resolvers swap in place; the old sources stay registered until C8c
- `exploration.root` becomes `() => gate; isolate(ExplorationMenu.overviewMenu(panel, {currentNode, suggestions}))`. The same `currentNode` fallback (`currentNodeFromAffordances`) is used, so exit payloads carry `current_node` as today.
- `exploration.target` becomes `ExplorationMenu.verbMenuFor(found.model, found.target)`.

The resolve hook deletes the exploration-root `NAVIGATION_ITEM_KEYS` filter (the overview never carries those keys) and drops `exploration.target` from the `gridCols = 1` list: `verbMenuFor` returns a list, which is already vertical. `NAVIGATION_ITEM_KEYS` stays in `shared.js` for its other consumers.

*Why keep `exploration.move/look/interact` registered here:* deleting them also deletes their resolver tests, the outlet pane, and the builders. That is a clean, separate retirement, following the `retire-service-keyboard-frames` precedent, and it keeps this change inside one day. After this change nothing pushes them (task 2.4 greps for it).

### D2. Return to the overview on a room change
`settleFrameStack(rs)` reads `rs.panels.exploration?.look?.room?.identity` (the committed room identity) when `dockOnExplorationForm(rs)` holds.
- If it differs from `ctx.lastRoomIdentity`, a previous identity exists, and `router.depth() > 1`, the settle calls `router.resetFrame(EXPLORATION_ROOT_DESCRIPTOR, {openerKey: null})` inside the existing `inStackMutation` window.
- Each settle then records the identity. An unavailable panel records `null` and never resets.
- The reset runs after the access-time settle, so a popover already popped by a departed target is not double-handled.
- An active `character` sub-dock is unaffected: it is not a frame.

*Why the room identity:* it is the panel's own stable room key, it changes exactly on movement, and it needs no narrative parsing. A `local_map.current_node` change would miss rooms without map knowledge.

*Alternative:* reset inside `handleExplorationItem` after dispatching `explore.move`. Rejected: minimap and typed moves bypass the dock, and a reset at dispatch would drop the frame before the move is accepted.

### D3. `ActionDock` chrome
- A new `tabBar` Boolean prop. `AppClient` passes `contextActionsPanel?.kind === 'combat'`. `DockTabBar` renders only when `tabBar && showChrome`.
- The pane becomes `div.action-dock__body` (`position: relative; flex: 1; min-height: 0`), holding `div.action-dock__pane` (`height: 100%; overflow-y: auto`, unchanged padding) and a named `overlay` slot rendered after it. An overlay child positioned `absolute; inset: 0` therefore covers exactly the visible pane box, whatever the pane's scroll position.
- `p.action-dock__legend` (`data-testid="action-dock-description"`) follows the body, rendered when `mode !== 'creation'`. It carries the unchanged legend markup and the `<kbd>` rule, moved from `DockTabBar.vue`.
- `DockTabBar` deletes its hint span and hint CSS. `app-shell.css` deletes `.elosern-root .dock-tab-bar__hint` and the combat `.dock-tab-bar__hint { display: none }` rule.

The legend now also shows in combat. Its spec already said "in exploration, combat, or dialogue mode", and the CSS was the only thing hiding it.

### D4. `AppClient` pane host
The pane-host children become:

```
<section v-if="waitOpen" class="waiting-screen">…unchanged…</section>
<SceneOverview v-if="overviewShown" :menu="overviewMenu" :focused-key="overviewActive ? focus.key : overviewFocusKey"
               :local-map="store.view.localMapModel" :active="overviewActive"
               @focus-change="onDockFocusChange" @activate="onDockActivate" />
<DockMenu v-else-if="!waitOpen && dockItems.length && …" …unchanged… />
<SkillDetailPane …unchanged… />
```

with the popover in the dock's overlay slot:

```
<template #overlay>
  <DockVerbPopover v-if="store.view.dockSource === 'exploration.target'" :menu="store.view.combatMenu"
                   :focused-key="store.view.focus.key" @focus-change="onDockFocusChange"
                   @activate="onDockActivate" @back="onDockBack" />
</template>
```

The new `use-dock.js` computeds are:
- `overviewShown`: the dock source is `exploration.root` or `exploration.target`, and `!store.view.degradedRoot`
- `overviewActive`: the source is `exploration.root`
- `overviewMenu`: `combatMenu` when active, else `rootMenu`
- `overviewFocusKey`: `` `target-${combatMenu.target.identity}` ``, read from the verb menu's own `target` (`verbMenuFor` returns it). It marks which chip opened the popover. The mark is cosmetic, since the overview is inert.

`DockMenu` is excluded while `overviewShown` holds. The degraded root still renders through `DockMenu`'s single marker row.

The interaction workspace markup and the `interaction-workspace` / `interaction-workspace--selected` classes are deleted. `portraitGlyph` and `faceObjectPosition` imports go if they are unused.

`use-dock.js` deletes `interactionOpen`, `interactionTarget`, `interactionChoices`, and `onInteractionTarget`, and its `portraitFor` import if it is unused. `showDetail` keeps `mode === "combat" || dockDepth > 1`, minus the workspace clause that lived in the template. `focusedRowDisabled` is deleted with the `showDetail && (!interactionOpen || focusedRowDisabled)` binding, which becomes `showDetail`.

`onDockActivate` keeps its `explore.wait` rest-form branch for the wait cards.

### D5. DOM focus across the popover
The overview listbox goes `inert` when the popover opens, and the popover unmounts on close. Either would drop DOM focus to `<body>` if it sat inside them.

A `watch(() => store.view.dockSource)` in `use-dock.js` calls `shellRef.value?.restoreDockFocus()` after the DOM flush, when the source enters or leaves `exploration.target` and `document.activeElement` is `<body>` or inside `#action-dock`. `restoreDockFocus` focuses `#action-dock`, the surface's documented focus target. The keyboard bridge routes keys from there exactly as today, and the router's `focusKey` (not DOM focus) decides which chip or row is focused.

This never steals focus from the command line or a drawer.

### D6. Tests re-pointed, not rewritten
Browser helpers gain `activate_overview_chip(page, key)`, which focuses the dock, calls `focusItemByKey(key)`, then presses Enter. Journeys use it instead of tab clicks and `ArrowRight` walks:
- 移動 → exit becomes the `exit-<ref>` chip.
- 查看 → room becomes `look-room`.
- 互動 → target → affordance becomes `target-<id>`, then the popover row.

The keyboard-only acceptance journeys keep pure arrows and Enter. They navigate the overview with ArrowLeft/ArrowRight.

`test_browser_contextual_hud_dock.py`:
- The badge and tab-glyph test is rewritten against the combat root (skills badge, combat glyphs) and re-anchored to the new combat requirement.
- The breadcrumb test opens a popover (crumb `場景 › <name>`).
- The pane-vocabulary test keeps its move-outlet assertions through a direct `pushFrame({source: "exploration.move"})`, since that frame is reachable only that way until C8c deletes it with the test.

### D7. Spec strategy
- The exploration dock requirement's subject changes, so it is REMOVED and ADDED ("…roots at the scene overview"), with six annotations re-anchored.
- The exploration tab-bar requirement is REMOVED, and its surviving combat half is ADDED as its own requirement. One annotation is re-anchored.
- Every other block is MODIFIED with all its scenario titles kept:
  - "Exploration root exposes the G2 hierarchical keys" keeps its title, and its body now describes the overview keys.
  - "Movement stays one action away" now activates an exit chip.
- MODIFIED blocks written on series texts:
  - "The action dock fills the band's command region at a fixed size" (C4a ADDED)
  - "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces" (C4c)
  - "Required desktop surfaces remain visible and usable" and "Keyboard routing is menu-first and submission-safe" (C5)

  No change later than C5 and before this one modifies any of them.
- The `webclient-exploration-menu` Purpose paragraph is edited in the main spec at sync.

## Risks / Trade-offs

- [Browser test churn is the bulk of the day] → D6's single helper keeps each re-point mechanical. Task 5 lists every file from `git grep`, and the gates run per shard.
- [`test_browser_contextual_hud_dock.py`'s move-outlet assertions reach a frame only by a direct push] → Accepted for one change. C8c deletes the outlet and the test together.
- [The legend strip takes about 18px of the 300px band in combat, where it was hidden] → The combat skill frame already scrolls inside the region (C4a), and `test_browser_combat_menu`'s reachability check runs at 1280x720 in task 6.1.
- [A room reset discards an open wait form or a half-read suggestions list when a move lands] → This is intended (design §7: "After any movement settles, the panel returns to the overview"). The rest form's watch closes it when `waitOpen` goes false.
- [The inactive overview's marker is derived from the popover's target, not from the router's root focus] → The two are the same key, because the popover is opened from that chip or by a digit on it. The marker is cosmetic (inert), and the router restores the true opener key on pop (`projectFocus` keeps the root frame's `focusKey`).

## Migration Plan

None. The client is unreleased.

Archive order: **C7 → C8a (`webclient-scene-overview-component`) → C8b (this change) → C8c (`webclient-retire-exploration-submenus`)**. This change is written on C4a, C4c, and C5 texts and must be archived after them. C8c modifies this change's legend requirement again. C9 (`explore-talk-open-action`) depends on this change's popover.
