# Spec Delta

## ADDED Requirements

### Requirement: Physical refresh includes generated scene contexts
Committed physical-source changes SHALL refresh generated and static scene contexts through the same canonical hooks. Generated content SHALL require no static registry membership and immutable package payloads SHALL remain unchanged.

#### Scenario: Generated exposure qualification refreshes
- **WHEN** equipped exposure changes a generated topic's qualification
- **THEN** shared post-commit refresh updates its choices without another selection or package mutation

### Requirement: Physical condition mutations refresh live dialogue after commit
Canonical item, equipped or base exposure, social identity and skill changes SHALL refresh affected owner dialogue availability after commit, including text, other-connection and no-session origins. Rolled-back changes SHALL publish no false eligibility, and current playback SHALL retain its chosen scene.

#### Scenario: No-session equipped exposure
- **WHEN** a canonical equipment writer runs without WebClient action context and crosses a live topic boundary
- **THEN** all current authenticated owner watchers receive updated availability without another selection

#### Scenario: Outer rollback cancels physical refresh
- **WHEN** inventory or skill writes occur inside an owning transaction that later fails
- **THEN** neither false open state nor an unlock observation publishes

