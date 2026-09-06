# npc-canonical-age Specification

## Purpose

Guarantee canonical age attributes on procedurally spawned and synced
NPCs, defaulting missing `age`/`apparent_age` to the authored baseline on
production paths that do not go through import or characterization.

## Requirements

### Requirement: Procedurally spawned NPCs carry canonical age attributes

The system SHALL initialize `age` and `apparent_age` to the authored baseline 18
on any synced or spawned NPC that would otherwise lack them, as part of the
spawn/sync flow (set-if-absent per field).

#### Scenario: Spawn without existing age gets the default age
- **WHEN** an NPC is created by a production spawn or sync path and has no `age` or `apparent_age`
- **THEN** both attributes are persisted as 18

#### Scenario: Existing canonical age is preserved
- **WHEN** an NPC already carries an `age`/`apparent_age` (e.g. from import or characterization)
- **THEN** the existing values are not overwritten

#### Scenario: Partial identity fills only the missing field
- **WHEN** an NPC has `age = 35` but no `apparent_age` (or the reverse)
- **THEN** `age` stays 35, `apparent_age` is set to 18 (or the reverse), and neither existing field is changed
