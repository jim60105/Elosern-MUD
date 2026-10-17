# Party Member Management and Party Window

**Date:** 2026-10-18
**Status:** Approved in conversation section by section on 2026-10-18; awaiting written-spec review.
**Scope:** Out-of-combat and in-combat management of every party member's inventory, equipment, status, skills, and lineage; a single party window that replaces the inventory, status, skill, lineage, and party drawers; a redesigned shop; a reduced main navigation; party-wide time settlement; and the shared window primitives extracted from the quest drawer.

The current webclient presents one character at a time: the session's controlled figure. Companions own inventories, equipment, gauges, skills, and practice XP, and the v7 party combat commands already let the player issue every companion's round command. Outside combat, however, the player cannot see a companion's bag, cannot move items between members, cannot re-equip a companion, cannot let a companion use an item or cast, and cannot see a companion's skill growth. This design closes that gap and restyles every affected surface after the quest drawer.

## 1. Authority and amendments

`2026-07-29-ai-mud-engine-design.md` remains the architectural source of truth. This document keeps its single-writer boundary: every new state change lives in `world/rules/`, and presentation modules only read.

This document explicitly amends §2 of `2026-10-15-party-combat-and-equipment-growth-design.md`. That section excluded out-of-combat companion inventory management, bilateral item-transfer UI, and companion equipment-management UI. They are now in scope here. The v7 combat command contract is otherwise unchanged: in-combat item use still flows through actor commands and their draft.

The visual reference is the quest drawer approved in `2026-10-09-quest-drawer-redesign-design.md` and its prototype `docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue`. The approved brainstorming mockups are kept, uncommitted, under `.superpowers/brainstorm/` (`inventory-layout.html` option A, `window-structure.html` A, `main-nav.html` A, `shop-layout-v2.html` C, `status-tab.html` A, `member-tab.html`, `skill-lineage-tabs.html` skill half, `lineage-tab-v3.html`, `bag-tab-final.html`). Where a mockup and this document disagree, this document wins.

## 2. Findings that motivate the design

- Practice XP already accrues to the acting entity. `world/rules/action/costs.py::_step6_skill_practice` awards `request.actor`, so a commanded companion grows every ACTIVE skill it uses in combat. Companion growth exists but is invisible.
- `world/rules/time_skip.py` and `world/rules/movement.py` advance the world clock with only the acting character in scope. Resting therefore never regenerates a companion's gauges, never expires its buffs, and never settles its practice booking. Only combat settlement includes companions.
- The wallet lives only on the commander (`db.wallet`). Companions have no money.
- The text command `給` moves an item from the caller to another character. Nothing moves an item back, and no UI exposes either direction.
- The lineage payload lists chains as reverse closures from each root. A merge node appears in every root's chain, and the payload carries no edges, so no client can draw the real graph from it.
- During possession the webclient renders an honest hybrid: wallet, quests, and status stay with the owner while inventory and equipment show the possessed companion. A party-scoped window removes the need for that hybrid in the windows this design touches.

## 3. Core concepts

### 3.1 Commander, viewed member, actor

| Identity | Meaning | Source |
|---|---|---|
| Commander | The account's own character. It stays the commander while possessing a companion. | Server, from authentication |
| Viewed member | The member selected on the member rail of the party window and the shop | Session-scoped presentation selection |
| Actor | The member performing a mutation: who casts, who uses an item, who gives an item, who receives a purchase | Sent explicitly with every mutating action and revalidated by the server |

The viewed member only chooses whose data is presented. It never authorizes anything. Every mutating action carries its actor (or recipient or seller) identity, and the server re-derives that the identity is the commander or a present effective party member. A forged or stale identity is rejected; it is never replaced by the commander. This mirrors the v7 separation of commander, actor, and target.

### 3.2 Party-scoped presentation

The party window, the shop, and the main navigation present the whole party. The member rail always lists the commander first, then companions in party order. No "you" marker exists. Possession changes only the stage figure the player controls and the existing possession banner; the party window and the shop look identical whether or not the player is possessing. The wallet shown is the party purse, which is the commander's `db.wallet`. The existing `possessed_shop` refusal stays.

