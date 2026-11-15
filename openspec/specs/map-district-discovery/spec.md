# map-district-discovery Specification

## Purpose

Announce newly explored districts only after a first landmark arrival commits, using the existing visited-node record as the sole discovery state.

## Requirements

### Requirement: Movement announces no district discovery
A landmark traversal, successful or not, SHALL emit only its movement narrative: no exploration announcement and no discovery event. A map read and a reconnect SHALL emit none either.

#### Scenario: First landmark traversal
- **WHEN** a first landmark traversal commits and records the canonical node
- **THEN** the movement narrative is one line with no exploration announcement, no discovery event is logged and the district is unlit

#### Scenario: Failed movement
- **WHEN** a traversal is blocked, vetoed or rolled back, or a map read/reconnect occurs
- **THEN** no exploration announcement is emitted and no new discovery state is persisted

### Requirement: The first completed rite adds one discovery narrative
The first committed rite at a district SHALL add one line naming that district to the rite's completion message and SHALL log one discovery event. A repeated rite, a refused rite and a rolled-back rite SHALL add no such line and log no discovery.

#### Scenario: First and repeated rite
- **WHEN** a rite commits at a district with no earlier completion and then commits again
- **THEN** the first completion message carries one extra line naming the district and one discovery event is logged, and the second has neither

#### Scenario: Refused or rolled-back rite
- **WHEN** a rite is refused, or fails after the advance and rolls back
- **THEN** no discovery event is logged
