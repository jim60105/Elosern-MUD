# Spec Delta

## ADDED Requirements

### Requirement: The activity record is stored in one part per settlement unit
The activity owner SHALL store each group, together with its journey and its receipts, in the stored part of the settlement unit of the group's home at the time the group was first stored, beside one header. Reading the record SHALL give the same complete state whether it is read from memory or from the database.

#### Scenario: Round trip
- **WHEN** a state holding groups homed in two disjoint synthetic zones, one of them travelling with a receipt, is written, every attribute cache is reset, and the record is read
- **THEN** the state read equals the state written

#### Scenario: Placement by home unit
- **WHEN** a group homed in the first zone and a group homed in the second zone are created
- **THEN** the first zone's part holds the first group and not the second, and the second zone's part holds the second group and not the first

#### Scenario: A group keeps its part
- **WHEN** a stored group's home is rewritten to a cell of another unit and the record is written again
- **THEN** the group is still held by the part it was first stored in, and reading the record gives the rewritten home

### Requirement: An activity write stores only the parts it changed
A write of the activity record SHALL store the header and each part that gained, lost or changed a group, journey or receipt, and SHALL NOT store any other part. A write of a state equal to the stored state SHALL store nothing.

#### Scenario: Other parts are not rewritten
- **WHEN** two zones each hold a stored group and one group of the first zone is changed and written
- **THEN** the stored value of the second zone's part is the same object as before the write

#### Scenario: A batched pass stores its parts once
- **WHEN** a batched pass changes two groups of the first zone several times and completes
- **THEN** the first zone's part is stored once and the second zone's part is not stored

#### Scenario: Unchanged state
- **WHEN** the state just read is written back unchanged
- **THEN** neither the header nor any part is stored

### Requirement: A stored activity record that is incomplete is refused
Reading the activity record SHALL raise the activity owner's invalid-state error, and SHALL rewrite nothing, when the header is missing or malformed, when a part the header lists is missing or malformed, or when two parts hold the same group, journey or receipt.

#### Scenario: Malformed header
- **WHEN** the stored header carries an unknown field, or a boolean where its settled-through tick belongs
- **THEN** reading the record raises the invalid-state error and the stored header is unchanged

#### Scenario: Missing part
- **WHEN** the header lists a unit whose part is not stored
- **THEN** reading the record raises the invalid-state error

#### Scenario: Duplicate entry
- **WHEN** two stored parts hold a group with the same identifier
- **THEN** reading the record raises the invalid-state error

### Requirement: A rolled-back activity write restores every part
The rollback surfaces of the activity record SHALL cover the header and every part, including a part that does not exist yet for a unit of the settlement-unit index. After a failed operation is restored from them, the record read from memory and after an attribute cache reset SHALL equal the record before the operation.

#### Scenario: Changed group
- **WHEN** an operation changes a stored group, fails, and its surfaces are restored
- **THEN** the record read from memory and after a cache reset equals the record before the operation

#### Scenario: Part created by the failed operation
- **WHEN** an operation creates the first group of a unit that had no part, fails, and its surfaces are restored
- **THEN** no part is stored for that unit, the header does not list it, and a later creation of a group in that unit succeeds
