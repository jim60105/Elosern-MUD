## ADDED Requirements

### Requirement: Exam opponents use collision-free unique display keys

`start_guild_exam` SHALL spawn each temporary opponent with a display key unique to that spawn (e.g. `guild-examiner-<rank>-<pk>`), so a participant whose display name equals the bare `guild-examiner-<rank>` pattern can never collide with the opponent in a battlefield roster.

#### Scenario: Same-named player can take the exam

- **WHEN** a player character is legally named `guild-examiner-E` and requests the E examination
- **THEN** the spawned opponent key differs from the player's key and the exam starts normally

#### Scenario: Opponent keys stay deterministic per rank

- **WHEN** two E examinations spawn opponents
- **THEN** each opponent key includes its own unique component (never identical to the other's)
