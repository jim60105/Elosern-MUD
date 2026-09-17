## Purpose

Binds the shipped item catalog to the lore item codex in `docs/lore/items.md`: which items exist, what identity, presentation, and price band each one carries, and which of them a shop actually stocks. Mechanics capabilities own an item's *shape*; this capability owns the *roster*.

## ADDED Requirements

### Requirement: The catalog roster is derived from the lore item codex
Every registered item SHALL correspond to an entry in the lore item codex, and the codex key SHALL be the registry key verbatim. An item's registered Traditional Chinese display name, closed presentation kind, closed icon key, closed rarity, and price-table key SHALL match what the codex states for that key. The codex, not the registry, SHALL be the source of truth for which items exist; the registry SHALL NOT carry an item the codex does not catalogue.

#### Scenario: A registered item resolves to its codex entry
- **WHEN** any key in the item registry is looked up in the lore item codex
- **THEN** the codex catalogues that key, and the registered display name, kind, icon key, rarity, and price-table key agree with the codex row

#### Scenario: An item absent from the codex is rejected
- **WHEN** a registry entry names a key the codex does not catalogue
- **THEN** the catalog contract test fails and the change cannot ship

### Requirement: Inspect-only catalogue items carry identity without mechanics
The catalog SHALL register the codex's inspect-only roster — the 食物, non-mechanical 藥劑, 工具, 素材, and 雜物 entries — with complete identity and presentation metadata and with neither use mechanics nor an equipment slot. Each SHALL name a price-table key that exists, and each reference price the codex publishes SHALL fall inside that band. A 雜物 entry SHALL be non-sellable and SHALL use the keepsake band, because the codex defines the category as carrying no trade meaning.

#### Scenario: Every inspect-only item is mechanically inert
- **WHEN** each inspect-only catalogue item is inspected
- **THEN** it declares no use mechanics, no equipment slot, and no modifier binding, and it resolves a valid price-table entry

#### Scenario: Curios cannot be traded
- **WHEN** the 雜物 entries are inspected
- **THEN** each is non-sellable and carries the keepsake price band

#### Scenario: A reference price outside its band is rejected
- **WHEN** a catalogue item declares a price band its codex reference price falls outside
- **THEN** the catalog contract test fails before any shop can list it

### Requirement: Regional delicacies price above an ordinary meal
Food SHALL split across two bands: everyday rations stay on the ordinary-meal band, and regional delicacies and refined foods SHALL use a dedicated band whose floor is at or above the ordinary-meal ceiling and whose ceiling does not exceed the lowest equipment-band floor. A delicacy SHALL remain an affordable indulgence rather than a capital purchase: the most expensive food the codex catalogues SHALL cost strictly less than the cheapest equipment it catalogues.

#### Scenario: The two food bands do not overlap downward
- **WHEN** the ordinary-meal band and the delicacy band are compared
- **THEN** the delicacy floor is at or above the meal ceiling, and the delicacy ceiling does not exceed the lowest equipment band floor

#### Scenario: No food outprices a piece of equipment
- **WHEN** the highest catalogued food reference price is compared against the lowest catalogued equipment reference price
- **THEN** the food price is strictly lower

#### Scenario: Every catalogued food fits one of the two bands
- **WHEN** each registered food item's reference buy price is checked against its declared band
- **THEN** the price lies inside that band

### Requirement: Shop stock is a lore decision, not an automatic consequence of registration
A registered item SHALL NOT be stocked by a shop merely because it exists. An item SHALL appear in a shop's offered keys only when the codex's stated provenance and distribution reach that shop. Items the codex marks as gift-only, as having no trade record, or as belonging to a storefront that does not yet exist SHALL be registry-only, remaining inspectable and referenceable by quests, presets, and starting kits without being purchasable.

#### Scenario: Gift-only and untraded goods stay off the shelf
- **WHEN** the general store's offered keys are inspected
- **THEN** 精靈之淚, 精靈體液, and 古龍心臟 are absent, matching the codex statements that the first two reach humans by gift and the third has no trade record

#### Scenario: A registry-only item is still fully usable as data
- **WHEN** a registry-only catalogue item is referenced by a quest objective or a starting kit
- **THEN** the reference resolves against the registry exactly as a stocked item's would

#### Scenario: Stocked items validate against their band
- **WHEN** the general store's offers are loaded
- **THEN** every new offer's buy price lies inside its item's price band, its sell price does not exceed its buy price, and its stock satisfies `0 <= initial <= max` with a positive restock quantity
