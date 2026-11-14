# Spec Delta

## ADDED Requirements

### Requirement: A drain run settles the most lagging closed set by one bounded slice
One drain run SHALL select the closed set of units with the lowest settled-through tick, ties broken by the smallest unit identifier, and SHALL settle it forward by at most the configured slice of game time and never past the world tick, admitting no field contact and leaving the world tick unchanged. A world with no lagging unit SHALL be left untouched.

#### Scenario: One slice
- **WHEN** one unit is at 100, another at 400, the world tick is 5000 and the slice is 600
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

### Requirement: Draining gives the whole-world result
A world whose lagging units were settled by drain runs SHALL have the same activity record, zone records, site records and per-individual position, gauges, reserve, posture and sleep receipt as the same world settled by one whole-world pass to the same tick.

#### Scenario: Drain to completion
- **WHEN** a synthetic two-zone world with both units behind is drained until no unit lags, and an identical world is settled by one whole-world pass to the world tick
- **THEN** both state projections are equal

### Requirement: A drain run is atomic and reports itself
A drain run that settled something SHALL emit one `population_backlog_drained` info event on durable commit with the number of units, both ticks and the number of units still lagging. A set whose settlement fails SHALL keep its complete prior durable state and live caches and SHALL cause one `population_backlog_drain_failed` error event; the same run SHALL then try the next most lagging set, up to three sets per run.

#### Scenario: Reported slice
- **WHEN** a run moves one of two lagging units from 100 to 700
- **THEN** one info event carries one unit, 100, 700 and one unit still lagging

#### Scenario: Failed run
- **WHEN** a fault is injected inside a run after a departure was written
- **THEN** the unit still reports 100, its state projection in memory and after an attribute cache reset equals its prior value, one error event is emitted, and the next run without the fault moves the unit to 700

#### Scenario: A failing set does not starve the next
- **WHEN** the most lagging set fails on every attempt and a second set is also behind
- **THEN** one run emits one error event for the first set, moves the second set by one slice and reports it

### Requirement: The periodic drain honours its switch
The periodic caller SHALL perform one drain run per repeat while the drain is enabled and SHALL perform none while it is disabled.

#### Scenario: Disabled
- **WHEN** the periodic caller repeats with the drain disabled and a unit lagging
- **THEN** no drain run happens and the unit's settled-through tick is unchanged

#### Scenario: Enabled
- **WHEN** the periodic caller repeats once with the drain enabled and a unit lagging
- **THEN** exactly one drain run happens with the configured slice
