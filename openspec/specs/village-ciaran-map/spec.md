# village-ciaran-map Specification

## Purpose
Make 暗影谷村 a walkable place, a small concealed elven settlement with its
own coordinate space, anchor and single way in, so settlement abstractions
are exercised against a second, deliberately unlike entry.

## Requirements

### Requirement: The village is a small connected grid with one anchor
The village settlement document SHALL define a connected branching graph in its own metre coordinate space with one anchor and costed directed travel, retaining its existing identities and attachments.

#### Scenario: The village grid spawns connected with one anchor
- **WHEN** grid synchronization runs
- **THEN** the village's declared rooms exist in its own coordinate space, are
  mutually reachable, and exactly one of them is an `AnchorRoom` whose
  anchor key is the village's

#### Scenario: Village movement is costed like city movement
- **WHEN** a character walks between two village rooms
- **THEN** the move charges its actual physical edge cost at the same baseline speed as capital streets

#### Scenario: The village occupies a coordinate space of its own
- **WHEN** a coordinate is queried in each settlement's map
- **THEN** the same coordinate resolves to a different room in each, and
  neither settlement's rooms appear in the other's shortest paths

#### Scenario: The village stays a tree as it grows
- **WHEN** the validated sparse village graph's links are counted against its nodes
- **THEN** there is exactly one fewer link than there are nodes, and removing
  any link disconnects the map

#### Scenario: Existing location identities are undisturbed
- **WHEN** the expanded map is parsed
- **THEN** the entrance, the plaza and the existing dwelling approaches
  occupy the approved meter coordinates while their existing dbids and every landed place attachment remain intact

#### Scenario: Growth preserves branching paths without loops
- **WHEN** the village map grows
- **THEN** it remains a tree with no cycle; growth adds leaves and short
  branches around the declared gathering places, without turning the village
  into a town-like street network

#### Scenario: Village text reads as a lived-in forest settlement
- **WHEN** the village's room keys and descriptions are authored
- **THEN** they SHALL be Traditional Chinese and SHALL read as a lived-in
  underground settlement with skylit basins and ravines: no walls, no city gates, no
  marketplace and no signed premises

### Requirement: The village has a wilderness footprint disjoint from every other settlement
The village SHALL declare a wilderness footprint and at least one gate
returning to its entrance node, so a traveller crossing the wilderness can
reach it.

Its footprint SHALL NOT overlap another settlement's footprint, and its
gate's approach cell and direction SHALL NOT duplicate another settlement's.
These rules already exist in the registry's validation; this is the first
entry that gives them a second entry to check against.

#### Scenario: Two settlements' footprints are disjoint
- **WHEN** the footprint cells of every registered settlement are collected
- **THEN** no cell belongs to two settlements, and no settlement's footprint
  cell is another's gate approach cell

#### Scenario: Gate identity stays globally unique with two settlements
- **WHEN** the approach cell and return direction of every registered gate
  are collected
- **THEN** no pair occurs twice

#### Scenario: The village is reachable from the wilderness
- **WHEN** a traveller stands on the village's gate approach cell and moves
  in the gate's return direction
- **THEN** they arrive at the village's entrance node

### Requirement: Ciaran uses metric skylit underground geography
Village geometry SHALL use integer metres from its settlement document while retaining branching topology, qualified attachments and the separation of physical map data from non-map lore.

#### Scenario: Metric identity preservation
- **WHEN** the existing village map is converted or a bound node is moved
- **THEN** node IDs, directions and room joins remain stable without inferring a new exit from coordinates; existing prose/population remain unchanged by conversion

#### Scenario: Exact metric positions
- **WHEN** a synthetic branching village document is loaded and a node is moved
- **THEN** its integer-metre binding changes without coordinate collision, ID change or a recomputed authored compass direction

#### Scenario: Underground setting and route
- **WHEN** the village source is converted and a source-defined route is measured
- **THEN** existing prose and concealed-entry semantics remain unchanged and route length uses its metre edges; underground setting fidelity is human-reviewed without a copied prose/duration approval table

### Requirement: The village's only outside connection is its concealed wilderness entrance
The village SHALL connect to anything outside it only at its entrance node, which is the return point from the wilderness. No village room SHALL hold an exit into the starting room or receive one from it, and the entrance node SHALL read as a concealed path, not a gate.

#### Scenario: The starting room does not reach the village
- **WHEN** every exit located in the starting room or in a spawned village room is inspected after grid synchronization
- **THEN** none of them joins the starting room and the village

#### Scenario: The entrance does not read as a gate
- **WHEN** the entrance node's key and description are read
- **THEN** they describe a concealed path through the forest, and name no wall, gate or guard

#### Scenario: The wilderness returns to the entrance node
- **WHEN** the village's wilderness entry gates are read
- **THEN** every gate destination is the entrance node
