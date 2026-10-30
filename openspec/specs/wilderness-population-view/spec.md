# wilderness-population-view Specification

## Purpose
Project live and prospective population without materializing objects. This capability owns its observable mechanism and rejection boundaries.

## Requirements

### Requirement: Population reads share materialization decisions
The wilderness population view SHALL apply the materializer decision rules to requested cells and registered entities without creating rooms, objects or registrations.

#### Scenario: View agrees with entry
- **WHEN** synthetic hunting, baseline, species and protected-session ambient cells are viewed then materialized
- **THEN** ambient view facts agree with retained/generated living population under the shared reconciliation rules

#### Scenario: No read mutation
- **WHEN** unprepared cells and foreign registered objects are viewed
- **THEN** clock, objects, room pools, Attributes and registrations remain unchanged

#### Scenario: Sites require committed lifecycle population
- **WHEN** a site is never populated, cleared, or eligible for recovery whose clock stage has not yet settled
- **THEN** the view returns only currently committed living site members and never predicts or triggers first population or recovery

#### Scenario: HP reads cannot construct traits
- **WHEN** registered entities have stored HP but no constructed trait handler
- **THEN** visibility reads persisted values without creating or rewriting any traits Attribute

### Requirement: Observation identities survive materialization
Prospective population slots SHALL retain their observation identity when materialized and remain distinct from foreign registered entities.

#### Scenario: Materialization identity
- **WHEN** a prospective hostile is viewed, materialized and viewed again
- **THEN** its stable key is unchanged and independent foreign objects keep separate identities
