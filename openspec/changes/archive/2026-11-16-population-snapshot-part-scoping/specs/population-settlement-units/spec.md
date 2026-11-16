# Spec Delta

## ADDED Requirements

### Requirement: A scoped settlement snapshots only its own activity parts
The rollback registry built for a scoped settlement SHALL hold the activity header, the part of each unit of the scope, and each part that holds a group of the scope. It SHALL hold no other activity part, however many groups another unit holds.

#### Scenario: Another unit's part is left out
- **WHEN** two disjoint synthetic zones each hold stored groups and the registry is built for a scope of the first zone's unit
- **THEN** the registry holds the header and the first zone's part and does not hold the second zone's part

#### Scenario: Growing the far zone
- **WHEN** the registry is built for the first zone's scope once while the second zone holds one group and once while it holds six
- **THEN** both registries name the same activity entries

#### Scenario: A group stored outside its present units
- **WHEN** a group of the scope is held by the part of a unit that is not a unit of the scope
- **THEN** the registry holds that part

### Requirement: A scoped snapshot names the parts its pass may create or retire from
The rollback registry of a scoped settlement SHALL name a unit of the scope that has no stored part as absent, so restoring it removes a part the pass created. When the scope holds the residual unit, the registry SHALL also hold every part storing a receipt whose group no longer exists.

#### Scenario: Part created by a failed scoped pass
- **WHEN** a scope's unit has no stored part, a group is created in that unit inside a transaction that then fails, and the registry built before it is restored
- **THEN** no part is stored for that unit and the record equals the record before the transaction, in memory and after an attribute cache reset

#### Scenario: Orphan receipt under a residual scope
- **WHEN** a part of a non-residual unit stores a receipt whose group no longer exists and the registry is built for a scope holding the residual unit
- **THEN** the registry holds that part

#### Scenario: Orphan receipt outside a residual scope
- **WHEN** the same record is snapshotted for a scope that holds neither the residual unit nor that part's unit
- **THEN** the registry does not hold that part

### Requirement: Unscoped snapshots keep the whole activity record
A population or activity snapshot taken without a scope SHALL hold the header and every activity part, as before.

#### Scenario: Whole snapshot
- **WHEN** the population surfaces are snapshotted without a scope in a world whose two zones each hold stored groups
- **THEN** the snapshot holds the header and both zones' parts
