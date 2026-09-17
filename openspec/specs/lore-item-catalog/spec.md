# lore-item-catalog Specification

## Purpose
Holds the behavioral invariants that follow from an item's declared mechanical shape, independent of which items the world happens to contain: what an item with no mechanics may and may not do, what non-sellability costs, what registration does and does not entitle an item to, and what must hold when an item is retired.

## Requirements

### Requirement: Retiring an item key leaves no dangling reference
An item key that leaves the registry SHALL leave every surface that names items in the same change. Every loader, validator, and registry that can name an item key SHALL fail closed on a key the registry does not define — raising and naming the offending key and its owning surface — rather than skipping the reference, substituting a placeholder, or degrading to an unnamed item. This SHALL hold for shop offered keys and shop offers, equipment modifier bindings and equipment-effect entries, item-effect profiles, starting kits, character presets, and quest objectives and rewards alike, so that a half-completed removal is impossible to ship rather than merely discouraged.

#### Scenario: A shop offer naming a retired key fails the catalog load
- **WHEN** a shop's offered keys or offers name an item key the registry does not define
- **THEN** the catalog load raises naming that key, and no merchant is constructed with a partial inventory

#### Scenario: An equipment binding naming a retired key fails startup
- **WHEN** an equipment-effect entry or modifier binding names an item key the registry does not define
- **THEN** the rulebook load raises naming that key rather than leaving an orphaned entry

#### Scenario: A usable-item profile naming a retired key fails startup
- **WHEN** an item-effect profile names an item key the registry does not define
- **THEN** the two-sided close raises naming that key

#### Scenario: A kit, preset, or quest naming a retired key is rejected
- **WHEN** a starting kit, a character preset, or a quest objective or reward names an item key the registry does not define
- **THEN** its validator rejects that record naming the key, rather than granting nothing or granting an unnamed item

#### Scenario: A completed retirement leaves the catalog closed
- **WHEN** an item key is removed from the registry together with every reference to it
- **THEN** startup succeeds, every loader closes with no unbound key and no orphaned entry, and no surface reports a missing item

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

### Requirement: A usable item's pleasure gain routes through the shared intimacy writer
A usable item declaring a positive pleasure adjustment SHALL settle it through the intimacy system's single shared pleasure writer, so the item's stimulation reaches arousal, wetness, and climax state by the identical path a skill's stimulation does, and the reported amount SHALL be what the gauge actually moved rather than the declared amount. Raising pleasure SHALL require no status definition and no verb beyond the existing gauge adjustment.

#### Scenario: A pleasure gain needs no status vocabulary
- **WHEN** a usable item profile declares a single positive pleasure adjustment scoped to the acting entity
- **THEN** it loads and settles with no status key involved anywhere in the profile

#### Scenario: A device's stimulation drives the same cascade as a skill's
- **WHEN** a usable intimacy device is used by an entity whose pleasure gauge is below its ceiling
- **THEN** the pleasure gauge rises through the shared writer and the arousal-coupled state changes follow, with the applied delta reported as what actually moved

#### Scenario: A device at a full gauge is refused rather than consumed
- **WHEN** a usable intimacy device is used by an entity whose pleasure gauge is already at its ceiling
- **THEN** the use is rejected with the full-gauge reason and the item is not consumed

### Requirement: A non-consuming use settles without spending the item
A usable item may declare that a use does not consume it. Such an item SHALL settle its effects, remain in inventory at the same count, and still incur the ordinary out-of-combat time cost of an item use — that time cost, together with the gauge ceiling that refuses a use with nothing to accomplish, SHALL be the only thing bounding repeated use. A rollback partway through a non-consuming use SHALL restore every surface it touched and SHALL leave the inventory count unchanged.

#### Scenario: A reusable item survives its own use
- **WHEN** an item declared as non-consuming is used successfully out of combat
- **THEN** its effect settles, the item remains in inventory at the same count, and the world clock advances by the standard item-use duration

#### Scenario: A consuming item is spent
- **WHEN** an item declared as consuming is used successfully
- **THEN** exactly one copy is removed from inventory

#### Scenario: A rolled-back reusable use leaves nothing behind
- **WHEN** settlement of a non-consuming use fails partway
- **THEN** every touched gauge, status, and intimate surface is restored and the inventory count is unchanged

### Requirement: An item barred from combat is refused at submission
A usable item declaring that it may not be used in combat SHALL be refused when submitted as a combat action, and the refusal SHALL name the combat restriction rather than a generic failure. No gauge SHALL move and the item SHALL NOT be consumed.

#### Scenario: A combat-barred item cannot be used in a turn
- **WHEN** an item declaring no combat use is submitted as a combat action
- **THEN** the submission is rejected for the combat restriction, no gauge moves, and the item stays in inventory
