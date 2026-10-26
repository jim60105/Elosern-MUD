# Spec Delta

## MODIFIED Requirements

### Requirement: The sample city has the declared rooms in a connected sparse topology
The capital settlement document SHALL define stable node identities, prototypes, bounded visual options and a connected sparse directed graph with its authored cycles and diagonal shortcuts.

#### Scenario: The map parses to the declared nodes
- **WHEN** `content/maps/settlements/capital_altoria.yaml`'s sparse node/road declaration is parsed with
  the sparse graph validator
- **THEN** its nodes match the declared identities, prototypes, and metric coordinates without omissions or duplicates

#### Scenario: Every room is reachable from every other room
- **WHEN** sparse shortest-path calculation is run against the validated sparse graph
- **THEN** a shortest path exists between every pair of declared nodes

#### Scenario: The topology contains cycles
- **WHEN** the roads in the validated sparse graph are inspected
- **THEN** they match the settlement document's declaration, and at least one pair of rooms has distinct routes between them

#### Scenario: The map declares bounded visual-range options
- **WHEN** `content/maps/settlements/capital_altoria.yaml`'s sparse map declaration is inspected
- **THEN** its `options` contains a `map_visual_range` positive integer of at most 8 and a `map_mode`
  equal to `nodes` or `scan`, and parsing the map still yields the declared nodes and roads

#### Scenario: The grid adapter reads the declared options and fails closed on invalid values
- **WHEN** the grid layer adapter runs against the declared `options` and against a malformed or
  out-of-range `options` value
- **THEN** the valid value is used as the visual range, and the invalid value produces the stable
  unavailable reason instead of a guessed default

#### Scenario: The declared topology is authoritative
- **WHEN** authored rooms or roads change
- **THEN** synchronization follows the settlement document rather than a historical count in specification prose

#### Scenario: The topology is not a tree
- **WHEN** the topology is evaluated
- **THEN** it SHALL contain cycles and authored diagonal shortcuts

#### Scenario: The cycles and diagonals are load-bearing world-building
- **WHEN** the cycles and diagonals are justified as world-building rather than incidentals
- **THEN** a city in which every route between two points is the only route is a corridor; the
  cycles are the ring of the old wall the city outgrew and the blocks the pilgrim road divides, and
  the diagonals are the shortcuts foot traffic wears into a city that grew rather than one that was
  laid out

#### Scenario: The options set is exactly the two visual-range tokens
- **WHEN** the map's declared `options` are inspected
- **THEN** they SHALL contain exactly `map_visual_range`, a positive integer at most 8, and
  `map_mode`, one of the closed tokens `nodes` or `scan`, the same closed values the xyzgrid
  contrib's own `get_visual_range` accepts

#### Scenario: The grid adapter reads the options as the configured visual range
- **WHEN** the `webclient-local-map` capability's grid adapter reads the declared `options`
- **THEN** it reads them as the configured grid visual range

#### Scenario: Invalid options fail closed
- **WHEN** an `options` value is absent, malformed, or out of range
- **THEN** the adapter SHALL fail closed to the stable unavailable reason rather than guessing a
  default

#### Scenario: Adding the options entry leaves the topology untouched
- **WHEN** this `options` entry is added to the map
- **THEN** it SHALL NOT change the room or exit topology, count, or connectivity required by this
  capability

### Requirement: The sample city's declared intra-city exits spawn as CostedXYZExit
Every declared capital road SHALL spawn as a costed grid exit using its YAML exit prototype without changing topology, including diagonal travel.

#### Scenario: Every intra-city exit is a CostedXYZExit instance
- **WHEN** `sync_grid()` runs and the sample city's intra-city exits are inspected by typeclass
- **THEN** every one of them is a `typeclasses.exits.CostedXYZExit` instance, diagonals included

#### Scenario: The topology and count required by this capability are unaffected
- **WHEN** the sample city's rooms and exits are inspected after this change lands
- **THEN** the declared rooms and roads still exist, in the identical
  topology this capability's other requirements already describe; only the exits' typeclass has
  changed

#### Scenario: A successful traversal of an intra-city exit advances the clock
- **WHEN** a `PlayerCharacter` successfully traverses any of the sample city's intra-city exits
- **THEN** `get_world_clock().tick` increases by exactly the resolved physical edge duration

#### Scenario: Every declared travel direction has a costed exit
- **WHEN** the settlement document's roads are synchronized
- **THEN** each directed road has a costed exit, without a specification-owned exit count

#### Scenario: The override changes only the spawned typeclass, not the topology
- **WHEN** the prototype override is evaluated against this capability's other requirements
- **THEN** it SHALL NOT change the room or exit topology, count, or connectivity already required
  by this capability's other requirements; it changes only which typeclass each link spawns as

#### Scenario: The override covers diagonals exactly as cardinals
- **WHEN** the wildcard link-prototype override's coverage is inspected
- **THEN** it SHALL cover diagonal links exactly as it covers cardinal ones

### Requirement: Altoria uses approved metric outdoor positions
Capital node positions SHALL be integer metres from the settlement document, with stable identities, authored direction choices, roads/cycles/shortcuts and current interior attachments preserved during source conversion.

#### Scenario: Metric source conversion
- **WHEN** the existing capital declaration is converted without an authoring edit
- **THEN** temporary comparison confirms no geography/topology/prose change and permanent tests establish unit, identity and consumer behavior without a duplicated coordinate approval table

