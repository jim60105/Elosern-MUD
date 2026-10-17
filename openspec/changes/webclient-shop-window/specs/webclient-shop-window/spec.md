# Spec Delta

## Purpose

The shop window: a quest-drawer-styled window with 購買 and 出售 tabs whose member rail chooses the recipient or seller from the shared viewed-member selection.

## ADDED Requirements

### Requirement: The shop window uses the frame with buy and sell tabs and the member rail
The shop window SHALL be built on `WindowFrame` with first-level tabs 購買 and 出售, the purse in the header, and the shared `MemberRail` whose selection is the session's viewed member (shared with the party window); selecting a member SHALL dispatch `party.view_member` with `tab: shop`. No category rail SHALL be used.

#### Scenario: The party window selection carries over
- **WHEN** the player selected 艾拉 in the party window and then opens the shop
- **THEN** the rail shows 艾拉 selected as the recipient

#### Scenario: Possession keeps the existing refusal
- **WHEN** the player opens the shop while possessing a companion
- **THEN** the window renders the same rows and every buy or sell attempt returns the existing `possessed_shop` refusal message

### Requirement: The buy view shows one price and the recipient's facts
Each 購買 row SHALL show icon, name, stock, buy price, and the recipient's committed delta (▲ 攻擊 +6, or 無法裝備) or held count for consumables; the detail SHALL show the item, a current-versus-after comparison for the recipient's slot, small delta chips for the other members from `item_holdings`, and the action bar with the quantity stepper (bounded by the committed maximum), the remaining purse and 買給 X, sending one `shop.buy` with the recipient's id.

#### Scenario: Buying for a companion
- **WHEN** 艾拉 is selected and the player buys three potions
- **THEN** exactly one `shop.buy {item_key, quantity: 3, recipient_id: 艾拉}` is sent and the button read 買給 艾拉

#### Scenario: The buy view shows no sell price
- **WHEN** the 購買 tab renders
- **THEN** no sell price appears anywhere in it

### Requirement: The sell view lists the seller's unequipped items with one price
Each 出售 row SHALL list the seller's sellable item with held count and sell price; the action bar SHALL show the stepper, the proceeds and the remaining purse, sending one `shop.sell` with the seller's id.

#### Scenario: Selling a companion's spare sword
- **WHEN** 卡恩 is selected on 出售 and the player sells two rusty swords
- **THEN** exactly one `shop.sell {item_key, quantity: 2, seller_id: 卡恩}` is sent and no buy price appears in the view

### Requirement: The shop window explains no rules
The shop window SHALL render values, states and committed disabled reasons only, with no explanatory rule text.

#### Scenario: A closed shop shows only its state
- **WHEN** the merchant is closed
- **THEN** the rows render with disabled controls carrying the committed closed reason and no prose about opening hours rules
