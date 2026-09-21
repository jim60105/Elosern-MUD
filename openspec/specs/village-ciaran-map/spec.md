# village-ciaran-map Specification

## Purpose
Make 暗影谷村 a walkable place — a small concealed elven settlement with its
own coordinate space, anchor and single way in — so settlement abstractions
are exercised against a second, deliberately unlike entry.

## Requirements

### Requirement: The village is a small connected grid with one anchor
`world/maps/village_ciaran.py` SHALL declare map data for
`zcoord="village_ciaran"` describing a ten-node connected tree: a single
entrance node, a central plaza, and eight further exterior nodes reflecting
the branch's culture and dwellings. The plaza SHALL spawn as the settlement's
sole `AnchorRoom`, carrying `anchor_key="village_ciaran"`.

The village SHALL remain a tree as it grows. It SHALL contain no cycle and no
crossroads, because a settlement of a hundred people laid out with the
branching street pattern of a town reads as a town. Growth SHALL add leaves
and short branches, never a loop.

Every intra-village link SHALL spawn as the project's costed grid exit so
movement inside the village charges the ordinary move cost, exactly as
movement inside the capital does.

Room keys and descriptions SHALL be Traditional Chinese and SHALL read as a
lived-in forest settlement rather than as a town: no walls, no gates, no
marketplace and no signed premises.

#### Scenario: The village grid spawns connected with one anchor
- **WHEN** grid synchronization runs
- **THEN** the village's ten rooms exist in its own coordinate space, are
  mutually reachable, and exactly one of them is an `AnchorRoom` whose
  anchor key is the village's

#### Scenario: Village movement is costed like city movement
- **WHEN** a character walks between two village rooms
- **THEN** the move charges the same ordinary cost a capital street move
  charges

#### Scenario: The village occupies a coordinate space of its own
- **WHEN** a coordinate is queried in each settlement's map
- **THEN** the same coordinate resolves to a different room in each, and
  neither settlement's rooms appear in the other's shortest paths

#### Scenario: The village stays a tree as it grows
- **WHEN** the parsed village map's links are counted against its nodes
- **THEN** there is exactly one fewer link than there are nodes, and removing
  any link disconnects the map

#### Scenario: The six original coordinates are undisturbed
- **WHEN** the expanded map is parsed
- **THEN** the entrance, the plaza and the four original dwelling approaches
  occupy exactly the coordinates they occupied before, so no landed place's
  exterior moves

### Requirement: The village has exactly one concealed entrance
The village SHALL have exactly one connection to anything outside it, at its
entrance node, serving both as the arrival point from the starting room and
as the return point from the wilderness.

That entrance SHALL be presented as a concealed path, not a city gate: the
world's elven villages have no walls and no gates, their concealment being
the forest and the villagers themselves. The naming and description SHALL
reflect that even though the entrance occupies the same registry slot a city
gate would.

The connection SHALL be one-way from the starting room, on the same terms
the capital's is: no village room SHALL hold an exit whose destination is
the starting room, and synchronization SHALL prune any such exit on every
run.

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
