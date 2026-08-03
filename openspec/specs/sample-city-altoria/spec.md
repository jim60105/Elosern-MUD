## Purpose

Define the one sample city (聖潔王都 / `capital_altoria`) built as real, walkable xyzgrid rooms and
exits: exactly thirteen rooms in a fixed tree topology, with a single `AnchorRoom` at the central
plaza and one authored bridging exit to non-grid space.

## Requirements


### Requirement: The sample city has exactly thirteen rooms in a fixed, connected topology
`world/maps/altoria_capital.py` SHALL declare `XYMAP_DATA` for `zcoord="capital_altoria"` describing
exactly thirteen rooms at the coordinates: `(2,0)`, `(1,1)`, `(2,1)`, `(3,1)`, `(0,2)`, `(1,2)`,
`(2,2)`, `(3,2)`, `(4,2)`, `(1,3)`, `(2,3)`, `(3,3)`, `(2,4)`, connected by exactly twelve exits with
no cycle (a tree), such that every room is reachable from every other room. The map's declared `options` SHALL contain exactly `map_visual_range`, a positive integer at most 8,
and `map_mode`, one of the closed tokens `nodes` or `scan` — the same closed values the xyzgrid
contrib's own `get_visual_range` accepts. The `webclient-local-map` capability's grid adapter reads
these as the configured grid visual range; an absent, malformed, or out-of-range `options` value SHALL
fail closed to the stable unavailable reason rather than guessing a default. Adding this `options`
entry SHALL NOT change the room or exit topology, count, or connectivity required by this capability.

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

#### Scenario: The map declares bounded visual-range options
- **WHEN** `world/maps/altoria_capital.py`'s `XYMAP_DATA` is inspected
- **THEN** its `options` contains a `map_visual_range` positive integer of at most 8 and a `map_mode`
  equal to `nodes` or `scan`, and parsing the map still yields exactly thirteen nodes and twelve links

#### Scenario: The grid adapter reads the declared options and fails closed on invalid values
- **WHEN** the grid layer adapter runs against the declared `options` and against a malformed or
  out-of-range `options` value
- **THEN** the valid value is used as the visual range, and the invalid value produces the stable
  unavailable reason instead of a guessed default

### Requirement: Exactly one room is the AnchorRoom, at the central plaza
Of the thirteen rooms, exactly one, at coordinate `(2,2)`, SHALL spawn as an `AnchorRoom` with
`anchor_key="capital_altoria"`. The remaining twelve SHALL spawn as plain `GridRoom`.

#### Scenario: Only the plaza is an AnchorRoom
- **WHEN** all thirteen spawned rooms are inspected by typeclass
- **THEN** exactly one, at `(2,2)`, is an `AnchorRoom` instance, and the other twelve are `GridRoom`
  instances that are not `AnchorRoom` instances

### Requirement: The sample city's xyzgrid remains thirteen exterior nodes while permanent service interiors are attached
Every notable building referenced by the thirteen-node xyzgrid SHALL remain represented by one exterior
GridRoom in that map. Guild economy SHALL additionally create exactly two ordinary permanent rooms
outside the xyzgrid node count: `altoria_guild_hall`, linked bidirectionally from the adventurers' guild
exterior, and `altoria_general_store`, linked bidirectionally from the market/blacksmith exterior. The
thirteen grid coordinates, twelve grid links, tree topology, and sole AnchorRoom SHALL remain unchanged.

#### Scenario: Grid topology is unchanged
- **WHEN** `XYMAP_DATA` is parsed after guild economy lands
- **THEN** it still contains exactly the original thirteen grid nodes and twelve tree links

#### Scenario: Both interiors are reachable and permanent
- **WHEN** map and guild-economy synchronization complete
- **THEN** each interior exists once, has no expiry tick, and can be reached from and exited back to its
  documented exterior

#### Scenario: Interiors do not become xyzgrid nodes
- **WHEN** the XYZGrid map is queried by coordinate
- **THEN** neither service interior appears as an additional coordinate or changes shortest paths among
  the thirteen street rooms

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

### Requirement: The sample city's twelve intra-city exits spawn as CostedXYZExit, not the bare contrib XYZExit
`world/maps/altoria_capital.py::XYMAP_DATA["prototypes"]` SHALL include exactly one
wildcard link-prototype override, `("*", "*", "*"): {"prototype_parent": "xyz_exit", "typeclass":
"typeclasses.exits.CostedXYZExit"}`, so that every one of the sample city's twelve intra-city links
spawns as `typeclasses.exits.CostedXYZExit` (the `movement-cost-charging` capability) instead of the
contrib's own bare `evennia.contrib.grid.xyzgrid.xyzroom.XYZExit`. This SHALL NOT change the room or
exit topology, count, or connectivity already required by this capability's other requirements — it
changes only which typeclass each of the twelve links spawns as.

#### Scenario: Every intra-city exit is a CostedXYZExit instance
- **WHEN** `sync_grid()` runs and the sample city's twelve intra-city exits are inspected by typeclass
- **THEN** every one of them is a `typeclasses.exits.CostedXYZExit` instance

#### Scenario: The topology and count required by this capability are unaffected
- **WHEN** the sample city's rooms and exits are inspected after this change lands
- **THEN** exactly thirteen rooms and twelve intra-city exits still exist, in the identical topology
  this capability's other requirements already describe — only the exits' typeclass has changed

#### Scenario: A successful traversal of an intra-city exit advances the clock
- **WHEN** a `PlayerCharacter` successfully traverses any of the sample city's twelve intra-city exits
- **THEN** `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`

### Requirement: Altoria service content synchronizes idempotently without resetting live state
Guild-economy startup SHALL create or update by stable key/tag one adult guild-service NPC with
GuildStaff and GuildExaminer components in the guild hall and one adult Merchant NPC in the general
store. It SHALL create required bidirectional exits and exam spawn metadata exactly once. Repeated sync
SHALL update authored descriptions/component definitions without duplicating objects or resetting
merchant stock that has already been initialized.

#### Scenario: Fresh startup creates a playable service path
- **WHEN** startup runs against an empty database after grid sync
- **THEN** the two interiors, four directed doorway exits, guild service host, merchant host, and exam
  spawn metadata all exist before player commands are accepted

#### Scenario: Repeated startup creates no duplicates
- **WHEN** guild-economy sync runs twice
- **THEN** object, exit, component-host, and component counts remain unchanged

#### Scenario: Live merchant stock survives content resync
- **WHEN** a player buys an item and startup sync runs again
- **THEN** the decremented stock remains rather than returning to initial stock
