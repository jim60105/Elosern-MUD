## Context

The keyboard menus are built client-side from committed panels (`service_menu.js` / `exploration_menu.js`, mirrored in `web/webclient-app/lib/` and `web/static/webclient/js/elosern/`). 背包 has exactly two openers: the exploration root's 背包 row (`{ openServiceSubmenu: "inventory" }`, gated on `panel.inventory.available`) and the services sub-dock root's 背包 row (`openSubmenu: "inventory"`). Both push the same client-built 背包 frame whose rows (`inventoryItems()`) are built from `services.inventory.rows` with `enabled: false` and `actionId: null`. Because 背包 is in `SERVICE_FRAME_TITLES` and maps through `SERVICE_SURFACE_DRAWERS`, the push records `serviceSurface = "inventory"`, and `AppClient.drawerHostsServiceFrame` renders that frame's rows through `DockMenu` inside the bag drawer — beside the `InventoryPanel` three-section stack that presents the same committed rows. Since the item-grid redesign, that is one drawer showing the same data twice: read-only tiles plus a disabled navigation list. The merged bag requirement in `openspec/specs/webclient-contextual-hud/spec.md` already says the drawer's available body is the three-section stack, and the hosted-frame requirement already legitimizes frameless drawers ("A drawer that presents no router frame SHALL open and close without touching the frame stack at all"). A frameless dock-row opener already exists as precedent: the exploration root's 角色 row carries `openCharacter: true` and its activation calls `openHudDrawer("status")` without touching the router.

## Goals / Non-Goals

**Goals:**

- Opening 背包 from either opener (exploration root or services root) opens the drawer without pushing a menu frame, switching sub-docks, recording a service surface, or changing the breadcrumb.
- The bag drawer body contains only its own stack: no hosted listbox and no detail aside, in every state.
- Closing (Escape, close control, scrim) pops nothing and restores focus to the 背包 row, matching the skill/lore/status drawers.
- 公會／商店 hosting, the quantity form, the abandon confirmation flow, and every frozen `dock-menu`/`dock-detail` hook remain untouched.

**Non-Goals:**

- No change to the tiles, their inspector, rarity/count behavior, or any item-grid contract.
- No change to the `services` payload, protocol, presenter, or server rules.
- No new keyboard surface: the focusable tiles and inspector already provide row reachability; this change only deletes the duplicate list.
- No change to the 公會／商店 drawer hosting model or the quantity-form/confirmation flows.

## Decisions

### Make 背包 a client-local drawer-open row

Add an `openDrawer` field to the menu-item shape (alongside `openSubmenu` / `openServiceSubmenu`): both 背包 rows become `{ key: "inventory", label: "背包", enabled: true, actionId: null, payload: null, openDrawer: "inventory" }` — the exploration root row (in `exploration_menu.js`, still gated on `panel.inventory.available`) and the services root row (in `service_menu.js`). This mirrors the existing frameless 角色 row (`openCharacter: true` → `openHudDrawer("status")`). The store carries `openDrawer` through the raw→item projection (next to `openSubmenu`/`openServiceSubmenu` in `stores/elosern.js`) and, in the activation path, handles `item.openDrawer` before the `openServiceSubmenu`/`openSubmenu` branches by calling the existing `openHudDrawer("inventory")` — which already rejects unknown names. No `router.pushMenu`, no `setActiveSubDock`, no `setServiceSurface`, no publish-side frame bookkeeping changes.

