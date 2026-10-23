# Webclient Design Direction

The webclient is being redesigned as an AVG (visual-novel) + RPG hybrid in which
artwork is a primary subject, not a MUD text column. Frame UI proposals and
changes accordingly, and ship them as OpenSpec changes (no standalone HTML
prototypes; the real app differs too much for a prototype to be useful).

- Target desktop 16:9 only.
- Layout: full-bleed stage on top; bottom band = message window (2/3 width) plus
  command panel (1/3 width, at the band's right end) outside combat. In combat
  the command menu is a narrow card at the stage's dead centre (the same
  `#action-dock` moved into the `choices` anchor, in the gap the formation
  keeps clear) and the message window spans the band. Keep the image area
  large; do not put a narrative column and minimap side by side eating ~60% of
  the width.
- The player's own generated portrait stands on stage at all times; NPCs and
  enemies stand opposite in dialogue and combat.
- In combat both sides stand in one shared-scale formation around a clear
  dead centre (`components/combat-formation.js`, applied by AppClient): the
  party may leave its single row, every foe that has not fled stands, and
  each figure but the controlled one carries a glance plate (`FigurePlate.vue`,
  the stage's `plates` layer). A knocked-out or defeated foe keeps its slot
  collapsed under a broken seal (`✕ 已擊破`) and a knocked-out ally kneels
  (`▼ 倒地`); both differ from the listener dim by shape and text
  (StageActor's `fallen`). The place card and the participant roster are not
  shown in combat; the controlled figure's values stay in the vitals dock.
- Combat targets are picked on the stage figures (the stage target step,
  `stores/elosern/stage_targets.js`, published as `view.stageTarget`): in the
  target frame of an enabled SINGLE, SELF or AREA skill — and, since
  webclient-party-items-tactics, of a SINGLE item or 挑釁 — the card collapses
  to a target prompt, every figure outside the focused position's lit set
  takes the dialogue listener dim, each candidate carries a gold arrow marker
  above its plate (`components/stage-targeting.js`) and a hit area over its
  figure. The arrow keys walk the positions in stage order (left to right on
  the formation); the digits still pick the frame's items in server order;
  Enter, Space and Escape, the item order and every payload are the card rows'.
  The step's subject is the opened skill, item or basic action (same
  `{key,label,enabled,targetSpec,targets}` shape), never a second model.
- The commanded member's own items and basic actions live in the card, never
  in the bag: 道具 opens that member's committed stock (`item-<key>` rows
  carrying quantity and effect summary, each with its own committed reason),
  one item opens its review/SINGLE-target frame, Defend/Dodge confirm their
  round choice and Taunt picks one server-listed enemy. Every row submits the
  closed wire union through the guarded `combat.command` envelope
  (`{kind:"item", payload:{item_key[, target_id]}}`,
  `{kind:"tactic", payload:{key[, target_id]}}` — the literal wire kind is
  `tactic`; the panel echoes admitted entries back as `tactical`). A hostile
  item on an ally asks through the same actor-bound cross-side question. In
  combat the party window's 背包 tab routes 設為 X 本回合的行動… to that same
  flow (`store.useCombatItem(itemKey, memberId)`) and never dispatches
  `inventory.use`; inspection and every member's equipment toggles stay
  free. Both the exploration use and the toggle name the viewed member's
  `actor_id`, which the server reauthorizes.
- A cast across sides asks first (`stores/elosern/cross_side.js`, held in
  the store as `crossSideConfirm`, published as `view.crossSideConfirm`): a
  target-step submission whose skill is `hostile` and reaches a `party`
  participant (the actor included), or `beneficial` and reaches a `foes`
  one, opens a caution `QuestionCard` (`確定要對{友方|自己|敵方|友方與敵方}使用〈…〉？`)
  below the collapsed prompt with focus on 否, instead of sending. The dock is
  inert beneath it, no dock key or stage pointer acts, the stage keeps the
  step's dim and markers; 是 sends the held payload once, 否 / ✕ / Escape
  return to the step, and a panel that drops the skill or a target, a
  playing round or a mode change cancels it. Only the static facts decide;
  never add client-side combat maths to it.
