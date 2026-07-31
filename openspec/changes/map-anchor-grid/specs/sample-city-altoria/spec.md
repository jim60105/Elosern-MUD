## ADDED Requirements

### Requirement: The sample city has exactly thirteen rooms in a fixed, connected topology
`world/maps/altoria_capital.py` SHALL declare `XYMAP_DATA` for `zcoord="capital_altoria"` describing
exactly thirteen rooms at the coordinates: `(2,0)`, `(1,1)`, `(2,1)`, `(3,1)`, `(0,2)`, `(1,2)`,
`(2,2)`, `(3,2)`, `(4,2)`, `(1,3)`, `(2,3)`, `(3,3)`, `(2,4)`, connected by exactly twelve exits with
no cycle (a tree), such that every room is reachable from every other room.

#### Scenario: The map parses to exactly thirteen nodes
- **WHEN** `world/maps/altoria_capital.py`'s `XYMAP_DATA["map"]` string is parsed with
  `evennia.contrib.grid.xyzgrid.xymap.XYMap.parse()`
- **THEN** exactly thirteen nodes exist, at exactly the coordinates listed above

#### Scenario: Every room is reachable from every other room
- **WHEN** `XYMap.calculate_path_matrix()` is run against the parsed map
- **THEN** a shortest path exists between every pair of the thirteen coordinates

#### Scenario: The topology has no cycle
- **WHEN** the twelve links in the parsed map are inspected
- **THEN** they connect the thirteen nodes with exactly twelve edges, and removing any one edge
  disconnects the graph (a tree, not a graph with a cycle)

### Requirement: Exactly one room is the AnchorRoom, at the central plaza
Of the thirteen rooms, exactly one, at coordinate `(2,2)`, SHALL spawn as an `AnchorRoom` with
`anchor_key="capital_altoria"`. The remaining twelve SHALL spawn as plain `GridRoom`.

#### Scenario: Only the plaza is an AnchorRoom
- **WHEN** all thirteen spawned rooms are inspected by typeclass
- **THEN** exactly one, at `(2,2)`, is an `AnchorRoom` instance, and the other twelve are `GridRoom`
  instances that are not `AnchorRoom` instances

### Requirement: The sample city covers exteriors only, with no building interiors
Every notable building referenced by a room's description (inn, adventurers' guild, temple of light,
blacksmith, noble quarter) SHALL be represented by exactly one exterior `GridRoom`. This change SHALL
NOT add any interior room reachable from a building's exterior.

#### Scenario: No exit leads into a building interior
- **WHEN** every exit spawned by this change's map data is inspected
- **THEN** none leads to a room representing a building's interior — every one of the thirteen rooms
  is a street, gate, plaza, or building exterior

### Requirement: The sample city connects to the rest of the world through exactly one bridging exit
The South Gate room, at `(2,0)`, SHALL be the sample city's sole connection point to non-grid space,
reached via the single bridging `Exit` from Limbo described by the `grid-room-sync` capability. The
North Gate room, at `(2,4)`, SHALL have no exit beyond the one leading back into the city.

#### Scenario: The South Gate is the only room reachable from Limbo
- **WHEN** Limbo's exits are inspected after `sync_grid()` runs
- **THEN** exactly one of them leads into the `capital_altoria` map, and it leads to `(2,0)`

#### Scenario: The North Gate is a dead end, reserved for a future wilderness link
- **WHEN** the North Gate room's exits are inspected
- **THEN** its only exit is the one leading south back to `(2,3)`; it has no other exit, and no
  `WildernessMapProvider` or other non-grid destination is referenced anywhere in this change's map
  data
