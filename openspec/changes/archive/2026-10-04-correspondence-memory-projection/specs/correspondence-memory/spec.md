## Purpose

Projects delivered or first-read letter claims into owner cognition with durable correspondence provenance, without leaking unknown bodies or replacing face-to-face history.

## ADDED Requirements

### Requirement: Letter knowledge enters at the approved boundary

NPC cognition SHALL gain letter content at delivery; player cognition SHALL gain it only at first reading after collection. Undelivered letters and collected-but-unread player content SHALL be absent from recipient retrieval, fixed selection and prompt context.

#### Scenario: Paired letter boundary roles
- **WHEN** the same content is inspected for an undelivered NPC, delivered NPC, collected-unread player and first-read player
- **THEN** only the delivered NPC and first-read player can retrieve it

#### Scenario: Delivery projection lags
- **WHEN** an NPC reply is ready before its durable delivery projection has completed
- **THEN** cognition projection catches up or reply waits; generation never bypasses the delivery knowledge boundary

### Requirement: Letters preserve claims and channel provenance

Letter memories SHALL retain immutable letter/source references and told-information status. Projection SHALL be idempotent across restart. Letters SHALL NOT be copied wholesale into face-to-face turn streams, and letter claims SHALL NOT establish world truth or objective progress.

#### Scenario: Duplicate read projection
- **WHEN** a first-read source is processed twice
- **THEN** one owner memory exists with the original letter provenance

#### Scenario: Claimed deed is unverified
- **WHEN** a letter says an enemy was defeated
- **THEN** it remains told speech, quest progress is unchanged and no defeat fact is created

#### Scenario: Face-to-face continuity
- **WHEN** the NPC later discusses a delivered letter in person
- **THEN** selected shared memory supplies continuity without appending the letter archive as dialogue turns

