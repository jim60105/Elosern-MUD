# webclient-party-window Specification

## Purpose
The party window: one quest-drawer-styled window that presents the whole party through a member rail and first-level tabs, with the 成員 tab for bond, membership, persona and member actions.

## Requirements

### Requirement: The party window presents the whole party through one rail
The party window SHALL be built on `WindowFrame` with the first-level tabs 成員, 背包, 狀態, 技能, 系譜 in that order, the party purse in the header, and a `MemberRail` listing the `party` v3 rows (commander first) plus a 空位 entry while the general quota has room. Selecting a rail entry SHALL dispatch `party.view_member` with the current tab.

#### Scenario: Selecting a member dispatches the selection
- **WHEN** the player selects 艾拉 on the rail while the 狀態 tab is open
- **THEN** exactly one `party.view_member` with 艾拉's id and `tab: status` is sent and the tab stays 狀態

#### Scenario: Possession leaves the window identical
- **WHEN** the same party state is rendered while possessing 艾拉 and while not possessing
- **THEN** the rail, the tabs and every tab's content render identically, with no "you" marker

### Requirement: The window remembers its tab and member for the session
The selected member SHALL persist across tab changes, the window SHALL reopen on its last tab for the session, and when the server's `viewed_member_id` differs from the local selection (the member left or was deleted) the window SHALL adopt the server value and reset its local item selection and quantity.

#### Scenario: A departed member falls back to the commander
- **WHEN** the viewed companion leaves the party while the window is open on 背包
- **THEN** the rail selects the commander, the bag shows the commander's items, and no item stays selected

### Requirement: The member tab presents bond, membership, persona and actions
For a companion the 成員 tab SHALL show the bond stage with its pips, membership tags and intimate state, and an action bar with 請其離隊 (two-step confirmation like the quest drawer's abandon), 人物卡 (opens `NpcPersonaEditor`) and 附身 or 解除附身; for the commander it SHALL show the four persona fields, the intimate state and 編輯人物設定; for 空位 it SHALL show the invite target and its enabled or disabled descriptor from the existing `explore.party_invite` affordance.

#### Scenario: Leaving takes two steps
- **WHEN** the player activates 請其離隊 once
- **THEN** nothing is sent until the second confirming activation, and Escape cancels without sending

#### Scenario: The empty slot shows the invite descriptor
- **WHEN** 空位 is selected and the present innkeeper's invite affordance is disabled
- **THEN** the tab names the innkeeper and shows the committed disabled reason, and no invite is sent

### Requirement: Windows show state, never rule explanations
The party window SHALL render values, states and committed disabled reasons only, and SHALL NOT render explanatory rule text (follow rules, transfer rules, combat restrictions or legend prose).

#### Scenario: No rule prose in the member tab
- **WHEN** the 成員 tab renders a temporary escort member
- **THEN** it shows the commission tag and the leave descriptor's committed reason, and no prose explaining escort rules

### Requirement: The bag tab presents the viewed member's doll, bag and holdings
The 背包 tab SHALL show the viewed member's equipment doll (main hand, off hand, armor, accessory count) above the bag rows from `party_inventory`; selecting a doll slot SHALL filter the bag to items for that slot; selecting a row SHALL dispatch `party.view_member` with its `item_key` and show the item ribbon, name, summary and the `HoldingsStrip` from `item_holdings`.

#### Scenario: Selecting an item shows every member's holdings
- **WHEN** the commander's bag is viewed and the player selects 治療藥水
- **THEN** one `party.view_member` carries `item_key` 治療藥水 and the strip shows each member's committed count

#### Scenario: Equipment shows server deltas
- **WHEN** the selected item is the steel shortsword
- **THEN** each strip cell shows that member's committed delta (for example ▲ 攻擊 +6) or 無法裝備, and nothing is computed by the client

### Requirement: Giving from the bag uses the committed receive facts
Each non-owner holdings cell SHALL end in 交給 X when its receive fact is enabled; the action bar's quantity stepper SHALL bound the quantity by the row's `give.max_quantity` (equipment gives one), and confirming SHALL send exactly one `party.transfer` with the viewed member as giver. Taking an item back SHALL be done by selecting the companion on the rail and giving to the commander's cell.

#### Scenario: Three potions go to 卡恩
- **WHEN** the viewed member 艾拉 holds five potions and the player sets the stepper to 3 and activates 交給 卡恩
- **THEN** exactly one `party.transfer {giver_id: 艾拉, receiver_id: 卡恩, item_key, quantity: 3}` is sent

#### Scenario: A disabled receiver shows its reason
- **WHEN** 卡恩's receive fact is disabled with 「對方不在這裡。」
- **THEN** his cell shows no 交給 control and the reason is available as state feedback

### Requirement: The bag action bar uses or equips for the viewed member
The action bar SHALL offer 使用… (exploration, after confirmation) or 裝備 naming the replaced item, each sending the viewed member's `actor_id`, and SHALL show a disabled control's committed reason.

#### Scenario: Equipping names the replaced item
- **WHEN** the viewed member wields an iron longsword and the selected row is a steel shortsword
- **THEN** the button reads 裝備（替換 鐵製長劍） and one `inventory.toggle_equip` with the member's `actor_id` is sent on activation

### Requirement: In combat the bag shows counts and saves draft item use
During combat the holdings strip SHALL show counts only, transfer controls SHALL be absent, the action bar SHALL show 戰鬥中無法交換物品, 使用 SHALL become 設為 X 本回合的行動… which saves that member's v7 draft entry through the existing combat item flow, and equipment toggles SHALL stay available for every member.

#### Scenario: Combat use saves the draft entry
- **WHEN** in combat the player selects 艾拉's mana potion and activates 設為 艾拉 本回合的行動…
- **THEN** the existing combat item review/target flow opens for 艾拉 and no `inventory.use` or `party.transfer` is sent
