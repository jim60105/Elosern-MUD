## Context

After H1, the client's reference surfaces live in the `hud-right` stage anchor: a 230px-wide,
absolutely positioned, internally scrolling column holding `CharacterPanel`, `SkillBook`, `ShopPanel`,
`QuestBoard`, `LoreDrawer` and `InventoryPanel` in that order (`AppClient.vue:477-498`,
`HudFrame.vue:147-159`). It is the migration's right column with a new address: six
surfaces permanently mounted, permanently in the tab order, and mostly below the fold at 1280x720,
so a player standing nowhere near a merchant still carries a shop panel, a quest board and a lore
panel in the accessibility tree of every frame they play. The anchor itself is not the problem and is
not this wave's to remove — H2's `webclient-contextual-hud` delta re-tenants `hud-right` with the
minimap island, and the caption's `calc(90vw - 524px)` reservation (`HudFrame.vue:167`) is sized for
that end state.

The draft is architecturally different. `index.html:404-413` defines one drawer chrome
(`position:fixed; top:46px; right:0; bottom:0; width:min(560px,94vw)`, `--panel-solid`, `border-left`,
`transform:translateX(100%)` → `translateX(0)`, a `.dhead` / `.body` / `.foot` column) and seven
instances of it over a `backdrop-filter:blur(3px)` scrim, with `game.classList.add('menu-open')` while
any is open. The `top:46px` is scaffolding — `index.html:593` says `.game{padding-top:46px} /* clear
the design switch */`, the preview toolbar — so in the client the drawer runs the full height.

Three landed contracts bound this wave. H1's `webclient-contextual-hud` already requires that an open
drawer recesses the stage and that the recession clears only when nothing is open, and left the seam
open in code (`AppClient.vue:95-96`: *"H4's drawers will register into the same set"*). H3 makes the
dock's root frame the surface's single listbox and single tab stop, and makes every visible level a
rendering of one router frame rather than a second navigation model. And `webclient-service-menus`
pins a keyboard-only journey through the dock's service frames, a bounded quantity form and an
explicit abandon confirmation — none of which H4 may quietly relocate or weaken.

Constraints inherited from the roadmap: no server, protocol or read-model change; the preserved DOM
identifiers do not move; every surface is backed by a real read model or absent; both 1440x900 and
1280x720 supported; the client is shippable at the landing.

## Goals / Non-Goals

**Goals**

- Ship one reusable drawer chrome with a correct modal contract (single-open, focus trap, Escape,
  focus restoration, scrim) and satisfy H1's stage-recession requirement through it.
- Move all six reference surfaces into drawers in the same change that empties the `hud-right` stack,
  so nothing is homeless and nothing stays mounted that the player did not ask for.
- Build the inventory bag and the equipment paper doll from the payloads that already back them, and
  correct the two spec statements that say the bag is unbacked.
- Keep the keyboard service journey identical in its steps, its payloads and its confirmations.
- Leave the dock's navigation model, every router frame and every preserved identifier untouched.

**Non-Goals**

- Any change to the dock's root items, frames, keys, badges or Escape semantics (H3 owns those).
- The HUD island stack, the condition chips or the HUD wallet (H2), the command line or the
  `Map`/`Settings`/`Help` overlays (H5).
- Any new read model: no party drawer, no 親密狀態 block, no toasts, no item rarity, no discovered-lore
  compendium.
- Re-homing the dock's `service_menu.js` frames into drawer-only markup. The drawer *hosts* them; it
  does not replace them.

## Decisions

### D1 — One drawer chrome, six instances, one open at a time

`HudDrawer.vue` owns the geometry, the scrim, the header/body/footer frame, the transition and the
whole modal contract; each drawer is that component with a title, a subtitle and a body slot. A single
`view.hudDrawer` name (or `null`) means the "one open at a time" rule is structural rather than a
convention six components must each remember.

*Rationale:* six copies of a focus trap is six chances to get the accessibility contract subtly
different, and the draft itself has exactly one `.draw` rule for all seven drawers.
*Alternative rejected:* a `<dialog>` element with the platform's own modality. `showModal()` gives a
free trap and a free scrim, but it moves the surface into the top layer, outside the stage's
`data-menu-open` filter — the stage would not visibly recess, so H1's landed recession requirement
would need a second mechanism to stay satisfied.

