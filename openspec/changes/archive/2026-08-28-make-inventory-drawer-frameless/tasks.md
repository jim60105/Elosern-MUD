## 1. Menu models (both mirrored copies)

- [x] 1.1 In `web/webclient-app/lib/service_menu.js` + `web/webclient-app/lib/exploration_menu.js` and their mirrored dependency-free copies under `web/static/webclient/js/elosern/`: add the `openDrawer` menu-item shape (`{ key, label, enabled: true, actionId: null, payload: null, openDrawer }`); convert the exploration-root 背包 row (`openServiceSubmenu: "inventory"` → `openDrawer: "inventory"`, availability gate unchanged) and the services-root 背包 row (`openSubmenu: "inventory"` → `openDrawer: "inventory"`); delete the 背包 menu entry, its `inventoryItems()` row builder, and its export. Keep `SURFACE_ORDER` availability and the 公會／商店 menus byte-stable.

- [x] 1.2 Update the dependency-free Node tests (`web/static/webclient/js/tests/service_menu.test.js`, `hud_dock_menus.test.js`): both 背包 rows carry `openDrawer` (not `openSubmenu`/`openServiceSubmenu`), no 背包 menu exists in the built model, and guild/shop menus plus quantity/confirmation state are unchanged. Run `node --test web/static/webclient/js/tests/*.test.js` green.

## 2. Store and shell wiring

- [x] 2.1 In `web/webclient-app/stores/elosern.js`, carry `openDrawer` through the raw→item projection beside `openSubmenu`/`openServiceSubmenu`, and in the dock-activation path handle `item.openDrawer === "inventory"` before the `openServiceSubmenu`/`openSubmenu` branches by calling `openHudDrawer("inventory")` only — no `setActiveSubDock`, no `router.pushMenu`, no `setServiceSurface` (mirrors the existing frameless `openCharacter` → `openHudDrawer("status")` precedent).

- [x] 2.2 Remove the inventory hosting metadata: drop `"背包"` from `SERVICE_FRAME_TITLES`, drop the `inventory` key from `SERVICE_SURFACE_DRAWERS` (update its D2 comment and the `openServiceSubmenu` handler's inventory sentence), and delete the dead `subKey === "inventory"` push-time branch. Add `"inventory"` to the frameless exclusion set in `drawerHostsServiceFrame` in `web/webclient-app/AppClient.vue`.

- [x] 2.3 Exempt the frameless `inventory` drawer from BOTH `closeHudDrawer()` effects: closing it returns before the pop-on-hosted-close and before the clear-sub-dock + `rehomeFrame()` step, so depth, current frame, `activeSubDock`, and the breadcrumb trail are exactly as the open found them — in any drawer state, including while some other service frame is current. Every other drawer's close path keeps today's code byte-for-byte. Do not extend the `›` nav-chevron condition to `openDrawer` (frameless rows follow the chevronless 角色 precedent).

## 3. Tests with the behavior

- [x] 3.1 Vitest store tests: activating either 背包 row (exploration root and services root) opens the bag drawer with frame stack, active sub-dock, depth, and breadcrumb unchanged; a services-panel commit while the bag drawer is open never records a hosted surface; 公會／商店 activation still pushes and hosts as before (regression).

- [x] 3.2 Vitest close-path test for the new contract, covering all three close routes named in the spec — Escape, the close control, and scrim activation — and both openers: each pops nothing, restores focus to the opening row, and leaves `activeSubDock` / depth / current frame / breadcrumb exactly as before the open.

- [x] 3.3 Vitest regression test that the scoped teardown in task 2.3 does not regress the other drawers: closing the 公會／商店 (hosted) and 技能／百科／狀態 (frameless) drawers keeps their current sub-dock / re-home behavior while a service frame is current.

- [x] 3.4 Vitest composition test: with the bag drawer open after hosted-style navigation, no `[data-testid="dock-menu"]` or `[data-testid="dock-detail"]` element renders inside the drawer body, while the 商店 drawer still hosts its frame's rows (regression); assert the 背包 dock row carries no `›` nav chevron (matches the 角色 precedent).

- [x] 3.5 Managed browser journeys: first sync the delta requirement into `openspec/specs/webclient-contextual-hud/spec.md` (the traceability rule: an in-progress change's requirement enters the index once synced, and the owning change carries the tests), then annotate with the canonical ID from `uv run --locked python -m tools.spec_traceability list`. In `web/tests/browser/test_browser_services.py`, remap the 背包 journey onto `inventory-panel__*` hooks (committed-row tiles and the section stack present), assert no dock-menu/dock-detail inside the open bag drawer, an unchanged frame stack around open+close, and no dispatched action; `web/tests/browser/test_browser_inventory_grid.py` carries the keyboard-reachability substance (Tab traversal reaches every committed tile with the shared inspector following focus) and shares the annotation. Do not run the managed browser suite locally (CI-owned).

## 4. Validation

- [x] 4.1 Run the Node gate, the focused Vitest suites, `npm run build` (production bundle), `npm run build-storybook` and `npm run showcase-coverage` (no story change expected; the guard must stay green), and `uv run --locked python -m tools.spec_traceability check`.

- [x] 4.2 Run `openspec validate make-inventory-drawer-frameless --strict` and confirm `git diff --check` is clean.
