# Spec Delta

## MODIFIED Requirements

### Requirement: A SINGLE skill opens against the named monster and an AREA skill opens against every living hostile monster in the room
Ordinary field openings SHALL admit every living co-located monster in persistent-ID order while resolving opening recipients independently through the selected action's existing targeting rules.

#### Scenario: Single recipient in mixed cell
- **WHEN** a SINGLE action selects one A in a cell with A, A and B
- **THEN** all three enter the roster, only selected A is the opening recipient, and untouched recipient controls retain their state

#### Scenario: Area opening
- **WHEN** an AREA action anchors a valid living monster
- **THEN** the full roster is admitted and concrete action recipients pass existing targeting and faction checks

#### Scenario: Preview and companion parity
- **WHEN** a player or authorized companion previews then commits an opening
- **THEN** candidate and committed roster and recipient identities agree; party authority, costs, order and draft semantics are unchanged

#### Scenario: Dead and absent exclusion
- **WHEN** a cell also contains a dead or remote monster
- **THEN** neither enters ordinary membership and no invalid target is substituted

