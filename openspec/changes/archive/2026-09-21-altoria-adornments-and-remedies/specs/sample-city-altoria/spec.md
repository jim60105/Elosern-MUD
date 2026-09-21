## MODIFIED Requirements

### Requirement: The sample city's xyzgrid remains thirteen exterior nodes while permanent service interiors are attached
<!-- Requirement name retained verbatim; the count it names is stale, the text is current.
     This block is written against the text `altoria-capital-replan` leaves behind and MUST be
     archived after it. -->
Every notable building referenced by the xyzgrid SHALL remain represented by one exterior
GridRoom in that map. Guild economy SHALL additionally create one ordinary permanent room outside the
xyzgrid node count for each place the settlement's place registry declares, linked bidirectionally from
that place's declared exterior. The number and identity of those interiors SHALL follow the registry
rather than being fixed by this requirement.

One exterior MAY carry more than one interior, distinguished by their authored doorway names: a
craft alley with a forge and a tailor on it is one street with two doors. Some exteriors SHALL
carry none at all — a capital contains squares, steps, ruins and quaysides that exist to be walked
through rather than entered.

The capital's goods SHALL be partitioned by what a shop is for, not by which shop happened to
stock an item first. In particular the adornments bundle SHALL hold exactly those capital goods
that equip to the accessory slot: an accessory-slot good the capital sells and the adornments
bundle omits is a gap in the partition, and a non-accessory good inside it is a leak. Stating the
rule as a set equality rather than a hand-listed inventory is what keeps the next item added to
the capital from landing on whichever shelf is nearest.

The grid coordinates, grid links, cycle count and sole AnchorRoom SHALL remain unchanged by
interior attachment.

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
- **WHEN** the goods offered across every capital place are collected
- **THEN** the set equals the set the single general store offered before the split, with no key
  offered by two places

#### Scenario: One exterior carries two doors
- **WHEN** two places declare the same exterior with different doorway names
- **THEN** both interiors exist, that exterior holds one doorway exit per place, and each interior
  leads back to it

#### Scenario: The adornments bundle is exactly the accessory-slot goods
- **WHEN** the capital's offered goods are partitioned by equipment slot
- **THEN** the set of accessory-slot keys the capital sells equals the adornments bundle's key
  set exactly, with no accessory-slot key left in another capital bundle

#### Scenario: Moving a good between shelves does not change its price
- **WHEN** an item's resolved offer is compared before and after it moves from one capital
  bundle to another
- **THEN** its buy copper, sell copper, stock cap, initial stock and restock quantity are
  unchanged

### Requirement: Altoria service content synchronizes idempotently without resetting live state
<!-- The shipped text fixed the surface at ONE merchant NPC, TWO interiors and FOUR doorway
     exits while the place registry already drove two, three and six. altoria-adornments-and-
     remedies adds two more merchant places, so the quantities are restated as registry-driven
     — the idempotence, no-reset and single-creation guarantees below are unchanged. -->
Guild-economy startup SHALL create or update by stable key/tag one guild-service NPC with
GuildStaff and GuildExaminer components in the guild hall and one Merchant NPC in the interior
of every merchant place the settlement's place registry declares. It SHALL create one permanent
interior and its two directed doorway exits for each place-registry row, and exam spawn
metadata, exactly once. Repeated sync SHALL update authored descriptions/component definitions
without duplicating objects or resetting merchant stock that has already been initialized.

#### Scenario: Fresh startup creates a playable service path
- **WHEN** startup runs against an empty database after grid sync
- **THEN** one interior per place-registry row exists, reached by two directed doorway exits
  from its exterior, alongside the guild service host, one merchant host per merchant place,
  and exam spawn metadata — all before player commands are accepted

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
