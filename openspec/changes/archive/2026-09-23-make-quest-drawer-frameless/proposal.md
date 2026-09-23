## Why

The 任務 drawer has the same duplicate the 商店 drawer had: opening it through the guild clerk's navigate row or the top navigation's 任務 button pushes a guild service frame (`services.guild` / `services.quests`), and the drawer body renders that frame's rows through the shared dock row renderer (`dock-menu`, plus `dock-detail`) beside the drawer's own `QuestLog` + `GuildCounter` stack. Those two surfaces already present everything the hosted guild frames list — registration, every board offer with its accept control, every quest-log row with track / abandon (behind its own confirmation) / turn-in, and the rank examination — so the hosted rows are a second navigation model over the same committed `services` data. Once the shop drawer is frameless (`make-shop-drawer-frameless`), the quest drawer is the last drawer that hosts a router frame, and removing it lets the whole drawer-hosting render path go.

## What Changes

- Make the 任務 drawer frameless: both live openers — the top navigation's 任務 entry (the exploration root's `quests` item, reached through `tabToRootAndConfirm`) and the guild clerk's `navigate`-kind affordance row (`service-guild`) — open the drawer as a client-local open (`openDrawer: "quest"`) that leaves the router's frame stack, current frame, breadcrumb, menu keys, and active sub-dock unchanged, and records no service surface.
- Exempt the 任務 drawer from `closeHudDrawer()`'s frame pop and sub-dock teardown, so closing it pops nothing and returns focus to its opener.
- **Remove the drawer hosting render path** now that no drawer hosts a frame: the drawer-body `DockMenu` in `AppClient.vue`, the `drawerHostsServiceFrame` computed and its guard on the dock's own `DockMenu`, the `hud-drawer__body--dock` modifier class with its CSS rules, and `HudDrawer`'s `bodyClass` prop. No reference drawer renders a `dock-menu` or `dock-detail` in any state.
- Restate the contracts that described hosting or service submenus: the contextual-HUD "a drawer hosting a dock frame" requirement becomes "reference drawers present no router frame"; the desktop-shell direct-child rule drops its drawer-body clause; the frame-resolution "a drawer follows the stack when its hosted frame pops" requirement is removed; the service-menus acceptance requirement drives the guild journeys through the drawer's own controls; the exploration-menu requirements say Quests / Inventory and the navigate affordances open drawers, not service submenus.
- Remap the managed guild and quest-drawer browser journeys (register, board accept, abandon confirmation, turn-in, exam, 1280x720 visibility) from router rows onto `GuildCounter` / `QuestLog` controls driven by the keyboard (Tab / Enter).
- The unreachable guild/shop keyboard frames, the services sub-dock, the store quantity form, and the hosting bookkeeping stay in place and are deleted by `retire-service-keyboard-frames`.
- No OOB schema, presenter, server rule, or persistence change.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`: the hosting requirement is replaced by one frameless-drawer requirement that covers every reference drawer (the quest drawer's openers and close path, plus the bag's and shop's), keeping the payload-gated open and teardown-close rules; the bag-specific and shop-specific frameless requirements are folded into it and removed, so one requirement owns the rule.
- `webclient-desktop-shell`: the direct-child layout requirement is replaced by one scoped to the action dock's pane host (the drawer-body host and its scenario are dropped; no drawer body renders the row region).
- `webclient-frame-resolution`: the drawer-follows-hosted-frame requirement is removed (no drawer hosts a frame).
- `webclient-service-menus`: the browser acceptance requirement no longer names a drawer-hosted row renderer for guild submenus; guild and quest journeys are driven through the quest drawer's own controls.
- `webclient-exploration-menu`: Quests / Inventory and the guild/shop navigate affordances open their drawers without a service submenu frame (the keyboard-first dock requirement and the exploration browser acceptance requirement are restated; requirement names are kept so existing traceability anchors stay valid).

## Impact

- `web/static/webclient/js/elosern/exploration_menu.js` (root `quests` item and the guild navigate affordance row).
- `web/webclient-app/stores/elosern/interaction.js` (frameless allow-set gains `quest`), `stores/elosern/hud.js` (`FRAMELESS_DRAWER_NAMES` gains `quest`), `composables/use-dock.js` (delete `drawerHostsServiceFrame`), `AppClient.vue` (delete the drawer-body `DockMenu`, the `body-class` binding, the dock guard, the `.hud-drawer__body--dock` CSS, and the stale `quest-drawer` CSS comment), `components/HudDrawer.vue` (delete `bodyClass`).
- Tests: Node (`exploration_menu.test.js`, `hud_dock_menus.test.js`), Vitest (`hud_drawer.test.js` ×2, `app_client_drawers.test.js`, `frameless_bag.test.js`, `app_client_frameless_bag.test.js`, `declarative_surfaces.test.js`), the evidence module `web/webclient/tests/test_vue_hud_drawer_evidence.py`, and the managed browser files `test_browser_services_guild.py`, `test_browser_services_quest_drawer.py`, `test_browser_services_base.py`, `test_browser_exploration_nav.py` (CI-owned; not run locally).
- Depends on `make-shop-drawer-frameless` (shared files and the shared service-menus acceptance requirement); followed by `retire-service-keyboard-frames`.
