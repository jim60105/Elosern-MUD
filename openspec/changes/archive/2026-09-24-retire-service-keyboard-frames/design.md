## Context

See proposal.md for motivation. Preconditions after the two earlier changes:

- `exploration_menu.js` emits no `openServiceSubmenu`; the navigate rows and the root `quests` item use `openDrawer`. Nothing pushes `services.root` (already true before either change).
- `FRAMELESS_DRAWER_NAMES` = `inventory`, `party`, `shop`, `quest`; `drawerHostsServiceFrame`, the drawer-body `DockMenu`, and `HudDrawer.bodyClass` are gone.
- Still present but unreachable: `ServiceMenu` (menus + quantity state), `services.*` resolvers, `handleExplorationItem`'s `openServiceSubmenu` branch, `handleServiceItem` (called first in the router submit path in `frames.js`), `activeSubDock === "services"`, `servicesConfirm`, `quantityForm` (+ `focusPress` capture, `view.js` reset, `frames.js` reset, store export, `ShopPanel` prop), `serviceSurface`, `HOSTED_SERVICE_SOURCES`, `descriptorIsServiceFrame` / `currentFrameIsServiceFrame`, `SERVICE_SURFACE_*`, the `syncHudDrawer` hosting block, the settle hosted-drawer pop rule, and the `popFrame && currentFrameIsServiceFrame()` branch of `closeHudDrawer`.
- `"services"` in `stores/elosern/shared.js` is a panel name (the committed panel list), not the sub-dock, and stays.

## Goals / Non-Goals

**Goals:**
- Delete every unreachable piece listed above with no behaviour change for any reachable path.
- Keep the spec set truthful: no requirement names a services dock, a service submenu frame, a services resolver, or a store quantity form.

**Non-Goals:**
- The `character` sub-dock (`activeSubDock === "character"`, set by the Character entry) and the status drawer's close-time sub-dock clear + root re-home stay exactly as they are.
- `webclient-options-surface`'s "never while a re-homed services/character sub-dock is active" clause stays: it remains true (the character sub-dock still exists and the services one can no longer be active), and rewording it is not worth a delta of that large requirement.
- The `services` OOB panel, its protocol validator, presenter, and the seven adapters are untouched.

## Decisions

### D1. Delete `ServiceMenu` outright rather than trimming it
After the resolvers and the quantity form go, no production module imports `ServiceMenu`. The only remaining consumer is a test (`hud_dock_menus.test.js` builds a services model to compare dock shapes); that block is deleted with the module. The Node-suite evidence test that ran `service_menu.test.js` to cover `webclient-service-menus::the-services-panel-is-an-exact-read-only-exploration-mode-panel` is re-pointed at `protocol_services_a.test.js` + `protocol_services_b.test.js`, which validate the panel itself (the menu test never did). The file is also dropped from `tools/test_data_lint_seed.json`, `tools/test_data_freeze.json`, and `tests/test_data_independence_js_webclient.py` (those lists enumerate existing files; a deleted file is removed, which the shrink-only rule allows).
*Alternative:* keep `quantityState` / `validateQuantity` as a shared helper for `ShopPanel`. Rejected: `ShopPanel` bounds its native number entry with `min`/`max` and a clamp; a digit-buffer state machine has no caller.

### D2. `closeHudDrawer` becomes one path
With no hosted drawers, the function keeps two branches only: frameless drawers (`inventory`, `party`, `shop`, `quest`) close without touching the router; the remaining drawers (`skill`, `lore`, `status`) keep today's "clear an active exploration sub-dock and re-home the root" step, which exists for the Character entry's `character` sub-dock. The `popFrame` option loses its meaning; its callers (`use-drawers.js` `onHudDrawerClose`, `use-dock.js` `onNavigateHome`, `openOverlay`) drop the argument.

### D3. Router submit path loses the services handler
`frames.js` calls `handleServiceItem` before `handleExplorationItem`; the call and the handler are deleted. `handleExplorationItem` keeps the `openDrawer`, `openSubmenu`, `openCharacter`, `goBack`, `openTarget`, `openKeywords`, `openRestForm`, `freeform`, and `actionId` branches.

### D4. Test re-pointing keeps the live behaviour covered
- `command_echo_surfaces.test.js`: the stock-frame / quantity-form echo cases become `ShopPanel` buy/sell emits routed through `onShopBuy` / `onShopSell`, asserting the echo still resolves `itemLabel` from the committed panel (the `combat.js` fill path, which stays).
- `digit_row_picks.test.js`: the "quantity form captures digits first" case is deleted; the remaining digit-pick cases are unchanged.
- `frame-resolvers.test.js`: services-family cases are replaced by one "every `services.*` source resolves to the unregistered marker" case.
- `declarative_surfaces.test.js`, `frameless_bag.test.js`, `hud_drawer.test.js`, `app_client_frameless_bag.test.js`: remove the forced-hosting setups (`setServiceSurface`, `services.*` pushes); the frameless assertions from the earlier changes stay.

### D5. Spec edits
Delta specs cover the requirement changes (see `specs/`). The Purpose paragraphs of `webclient-service-menus` ("…the keyboard service dock with bounded quantity forms and an abandon confirmation…") and `webclient-frame-resolution` ("…exploration/services/combat/creation descriptor tables…drawer-follows-stack behavior") are edited directly in the main specs, as the OpenSpec workflow requires for Purpose text.

## Risks / Trade-offs

- [A hidden reachable path still pushes a `services.*` frame] → Before deleting, `grep` for `services\.` push sites and `openServiceSubmenu` / `openSubmenu: "guild|shop|board|quests|stock|sell"` producers; after deleting, the new frame-resolution scenario makes any such push resolve to the unregistered marker, and the Vitest suite asserts it.
- [Traceability: the removed resolver-table ID is still annotated in combat/creation browser tests] → Re-anchor both annotations in the same step as the spec sync; run `tools.spec_traceability check`.
- [Deleting a file listed in the test-data freeze or lint seed breaks `tools.test_data_lint check`] → Remove the entries in the same commit and run the lint gate.
