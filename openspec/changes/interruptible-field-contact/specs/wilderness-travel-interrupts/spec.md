# Spec Delta

## ADDED Requirements

### Requirement: Arrival combat stops walking before the next edge
A committed wilderness traversal SHALL complete its physical edge and publish its resulting arrival encounter coherently before any further automatic walking edge.

#### Scenario: One committed mode
- **WHEN** a paid edge arrives among currently aggressive actual occupants
- **THEN** the final update is combat with the actual whole-cell roster, no actionable exploration frame appears and continuation cannot take another edge

#### Scenario: Stale target
- **WHEN** a text/browser target names a traveller that has departed or not yet arrived
- **THEN** presence validation rejects without substituting another same-label individual or beginning a remote fight