### 3.3 Summaries for all, detail for one

Following the v7 precedent, the server publishes a summary row for every member and full detail for one member only, the viewed member. Selecting a rail entry dispatches `party.view_member`; the server stores the selection on the session and pushes that member's detail panels. This keeps every payload within the 65,536-byte OOB bound regardless of party size.

Two facts need the whole party for one item: the bag's holdings strip and the shop's comparison strip. The server answers them for the selected item only, returning each member's held count and, for equipment, each member's stat delta. The client computes neither.

### 3.4 No rule explanations in the UI

Windows show state, values, and disabled reasons. They do not show explanatory rule text such as follow rules, transfer rules, or legend prose. That text moves to the help overlay. A disabled control's committed reason (for example 戰鬥中無法交換物品) is state feedback and stays.

## 4. Rules

All rules below live under `world/rules/`. Each mutation validates fully before writing and commits all of its writes or none.

### 4.1 Item transfer between members

- Allowed only outside combat. In combat the request is rejected with `transfer_in_combat`.
- Giver and receiver must each be the commander or an effective party member present in the commander's room. A knocked-out member may give and receive, because transfer only reorganizes bags; it may not use items or cast.
- An equipped item cannot be transferred (`item_equipped`); unequip first. Items carrying an existing lock reason (guild property, exam-kit lock) cannot be transferred (`item_locked`).
- Transfer is free: it advances no time and changes no affinity. Players have full authority over companion bags and equipment.
- One transaction composes the giver's removal and the receiver's addition through `plan_inventory_delta`, keeping containment and the key list synchronized.
- The text command `給` routes through the same rule entry. A new `取回` command moves an item from a member back to the commander.

### 4.2 Equipment for any member

`preflight_equipment_toggle(entity)` already accepts any entity. The toggle action now takes an actor and accepts any present party member. Toggling stays free in exploration and in combat, for every member, consuming no combat turn and no world time. The existing invalidation of affected previews and drafts applies to the re-equipped member.

### 4.3 Shop

- `shop.buy` carries a recipient. The price is debited from the party purse and the items enter the recipient's bag.
- `shop.sell` carries a seller. Only the seller's unequipped items are sellable. Proceeds enter the party purse.
- Buy and sell prices are unchanged. The sell price is always half the buy price, so the buy view shows only buy prices and the sell view shows only sell prices.
- Equipment comparison deltas use the same breakdown arithmetic as the status tab and are computed server-side for each member.
- Possession keeps the existing `possessed_shop` refusal.

### 4.4 Companion field actions

Out-of-combat item use and field casting take an actor. Costs are charged to the actor, SELF effects bind to the actor, and practice XP accrues to the actor through the existing path. The time cost equals the commander performing the same action. A member that is knocked out, unable to act, or absent is rejected with the existing reason codes. In combat these surfaces route to the v7 actor command flow instead (§6.4).

### 4.5 Practice booking per member

Each member owns one `db.practice_booking`. The commander can book practice for any member. The next SKIP advance settles every in-scope member's booking through the existing `grant_study_practice_xp` writer.

### 4.6 Party-wide time settlement

Three commander-initiated clock advances settle the commander plus every effective party member present in the commander's room: SKIP (rest and time skip in `world/rules/time_skip.py`), movement (`world/rules/movement.py`), and out-of-combat field casting and item use. The wider scope applies to gauge regeneration, buff expiry and decay, and practice settlement. Every other advance keeps its current scope, including the church rite in `world/rules/church.py`, which settles only its participant, the GM console, and defeat aftermath. Combat settlement already includes companions and is unchanged. A member in another room is not settled by the commander's advance.

### 4.7 Unlock notifications

When any member's practice award unlocks a skill, the commander receives a notification naming the member and the skill (艾拉 學會了 群體治癒). The rail's unread dot is session-scoped state in `ndb`; opening that member's skill tab clears it, and a reconnect drops it. Viewing therefore never writes persistent state.

