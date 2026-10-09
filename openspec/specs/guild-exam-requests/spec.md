# guild-exam-requests Specification

## Purpose

Define cut all examination surfaces to presence-first appointment requests and services schema v5 as observable deterministic behavior with explicit rejection and acceptance boundaries.

## Requirements

### Requirement: All examination requests resolve attendance before merit and start conditions
The shared rules-core coordinator SHALL resolve registration/branch/next target/qualified persistent host and local functioning counter/direct-host access, then inspect actual required-guild presence before merit or battle checks. Absent host SHALL yield read-only planned attendance or named unknown; present host SHALL delegate to start_guild_exam for authoritative service/merit/combat checks. Command, browser and validated NPC intent SHALL share this order and server-derived authority.

#### Scenario: Below merit absent
- **WHEN** registered below-threshold member asks at functioning counter while qualified host is absent
- **THEN** exam_schedule returns planned host/date/interval before merit, with no attempt/resources/affinity/session mutation

#### Scenario: Below merit present
- **WHEN** same actor asks while host is present and service-capable
- **THEN** start rejects BELOW_THRESHOLD with no attempt mutation

#### Scenario: Eligible present
- **WHEN** eligible actor asks while qualified host is present and available
- **THEN** start_guild_exam starts same persistent simulation and outcome is exam_started

#### Scenario: Unknown absent
- **WHEN** absent host has malformed schedule
- **THEN** named attendance rejection returns without merit/start checks

#### Scenario: Busy present
- **WHEN** present host blocks service
- **THEN** authoritative service rejection returns without starting

### Requirement: Appointment semantics provide information without storing bookings
Visible action SHALL be exactly 「預約升等考核」. Request payload SHALL be exactly target_rank and authority SHALL be derived server-side. Distinct exam_schedule/exam_started outcomes SHALL represent planned information and actual simulation start. Unknown/failed start SHALL use established rejection shape. No reservation/queue/expiry/cancellation, absent host spawn, teleport, automatic wait or auto-start SHALL exist. NPC speech SHALL remain in-character.

#### Scenario: Tampered payload
- **WHEN** browser or intent supplies host/branch/clock/threshold
- **THEN** exact validation rejects before coordinator mutation

#### Scenario: Planned response
- **WHEN** schedule information succeeds below threshold
- **THEN** response names host and planned calendar interval, claims no saved booking and exposes no private route
