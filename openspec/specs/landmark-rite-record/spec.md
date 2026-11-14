# landmark-rite-record Specification

## Purpose
Defines the player character's landmark rite completion record: which districts and which ritual options were completed, how often and when, with a strict envelope that is never silently repaired or overwritten.

## Requirements

### Requirement: The rite record counts completions per district and per option
Recording a completion SHALL create or update the district's entry and the option's entry: counts increase by one, the last tick becomes the completion tick, and the first tick of an existing district never changes.

#### Scenario: First completion
- **WHEN** an option is completed at tick 100 in a district with no entry
- **THEN** the district entry has count 1 and first and last tick 100, and the option entry has count 1 and last tick 100

#### Scenario: Repeat and second option
- **WHEN** the same option is completed again at tick 250 and another option at tick 300
- **THEN** the district count is 3, its first tick is still 100, its last tick is 300, and each option entry carries its own count and last tick

### Requirement: The rite record envelope is strict and never repaired
Reading the record SHALL reject any value outside the schema-1 envelope with a named error and SHALL never write. A character with no record SHALL read as having completed nothing without a record being created.

#### Scenario: Envelope violations
- **WHEN** the stored value has an extra top-level key, a schema version other than 1, a count below 1, a first tick after the last tick, or a non-mapping entry
- **THEN** each read raises the named record error and the stored value is unchanged

#### Scenario: No record
- **WHEN** a character with no record is read
- **THEN** the result has no completed district and the character still has no record

#### Scenario: Refused write
- **WHEN** an invalid record is written
- **THEN** the write raises and the stored value is unchanged

### Requirement: Undeclared keys survive a write
Recording a completion SHALL preserve every district entry and option entry already in the record unchanged, including keys that current content no longer declares.

#### Scenario: Retired keys
- **WHEN** a record holding an entry for a retired district and a retired option receives a completion for another district
- **THEN** the retired entries are present and unchanged after the write
