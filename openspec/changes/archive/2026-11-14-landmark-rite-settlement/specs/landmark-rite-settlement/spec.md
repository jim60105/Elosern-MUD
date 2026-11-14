# Spec Delta

## Purpose

Defines where a landmark rite is available, who may perform it, when it is refused, and how one rite settles time, the acting body's sexual state and the completion record as a single atomic unit.

## ADDED Requirements

### Requirement: A rite is available exactly on a rite landmark's node
A rite SHALL be available when the record owner's current canonical node equals the canonical node of a district landmark whose district is assigned a ritual archetype, and nowhere else. The district and archetype SHALL be resolved by the server from that node.

#### Scenario: On the landmark
- **WHEN** the record owner stands on a synthetic district's landmark node
- **THEN** the rite site names that district, its landmark and its archetype

#### Scenario: Elsewhere
- **WHEN** the record owner stands on a neighbouring node, or no rite content is installed
- **THEN** there is no rite site and a rite request is refused as having no landmark

### Requirement: One rite settles as a single atomic unit
A successful rite SHALL produce one climax on the acting body, apply the option's shame and exposure steps to that body, advance world time by the option's full duration, and record the completion on the record owner, all or nothing.

#### Scenario: Committed rite
- **WHEN** the controlled character performs an option of 120 seconds on a rite landmark
- **THEN** world time advanced by 120 seconds, the body's daily climax count rose by one and its climax has ended, its shame and exposure moved by the declared steps, and the record holds the completion

#### Scenario: Failure after the advance
- **WHEN** the record write fails after time was advanced
- **THEN** world time, the body's pleasure, climax phase, climax count, shame and exposure, and the record are all as they were before the request

### Requirement: The acting body and the record owner are distinct roles
Sexual state SHALL be written only to the acting body. The completion record SHALL always belong to the player character. A companion SHALL act only when present, able to act and when the option declares a watch scene; the delivered scene SHALL be the watch scene for a companion and the self scene for the controlled character.

#### Scenario: Companion performs
- **WHEN** a present companion performs an option that declares a watch scene
- **THEN** the companion's sexual state changed, no rite sexual write reached the player character (ordinary time settlement still settles it), the record is the player character's, and the delivered scene is the watch scene

#### Scenario: Possessed companion
- **WHEN** the player possesses a companion and that companion performs with no member named
- **THEN** the delivered scene is the watch scene

#### Scenario: Solo-only option
- **WHEN** a companion is named for an option with no watch scene
- **THEN** the request is refused as having no watch scene and nothing is written

#### Scenario: Unavailable companion
- **WHEN** the named member is absent, asleep, knocked out or not a party member
- **THEN** the request is refused as member unavailable and nothing is written

### Requirement: Every refusal leaves no rite write
A rite request SHALL be refused with a stable code, before any change to time, sexual state or the record, when no landmark is present, the option is unknown, the acting body is unavailable, the record is unreadable, the party is in combat, in dialogue or asleep, the place is unsafe, or the full duration cannot elapse uninterrupted.

#### Scenario: Refusal table
- **WHEN** each refusal condition is produced in turn on a synthetic landmark
- **THEN** each request raises its own stable code and world time, the body's sexual state and the record are unchanged

#### Scenario: Corrupt record
- **WHEN** the record owner's record violates its envelope
- **THEN** the request is refused as record corrupt and the stored value is unchanged

### Requirement: A repeated request identity settles once
A rite request carrying a request identity that already committed SHALL return the committed result and SHALL settle nothing again.

#### Scenario: Retry after a rolled-back attempt
- **WHEN** a request fails after the advance and is retried with the same request identity
- **THEN** the retry commits and world time advanced by exactly one duration in total

#### Scenario: Duplicate request
- **WHEN** the same request identity is submitted twice
- **THEN** both calls return the same result, world time advanced once and the completion count is 1

### Requirement: Rite outcomes are logged as structured events
A committed rite SHALL emit one committed event after commit, a refused request one refused event naming its reason, and an unreadable record one warning.

#### Scenario: Committed, refused and corrupt
- **WHEN** one rite commits, one is refused and one meets a corrupt record
- **THEN** exactly one committed event with the owner, district, archetype, option, body, duration, elapsed time and climax flag, one refused event with its reason, and one record-corrupt warning are emitted

#### Scenario: Rolled-back rite
- **WHEN** a rite fails after the advance and rolls back
- **THEN** no committed event is emitted