- Party exits are party-scope, never the selected member's (`stores/elosern/
  frames.js` `requestPartyExit`/`confirmPartyExit`/`cancelPartyExit`, published
  as `view.partyExitConfirm`): 撤退 and 投降 sit at the end of every member
  root (and are the recovery root's only row) and are reachable without the
  member being commandable. Activating one sends one read-only
  `combat.exit_prompt {session_id, round_revision, operation}`; the
  server-bound answer opens the same `QuestionCard` in `choices` with 否
  focused, the whole-party scope and the server-authored consequence
  (`question-card-detail`), and every dock key, pointer and stage hit inert.
  是 sends exactly one `combat.exit_confirm` with the held token; 否 / ✕ /
  Escape discard only the prompt — the draft, the focused row and the clock
  stay untouched. The prompt is bound to session/round/generation/epoch: any
  replacement, a disconnect or a played round cancels it without a retry, and
  `combat.flee` / `combat.forfeit` have no client producer left.
- Vitals (HP/MP/stamina) are hidden at full and auto-appear when damaged or under a
  condition; always shown in combat.
- Dialogue collapses the action dock, and pressing 交談 enters the dialogue screen
  immediately (the server has `greeting_for()` in `world/rules/dialogue.py` for a
  no-keyword opener).
- The command line is hidden by default and expands via `/` or an icon.
- The message window uses AVG click-to-advance paging with a typewriter effect,
  paged per action response and never breaking mid-sentence; the player may act
  while pages remain (leftover pages flush to the log).
- A motion layer covers scene/mode transitions, typewriter, and beat-by-beat combat
  choreography; structured combat beats in the server protocol are accepted.
- Minimap has no legend and a thin frame, the full map is the map drawer, the full log
  opens scrolled to the bottom, the dock has a fixed height, and redundant head
  cards, 美術展示, and quick-word chips are removed.
- Minimap island labels are placed by `lib/island_labels.js` in navigation
  priority (exits, then current, then context): remembered rim names are laid
  out first and always drawn whole; an exit label is never dropped (truncated
  with a leader line when crowded); context names appear only where room is
  left. Gateways wear a gold arch with a `通往 <leads_to>` line, and a
  cross-layer gate target is an exit-ring stub whose native button is named
  `往 <leads_to> 移動` (Space is stopped at the button so the shell's key
  routing cannot swallow it).
- Island motion is scale-aware (`lib/map_pan.js` `islandMotion`): an
  unchanged projection mode and level pans the drawing with its
  world-anchored dot field; a changed one never pans. It dissolves an inert
  copy of the previous drawing at `full`
  (`composables/use-island-dissolve.js`) and switches at once at
  `reduced`/`off`.

- The full map is `MapDrawer.vue` inside the shared `OverlayHost`
  (`ownHeader`: the drawer draws the one header with the 區域／世界 tabs on
  keys 1／2). Its body is the real `AreaMapView` or `WorldMapView` over the
  on-demand `area_map`／`world_map` (`store.view.maps`), with floating
  chrome: the commission list top left, the control pill top right, the
  view's scale bar bottom left, and the view's ~360 px detail card only on
  selection, which the pill and `MapEdgePointers` step around.
  `composables/use-map-drawer.js` chooses the tab by layer on every opening,
  keeps per-tab view／selection memory per generation｜epoch (the area half
  also per `map_id|frame.key|frame.unit`), and sends `map.view` on open, on a
  tab switch and once per committed move while open — never on input or
  while closed. Keep the drawer data-free: it requests nothing itself.

## Styling pitfall

`styles/app-shell.css` contains `.elosern-root …` rules that duplicate or override
component `<style>` blocks, and Storybook does not render under `.elosern-root`.
When restyling a component, grep app-shell.css for its class names and remove or
update the `.elosern-root` duplicates, and verify geometry with a live-client
browser test, not only Storybook.

## Main navigation and window hotkeys

The top bar (`DesktopNavigation.vue`; webclient-main-navigation-hotkeys,
design §8 of the party member management design, after the prototype's
`MainNavPrototype.vue`) is 隊伍 / 任務 / 地圖, the `工具` icon group (信件,
圖鑑, 稱號冊, 角色肖像圖庫 while the `gallery` panel is available, 說明) and
設定 last, divided by thin gold hairlines.

- `components/nav-primary.js` is the one entry model (label, glyph, hotkey)
  and `primaryEntries()` decides presence: 隊伍 follows `store.partyAvailable`
  in every playing mode, 任務 is the server's `quests` navigation row (none in
  combat), 地圖 is absent in combat. Each entry draws its hotkey as a
  decorative key chip (`aria-hidden`, the control carries `aria-keyshortcuts`).
  The primary region is sized for all three entries (glyph counts plus a
  fixed chrome including the chip) and packed trailing, so the tools and 設定
  hold their place within 1px across modes.
- 隊伍 is `store.openHudDrawer("party")` — the remembered tab, no router pop
  and no submission-lock wait; 任務 keeps `tabToRootAndConfirm("quests")`.
  The bar marks 隊伍 current while the party window is open, whatever its tab.
- `composables/use-window-hotkeys.js`: one document `keydown` listener
  (bubble phase, beside the keyboard bridge, which never claims letters).
  P B C K L open the party window (bare, `inventory`, `status`, `skill`,
  `lineage` aliases), J and M run the 任務 and 地圖 openers. It reads
  the typed Latin letter (so the chip's letter works on any Latin layout),
  falling back to `event.code` on non-Latin layouts, and ignores consumed, repeated,
  modified (Shift included) and composing keys, text entries, the held
  cross-side / party-exit questions and any rendered alertdialog or
  aria-modal surface other than a drawer frame, creation, and every open
  drawer, overlay or full log — except that P B C K L switch an open party
  window live. An AppClient left mounted in a test keeps its listener, so
  AppClient suites unmount between tests.

## Shared window primitives

The party window and the shop compose the quest drawer frame through five
primitives (webclient-window-primitives; design §9 of
`docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`).
Reuse them for any new window instead of copying markup:

- `WindowFrame` — a `HudDrawer` (seal glyph, title, close, focus trap,
  Escape, motion unchanged) with the quest drawer's head row under it: the
  first-level `IconTabs` (`v-model`) and an `extras` slot (purse, quota).
  The body is one tabpanel; mount the frame only while the window is open.
  The dialog is named by its title, and the frame re-exposes HudDrawer's
  `forceClose()` for a host's confirmed discard past `closeGuard`.
  The prototype draws one header row; the frame keeps HudDrawer's header and
  puts the tabs and extras in the second row, as the quest drawer does.
- `MemberRail` — plain props (`members[]` with `id`, `name`, `portrait`
  URL, `knockedOut`, `unread`; `selected`; `emptySlot`), emits
  `select(id)`; the 空位 entry emits `select(EMPTY_SLOT)` (exported
  `"empty"`). Roving focus like `IconTabs`; selection only on Enter, Space
  or click; the selected entry has `aria-current`.
- `ListDetail` — `rail`, `list`, `detail` and `actions` slots; the list and
  the detail scroll independently and the actions stay pinned under the
  detail. `variant="portrait"` narrows the list column.
- `ActionBar` — `actions[]` (`key`, `label`, `enabled`, `reason`, `tone`,
  `glyph`) and an optional committed `reason`; the left slot shows only
  committed reasons (no rule text), disabled controls stay focusable with
  `aria-disabled` and emit nothing.
- `HoldingsStrip` — `item_holdings` v1 `rows` verbatim plus `members` for
  names, `giverId` and `combat`; emits `give(memberId)` only for an enabled
  receive fact. It computes no count or delta; in combat it shows counts
  only (the owner's cell keeps its 持有者 text).

Every primitive size is `calc(<n>px * var(--ui-scale))` or a token, text
uses `--text-*` tokens (never below `--text-xs`), and durations use
`--motion-*` (pinned by `tests/components/window_primitives_styles.test.js`).
The prototype's new glyphs live in `components/dock-icons.js`.

## Party window

`PartyWindow` (webclient-party-window-member-tab; design §6/§6.1 of the party
member management design) mounts under the
existing `party` drawer key outside the generic `HudDrawer` (it is its own
`WindowFrame`), with the tabs 成員/背包/狀態/技能/系譜 (keys `member`, `bag`,
`status`, `skills`, `lineage` — the exact `party.view_member` tab values), the
party purse (`party_inventory.purse`) in the header and, on 成員, the
`同伴 used / limit` quota beside it.

- Selection is server truth. The rail's selected entry is
  `party.viewed_member_id`; a rail click emits `view-member` and
  `composables/use-party-window.js` sends one `party.view_member` with the
  open tab. The entry is only marked pending (`MemberRail`'s `pending`,
  `aria-busy`) while that request id is the store's in-flight dispatch; never
  switch optimistically. A changed viewed member resets the window's local
  item selection and quantity (exposed to the later tabs' scoped slots).
- 空位 is the only local selection (it has no member id): it shows on every
  tab while the general quota has room, opens 成員 and sends nothing.
- The tab is session memory (`components/party-window-memory.js`, scoped to
  `<generation>|<epoch>` like the quest drawer's). A companion figure on the
  stage lineup (exploration only, outside the stage target step, never the
  commander's figure) opens on 成員; every 背包 opener opens on 背包 (see
  Bag routing below) and every 角色狀態 opener on 狀態 (see the status tab
  below); a bare `openHudDrawer('party')` reopens on the remembered tab. The lineup hit is a pointer convenience over the
  decorative `aria-hidden` layer; keyboard users reach every member through
  the rail.
- `PartyMemberTab` renders only the `party_member` panel's descriptors
  (possess or release, leave, `npc.persona.read`, `character.persona.update`)
  through `ActionBar`; 請其離隊 takes two steps and any close attempt while
  armed (Escape, ✕, scrim, via the window's `closeGuard`) cancels it instead.
  The commander's persona editor lives here (`composables/
  use-member-persona.js`). 人物卡 opens `NpcPersonaEditor` through
  `store.openNpcPersonaEditor`.
- The window has no possession input: it renders identically while
  possessing, with no "you" marker. It shows values, states and committed
  reasons only — no follow, transfer, combat or legend rule prose (design
  §3.4). The only client-authored state line is the 空位's
  `這裡沒有可邀請的對象。`.
- The rail draws initials, not portraits: only the shared attempt lifecycle
  resolves an artwork descriptor, so the viewed member's portrait is the
  成員 nameplate's `AvatarArtwork`.
- `PartyBagTab` (webclient-party-bag-tab; design §6.2) is the 背包 tab,
  backed by `party_inventory` (the viewed member's doll and rows) and
  `item_holdings` (the selected item's answer); `components/party-bag-model.js`
  holds its pure projections. A doll slot filters the rows locally. A row
  selection is server state: the window emits `view-item` and
  `use-party-window.js` sends one `party.view_member {member_id, tab: "bag",
  skill_key: null, item_key}`; the requested row shows (`aria-busy`) only while
  that request id is the store's in-flight dispatch (a refused click keeps the
  in-flight row; a request made for another member shows nothing), after
  which the committed `item_holdings.item_key` is the selection; an
  unavailable `item_holdings` states its reason for the last admitted row. The strip renders only an answer
  for exactly the shown item and viewed member. The stepper is bounded by the
  row's `give.max_quantity` (and the `party.transfer` wire limit of 99;
  equipment gives one) and resets with the member or item. Every intent leaves
  as `bag-action` through `intents.js` `onPartyBagAction` and names the
  viewed member: the `party.transfer` giver, the `inventory.use` /
  `inventory.toggle_equip` `actor_id`. 使用… opens a labelled confirmation
  drawn inside the window (its keys never reach the window's trap, the content
  behind it is `inert`, a close attempt cancels it); 裝備 names the replaced
  singleton occupant (`裝備（替換 X）`), never an accessory. An available but
  empty bag shows the shared `EmptyState`; a slot filter with no match is a
  one-line state. Rarity frames use the non-colour border patterns (uncommon
  dotted and rare dashed at 2px, epic double and legendary ridge at 3px).
- In combat (webclient-party-bag-retire) the strip shows counts only in
  one-line cells (the owner's 持有者 rides beside the name), no give control
  or stepper is offered, and the bar shows the committed give reason
  (戰鬥中無法交換物品。). A `use` descriptor routed `combat_draft` becomes
  設為 X 本回合的行動…, which emits `combat-item` (no confirmation: the card's
  item review/target step is the confirmation) and `intents.js`
  `onPartyBagCombatItem` calls `store.useCombatItem(itemKey, memberId)`. When
  that member is not the commanded one, the store first sends the actor
  selector's read-only `combat.actor_choices` and `followCombatItem` (run at
  the end of `publishView`, like the automatic advance) opens the item frame
  once that member's choices committed; the card then stays on that member.
  A refused or rejected switch toasts; a closed window, another viewed member
  or another actor query drops the intent. `onPartyBagAction` drops
  `party.transfer` and `inventory.use` in combat; toggles keep their committed
  descriptors. The server republishes `party_inventory` on engagement and on
  every settled round so the tab never shows stale combat descriptors or
  counts.
- Bag routing: every bag
  opener — the B hotkey, the exploration 背包 row and the combat root's
  client-local 背包 row — asks for the `inventory`
  drawer, and `stores/elosern/hud.js` `openHudDrawer("inventory")` remembers
  the 背包 tab and opens `party` instead; `inventory` is never the stored
  drawer name. The party purse in the window header is the only balance in
  the drawer layer.
- `PartyStatusTab` (webclient-party-status-tab; design §6.3) is the 狀態
  tab, in every mode, for the viewed member: the hero (rail-row name and
  portrait, `character.full_title`, a `GradeGem` with merit only while
  `guild.rank` is set), HP/MP/SP gauges from the `party` row, one listbox of
  the four static traits (`components/party-status-model.js`
  `STATUS_TRAIT_KEYS`, fail-closed) and the conditions, a selected trait's
  waterfall (base → each payload layer with source bar, glyph and 裝備/技能/
  狀態 label → effective) or a condition's 來源/剩餘/修正, and an active
  disguise pinned at the detail's foot as 對外顯示 values; every row keeps the
  true value. Raised/lowered totals carry ▲/▼ and a sign besides colour, and
  each severity its own glyph. The selection is local (first layered trait on
  open, reset with the viewed member); the `character` payload renders only
  while its `member_id` is the viewed member. `openHudDrawer("status")` remembers 狀態 and opens
  `party` (an open window switches tab live), the 角色狀態 row no longer sets
  the `character` sub-dock, and no `HudDrawer` drawer stands an art column.
- `PartySkillTab` (webclient-party-skill-tab; design §6.4) is the 技能 tab
  for the viewed member, after the prototype's `tabs/SkillTab.vue`; its pure
  projections live in `components/party-skill-model.js`. It keeps the old
  book's browsing (主動/被動 segment with the payload's counts, search, the
  keyboard tree in payload order, every category open on a reset) and adds
  per-row growth: meter and `Lv n` / 見頂 from the v9 growth facts
  (`xp_to_next_level` is the remainder, so the band is the pair's sum), 新
  from `fresh`, 修煉中 from `booked`. Rows carry no per-skill icon (the
  payload has none): actives draw the `skills` glyph, passives `buff`. The
  ladder (威力×label, `MP n` or `需 Lv n`, verbatim) and the lineage position
  render only while `character.selected_skill.key` is the row on screen;
  在系譜中檢視 emits `lineage` and the window switches to 系譜. The
  selection is server state: the tab calls the `requestSkill` prop
  (AppClient's `onViewSkill`, one `party.view_member {tab: "skills"}`), which
  returns the request id or null; opening the tab sends one only while the
  rail row is `unread` or the committed key differs, never while the
  dispatch lock is closed, and a refused one is retried when it opens. The
  `ActionBar` offers 排入修煉 (`practice` → `explore.practice {actor_id,
  skill}`) and 施放 (`use-skill` → `store.beginSkillUse`, the viewed member's
  `explore.skill_preview`); in combat both are disabled with
  戰鬥中無法排入修煉。 / 戰鬥中請使用指令卡 and `beginSkillUse` refuses
  without a hand-off. No local knocked-out gate: the preview's refusal is
  shown as 無法施放：… for that caster only.
  `openHudDrawer("skill")` remembers 技能 and opens `party`; the store hands
  a preview over only while the window is open on 技能 (it closes the window
  first) and its Escape return carries `{actorId, skillKey}`.
- `PartyLineageTab` (webclient-party-lineage-tab; design §6.5) is the 系譜
  tab, after the prototype's `tabs/LineageTab.vue`; its pure projections
  live in `components/party-lineage-model.js`. It renders the committed
  `lineage` v2 panel alone (the server builds it for the viewed member; it
  carries no member id). The list groups graphs by `group_label_zh` in
  payload order under `已完成 completed / total 樹`; a row is named by its
  supplied roots' display names joined with ` ‧ ` (never a skill key) and
  shows one diamond per node, the committed owned/total, 可解鎖 when a node
  is `ready` and 已全數見頂 when `consumed`. Node state follows ownership
  (capped: filled diamond, solid gold border, 見頂; owned: half-filled, solid
  border, `Lv n` and 「into/band → 下一階」 with band = into + to-next;
  otherwise locked: dashed), so the diamonds agree with `owned_count`; a
  non-empty `prereq_text_zh` shows on any node. The detail draws the
  selected graph: one row per `depth`, each row's nodes spread evenly in
  payload order (a lone merge node centres), one SVG curve per edge (an edge
  to an absent node is skipped) with an HTML `Lv n` pill at its midpoint; a
  wide row scrolls sideways. The graph selection is local (kept across a
  republish, first graph for a new member). An owned node emits
  `open-skill` and the window switches to 技能 with `focusSkill` set: the
  技能 tab selects it on its own segment ahead of the committed selection
  (waiting for the payload that carries it) and its normal selection
  dispatch tells the server. Locked nodes, and every node while a rail
  selection is in flight, are `aria-disabled`. 在系譜中檢視 on 技能 opens the
  selected skill's graph with its node marked current; both links are
  dropped when their tab is left or the member changes. The L
  hotkey's `openHudDrawer("lineage")` remembers 系譜 and opens `party`,
  switching an open window live.

## Shop window

`ShopWindow` (webclient-shop-window; design §4.3/§7 of the party member
management design) mounts under the `shop` drawer
key on its own `WindowFrame` (like `PartyWindow`, outside the generic
`HudDrawer`): the shop seal, the host's `display_name`, 營業中 / 已打烊 as the
header subtitle, the tabs 購買 / 出售 (`buy` / `sell`, local, default 購買) and
the party purse from `services.player.wallet` in the header extras. Every
merchant navigate affordance (`surface: "shop"`) opens it through
`openHudDrawer("shop")`; no category rail exists. Pure projections live in
`components/shop-window-model.js`; the row listbox is `ShopRows.vue` (also the
VitalsTrack changing-numerals story's price column).

- The `MemberRail` shows `party.viewed_member_id` (shared with the party
  window, so a member chosen there is the default recipient). A rail or chip
  selection emits `view-member` and `use-party-window.js`
  `onViewShopMember` sends one `party.view_member {tab: "shop", item_key}`
  carrying the shown item; the entry stays pending (never switched
  optimistically) and the rows' facts are dimmed and trading is off until
  the server adopts it. A row selection emits `view-item` →
  `onViewShopItem`; the row shows once admitted (`pendingItemKey`) or
  committed (`item_holdings.item_key` for `shop.member_id`).
- Rows: rarity-framed icon, name, 庫存 n / 售完 (購買) or 持有 n (出售), ONE
  price per view (`buy_copper` or `sell_copper`), and on 購買 the
  recipient's `viewed` fact: ▲/▼ delta lines, 無法裝備, ±0 or 持有 n. Delta
  reason codes (`accessory_slots_full`, ...) are never printed: they ride on
  `data-reason-code`, here and in `HoldingsStrip`.
- Detail: hero, and on 購買 for equipment a 裝備比較 of the recipient's
  committed current values (from `character`, only while its `member_id` is
  the recipient) beside the server change lines — no slot is committed for a
  stock row, so the replaced item is never named and nothing is added up —
  then 其他成員 chips; otherwise 隊伍持有量 chips. Chips are
  `HoldingsStrip variant="chips"` over the committed `item_holdings` answer
  for exactly the shown item and recipient.
- Action bar: the quantity entry and ± stepper bounded by the descriptor's
  committed `quantity` (absent when it is disabled), committed on change/
  blur; an out-of-bounds typed value sends nothing. 花費/得到 and 剩餘 N 銅
  are the one display-only arithmetic. 買給 X / 出售 sends one `shop.buy
  {item_key, quantity, recipient_id}` / `shop.sell {..., seller_id}` naming
  `shop.member_id`, only while the rail agrees with it. `use-shop-trade.js`
  states that trade's committed refusal (e.g. `insufficient_funds`) in the bar;
  a new member, tab or row drops it.
- The server republishes `party_inventory` with every trade, so the party
  window's 背包 tab and header purse never lag a purchase.
