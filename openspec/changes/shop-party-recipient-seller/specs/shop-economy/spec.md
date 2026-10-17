# Spec Delta

## ADDED Requirements

### Requirement: Purchases debit the party purse and fill the recipient's bag
A purchase SHALL name a recipient member (authorized for the organizing purpose), debit the unchanged buy price from the commander's wallet (the party purse), add the items to the recipient's bag, and decrement merchant stock, all in one transaction that restores every surface on failure.

#### Scenario: Buying potions for a companion
- **WHEN** the commander, holding 1,240 copper, buys three 40-copper potions for companion 艾拉
- **THEN** the commander's wallet is 1,120, 艾拉 holds three more potions, the commander's bag is unchanged, and stock drops by three

#### Scenario: Insufficient purse rejects for any recipient
- **WHEN** the purse holds less than the total price
- **THEN** the purchase is rejected with the existing insufficient-funds reason and nothing changes

#### Scenario: A forged recipient is refused
- **WHEN** the recipient names an NPC outside the party
- **THEN** the purchase is rejected with `not_party_member` and the commander does not receive the items

### Requirement: Sales draw from the seller's unequipped items and credit the party purse
A sale SHALL name a seller member (authorized for the organizing purpose), remove only that member's unequipped copies, credit the unchanged sell price (half the buy price) to the commander's wallet, and raise merchant stock up to its cap, atomically.

#### Scenario: Selling a companion's spare sword
- **WHEN** the commander sells companion 卡恩's two unequipped rusty swords
- **THEN** 卡恩 holds none, the purse rises by twice the sell price, and his equipped weapon is untouched

#### Scenario: An equipped copy is not sellable
- **WHEN** the seller's only copy of an item is equipped
- **THEN** the sale is rejected with `item_equipped` and nothing changes

### Requirement: Possession keeps the shop refusal
Every purchase and sale requested while the player is possessing a companion SHALL keep the existing `possessed_shop` refusal, whatever recipient or seller is named.

#### Scenario: Possessed purchase is refused
- **WHEN** the player, possessing 艾拉, asks to buy a potion for the commander
- **THEN** the request is refused with `possessed_shop` and nothing changes

### Requirement: Text shop commands name the recipient or seller
`buy <物品> [數量] [= <成員>]` (aliases `購買`, `買`, `shop buy`) and `sell <物品> [數量] [= <成員>]` (aliases `販賣`, `賣`, `shop sell`) SHALL name the recipient or seller (default: the caller) with the same rules and messages as the actions, and SHALL be documented in both player command documents.

#### Scenario: Text purchase for a companion
- **WHEN** the player types `買 治療藥水 3 = 艾拉` at an open merchant
- **THEN** the outcome equals `shop.buy` with `recipient_id` naming 艾拉
