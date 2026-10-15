# Spec Delta

## MODIFIED Requirements

### Requirement: The scheduler is settings-configurable and disableable
`world/art/scheduler.py` SHALL provide a persistent Script that drains up to the configured limit of
pending jobs at the configured interval. When `ART_SCHEDULER_ENABLED` is false the scheduler SHALL run
no drain, records SHALL remain `missing`/`pending`, truthful normal alpha/name-initial/bundled-scene fallbacks SHALL remain, and gameplay SHALL
proceed unchanged.

#### Scenario: The disabled scheduler never drains
- **WHEN** the scheduler is disabled and pending records exist
- **THEN** no drain runs, the records stay `pending`, and gameplay proceeds

#### Scenario: The enabled scheduler drains up to its limit per interval
- **WHEN** the scheduler is enabled with a limit and pending records exist
- **THEN** each interval drains at most the configured limit of pending records through the worker

#### Scenario: Disabled generation does not erase independent faults
- **WHEN** scheduler is disabled while a recorded failed job or required static resource is broken
- **THEN** resolution preserves independent truthful failure facts and required scene-art selection without scheduling new work

