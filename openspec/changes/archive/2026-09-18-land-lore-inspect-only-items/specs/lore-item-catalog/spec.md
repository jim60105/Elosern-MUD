## ADDED Requirements

### Requirement: An item declaring no mechanics is inert
An item that declares neither use mechanics nor an equipment slot SHALL be holdable, inspectable, and — when sellable and stocked — tradeable, and SHALL refuse every mechanical interaction with a stable named reason rather than a generic failure. Using such an item SHALL be refused for having no use mechanics; equipping it SHALL be refused for not being equipment. Neither refusal SHALL move a gauge, consume the item, or mutate inventory.

#### Scenario: Using an inert item is refused by name
- **WHEN** an entity uses an item that declares no use mechanics
- **THEN** the attempt is refused with the not-usable reason, the item stays in inventory, and no gauge changes

#### Scenario: Equipping an inert item is refused by name
- **WHEN** an entity equips an item that declares no equipment slot
- **THEN** the attempt is refused with the not-equipment reason and the equipment state is unchanged

#### Scenario: An inert item is still a first-class inventory object
- **WHEN** an inert item is held and inspected
- **THEN** its display name, presentation, and summary resolve exactly as a mechanically active item's do

### Requirement: A non-sellable item never reaches a merchant transaction
An item declaring itself non-sellable SHALL NOT be buyable or sellable regardless of how it entered inventory or what price band it names. The refusal SHALL be by the item's own sellability, not by the absence of a shop offer, so an authoring mistake that lists a non-sellable item in a shop cannot open a trade path.

#### Scenario: Selling a non-sellable item is refused
- **WHEN** an entity holding a non-sellable item offers it to a merchant
- **THEN** the sale is refused and neither the wallet nor the inventory changes

#### Scenario: Sellability outranks a shop listing
- **WHEN** a shop's offers list a non-sellable item key
- **THEN** buying and selling it are still refused

### Requirement: Registration does not entitle an item to a market
A registered item SHALL NOT become purchasable merely by existing. An item no shop offers SHALL remain fully functional through every non-shop path — granted into inventory, held, inspected, equipped if it is equipment, used if it is usable, and named by a quest objective, a starting kit, a preset, or a generated scenario. No loader, validator, or startup check SHALL treat "registered but offered nowhere" as an incomplete or invalid state.

#### Scenario: An unstocked item is fully usable when granted
- **WHEN** a registered item that no shop offers is placed in an entity's inventory by a non-shop path
- **THEN** it inspects, equips, or is used exactly as a stocked item of the same shape would

#### Scenario: An unstocked item cannot be bought
- **WHEN** an entity attempts to buy a registered item that the local merchant does not offer
- **THEN** the purchase is refused for the item not being offered, distinct from the refusal an unknown key produces

#### Scenario: Startup accepts a catalog with unstocked items
- **WHEN** the registries and rulebooks load with registered items that no shop offers
- **THEN** startup succeeds and no validator reports a missing offer
