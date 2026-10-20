# Spec Delta

## REMOVED Requirements

### Requirement: Possession keeps the shop refusal
**Reason**: The approved decision permits party-scoped shop transactions while possessing a companion.
**Migration**: Replace the old `possessed_shop` refusal and its scenario with the normal party-authorized trade contract below. No saved-data migration or compatibility path is required.

## ADDED Requirements

### Requirement: Possessed trades use the named bag and the party purse
While possessing a companion, text `buy`/`sell` and web `shop.buy`/`shop.sell` SHALL use normal trade settlement. The named member's bag, commander's purse and merchant affinity, configured prices, authorization, and atomicity SHALL remain unchanged. Possession alone SHALL NOT refuse a trade. Text commands without a member suffix SHALL use the acting puppet's bag; web actions SHALL retain their explicit recipient or seller field.

#### Scenario: Possessed text purchase defaults to the acting puppet
- **WHEN** a player possessing a companion uses `buy <item_key> 2` at a valid open local merchant with stock and sufficient party funds
- **THEN** two items enter the companion's bag, the commander's bag is unchanged, the commander's purse is debited by twice the configured buy price, stock drops by two, and merchant affinity accrues to the commander exactly as for an unpossessed purchase

#### Scenario: Possessed text sale defaults to the acting puppet
- **WHEN** a player possessing a companion uses `sell <item_key> 1` for an unequipped offered item with merchant stock headroom
- **THEN** one item leaves that companion's bag, the commander's bag is unchanged, stock rises by one, and the commander's purse and merchant affinity receive the normal sale result

#### Scenario: Possessed web trades name the acting puppet explicitly
- **WHEN** an authenticated possessing client submits a legal `shop.buy` with the puppet's `recipient_id`, or `shop.sell` with its `seller_id`
- **THEN** the matching trade succeeds once against that puppet's bag and the commander's purse with normal configured prices and commander-keyed merchant affinity, without creating a companion wallet

#### Scenario: A possessed trade can name another authorized member
- **WHEN** the possessed actor names the commander or another authorized present party member through the text suffix or web member field
- **THEN** only the named member's bag changes and the same commander's purse pays or receives the configured price

#### Scenario: Possession does not bypass normal trade refusals
- **WHEN** a possessing actor requests a forged or absent member, insufficient funds or stock, a closed or unavailable merchant, an equipped-only sale, or a sale beyond the merchant cap
- **THEN** the normal party or trade refusal is returned without changing any transaction surface, with no fallback to the commander's bag

#### Scenario: Read-only stock remains available
- **WHEN** a player possessing a companion requests `shop stock` at a normally available local merchant
- **THEN** the existing read-only stock listing remains available and changes no state

### Requirement: Text inventory reports the party purse independently of the caller's bag
Text `inventory` SHALL display the commander's current party purse for an authenticated possessed companion and the caller's wallet for an unpossessed player. Its bag rows and existing character breakdown SHALL continue to describe the caller. Both player command documents SHALL describe possessed trade availability and distinguish the party purse from the caller's bag.

#### Scenario: Inventory shows the purchase debit from the party purse
- **WHEN** a companion with no wallet is possessed and a legal text purchase debits the commander's purse
- **THEN** `inventory` displays that same remaining purse as the web party window, lists the companion's updated bag, and does not display zero from the companion's absent wallet

#### Scenario: Unpossessed inventory keeps its existing bag presentation
- **WHEN** an unpossessed player requests `inventory`
- **THEN** the displayed purse remains that player's wallet and the existing bag ordering, quantities, item prose, and breakdown header remain unchanged
