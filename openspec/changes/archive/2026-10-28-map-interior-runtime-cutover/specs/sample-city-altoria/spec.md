# Spec Delta

## MODIFIED Requirements

### Requirement: The sample city's declared exterior topology remains unchanged while permanent service interiors are attached
Map-owned permanent interiors SHALL attach by qualified relationships without becoming settlement grid nodes or changing exterior topology; service/goods behavior remains service-owned.

#### Scenario: Grid topology is unchanged
- **WHEN** the sparse map declaration is parsed after map-owned interiors lands
- **THEN** it still contains the declared exterior nodes and roads, without service interiors becoming grid nodes

#### Scenario: Declared interiors are reachable and permanent
- **WHEN** map and guild-economy synchronization complete
- **THEN** each interior exists once, has no expiry tick, and can be reached from and exited back to its
  documented exterior

#### Scenario: Interiors do not become xyzgrid nodes
- **WHEN** the XYZGrid map is queried by coordinate
- **THEN** no service interior appears as an additional coordinate or changes shortest paths among
  the grid rooms

#### Scenario: Adding a trading place needs no map edit
- **WHEN** an interior relationship is declared against an exterior that already exists in the grid
- **THEN** its interior and doorways appear after synchronization with no change to the sparse map declaration

#### Scenario: Specialist shops do not narrow what the capital sells
- **WHEN** offers across capital places are resolved
- **THEN** each shop exposes its current authored assortment union and allowed place-level additions/removals; no historical roster defines capital availability

#### Scenario: One exterior carries two doors
- **WHEN** two interior relationships declare the same exterior with different doorway names
- **THEN** both interiors exist, that exterior holds one doorway exit per place, and each interior
  leads back to it

#### Scenario: The accessory bundles together are exactly the accessory-slot goods
- **WHEN** capital specialist assortment policies are validated
- **THEN** every offered accessory obeys its declared shelf eligibility; no fixed named two-bundle membership is required

#### Scenario: Moving a good between shelves does not change its price
- **WHEN** an item's resolved offer is compared before and after it moves from one capital
  bundle to another
- **THEN** its buy copper, sell copper, stock cap, initial stock and restock quantity are
  unchanged

#### Scenario: An exterior may carry several doors or none
- **WHEN** interior relationship declarations against grid exteriors are inspected
- **THEN** one exterior MAY carry more than one interior, distinguished by their authored doorway
  names (a craft alley with a forge and a tailor on it is one street with two doors), and some
  exteriors SHALL carry none at all, since a capital contains squares, steps, ruins and quaysides
  that exist to be walked through rather than entered

#### Scenario: Goods are partitioned by shop purpose, not by first stock
- **WHEN** the capital's goods are partitioned among places
- **THEN** the partition follows what a shop is for, not which shop happened to stock an item first

#### Scenario: The accessory-slot partition follows the declared bundles
- **WHEN** accessory goods are assigned to authored specialist shelves
- **THEN** every assignment follows explicit registry-owned shop-purpose and eligible-slot declarations; the number and identity of bundles are data

#### Scenario: An omitted accessory good is a gap; a non-accessory good is a leak
- **WHEN** an offer references missing item data or violates its declared shelf eligibility
- **THEN** validation rejects the missing reference or slot/kind mismatch, naming shop, assortment and item

#### Scenario: The partition is stated as a set equality, not a hand-listed inventory
- **WHEN** resolved shop membership is checked
- **THEN** membership equals the authored union plus additions minus removals, without an approved item-list snapshot

#### Scenario: Interior attachment leaves grid coordinates, cycles, and the AnchorRoom unchanged
- **WHEN** service interiors are attached
- **THEN** the grid coordinates, grid links, cycle count and sole AnchorRoom SHALL remain unchanged
  by interior attachment

