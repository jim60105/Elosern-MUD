## Why

This is change **H4** of the WebClient Contextual HUD Redesign, governed by
`docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md`
(depends on: **H1** `webclient-hud-01-shell-and-scene`, landed and archived, and **H3**
`webclient-hud-03-action-dock`, authored and validated — roadmap §6's `H1 → H3 → {H4, H5}` critical
path, and §9's rule that a sub-change may not start before its dependencies are `Done`).

H1 replaced the three-column grid with the cinematic stage and re-homed the six reference panels —
`CharacterPanel`, `SkillBook`, `ShopPanel`, `QuestBoard`, `LoreDrawer`, `InventoryPanel` — into the
`hud-right` stage anchor (`components/HudFrame.vue:147-159`: `top:64px; right:16px; width:230px;
max-height:calc(100% - var(--dock-h) - 110px); overflow-y:auto`). That was the correct H1 move — the
frame changed and no panel's chrome did — but it left the redesign's actual problem intact and made
it sharper: six panels are now stacked in a **230px** internally-scrolling column that is permanently
mounted, permanently in the tab order, and mostly below the fold at 1280x720. A player who is not
standing in a shop still carries a shop panel, a quest board and a lore panel in the accessibility
tree of every frame they play.

The design draft's answer (REDESIGN.md §0.1 「不常用→隱藏」, §1.3) is the opposite architecture: the
reference surfaces are **right-side slide-in drawers over a blurred scrim** (`index.html:404-413`),
absent until asked for, and no reference column exists. H4 builds that drawer surface and moves all
six panels into it **in the same change that empties the `hud-right` stack**, per roadmap §5's "a
surface is moved from its old home to its new home within one change, never split across two". The
anchor itself survives: H2 re-tenants it with the minimap island (its
`webclient-contextual-hud` delta, "The minimap island states only its own drawing convention", places
the minimap "in the stage's right anchor"), so H4 empties the anchor rather than deleting it, and the
narrative caption's width reservation is H2's business, not H4's.

The dependency on H3 is ordering-critical, not cosmetic. H3 makes the dock's root frame a tab bar
that is the surface's single listbox and single tab stop, and makes each frame's rendering a function
of the router's current frame. H4's drawers hang off exactly that model — a drawer is an alternate
*rendering* of a router frame the dock already owns, not a second navigation model. Landing H4 first
would mean inventing a trigger against a dock that is about to be rebuilt.

**A spec correction rides with this wave.** `openspec/specs/webclient-component-showcase/spec.md`
lists "a full inventory bag" among the surfaces that "MUST NOT be built here or mocked" because they
have "no backing OOB read model today", and the sibling requirement pins `InventoryPanel` to
"equipped items only". That premise is false for the bag, and was false when it was written:
`services.inventory` is built by `world/rules/service_view.py:695-720` **unconditionally for any
actor in exploration mode**, independent of any service host, and carries
`rows:[{item_key,display_name,held,equipped}]` bounded by `MAX_INVENTORY_ROWS = 32`. Today's
`InventoryPanel.vue:28-32` filters that real payload down to `equipped === true` and titles itself
「裝備」, so the client discards backed data it already receives. H4 carries `MODIFIED` deltas that
remove the bag from the deferred list, bind it to `services.inventory.rows`, and keep the three
genuinely unbacked surfaces — the Party/companion panel, the intimate/adult collapsible, and the
event-log Toasts — deferred and absent.

**A second correction, found while verifying the first.** The roadmap §2.4 and this wave's brief
describe `pagination.inventory_total` as the true count behind the 32-row bound. It is not:
`service_view.py:757` computes `inventory_total=len(inventory.rows)` — the *shipped* row count after
truncation — and `webclient-service-menus` already states each pagination total is "equal to the
number of rows shipped in that surface". The client therefore cannot truthfully render "32 of N".
The bag renders the rows it has and, at the 32-row ceiling, states the ceiling; it never claims to
know untruncated holdings. This proposal records the correction rather than propagating the wrong
premise into a requirement.

## What Changes

- **A reusable HUD drawer shell.** `HudDrawer.vue`: `position:fixed; top:0; right:0; bottom:0;
  width:min(560px,94vw)`, `--panel-solid` background, a left border and the draft's left-cast shadow,
  a `translateX(100%)`→`translateX(0)` slide over a blurred scrim, and the draft's head/body/foot
  frame (`.dhead` / `.body` / `.foot`, `index.html:404-413`). The draft's `top:46px` is **not**
  carried over: that offset clears the draft's own `設計預覽切換` preview toolbar
  (`index.html:593`), which does not exist in the client. Focus is trapped while open, Escape closes
  and restores focus to the control that opened it, activating the scrim closes it, and **at most one
  drawer is open at a time**. The drawer registers into H1's existing open-surface registry
  (`AppClient.vue:97-106`, whose comment already reserves the seam: *"H4's drawers will register into
  the same set"*), so H1's landed "An open drawer or overlay dims the stage behind it" requirement is
  **satisfied, not re-specified**.
- **Six drawers replace the `hud-right` stack.** 技能書 (`SkillBook`), 背包 · 裝備 (`InventoryPanel`
  plus a new equipment paper doll), 商店 (`ShopPanel`), 任務 (`QuestBoard`), 圖鑑 (`LoreDrawer`),
  角色狀態 (a new drawer composing the `status` vitals and full condition roster with the
  `character`-backed `CharacterPanel` body). `AppClient.vue`'s `#panel-right` slot contents are
  **removed**, so no reference surface is mounted while its drawer is closed. The `hud-right` anchor
  stays: H2 re-tenants it with the minimap island. If H4 lands before H2 the anchor renders nothing
  for one wave, which costs no layout and no tab stop.
- **A drawer is an alternate rendering of a dock frame, not a new navigation model.** H4 changes no
  root item, no router frame, no menu key and no Escape semantics. The `character` root item is today
  a no-op marker — `stores/elosern.js:703-705` sets `activeSubDock = "character"` and pushes nothing,
  because the always-visible right column *was* the character surface — so H4 makes it real by
  opening the 角色狀態 drawer. The `quests` / `inventory` roots and the interact-target
  `公會服務` / `商店` affordances keep pushing their existing `service_menu.js` frames; while such a
  frame is the router's current frame, that frame's rows render **inside** the matching drawer
  alongside the rich panel, so the keyboard path, the bounded quantity form and the abandon
  confirmation are the same code in the same place as the pointer path. Escape still pops exactly one
  level; leaving the surface closes the drawer.
- **A closed name set and one open entry.** `openHudDrawer(name)` / `closeHudDrawer()` over
  `skill` / `inventory` / `shop` / `quest` / `lore` / `status` is the only way a drawer opens, so H2's
  condition-overflow `+N` chip binds to `openHudDrawer("status")` without importing anything from
  H4, and a mode change or an epoch reset closes every drawer from one place.
- **The inventory bag is built.** `InventoryPanel` stops filtering to `equipped === true` and renders
  the bounded `services.inventory.rows` listing — `display_name`, `held`, and an `equipped` marker —
  stating the 32-row ceiling when the listing reaches it. The draft's rarity borders (`.it.r-c` …
  `.it.r-l`) and its comparison tooltip (`.tip`) are **dropped**: `services.inventory.rows` carries no
  rarity and no statistics.
- **An equipment paper doll from `character.equipment`.** Three named singleton slots (主手 / 副手 /
  盔甲) rendering empty when no row carries that slot, an accessory group holding the 0..3
  `accessory` rows, and a labelled passthrough row for any other server-authored slot key so nothing
  the payload sends is dropped. No stat line: `character.equipment` rows are exactly
  `{slot,item_key,display_name}` (`web/webclient/presentation/character.py:156-167`), and the doll's
  slot vocabulary is server-authored (`world/skills/equipment.py:8-17`), never invented.
- **The wallet stops being printed four times.** `ShopPanel`, `LoreDrawer` and `InventoryPanel` each
  render 「錢包 N 銅」 today, and `CharacterPanel` renders a fourth. H4 removes the three duplicates;
  the character-status drawer's wallet row remains the drawer layer's single wallet, so the value
  stays reachable whether or not H2 — which makes the HUD head card the persistent wallet surface —
  has landed yet.
- **Disguise stays a comparison, never a substitution.** The status drawer renders
  `character.disguise.displayed[]` beside the true `traits` rows it describes, with the standing
  statement that a disguise affects display, guild registration and identification only and that
  combat always resolves on true traits.
- **BREAKING (test-facing only):** the six surfaces are no longer in the DOM until their drawer is
  opened. `web/tests/browser/test_browser_services.py:79-95`'s `_wait_services_available` gates on
  `[data-testid="quest-board"]` being *visible*, so all 17 of its call sites break; H4 re-maps them in
  this change. No preserved contract identifier moves.
- **No server, protocol, presenter, action-allowlist or read-model change.** Every drawer consumes
  the eight allowlisted panels as they are.

## Capabilities

### New Capabilities

None. H1 created and archived `webclient-contextual-hud`; H4 adds requirements to it.

### Modified Capabilities

- `webclient-contextual-hud` (**ADDED** requirements; none of H1's five landed requirements and none
  of H3's ADDED requirements is modified): the right-anchored drawer surface and its
  focus/Escape/single-open contract; the removal of the permanently visible `hud-right` stack; the
  drawer-open contract and its availability-truthful rule; the bounded inventory bag and the
  equipment doll; the character-status drawer's per-section degradation; the single wallet rendering;
  and the dispatch/confirmation contract for mutations issued from inside a drawer.
- `webclient-component-showcase`: two `MODIFIED` requirements. The frozen/deferred requirement drops
  "a full inventory bag" from the deferred list while keeping the Party/companion panel, the
  intimate/adult collapsible and the event-log Toasts deferred and absent; the OOB-backed-surfaces
  requirement replaces "the inventory panel SHALL render only equipped items" with the bounded bag
  bound to `services.inventory.rows`. H1's added frozen-set growth rule (main spec) is **not**
  duplicated — H4 obeys it.
- `webclient-desktop-shell`: the required-surfaces requirement is re-expressed so the reference
  surfaces are demand-opened rather than permanently visible and each is reachable in at most two
  actions from the dock root. H3 also modifies this requirement, and H4 lands after H3 (roadmap §6),
  so **H4's copy is based on H3's edited version**
  (`openspec/changes/webclient-hud-03-action-dock/specs/webclient-desktop-shell/spec.md`), not on the
  current main spec. H1's narrowing of the non-closable set to the dock, the narrative caption and the
  command line is cited, not re-litigated.
- `webclient-service-menus`: the browser-acceptance requirement is re-expressed so the keyboard-only
  journey is unchanged in its steps while its service frames render inside the drawer, and so the
  1280x720 scenario stops requiring the narrative, the wallet and the stock to be legible
  simultaneously — an open drawer deliberately covers the stage.

## Impact

- **New:** `web/webclient-app/components/HudDrawer.vue`, `EquipmentDoll.vue`,
  `CharacterStatusDrawer.vue`, the shared `components/focus-trap.js` (a general focusable-query trap
  replacing the two-element cycle H1 hard-coded in `FullLogOverlay.vue:54-68`), their Storybook
  stories with deterministic offline args and their Vitest suites; three `component-manifest.json`
  entries (`Core/HudDrawer`, `Data/EquipmentDoll`, `Data/CharacterStatusDrawer`). The manifest stands
  at **29** after H1; H2 and H3 each extend it independently, so H4 extends whatever count its
  predecessors leave by exactly three and updates the frozen-count assertion in
  `tests/overlays/deferred_surfaces_absent.test.js` to match — never a hard-coded 25.
- **Modified:** `components/InventoryPanel.vue` (equipped-only filter → bounded bag + doll, wallet
  line removed), `ShopPanel.vue` (wallet line removed, drawer chrome), `QuestBoard.vue` (drawer
  chrome, explicit two-step abandon confirmation on the pointer path), `LoreDrawer.vue` (wallet and
  player-summary duplication removed, drawer chrome), `SkillBook.vue` (drawer chrome),
  `CharacterPanel.vue` (becomes the status drawer's `character`-backed body),
  `components/FullLogOverlay.vue` (re-pointed at the shared trap), `AppClient.vue` (empty the
  `#panel-right` slot, mount the drawer layer, register drawers into the open-surface set),
  `stores/elosern.js` (the drawer slice, the `openCharacter` branch at :703-705, and the
  mode/epoch teardown), `styles/app-shell.css`.
- **Re-mapped browser assertions:** `web/tests/browser/test_browser_services.py` (the
  `_wait_services_available` DOM-readiness gate on `[data-testid="quest-board"]` at :84-91 plus its
  17 call sites, and the `.quest-board__title` visibility assertion at :174) and
  `web/tests/browser/test_browser_pointer.py` (`.quest-board__action` at :512 — H3's Impact
  explicitly assigns this one to H4). No other browser file references these six surfaces.
- **Re-mapped unit assertions:** `tests/world/{shop_panel,quest_board,lore_drawer,inventory_panel}.test.js`,
  `tests/data/{character_panel,skill_book}.test.js`, and
  `tests/overlays/deferred_surfaces_absent.test.js` (the `\bBag\b` deferred pattern and the
  "keeps the equipped-only InventoryPanel" case are removed; Party / Intimate / EventLog / Toasts and
  H3's added deferred names stay).
- **Preserved / untouched:** the server, all eight presenters, the seven `guild.*`/`shop.*` adapters,
  the OOB envelope, `transport.js`, `bridge.js`, the preserved `js/elosern/*` logic — including
  `exploration_menu.js`'s root items, `service_menu.js`'s frames and the `KeyboardRouter`'s key
  semantics — `#action-dock`, `#inputfield`, `#elosern-offline-overlay`, `#elosern-action-live`,
  `#narrative-unread`, `#combat-row-<i>`, the `action-*` / `target-*` item keys, and the
  dependency-free text fallback.
- **Wave boundaries:** H4 does not edit `StatusPanel.vue`, `LocalMap.vue`, `CharacterHead.vue`,
  `VitalsTrack.vue` or `ConditionChips.vue` (H2), nor `ActionDock.vue`, `DockMenu.vue`,
  `DockMenuItem.vue`, `DockTabBar.vue`, `DockBreadcrumb.vue` or `ParticipantFrame.vue` (H3), nor
  `HudFrame.vue`'s anchor geometry or the caption's width reservation (H2 owns the `hud-right`
  re-tenanting and the left-stack width question that follows it). It reads the `status` payload
  for the drawer's condition roster rather than importing H2's chip components, so the two waves may
  land in either order.
- **Not built (no backing read model, roadmap §2.4):** the Party/companion drawer the draft shows at
  `dr-party`, the 親密狀態 collapsible inside `dr-status` (arousal / wetness / shame / exposure /
  climax_phase / per-part sensitivity / virginity flags have no field in `status` or `character`),
  the event-log Toasts surface, item rarity and per-item stat tooltips, and the draft's
  discovered-entry lore compendium (no `lore` panel exists in the eight-panel allowlist — the 圖鑑
  drawer keeps rendering the `services`-backed reference it renders today). Each is named in the
  extended `tests/overlays/deferred_surfaces_absent.test.js` with the field it waits on.