Alternative considered: keep pushing the frame but suppress the hosted listbox when the drawer is 背包. Rejected — with hosting suppressed but the frame current, the dock would regain its copy of the rows (the dock's suppression is keyed to the same host flag), re-creating the duplicate on a different surface; a frame whose rows are all disabled carries no navigation value worth preserving.

### Delete the 背包 menu from both model copies

The `inventory` menu entry, `inventoryItems()` builder, and its export are removed from `web/webclient-app/lib/service_menu.js` and the mirrored static copy; `SURFACE_ORDER` still lists the surface for root-row availability (the 背包 row renders only when the `inventory` section is present, unchanged). A plain 背包 submenu would then be unreachable through both production and Node tests, instead of lingering as dead model state. The legacy shell was retired with the Vue migration, so no live consumer loses the submenu. Targeted navigate-affordance rows also carry `openServiceSubmenu`, but the protocol-validated surface enums (`EXPLORATION_SURFACES`/`CONTEXT_ACTIONS_SURFACES` in `protocol.js`) are `["guild", "shop"]`, so no affordance row can reference the deleted 背包 menu — the two 背包 rows above are the menu's only openers.

### Remove the inventory hosting metadata and harden the host guard

`"背包"` is removed from `SERVICE_FRAME_TITLES`, the `inventory` key from `SERVICE_SURFACE_DRAWERS`, and the dead `subKey === "inventory"` branch from the push-time surface mapping (the `openServiceSubmenu` handler's D2 comment loses its inventory sentence; its surface mapping itself is unchanged because no row emits `openServiceSubmenu: "inventory"` anymore). `drawerHostsServiceFrame` in `AppClient.vue` gains `"inventory"` to its frameless exclusion set beside `skill`/`lore`/`status`: unreachable by construction once no inventory frame can be current, but it makes the frameless guarantee explicit and fails safe if a future surface reintroduces a frame.

### Scope the close teardown so a frameless bag close cannot move the dock

`closeHudDrawer()` has two effects today: it pops one menu level when `options.popFrame && currentFrameIsServiceFrame()`, and — independently — whenever exploration mode has any active sub-dock, it clears the sub-dock and re-homes the root frame. Both effects mutate the router or the dock, so either one would violate the new close contract ("closing the bag drawer SHALL leave the router alone, popping no menu level") — including the store-constructed case where 背包 opens while the services sub-dock is active, and the force-opened case where the bag is opened programmatically while some other service frame is current. The change therefore exempts the `inventory` drawer from both effects outright: closing it returns before the pop and before the sub-dock clear + re-home, leaving depth, current frame, `activeSubDock`, and the breadcrumb trail exactly as they were when the drawer opened. Every other drawer's close path (the pop for hosted closes, the teardown for every sub-dock state) keeps today's code byte-for-byte. (No production path can actually open 背包 from inside a sub-dock — the 背包 row is only rendered on the exploration root, and the standalone services root is not mounted — so the unconditional exemption exists to pin the spec contract and keep store-level tests honest; a service frame left current behind a closed bag is self-healing because the commit-path hosting watcher re-opens that frame's own surface drawer on the next commit.) Focus restoration to the opening row comes unchanged from `HudDrawer`.

The router's frame stack is in-memory closure state in `keyboard_router.js` — there is no persistence and no reconnect restores a stack, so a stale 背包 menu surviving into the new client is not a state this change must migrate; the explicit frameless exclusion in `drawerHostsServiceFrame` is the fail-safe for any residual in-memory value.

The `›` nav chevron (`DockMenu.vue`, condition `openSubmenu || openTarget || openKeywords`) is deliberately NOT extended to `openDrawer`: the chevron means "opens a deeper frame", and frameless drawer rows — the existing 角色 row (`openCharacter`) included — render without it. The production exploration-root 背包 row renders today via `openServiceSubmenu`, which the chevron condition never matched either, so production visuals are unchanged; only the never-mounted services-root model row loses a chevron whose meaning it no longer has.

### Remap the managed journey onto inventory-panel hooks

`test_browser_services.py` drives 背包 through the exploration root's Inventory entry and today evaluates dock-menu state for it. The journey re-asserts on `inventory-panel__*` test ids (sections, tiles), asserts no `[data-testid="dock-menu"]`/`[data-testid="dock-detail"]` exists inside the open bag drawer, and asserts the frame stack/breadcrumb is unchanged around open+close. The `dock-menu` hooks stay for the 商店 flow, so the frozen-contract audit needs no edit.

## Risks / Trade-offs

- [Two model copies drift] → Both copies get the identical item-shape change in the same task, and the Node tests pin the shared logical shape the store consumes.
- [Keyboard users lose a listbox for rows] → The tiles are native focusable buttons with the hover/focus inspector (item-grid contract); the removed list carried no enabled, activatable row, so no capability is lost.
- [Stale focus after close] → `HudDrawer`'s restore-to-opener contract is shared with the frameless drawers; a regression test pins it.
- [Drawer reopened by a surface effect] → Nothing else records `serviceSurface = "inventory"` once the mapping entries are removed; a store test asserts an open bag drawer survives services commits without acquiring a hosted frame.
- [Managed CI is the only place the browser journey runs] → Local validation covers Node + Vitest; the managed file's changes are reviewed statically, per the CI-ownership rule in AGENTS.md.

## Migration Plan

Land after the archived inventory-redesign changes; no data, protocol, or saved-state change. Deploy client-only. Rollback restores the submenu shape and hosting metadata with no conversion. Validate with the Node gate, focused Vitest, Storybook build + showcase coverage (expect no story change; the guard catches regressions), and `tools.spec_traceability check`; the managed services journey runs in CI.
