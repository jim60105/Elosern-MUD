## MODIFIED Requirements

### Requirement: The buy view shows one price and the recipient's facts
Each 購買 row SHALL show icon, name, stock, buy price, and the recipient's committed delta (▲ 攻擊 +6, or 無法裝備) or held count for consumables; the detail SHALL show the item, a current-versus-after comparison for the recipient's slot, small delta chips for the other members from `item_holdings`, and the action bar with the quantity stepper (bounded by the committed maximum), the remaining purse and 買給 X, sending one `shop.buy` with the recipient's id.

#### Scenario: Buying for a companion
- **WHEN** 艾拉 is selected and the player buys three potions
- **THEN** exactly one `shop.buy {item_key, quantity: 3, recipient_id: 艾拉}` is sent and the button read 買給 艾拉

#### Scenario: The buy view shows no sell price
- **WHEN** the 購買 tab renders
- **THEN** no sell price appears anywhere in it

#### Scenario: An asymmetric configured price is not inferred from sale value
- **WHEN** a valid synthetic offer has buy price 8 copper and sell price 6 copper and the recipient buys three
- **THEN** the buy view shows only 8, its total is 24, and the real trade debits 24 from the party purse while adding three to the recipient's bag and removing three from merchant stock

### Requirement: The sell view lists the seller's unequipped items with one price
Each 出售 row SHALL list the seller's sellable item with held count and sell price; the action bar SHALL show the stepper, the proceeds and the remaining purse, sending one `shop.sell` with the seller's id.

#### Scenario: Selling a companion's spare sword
- **WHEN** 卡恩 is selected on 出售 and the player sells two rusty swords
- **THEN** exactly one `shop.sell {item_key, quantity: 2, seller_id: 卡恩}` is sent and no buy price appears in the view

#### Scenario: The sell view preserves independently configured proceeds
- **WHEN** the same valid 8-buy/6-sell offer is sold once from a member's unequipped bag with stock headroom
- **THEN** the sell view shows only 6 and the real trade credits 6 to the party purse, removes one from that seller and adds one to merchant stock without deriving or enforcing a half-buy ratio
