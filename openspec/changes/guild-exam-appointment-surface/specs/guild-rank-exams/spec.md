## MODIFIED Requirements

### Requirement: Rank promotion requires cumulative merit and exactly the next examination
guild_economy.yaml SHALL retain strictly increasing merit thresholds E-S. Promotion/start SHALL require registered exact-next rank and true cumulative merit, never spent on attempt/promotion. Schedule-first requests SHALL remain available below threshold: absent-host attendance returns before merit; present-host start rejects insufficient merit. Rank skips and S next promotion SHALL reject.

#### Scenario: Threshold alone
- **WHEN** member reaches threshold
- **THEN** rank does not advance until exam PASS

#### Scenario: Absent below merit
- **WHEN** below-threshold member asks for exact-next exam at local counter with absent host
- **THEN** planned attendance returns with no exam mutation

#### Scenario: Present below merit
- **WHEN** same member asks with service-capable host present
- **THEN** start rejects without record/session/resources/affinity change

#### Scenario: Rank skipping
- **WHEN** F member requests D even with sufficient merit
- **THEN** only E is accepted as target

