# Spec Delta

## MODIFIED Requirements

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

#### Scenario: Transit is not endpoint presence
- **WHEN** a real individual has departed on an unfinished or protected-arrival journey
- **THEN** neither endpoint reports it as a local target; authorized inspection reports its actual journey separately and stale entity targets reject
