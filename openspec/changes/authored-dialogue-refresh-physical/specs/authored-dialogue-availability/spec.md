# Spec Delta

## ADDED Requirements

### Requirement: Physical condition mutations refresh live dialogue after commit
Canonical item, equipped or base exposure, social identity and skill changes SHALL refresh affected owner dialogue availability after commit, including text, other-connection and no-session origins. Rolled-back changes SHALL publish no false eligibility, and current playback SHALL retain its chosen scene.

#### Scenario: No-session equipped exposure
- **WHEN** a canonical equipment writer runs without WebClient action context and crosses a live topic boundary
- **THEN** all current authenticated owner watchers receive updated availability without another selection

#### Scenario: Outer rollback cancels physical refresh
- **WHEN** inventory or skill writes occur inside an owning transaction that later fails
- **THEN** neither false open state nor an unlock observation publishes

