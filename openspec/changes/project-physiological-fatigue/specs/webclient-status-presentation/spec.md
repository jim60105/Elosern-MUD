# Spec Delta

## ADDED Requirements

### Requirement: Fatigue presentation identifies its physiological subject
Existing read-only status/debuff surfaces SHALL show member identity, rounded reserve percent and text action-unavailability with registry severity. Exact thresholds SHALL use stored units. Controlled-body and party-member fatigue SHALL be identifiable without changing the existing owner-keyed possession hybrid for unrelated status resources.

#### Scenario: Possessed body differs from owner
- **WHEN** the owner is awake at 80% and the controlled companion is forced asleep at 2%
- **THEN** presentation identifies each subject and exposes the companion's sleep restriction; no owner gauge is relabelled as companion truth

#### Scenario: No independent countdown
- **WHEN** a forced sleeper is displayed twice without accepted time
- **THEN** reserve and posture stay unchanged and no fabricated expiry or wake is promised

