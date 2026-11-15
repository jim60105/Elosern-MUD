# Spec Delta

## ADDED Requirements

### Requirement: Adoption requires a registered art subject for every archetype
Adopting the rite document SHALL fail, installing nothing, when the art subject derived from any archetype key is not a registered scene archetype, and SHALL name each such archetype.

#### Scenario: Unregistered subject
- **WHEN** a valid synthetic document whose archetype has no registered art subject is adopted
- **THEN** adoption raises naming that archetype and no snapshot is installed

#### Scenario: Registered subject
- **WHEN** the same document is adopted while its derived subject is registered
- **THEN** the snapshot is installed
