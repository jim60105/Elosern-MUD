## MODIFIED Requirements

### Requirement: Objective descriptions are deterministic and exhaustive
The rendering layer SHALL produce a Traditional Chinese description for every
`ObjectiveKind` and `DestinationKind` combination used by the closed definition
vocabulary, including the regional species-hunt selector (region display name, species
display name, required count, and the countable variants' display names). It SHALL be read-only, SHALL NOT write quest or player state, and
SHALL raise on an unknown `ObjectiveKind` so drift fails loudly in tests.

#### Scenario: DEFEAT objective renders tier and quantity
- **WHEN** a DEFEAT objective declares tier `low` and quantity `1`
- **THEN** the description states the monster tier and the required count

#### Scenario: Species hunt renders region, species, and countable variants
- **WHEN** a species-hunt objective declares region, species, quantity, and countable variants
- **THEN** the description names the region, the species, the count, and the eligible variants in deterministic order

#### Scenario: REACH objective renders its destination
- **WHEN** a REACH objective declares an anchor, grid, or bound-instance
  destination
- **THEN** the description names the destination in Traditional Chinese

#### Scenario: ESCORT objective renders the protected-entity requirement
- **WHEN** an ESCORT objective declares a destination
- **THEN** the description states that every protected entity must be escorted
  to the destination

#### Scenario: ACQUIRE objective renders the item and count
- **WHEN** an ACQUIRE objective declares an item key and quantity
- **THEN** the description names the item and the required count

#### Scenario: Unknown objective kind raises
- **WHEN** the renderer is invoked with an `ObjectiveKind` it does not recognize
- **THEN** it raises an explicit error instead of emitting a wrong description

#### Scenario: A bound objective on a named site renders the name
- **WHEN** a bound site objective names a synthetic site that declares an individual name
- **THEN** the description is the defeat verb followed by that name, with no count and no note

#### Scenario: A bound objective on an unnamed site is unchanged
- **WHEN** a bound site objective names a synthetic site with no individual name
- **THEN** the description is the generic bound-target line with the required count
