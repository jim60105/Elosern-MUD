## ADDED Requirements

### Requirement: Procedurally spawned NPCs carry canonical adult identity

The system SHALL initialize `age` and `apparent_age` to 18 on any synced or spawned NPC that would otherwise lack them, as part of the spawn/sync flow.

#### Scenario: Spawn without existing age gets adult baseline

- **WHEN** an NPC is created by a production spawn or sync path and has no `age` or `apparent_age`
- **THEN** both attributes are persisted as 18

#### Scenario: Existing canonical age is preserved

- **WHEN** an NPC already carries an adult `age`/`apparent_age` (e.g. from import or characterization)
- **THEN** the existing values are not overwritten

#### Scenario: Partial identity fills only the missing field

- **WHEN** an NPC has `age = 35` but no `apparent_age` (or the reverse)
- **THEN** `age` stays 35, `apparent_age` is set to 18 (or the reverse), and neither existing field is changed
