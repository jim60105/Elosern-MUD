# Spec Delta

## ADDED Requirements

### Requirement: Ciaran uses metric skylit underground geography
Ciaran SHALL retain its ten-node nine-road branching topology at the following meter positions, with roughly 0.4km² living space for 100 elves. Main living chambers SHALL remain underground; outdoor nodes SHALL occupy skylit collapse basins or ravines, retaining the concealed path without walls or city gates.

#### Scenario: Exact metric positions
- **WHEN** village nodes synchronize
- **THEN** old-to-new bindings equal this table, without collisions or compass-octant changes.

| Location | Old local coordinate | New local coordinate, meters |
| --- | --- | --- |
| 隱密小徑 | (0, 1) | (35, 270) |
| 村中廣場 | (1, 1) | (220, 305) |
| 溪畔小徑 | (1, 0) | (245, 135) |
| 溪畔下游 | (2, 0) | (430, 85) |
| 練刀場 | (2, 1) | (405, 335) |
| 藥草園 | (3, 1) | (590, 300) |
| 村北古樹下 | (1, 2) | (200, 465) |
| 長老古樹下 | (1, 3) | (165, 650) |
| 織房坡 | (2, 2) | (390, 495) |
| 銀葉坡 | (2, 3) | (440, 665) |



#### Scenario: Underground setting and route
- **WHEN** the village and entrance-to-elder route are inspected
- **THEN** surrounding forest/gathering land lies beyond the living footprint, daylight/trees occur at openings, the village is never an ordinary exposed forest settlement, and the healthy straight-edge route is approximately seven minutes.

## MODIFIED Requirements

### Requirement: The village is a small connected grid with one anchor
`world/maps/village_ciaran.py` SHALL declare map data for
`zcoord="village_ciaran"` describing a ten-node connected tree: a single
entrance node, a central plaza, and eight further exterior nodes reflecting
the branch's culture and dwellings. The plaza SHALL spawn as the settlement's
sole `AnchorRoom`, carrying `anchor_key="village_ciaran"`. Every
intra-village link SHALL spawn as the project's costed grid exit so
movement inside the village charges the distance-derived move cost.

#### Scenario: The village grid spawns connected with one anchor
- **WHEN** grid synchronization runs
- **THEN** the village's ten rooms exist in its own coordinate space, are
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

#### Scenario: The six original coordinates are undisturbed
- **WHEN** the expanded map is parsed
- **THEN** the entrance, the plaza and the four original dwelling approaches
  occupy the approved meter coordinates while their existing dbids and every landed place attachment remain intact

#### Scenario: Growth adds leaves, never a loop or crossroads
- **WHEN** the village map grows
- **THEN** it remains a tree with no cycle and no crossroads — growth adds
  leaves and short branches, never a loop — because a settlement of a
  hundred people laid out with the branching street pattern of a town reads
  as a town

#### Scenario: Village text reads as a lived-in forest settlement
- **WHEN** the village's room keys and descriptions are authored
- **THEN** they SHALL be Traditional Chinese and SHALL read as a lived-in
  underground settlement with skylit basins and ravines: no walls, no city gates, no
  marketplace and no signed premises

### Requirement: The village has exactly one concealed entrance
The village SHALL have exactly one connection to anything outside it, at its
entrance node, serving both as the arrival point from the starting room and
as the return point from the wilderness.

#### Scenario: The village is reachable from the starting room
- **WHEN** the starting room's exits are inspected after grid
  synchronization
- **THEN** one of them leads into the village's entrance node

#### Scenario: No village room leads back to the starting room
- **WHEN** every exit of every spawned village room is inspected after grid
  synchronization
- **THEN** none has the starting room as its destination

#### Scenario: The entrance does not read as a gate
- **WHEN** the entrance node's key and description are read
- **THEN** they describe a concealed path through the forest, and name no
  wall, gate or guard

#### Scenario: A concealed path occupies the city-gate registry slot
- **WHEN** the entrance is registered in the slot a city gate would occupy
- **THEN** its naming and description SHALL still present a concealed path,
  not a city gate: the world's elven villages have no walls and no gates,
  their concealment being the forest and the villagers themselves

#### Scenario: Synchronization prunes any exit back to the starting room
- **WHEN** grid synchronization runs and any village room holds an exit whose
  destination is the starting room
- **THEN** synchronization SHALL prune that exit on every run, keeping the
  connection one-way from the starting room on the same terms the capital's
  is

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
