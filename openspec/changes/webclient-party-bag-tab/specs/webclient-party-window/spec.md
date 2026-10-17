# Spec Delta

## ADDED Requirements

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
