# Spec Delta

## MODIFIED Requirements

### Requirement: Terrain-fit lint checks footprint, water, gate side and gate approach
For a physical footprint of one or more cells, the lint SHALL report an error for a node outside every footprint cell and for a gate whose approach cell is not walkable. It SHALL report a warning for a gate node lying more than 90 degrees from its gate's outward bearing. For every settlement it SHALL report an error for a node standing in a water or sea cell. A single-cell concealed entry SHALL skip the footprint and gate-side checks.

#### Scenario: Multi-cell containment and water
- **WHEN** a synthetic two-cell footprint has one node inside it, one node in an adjacent land cell and one node in a river cell
- **THEN** the adjacent-cell node is reported as outside the footprint, and the river-cell node is reported as standing in water

#### Scenario: Gate side and approach
- **WHEN** a gate whose outward bearing is east targets a node west of the anchor node, and a second gate's approach cell is a ridge cell
- **THEN** the first gate yields a warning and the second yields an error

#### Scenario: Concealed point entry
- **WHEN** a single-`#` entry has nodes outside its one cell and a gate node on any side
- **THEN** no containment or gate-side finding is reported, and nodes in water are still reported

#### Scenario: One-cell physical footprint
- **WHEN** a single-`#` entry declared as a physical footprint has one node in an adjacent land cell and a gate whose approach cell is a ridge cell
- **THEN** the node is reported as outside the footprint and the gate approach is reported as an error
