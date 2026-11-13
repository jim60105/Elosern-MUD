# Spec Delta

## ADDED Requirements

### Requirement: A clock advance settles observed units only
The population stage of a clock advance SHALL settle the closed sets of the observed units through the advance's end tick, and SHALL leave every other unit's records, individuals and settled-through tick unchanged. An observed set that is behind the advance's start SHALL first be settled to the start, with no field contact, inside the same advance.

#### Scenario: Far unit is left alone
- **WHEN** a player character stands in one synthetic zone, a second zone beyond the sight radius has due groups and a deficit, and the clock advances from 100 to 700
- **THEN** the first zone's unit reports 700, the second zone's unit reports 100, and the second zone's state projection is unchanged

#### Scenario: Observed set behind the start
- **WHEN** the observed zone's unit is at 100, the world tick is 400 and the clock advances to 700
- **THEN** the unit reports 700 and its state projection equals that of one scoped pass from 100 to 700

#### Scenario: No player
- **WHEN** the clock advances with no player character in the world
- **THEN** only the residual unit's settled-through tick moves

#### Scenario: Rollback
- **WHEN** a later clock stage raises after the observed units were settled, including an inline catch-up
- **THEN** every unit reports its pre-advance tick and the state projection equals its pre-advance value in memory and after an attribute cache reset

### Requirement: Deferred settlement gives the whole-world result
A world advanced with observed-only settlement and then caught up everywhere SHALL have the same activity record, zone records, site records and per-individual position, gauges, reserve, posture and sleep receipt as the same world settled by whole-world passes over the same intervals.

#### Scenario: Advance, then catch up
- **WHEN** a synthetic two-zone world with a player in the first zone is advanced by three intervals and the second zone is then caught up, and an identical world is settled by three whole-world passes
- **THEN** both state projections are equal

#### Scenario: Reload while a unit is behind
- **WHEN** every attribute cache is reset while the second zone is behind and the zone is then caught up
- **THEN** its state projection equals the projection without the reset

### Requirement: Advance work is independent of unobserved units
The number of database statements, planned group decisions and snapshotted individuals of one clock advance SHALL NOT depend on how many groups, individuals or due boundaries unobserved units hold.

#### Scenario: Growing the far zone
- **WHEN** the same advance runs over a world whose unobserved zone holds one due group and over a world whose unobserved zone holds six
- **THEN** both advances issue the same number of database statements, plan decisions for the same groups and snapshot the same number of individuals

### Requirement: The contact forecast reads observed units only
The interruptible-skip boundary query SHALL project only the observed units and SHALL return the same tick as a projection of the whole world when every unit is current.

#### Scenario: Same answer
- **WHEN** a contact with the observing party is due at one tick and unobserved zones hold earlier maintenance boundaries
- **THEN** the query returns the contact tick, equal to the whole-world projection's answer, and projects no group of an unobserved zone
