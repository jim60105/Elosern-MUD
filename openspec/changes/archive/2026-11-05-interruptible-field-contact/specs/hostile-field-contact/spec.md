# Spec Delta

## ADDED Requirements

### Requirement: Contact forecasts stop interruptible time at actual interaction
Read-only contact forecasting SHALL use the same deterministic chronological planning as settlement, including intermediate births and journeys, to stop interruptible time at the first relevant contact while leaving distant maintenance internal.

#### Scenario: Intermediate birth and travel
- **WHEN** a wait spans distant maintenance105, birth110, departure120 and the first hostile arrival140 from tick100
- **THEN** forecast returns140 without writes; the actual skip settles40 seconds and contact, while no distant maintenance alone returns player control

#### Scenario: Projection purity and equivalence
- **WHEN** the same window is forecast repeatedly and committed once or in equal partitions with identical external events
- **THEN** forecast consumes no seeds/sequences, creates no entity/room/session and each actual result has the same route, resource and contact state

#### Scenario: Indivisible physical edge
- **WHEN** a hostile condition becomes true during a committed movement edge arriving later
- **THEN** the edge completes its normal costs with neither endpoint exposed in passage, then admits arrival contact before another exploration step

