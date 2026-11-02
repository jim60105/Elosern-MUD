# settlement-graph-generation Specification

## Purpose
Generate a settlement local map — footprint, wilderness gates, street nodes and directed roads — deterministically from a location's site context, size budget and archetype role catalogue, so national settlements can be authored in bulk and then refined by hand without breaking the map structure rules.

## Requirements

### Requirement: Generation is deterministic and seeded by location identity
The generator SHALL produce byte-identical settlement YAML for identical terrain, roster, budget, catalogue, forced gates and location identity. It SHALL draw all randomness from a seed derived from the location identifier. It SHALL emit the document through the map-core codec, so the output parses and re-serialises unchanged.

#### Scenario: Repeat runs
- **WHEN** one synthetic generation input is generated twice
- **THEN** both serialised documents are byte-identical, and parsing and re-serialising either one yields the same bytes

#### Scenario: Different identity on the same site
- **WHEN** two location identifiers are generated on otherwise identical synthetic inputs
- **THEN** the two node layouts differ in at least one node coordinate

### Requirement: Morphology follows the site and a dry port is refused
The generator SHALL select a beast-nation ring for beast nations. A port SHALL get a harbour layout when the sea is within reach, or a waterside layout when only a river is within reach. A river within reach SHALL give a crossing layout when one of its fords is also within reach, otherwise a waterside layout. Relief of at least two bands SHALL give a terrace layout, and anything else a crossroads layout. A port with no water within reach SHALL be refused.

#### Scenario: Selection order
- **WHEN** synthetic sites are generated for a beast-nation town beside a river, a port beside the sea, a town beside a river with a ford, a town beside a river without a ford, a town on a slope and a town on flat dry ground
- **THEN** their morphologies are, in order, ring, harbour, crossing, waterside, terraces and crossroads

#### Scenario: Dry port
- **WHEN** a port's nearest water lies beyond its reach distance
- **THEN** generation fails with an error naming the location and the water gap, and nothing is produced

### Requirement: Generated footprints are connected walkable masks centred on the location
A generated footprint SHALL contain the location cell and SHALL be 4-connected and walkable. It SHALL contain no blocked cell and SHALL hold the budgeted cell count plus any water-reach cells. For a waterside, harbour or crossing layout it SHALL touch its water. Its bounding-box midpoint SHALL be a footprint cell, or generation is refused. An offset warning SHALL be reported exactly when that midpoint differs from the location cell.

#### Scenario: Open ground
- **WHEN** a synthetic town with a 5-cell budget is generated on open walkable ground
- **THEN** its footprint has exactly 5 cells, is 4-connected, contains the location cell, and its bounding-box midpoint is the location cell

#### Scenario: Blocked cells and water reach
- **WHEN** another footprint, a harbour cell and a location cell are blocked around a riverside site whose river lies within reach
- **THEN** no blocked cell is in the footprint and at least one footprint cell is 8-adjacent to a river cell

#### Scenario: Unbalanced corridor
- **WHEN** walkable ground around the location allows growth on one side only, in a straight corridor
- **THEN** the footprint is still generated, its midpoint is one of its cells, and the result carries the offset warning

#### Scenario: Midpoint outside the footprint
- **WHEN** the only reachable water lies at the end of an L-shaped corridor, so that the grown mask's bounding-box midpoint falls on an unwalkable cell
- **THEN** generation fails with an error naming the location and `anchor_outside_footprint`, and nothing is produced

### Requirement: Generated graphs satisfy the structure rules and the terrain-fit lint
A generated map SHALL have the budgeted node count and exactly one anchor node at the location cell. Its coordinates SHALL be unique non-negative integers. Every road SHALL be paired with its reverse. No node SHALL have two outgoing roads in one direction or more than six roads. The graph SHALL be connected, with loops up to the tier target, and SHALL pass the terrain-fit lint with no error.

#### Scenario: Structural properties
- **WHEN** synthetic open, riverside and coastal sites are generated
- **THEN** each map satisfies every property above, the loop count equals the tier target or a reported shortfall warning names the deficit, and the terrain-fit lint reports no error

#### Scenario: Directions stay near geometry
- **WHEN** the directed roads of a generated map are inspected
- **THEN** every road direction is one of the eight compass values, and none differs by more than two octants from its segment bearing unless a deviation warning names that node

### Requirement: Gates face their neighbours on distinct walkable approaches
Gate bearings SHALL be taken in this order: forced bearings, then the own capital, then the neighbours nearest first, then fords, then a fixed fallback order. A bearing SHALL be accepted only when its approach cell is walkable, unblocked and unused, up to the budgeted gate count. Each gate's return direction SHALL be the opposite of its bearing, and its node SHALL lie toward that bearing.

#### Scenario: Ordered and skipped bearings
- **WHEN** a synthetic town has the forced bearing `s`, a capital to the north, a neighbour to the east whose approach cell is blocked and a gate budget of 3
- **THEN** its gates use the bearings `s`, `n` and the next fallback bearing, with return directions `n`, `s` and that bearing's opposite, and no gate uses the blocked approach

#### Scenario: Gate nodes face outward
- **WHEN** each gate node's position is compared with the anchor node
- **THEN** the angle between the gate node offset and its gate bearing is at most 90 degrees

### Requirement: Roles come from the catalogue and are placed by the site
Role slots SHALL come only from catalogue entries whose settlement class matches and whose minimum node count the budget reaches, taken in priority order. Water-edge roles SHALL be placed only when the footprint touches the required water, and then within the water-edge limit. High-ground roles SHALL go on the uphill side, and a downstream role SHALL take the most downstream water-edge position.

#### Scenario: Class and budget filter
- **WHEN** a synthetic catalogue holds one entry for another class and one entry whose minimum node count exceeds the budget
- **THEN** neither slot appears in the generated map

#### Scenario: Dry site and water site
- **WHEN** the same water-requiring entry is generated for a site with no water within reach and for a riverside site
- **THEN** the dry site has no such slot, and the riverside slot lies within the water-edge limit of a river cell

#### Scenario: Uphill and downstream
- **WHEN** a site rises to the north and its river flows east
- **THEN** a high-ground slot lies north of the anchor node and the downstream slot is the easternmost of the water-edge candidates

### Requirement: The generator never overwrites and batches in a fixed order
The generator SHALL refuse a location that already has a settlement document and leave every file unchanged. A plan-only run SHALL write nothing. A batch for one nation SHALL generate only national settlements that have no document, in order of descending population and then identifier. Each map SHALL see the footprints written earlier in the same batch.

#### Scenario: Existing document
- **WHEN** generation targets a synthetic location whose settlement document exists
- **THEN** the command exits with status 1 naming the existing file, and the workspace digest is unchanged

#### Scenario: Plan only and batch order
- **WHEN** a plan-only run and then a batch run cover two synthetic national settlements of one nation
- **THEN** the plan-only run leaves the digest unchanged, and the batch writes the larger settlement first, with the second footprint disjoint from the first
