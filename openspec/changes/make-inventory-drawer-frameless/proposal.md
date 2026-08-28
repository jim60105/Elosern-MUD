## Why

When the bag drawer is opened through the keyboard dock (the exploration root's 背包 row, or the services-root model row), it currently hosts the router's plain 背包 menu frame: its row region (`.dock-menu`, plus the `.dock-detail` pane on focus) re-lists the same committed `services.inventory.rows` that the drawer's own three-section stack already renders. Those hosted rows are all `enabled: false` with no action — a legacy-parity keyboard artifact that the item-grid redesign turned into a visible second copy of the same data. The merged bag requirement already states the drawer's available body IS the three-section stack rendered directly on the drawer body, so the hosting state contradicts the current contract.

## What Changes

- Make the 背包 drawer frameless: both 背包 openers — the exploration root's 背包 row and the services sub-dock's 背包 row — activate a client-local `openDrawer` (the pattern the root 角色 row already uses via `openCharacter`) that opens the drawer while leaving the router's frame stack, breadcrumb, and menu keys unchanged.
- Remove the plain 背包 keyboard menu from both service-menu model copies (drawer-open item shape replaces both root entries; the menu, its row builder, and its export are deleted) and remove the `openServiceSubmenu: "inventory"` row shape from the exploration-menu model. 公會／商店／任務板 frame hosting is unchanged; the navigate-affordance surface enum is `["guild","shop"]` (protocol-validated), so no affordance row can reference the deleted menu.
- Drop the inventory surface from the hosting metadata (`SERVICE_FRAME_TITLES`, `SERVICE_SURFACE_DRAWERS`, and the push-time surface branch), add a defensive frameless exclusion to the drawer-host detection in `AppClient`, and exempt the 背包 drawer from `closeHudDrawer()`'s frame pop and sub-dock teardown so closing the bag always leaves the router and dock exactly as the open found them — every other drawer's close behavior is byte-stable.
- Preserve keyboard/pointer parity: the focusable item tiles and their inspector remain the bag drawer's only row surface (the contract the item-grid redesign established); no new interactive surface is introduced here.
- Remap the managed services-browser 背包 journey from dock-menu hooks onto `inventory-panel__*` hooks and assert no hosted row region and no frame change.
- No OOB schema, presenter, server rule, item-data, or persistence change. The frozen `dock-menu` browser hooks stay valid for the 公會／商店 hosted drawers.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`: new requirement — the bag drawer is opened without a router frame, never hosts a row region, and closing it leaves the router alone.

## Impact

- `web/webclient-app/lib/service_menu.js` / `exploration_menu.js` and their mirrored dependency-free copies under `web/static/webclient/js/elosern/`: new `openDrawer` item shape, both 背包 root rows converted, deleted 背包 menu/row builder/export.
- `web/webclient-app/stores/elosern.js`: `openDrawer` carried through the raw→item projection, activation branch, and removal of the inventory hosting metadata; `web/webclient-app/AppClient.vue`: frameless exclusion in `drawerHostsServiceFrame`.
- Tests: Node model tests (`service_menu.test.js`, `hud_dock_menus.test.js`), focused Vitest store/composition tests, and the managed `web/tests/browser/test_browser_services.py` 背包 journey (CI-owned; managed browser suite is not run locally).
- No migration or compatibility layer is required (unreleased project); no player-facing command changes, so the command docs are untouched.
