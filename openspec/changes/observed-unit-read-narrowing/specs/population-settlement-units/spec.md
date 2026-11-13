# Spec Delta

## ADDED Requirements

### Requirement: A scoped pass enumerates only its own individuals
A scoped settlement pass SHALL build its presence facts from the members of the scope's groups and the individuals registered on cells of the scope, and SHALL give every zone of the scope the counts a whole-world enumeration gives.

#### Scenario: Counts equal the whole-world counts
- **WHEN** zone counts of one synthetic zone are measured in a scoped pass and from a whole-world enumeration, in a world where a second zone holds other individuals
- **THEN** the zone's local, home-owned and per-cell measures are equal

#### Scenario: Home-owned member standing in a linked unit
- **WHEN** a member of a group owned by the scope's zone stands on a cell of another unit that the group links into the scope
- **THEN** the member is counted against the zone's home ceiling

#### Scenario: Registered individual without a group
- **WHEN** a living individual with a home zone of the scope belongs to no group and is registered on a cell of the scope
- **THEN** it is counted locally and against the home ceiling

#### Scenario: Results are unchanged
- **WHEN** the synthetic two-zone world with a player in the first zone is advanced by three intervals and caught up everywhere, once with the scoped enumeration and once with the whole-world enumeration
- **THEN** both state projections are equal

### Requirement: Advance database work is independent of unobserved units
The number of database statements one clock advance issues SHALL NOT depend on how many groups or individuals unobserved units hold.

#### Scenario: Growing the far zone
- **WHEN** the same advance runs over a world whose unobserved zone holds one group of one individual and over a world whose unobserved zone holds six groups of three
- **THEN** both advances issue the same number of database statements
