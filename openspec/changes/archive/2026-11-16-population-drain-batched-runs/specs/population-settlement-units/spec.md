# Spec Delta

## MODIFIED Requirements

### Requirement: A drain run settles the most lagging closed set by one bounded slice
One drain run SHALL perform at most the configured number of settlement steps. Each step SHALL select the closed set of units with the lowest settled-through tick, ties broken by the smallest unit identifier, and SHALL settle it forward by at most the configured slice of game time and never past the world tick, admitting no field contact and leaving the world tick unchanged. A world with no lagging unit SHALL be left untouched.

#### Scenario: One slice
- **WHEN** one unit is at 100, another at 400, the world tick is 5000, the slice is 600 and the run may perform one step
- **THEN** one run moves the first unit to 700, leaves the second at 400 and the world tick at 5000

#### Scenario: Slice ends at the world tick
- **WHEN** the only lagging unit is at 4800, the world tick is 5000 and the slice is 600
- **THEN** one run moves the unit to 5000

#### Scenario: Nothing to do
- **WHEN** every unit is at the world tick
- **THEN** a run writes nothing and emits no event

#### Scenario: Linked units move together
- **WHEN** the most lagging unit is linked to a second unit by a group that touches both
- **THEN** one run moves both units by the same slice

#### Scenario: Several sets in one run
- **WHEN** one unit is at 100, another at 400, the world tick is 5000, the slice is 600 and the run may perform two steps
- **THEN** one run moves the first unit to 700 and the second to 1000, and reports two settled steps

#### Scenario: A far-behind set takes several steps
- **WHEN** one unit is at 100, every other unit is at the world tick 5000, the slice is 600 and the run may perform three steps
- **THEN** one run moves the unit to 1900 and reports three settled steps

#### Scenario: The run ends when nothing lags
- **WHEN** the only lagging unit is at 4800, the world tick is 5000, the slice is 600 and the run may perform three steps
- **THEN** one run moves the unit to 5000 and reports one settled step

### Requirement: A drain run is atomic and reports itself
Each drain step that settled a set SHALL emit one `population_backlog_drained` info event on durable commit with the number of units, both ticks and the number of units still lagging. A set whose step fails SHALL keep its complete prior durable state and live caches, SHALL cause one `population_backlog_drain_failed` error event and SHALL NOT be tried again in the same run. The run SHALL continue with the next most lagging set and SHALL stop after three failed sets.

#### Scenario: Reported slice
- **WHEN** a run of one step moves one of two lagging units from 100 to 700
- **THEN** one info event carries one unit, 100, 700 and one unit still lagging

#### Scenario: Failed run
- **WHEN** a fault is injected inside a run after a departure was written
- **THEN** the unit still reports 100, its state projection in memory and after an attribute cache reset equals its prior value, one error event is emitted, and the next run without the fault moves the unit to 700

#### Scenario: A failing set does not starve the next
- **WHEN** the most lagging set fails on every attempt and a second set is also behind
- **THEN** one run emits one error event for the first set, moves the second set by one slice and reports it

#### Scenario: One event per step
- **WHEN** a run of two steps moves one unit from 100 to 700 and another from 400 to 1000
- **THEN** two info events are emitted, the first carrying 100 and 700, the second carrying 400 and 1000

#### Scenario: A failed set is not retried in the same run
- **WHEN** the only lagging set fails on every attempt and the run may perform three steps
- **THEN** one run emits exactly one error event and reports no settled step

### Requirement: The periodic drain honours its switch
The periodic caller SHALL perform one drain run per repeat, with the configured slice and the configured number of steps, while the drain is enabled and SHALL perform none while it is disabled.

#### Scenario: Disabled
- **WHEN** the periodic caller repeats with the drain disabled and a unit lagging
- **THEN** no drain run happens and the unit's settled-through tick is unchanged

#### Scenario: Enabled
- **WHEN** the periodic caller repeats once with the drain enabled and a unit lagging
- **THEN** exactly one drain run happens with the configured slice and the configured number of steps

## ADDED Requirements

### Requirement: Group units are computed once per activity record
The units of every group SHALL be computed at most once while the activity record, the settlement-unit index and the published geography are unchanged, however many lagging-set, closure and scope queries read them. A changed record SHALL be computed again.

#### Scenario: Lagging sets and scopes share one computation
- **WHEN** the lagging sets are resolved and two scopes are then built over the same unchanged record
- **THEN** each group's units were computed once

#### Scenario: A written record is computed again
- **WHEN** a group's home is rewritten to a cell of another unit and the record is written between two scope builds
- **THEN** the second scope reflects the rewritten home
