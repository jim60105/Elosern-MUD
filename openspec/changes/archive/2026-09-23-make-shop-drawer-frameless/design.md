## Context

See proposal.md for motivation. Current wiring (all under `web/`):

- The shop is reached only from an exploration target frame's `navigate` affordance row (`exploration_menu.js`, key `service-shop`, `openServiceSubmenu: "shop"`). `handleExplorationItem` switches the active sub-dock to `services`, calls `setServiceSurface("shop")`, and pushes the `services.shop` descriptor (`stores/elosern/interaction.js`). The services-root model (`service_menu.js` `rootItems`, resolver `services.root`) still lists 商店 but nothing pushes `services.root` any more (the browser base notes "the standalone Services root no longer exists"), so it is not an opener.
- `syncHudDrawer` (`stores/elosern/creation.js`) sees a hosted service frame current with a recorded surface and forces `hudDrawer = "shop"` through `SERVICE_SURFACE_DRAWERS`.
- `AppClient.vue` renders `ShopPanel` in the drawer and, because `drawerHostsServiceFrame` (`composables/use-dock.js`) is true, a second `DockMenu` bound to `dockItems` — the router's current shop/stock/sell frame rows — which produces the `dock-menu` row region and the `dock-detail` pane inside the drawer.
- `closeHudDrawer({ popFrame: true })` (`stores/elosern/hud.js`) pops the hosted frame and discards the quantity form.
- The bag drawer went through exactly this migration in `make-inventory-drawer-frameless`: an `openDrawer` item shape, interception in both submit handlers, the `FRAMELESS_DRAWER_NAMES` close exemption, and the frameless exclusion in `drawerHostsServiceFrame`.
- `HudDrawer` owns every key while it holds trapped focus, so the only way to operate the drawer is through focusable controls inside it; `ShopPanel` already renders native `<input type="number">` quantity entries and `<button>` buy/sell controls per row.

## Goals / Non-Goals

**Goals:**
- The 商店 drawer is frameless: open and close never touch the router, the sub-dock, or the recorded service surface.
- No `dock-menu` / `dock-detail` inside the shop drawer in any state.
- `ShopPanel` alone is a complete keyboard trading surface that keeps the `services-quantity` / `services-quantity-value` hooks meaningful.

**Non-Goals:**
- The 任務 / guild drawer (next change, `make-quest-drawer-frameless`).
- Deleting the now-unreachable shop keyboard frames, the store quantity form, `serviceSurface` bookkeeping, or the hosting metadata (`retire-service-keyboard-frames`). This change only guarantees they are unreachable.
- Any change to the server-side `services` payload, shop rules, or command-line `buy`/`sell` commands.

## Decisions

### D1. Reuse the `openDrawer` item shape instead of a shop-specific flag
The navigate affordance row for `surface === "shop"` becomes `{ key: "service-shop", label, enabled, actionId: null, payload: null, openDrawer: "shop", description: null, disabledReason }` (it keeps its `enabled` / `disabledReason` from the affordance; a disabled navigate row stays focusable and opens nothing). The guild navigate row keeps `openServiceSubmenu: "guild"` until the next change.
The interception in `handleExplorationItem` / `handleServiceItem` generalises from `item.openDrawer === "inventory"` to a single allow-set of frameless drawer names (`inventory`, `shop`) → `openHudDrawer(item.openDrawer)`. The combat menu's `openDrawer: "inventory"` branch in `frames.js` is unaffected.
*Alternative:* keep the push but hide the rows. Rejected: the router would sit on an invisible frame (breadcrumb, Escape depth, and digit row picks would all describe rows the player cannot see), which the pointer-activation invariant forbids.

### D2. Add `shop` to `FRAMELESS_DRAWER_NAMES` and to the `drawerHostsServiceFrame` exclusion
Closing the shop drawer returns before the pop and before the sub-dock re-home, exactly like the bag. The exclusion in `drawerHostsServiceFrame` is defensive: even if some future path left a shop frame current, the drawer renders no hosted rows. The mode-change / epoch / transport-loss teardown in `syncHudDrawer` already closes `shop` and needs no change.

### D3. Leave the hosted-shop machinery in place but unreachable
`SERVICE_SURFACE_DRAWERS.shop`, the `services.shop|stock|sell` resolvers, `openQuantityForm`, and the `quantityForm` prop of `ShopPanel` stay untouched here. Nothing can push a shop frame after D1, so the settle watcher never opens the shop drawer from a frame, and the quantity form never opens. Removing them in the same change would double the diff and entangle this change with the quest drawer's shared machinery; `retire-service-keyboard-frames` removes all of it at once after both drawers are frameless.

### D4. `ShopPanel` selection follows focus; the quantity entry is bounded by the action
- `@focusin` on each stock/sellable row calls the existing `activateRow(row)`, so the row a keyboard user is working in carries `services-quantity` / `services-quantity-value` (today only a pointer click or the store quantity form selects a row).
- The `<input>` `min` binds to `row.buy.quantity.min` / `row.sell.quantity.min` (today hard-coded `1`), `max` keeps binding the action's `quantity.max`, and a `@change` clamp writes the value back into `[min, max]` so the entry can never hold an out-of-bounds value after the user leaves it (this satisfies the existing "A quantity form keeps the server's bounds" scenario, which expects clamping). `buyNow` / `sellNow` keep their bound check as the second line of defence: a value that reaches them without a `change` event (a pointer click on the button while the entry is still focused never skips `change`, but a programmatic or empty value can) submits nothing.
- A stock row and a sellable row for the same `item_key` share one quantity entry today; that is kept.
*Alternative:* a roving-tabindex listbox over the rows. Rejected: it re-creates the navigation model this change removes; native Tab order through the inputs and buttons is already the pattern the bag tiles and the quest drawer use.

### D5. Browser journeys drive native controls with the keyboard
The shop journeys open the drawer through the merchant's navigate row (keyboard, as today), then use a bounded Tab walk to reach the target row's quantity entry (asserting `document.activeElement` by `data-testid` / row container), `Control+A` + typed digits to set the quantity, Tab to the buy/sell button, and Enter. The quantity-bounds journey asserts the out-of-bounds attempt sends nothing (the clamp from D4 lowers the value on `change`, and the test asserts both the clamped display and that only the corrected submit dispatches). The closed-shop journey asserts every buy/sell button in the drawer is `disabled` with its reason text, instead of reading `.dock-menu-item` rows. The "no host-like control" check reads the drawer's buttons/inputs instead of `.dock-menu-item`.

## Risks / Trade-offs

- [The navigate row's key and label change nothing, but its item shape does] → Node model tests pin the new shape for `surface: "shop"` and the unchanged shape for `surface: "guild"`.
- [Clamp-on-change hides the "rejected before sending" behaviour the old journey asserted] → The browser journey asserts both that the displayed value is clamped to the max and that no request was sent before the explicit buy activation with the corrected value; the component test asserts `buyNow` rejects an out-of-bounds value when the clamp has not run.
- [`closeHudDrawer` teardown divergence between shop and guild while the next change is pending] → A Vitest regression keeps the guild (hosted) close path popping exactly one level.
- [Focus restoration after close] → The drawer's focus trap already restores to the opener; a Vitest close-path test covers Escape, close control, and scrim for both openers.
