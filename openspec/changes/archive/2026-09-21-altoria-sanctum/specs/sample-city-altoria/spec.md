## MODIFIED Requirements

### Requirement: The sample city's xyzgrid remains thirteen exterior nodes while permanent service interiors are attached
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
stock an item first. In particular the capital's accessory-slot goods SHALL be carved across
exactly two bundles — the adornments bundle and the sanctum bundle (altoria-sanctum: the wearable
devices the sanctum's own counter supplies) — and every accessory-slot good the capital sells
SHALL sit in one of those two and nowhere else: an accessory-slot good the capital sells and
both bundles omit is a gap in the partition, and a non-accessory good inside either is a leak.
Stating the rule as a set equality rather than a hand-listed inventory is what keeps the next
item added to the capital from landing on whichever shelf is nearest.

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
- **THEN** the set equals the set the single general store offered before the split, plus
  exactly the goods a later change has deliberately added to the capital (altoria-sanctum's
  twelve intimacy goods), with no key offered by two places

#### Scenario: One exterior carries two doors
- **WHEN** two places declare the same exterior with different doorway names
- **THEN** both interiors exist, that exterior holds one doorway exit per place, and each interior
  leads back to it

#### Scenario: The accessory bundles together are exactly the accessory-slot goods
- **WHEN** the capital's offered goods are partitioned by equipment slot
- **THEN** the set of accessory-slot keys the capital sells equals the union of the adornments
  and sanctum bundles' accessory keys exactly, disjointly, with no accessory-slot key left in
  another capital bundle

#### Scenario: Moving a good between shelves does not change its price
- **WHEN** an item's resolved offer is compared before and after it moves from one capital
  bundle to another
- **THEN** its buy copper, sell copper, stock cap, initial stock and restock quantity are
  unchanged
