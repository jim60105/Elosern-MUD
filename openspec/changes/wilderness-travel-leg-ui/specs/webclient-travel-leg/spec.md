# Spec Delta

## Purpose

Supply server-authored foot capacity and neighbour duration facts, then present the leg gauge and persisted travel preferences. This capability defines observable browser travel behavior and its data boundaries.

## ADDED Requirements

### Requirement: Travel status supplies bounded foot capacity and quotes
Wilderness status SHALL supply read-only per-stage foot-capacity counts and current neighbour duration quotes from canonical traversal and fatigue inputs without exposing undisclosed targets or predicting eligibility in the browser.

#### Scenario: Sequential capacity
- **WHEN** synthetic mixed-speed parties, threshold boundaries, sleep/refusal and allowed flight are queried
- **THEN** foot capacity counts match independent sequential physical steps, neighbour charged seconds retain the waiver and all canonical state stays unchanged

#### Scenario: Bounds and unavailable values
- **WHEN** non-wilderness, corrupt capacity inputs and malformed wire counts/quotes are supplied
- **THEN** non-wilderness or unreadable capacity is null, malformed wire facts reject and no hidden destination metadata serializes

### Requirement: Leg panel projects supplied state and persisted preferences
The leg panel SHALL present aim, capacity, plan, walking and error states from supplied facts with non-colour ticks and persisted pace/night preferences that remain fixed while walking.

#### Scenario: State precedence and preferences
- **WHEN** every intent state and valid/default persisted preferences are exercised, including an active walk
- **THEN** the documented precedence selects the intent, supplied stages determine ticks and controls cannot alter an active departure

#### Scenario: Actions and unavailable state
- **WHEN** look, sleep/camp entry, Stop or Depart are activated with absent/current plans or stale maps
- **THEN** only available guarded actions execute, Depart requires a current lock and stale map disables the panel

