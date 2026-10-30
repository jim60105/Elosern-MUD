# Spec Delta

## Purpose

Project live and prospective population without materializing objects. This capability owns its observable mechanism and rejection boundaries.

## ADDED Requirements

### Requirement: Population reads share materialization decisions
The wilderness population view SHALL apply the materializer decision rules to requested cells and registered entities without creating rooms, objects or registrations.

#### Scenario: View agrees with entry
- **WHEN** synthetic hunting, baseline, species, site, foreign and protected-session cells are viewed then materialized
- **THEN** view facts agree with retained/generated living population under existing rules

#### Scenario: No read mutation
- **WHEN** unprepared cells and foreign registered objects are viewed
- **THEN** clock, objects, room pools, Attributes and registrations remain unchanged

### Requirement: Observation identities survive materialization
Prospective population slots SHALL retain their observation identity when materialized and remain distinct from foreign registered entities.

#### Scenario: Materialization identity
- **WHEN** a prospective hostile is viewed, materialized and viewed again
- **THEN** its stable key is unchanged and independent foreign objects keep separate identities
