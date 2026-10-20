# Spec Delta

## REMOVED Requirements

### Requirement: The shop window uses the frame with buy and sell tabs and the member rail
**Reason**: The old possessed-refusal scenario is unsatisfiable and superseded. The CLI forbids retiring scenario names within a MODIFIED block, so the requirement is replaced while retaining frame, tabs and member selection.
**Migration**: Use the replacement shop-window requirement below and update active traceability references at spec synchronization. No runtime compatibility path or saved-data migration is needed.

## ADDED Requirements

### Requirement: The shop window shares member selection and normal trades during possession
The shop window SHALL be built on `WindowFrame` with first-level tabs 購買 and 出售, the purse in the header, and the shared `MemberRail` whose selection is the session's viewed member (shared with the party window); selecting a member SHALL dispatch `party.view_member` with `tab: shop`. No category rail SHALL be used.

#### Scenario: The party window selection carries over
- **WHEN** the player selected 艾拉 in the party window and then opens the shop
- **THEN** the rail shows 艾拉 selected as the recipient

#### Scenario: Possession keeps normal shop presentation and transactions
- **WHEN** a player possessing a companion opens the shop at an available merchant with the same viewed member and canonical state as without possession
- **THEN** the window renders the same member rail, purse, stock and sellable rows, and ordinary legal buy and sell attempts succeed under the unchanged named-member bag, commander purse, configured price and merchant-affinity rules

#### Scenario: Possessed trades refresh committed values
- **WHEN** a possessing client buys for or sells from the selected acting puppet through the shop window
- **THEN** exactly one matching `shop.buy` or `shop.sell` names that member, and the committed services, item holdings and party-inventory panels update the rows and party purse without a `possessed_shop` refusal or client-invented balance