### 4.8 Text-client parity

The text client exposes every operation. Each new or changed command is documented in both player command documents.

| Command | Operation |
|---|---|
| `給 <物品> = <成員>`, `取回 <物品> = <成員>` | Transfer between members |
| `裝備 <物品> = <成員>` | Toggle a member's equipment |
| `買 <物品> <數量> = <成員>` | Buy into a member's bag |
| `賣 <物品> <數量> = <成員>` | Sell from a member's bag |
| `使用 <物品> = <成員>` | A member uses an item |
| Casting with `由 <成員>` | A member casts |
| `修煉 <技能> = <成員>` | Book a member's practice |
| `狀態 <成員>`, `技能 <成員>`, `系譜 <成員>` | Show a member's data |

## 5. Presentation protocol

Every change follows the versioned exact-field schema convention. No old/new compatibility layer is added.

| Panel | Change |
|---|---|
| `party` v2 → v3 | Each summary row adds MP, SP, a knocked-out flag, and the session unread-unlock flag. The commander is row 0. |
| `party_member` (new) | The viewed member's member-tab facts: bond stage, membership (general and temporary commissions), intimate state, persona prose (commander only), and action descriptors for possess or release, leave, and opening the NPC persona editor. |
| `character` v5 → v6 | Built for the viewed member. Persona and intimate sections are removed (moved to `party_member`). Traits with breakdown layers, disguise, guild, and skill groups remain. |
| `party_inventory` (new) | The viewed member's equipment and bag rows with toggle, use, and transfer descriptors, plus the party purse. The `inventory` section leaves `services`. |
| Item holdings query (new) | For one selected item: every member's held count, and for equipment every member's stat delta against that member's current slot occupant. |
| `services` shop section | Stock rows gain the item presentation (kind, icon, rarity, summary) and the delta for the viewed member. Sellable rows list the viewed member's unequipped items. |
| `lineage` v1 → v2 | Built for the viewed member. The unit becomes a connected skill graph: group label, root keys, unique nodes with level, XP band, capped, owned, usable, and prerequisite text, plus edges with their minimum level, and owned/total counts. The chain meter is removed. |
| `status` v1 | Unchanged. It still describes the stage's controlled figure for the HUD vitals dock. |

The party window and the shop share one viewed-member selection. Selecting 艾拉 in the party window makes 艾拉 the shop's default recipient.

Action identifiers: `party.view_member` and `party.transfer` are new. `inventory.toggle_equip`, `inventory.use`, field casting, and practice booking gain an actor. `shop.buy` gains a recipient and `shop.sell` gains a seller.

## 6. Party window

One window, opened from the 隊伍 navigation entry. It reuses the quest drawer frame: seal glyph and title, first-level icon tabs, a left rail, a list column, a detail column, and an action bar pinned to the detail's bottom.

```
┌─ (◈) 隊伍  [♡成員][⚱背包][☰狀態][✦技能][⟟系譜]          ◎ 1,240 銅  [×] ┐
├────┬──────────────────────────┬──────────────────────────────────────────┤
│(莉)│ list column              │ detail column                            │
│(艾)│                          │                                          │
│(卡)│                          │                                          │
│(＋)│                          ├──────────────────────────────────────────┤
│rail│                          │ action bar                               │
└────┴──────────────────────────┴──────────────────────────────────────────┘
```

The rail lists members with portrait, name, a ▼倒地 shape-and-text marker for knocked-out members, and the unread-unlock dot. A dashed 空位 entry ends the rail while a slot is free. The selected member persists across tab changes. The window remembers its last tab for the session.

### 6.1 成員 tab

The list column holds the portrait nameplate (art, name, title, HP and MP). The detail column holds:

