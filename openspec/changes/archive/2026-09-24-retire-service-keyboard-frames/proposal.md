## Why

After `make-shop-drawer-frameless` and `make-quest-drawer-frameless`, no opener pushes a `services.*` frame and no drawer hosts one. What remains of the keyboard service dock — the `ServiceMenu` model (services root, guild / board / quests / quest-detail / abandon-confirm menus, shop / stock / sell menus, the digit-capturing quantity state), the nine `services.*` frame resolvers, the `services` sub-dock with its submit handler and confirm banner, the store quantity form, and the service-surface hosting bookkeeping (`serviceSurface`, `SERVICE_SURFACE_*`, the settle-time drawer hosting and hosted-pop rules, the hosted branch of `closeHudDrawer`) — is unreachable code. Keeping it leaves contracts that describe behaviour no player can reach (the pointer-activation quantity-form exception, the services resolver family) and tests that exercise only themselves. The project is unreleased, so the dead path is removed rather than kept for compatibility.

## What Changes

- **BREAKING (internal)**: delete the `ServiceMenu` UMD model (`web/static/webclient/js/elosern/service_menu.js`), its ESM wrapper (`web/webclient-app/lib/service_menu.js`), and its Node test (`service_menu.test.js`), removing the file from the test-data lint seed / freeze lists and the data-independence list, and re-pointing the Node-suite evidence test that used it to the services protocol suites.
- Delete the nine `services.*` resolvers (and their helpers) from `stores/frame-resolvers.js`; a `services.*` descriptor becomes an unregistered source.
- Delete the `services` sub-dock: the `openServiceSubmenu` branch of `handleExplorationItem`, the whole `handleServiceItem` handler and its call in the router submit path, the `servicesConfirm` computed and the `.services-confirm` banner in `AppClient.vue`.
- Delete the store quantity form (`quantityForm`, `openQuantityForm`, its key capture in `focusPress`, its reset in `view.js` / `frames.js`, its store export) and `ShopPanel`'s `quantityForm` prop and watch.
- Delete the hosting bookkeeping: `serviceSurface` / `setServiceSurface`, `HOSTED_SERVICE_SOURCES`, `descriptorIsServiceFrame`, `currentFrameIsServiceFrame`, `SERVICE_SURFACE_DRAWERS`, `SERVICE_SURFACE_FOR_SOURCE`, the settle-time hosting block in `syncHudDrawer`, the hosted-drawer pop rule in the frame settle, and the hosted branch of `closeHudDrawer` (every drawer close becomes a frameless close, keeping the status drawer's existing sub-dock clear and root re-home).
- Restate the contracts that still name the removed pieces: the pointer-activation invariant and keyboard-bridge requirement lose the services dock and its quantity form, the pointer-parity requirement names drawer controls instead of a service submenu, the dock legend's digit rule loses the quantity-form precedence, and the frame-resolution resolver table loses its services family. Edit the `webclient-service-menus` and `webclient-frame-resolution` Purpose paragraphs directly in the main specs.
- Delete or re-point every Vitest / Node test that drove the removed code (service frames, quantity form digits, services confirm, hosted pops), keeping equivalent coverage where the behaviour still exists (shop echo through `ShopPanel` dispatch, digit row picks without the quantity precedence).
- No player-visible behaviour change; no OOB schema, presenter, server, or persistence change.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-pointer-activation`: the modal-form exception list and the keyboard-bridge capture list drop the services quantity form; the dock list drops the services dock; pointer parity names a drawer-control service submission.
- `webclient-contextual-hud`: the shortcut-legend digit rule drops the quantity-form precedence.
- `webclient-frame-resolution`: the resolver-table requirement is replaced by one covering only the combat and creation families and stating that no services descriptor is registered.

## Impact

- Deleted: `web/static/webclient/js/elosern/service_menu.js`, `web/webclient-app/lib/service_menu.js`, `web/static/webclient/js/tests/service_menu.test.js`.
- Edited: `web/webclient-app/stores/frame-resolvers.js`, `stores/elosern/{hud,interaction,frames,creation,view}.js`, `stores/elosern.js`, `composables/use-dock.js`, `AppClient.vue`, `components/ShopPanel.vue`; `web/static/webclient/js/tests/hud_dock_menus.test.js`; Vitest files `frame-resolvers.test.js`, `app_client_frameless_bag.test.js`, `store/{frameless_bag,command_echo_surfaces,digit_row_picks,declarative_surfaces,hud_drawer,store_dispatch_focus}.test.js`, `dialogue_store.test.js`, `dialogue_dock.test.js`, `bridge/bridge.test.js` (the `"services"` sub-dock literal used as a generic marker); `web/webclient/tests/test_node_suite_evidence.py`; `tests/test_data_independence_js_webclient.py`; `tools/test_data_lint_seed.json`; `tools/test_data_freeze.json`; traceability annotations in `web/tests/browser/test_browser_combat_menu.py` and `test_browser_creation_reset_draft.py`.
- Depends on `make-quest-drawer-frameless` (which depends on `make-shop-drawer-frameless`).