### D2 — The drawer is an alternate rendering of a router frame, never a second navigation model

H4 changes no root item and no menu frame. Where the dock already owns a surface, the drawer renders
that surface's frame:

- `character` root → the 角色狀態 drawer. This root is today a **no-op**: `stores/elosern.js:703-705`
  sets `activeSubDock = "character"` and pushes nothing, because the permanently visible right column
  *was* the character surface. H4 gives it the surface it always implied.
- `quests` / `inventory` roots and the interact-target `公會服務` / `商店` affordances → the 任務 /
  背包 / 商店 drawers. These keep pushing their existing `service_menu.js` frames; while such a frame
  is the router's current frame, its rows render inside the drawer beside the rich panel.
- 技能書 and 圖鑑 have no dock entry of their own; each is opened by one labelled control inside the
  drawer that already presents the same read model — the skill book from the character-status drawer
  (`character.actives`/`passives` is the same payload as its traits) and the lore reference from the
  quest drawer (both are the `services.guild` section).

*Rationale:* H3's central claim is that the tab bar, the breadcrumb and the panes are three renderings
of one state. A drawer that opened its own frames would be a fourth state that Escape does not know
about, and `webclient-service-menus`' keyboard journey would have to be rewritten to reach it.
*Alternative rejected:* adding six drawer-opener rows to the exploration root (or repointing the
existing `character` / `quests` / `inventory` roots at drawers and adding three more). Either forces a
`MODIFIED` on H3's just-authored root-key list in `webclient-desktop-shell`, on
`webclient-exploration-menu`'s root prose and on four of its scenarios, for a wave the roadmap already
flags as oversized — and the second variant strands the keyboard service flow.

### D3 — One named open entry in the store, not prop-drilling

`store.openHudDrawer(name)` / `store.closeHudDrawer()` over the closed set
`skill | inventory | shop | quest | lore | status`, with `view.hudDrawer` published on the committed
view. Every opener — the router branches of D2, the drawer-internal controls, and H2's
condition-overflow `+N` chip — goes through it.

*Rationale:* three unrelated subtrees need to open a drawer, and exactly one place must be able to
force every drawer closed on a mode change, an epoch reset or a transport loss. The store is already
the single writer for view state and already owns `mutationsLocked` and the epoch gates.
*Alternative rejected:* `provide`/`inject` from `AppClient`. It reaches the dock and the islands, but
it leaves the teardown scattered across whichever component happens to watch `mode`, and it is
invisible to the store tests that already assert epoch behaviour.

### D4 — Escape belongs to the drawer while a drawer is open

Focus is trapped inside the open drawer, so the dock never receives the key. Escape closes the drawer
and returns focus to the control that opened it. When the drawer is hosting a router frame, closing it
also pops that frame — one Escape, one level, exactly as `webclient-desktop-shell` requires.

*Rationale:* the alternative is two Escape owners racing, which is the precise failure mode H3's
"the breadcrumb cannot drift from the router" requirement exists to prevent.
*Alternative rejected:* letting Escape fall through to the router and closing the drawer as a side
effect of the frame popping. It inverts the causality — a player who opened the status drawer (no
frame pushed) would press Escape and have nothing to pop.

### D5 — One general focus trap, extracted rather than duplicated

H1's `FullLogOverlay.vue:54-68` traps focus by cycling between two known elements. A drawer holds an
arbitrary number of focusables (tabs, search fields, quantity steppers, action buttons), so H4 adds
`components/focus-trap.js` — a focusable-query trap with a documented selector list — and re-points
`FullLogOverlay` at it in the same change.

*Rationale:* two implementations of the same accessibility contract diverge; the overlay's two-element
cycle is the special case of the general trap, not a different thing. H1 is archived, so editing its
file is a serialize, not a merge conflict (roadmap §7).
*Alternative rejected:* leaving `FullLogOverlay` alone and writing a second trap for drawers. It ships
the divergence deliberately and gives H5 (which wires three more overlays) a third choice to make.

### D6 — The bag is built; the ceiling is stated, the total is not invented

`InventoryPanel` renders `services.inventory.rows` — up to 32 distinct item keys, each with
`display_name`, `held` and `equipped`. `pagination.inventory_total` is `len(rows)`
(`service_view.py:757`), i.e. the shipped count, not the untruncated holding count, so the drawer
**never** renders "32 of N". When the listing is at the ceiling it says so in words; otherwise it says
nothing about a total. The draft's rarity borders and comparison tooltip are dropped because the rows
carry neither, and no use/consume/equip control is added because the schema advertises none.

