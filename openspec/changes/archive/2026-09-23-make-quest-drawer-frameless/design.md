## Context

See proposal.md for motivation. This change assumes `make-shop-drawer-frameless` is applied: the shop navigate row is `openDrawer: "shop"`, `interaction.js` has a frameless allow-set (`inventory`, `shop`), `FRAMELESS_DRAWER_NAMES` holds `inventory`, `party`, `shop`, and `drawerHostsServiceFrame` excludes shop.

Remaining quest-drawer wiring (all under `web/`):

- Top navigation: `DesktopNavigation.vue` emits `navigate("quests")` → `use-dock.js` `onTabClick` → `store.tabToRootAndConfirm("quests")`, which pops to depth 1 and submits the exploration root's `quests` item (`exploration_menu.js` `rootItems`, `openServiceSubmenu: "quests"`; hidden from the dock by `NAVIGATION_ITEM_KEYS`, shown in the top navigation). `handleExplorationItem` switches the sub-dock to `services`, records surface `guild`, and pushes `services.quests`.
- Guild clerk: the target frame's `navigate` row `service-guild` (`openServiceSubmenu: "guild"`) takes the same branch and pushes `services.guild`.
- `syncHudDrawer` maps the hosted source to `quest` through `SERVICE_SURFACE_DRAWERS`; `AppClient.vue` then renders `QuestLog` + `GuildCounter` inside `.quest-drawer` and, because `drawerHostsServiceFrame` is true, the drawer-body `DockMenu` with the `hud-drawer__body--dock` flex layout.
- `QuestLog` already emits `quest_track`, `quest_abandon` (behind its own `quest-log__abandon-confirm` step), `quest_turnin`; `GuildCounter` emits `quest_register`, `quest_accept`, `exam_start`. Every one is a native `<button>` wired to `onQuestAction` → the single dispatch entry.
- `tabToRootAndConfirm` already handles frameless navigation items (the 背包 top-nav entry is `openDrawer: "inventory"` today).

## Goals / Non-Goals

**Goals:**
- The 任務 drawer is frameless for both openers; its close pops nothing.
- The drawer hosting render path is deleted outright (the user-visible ask: no `dock-menu` / `dock-detail` in any drawer).
- Guild/quest browser journeys run on the drawer's own controls.

**Non-Goals:**
- Deleting the now-unreachable `openServiceSubmenu` branch, the services sub-dock, the guild/shop resolvers and menu builders, the quantity form, `serviceSurface`, `SERVICE_SURFACE_*`, the settle-time hosting block, and the hosted branch of `closeHudDrawer` — all left to `retire-service-keyboard-frames`, which also restates `webclient-frame-resolution`'s services-family resolver table and `webclient-pointer-activation`'s quantity-form exception.
- Any change to `QuestLog` / `GuildCounter` behaviour or markup (they already carry every action).

## Decisions

### D1. Both quest openers use `openDrawer: "quest"`
The root `quests` item becomes `{ key: "quests", label: "任務", enabled: true, actionId: null, payload: null, openDrawer: "quest" }` (the availability gate on `panel.quests.available` is unchanged), and the navigate row for `surface === "guild"` becomes `openDrawer: "quest"` with its key, label fallback, `enabled`, and `disabledReason` kept. After this, the navigate branch emits `openDrawer` for both surfaces, so it maps `{ guild: "quest", shop: "shop" }` in one place. `quest` joins the frameless allow-set in `interaction.js`.
The top-navigation path keeps its existing pop-to-root: that is the top navigation's contract for every entry (it also applies to 背包 today), not something the drawer does; the spec states it explicitly so the "no push" assertion is measured after the pop.

