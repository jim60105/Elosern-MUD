## ADDED Requirements

### Requirement: Exam opponents receive their rank examiner's card at spawn
Spawning an examination opponent SHALL initialize the opponent's compact NPC card from the target rank's examiner profile, with `profile` provenance naming that profile, inside the same all-or-nothing examination start as the opponent, the exam record, and the combat session. A persona initialization failure SHALL delete the partially built opponent and roll the whole start back. Each spawn SHALL receive its own card instance at version 1, so editing one opponent's card never changes another opponent or a later spawn.

#### Scenario: An opponent carries its examiner's card
- **WHEN** a qualified candidate starts the F-rank examination
- **THEN** the spawned opponent's persona equals the F-rank examiner profile's card and its persona metadata is at version 1 with `profile` provenance

#### Scenario: A persona failure aborts the start
- **WHEN** the opponent's card initialization raises during an examination start
- **THEN** no opponent, exam record, or combat session survives and the candidate's state is unchanged

#### Scenario: Spawns do not share edits
- **WHEN** one spawned opponent's card is updated and a later examination spawns another opponent of the same rank
- **THEN** the later opponent carries the unedited profile card at version 1
