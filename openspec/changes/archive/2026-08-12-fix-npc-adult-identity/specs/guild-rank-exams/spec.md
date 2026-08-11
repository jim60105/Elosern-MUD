## ADDED Requirements

### Requirement: Guild exam opponents carry adult identity

The system SHALL persist adult `age`/`apparent_age` on every temporary exam opponent spawned by `start_guild_exam`.

#### Scenario: Exam opponent has adult age

- **WHEN** `guild exam <rank>` spawns `guild-examiner-<rank>`
- **THEN** the opponent has integer `age` and `apparent_age` of at least 18