*Rationale:* the whole point of the truthful-data rule is that a number on screen is a claim. "32 of
32" would be a true statement that reads as a false one.
*Alternative rejected:* showing `pagination.inventory_total` as a total next to the row count. It is
the same number as the row count in every case, so it is either redundant or misleading.

### D7 — The paper doll is drawn from the server's slot vocabulary, with a passthrough

`character.equipment` rows are exactly `{slot, item_key, display_name}`
(`presentation/character.py:156-167`) and exist only for filled slots. The server's slot vocabulary is
closed — `weapon_main`, `weapon_off`, `armor`, and `accessory` repeated 0..3 times
(`world/skills/equipment.py:8-17`, `world/rules/status_query.py:42,571-585`) — so the doll renders
主手 / 副手 / 盔甲 as three named boxes that show an explicit empty state when no row carries that
slot, plus an accessory group. But the *protocol* validator accepts any non-empty slot string up to 32
rows, so any unrecognised slot renders as a labelled passthrough row rather than being dropped. No
statistics line is rendered: the payload carries none.

*Rationale:* a fixed four-box doll would silently discard a second accessory or a slot a future
release adds — the failure would be invisible.
*Alternative rejected:* rendering the doll purely as a flat list of the rows present. It is honest but
loses the draft's affordance of *seeing an empty slot*, which is the doll's whole reason to exist.

### D8 — The status drawer degrades per section, because its two payloads have different availability

`status` is available in every mode (`presentation/status.py:17-23` raises only on a read-model
error); `character` and `services` are exploration-only (`character.py:409`, `services.py:786-788`
both raise `PanelUnavailableError` outside exploration mode). So the character-status drawer renders
its vitals and its full condition roster from `status` in **every** mode, and marks the traits,
equipment, disguise, guild, wallet and persona sections with the registry-owned reason when
`character` is unavailable. This is what makes H2's `+N` condition-overflow chip usable in combat,
where it matters most.