- For a companion: bond stage with stage pips, membership tags, and intimate state. The action bar offers 請其離隊 (two-step confirmation like the quest drawer's abandon), 人物卡 (opens the existing `NpcPersonaEditor`), and 附身 or 解除附身.
- For the commander: the four persona prose fields and intimate state. The action bar offers 編輯人物設定.
- For 空位: the invite target and its enabled or disabled descriptor, taken from the existing `explore.party_invite` affordance.

### 6.2 背包 tab

The list column shows the viewed member's equipment doll (main hand, off hand, armor, accessory count) above the bag rows. Selecting a doll slot filters the bag to items for that slot. The detail column shows the item ribbon, name, summary, and the holdings strip: one cell per member with that member's count, and for equipment the stat delta. Each non-owner cell ends in 交給 X. The quantity stepper in the action bar sets how many to give; equipment transfers one. The action bar also offers 使用… or 裝備 (naming the replaced item). To take an item back from a companion, the player selects that companion on the rail and uses the commander's cell.

In combat the holdings strip shows counts only, transfer controls are absent, the action bar shows the 戰鬥中無法交換物品 reason, and 使用 becomes 設為 X 本回合的行動…, which saves that member's v7 draft entry. Equipment toggles stay available for every member.

### 6.3 狀態 tab

The list column shows a hero row (portrait, name, title, and the guild `GradeGem` with merit when the member has a guild rank; a member without one shows no gem), the HP, MP, and SP gauges, the trait rows (label, base, effective; buffed values green and debuffed values orange, each also signed), and the condition rows (shape glyph, label, remaining time, modifier summary). Selecting a trait shows its breakdown as a waterfall in the detail column: base, then each layer with its source bar, glyph, and text label (裝備, 技能, 狀態), then the effective total. Selecting a condition shows its source, remaining time, and modifiers. An active disguise appears at the detail's foot with its displayed values; the tab itself always shows true values. The first trait with layers is selected on open.

### 6.4 技能 tab

The existing SkillBook content moves into the frame: active/passive segment, search, the category tree, and the detail card (target, cost, field capability, freeform rungs). Each row adds a proficiency meter and level, and newly unlocked skills carry a 新 tag. The detail adds the lineage position (prerequisite → skill → next unlock) that links into the 系譜 tab. The action bar offers 施放 (cast by the viewed member through the existing server preview and target flow) and 排入修煉 (book that member's practice). In combat both are disabled with their reason; combat casting stays on the command card.

### 6.5 系譜 tab

The list column groups skill graphs by element or style. Each row names the graph by its roots joined with ‧, shows one diamond per node (filled: capped, half-filled: owned, dashed: locked), shows owned/total, and marks 可解鎖 when a prerequisite is met for an unowned node. Graphs of one, two, or seven nodes render the same way. The detail column draws the selected graph: nodes placed by depth, merge nodes drawn once, edges labeled with their minimum level, and three node states distinguished by border style and text as well as color. Selecting a node opens that skill in the 技能 tab.

## 7. Shop window

The shop reuses the frame with first-level tabs 購買 and 出售 and the shared member rail. Merchants sell a single kind of goods with at most 12 stock rows, so no category rail is used.

- 購買: the rail selects the recipient. Each stock row shows icon, name, stock, buy price, and the delta for the selected member (▲ 攻擊 +6, or 無法裝備), or that member's held count for consumables. The detail shows the item, a current-versus-after comparison for the recipient's slot, small delta chips for the other members, and the action bar with the quantity stepper, the remaining purse, and 買給 X.
- 出售: the rail selects the seller. Rows list that member's sellable items with held count and sell price. The action bar shows the stepper, proceeds, and remaining purse.

## 8. Main navigation

The labelled entries become 隊伍, 任務, and 地圖. The icon tool group holds 信件, 圖鑑, 稱號冊, 肖像圖庫 (when available), and 說明, with 設定 fixed at the end. 隊伍 opens the party window on its last tab.

Hotkeys: P 隊伍, B 背包, C 狀態, K 技能, L 系譜, J 任務, M 地圖. They act only when focus is outside any text input. Activating a companion figure on the stage lineup opens the 成員 tab with that companion selected.

## 9. Shared window primitives

| Primitive | Responsibility |
|---|---|
| `WindowFrame` | Seal, title, first-level icon tabs, header extras (purse, quota), close; `HudDrawer` focus and motion contract |
| `IconTabs` | Existing; reused unchanged |
| `MemberRail` | Member entries, knocked-out marker, unread dot, 空位, roving focus |
| `ListDetail` | The list and detail grid with independent scrolling |
| `ActionBar` | Pinned bar with a left disabled-reason slot and right-aligned buttons |
| `HoldingsStrip` | Per-member count or delta cells, used by the bag and the shop |

Every size uses `calc(<n>px * var(--ui-scale))` or a token, with no text below `--text-xs`, and every literal duration uses a `--motion-*` token.

`InventoryPanel`, `EquipmentDoll`, `CharacterStatusDrawer`, `SkillBook`, `LineagePanel`, `PartyDrawer`, and `ShopPanel` are removed once their replacements land, together with their stories, manifest entries, and `.elosern-root` duplicate rules.

The rule text removed from the windows (follow rules, transfer rules, combat restrictions, the diamond legend) is added to the help overlay.

## 10. Error handling

- Every rejection returns a stable code and a fixed Traditional Chinese message and writes nothing. New codes include `transfer_in_combat`, `member_not_present`, `member_cannot_act`, `item_equipped`, `item_locked`, and `not_party_member`.
- A viewed member who leaves the party or is deleted falls back to the commander, and the client resets its local item selection and quantity.
- An unavailable panel renders its registry reason and invents no rows, counts, or deltas.
- A forged, stale, or non-member identity in any actor, recipient, or seller field is rejected. The server never substitutes the commander.

## 11. Verification

- Rules: focused tests for transfer and toggle success and every rejection, rollback of both bags under injected failure, companion cast costs and XP on the actor, shop recipient and seller with purse arithmetic, per-member practice settlement, party-wide time settlement including the different-room exclusion, and unlock notifications reaching the commander.
- Protocol: Python validators and JS mirrors with parity contracts, envelope bounds at maximal rows, and realistic fixtures.
- Client: Vitest for primitive keyboard behavior (rail, tabs, listbox), disabled reasons, and the no-invention rule. Storybook stories for every surface at 1451×790 and 1920×1080.
- Runtime: an `agent-browser` journey that buys potions for 艾拉, transfers some to 卡恩, re-equips 艾拉, casts a field heal as 艾拉, possesses 艾拉 and confirms the windows are unchanged, and in combat re-equips a companion and observes transfer disabled. Each text command also gets an exercised path.
- Implementation updates main specs through OpenSpec with canonical traceability IDs, updates both command documents, validators, fixtures, and shard manifests, and runs focused tests plus the contract gate. Logging changes also run the observability lint.

## 12. Decomposition

Implementation ships as about 20 OpenSpec changes, each under one engineer-day. The implementation plan fixes the exact split, dependencies, and conflict matrix.

| Phase | Changes |
|---|---|
| Rules (1–7) | Party-wide time settlement; member transfer; member equipment; companion field actions; per-member practice; shop recipient and seller; unlock notifications. Text commands ship with their rule. |
| Protocol (8–12) | Viewed-member selection with `party` v3 and `party_member`; `character` v6; `party_inventory` and the holdings query; `lineage` v2 graphs; structured shop rows. |
| Client (13–20) | Shared primitives; party window shell with the 成員 tab, navigation, and hotkeys; 背包; 狀態; 技能; 系譜; shop window; help content, removal of replaced components, and assembled acceptance. |

## 13. Non-goals

- No restyle of the letters, codex, title, gallery, settings, help, or remaining service windows in this batch. They adopt the shared primitives in a later design.
- No affinity cost or bond gate on managing a companion's items.
- No item transfer during combat, and no new combat command kind.
- No change to buy or sell price formulas, to possession entry or exit rules, or to the `possessed_shop` refusal.
- No companion wallets and no shared party inventory store.
- No persistent unread-unlock record.
