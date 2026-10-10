# Spec Delta

## MODIFIED Requirements

### Requirement: The capital has a palace, a noble quarter, a guardhouse and a drill yard
The capital SHALL carry a palace, a noble quarter, a guardhouse and a drill yard as permanent, complete, enterable tagged interiors reachable both ways. Staffing and authored host identity SHALL follow current place declarations, not historical personnel counts. Declared dialogue hosts SHALL converse without gaining forbidden watch-work capabilities.

#### Scenario: Four locations exist, three of them staffed
- **WHEN** synchronization completes
- **THEN** all four interiors exist once and remain reachable both ways; staffing matches declarations, including absent hosts

#### Scenario: The empty palace survives a resynchronization
- **WHEN** a currently hostless place is synchronized twice
- **THEN** its interior exists once and no service host appears on either run

