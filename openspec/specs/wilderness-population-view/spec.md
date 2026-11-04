# wilderness-population-view Specification

## Purpose
Project live and prospective population without materializing objects. This capability owns its observable mechanism and rejection boundaries.

## Requirements

### Requirement: Population reads report actual living registrations
Population reads SHALL project only actual living registered entities in requested cells without materializing, reconciling or predicting population.

#### Scenario: No prospective entities
- **WHEN** an empty zone has configured compositions, uninitialized state or a pending due wave
- **THEN** no monster presence fact or exact entity target is returned and no state changes

#### Scenario: Actual members of every owner
- **WHEN** ambient, site, quest and foreign living individuals share a cell
- **THEN** all actual IDs are projected once with current position, public label and canonical threat/grade; dead or absent IDs are excluded

#### Scenario: No read mutation
- **WHEN** unprepared cells and stored HP are read repeatedly
- **THEN** clock, objects, room pools, Attributes, registrations, seed, sequence and schedule remain unchanged, and no traits handler is created

### Requirement: Observation identity belongs to persistent individuals
Each living population observation SHALL use persistent individual identity across room activation, recycling, rename and reload, while each fresh birth retains a new distinct identity.

#### Scenario: Identity across room lifecycle
- **WHEN** a registered living object is observed, attached to a prepared room, renamed and reloaded
- **THEN** its observation identity stays unchanged without a coordinate-slot alias or false new-entity transition

#### Scenario: Fresh birth and repeated labels
- **WHEN** a dead member is later replaced by an independently born individual with the same label
- **THEN** the new ID is distinct and another same-label survivor retains its own identity
