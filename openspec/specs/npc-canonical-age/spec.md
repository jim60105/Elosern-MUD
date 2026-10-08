# npc-canonical-age Specification

## Purpose

Guarantee canonical age attributes on procedurally spawned and synced
NPCs, defaulting missing `age`/`apparent_age` to the authored baseline on
production paths that do not go through import or characterization.

## Requirements

### Requirement: Procedurally spawned NPCs carry canonical age attributes

The system SHALL persist `age` and `apparent_age` in every production spawn/sync flow, setting only absent fields, each independently. When the source authors a validated canonical age pair, each absent field SHALL receive its authored value; otherwise it SHALL receive the generic baseline 18. Authored ages SHALL be integers, never booleans, within inclusive 0..10000. A present age SHALL NOT be overwritten by defaults, source changes, restart, or edited persona text.

#### Scenario: Spawn without existing age gets the default age
- **WHEN** an NPC is created by an unauthored production spawn or sync path and has no `age` or `apparent_age`
- **THEN** both attributes are persisted as 18

#### Scenario: Existing canonical age is preserved
- **WHEN** an NPC already carries an `age`/`apparent_age` from import, characterization, or an earlier spawn
- **THEN** the existing values are not overwritten even when its authored source now supplies different values

#### Scenario: Partial identity fills only the missing field
- **WHEN** an NPC has `age = 35` but no `apparent_age` and its source authors age 980 and apparent age 42
- **THEN** `age` stays 35 and `apparent_age` is set to 42, with the reverse missing-field case preserving its existing apparent age and filling authored age 980

#### Scenario: Unauthored partial identity retains the generic fallback
- **WHEN** an unauthored NPC has `age = 35` but no `apparent_age` or the reverse
- **THEN** only the missing field is filled with 18
