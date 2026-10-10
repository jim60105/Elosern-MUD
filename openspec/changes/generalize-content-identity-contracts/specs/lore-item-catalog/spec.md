# Spec Delta

## MODIFIED Requirements

### Requirement: A non-sellable item never reaches a merchant transaction
An item declaring itself non-sellable SHALL NOT be buyable or sellable regardless of how it entered inventory or what price band it names. The refusal SHALL be by the item's own sellability, not by the absence of a shop offer, so an authoring mistake that lists a non-sellable item in a shop cannot open a trade path.

#### Scenario: Selling a non-sellable item is refused
- **WHEN** an entity holding a non-sellable item offers it to a merchant
- **THEN** the sale is refused and neither the wallet nor the inventory changes

#### Scenario: Sellability outranks a shop listing
- **WHEN** a synthetic non-sellable item is introduced through an assortment, place addition or price override
- **THEN** buy and sell still refuse before wallet, inventory, stock, acquisition progress or affinity changes; a valid price band cannot authorize trade