*Rationale:* a drawer that refuses to open in combat would strand the one chip the roadmap explicitly
routes to it (roadmap §6, H2's row).
*Alternative rejected:* two drawers, one per payload. It doubles the chrome and forces the player to
know which server panel a fact came from.

### D9 — The drawer layer renders the wallet exactly once, and it is the character sheet's row

`ShopPanel`, `LoreDrawer` and `InventoryPanel` each print 「錢包 N 銅」 today and `CharacterPanel`
prints a fourth. H4 deletes the first three. The character-status drawer keeps its row, because a
wallet is a character fact and because H2 — which makes the HUD head card the persistent at-a-glance
wallet — may land after H4; deleting all four would leave the value unreachable at H4's landing, which
roadmap §5 forbids.

*Rationale:* "the client stays shippable after every change" is a hard rule, and wave order between H2
and H4 is not fixed.
*Alternative rejected:* keeping the shop drawer's wallet "because you need it while buying". The buy
row already carries its own affordability reason from the server; a second copy of the balance is a
second thing to keep in sync.

### D10 — H4 empties the `hud-right` stack; it does not touch the anchor or the caption's width

H4 removes the six reference surfaces from `AppClient.vue`'s `#panel-right` slot and mounts nothing in
their place. It does **not** delete the `hud-right` anchor, does not edit `HudFrame.vue`'s geometry,
and does not re-derive `min(880px, calc(90vw - 524px))`, because H2's delta places the minimap island
"in the stage's right anchor" and its design sizes the 524px reservation as
`262 (hud-left) + 230 (hud-right) + gutters` for exactly that end state. If H4 lands before H2 the
anchor renders nothing for one wave — no layout cost, no tab stop, no dead controls.

*Rationale:* two waves editing one anchor's geometry is the forced serialize roadmap §7 exists to
prevent, and the anchor is not what makes the reference panels wrong — being permanently mounted is.
*Alternative rejected:* deleting the anchor and reclaiming its width for the caption. It reads as the
bigger win, but it would be undone by H2 in either landing order, and in the order `H4 → H2` it would
leave the minimap with nowhere to go.

### D11 — Drawer mutations reuse the dispatch path, and the destructive one gains the confirmation it lacks

Every affordance inside a drawer emits its intent through the single store dispatch entry with the
server-authored `action_id` and payload, and locks with `mutationsLocked` exactly as it does now. One
gap is closed on the way: `QuestBoard.vue:155-161` dispatches `guild.quest_abandon` directly on click,
with no confirmation, while the dock path has required an explicit confirm screen since the services
wave. The drawer gains the same two-step confirm.

*Rationale:* H4 is the change that makes the pointer path the primary way most players will reach
abandon; shipping it without the confirmation the keyboard path has had all along would be a
regression the wave caused.
*Alternative rejected:* leaving it and filing a follow-up. The file is open, the contract already
exists in `webclient-service-menus`, and the fix is one frame.

## Risks / Trade-offs

- **Risk: H4 is the roadmap's largest wave and D2 adds the router-hosting seam on top of six panel
  migrations.** → Mitigation: the task list is ordered so groups 1–4 (trap, shell, controller, the
  three non-service drawers) are independently verifiable and leave the client shippable; if
  verification exceeds one workday the wave splits at that boundary per roadmap §6's
  "split, not stretched", which amends the roadmap table and re-opens nothing.
- **Risk: a drawer that hosts a router frame can disagree with the router about what is open.** →
  Mitigation: the drawer never stores a frame. It renders `view.combatMenu`/`view.dockTrail` exactly as
  the dock does, through H3's shared row renderer, and D4 makes closing and popping the same action.
  A Vitest asserts that no state exists in which a service frame is current and its drawer is closed.
- **Risk: the services browser suite's readiness gate is a visibility check on a surface that is now
  hidden by default.** → Mitigation: the gate re-maps to the committed store state plus the drawer's
  own `data-testid`, opened as the first step of each journey; all 17 call sites are re-mapped in this
  change, not deferred to H6.
- **Risk: an open 560px drawer at 1280x720 covers most of the stage, including the narrative.** →
  Mitigation: this is the draft's deliberate trade (REDESIGN.md §0.1) and H1 already narrowed the
  non-closable set to the dock, the caption and the command line for exactly this reason. H4 carries
  the `webclient-service-menus` `MODIFIED` so the 1280x720 scenario stops asserting simultaneous
  legibility, and asserts instead that closing the drawer is always one action away.
- **Risk: H2 may land before or after H4, and both touch the wallet story and the manifest count.** →
  Mitigation: D9 keeps a wallet reachable in either order; the drawer reads `status.conditions`
  directly rather than importing H2's chip components; and the manifest edit is a `+3` against
  whatever count the predecessor left, with the frozen-count assertion updated in the same change
  (roadmap §7's serial-bottleneck rule).
- **Risk: un-deferring the inventory bag weakens the deferred-surface assertion that has been the
  guard against invented UI since B5.** → Mitigation: only the `\bBag\b` pattern and its dedicated
  case are removed, with the removal justified in the test's own comment by the backing payload and
  the file/line that builds it; Party, Intimate, EventLog, Toasts and H3's added names stay, and the
  status drawer's absent 親密狀態 block gains its own assertion.

## Migration Plan

0 released users, so there is no data migration. No persisted layout state describes the drawers — the
open drawer is session state and is not persisted, so a reload lands on a closed stage, which is the
correct default. Rollback is `git revert` of the change: the store's dispatch entry, the router, the
preserved identifiers, the presenters and the transport are untouched, so a revert restores the
`hud-right` stack without any state migration.

The order inside the wave keeps the client shippable at every commit: the shared trap and the drawer
shell land first with no surface moved; then the controller; then the three drawers whose surfaces the
dock does not own (skill, lore, status); then the three service drawers together with the emptying of
the `#panel-right` slot, so no surface is ever homeless.

## Open Questions

None blocking. Three deferred to their owning wave:

1. Whether the 圖鑑 drawer eventually becomes the draft's discovered-entry compendium — that needs a
   `lore` OOB panel, which is a server-side delivery unit, not a view wave.
2. Whether the character-status drawer's skill-book control becomes a second tab inside one drawer
   rather than a second drawer (H6, when the complete drawer set is re-frozen and the count is known).
3. Whether the drawer width becomes a user preference alongside `--prose-scale` (H5, with the settings
   surface).
