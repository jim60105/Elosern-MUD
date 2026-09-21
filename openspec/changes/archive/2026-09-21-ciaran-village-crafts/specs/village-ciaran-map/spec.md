## MODIFIED Requirements

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
