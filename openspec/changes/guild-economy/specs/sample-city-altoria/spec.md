## MODIFIED Requirements

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

## ADDED Requirements

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
