## Why

Opening the 商店 drawer today pushes the router's `services.shop` frame, and the drawer body then renders that frame's rows through the shared dock row renderer (`dock-menu`, plus the `dock-detail` pane on focus) beside `ShopPanel`. `ShopPanel` already presents every piece of the committed `services.shop` section — open state, every stock row with buy/sell prices and stock levels, every sellable row with the held count, a bounded quantity entry, and the enabled/disabled buy and sell controls with their server-authored reasons — so the hosted rows (`貨架（營業中）` / `販賣`, then the stock/sell row lists and their detail text) are a second, parallel copy of the same data that only adds a navigation layer on top of it. The bag drawer already removed the same kind of duplicate (`make-inventory-drawer-frameless`); the shop drawer should follow that precedent.

## What Changes

- Make the 商店 drawer frameless: the only live 商店 opener — the exploration target frame's `navigate`-kind shop affordance row (`service-shop`) — opens the drawer as a client-local open (`openDrawer: "shop"`, the 背包 precedent) that leaves the router's frame stack, current frame, breadcrumb, menu keys and active sub-dock unchanged, and records no service surface. (The services sub-dock root that also lists 商店 has no push site left and is deleted by `retire-service-keyboard-frames`.)
- Exempt the 商店 drawer from the frame-pop and sub-dock teardown that `closeHudDrawer()` performs for hosted drawers, so closing it (Escape, close control, scrim) pops nothing and returns focus to the opener.
- The 商店 drawer never renders a hosted row region: no `dock-menu` and no `dock-detail` render inside it in any state; `ShopPanel` is the drawer's only body.
- Make `ShopPanel` the complete keyboard surface for trading: the row a keyboard user is working in (focus inside the row) becomes the selected row that carries the `services-quantity` hooks, and the quantity entry is bounded by the row action's own server-advertised `quantity.min`/`quantity.max` (clamped on change; an out-of-bounds value still submits nothing).
- Remap the managed shop browser journeys (buy quantity validation, sell, closed shop, dispatch gates) from router rows + digit-capturing quantity form onto the drawer's native controls driven by the keyboard (Tab / typing / Enter).
- The 公會 / 任務 drawer keeps hosting its guild frames unchanged in this change (handled by `make-quest-drawer-frameless`). The now-unreachable shop keyboard frames (`services.shop` / `services.stock` / `services.sell`), the store quantity form, and the shop hosting metadata stay in place, unreachable, and are deleted by `retire-service-keyboard-frames`.
- Repair the drawer-mutation evidence test, which still targets the deleted `quest_board.test.js`, so the existing "a quantity form keeps the server's bounds" requirement is proven by the new `ShopPanel` clamp (the requirement text itself is unchanged).
- No OOB schema, presenter, server rule, item-data, or persistence change.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`: new requirement — the shop drawer is opened without a router frame, never hosts a row region, and closing it leaves the router alone.
- `webclient-service-menus`: the service browser acceptance requirement no longer claims a drawer-hosted row renderer for the shop (the shop is driven through its frameless drawer's native controls), and the shop reconnect scenario is restated for the drawer-local quantity entry.

## Impact

- `web/static/webclient/js/elosern/exploration_menu.js` (the navigate-affordance row for `surface: "shop"`), the single UMD source the `web/webclient-app/lib/exploration_menu.js` wrapper imports.
- `web/webclient-app/stores/elosern/interaction.js` (the `openDrawer` interception in both submit handlers), `stores/elosern/hud.js` (frameless drawer set), `composables/use-dock.js` (`drawerHostsServiceFrame` frameless exclusion), `components/ShopPanel.vue` (focus-driven selection, bounded quantity).
- Tests: Node model tests (`exploration_menu.test.js`, `hud_dock_menus.test.js`), Vitest store/composition tests (`frameless_bag.test.js`, `app_client_frameless_bag.test.js`, `declarative_surfaces.test.js`, `hud_drawer.test.js`, `app_client_drawers.test.js`, a ShopPanel component test), the evidence module `web/webclient/tests/test_vue_hud_drawer_evidence.py`, and the managed browser files `test_browser_services_shop.py`, `test_browser_services_dispatch.py`, `test_browser_services_base.py` (CI-owned; not run locally).
- Follow-ups: `make-quest-drawer-frameless` (the 任務 drawer, and removal of the drawer hosting render path) and `retire-service-keyboard-frames` (dead-code removal).
