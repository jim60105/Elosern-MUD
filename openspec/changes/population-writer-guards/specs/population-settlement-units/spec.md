# Spec Delta

## ADDED Requirements

### Requirement: Population writers refuse a lagging unit
Outside a running settlement pass, registering an explicit group, creating a group, recording a presence transition, recording a cell protection, and committing a monster departure SHALL raise a named error and write nothing when a unit they touch is behind the current world tick.

#### Scenario: Explicit registration into a lagging unit
- **WHEN** an explicit group is registered on a cell whose unit is at 100 while the world tick is 700
- **THEN** the named not-current error is raised and no group, registration or transition is stored

#### Scenario: Group reaching a lagging unit
- **WHEN** a group is created on a cell of a current unit with an activity area inside a unit that is behind
- **THEN** the named not-current error is raised and no group is stored

#### Scenario: Transition, protection and departure
- **WHEN** a presence transition, a cell protection and a monster departure are each attempted for a cell of a unit that is behind
- **THEN** each raises the named not-current error and the timeline, the coordinate registration and the activity record are unchanged

#### Scenario: Current unit and running pass
- **WHEN** the same writers run for a cell of a current unit, or inside a settlement pass of the cell's unit
- **THEN** they write as before

### Requirement: The GM monster view reports settlement progress without settling
The GM monster placement read SHALL report the settled-through tick of the monster's unit and SHALL mark a unit that is behind the world tick. The read SHALL NOT change any state.

#### Scenario: Lagging monster
- **WHEN** the placement section is read for a monster of a unit at 100 while the world tick is 700
- **THEN** the section carries the progress row with 100 and the behind row with 600, and the unit still reports 100

#### Scenario: Current monster
- **WHEN** the placement section is read for a monster of a current unit
- **THEN** the section carries the progress row and no behind row