### D2. `quest` joins `FRAMELESS_DRAWER_NAMES`; delete `drawerHostsServiceFrame`
With `quest` frameless, `drawerHostsServiceFrame` can only ever be false, so it is deleted rather than extended, together with every consumer:
- `AppClient.vue`: the drawer-body `<DockMenu v-if="drawerHostsServiceFrame" …>` block and its comment; the `:body-class` binding on `<HudDrawer>`; the `&& !drawerHostsServiceFrame` clause on the dock's own `DockMenu`; the `.hud-drawer__body--dock` rules and comment; the `.quest-drawer` comment's reference to the `--dock` body.
- `HudDrawer.vue`: the `bodyClass` prop and its class binding (its only caller was the removed binding).
- `use-dock.js`: the computed and its return entry.
After `closeHudDrawer` routes `quest`/`shop`/`inventory`/`party` through the frameless early return, its hosted branch is reachable only for `skill` / `lore` / `status`, which never host a frame (the `popFrame && currentFrameIsServiceFrame()` guard is false for them) — left byte-stable here and simplified in the retire change.
*Alternative:* keep `drawerHostsServiceFrame` as a defensive always-false guard. Rejected: the defensive value came from a hosting path that still existed; once no opener can push a service frame, dead render code only misleads.

### D3. The settle-time hosting block stays but can no longer fire
`syncHudDrawer` opens a drawer only when a hosted service descriptor is current *and* a surface is recorded. After D1 nothing records a surface or pushes a service frame, so the block is inert. Tests that forced hosting (`pushFrame({source: "services.*"})` plus `setServiceSurface`) are rewritten to assert the frameless contract instead; the block itself is deleted in the retire change so this change stays reviewable.

### D4. Browser journeys use the drawer's controls; frame-resolution coverage moves off the services family
The exploration-menu requirement names ("…re-homes the service submenus", "Exploration browser acceptance…") are kept and their bodies restated, because six test annotations anchor to the first one; the restated text says the services are re-homed into drawers.
- `test_browser_services_guild.py`: register, board accept, abandon confirmation, turn-in, exam, and the 1280x720 visibility journey open the quest drawer through `_open_surface(page, "guild")` (still the clerk's navigate row) and reach `guild-counter__register`, `guild-counter__accept`, `guild-counter__exam`, `quest-log__abandon` → `quest-log__abandon-confirm-yes|no`, `quest-log__turnin` with the bounded Tab helper from the shop change, then Enter. Each journey asserts zero `dock-menu` / `dock-detail` in the drawer.
- `test_board_frame_refreshes_on_committed_update` becomes "the guild counter's board re-renders on a committed update" (same fixture, asserting `guild-counter__*` rows) and drops its `webclient-frame-resolution` resolver-table annotation — that requirement stays covered by the combat and creation browser journeys that already carry it.
- `test_quest_drawer_closes_with_the_hosted_frame` is deleted with the removed requirement; its "quest vanishes while the drawer is open" fixture becomes an assertion that the quest book drops the row and the drawer stays open.
- `test_browser_services_quest_drawer.py`: the direct-child `.dock-menu` layout assertion is replaced by "no `dock-menu` / `dock-detail` inside the drawer".
- `test_browser_exploration_nav.py`: the "Escape from Quests" journey asserts the frameless contract (no sub-dock, depth 1, Escape closes the drawer only).
- `web/webclient/tests/test_vue_hud_drawer_evidence.py`: the hosting evidence test is re-anchored to the new contextual-HUD requirement ID and its Vitest marker text updated to the frameless assertion.

## Risks / Trade-offs

- [The top-nav 任務 entry used to land the dock on a services sub-dock; now the dock stays on the exploration root] → Intended: the drawer is the surface; the dock keeps its exploration frame. A Vitest test asserts `activeSubDock` stays `null`.
- [Traceability gate breaks when a requirement is removed while tests still reference it] → Tasks sync specs first, then remove/re-anchor every `covers_requirement` / evidence reference in the same step, and run `tools.spec_traceability check`.
- [Keyboard-only guild journeys get longer Tab walks] → The bounded Tab helper fails loudly with the focused element's `data-testid`, and the drawer's DOM order (book above counter) is fixed by `quest-drawer-split`.
- [Change applied before the shop change] → Declared dependency; the service-menus MODIFIED text already contains the shop change's wording and would silently drop it otherwise.
