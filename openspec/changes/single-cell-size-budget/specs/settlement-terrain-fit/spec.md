# Spec Delta

## MODIFIED Requirements

### Requirement: Size budget follows the population-area relation with a multi-cell floor
The size budget SHALL compute built-up area as the reference area times (population divided by the reference population) raised to the configured exponent. Footprint cells SHALL be the larger of two and the area rounded up in km², except that a village or hamlet SHALL receive one cell and its node count from the single-cell tier table. The envelope radius SHALL be that of a circle of that area. Node, gate and loop targets of every other kind SHALL come from the supplied tier tables. Unsupported kinds and non-positive populations SHALL be rejected.

#### Scenario: Area scales by the configured exponent
- **WHEN** a synthetic configuration with reference population 10,000, reference density 100 inhabitants per hectare and exponent 0.5 is applied to population 40,000
- **THEN** the built-up area is exactly 2 km², the footprint is 2 cells and the envelope radius is the rounded metre radius of a 2 km² circle

#### Scenario: Multi-cell floor
- **WHEN** a population yields 0.3 km² and another yields 3.2 km²
- **THEN** their footprints are 2 and 4 cells; no capital, city, town or port ever receives a single-cell footprint

#### Scenario: Tier tables
- **WHEN** a synthetic tier table is applied at, just below and just above each population boundary, and a capital-kind location is applied at a small population
- **THEN** each boundary is inclusive of its lower bound, and the capital receives the capital node, gate and loop targets regardless of population

#### Scenario: Single-cell kinds
- **WHEN** a village and a hamlet are budgeted with a synthetic single-cell tier table, and a town is budgeted at the village's population
- **THEN** the village and the hamlet each receive one footprint cell and their table's node count, and the town still receives two cells

#### Scenario: Invalid single-cell table
- **WHEN** a configuration's single-cell tier table omits one of the two kinds or gives a node count below two
- **THEN** the configuration is rejected

#### Scenario: Rejected inputs
- **WHEN** the budget is requested for an `elven_village` or `dungeon` kind, or for a population of 0 or none
- **THEN** it is rejected with an error naming the location and no budget is produced

## ADDED Requirements

### Requirement: Terrain-fit lint checks single-cell entrances against road contacts
For a village or hamlet with a one-cell physical footprint, the lint SHALL report an error when its gate approach cells differ from the road cells that precede or follow its location cell on any road, or when it has more than one gate and no such road cell. Other settlements SHALL NOT receive this check.

#### Scenario: Matching and mismatching gates
- **WHEN** a synthetic village on a through road has gates on both road contacts, then loses one gate, then gains a gate on a cell with no road
- **THEN** the first lint is clean and each of the other two reports the entrance mismatch naming the cell

#### Scenario: No road contact
- **WHEN** a synthetic hamlet with no road contact has one gate, and then two gates
- **THEN** only the second reports the entrance mismatch

#### Scenario: National settlements are unaffected
- **WHEN** a synthetic town's gates lie on cells with no road
- **THEN** no entrance mismatch is reported
