# Spec Delta

## ADDED Requirements

### Requirement: Lifecycle operations inside an advance rely on the advance rollback
A population lifecycle operation settled by a clock advance SHALL open no savepoint and take no attribute snapshot of its own. A failure inside such an operation SHALL fail the advance, which SHALL restore the complete pre-advance durable state and live caches.

#### Scenario: Savepoints do not grow with the population
- **WHEN** the same interval is advanced once over a synthetic world with one due group and once over the same world with four due groups
- **THEN** both advances issue the same number of savepoint statements

#### Scenario: Fault after a partial departure
- **WHEN** a fault is injected after a group's bodies were detached and before its journey was recorded, during a clock advance
- **THEN** the advance raises, the clock tick is unchanged, and the population state projection, each body's room contents membership and each body's reloaded attributes equal their pre-advance values

#### Scenario: Fault during a fatigue write
- **WHEN** a fault is injected after the first of two members' reserve was written by lifecycle physiology during a clock advance
- **THEN** the advance raises and both members' reserve, posture and sleep receipt equal their pre-advance values in cache and after reload

#### Scenario: Results are unchanged
- **WHEN** a synthetic world with a wandering group, a travelling group, a zone below its lower density and a recoverable site is advanced over one interval and over a partition of it, once relying on the advance rollback and once with per-operation protection
- **THEN** all resulting state projections are equal

### Requirement: Operations that recover and continue keep their own protection
A lifecycle operation called outside a clock advance, and the field contact admission inside a settlement pass, SHALL keep its own savepoint and snapshot, so that its failure restores exactly what it wrote and the caller can continue.

#### Scenario: Direct operation outside an advance
- **WHEN** a group departure committed directly through the activity owner fails after detaching its bodies, with no clock advance running
- **THEN** the owner restores the activity record, coordinates, timeline, locations and physiology before the error reaches the caller

#### Scenario: Failed contact inside a pass
- **WHEN** a field contact admission fails at the endpoint of a pass inside a clock advance
- **THEN** its participants are restored, the advance commits, and the idle decisions due at that tick are settled
