# Spec Delta

## ADDED Requirements

### Requirement: Adult memories authorize fields per participant
Adult narrative memories SHALL be derived only from fields the memory owner is authorized to know. Event visibility and presence SHALL NOT authorize every participant's private milestone, roll, compliance reasoning or counter. The same recipient-authorized projection SHALL serve nomination and memory boundaries. Unsupported or malformed adult records SHALL remain fail-closed rather than falling through to a raw-content memory branch.

#### Scenario: Public adult event hides another participant's private history
- **WHEN** an adult action is witnessed by a third living participant while one participant has private milestone history and an unknown internal counter
- **THEN** each participant's memory contains only the acts, roles and results that participant can know; the third participant receives no private milestone or counter and no invented participation

#### Scenario: Own experience remains available
- **WHEN** the player is an adult-action participant and the affected fields are knowable to the player
- **THEN** the player's authorized memory retains those fields and source provenance without explicit consent or relationship claims

#### Scenario: Memory projection reuses its source exactly once
- **WHEN** committed adult memory projection is retried or resumes after process restart
- **THEN** the original source and progress are reused once per authorized owner, with no duplicate memory and no newly authorized private fields

#### Scenario: Malformed adult payload does not bypass authorization
- **WHEN** an adult event has an unsupported shape
- **THEN** projection fails closed for that record with a diagnostic and no raw-content memory is created
