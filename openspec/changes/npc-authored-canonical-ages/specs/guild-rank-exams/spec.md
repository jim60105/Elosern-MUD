## MODIFIED Requirements

### Requirement: Guild exam opponents carry canonical age
The system SHALL persist canonical `age` and `apparent_age` on every temporary examination opponent from the target rank's authored examiner profile, with both values integers in inclusive 0..10000 and never booleans. Ages and card SHALL be initialized within the existing all-or-nothing examination start before the opponent becomes usable. Invalid authored ages SHALL reject start without an opponent, record, or combat session. Generic default 18 SHALL NOT replace an explicit examiner pair.

#### Scenario: Exam opponent has canonical age
- **WHEN** a guild examination spawns an opponent for a rank whose examiner profile authors age 26 and apparent age 26
- **THEN** the opponent has canonical age 26 and apparent age 26 and its matching examiner card, not default-18 identity

#### Scenario: Invalid examiner age leaves no partial examination
- **WHEN** a requested rank's examiner profile has an out-of-bounds age
- **THEN** start rejects before publication and no opponent, exam record, combat session, merit, or affinity change remains
