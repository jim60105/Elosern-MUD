# Spec Delta

## Purpose

Divides the monster population into settlement units whose settlement never reads another unit's state, and records how far each unit has been settled, so that settlement work can be limited to the units that matter to an action.

## ADDED Requirements

### Requirement: Authored geometry resolves to settlement units
Ecology zones and region-bound activity areas SHALL resolve to settlement units such that two of them share a unit exactly when a chain of links connects them: a rectangle overlap inside one region, or a zone or site whose births can be bound to an area. A cell or room that belongs to none of them SHALL belong to the residual unit. The resolution SHALL be deterministic and SHALL read no database state.

#### Scenario: Disjoint zones
- **WHEN** two synthetic zones in one region have rectangles that do not overlap and no activity area touches both
- **THEN** they resolve to two different units, and a cell of each zone resolves to that zone's unit

#### Scenario: Area bridges two zones
- **WHEN** a synthetic region-bound activity area overlaps the rectangles of two otherwise disjoint zones
- **THEN** both zones and the area resolve to one unit

#### Scenario: Birth binding links a zone to a distant area
- **WHEN** a synthetic zone's pool can birth a group bound to a region-bound area whose rectangles do not overlap the zone
- **THEN** the zone and the area resolve to one unit

#### Scenario: Same rectangles in different regions
- **WHEN** two synthetic zones have equal rectangles but different region keys
- **THEN** they resolve to two different units

#### Scenario: Residual
- **WHEN** a room locator, and a wilderness cell covered by no zone and no activity area, are resolved
- **THEN** both resolve to the residual unit

#### Scenario: Stable identity
- **WHEN** the same registries are resolved twice, the second time with their entries in reverse order
- **THEN** every zone, area and cell resolves to the same unit identifier both times

### Requirement: A group's units and unit closures are derived from live state
The units a group touches SHALL be the units of its home, its position, its journey endpoints, every cell of its activity area and its owning zone or site. The closure of a set of units SHALL add every unit reachable through groups and sites that touch more than one unit.

#### Scenario: Group inside its zone
- **WHEN** a zone-owned group stands inside its zone with an area inside that zone
- **THEN** it touches exactly that zone's unit, and the closure of that unit is that unit alone

#### Scenario: Escaped member links two units
- **WHEN** a group owned by one zone stands on a cell of a second, disjoint zone
- **THEN** it touches both units, and the closure of either unit contains both

#### Scenario: Journey endpoints
- **WHEN** a group travels from a cell of one unit to a cell of another
- **THEN** it touches both units until its arrival is recorded

### Requirement: Each unit records its settlement progress
The world SHALL store one settled-through tick per settlement unit, with a default for units not yet listed. Fresh provisioning SHALL create the record at the provisioning tick, a pass SHALL record its endpoint, a rolled-back advance SHALL restore the record, and a missing or malformed record SHALL be refused by name.

#### Scenario: Fresh world
- **WHEN** a population is provisioned at tick 100
- **THEN** every unit reports settled-through tick 100

#### Scenario: Pass records its endpoint
- **WHEN** a lifecycle pass settles through tick 260
- **THEN** every unit reports 260

#### Scenario: Rollback
- **WHEN** a later clock stage raises after a pass recorded tick 260 over a world at 100
- **THEN** every unit reports 100 in memory and after reload

#### Scenario: Malformed record
- **WHEN** the stored record is absent, or is not a mapping with an integer default and a mapping of unit identifiers to integers
- **THEN** reading it raises the population owner's malformed-state error and nothing is rewritten
