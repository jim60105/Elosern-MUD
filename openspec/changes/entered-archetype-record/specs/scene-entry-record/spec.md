## Purpose

Record, per character, which scene archetypes the character has entered,
through one deterministic writer at the room-entry seam, so the gallery lists
only backgrounds the player has seen.

## ADDED Requirements

### Requirement: Room entry records the entered scene archetype per character
A successful room entry that ensures a scene asset for a validated archetype SHALL also record that archetype in the entering character's scene-entry record, through exactly one writer module. A room with no resolvable archetype SHALL record nothing, and a recording failure SHALL never block the move.

#### Scenario: Entering records the archetype once
- **WHEN** character C enters two rooms of synthetic archetype `t_arch` and one room of `t_other`
- **THEN** C's record holds exactly `t_arch` and `t_other`

#### Scenario: Another character's entries are separate
- **WHEN** character D of the same account has entered nothing
- **THEN** D's record is empty

#### Scenario: An unresolvable archetype records nothing
- **WHEN** C enters a room whose archetype is missing or unregistered
- **THEN** C's record is unchanged and the move succeeds

#### Scenario: A failing write never blocks the move
- **WHEN** the record write raises during entry
- **THEN** a bounded diagnostic is logged and the move succeeds

### Requirement: Reads list registered entered archetypes only
Reading a character's scene-entry record SHALL return the recorded archetypes that are still registered, in scene-archetype registry order, and SHALL never write.

#### Scenario: A removed archetype is not returned
- **WHEN** C's record holds `t_gone`, which the synthetic registry no longer declares
- **THEN** the read omits it and the stored record is unchanged
