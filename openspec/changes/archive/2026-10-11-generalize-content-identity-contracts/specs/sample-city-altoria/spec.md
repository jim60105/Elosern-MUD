# Spec Delta

## MODIFIED Requirements

### Requirement: Altoria service content synchronizes idempotently without resetting live state
Startup SHALL create service hosts by stable service identity from every current hosted place declaration, using its authored identity and shared profession blueprint. Repeated sync SHALL update authored descriptions/component definitions without duplicating hosts or resetting initialized merchant stock or mutable identity. Interiors, doorways and exam metadata SHALL retain their existing synchronization contract.

#### Scenario: Fresh startup creates a playable service path
- **WHEN** startup runs on an empty database after grid sync
- **THEN** one interior per current place row and its two doorway exits exist, with exactly the declared service hosts/components and exam metadata before commands are accepted

#### Scenario: Repeated startup creates no duplicates
- **WHEN** guild-economy sync runs twice
- **THEN** object, exit, component-host, and component counts remain unchanged

#### Scenario: Live merchant stock survives content resync
- **WHEN** a player buys an item and startup sync runs again
- **THEN** the decremented stock remains rather than returning to initial stock

#### Scenario: A new specialist shop trades through the ordinary command path
- **WHEN** a player stands in a specialist shop's interior during its opening hours and invokes
  the stock listing and a purchase
- **THEN** the listing names that shop's own interior and every good its assortment carries,
  and the purchase moves goods, wallet and stock through the same deterministic trade APIs
  every other shop uses

#### Scenario: Interiors, doorways, and exam metadata are created exactly once
<!-- The shipped text fixed the surface at ONE merchant NPC, TWO interiors and FOUR doorway
     exits while the place registry already drove two, three and six. altoria-adornments-and-
     remedies adds two more merchant places, so the quantities are restated as registry-driven
     — the idempotence, no-reset and single-creation guarantees elsewhere are unchanged. -->
- **WHEN** guild-economy startup runs against the place registry
- **THEN** it SHALL create one permanent interior and its two directed doorway exits for each
  place-registry row, and exam spawn metadata, exactly once

### Requirement: The sample city's xyzgrid remains thirteen exterior nodes while permanent service interiors are attached
Every notable building referenced by the xyzgrid SHALL remain represented by one exterior
GridRoom in that map. Guild economy SHALL additionally create one ordinary permanent room outside the
xyzgrid node count for each place the settlement's place registry declares, linked bidirectionally from
that place's declared exterior. The number and identity of those interiors SHALL follow the registry
rather than being fixed by this requirement.

#### Scenario: Grid topology is unchanged
- **WHEN** `XYMAP_DATA` is parsed after guild economy lands
- **THEN** it still contains exactly the twenty-one grid nodes and twenty-six links

#### Scenario: Both interiors are reachable and permanent
- **WHEN** map and guild-economy synchronization complete
- **THEN** each interior exists once, has no expiry tick, and can be reached from and exited back to its
  documented exterior

#### Scenario: Interiors do not become xyzgrid nodes
- **WHEN** the XYZGrid map is queried by coordinate
- **THEN** no service interior appears as an additional coordinate or changes shortest paths among
  the grid rooms

#### Scenario: Adding a trading place needs no map edit
- **WHEN** a place is declared against an exterior that already exists in the grid
- **THEN** its interior and doorways appear after synchronization with no change to `XYMAP_DATA`

#### Scenario: Specialist shops do not narrow what the capital sells
- **WHEN** offers across capital places are resolved
- **THEN** each shop exposes precisely its current authored assortment union and allowed place-level additions/removals; no historical roster defines capital availability

#### Scenario: One exterior carries two doors
- **WHEN** two places declare the same exterior with different doorway names
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
- **WHEN** place declarations against grid exteriors are inspected
- **THEN** one exterior MAY carry more than one interior, distinguished by their authored doorway
  names — a craft alley with a forge and a tailor on it is one street with two doors — and some
  exteriors SHALL carry none at all, since a capital contains squares, steps, ruins and quaysides
  that exist to be walked through rather than entered

#### Scenario: Goods are partitioned by shop purpose, not by first stock
- **WHEN** the capital's goods are partitioned among places
- **THEN** the partition follows what a shop is for, not which shop happened to stock an item first

#### Scenario: The accessory-slot partition is exactly two bundles
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
