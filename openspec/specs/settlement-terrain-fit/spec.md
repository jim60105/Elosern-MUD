# settlement-terrain-fit Specification

## Purpose
Derive a settlement's coarse terrain context and research-based size budget from authored terrain and lore inputs, and lint authored settlement maps for terrain fit in world coordinates, so that generated and hand-edited street graphs stay consistent with the continent they stand on.

## Requirements

### Requirement: Site context derives water, relief and neighbour bearings from terrain
The site analysis SHALL derive, for one settlement location and search radius, each waterway and the sea within the radius with distance and 8-way bearing, a river's downstream bearing from its source-to-mouth route order, fords, harbour sites, the uphill bearing and relief, the nearest other settlements and the bearing to the settlement's own capital, using only the terrain and location inputs it is given.

#### Scenario: River contact with flow
- **WHEN** a synthetic window holds a location at cell (10,10) and a river whose route runs from (13,20) to (13,0)
- **THEN** the river contact names that river with distance 3 cells, bearing `e` and downstream bearing `s`

#### Scenario: Sea contact and absent water
- **WHEN** every cell with x of 6 or less is sea, and a second synthetic window has no sea and no waterway within the radius
- **THEN** the first site's sea contact has distance 4 cells and bearing `w`, and the second site has no river contact and no sea contact

#### Scenario: Uphill bearing and flat ground
- **WHEN** elevation bands rise by one per row northward around the location, and separately all bands are equal
- **THEN** the first site's uphill bearing is `n` with a relief equal to the band range in the relief radius, and the flat site has no uphill bearing and a relief of 0

#### Scenario: Neighbours and capital bearing
- **WHEN** three other national settlements lie at known offsets and one of them is the location's nation capital
- **THEN** the neighbours are listed nearest first, with ties broken by identifier, the capital bearing is that capital's 8-way bearing, and a capital's own site has no capital bearing

### Requirement: Size budget follows the population-area relation with a multi-cell floor
The size budget SHALL compute built-up area as the reference area times (population divided by the reference population) raised to the configured exponent. Footprint cells SHALL be the larger of two and the area rounded up in square kilometres. The envelope radius SHALL be that of a circle of that area. Node, gate and loop targets SHALL come from the supplied tier tables. Unsupported kinds and non-positive populations SHALL be rejected.

#### Scenario: Area scales by the configured exponent
- **WHEN** a synthetic configuration with reference population 10,000, reference density 100 inhabitants per hectare and exponent 0.5 is applied to population 40,000
- **THEN** the built-up area is exactly 2 km², the footprint is 2 cells and the envelope radius is the rounded metre radius of a 2 km² circle

#### Scenario: Multi-cell floor
- **WHEN** a population yields 0.3 km² and another yields 3.2 km²
- **THEN** their footprints are 2 and 4 cells; no supported settlement ever receives a single-cell footprint

#### Scenario: Tier tables
- **WHEN** a synthetic tier table is applied at, just below and just above each population boundary, and a capital-kind location is applied at a small population
- **THEN** each boundary is inclusive of its lower bound, and the capital receives the capital node, gate and loop targets regardless of population

#### Scenario: Rejected inputs
- **WHEN** the budget is requested for an `elven_village` or `dungeon` kind, or for a population of 0 or none
- **THEN** it is rejected with an error naming the location and no budget is produced

### Requirement: Terrain-fit lint flags dry water-edge roles and unbridged crossings
The terrain-fit lint SHALL report an error for a node whose identifier carries a water-edge word and lies farther than the water-edge limit from inland water or sea. It SHALL also report an error for a road whose world-metre polyline enters an inland-water or sea cell while neither endpoint carries a crossing word. Words are whole underscore-separated tokens, and ford cells never count as water.

#### Scenario: Water-edge distance
- **WHEN** a synthetic settlement has a `quay` node 300 m from a river cell edge and a `riverbank_road` node 1,500 m from any water
- **THEN** only the `riverbank_road` node is reported, with the error code for a dry water-edge role

#### Scenario: Crossing words
- **WHEN** one road crosses a river cell between two plain nodes, a second crosses it from a `bridge` node, and a third passes over a ford cell
- **THEN** only the first road is reported as an unbridged crossing

#### Scenario: Whole-word tokens
- **WHEN** node identifiers `quayside` and `old_ford_lane` are checked
- **THEN** `quayside` carries no water-edge word and `old_ford_lane` carries the crossing word `ford`

### Requirement: Terrain-fit lint checks footprint, water, gate side and gate approach
For a multi-cell footprint, the lint SHALL report an error for a node outside every footprint cell and for a gate whose approach cell is not walkable. It SHALL report a warning for a gate node lying more than 90 degrees from its gate's outward bearing. For every settlement it SHALL report an error for a node standing in a water or sea cell. A single-cell concealed entry SHALL skip the footprint and gate-side checks.

#### Scenario: Multi-cell containment and water
- **WHEN** a synthetic two-cell footprint has one node inside it, one node in an adjacent land cell and one node in a river cell
- **THEN** the adjacent-cell node is reported as outside the footprint, and the river-cell node is reported as standing in water

#### Scenario: Gate side and approach
- **WHEN** a gate whose outward bearing is east targets a node west of the anchor node, and a second gate's approach cell is a ridge cell
- **THEN** the first gate yields a warning and the second yields an error

#### Scenario: Concealed point entry
- **WHEN** a single-`#` entry has nodes outside its one cell and a gate node on any side
- **THEN** no containment or gate-side finding is reported, and nodes in water are still reported

### Requirement: Road direction drift is a warning
The lint SHALL report a warning, never an error, for a road whose authored direction differs by more than one octant from the 8-way bearing of its first polyline segment. It SHALL NOT change any direction.

#### Scenario: Drifted and adjacent directions
- **WHEN** a road whose first segment points due east is authored `e`, a second is authored `ne` and a third is authored `n`
- **THEN** only the third road yields the direction-drift warning and the document is unchanged

### Requirement: The fit commands are read-only and report by exit status
The site, budget and lint commands SHALL read the workspace and the lore inputs without writing any file. Each finding SHALL be printed with its code, severity, map and object. The lint SHALL exit 0 when no error-severity finding exists, 1 when any exists, and 2 when the map sources do not load.

#### Scenario: Synthetic workspace runs
- **WHEN** the lint runs on a synthetic workspace that is clean, then after a dry water-edge node is added, then after a structure error is introduced
- **THEN** the exit statuses are 0, 1 and 2, and the workspace file digests are identical before and after every run
