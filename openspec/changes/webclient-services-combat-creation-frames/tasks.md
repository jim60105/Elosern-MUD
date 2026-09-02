# Tasks — webclient-services-combat-creation-frames

## 1. Resolver table completion

- [ ] 1.1 Add services resolvers to `web/webclient-app/stores/frame-resolvers.js` (`services.root|guild|board|quests|quest-detail{questIndex}|shop|stock|sell|confirm{questIndex}`) bound to `ServiceMenu.buildMenus`/`questMenuFor`/`confirmMenu`; out-of-range `questIndex` → unresolvable marker
- [ ] 1.2 Add combat resolvers (`combat.root|categories|category|group|skill|target|forfeit`) bound to `CombatMenu.buildMenus`/`openCategory`/`openGroup`/`openSkill`/`openSkillTargets`, with selection preservation through the unchanged `rebuildForPanel` seam as the declared model-state exception; Vitest pins each step's resolved menu to the pre-migration builder output and pins repeat-resolution idempotency
- [ ] 1.3 Add creation resolvers (`creation.root|presets|form{view}|confirm{kind, presetKey?}`) bound to `CreationMenu.buildMenus` and the committed panel's confirm content; form markers resolve to the same empty marker menu

## 2. Router final form (same commit as Node gate)

- [ ] 2.1 Delete the transitional legacy `{menu, focusRow, focusCol}` shape from `web/static/webclient/js/elosern/keyboard_router.js`; frames are `{descriptor, focusKey}` only; unknown frame shapes and empty-stack reads throw programmer errors; update `keyboard_router.test.js`, `ui_contract.test.js`, `hud_dock_menus.test.js`

## 3. Store cutover and deletion sweep

- [ ] 3.1 Convert services push sites (root/guild/board/quests/quest-detail/abandon-confirm/shop/stock/sell) to descriptors; the `SERVICE_SURFACE_DRAWERS` hosting watcher drives drawer open/close from the stack: a pop removing the hosted surface's frame closes that drawer and discards its selection/quantity/confirmation state through the existing cleanup; a descendant pop leaves the drawer open; drawer close pops exactly one level
- [ ] 3.2 Convert the combat chain (skills tab, category/group collapse rules, `openCombatSkill`, scale→target, forfeit) and creation sites (presets, custom/concept form markers, confirm frames incl. the `creation.confirmItems` copy) to descriptors
- [ ] 3.3 Delete `rehomeFrame`, `dockRawByKey`, and the wrapped empty-stack `router.reset` fuse; teardown posts the one-frame declarative root stack for all three modes; `view.combatMenu`/`view.rootMenu`/`view.dockTrail` derive from the stack with unchanged shapes
- [ ] 3.4 Audit `DockMenu.vue`, `ActionDock.vue`, `DockBreadcrumb.vue`, `AppClient.vue` drawer plumbing; change bindings only where a source shifted

## 4. Vitest + fixtures

- [ ] 4.1 Store-level Vitest: hosted-frame pop closes its drawer and discards drawer-local state; descendant pop keeps the drawer; drawer close pops exactly one; combat step frames refresh by resolution with selection preserved; creation confirm text follows the committed panel; teardown to each mode's root descriptor; empty-stack read throws
- [ ] 4.2 Update `stories/fixtures.js` and affected stories to declarative-only frames; `npm test`, `npm run build-storybook`, `npm run showcase-coverage` green

## 5. Browser verification and traceability

- [ ] 5.1 Browser methods (one-class budget per file): services surface freshness after a committed `ui_update`; quest drawer closes with state discarded on quest disappearance; combat skill frame reflects a panel replacement mid-fight with focus key tracked; creation confirm shows refreshed server-authored text. Annotate covering methods with `covers_requirement` after the delta syncs at archive time; `tools.spec_traceability check` green

## 6. Gates

- [ ] 6.1 `node --test web/static/webclient/js/tests/*.test.js`, `npm test`, `tools.spec_traceability check`, `git diff --check` clean; the combat-menu, service-menus, and character-creation-ui suites run untouched as oracles
