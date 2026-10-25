# Spec Delta

## MODIFIED Requirements

### Requirement: Altoria qualifications select one persistent adventurer per branch and target
The qualification registry SHALL select one authored persistent adventurer per branch and target rank. Missing, duplicate, wrong-branch or insufficient-rank bindings SHALL fail closed. No profession field SHALL be authored or written; examination authority SHALL remain separate from counter reception capability. Person identity and qualification membership SHALL remain data; synchronization SHALL reuse the same person without overwriting live ordinary state.

#### Scenario: Different qualified hosts co-locate
- **WHEN** multiple differently qualified persistent hosts stand at the guild
- **THEN** the requested target selects its registry-bound person without generic component ambiguity

#### Scenario: Missing binding
- **WHEN** a new branch lacks its own senior
- **THEN** no Altoria fallback is selected

#### Scenario: Repeat sync
- **WHEN** an authored host has moved and edited its persona
- **THEN** sync retains dbref/location and mutable state

#### Scenario: Occupied key at persistent creation
- **WHEN** another live entity holds the authored person's key before normal host creation
- **THEN** one host is created with its own primary-key suffix and stable person provenance, and later sync/exams reuse its key/dbref without renaming
