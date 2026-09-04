# guild-rank-exams delta

## MODIFIED Requirements

### Requirement: Exam opponents use collision-free unique display keys
`start_guild_exam` SHALL spawn each temporary opponent under the rank's authored examiner name,
falling back to the authored name suffixed with the spawn's primary key (`<authored-name>-<pk>`)
only when another entity (including any player character) already holds that key, so a battlefield
roster or skip-safety registry keyed on the entity key can never see two participants under one
key while the authored name is used whenever it is free.

#### Scenario: A free authored name is used verbatim
- **WHEN** `start_guild_exam` spawns an opponent and no other entity holds the rank's authored
  examiner name
- **THEN** the opponent's key is exactly the authored examiner name

#### Scenario: A taken authored name gains a unique suffix
- **WHEN** a player character is legally named the rank's authored examiner name and requests that
  examination
- **THEN** the spawned opponent key differs (authored name with its `-<pk>` suffix) and the exam
  starts normally

#### Scenario: Concurrent same-rank exams never share a key
- **WHEN** two examinations of one rank spawn opponents while the authored name is occupied
- **THEN** each opponent key includes its own primary-key component and the two keys are never
  identical
